"""
Workstream 4 tests: event-level detection, fault classification, alarm overhang (clearance),
detection delay, false alarms per hour, confidence intervals, stratified performance, and the
evaluate-once / frozen-code guards of the final evaluation stage.
"""

import importlib.util
import json
import os

import numpy as np
import pandas as pd
import pytest

from src.imuca.hybrid_evaluation import (EvalSet, classification_accuracy, full_eval, lifecycle_stats, quick_score,
                                         stratified_recall, event_strata)
from src.imuca.cusum_tuning import cusum_max_statistic, first_crossings, run_cusum

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = {"persistent_event_window_samples": 10, "transient_tolerance_samples": 2, "true_alarm_tolerance_samples": 2,
       "post_event_transient_samples": {"voltage_V": 5}, "post_fault_aftermath_samples": 5, "episode_gap_samples": 2}


def _run(exp, n, faults, process=()):
    """Synthetic clean run: faults = list of (event_id, type, start_seq, end_seq)."""
    lab = ["none"] * n
    ids = ["none"] * n
    for eid, ft, a, b in faults:
        for s in range(a, b + 1):
            lab[s - 1] = ft if lab[s - 1] == "none" else lab[s - 1] + ";" + ft
            ids[s - 1] = eid if ids[s - 1] == "none" else ids[s - 1] + ";" + eid
    pe = ["none"] * n
    for s in process:
        pe[s - 1] = "setpoint_change"
    run = pd.DataFrame({"scenario_id": "S", "experiment_id": exp, "partition": "test", "sequence_number": np.arange(1, n + 1),
                        "elapsed_ms": np.arange(n) * 1000.0, "protocol_phase": "steady", "setpoint_index": 0,
                        "label_fault_type": lab, "label_fault_event_id": ids, "label_process_event": pe})
    return {"run": run, "clean_index": np.arange(n)}


def _eset():
    comps = [_run("R1", 3600, [("E1", "isolated_spike", 100, 100), ("E2", "offset_shift", 1000, 3600)]),
             _run("R2", 3600, [("E3", "abrupt_change", 500, 520), ("E4", "gradual_drift", 2000, 3600)])]
    events = [{"event_id": "E1", "fault_type": "isolated_spike", "run_id": "R1", "onset_sequence_number": 100, "magnitude": 0.05},
              {"event_id": "E2", "fault_type": "offset_shift", "run_id": "R1", "onset_sequence_number": 1000, "magnitude": 0.002},
              {"event_id": "E3", "fault_type": "abrupt_change", "run_id": "R2", "onset_sequence_number": 500, "magnitude": 0.03},
              {"event_id": "E4", "fault_type": "gradual_drift", "run_id": "R2", "onset_sequence_number": 2000, "magnitude": 1e-5}]
    info = {"E1": {"noise_group": "noise_low", "variant": "VA", "magnitude_bin": ">=30 sigma"},
            "E2": {"noise_group": "noise_low", "variant": "VA", "magnitude_bin": "<10 sigma"},
            "E3": {"noise_group": "noise_high", "variant": "VC", "magnitude_bin": "10-30 sigma"},
            "E4": {"noise_group": "noise_high", "variant": "VC"}}
    return EvalSet(comps, events, CFG, "voltage_V", info)


def test_event_detection_delay_and_false_alarms_per_hour():
    E = _eset()
    a = np.zeros(len(E.df), bool)
    a[100] = True                        # E1 detected 1 sample late (tolerance 2)
    a[1003:1006] = True                  # E2 detected at seq 1004 -> delay 4
    a[3600 + 2100] = True                # E4 detected at seq 2101 -> delay 101
    a[3600 + 3000:3600 + 3003] = True    # inside the drift -> true episode, not a false alarm
    a[2500] = True                       # inside the offset fault (fault-active) -> true
    a[3600 + 1500] = True                # clean region -> false alarm
    r = full_eval(a, E, n_boot=100)
    pc = r["per_class"]
    assert pc["isolated_spike"]["detected"] == 1 and pc["isolated_spike"]["median_delay_samples"] == 1
    assert pc["offset_shift"]["median_delay_samples"] == 4
    assert pc["abrupt_change"]["detected"] == 0 and pc["abrupt_change"]["missed_event_ids"] == ["E3"]
    assert pc["gradual_drift"]["median_delay_samples"] == 101
    ev = r["event"]
    assert ev["false_alarm_episodes"] == 1 and ev["episodes"] == 6
    assert ev["false_alarms_per_hour"] == pytest.approx(1 / 2.0)          # 2 h of records
    lo, hi = ev["false_alarms_per_hour_ci95"]
    assert lo < 0.5 < hi
    assert ev["missed_events"] == 1 and ev["macro_recall"] == pytest.approx(0.75)
    assert ev["median_delay_samples_non_drift"] == 2.5


def test_classification_accuracy_counts_category_at_first_alarm():
    E = _eset()
    a = np.zeros(len(E.df), bool); a[99] = True; a[1000] = True; a[3600 + 499] = True
    cat = np.array(["none"] * len(E.df), dtype=object)
    cat[99] = "transient"; cat[1000] = "transient"; cat[3600 + 499] = "transient"
    c = classification_accuracy(a, cat, E)
    assert c["detected"] == 3 and c["correct"] == 2                      # the offset was labelled 'transient'
    assert c["per_class"]["offset_shift"]["accuracy"] == 0.0
    lo, hi = c["accuracy_ci95"]
    assert lo < 2 / 3 < hi


def test_alarm_overhang_after_fault_end_is_measured():
    E = _eset()
    a = np.zeros(len(E.df), bool)
    a[3600 + 499:3600 + 600] = True      # abrupt change ends at seq 520 (+2 tolerance) -> 78 overhang records
    st = lifecycle_stats(a, E)
    assert st["true_episode_overhang_samples_total"] == 600 - 522
    assert st["true_episodes_with_overhang_over_60"] == 1
    b = np.zeros(len(E.df), bool); b[3600 + 499:3600 + 522] = True   # alarm cleared at fault end
    assert lifecycle_stats(b, E)["true_episode_overhang_samples_total"] == 0


def test_quick_score_matches_full_eval_and_class_restriction():
    E = _eset()
    a = np.zeros(len(E.df), bool); a[100] = True; a[3600 + 505] = True; a[3600 + 1500] = True
    q, f = quick_score(a, E), full_eval(a, E, n_boot=50)
    assert q["event_f1"] == pytest.approx(f["event"]["event_f1"])
    assert q["false_alarms_per_hour"] == pytest.approx(f["event"]["false_alarms_per_hour"])
    qt = quick_score(a, E, ("isolated_spike", "abrupt_change"))
    assert qt["macro_event_recall"] == 1.0


def test_stratified_recall_by_noise_variant_and_magnitude():
    E = _eset()
    a = np.zeros(len(E.df), bool); a[100] = True; a[3600 + 2000] = True
    s = stratified_recall(a, E)
    assert s["noise_group"]["noise_low"] == {"detected": 1, "events": 2, "recall": 0.5, "recall_ci95": s["noise_group"]["noise_low"]["recall_ci95"]}
    assert s["noise_group"]["noise_high"]["detected"] == 1
    assert s["variant"]["VA"]["events"] == 2 and s["variant"]["VC"]["events"] == 2
    assert set(s["magnitude_bin"]) == {">=30 sigma", "<10 sigma", "10-30 sigma"}   # drift has no magnitude bin


def test_bootstrap_interval_contains_point_estimate():
    E = _eset()
    a = np.zeros(len(E.df), bool); a[100] = True; a[1001] = True; a[3600 + 505] = True; a[3600 + 2050] = True
    r = full_eval(a, E, n_boot=300, seed=1)
    lo, hi = r["event"]["event_f1_ci95_run_bootstrap"]
    assert lo <= r["event"]["event_f1"] <= hi


def test_event_strata_uses_device_noise_for_magnitude_bins():
    meta = {"dataset_id": "FD4_VA_MIXED", "sensor_error_model": {"device_id": "D1"},
            "fault_events": [{"event_id": "a", "fault_type": "isolated_spike", "magnitude": -0.005},
                             {"event_id": "b", "fault_type": "isolated_spike", "magnitude": 0.05},
                             {"event_id": "c", "fault_type": "gain_change", "magnitude": 0.004}]}
    s = event_strata(meta, {"D1": {"noise_std": 0.001}}, {"D1": "noise_low"})
    assert s["a"]["magnitude_bin"] == "<10 sigma" and s["b"]["magnitude_bin"] == ">=30 sigma"
    assert "magnitude_bin" not in s["c"] and s["c"]["variant"] == "VA" and s["c"]["noise_group"] == "noise_low"


def test_fast_cusum_equals_existing_detector():
    rng = np.random.default_rng(3)
    for _ in range(50):
        n = int(rng.integers(100, 600))
        e = rng.normal(size=n); e[n // 2:] += 0.02 * np.arange(n - n // 2)
        o = run_cusum(np.arange(float(n)), e, 0.5, 8.0)
        fc = first_crossings(cusum_max_statistic(e, o["target"], o["sigma_used"], 0.5), [8.0])[8.0]
        assert (fc is None and not o["alarm"]) or fc == int(o["alarm_time_s"])


def _iter_module():
    spec = importlib.util.spec_from_file_location("it", os.path.join(ROOT, "scripts", "run_hybrid_iteration.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_final_stage_guards(tmp_path):
    it = _iter_module()
    assert it.changed_code({"a.py": "1", "b.py": "2"}, {"a.py": "1", "b.py": "2"}) == []
    assert it.changed_code({"a.py": "1", "b.py": "2"}, {"a.py": "1", "b.py": "X"}) == ["b.py"]
    assert it.previous_evaluation(tmp_path, "F", "M") is None
    d = tmp_path / "hybrid_final_20990101_000000"
    d.mkdir()
    (d / "evaluation_complete.json").write_text(json.dumps({"frozen_settings_sha256": "F", "suite_manifest_sha256": "M"}))
    assert it.previous_evaluation(tmp_path, "F", "M") == d
    assert it.previous_evaluation(tmp_path, "F", "OTHER") is None


def test_posthoc_paired_f1_helper():
    spec = importlib.util.spec_from_file_location("ph", os.path.join(ROOT, "scripts", "posthoc_paired_comparison.py"))
    ph = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ph)
    tab = pd.DataFrame({"hours": [1.0, 1.0], "tp_eps": [3, 1], "fp_eps": [1, 0],
                        "isolated_spike__n": [2, 2], "isolated_spike__d": [2, 1], "offset_shift__n": [1, 0], "offset_shift__d": [0, 0]})
    p, r = 4 / 5, (3 / 4 + 0 / 1) / 2
    assert ph.f1(tab) == pytest.approx(2 * p * r / (p + r))
    E = _eset()
    a = np.zeros(len(E.df), bool); a[100] = True; a[3600 + 1500] = True
    counts = ph.per_run_counts(a, E)
    assert counts.loc["R1", "tp_eps"] == 1 and counts.loc["R2", "fp_eps"] == 1
    assert ph.f1(counts) == pytest.approx(quick_score(a, E)["event_f1"])
