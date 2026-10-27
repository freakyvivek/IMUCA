"""
Milestone 6 regression tests: alarm lifecycle (activation, persistence, clearance), confirmed
fault attribution, the curvature transient detector, cached segment scores, and preservation of
the frozen Milestone-5 behaviour under default settings.
"""

import json
import os

import joblib
import numpy as np
import pandas as pd
import pytest

from src.imuca.hybrid_detector import (HybridDetector, HybridSettings, combine, confirm_categories, curvature_scores,
                                       drift_component, segment_flags_from_scores, segment_scores,
                                       segment_transient_flags, SEGMENT_MODES)
from src.imuca.detection_metrics import alarm_episodes

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V3 = os.path.join(ROOT, "data", "synthetic_v3")
M5 = os.path.join(ROOT, "results", "hybrid_fault_detection_20261026_113043")


def _json(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


BASE_CFG = _json(os.path.join(ROOT, "config", "default_config.json"))


def _st(**kw):
    base = dict(segment_mode="phase_blocks", stuck_mode="rule", gbt_threshold=0.9, stuck_alpha=1e-4,
                cusum_k=0.5, cusum_h=15.0, transition_exclusion=5)
    base.update(kw)
    return HybridSettings(**base)


# ==============================================================================
# Default behaviour preserved (frozen Milestone-5 bundle)
# ==============================================================================

@pytest.mark.parametrize("measurand,scenario", [("voltage_V", "FD3_VB_MIXED"), ("current_mA", "FD3_IC_OFFSET_SHIFT"),
                                                ("temperature_C", "FD3_TC_GRADUAL_DRIFT")])
def test_new_code_reproduces_frozen_m5_alarms(measurand, scenario):
    bundle = joblib.load(os.path.join(M5, "models", f"{measurand}_detectors.joblib"))
    settings = bundle["hybrid_settings"]
    df = pd.read_csv(os.path.join(V3, "fault_detection", f"{scenario}.csv"))
    meta = _json(os.path.join(V3, "metadata", f"{scenario}.metadata.json"))
    dev = meta["sensor_error_model"]["device_id"]
    hd = HybridDetector(measurand, bundle["feature_builder"], bundle["targeted_gbt"], bundle["calibration_models"][dev],
                        BASE_CFG, settings, (BASE_CFG["quality"]["mad_threshold"], settings.segment_mad_threshold))
    saved = pd.read_csv(os.path.join(M5, "predictions", f"{measurand}_test_alarms.csv"))
    for _, run in df[df.partition == "test"].groupby("experiment_id"):
        comp = hd.components(run)
        res = hd.apply(comp)
        clean = comp["run"].loc[comp["clean_index"]]
        ref = saved[saved.experiment_id == run.experiment_id.iat[0]].set_index("sequence_number")
        got = pd.DataFrame({"alarm": res["alarm"], "cat": res["category"]}, index=clean["sequence_number"].to_numpy())
        assert np.array_equal(got["alarm"].to_numpy(), ref.loc[got.index, "hybrid_alarm"].to_numpy())
        assert np.array_equal(got["cat"].astype(str).to_numpy(), ref.loc[got.index, "hybrid_category"].astype(str).to_numpy())


def test_cached_segment_scores_equal_direct_detector():
    df = pd.read_csv(os.path.join(V3, "fault_detection", "FD3_TB_ISOLATED_SPIKE.csv"))
    run = df[df.run_id == "VAL01"].reset_index(drop=True)
    for mode in SEGMENT_MODES:
        sc = segment_scores(run, "temperature_C", BASE_CFG, mode)
        for thr in (3.5, 5.0, 7.0, 12.0):
            assert np.array_equal(segment_flags_from_scores(sc, thr), segment_transient_flags(run, "temperature_C", BASE_CFG, mode, thr))
    with pytest.raises(ValueError):
        segment_flags_from_scores(sc, 3.0)
    sc25 = segment_scores(run, "temperature_C", BASE_CFG, "phase_blocks", base_threshold=2.5)
    for thr in (2.5, 3.0, 3.5, 7.0):
        assert np.array_equal(segment_flags_from_scores(sc25, thr), segment_transient_flags(run, "temperature_C", BASE_CFG, "phase_blocks", thr))


# ==============================================================================
# Alarm lifecycle
# ==============================================================================

def _err(n=1200, seed=1):
    rng = np.random.default_rng(seed)
    return np.arange(float(n)), rng.normal(size=n)


def test_latched_alarm_persists_after_transient_cause_but_hysteresis_clears():
    t, e = _err()
    e[400:420] += 8.0                      # short excursion (e.g. an unexplained transient fault)
    usable = np.ones(len(e), bool)
    latched = drift_component(t, e, usable, [], _st(cusum_h=10.0))
    hyst = drift_component(t, e, usable, [], _st(cusum_h=10.0, drift_lifecycle="hysteresis", clear_window=60, clear_z=2.0))
    first_l = int(np.argmax(latched))
    assert 400 <= first_l <= 405 and latched[first_l:].all()     # M5 behaviour: stays on to the end of the run
    first = int(np.argmax(hyst))
    assert 400 <= first <= 425
    eps = alarm_episodes(hyst, np.array(["R"] * len(e)), gap=2)
    assert len(eps) == 1 and eps[0]["end"] < 400 + 200          # cleared within a few clearance windows
    assert eps[0]["end"] - first + 1 >= 60                      # never cleared before clear_window samples


def test_hysteresis_keeps_genuine_drift_active_and_reactivates():
    t, e = _err(1500, seed=2)
    e[300:310] += 9.0                                            # transient excursion -> alarm then clearance
    e[900:] += 0.03 * np.arange(600)                             # genuine drift later in the run
    a = drift_component(t, e, np.ones(len(e), bool), [], _st(cusum_h=10.0, drift_lifecycle="hysteresis"))
    eps = alarm_episodes(a, np.array(["R"] * len(e)), gap=2)
    assert len(eps) == 2
    assert eps[1]["start"] >= 900 and eps[1]["end"] == len(e) - 1   # drift alarm not hidden, persists while drift continues


def test_unknown_lifecycle_rejected():
    t, e = _err()
    e[500:] += 10
    with pytest.raises(ValueError):
        drift_component(t, e, np.ones(len(e), bool), [], _st(cusum_h=10.0, drift_lifecycle="sometimes"))


# ==============================================================================
# Confirmed attribution
# ==============================================================================

def _signal(kind, n=300, seed=3):
    rng = np.random.default_rng(seed)
    x = 5.0 + rng.normal(0, 0.001, n)
    alarm = np.zeros(n, bool)
    if kind == "offset":
        x[150:] += 0.02
        alarm[150:153] = True
    elif kind == "spike":
        x[150] += 0.03
        alarm[150] = True
    elif kind == "abrupt":
        x[150:170] += 0.02
        alarm[150:170] = True
    return x, alarm


@pytest.mark.parametrize("kind,expected", [("offset", "persistent"), ("spike", "transient"), ("abrupt", "transient")])
def test_confirmed_attribution(kind, expected):
    x, alarm = _signal(kind)
    n = len(x)
    cat = np.where(alarm, "transient", "none").astype(object)    # provisional: the segment detector fired first
    out = confirm_categories(cat, alarm, x, np.zeros(n, int), np.array(["steady"] * n, dtype=object), 1e-4,
                             _st(attribution="confirmed"), np.array(["R"] * n))
    assert set(out[alarm]) == {expected}
    assert (out[~alarm] == "none").all()


def test_attribution_keeps_provisional_label_in_nonstationary_phase_and_stuck_drift_untouched():
    x, alarm = _signal("offset")
    n = len(x)
    cat = np.where(alarm, "transient", "none").astype(object)
    out = confirm_categories(cat, alarm, x, np.zeros(n, int), np.array(["plateau_settling"] * n, dtype=object), 1e-4,
                             _st(attribution="confirmed"), np.array(["R"] * n))
    assert set(out[alarm]) == {"transient"}
    cat2 = np.where(alarm, "stuck", "none").astype(object)
    out2 = confirm_categories(cat2, alarm, x, np.zeros(n, int), np.array(["steady"] * n, dtype=object), 1e-4,
                              _st(attribution="confirmed"), np.array(["R"] * n))
    assert set(out2[alarm]) == {"stuck"}


def test_combine_confirmed_reports_provisional_and_final_categories_without_duplicates():
    x, alarm = _signal("offset")
    n = len(x)
    exp = np.array(["R"] * n)
    gbt = np.zeros(n, bool); gbt[151:156] = True                 # GBT also fires on the same step
    sig = {"x": x, "setpoint_index": np.zeros(n, int), "protocol_phase": np.array(["steady"] * n, dtype=object), "floor": 1e-4}
    res = combine(alarm, np.zeros(n, bool), gbt, np.zeros(n), None, _st(attribution="confirmed"), exp, sig)
    assert res["provisional_category"][150] == "transient" and res["category"][150] == "persistent"
    assert len(alarm_episodes(res["alarm"], exp, 2)) == 1       # one episode, not one per component
    assert res["alarm"].sum() == len(set(np.flatnonzero(alarm)) | set(np.flatnonzero(gbt)))


# ==============================================================================
# Curvature transient detector
# ==============================================================================

def test_curvature_quiet_on_ramps_and_settling_but_flags_spikes():
    rng = np.random.default_rng(5)
    q = 0.0625
    ramp = np.r_[np.full(100, 25.0), 25.0 + 0.1 * np.arange(1, 151), np.full(300, 40.0)]
    elem = ramp.copy()
    for k in range(1, len(elem)):                                # first-order lag, tau = 20 s
        elem[k] = elem[k - 1] + (1 - np.exp(-1 / 20)) * (ramp[k] - elem[k - 1])
    x = np.round((elem + rng.normal(0, 0.03, len(elem))) / q) * q
    z = curvature_scores(x, np.zeros(len(x), int), floor=0.016)
    assert z.max() < 8.0
    x2 = x.copy(); x2[300] += 1.2                                 # ~35 sigma of noise, ~11 robust d2-scales
    z2 = curvature_scores(x2, np.zeros(len(x), int), floor=0.016)
    assert z2[300] > 8.0 and z2[300] > 1.5 * z.max()
    assert np.array_equal(z2[:300], z[:300])                     # causal: nothing before the spike changes


def test_curvature_guard_after_setpoint_change():
    x = np.r_[np.full(200, 25.0), np.full(200, 40.0)] + np.random.default_rng(6).normal(0, 0.03, 400)
    sp = np.r_[np.zeros(200, int), np.ones(200, int)]
    z = curvature_scores(x, sp, floor=0.016, guard=3)
    assert (z[200:203] == 0).all()
    assert curvature_scores(x, np.zeros(400, int), floor=0.016)[200] > 8.0   # without protocol knowledge it would alarm


def test_absolute_clearance_band_clears_despite_baseline_estimation_error():
    t, e = _err(1500, seed=11)
    e[600:] += 0.25                                              # small residual bias after a transient (baseline error)
    e[400:420] += 8.0
    strict = drift_component(t, e, np.ones(len(e), bool), [], _st(cusum_h=10.0, drift_lifecycle="hysteresis", clear_window=60, clear_z=1.5))
    band = drift_component(t, e, np.ones(len(e), bool), [], _st(cusum_h=10.0, drift_lifecycle="hysteresis", clear_window=60, clear_sigma=1.0))
    assert band.sum() < strict.sum()
    assert not band[700:].all()


def test_confirmation_delay_fixes_partially_flagged_abrupt_change():
    rng = np.random.default_rng(12)
    n = 300
    x = 5.0 + rng.normal(0, 0.001, n)
    x[150:190] += 0.02                                           # 40-sample abrupt change ...
    alarm = np.zeros(n, bool); alarm[150:155] = True             # ... of which only the start was flagged
    cat = np.where(alarm, "transient", "none").astype(object)
    args = (alarm, x, np.zeros(n, int), np.array(["steady"] * n, dtype=object), 1e-4)
    no_delay = confirm_categories(cat, *args, _st(attribution="confirmed", confirm_window=20, confirm_delay=0), np.array(["R"] * n))
    delayed = confirm_categories(cat, *args, _st(attribution="confirmed", confirm_window=20, confirm_delay=45), np.array(["R"] * n))
    assert set(no_delay[alarm]) == {"persistent"}               # the defect: looks persistent right after the episode
    assert set(delayed[alarm]) == {"transient"}
    x2, a2 = _signal("offset")
    off = confirm_categories(np.where(a2, "transient", "none").astype(object), a2, x2, np.zeros(len(x2), int),
                             np.array(["steady"] * len(x2), dtype=object), 1e-4,
                             _st(attribution="confirmed", confirm_window=20, confirm_delay=45), np.array(["R"] * len(x2)))
    assert set(off[a2]) == {"persistent"}                        # a genuine offset is still persistent with the delay


def test_drift_alarm_starting_just_before_another_episode_is_explained():
    rng = np.random.default_rng(13)
    n = 600
    t = np.arange(float(n)); e = rng.normal(size=n); e[300:] += 30.0
    exp = np.array(["R"] * n)
    di = {"t_s": t, "err": e, "finite": np.ones(n, bool), "segment_starts": np.array([], int),
          "protocol": pd.DataFrame({"setpoint_index": np.zeros(n, int), "protocol_phase": ["steady"] * n, "sequence_number": np.arange(1, n + 1)})}
    z = np.zeros(n, bool)
    stuck = z.copy(); stuck[309:330] = True                      # stuck confirmed ~9 samples after the drift alarm fired
    ident = np.zeros(n); ident[309:330] = 10
    rule = stuck.copy()
    m5 = combine(z, rule, z, ident, dict(di), _st(), exp)
    m6 = combine(z, rule, z, ident, dict(di), _st(explain_before=15), exp)
    assert m5["drift"][300:309].any()                            # M5: drift alarm survives (not explained)
    assert not m6["drift"].any()                                 # explained by the stuck episode that follows


def test_transient_transition_window_suppresses_segment_flags_after_true_steps():
    n = 400
    sp = np.r_[np.zeros(200, int), np.ones(200, int)]
    comp = {"segment_scores": {"phase_blocks_stationary_only": {"z": np.r_[np.zeros(200), np.full(30, 9.0), np.zeros(170)],
                                                                "other": np.zeros(n, bool), "nonstationary": np.zeros(n, bool),
                                                                "base_threshold": 3.5, "mode": "phase_blocks_stationary_only"}},
            "signal": {"protocol_phase": np.array(["steady"] * n, dtype=object)},
            "signal_protocol": pd.DataFrame({"setpoint_index": sp, "protocol_phase": ["steady"] * n, "sequence_number": np.arange(1, n + 1)}),
            "curvature_z": np.r_[np.zeros(215), [20.0], np.zeros(184)]}
    from src.imuca.hybrid_detector import transient_flags
    base = transient_flags(comp, _st(segment_mode="phase_blocks_stationary_only", segment_mad_threshold=5.0))
    win = transient_flags(comp, _st(segment_mode="phase_blocks_stationary_only", segment_mad_threshold=5.0,
                                    transient_transition_window=60, transient_extra="curvature_nonstationary", curvature_threshold=8.0))
    assert base[200:230].all()                                   # lag settling after a true step flagged (the defect)
    assert list(np.flatnonzero(win)) == [215]                    # suppressed, but a spike inside the window is still caught


def test_error_based_attribution_spans_setpoint_changes():
    from src.imuca.hybrid_detector import confirm_categories_error
    rng = np.random.default_rng(14)
    n = 400
    err = rng.normal(0, 0.001, n); err[180:] += 0.02            # persistent offset just before a set-point change at 190
    alarm = np.zeros(n, bool); alarm[180:184] = True
    cat = np.where(alarm, "transient", "none").astype(object)
    usable = np.ones(n, bool); usable[190:250] = False          # transition after the set-point change excluded
    out = confirm_categories_error(cat, alarm, err, usable, np.array(["steady"] * n, dtype=object), 1e-4,
                                   _st(attribution="confirmed", attribution_source="error", confirm_window=20, confirm_delay=45),
                                   np.array(["R"] * n))
    assert set(out[alarm]) == {"persistent"}
    err2 = rng.normal(0, 0.001, n); err2[180:200] += 0.02        # abrupt change that ends
    out2 = confirm_categories_error(cat, alarm, err2, usable, np.array(["steady"] * n, dtype=object), 1e-4,
                                    _st(attribution="confirmed", attribution_source="error", confirm_window=20, confirm_delay=45),
                                    np.array(["R"] * n))
    assert set(out2[alarm]) == {"transient"}


def test_suppress_persistent_alarms_on_ramps_keeps_stuck():
    n = 50
    exp = np.array(["R"] * n)
    phase = np.array(["steady"] * 20 + ["ramp"] * 30, dtype=object)
    gbt = np.zeros(n, bool); gbt[25:30] = True; gbt[40:45] = True
    ident = np.zeros(n); ident[40:45] = 6                        # identical readings on a ramp -> stuck evidence
    sig = {"x": np.zeros(n), "setpoint_index": np.zeros(n, int), "protocol_phase": phase, "floor": 1e-4}
    z = np.zeros(n, bool)
    keep = combine(z, z, gbt, ident, None, _st(stuck_mode="gbt"), exp, sig)
    sup = combine(z, z, gbt, ident, None, _st(stuck_mode="gbt", suppress_persistent_nonstationary=True), exp, sig)
    assert keep["persistent"][25:30].all() and not sup["persistent"].any()
    assert sup["stuck"][40:45].all()


def test_confirmed_attribution_error_persistent_alarm_to_end():
    from src.imuca.hybrid_detector import confirm_categories_error
    rng = np.random.default_rng(42)
    n = 300
    err = rng.normal(0, 0.001, n)
    err[100:] += 0.025  # persistent offset shift from 100 to end
    alarm = np.zeros(n, bool)
    alarm[100:] = True  # GBT/hybrid alarm stays active through end of run
    cat = np.where(alarm, "transient", "none").astype(object)
    usable = np.ones(n, bool)
    out = confirm_categories_error(cat, alarm, err, usable, np.array(["steady"] * n, dtype=object), 1e-4,
                                   _st(attribution="confirmed", attribution_source="error", confirm_window=20, confirm_delay=15),
                                   np.array(["R"] * n))
    assert set(out[alarm]) == {"persistent"}


def test_settling_suppression_blocks_segment_flags_in_settling():
    from src.imuca.hybrid_detector import transient_flags
    n = 100
    comp = {
        "segment_scores": {
            "phase_blocks": {
                "z": np.full(n, 8.0),  # all samples would be flagged by segment detector
                "other": np.zeros(n, bool),
                "nonstationary": np.zeros(n, bool),
                "base_threshold": 3.5,
                "mode": "phase_blocks"
            }
        },
        "signal": {"protocol_phase": np.array(["plateau_settling"] * n, dtype=object)},
        "signal_protocol": pd.DataFrame({
            "setpoint_index": np.zeros(n, int),
            "protocol_phase": ["plateau_settling"] * n,
            "sequence_number": np.arange(1, n + 1)
        }),
        "curvature_z": np.r_[np.zeros(50), [15.0], np.zeros(49)]  # genuine spike at index 50
    }
    # Without settling_suppression: all samples flagged
    unsupp = transient_flags(comp, _st(segment_mode="phase_blocks", segment_mad_threshold=3.5))
    assert unsupp.all()

    # With settling_suppression + curvature: only the spike at index 50 is flagged
    supp = transient_flags(comp, _st(segment_mode="phase_blocks", segment_mad_threshold=3.5,
                                     settling_suppression=True, transient_extra="curvature_nonstationary",
                                     curvature_threshold=8.0))
    assert list(np.flatnonzero(supp)) == [50]

