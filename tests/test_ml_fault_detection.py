"""
Tests for causal feature engineering, leakage safeguards, split integrity, reproducibility,
detection metrics and CUSUM behaviour (ML fault-detection milestone).
"""

import json
import os

import numpy as np
import pandas as pd
import pytest

from src.imuca.ml_features import (
    CausalFeatureBuilder, FEATURE_NAMES, OBSERVABLE_INPUT_COLUMNS, build_signal_dataset,
    causal_features, integrity_rule_flags, INTEGRITY_FAULT_TYPES,
)
from src.imuca.ml_fault_detection import GBTDetector, IsolationForestDetector, class_balanced_weights
from src.imuca.detection_metrics import (
    binary_metrics, event_detection, summarize_events, operating_context, false_alarms_by_context,
    threshold_at_false_alarm_rate,
)
from src.imuca.cusum_tuning import siegmund_arl_two_sided, run_cusum
from src.imuca.validation import analyze_temporal_drift

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FD = os.path.join(ROOT, "data", "synthetic", "fault_detection")
META = os.path.join(ROOT, "data", "synthetic", "metadata")


def _load(sid):
    df = pd.read_csv(os.path.join(FD, f"{sid}.csv"))
    with open(os.path.join(META, f"{sid}.metadata.json"), "r", encoding="utf-8") as f:
        return df, json.load(f)


@pytest.fixture(scope="module")
def volt_frames():
    return {sid: _load(sid)[0] for sid in ("FD_VOLT_NONE", "FD_VOLT_ISOLATED_SPIKE", "FD_VOLT_OFFSET_SHIFT", "FD_VOLT_DUPLICATE_SEQUENCE")}


@pytest.fixture(scope="module")
def builder(volt_frames):
    cal = pd.concat([df[df.partition == "calibration"] for df in volt_frames.values()], ignore_index=True)
    return CausalFeatureBuilder("voltage_V").fit(cal)


@pytest.fixture(scope="module")
def dataset(volt_frames, builder):
    return build_signal_dataset(volt_frames, "voltage_V", builder)


# ==============================================================================
# Causal features
# ==============================================================================

def test_features_do_not_depend_on_future_samples():
    rng = np.random.default_rng(1)
    x = 5.0 + rng.normal(0, 0.002, 800)
    base = causal_features(x, floor=1e-4)
    for t in (50, 299, 600):
        y = x.copy()
        y[t + 1:] += rng.normal(0, 5.0, len(y) - t - 1)  # violent change strictly after t
        alt = causal_features(y, floor=1e-4)
        pd.testing.assert_frame_equal(base.iloc[: t + 1], alt.iloc[: t + 1])
        assert not base.iloc[t + 1:].equals(alt.iloc[t + 1:])


def test_features_ignore_truth_reference_labels_and_protocol(volt_frames, builder):
    run = volt_frames["FD_VOLT_ISOLATED_SPIKE"].query("run_id == 'TST01'").reset_index(drop=True)
    f1, flags1, _ = builder.transform_run(run)
    poisoned = run.copy()
    for c in run.columns:
        if c.startswith(("true_", "reference_", "label_", "error_")) or c in (
                "is_injected_fault", "setpoint_index", "operating_condition_id", "protocol_phase", "partition", "dq_flags"):
            poisoned[c] = 1e6 if pd.api.types.is_numeric_dtype(run[c]) else "POISON"
    f2, flags2, _ = builder.transform_run(poisoned)
    pd.testing.assert_frame_equal(f1, f2)
    assert np.array_equal(flags1, flags2)


def test_feature_inputs_are_observable_roles_only():
    _, meta = _load("FD_VOLT_NONE")
    roles = {c["name"]: c["role"] for c in meta["columns"]}
    for c in OBSERVABLE_INPUT_COLUMNS:
        assert roles[c] in ("observation", "time", "identifier"), c
    assert roles["voltage_V"] == "observation"
    assert all(n.startswith("f_") for n in FEATURE_NAMES) and len(FEATURE_NAMES) == len(set(FEATURE_NAMES))


def test_integrity_rules_are_causal_and_exact(volt_frames):
    run = volt_frames["FD_VOLT_DUPLICATE_SEQUENCE"].query("run_id == 'TST01'").reset_index(drop=True)
    flags, _ = integrity_rule_flags(run, "voltage_V")
    assert np.array_equal(flags, run["is_injected_fault"].to_numpy())
    cut = 300
    flags_prefix, _ = integrity_rule_flags(run.iloc[:cut], "voltage_V")
    assert np.array_equal(flags_prefix, flags[:cut])


# ==============================================================================
# Leakage and split integrity
# ==============================================================================

def test_fitting_rejects_non_calibration_data(volt_frames, dataset):
    sig, _ = dataset
    with pytest.raises(ValueError):
        CausalFeatureBuilder("voltage_V").fit(volt_frames["FD_VOLT_NONE"])
    with pytest.raises(ValueError):
        GBTDetector(params={"max_iter": 5}, seed=0).fit(sig)
    with pytest.raises(ValueError):
        IsolationForestDetector(params={"n_estimators": 5}, seed=0).fit(sig[sig.partition == "validation"])


def test_split_integrity_and_feature_matrix(dataset):
    sig, integ = dataset
    ids = {p: set(sig.loc[sig.partition == p, "experiment_id"]) for p in ("calibration", "validation", "test")}
    assert all(ids.values())
    assert not (ids["calibration"] & ids["validation"]) and not (ids["calibration"] & ids["test"]) and not (ids["validation"] & ids["test"])
    assert set(FEATURE_NAMES) <= set(sig.columns)
    forbidden = [c for c in FEATURE_NAMES if c.startswith(("true_", "reference_", "label_", "error_"))]
    assert forbidden == []
    # integrity-flagged records never enter the signal track
    assert len(sig) == int((~integ["integrity_rule_flag"]).sum())
    assert not sig["label_fault_type"].str.contains("|".join(INTEGRITY_FAULT_TYPES)).any()


def test_class_balanced_weights():
    t = pd.Series(["none"] * 90 + ["isolated_spike"] * 2 + ["offset_shift"] * 8)
    w = class_balanced_weights(t)
    assert np.isclose(w[t == "isolated_spike"].sum(), w[t == "offset_shift"].sum())
    assert np.isclose(w[t == "none"].sum(), w[t != "none"].sum())


# ==============================================================================
# Reproducibility
# ==============================================================================

def test_training_is_reproducible(dataset):
    sig, _ = dataset
    train = sig[sig.partition == "calibration"]
    val = sig[sig.partition == "validation"]
    params = {"max_depth": 3, "learning_rate": 0.1, "max_iter": 40, "l2_regularization": 1.0}
    a = GBTDetector(params=params, seed=7).fit(train).score(val)
    b = GBTDetector(params=params, seed=7).fit(train).score(val)
    assert np.array_equal(a, b)
    ip = {"n_estimators": 50, "max_samples": 256, "max_features": 1.0}
    c = IsolationForestDetector(params=ip, seed=7).fit(train).score(val)
    d = IsolationForestDetector(params=ip, seed=7).fit(train).score(val)
    assert np.array_equal(c, d)


def test_isolation_forest_trains_on_fault_free_records_only(dataset):
    sig, _ = dataset
    train = sig[sig.partition == "calibration"]
    det = IsolationForestDetector(params={"n_estimators": 20, "max_samples": 128, "max_features": 1.0}, seed=0).fit(train)
    assert det.training_records == int((~train["is_signal_fault"]).sum())


# ==============================================================================
# Metric calculations
# ==============================================================================

def test_binary_metrics_hand_example():
    truth = np.array([1, 1, 1, 1, 0, 0, 0, 0, 0, 0], bool)
    pred = np.array([1, 1, 1, 0, 1, 0, 0, 0, 0, 0], bool)
    m = binary_metrics(pred, truth)
    assert (m["TP"], m["FP"], m["TN"], m["FN"]) == (3, 1, 5, 1)
    assert m["precision"] == pytest.approx(0.75) and m["recall"] == pytest.approx(0.75)
    assert m["f1"] == pytest.approx(0.75)
    assert m["false_alarm_rate"] == pytest.approx(1 / 6) and m["missed_detection_rate"] == pytest.approx(0.25)
    none = binary_metrics(np.zeros(4, bool), np.zeros(4, bool))
    assert none["precision"] is None and none["recall"] is None and none["false_alarm_rate"] == 0.0


def test_threshold_at_false_alarm_rate():
    scores = np.r_[np.arange(1000) / 1000.0, [5.0, 6.0]]
    truth = np.r_[np.zeros(1000, bool), [True, True]]
    thr = threshold_at_false_alarm_rate(scores, truth, 0.01)
    fa = np.mean(scores[~truth] > thr)
    assert fa <= 0.01 and fa >= 0.009
    assert np.all(scores[truth] > thr)


def _event_frame():
    n = 40
    return pd.DataFrame({
        "experiment_id": ["R1"] * n, "sequence_number": np.arange(1, n + 1),
        "label_fault_event_id": ["none"] * 10 + ["E1"] * 5 + ["none"] * 25,
        "protocol_phase": ["steady"] * 20 + ["ramp"] * 5 + ["steady"] * 15,
        "label_process_event": ["none"] * 30 + ["setpoint_change"] + ["none"] * 9,
        "is_signal_fault": [False] * 10 + [True] * 5 + [False] * 25,
    })


def test_event_detection_delay_window_and_chance():
    df = _event_frame()
    events = [{"event_id": "E1", "fault_type": "abrupt_change", "run_id": "R1", "onset_sequence_number": 11},
              {"event_id": "E2", "fault_type": "offset_shift", "run_id": "R1", "onset_sequence_number": 21}]
    pred = np.zeros(len(df), bool)
    pred[12] = True       # seq 13: inside E1, delay 2
    pred[35] = True       # seq 36: after the 10-sample persistent window of E2 -> not a detection
    ev = event_detection(pred, df, events, persistent_types=["offset_shift"], persistent_window=10, false_alarm_rate=0.01)
    e1 = next(e for e in ev if e["event_id"] == "E1")
    e2 = next(e for e in ev if e["event_id"] == "E2")
    assert e1["detected"] and e1["delay_samples"] == 2 and e1["window_samples"] == 5
    assert not e2["detected"] and e2["window_samples"] == 10
    assert e2["chance_detection_probability"] == pytest.approx(1 - 0.99 ** 10)
    s = summarize_events(ev)
    assert s["abrupt_change"]["event_recall"] == 1.0 and s["offset_shift"]["event_recall"] == 0.0


def test_operating_context_and_false_alarm_split():
    df = _event_frame()
    ctx = operating_context(df, transient_samples=4, aftermath_samples=3)
    assert list(ctx[15:18]) == ["post_fault_aftermath"] * 3          # seq 16-18 follow the fault
    assert list(ctx[20:25]) == ["ramp"] * 5
    assert list(ctx[25:29]) == ["post_event_transient"] * 4          # after the ramp ends
    assert list(ctx[30:34]) == ["post_event_transient"] * 4          # after the set-point change
    assert ctx[29] == "steady" and ctx[0] == "steady"
    pred = np.zeros(len(df), bool); pred[[0, 21, 26]] = True
    fa = false_alarms_by_context(pred, df["is_signal_fault"].to_numpy(), ctx)
    assert fa["steady"]["false_alarms"] == 1 and fa["ramp"]["false_alarms"] == 1 and fa["post_event_transient"]["false_alarms"] == 1


# ==============================================================================
# CUSUM behaviour
# ==============================================================================

def test_cusum_defaults_unchanged():
    rng = np.random.default_rng(3)
    t = np.arange(600, dtype=float)
    y = 0.01 * rng.normal(size=600) + 1e-5 * t
    a = analyze_temporal_drift(t, y, nominal_target=0.0)
    b = analyze_temporal_drift(t, y, nominal_target=0.0, cusum_k_sigma=0.5, cusum_h_sigma=4.0, cusum_sigma=None)
    assert a == b


def test_siegmund_arl_reference_values():
    assert siegmund_arl_two_sided(0.5, 4.0) == pytest.approx(169, abs=2)
    assert siegmund_arl_two_sided(0.5, 4.77) == pytest.approx(370, rel=0.02)   # classic textbook design point
    assert siegmund_arl_two_sided(0.5, 15.0) > siegmund_arl_two_sided(0.5, 10.0) > siegmund_arl_two_sided(0.5, 5.0)
    assert siegmund_arl_two_sided(0.5, 10.0, mu=0.3) < siegmund_arl_two_sided(0.5, 10.0) / 10


def test_existing_cusum_false_alarms_on_long_in_control_series():
    """Root cause: k=0.5, h=4 (ARL0 ~ 169) almost surely alarms on 1800 in-control samples."""
    rng = np.random.default_rng(11)
    alarms = 0
    for _ in range(10):
        e = rng.normal(size=1800)
        alarms += run_cusum(np.arange(1800.0), e, 0.5, 4.0, sigma_mode="baseline_window")["alarm"]
    assert alarms >= 9


def test_tuned_cusum_quiet_in_control_and_detects_shift():
    rng = np.random.default_rng(5)
    quiet = sum(run_cusum(np.arange(1800.0), rng.normal(size=1800), 0.5, 15.0)["alarm"] for _ in range(10))
    assert quiet == 0
    e = rng.normal(size=1800)
    e[1000:] += 2.0
    o = run_cusum(np.arange(1800.0), e, 0.5, 15.0, onset_s=1000.0)
    assert o["alarm"] and not o["alarm_before_onset"]
    assert 0 <= o["delay_s"] <= 30  # Siegmund ARL1 for a 2-sigma shift is ~11 samples


def test_cusum_baseline_window_is_causal():
    rng = np.random.default_rng(9)
    e = rng.normal(size=1000)
    a = run_cusum(np.arange(1000.0), e, 0.5, 15.0)
    e2 = e.copy(); e2[500:] += 0.01  # change after the baseline window
    b = run_cusum(np.arange(1000.0), e2, 0.5, 15.0)
    assert a["sigma_used"] == b["sigma_used"] and a["target"] == b["target"]
