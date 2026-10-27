"""
IMUCA hybrid-detector evaluation helpers (Milestone 6).

Event-level and sample-level scoring of alarm streams on integrity-clean records, with
fault-classification accuracy, alarm-lifecycle statistics (alarm records that persist after
the fault has ended), stratified recall (noise level, operating variant, fault magnitude)
and uncertainty intervals (Wilson, exact Poisson, run-level bootstrap).
"""

from __future__ import annotations
from typing import Any, Callable, Dict, Iterable, List, Optional

import numpy as np
import pandas as pd

from src.imuca.detection_metrics import (alarm_episodes, binary_metrics, bootstrap_by_run, classify_episodes,
                                         detect_with_windows, event_windows, fault_active_mask, operating_context,
                                         poisson_rate_interval, wilson_interval, CONTEXTS)
from src.imuca.hybrid_detector import FAULT_CATEGORY
from src.imuca.ml_features import signal_fault_type

PERSISTENT_WINDOW_TYPES = ("offset_shift", "gain_change")
RUN_END_TYPES = ("gradual_drift",)
TRANSIENT_CLASSES = ("isolated_spike", "abrupt_change")
PERSISTENT_STUCK_CLASSES = ("offset_shift", "gain_change", "stuck_signal")


class EvalSet:
    """Integrity-clean records of one partition (runs concatenated) with precomputed event windows."""

    def __init__(self, comps: List[Dict[str, Any]], events: List[Dict[str, Any]], cfg: Dict[str, Any], measurand: str,
                 event_info: Optional[Dict[str, Dict[str, Any]]] = None):
        frames, self.slices, pos = [], [], 0
        for c in comps:
            run = c["run"]
            ev = run.loc[c["clean_index"], ["scenario_id", "experiment_id", "partition", "sequence_number", "elapsed_ms",
                                            "protocol_phase", "setpoint_index", "label_fault_type", "label_fault_event_id",
                                            "label_process_event"]].reset_index(drop=True)
            frames.append(ev)
            self.slices.append(slice(pos, pos + len(ev)))
            pos += len(ev)
        self.df = pd.concat(frames, ignore_index=True)
        self.df["signal_fault_type"] = [signal_fault_type(s) for s in self.df["label_fault_type"]]
        self.df["is_signal_fault"] = self.df["signal_fault_type"] != "none"
        self.truth = self.df["is_signal_fault"].to_numpy()
        self.seq = self.df["sequence_number"].to_numpy()
        self.exp = self.df["experiment_id"].to_numpy()
        present = set(self.exp)
        self.events = [e for e in events if e["run_id"] in present]
        self.event_info = event_info or {}
        self.windows = event_windows(self.df, self.events, PERSISTENT_WINDOW_TYPES, cfg["persistent_event_window_samples"],
                                     cfg["transient_tolerance_samples"], RUN_END_TYPES)
        self.late_windows = event_windows(self.df, self.events, (), 0, cfg["transient_tolerance_samples"],
                                          RUN_END_TYPES + PERSISTENT_WINDOW_TYPES)
        self.active = fault_active_mask(self.df, cfg["true_alarm_tolerance_samples"])
        self.context = operating_context(self.df, cfg["post_event_transient_samples"][measurand], cfg["post_fault_aftermath_samples"])
        self.hours = len(self.df) / 3600.0
        self.gap = cfg["episode_gap_samples"]
        self.cfg = cfg


def _macro(det: List[Dict[str, Any]], classes: Optional[Iterable[str]] = None) -> float:
    by: Dict[str, List[int]] = {}
    for d in det:
        if classes is not None and d["fault_type"] not in classes:
            continue
        b = by.setdefault(d["fault_type"], [0, 0])
        b[0] += d["detected"]; b[1] += 1
    return float(np.mean([v[0] / v[1] for v in by.values()])) if by else 0.0


def quick_score(alarm: np.ndarray, E: EvalSet, classes: Optional[Iterable[str]] = None) -> Dict[str, float]:
    """Event F1 (macro timely recall over `classes` x episode precision) and false alarms per hour."""
    det = detect_with_windows(alarm, E.windows, E.seq)
    macro = _macro(det, classes)
    eps = alarm_episodes(alarm, E.exp, E.gap)
    true = classify_episodes(eps, E.active)
    prec = (sum(true) / len(eps)) if eps else 0.0
    fa_h = (len(eps) - sum(true)) / E.hours
    f1 = 2 * prec * macro / (prec + macro) if prec + macro > 0 else 0.0
    return {"event_f1": f1, "macro_event_recall": macro, "episode_precision": prec, "false_alarms_per_hour": fa_h,
            "episodes": len(eps)}


def classification_accuracy(alarm: np.ndarray, category: np.ndarray, E: EvalSet) -> Dict[str, Any]:
    """Share of detected events whose first in-window alarm carries the fault's category."""
    det = detect_with_windows(alarm, E.windows, E.seq)
    per, ok_all, n_all = {}, 0, 0
    for d in det:
        if not d["detected"]:
            continue
        ok = category[d["first_alarm_position"]] == FAULT_CATEGORY[d["fault_type"]]
        p = per.setdefault(d["fault_type"], [0, 0])
        p[0] += int(ok); p[1] += 1
        ok_all += int(ok); n_all += 1
    return {"accuracy": ok_all / n_all if n_all else None, "accuracy_ci95": wilson_interval(ok_all, n_all),
            "correct": ok_all, "detected": n_all,
            "per_class": {t: {"correct": v[0], "detected": v[1], "accuracy": v[0] / v[1]} for t, v in sorted(per.items())}}


def lifecycle_stats(alarm: np.ndarray, E: EvalSet) -> Dict[str, Any]:
    """Alarm records that persist after the fault-active period inside true episodes (overhang)."""
    eps = alarm_episodes(alarm, E.exp, E.gap)
    true = classify_episodes(eps, E.active)
    overhang, durations = [], []
    for e, t in zip(eps, true):
        sl = np.arange(e["start"], e["end"] + 1)
        durations.append(len(sl))
        if t:
            last_active = sl[E.active[sl]].max() if E.active[sl].any() else e["start"]
            overhang.append(int(np.sum(sl > last_active)))
    return {"episodes": len(eps), "median_episode_samples": float(np.median(durations)) if durations else None,
            "true_episode_overhang_samples_total": int(np.sum(overhang)) if overhang else 0,
            "true_episode_overhang_samples_median": float(np.median(overhang)) if overhang else None,
            "true_episodes_with_overhang_over_60": int(np.sum(np.array(overhang) > 60)) if overhang else 0,
            "alarm_records_after_fault_end_per_hour": float(np.sum(overhang) / E.hours) if overhang else 0.0}


def stratified_recall(alarm: np.ndarray, E: EvalSet, keys: Iterable[str] = ("noise_group", "variant", "magnitude_bin")) -> Dict[str, Any]:
    det = detect_with_windows(alarm, E.windows, E.seq)
    out: Dict[str, Any] = {}
    for key in keys:
        groups: Dict[str, List[int]] = {}
        for d in det:
            g = E.event_info.get(d["event_id"], {}).get(key)
            if g is None:
                continue
            b = groups.setdefault(str(g), [0, 0])
            b[0] += d["detected"]; b[1] += 1
        out[key] = {g: {"detected": v[0], "events": v[1], "recall": v[0] / v[1], "recall_ci95": wilson_interval(v[0], v[1])}
                    for g, v in sorted(groups.items())}
    return out


def full_eval(alarm: np.ndarray, E: EvalSet, category: Optional[np.ndarray] = None, n_boot: int = 2000, seed: int = 0) -> Dict[str, Any]:
    alarm = np.asarray(alarm, bool)
    sample = binary_metrics(alarm, E.truth)
    far = sample["false_alarm_rate"]
    det = detect_with_windows(alarm, E.windows, E.seq, far)
    late = {d["event_id"]: d["detected"] for d in detect_with_windows(alarm, E.late_windows, E.seq)}
    classes: Dict[str, Dict[str, Any]] = {}
    for d in det:
        c = classes.setdefault(d["fault_type"], {"events": 0, "detected": 0, "delays": [], "chance": [], "eventually": 0, "missed_ids": []})
        c["events"] += 1
        c["detected"] += int(d["detected"])
        c["eventually"] += int(late.get(d["event_id"], False))
        c["chance"].append(d["chance_detection_probability"] or 0.0)
        if d["detected"]:
            c["delays"].append(d["delay_samples"])
        else:
            c["missed_ids"].append(d["event_id"])
    per_class = {}
    for t, c in sorted(classes.items()):
        per_class[t] = {"events": c["events"], "detected": c["detected"], "recall": c["detected"] / c["events"],
                        "recall_ci95": wilson_interval(c["detected"], c["events"]), "missed": c["events"] - c["detected"],
                        "eventually_detected": c["eventually"],
                        "median_delay_samples": float(np.median(c["delays"])) if c["delays"] else None,
                        "p90_delay_samples": float(np.percentile(c["delays"], 90)) if c["delays"] else None,
                        "mean_chance_detection_probability": float(np.mean(c["chance"])), "missed_event_ids": c["missed_ids"]}
    eps = alarm_episodes(alarm, E.exp, E.gap)
    true = classify_episodes(eps, E.active)
    n_true, n_ep = sum(true), len(eps)
    fa = n_ep - n_true
    macro = float(np.mean([v["recall"] for v in per_class.values()])) if per_class else None
    prec = n_true / n_ep if n_ep else None
    f1 = (2 * prec * macro / (prec + macro)) if (prec and macro) else 0.0
    all_delays = [d["delay_samples"] for d in det if d["detected"] and d["fault_type"] not in RUN_END_TYPES]

    rows = []
    det_by_run: Dict[Any, List] = {}
    for d in det:
        det_by_run.setdefault(d["run_id"], []).append(d)
    ep_by_run: Dict[Any, List] = {}
    for e, t in zip(eps, true):
        ep_by_run.setdefault(e["run"], []).append(t)
    for r in pd.unique(E.exp):
        row = {"run": r, "hours": float(np.sum(E.exp == r)) / 3600.0,
               "eps_true": sum(ep_by_run.get(r, [])), "eps_false": len(ep_by_run.get(r, [])) - sum(ep_by_run.get(r, []))}
        for t in per_class:
            dd = [x for x in det_by_run.get(r, []) if x["fault_type"] == t]
            row[f"{t}__n"] = len(dd)
            row[f"{t}__d"] = sum(x["detected"] for x in dd)
        rows.append(row)
    pr = pd.DataFrame(rows)
    classes_list = list(per_class)

    def f1_stat(tab):
        recs = [tab[f"{c}__d"].sum() / tab[f"{c}__n"].sum() for c in classes_list if tab[f"{c}__n"].sum() > 0]
        ne = tab["eps_true"].sum() + tab["eps_false"].sum()
        if not recs or ne == 0:
            return None
        p, r = tab["eps_true"].sum() / ne, float(np.mean(recs))
        return 2 * p * r / (p + r) if p + r > 0 else 0.0

    def fa_stat(tab):
        return tab["eps_false"].sum() / tab["hours"].sum()

    ctx = {}
    neg = ~E.truth
    for c in CONTEXTS:
        expo = float(np.sum(neg & (E.context == c))) / 3600.0
        n_fa = sum(1 for e, t in zip(eps, true) if not t and E.context[e["start"]] == c)
        ctx[c] = {"exposure_hours": expo, "false_alarm_episodes": n_fa,
                  "per_hour": n_fa / expo if expo > 0 else None, "per_hour_ci95": poisson_rate_interval(n_fa, expo)}
    settle = (E.df["protocol_phase"] == "plateau_settling").to_numpy() & neg
    expo_s = settle.sum() / 3600.0
    n_s = sum(1 for e, t in zip(eps, true) if not t and settle[e["start"]])
    ctx["protocol_plateau_settling"] = {"exposure_hours": expo_s, "false_alarm_episodes": n_s,
                                        "per_hour": n_s / expo_s if expo_s > 0 else None, "per_hour_ci95": poisson_rate_interval(n_s, expo_s)}
    out = {
        "sample": sample,
        "event": {"macro_recall": macro, "episodes": n_ep, "true_episodes": n_true, "false_alarm_episodes": fa,
                  "episode_precision": prec, "episode_precision_ci95": wilson_interval(n_true, n_ep),
                  "event_f1": f1, "event_f1_ci95_run_bootstrap": bootstrap_by_run(pr, f1_stat, n_boot, seed),
                  "false_alarms_per_hour": fa / E.hours, "false_alarms_per_hour_ci95": poisson_rate_interval(fa, E.hours),
                  "false_alarms_per_hour_ci95_run_bootstrap": bootstrap_by_run(pr, fa_stat, n_boot, seed),
                  "hours": E.hours, "events": len(det), "detected": sum(d["detected"] for d in det),
                  "missed_events": sum(not d["detected"] for d in det),
                  "median_delay_samples_non_drift": float(np.median(all_delays)) if all_delays else None,
                  "p90_delay_samples_non_drift": float(np.percentile(all_delays, 90)) if all_delays else None},
        "per_class": per_class, "false_alarms_by_context": ctx,
        "lifecycle": lifecycle_stats(alarm, E),
        "strata": stratified_recall(alarm, E),
    }
    if category is not None:
        out["classification"] = classification_accuracy(alarm, category, E)
    return out


def event_strata(meta: Dict[str, Any], devices: Dict[str, Dict[str, Any]], noise_rank: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
    """Per-event stratification attributes (evaluation only): noise group, variant, magnitude in noise sigmas."""
    dev_id = meta["sensor_error_model"]["device_id"]
    dev = devices[dev_id]
    sigma = dev.get("noise_std", dev.get("adc_noise_std_mV", 0.0) / dev.get("r_shunt_nominal_ohm", 1.0))
    variant = meta["dataset_id"].split("_")[1] if meta["dataset_id"].startswith(("FD3_", "FD4_")) else meta["dataset_id"]
    out = {}
    for e in meta["fault_events"]:
        info = {"noise_group": noise_rank.get(dev_id, "n/a"), "variant": variant, "device_id": dev_id}
        if e["fault_type"] in ("isolated_spike", "offset_shift", "abrupt_change") and e.get("magnitude") is not None and sigma:
            ms = abs(e["magnitude"]) / sigma
            info["magnitude_bin"] = "<10 sigma" if ms < 10 else ("10-30 sigma" if ms < 30 else ">=30 sigma")
        out[e["event_id"]] = info
    return out
