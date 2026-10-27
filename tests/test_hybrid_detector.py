"""
Tests for the hybrid fault detector: causal behaviour, leakage prevention, reproducibility,
alarm combination, fault-event matching, independent v3 data, and compatibility with the
existing metrology pipeline.
"""

import json
import os

import numpy as np
import pandas as pd
import pytest

from src.imuca.calibration import CalibrationEngine
from src.imuca.data_ingestion import DataIngestionPipeline
from src.imuca.data_quality import DataQualityAssessor
from src.imuca.ml_features import CausalFeatureBuilder, build_signal_dataset, causal_features
from src.imuca.ml_fault_detection import TargetedGBTDetector, targeted_weights
from src.imuca.hybrid_detector import (HybridDetector, HybridSettings, combine, drift_component, stuck_rule_flags,
                                       segment_transient_flags, transition_mask, CATEGORY_PRECEDENCE)
from src.imuca.detection_metrics import (event_detection, event_windows, detect_with_windows, alarm_episodes,
                                         fault_active_mask, classify_episodes, wilson_interval, poisson_rate_interval,
                                         bootstrap_by_run)
from src.imuca.cusum_tuning import run_cusum
from src.imuca.synthetic_suite import SyntheticSuiteGenerator, dataframe_to_csv_bytes, _sha256_bytes, iter_run_csv_buffers

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

V3 = os.path.join(ROOT, "data", "synthetic_v3")
BASE_CFG = _json(os.path.join(ROOT, "config", "default_config.json"))


def _v3(sid, group="fault_detection"):
    return pd.read_csv(os.path.join(V3, group, f"{sid}.csv"))


def _settings(**kw):
    base = dict(segment_mode="phase_blocks", stuck_mode="gbt_or_rule", gbt_threshold=0.9, stuck_alpha=1e-4,
                cusum_k=0.5, cusum_h=15.0, transition_exclusion=5)
    base.update(kw)
    return HybridSettings(**base)


@pytest.fixture(scope="module")
def volt_setup():
    sweep = _v3("SWEEP_DUT_V11", "voltage")
    d = sweep[sweep.partition == "calibration"]
    cal = CalibrationEngine().select_best_model(d.voltage_V.values, d.reference_voltage_V.values, max_degree=3)
    frames = {s: _v3(s) for s in ("FD3_VA_NONE", "FD3_VA_MIXED", "FD3_VA_STUCK_SIGNAL", "FD3_VA_OFFSET_SHIFT")}
    builder = CausalFeatureBuilder("voltage_V").fit(pd.concat([f[f.partition == "calibration"] for f in frames.values()]))
    return cal, frames, builder


# ==============================================================================
# Independent v3 data
# ==============================================================================

def test_v3_seeds_independent_of_v2_and_runs_partitioned():
    v2 = _json(os.path.join(ROOT, "config", "synthetic_suite_config.json"))
    v3 = _json(os.path.join(ROOT, "config", "synthetic_suite_v3_config.json"))
    assert not set(v2["seed_roots"].values()) & set(v3["seed_roots"].values())
    assert len(set(v3["seed_roots"].values())) == 3
    man = _json(os.path.join(V3, "metadata", "suite_manifest.json"))
    assert man["scenario_count"] == 94
    seeds = [s for f in man["files"] for s in f["run_seeds"].values()]
    assert len(seeds) == len(set(seeds))
    for f in man["files"][:20]:
        meta = _json(os.path.join(V3, f["metadata_file"]))
        parts = meta["partitions"]
        ids = [set(parts[p]["experiment_ids"]) for p in ("calibration", "validation", "test")]
        assert not (ids[0] & ids[1]) and not (ids[0] & ids[2]) and not (ids[1] & ids[2])


def test_v3_regenerates_bit_identically_and_variants_expand():
    g = SyntheticSuiteGenerator.from_file(os.path.join(ROOT, "config", "synthetic_suite_v3_config.json"))
    man = _json(os.path.join(V3, "metadata", "suite_manifest.json"))
    entry = next(f for f in man["files"] if f["scenario_id"] == "FD3_TC_MIXED")
    df, meta = g.generate_scenario("FD3_TC_MIXED")
    assert _sha256_bytes(dataframe_to_csv_bytes(df)) == entry["csv_sha256"]
    assert {e["fault_type"] for e in meta["fault_events"]} == {"isolated_spike", "stuck_signal", "abrupt_change", "offset_shift"}
    prefixes = {s["scenario_id"].rsplit("_", 1)[0] for s in g.scenarios if s["scenario_id"].startswith("FD3_")}
    assert {"FD3_VA", "FD3_VB", "FD3_VC", "FD3_IA", "FD3_IB", "FD3_IC", "FD3_TA", "FD3_TB", "FD3_TC"} <= {p.split("_INTEGRITY")[0].split("_GRADUAL")[0].split("_ISOLATED")[0].split("_OFFSET")[0].split("_GAIN")[0].split("_ABRUPT")[0].split("_STUCK")[0] for p in prefixes}


# ==============================================================================
# Causal behaviour
# ==============================================================================

def test_stuck_rule_is_causal_and_fires_on_long_identical_runs():
    rng = np.random.default_rng(2)
    x = np.round((5 + rng.normal(0, 0.0015, 900)) / 0.001) * 0.001
    x[500:540] = x[499]
    f = causal_features(x, 1e-4)
    flags = stuck_rule_flags(f, 1e-4)
    assert flags[520:540].all() and not flags[:495].any()
    y = x.copy(); y[600:] += 1.0
    assert np.array_equal(stuck_rule_flags(causal_features(y, 1e-4), 1e-4)[:600], flags[:600])


def test_drift_component_is_causal():
    rng = np.random.default_rng(4)
    t = np.arange(1200.0); e = rng.normal(size=1200); e[700:] += 0.02 * np.arange(500)
    st = _settings(cusum_k=0.5, cusum_h=15.0)
    usable = np.ones(1200, bool)
    a = drift_component(t, e, usable, [], st)
    assert a.any() and np.argmax(a) >= 700
    e2 = e.copy(); e2[1000:] = 50.0
    b = drift_component(t, e2, usable, [], st)
    first = np.argmax(a)
    assert np.array_equal(a[:first + 1], b[:first + 1])


def test_hybrid_decisions_final_at_segment_end(volt_setup):
    """Changing records after a protocol segment ends leaves all earlier hybrid decisions unchanged."""
    cal, frames, builder = volt_setup
    run = frames["FD3_VA_MIXED"].query("run_id == 'VAL01'").reset_index(drop=True)
    hd = HybridDetector("voltage_V", builder, None, cal, BASE_CFG, _settings())
    a = hd.annotate(run)
    seg_end = int(np.flatnonzero(run.setpoint_index.values == 0)[-1])
    mod = run.copy()
    mod.loc[seg_end + 1:, "voltage_V"] += 0.5
    b = hd.annotate(mod)
    cols = ["hybrid_integrity_alarm", "hybrid_signal_alarm", "hybrid_category"]
    pd.testing.assert_frame_equal(a.loc[:seg_end, cols], b.loc[:seg_end, cols])


# ==============================================================================
# Leakage prevention
# ==============================================================================

def test_hybrid_ignores_truth_labels_and_derived_errors(volt_setup):
    cal, frames, builder = volt_setup
    run = frames["FD3_VA_MIXED"].query("run_id == 'VAL01'").reset_index(drop=True)
    hd = HybridDetector("voltage_V", builder, None, cal, BASE_CFG, _settings())
    a = hd.annotate(run)
    poisoned = run.copy()
    for c in run.columns:
        if c.startswith(("true_", "label_", "error_")) or c in ("is_injected_fault", "dq_flags", "operating_condition_id", "partition"):
            poisoned[c] = 1e6 if pd.api.types.is_numeric_dtype(run[c]) else "POISON"
    b = hd.annotate(poisoned)
    for c in ("hybrid_integrity_alarm", "hybrid_signal_alarm", "hybrid_category"):
        assert a[c].equals(b[c])


def test_targeted_weights_exclude_other_components_and_late_persistent_rows():
    train = pd.DataFrame({
        "signal_fault_type": ["none"] * 6 + ["offset_shift"] * 4 + ["isolated_spike", "stuck_signal", "stuck_signal", "gradual_drift"],
        "label_fault_event_id": ["none"] * 6 + ["E1"] * 4 + ["E2", "E3", "E3", "E4"],
        "sequence_number": list(range(1, 7)) + [10, 11, 12, 13] + [20, 21, 22, 23],
    })
    y, w = targeted_weights(train, ("offset_shift", "gain_change", "stuck_signal"), ("isolated_spike", "abrupt_change", "gradual_drift"),
                            onset_window=2, persistent_types=("offset_shift", "gain_change"), onset_seq={"E1": 10})
    assert list(y[6:10]) == [True, True, False, False] and w[8] == 0 and w[9] == 0   # beyond onset window
    assert w[10] == 0 and w[13] == 0                                                  # spike, drift excluded
    assert y[11] and y[12]
    assert np.isclose(w[y & (train.signal_fault_type == "offset_shift").values].sum(), w[y & (train.signal_fault_type == "stuck_signal").values].sum())
    assert np.isclose(w[~y & (w > 0)].sum(), w[y].sum())


def test_targeted_gbt_rejects_non_calibration_and_is_reproducible(volt_setup):
    _, frames, builder = volt_setup
    sig, _ = build_signal_dataset(frames, "voltage_V", builder)
    kw = dict(params={"max_depth": 3, "learning_rate": 0.1, "max_iter": 30}, seed=1, target_types=("offset_shift", "stuck_signal"),
              excluded_types=("isolated_spike", "abrupt_change", "gradual_drift"), onset_window=30,
              persistent_types=("offset_shift",), monotone_increasing=("f_identical_run",))
    with pytest.raises(ValueError):
        TargetedGBTDetector(**kw).fit(sig, {})
    train = sig[sig.partition == "calibration"].reset_index(drop=True)
    meta = {e["event_id"]: e["onset_sequence_number"] for s in frames for e in _json(os.path.join(V3, "metadata", f"{s}.metadata.json"))["fault_events"]}
    a = TargetedGBTDetector(**kw).fit(train, meta).score(sig[sig.partition == "validation"])
    b = TargetedGBTDetector(**kw).fit(train, meta).score(sig[sig.partition == "validation"])
    assert np.array_equal(a, b)


def test_annotation_is_reproducible_and_non_destructive(volt_setup):
    cal, frames, builder = volt_setup
    run = frames["FD3_VA_STUCK_SIGNAL"].query("run_id == 'VAL01'").reset_index(drop=True)
    before = run.copy()
    hd = HybridDetector("voltage_V", builder, None, cal, BASE_CFG, _settings(stuck_mode="rule"))
    a, b = hd.annotate(run), hd.annotate(run)
    pd.testing.assert_frame_equal(run, before)
    pd.testing.assert_frame_equal(a, b)
    pd.testing.assert_frame_equal(a[run.columns], run)
    # the stuck events of this run are flagged with the stuck category
    stuck_rows = a.label_fault_type.str.contains("stuck_signal")
    assert (a.loc[stuck_rows, "hybrid_category"] == "stuck").any()


# ==============================================================================
# Alarm combination
# ==============================================================================

def test_combination_precedence_and_single_alarm_per_record():
    n = 40
    exp = np.array(["R"] * n)
    transient = np.zeros(n, bool); transient[5:7] = True
    gbt = np.zeros(n, bool); gbt[5:10] = True; gbt[20:23] = True
    ident = np.zeros(n); ident[20:23] = 5
    rule = np.zeros(n, bool)
    res = combine(transient, rule, gbt, ident, None, _settings(stuck_mode="gbt"), exp)
    assert list(res["category"][5:7]) == ["transient"] * 2          # transient wins over persistent
    assert list(res["category"][7:10]) == ["persistent"] * 3
    assert list(res["category"][20:23]) == ["stuck"] * 3            # GBT alarm with identical-run evidence
    assert res["alarm"].sum() == 2 + 3 + 3                          # one alarm per record, no double counting
    assert len(alarm_episodes(res["alarm"], exp, gap=2)) == 2
    assert CATEGORY_PRECEDENCE == ("transient", "stuck", "persistent", "drift")


def test_stuck_modes():
    n = 10
    exp = np.array(["R"] * n)
    rule = np.zeros(n, bool); rule[2] = True
    gbt = np.zeros(n, bool); gbt[6] = True
    ident = np.zeros(n); ident[6] = 4
    z = np.zeros(n, bool)
    g = combine(z, rule, gbt, ident, None, _settings(stuck_mode="gbt"), exp)["stuck"]
    r = combine(z, rule, gbt, ident, None, _settings(stuck_mode="rule"), exp)["stuck"]
    b = combine(z, rule, gbt, ident, None, _settings(stuck_mode="gbt_or_rule"), exp)["stuck"]
    assert list(np.flatnonzero(g)) == [6] and list(np.flatnonzero(r)) == [2] and list(np.flatnonzero(b)) == [2, 6]


def test_drift_alarm_explained_by_preceding_transient_episode():
    rng = np.random.default_rng(8)
    n = 600
    t = np.arange(float(n)); e = rng.normal(size=n)
    e[300:] += 30.0                                              # step: CUSUM alarms immediately at 300
    exp = np.array(["R"] * n)
    drift_inputs = {"t_s": t, "err": e, "finite": np.ones(n, bool), "segment_starts": np.array([], int),
                    "protocol": pd.DataFrame({"setpoint_index": np.zeros(n, int), "protocol_phase": ["steady"] * n, "sequence_number": np.arange(1, n + 1)})}
    z = np.zeros(n, bool)
    plain = combine(z, z, z, np.zeros(n), dict(drift_inputs), _settings(), exp)
    assert plain["drift"][300:].all()
    transient = z.copy(); transient[298] = True                  # another component explains the change
    explained = combine(transient, z, z, np.zeros(n), dict(drift_inputs), _settings(), exp)
    assert not explained["drift"].any() and explained["category"][298] == "transient"


def test_drift_rebaselines_after_persistent_episode():
    rng = np.random.default_rng(9)
    n = 900
    t = np.arange(float(n)); e = rng.normal(size=n)
    e[400:] += 25.0                                              # persistent offset explained by the GBT component
    st = _settings()
    eps = [{"run": "R", "start": 400, "end": 405}]
    a = drift_component(t, e, np.ones(n, bool), eps, st)
    assert not a.any()                                           # re-baselined after the offset: no drift alarm
    e2 = e.copy(); e2[650:] += 0.05 * np.arange(250)             # genuine drift after the offset
    assert drift_component(t, e2, np.ones(n, bool), eps, st)[650:].any()


# ==============================================================================
# Fault-event matching and intervals
# ==============================================================================

def _match_frame():
    n = 60
    return pd.DataFrame({"experiment_id": ["R"] * n, "sequence_number": np.arange(1, n + 1),
                         "label_fault_event_id": ["none"] * 10 + ["S1"] + ["none"] * 9 + ["P1"] * 40,
                         "is_signal_fault": [False] * 10 + [True] + [False] * 9 + [True] * 40})


def test_precomputed_windows_match_event_detection():
    df = _match_frame()
    events = [{"event_id": "S1", "fault_type": "isolated_spike", "run_id": "R", "onset_sequence_number": 11},
              {"event_id": "P1", "fault_type": "offset_shift", "run_id": "R", "onset_sequence_number": 21},
              {"event_id": "D1", "fault_type": "gradual_drift", "run_id": "R", "onset_sequence_number": 30}]
    rng = np.random.default_rng(0)
    for _ in range(20):
        pred = rng.random(len(df)) < 0.08
        ref = event_detection(pred, df, events, ["offset_shift"], 10, 0.01, transient_tolerance=2, run_end_types=["gradual_drift"])
        win = event_windows(df, events, ["offset_shift"], 10, 2, ["gradual_drift"])
        new = detect_with_windows(pred, win, df.sequence_number.values, 0.01)
        for a, b in zip(ref, new):
            for k in ("event_id", "detected", "delay_samples", "window_samples", "chance_detection_probability"):
                assert a[k] == b[k]


def test_spike_tolerance_and_episode_classification():
    df = _match_frame()
    events = [{"event_id": "S1", "fault_type": "isolated_spike", "run_id": "R", "onset_sequence_number": 11}]
    pred = np.zeros(len(df), bool); pred[12] = True               # alarm 2 samples after the spike
    win = event_windows(df, events, [], 0, transient_tolerance=2)
    assert detect_with_windows(pred, win, df.sequence_number.values)[0]["delay_samples"] == 2
    active = fault_active_mask(df, tolerance=2)
    assert active[11] and active[12] and not active[13]
    # 12 and 15 are 2 quiet records apart -> merged; 16-17 after 3 quiet records -> separate episode
    merged = alarm_episodes(np.isin(np.arange(len(df)), [12, 15]), df.experiment_id.values, gap=2)
    assert len(merged) == 1
    eps = alarm_episodes(np.isin(np.arange(len(df)), [12, 16, 17]), df.experiment_id.values, gap=2)
    assert classify_episodes(eps, active) == [True, False]


def test_interval_estimators():
    lo, hi = wilson_interval(0, 10)
    assert lo == 0.0 and hi == pytest.approx(0.2775, abs=1e-3)
    lo, hi = wilson_interval(10, 10)
    assert hi == 1.0 and lo == pytest.approx(0.7225, abs=1e-3)
    lo, hi = poisson_rate_interval(0, 1.0)
    assert lo == 0.0 and hi == pytest.approx(3.689, abs=1e-3)
    lo, hi = poisson_rate_interval(5, 2.0)
    assert lo == pytest.approx(1.6235 / 2, abs=1e-3) and hi == pytest.approx(11.668 / 2, abs=1e-3)
    tab = pd.DataFrame({"x": np.arange(20.0)})
    a = bootstrap_by_run(tab, lambda t: t.x.mean(), 200, seed=3)
    assert a == bootstrap_by_run(tab, lambda t: t.x.mean(), 200, seed=3) and a[0] < 9.5 < a[1]


# ==============================================================================
# Compatibility with the existing metrology pipeline
# ==============================================================================

def test_segment_component_default_threshold_is_existing_detector():
    run = _v3("FD3_IB_NONE").query("run_id == 'VAL01'").reset_index(drop=True)
    a = segment_transient_flags(run, "current_mA", BASE_CFG, "setpoint_blocks")
    b = segment_transient_flags(run, "current_mA", BASE_CFG, "setpoint_blocks", BASE_CFG["quality"]["mad_threshold"])
    assert np.array_equal(a, b)
    # identical to calling the existing assessor directly on one segment
    seg = run[run.setpoint_index == 1].reset_index(drop=True)
    rep = DataQualityAssessor(mad_threshold=3.5).assess(seg[["current_mA", "sequence_number", "elapsed_ms", "status"]], "current_mA",
                                                        (0.0, 3200.0), max_rate_of_change=500.0, ground_truth_fault_col=None)
    direct = sorted({i.record_index for i in rep.issues if i.issue_type in ("OUTLIER", "ABRUPT_CHANGE", "OUT_OF_RANGE")})
    assert direct == list(np.flatnonzero(a[(run.setpoint_index == 1).values]))


def test_v3_runs_ingest_through_existing_pipeline():
    pipe = DataIngestionPipeline()
    for exp_id, buf in iter_run_csv_buffers(os.path.join(V3, "temperature", "TEMP_LONG_TRANSITIONS.csv")):
        _, diag = pipe.load_csv(buf, source_id=exp_id)
        assert diag.schema_validation.is_valid and diag.schema_validation.error_record_count == 0


def test_run_cusum_min_baseline_default_unchanged():
    rng = np.random.default_rng(1)
    e = rng.normal(size=400)
    a = run_cusum(np.arange(400.0), e, 0.5, 8.0)
    b = run_cusum(np.arange(400.0), e, 0.5, 8.0, min_baseline=10)
    assert a == b and a["baseline_samples"] == 40


def test_transition_mask_respects_explicit_settling_phases():
    clean = pd.DataFrame({"setpoint_index": [0] * 5 + [1] * 10 + [2] * 10,
                          "protocol_phase": ["steady"] * 5 + ["steady"] * 10 + ["plateau_settling"] * 3 + ["plateau_stable"] * 7,
                          "sequence_number": np.arange(1, 26)})
    m = transition_mask(clean, 4)
    assert list(m[5:9]) == [True] * 4 and not m[9]               # window after a change into a 'steady' segment
    assert list(m[15:18]) == [True] * 3 and not m[18:].any()     # plateau protocol: only explicit settling excluded
