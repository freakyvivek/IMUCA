#!/usr/bin/env python3
"""
IMUCA Hybrid Fault Detector experiment on the fresh v3 synthetic suite (synthetic data only).

Protocol
  1. Train on v3 calibration runs (feature floor, GBT models, Isolation Forest).
  2. Tune CUSUM on calibration+validation runs; choose GBT thresholds, GBT settings,
     segment mode and stuck mode on validation runs only.
  3. Write the frozen settings (frozen_settings.json, SHA-256 recorded) BEFORE any test
     record is processed.
  4. Score the v3 test runs once with every detector.

Detectors compared: integrity rules (shared track), existing segment detector (set-point
blocks), Milestone-4-style GBT (all signal faults), Isolation Forest, targeted GBT
(offset/gain/stuck), stuck rule, tuned CUSUM, and the hybrid.

Outputs: results/hybrid_fault_detection_<timestamp>/ - nothing existing is modified.

Usage:
    python scripts/run_hybrid_fault_detection.py                   # full protocol (test scored once)
    python scripts/run_hybrid_fault_detection.py --selection-only  # stop after freezing; no test record is read into a detector
"""

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
import sklearn

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from src.imuca.calibration import CalibrationEngine
from src.imuca.synthetic_suite import _sha256_bytes
from src.imuca.ml_features import (CausalFeatureBuilder, build_signal_dataset, integrity_rule_flags, signal_fault_type,
                                   SIGNAL_FAULT_TYPES, INTEGRITY_FAULT_TYPES, FEATURE_NAMES)
from src.imuca.ml_fault_detection import GBTDetector, IsolationForestDetector, TargetedGBTDetector
from src.imuca.detection_metrics import (binary_metrics, threshold_at_false_alarm_rate, event_windows, detect_with_windows,
                                         alarm_episodes, fault_active_mask, classify_episodes, wilson_interval,
                                         poisson_rate_interval, bootstrap_by_run, operating_context, CONTEXTS)
from src.imuca.hybrid_detector import (HybridDetector, HybridSettings, combine, drift_component, drift_usable,
                                       transition_mask, setpoint_change_positions, stuck_rule_flags, FAULT_CATEGORY, SEGMENT_MODES)
from src.imuca.cusum_tuning import siegmund_arl_two_sided

STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUT = WORKSPACE_ROOT / "results" / f"hybrid_fault_detection_{STAMP}"
DETECTORS = ("hybrid", "segment_setpoint", "gbt_all", "iforest", "gbt_persistent", "stuck_rule", "cusum")
LABEL = {"hybrid": "Hybrid", "segment_setpoint": "Segment detector (existing)", "gbt_all": "GBT (all faults)",
         "iforest": "Isolation Forest", "gbt_persistent": "Targeted GBT (offset/gain/stuck)", "stuck_rule": "Stuck rule",
         "cusum": "Tuned CUSUM"}
RUN_END_TYPES = ("gradual_drift",)


def load_json(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def jsonable(o):
    if isinstance(o, dict):
        return {str(k): jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jsonable(v) for v in o]
    if isinstance(o, (np.bool_, bool)):
        return bool(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.ndarray):
        return jsonable(o.tolist())
    return o


# ==============================================================================
# Evaluation helpers
# ==============================================================================

class EvalSet:
    """Integrity-clean records of one partition (concatenated runs) with precomputed event windows."""

    def __init__(self, comps, events, cfg, measurand):
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
        self.windows = event_windows(self.df, self.events, ("offset_shift", "gain_change"), cfg["persistent_event_window_samples"],
                                     cfg["transient_tolerance_samples"], RUN_END_TYPES)
        self.late_windows = event_windows(self.df, self.events, (), 0, cfg["transient_tolerance_samples"],
                                          RUN_END_TYPES + ("offset_shift", "gain_change"))
        self.active = fault_active_mask(self.df, cfg["true_alarm_tolerance_samples"])
        self.context = operating_context(self.df, cfg["post_event_transient_samples"][measurand], cfg["post_fault_aftermath_samples"])
        self.hours = len(self.df) / 3600.0
        self.gap = cfg["episode_gap_samples"]


def quick_score(alarm, E):
    det = detect_with_windows(alarm, E.windows, E.seq)
    by = {}
    for d in det:
        b = by.setdefault(d["fault_type"], [0, 0])
        b[0] += d["detected"]; b[1] += 1
    macro = float(np.mean([v[0] / v[1] for v in by.values()])) if by else 0.0
    eps = alarm_episodes(alarm, E.exp, E.gap)
    true = classify_episodes(eps, E.active)
    prec = (sum(true) / len(eps)) if eps else 0.0
    fa_h = (len(eps) - sum(true)) / E.hours
    f1 = 2 * prec * macro / (prec + macro) if prec + macro > 0 else 0.0
    return {"event_f1": f1, "macro_event_recall": macro, "episode_precision": prec, "false_alarms_per_hour": fa_h}


def full_eval(alarm, E, cfg, category=None):
    alarm = np.asarray(alarm, bool)
    sample = binary_metrics(alarm, E.truth)
    far = sample["false_alarm_rate"]
    det = detect_with_windows(alarm, E.windows, E.seq, far)
    late = {d["event_id"]: d["detected"] for d in detect_with_windows(alarm, E.late_windows, E.seq)}
    classes = {}
    for d in det:
        c = classes.setdefault(d["fault_type"], {"events": 0, "detected": 0, "delays": [], "chance": [], "eventually": 0,
                                                 "correct_category": 0, "missed_ids": []})
        c["events"] += 1
        c["detected"] += int(d["detected"])
        c["eventually"] += int(late.get(d["event_id"], False))
        c["chance"].append(d["chance_detection_probability"] or 0.0)
        if d["detected"]:
            c["delays"].append(d["delay_samples"])
            if category is not None and category[d["first_alarm_position"]] == FAULT_CATEGORY[d["fault_type"]]:
                c["correct_category"] += 1
        else:
            c["missed_ids"].append(d["event_id"])
    per_class = {}
    for t, c in sorted(classes.items()):
        per_class[t] = {"events": c["events"], "detected": c["detected"], "recall": c["detected"] / c["events"],
                        "recall_ci95": wilson_interval(c["detected"], c["events"]),
                        "missed": c["events"] - c["detected"], "eventually_detected": c["eventually"],
                        "median_delay_samples": float(np.median(c["delays"])) if c["delays"] else None,
                        "p90_delay_samples": float(np.percentile(c["delays"], 90)) if c["delays"] else None,
                        "mean_chance_detection_probability": float(np.mean(c["chance"])),
                        "correct_category": c["correct_category"] if category is not None else None,
                        "missed_event_ids": c["missed_ids"]}
    eps = alarm_episodes(alarm, E.exp, E.gap)
    true = classify_episodes(eps, E.active)
    n_true, n_ep = sum(true), len(eps)
    fa = n_ep - n_true
    macro = float(np.mean([v["recall"] for v in per_class.values()])) if per_class else None
    prec = n_true / n_ep if n_ep else None
    f1 = (2 * prec * macro / (prec + macro)) if (prec and macro) else 0.0

    # per-run table for bootstrap
    rows = []
    det_by_run = {}
    for d in det:
        det_by_run.setdefault(d["run_id"], []).append(d)
    ep_by_run = {}
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

    def f1_stat(t):
        recs = [t[f"{c}__d"].sum() / t[f"{c}__n"].sum() for c in classes_list if t[f"{c}__n"].sum() > 0]
        ne = t["eps_true"].sum() + t["eps_false"].sum()
        if not recs or ne == 0:
            return None
        p, r = t["eps_true"].sum() / ne, float(np.mean(recs))
        return 2 * p * r / (p + r) if p + r > 0 else 0.0

    # false alarms by context and in settling phases
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
    ff = {}
    for sid, idx in E.df.groupby("scenario_id").indices.items():
        if E.truth[idx].any():
            continue
        expo = len(idx) / 3600.0
        n_fa = sum(1 for e, t in zip(eps, true) if not t and E.df["scenario_id"].iat[e["start"]] == sid)
        grp = sid.split("_")[0] if sid.startswith(("SWEEP", "PLATEAUS")) else ("FD_NONE" if sid.endswith("_NONE") else ("FD_INTEGRITY_MIX" if sid.endswith("INTEGRITY_MIX") else sid))
        g = ff.setdefault(grp, [0, 0.0])
        g[0] += n_fa; g[1] += expo
    ff = {k: {"false_alarm_episodes": v[0], "hours": v[1], "per_hour": v[0] / v[1]} for k, v in ff.items()}
    return {
        "sample": sample,
        "event": {"macro_recall": macro, "episodes": n_ep, "true_episodes": n_true, "false_alarm_episodes": fa,
                  "episode_precision": prec, "episode_precision_ci95": wilson_interval(n_true, n_ep),
                  "event_f1": f1, "event_f1_ci95_run_bootstrap": bootstrap_by_run(pr, f1_stat, CFG["bootstrap_resamples"], CFG["random_seed"]),
                  "false_alarms_per_hour": fa / E.hours, "false_alarms_per_hour_ci95": poisson_rate_interval(fa, E.hours),
                  "hours": E.hours, "events": len(det), "detected": sum(d["detected"] for d in det),
                  "missed_events": sum(not d["detected"] for d in det)},
        "per_class": per_class, "false_alarms_by_context": ctx, "fault_free_scenarios": ff,
    }


# ==============================================================================
# Training helpers
# ==============================================================================

def select_threshold_detector(cls, grid, train, val_eval_scores, E_val, far_target):
    """Fit configs on calibration; threshold at FAR target on validation negatives; pick best by validation macro recall."""
    best, trials = None, []
    for params in grid:
        det = cls(params=params, seed=CFG["random_seed"]).fit(train)
        s = val_eval_scores(det)
        thr = threshold_at_false_alarm_rate(s, E_val.truth, far_target)
        q = quick_score(s > thr, E_val)
        trials.append({"params": params, "threshold": thr, **q})
        key = (q["macro_event_recall"], q["event_f1"])
        if best is None or key > best[0]:
            det.threshold = thr
            best = (key, det)
    return best[1], trials


def cusum_tuning(m, runs_cv, cal_models, cfg_c, windows):
    """Tune k, h of the existing CUSUM on calibration+validation runs (standalone drift detector)."""
    series = []
    for run, dev, meta in runs_cv:
        flags, _ = integrity_rule_flags(run, m)
        clean = run.loc[~flags].reset_index(drop=True)
        types = set(t for s in clean["label_fault_type"] for t in s.split(";") if t in SIGNAL_FAULT_TYPES)
        if types and types != {"gradual_drift"}:
            continue
        err = cal_models[dev].predict(clean[m].to_numpy(float)) - clean[f"reference_{m}"].to_numpy(float)
        di = {"finite": np.isfinite(err), "protocol": clean[["setpoint_index", "protocol_phase", "sequence_number"]]}
        ev = [e for e in meta["fault_events"] if e["run_id"] == run["experiment_id"].iat[0] and e["fault_type"] == "gradual_drift"]
        series.append({"t": clean["elapsed_ms"].to_numpy(float) / 1000.0, "err": err, "di": di,
                       "segment_starts": setpoint_change_positions(clean),
                       "seq": clean["sequence_number"].to_numpy(), "drift": bool(ev),
                       "onset": ev[0]["onset_sequence_number"] if ev else None, "n": int(np.isfinite(err).sum())})
    longest = max(s["n"] for s in series)
    min_arl = cfg_c["min_arl0_multiple_of_longest_series"] * longest
    grid = []
    for mode, w, k, h in [(md, w, k, h) for md in cfg_c["modes"] for w in windows for k in cfg_c["k_grid"] for h in cfg_c["h_grid"]]:
        if True:
            st = HybridSettings("setpoint_blocks", "rule", 1.0, 1e-4, k, h, cfg_c["baseline_fraction"], cfg_c["min_baseline"],
                                cfg_c["min_series"], w, cusum_mode=mode)
            fa = pre = detected = 0
            delays = []
            for s in series:
                a = drift_component(s["t"], s["err"], drift_usable(s["di"], w), [], st, s["segment_starts"])
                if not a.any():
                    continue
                first = s["seq"][np.argmax(a)]
                if not s["drift"]:
                    fa += 1
                elif first < s["onset"]:
                    pre += 1
                else:
                    detected += 1
                    delays.append(first - s["onset"])
            arl = siegmund_arl_two_sided(k, h)
            grid.append({"mode": mode, "window": w, "k": k, "h": h, "arl0": arl, "arl0_ok": arl >= min_arl, "false_alarms": fa, "pre_onset": pre,
                         "detected": detected, "median_delay": float(np.median(delays)) if delays else None})
    ok = [g for g in grid if g["arl0_ok"]] or grid
    best = sorted(ok, key=lambda g: (g["false_alarms"] + g["pre_onset"], -g["detected"],
                                     g["median_delay"] if g["median_delay"] is not None else 1e9, -g["arl0"]))[0]
    return best, grid, {"controls": sum(not s["drift"] for s in series), "drift_runs": sum(s["drift"] for s in series),
                        "longest_series": longest, "min_arl0": min_arl}


# ==============================================================================
# Plots and report
# ==============================================================================

def _style(ax, pal):
    ax.set_facecolor(pal["surface"])
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(pal["muted"])
    ax.tick_params(colors=pal["muted"], labelsize=8)
    ax.grid(axis="x", color=pal["grid"], linewidth=0.6)
    ax.set_axisbelow(True)


def plot_recall(R, path):
    pal = CFG["plot_palette"]
    show = ("hybrid", "segment_setpoint", "gbt_all", "cusum")
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.8), facecolor=pal["surface"], layout="constrained")
    for ax, m in zip(axes, CFG["measurands"]):
        classes = [c for c in SIGNAL_FAULT_TYPES if c in R[m]["test"]["hybrid"]["per_class"]]
        y = np.arange(len(classes))
        h = 0.19
        for j, d in enumerate(show):
            pc = R[m]["test"][d]["per_class"]
            vals = np.array([pc[c]["recall"] for c in classes])
            lo = np.array([pc[c]["recall_ci95"][0] for c in classes]); hi = np.array([pc[c]["recall_ci95"][1] for c in classes])
            yy = y + (j - 1.5) * (h + 0.02)
            ax.barh(yy, vals, height=h, color=pal[d], label=LABEL[d])
            ax.errorbar(vals, yy, xerr=[np.maximum(vals - lo, 0), np.maximum(hi - vals, 0)], fmt="none", ecolor=pal["muted"], elinewidth=0.8, capsize=0)
        n_ev = [R[m]["test"]["hybrid"]["per_class"][c]["events"] for c in classes]
        ax.set_yticks(y, [f"{c.replace('_', ' ')} (n={n})" for c, n in zip(classes, n_ev)], color=pal["text"], fontsize=8)
        ax.invert_yaxis(); ax.set_xlim(0, 1.0)
        ax.set_title(m, color=pal["text"], fontsize=10, loc="left")
        ax.set_xlabel("Timely event recall, 95 % Wilson interval (test runs)", color=pal["muted"], fontsize=8)
        _style(ax, pal)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="outside lower left", ncol=4, frameon=False, fontsize=8)
    fig.suptitle("Event recall by fault class: hybrid vs individual detectors (v3 synthetic test runs)", color=pal["text"], fontsize=11, x=0.01, ha="left")
    fig.savefig(path, dpi=150, facecolor=pal["surface"])
    plt.close(fig)


def plot_fa(R, path):
    pal = CFG["plot_palette"]
    show = ("hybrid", "segment_setpoint", "gbt_all", "cusum")
    ctxs = ("steady", "ramp", "post_event_transient", "protocol_plateau_settling")
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.4), facecolor=pal["surface"], layout="constrained")
    for ax, m in zip(axes, CFG["measurands"]):
        y = np.arange(len(ctxs)); h = 0.19
        for j, d in enumerate(show):
            fc = R[m]["test"][d]["false_alarms_by_context"]
            vals = np.array([fc[c]["per_hour"] or 0.0 for c in ctxs])
            lo = np.array([fc[c]["per_hour_ci95"][0] or 0.0 for c in ctxs]); hi = np.array([fc[c]["per_hour_ci95"][1] or 0.0 for c in ctxs])
            yy = y + (j - 1.5) * (h + 0.02)
            ax.barh(yy, vals, height=h, color=pal[d], label=LABEL[d])
            ax.errorbar(vals, yy, xerr=[np.maximum(vals - lo, 0), np.maximum(hi - vals, 0)], fmt="none", ecolor=pal["muted"], elinewidth=0.8)
        ax.set_yticks(y, [f"{c.replace('_', ' ')}\n({R[m]['test']['hybrid']['false_alarms_by_context'][c]['exposure_hours']:.2f} h)" for c in ctxs],
                      color=pal["text"], fontsize=8)
        ax.invert_yaxis()
        ax.set_title(m, color=pal["text"], fontsize=10, loc="left")
        ax.set_xlabel("False-alarm episodes per fault-free hour (95 % CI)", color=pal["muted"], fontsize=8)
        _style(ax, pal)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="outside lower left", ncol=4, frameon=False, fontsize=8)
    fig.suptitle("False alarms by operating context (v3 synthetic test runs)", color=pal["text"], fontsize=11, x=0.01, ha="left")
    fig.savefig(path, dpi=150, facecolor=pal["surface"])
    plt.close(fig)


def f3(x, nd=3):
    if x is None:
        return "–"
    return f"{x:.{nd}f}" if isinstance(x, (float, np.floating)) else str(x)


def ci(t, nd=2):
    return "–" if t is None or t[0] is None else f"[{t[0]:.{nd}f}, {t[1]:.{nd}f}]"


def write_report(R, path):
    info = R["run_info"]
    L = ["# IMUCA — Hybrid Fault Detector Report (v3 independent test)", "",
         "> SYNTHETIC DATA ONLY. Results describe detectors on simulated faults from `config/synthetic_suite_v3_config.json`; no real-sensor performance is claimed.", "",
         f"- Run: `{info['command']}` at {info['timestamp_utc']}",
         f"- Data: `{info['dataset_root']}` (suite `{info['suite_id']}`, manifest `{info['manifest_sha256'][:16]}…`, checksums verified); seed roots {info['seed_roots']} (v2 roots {info['v2_seed_roots']}).",
         f"- Settings frozen before test scoring: `frozen_settings.json` SHA-256 `{info['frozen_settings_sha256']}` written {info['frozen_at_utc']}; test components first computed {info['test_started_utc']}.",
         "- Episode = consecutive alarmed records (gap ≤ 2) = one operator-facing alarm. True episode = overlaps a fault-active record (+2 samples). Timely event detection: transient/stuck = event records + 2 samples; offset/gain = first 60 samples; drift = onset → end of run.",
         "- Intervals: Wilson 95 % for proportions, exact Poisson (Garwood) 95 % for false alarms per hour, run-level bootstrap 95 % for event F1.", ""]

    L += ["## 1. Overall comparison (test runs, signal track)", "",
          "| Measurand | Detector | Sample P / R / F1 | Sample FAR | Event F1 [95 % CI] | Macro timely recall | Episode precision [CI] | False alarms / h [CI] | Missed events | Events |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for m in CFG["measurands"]:
        for d in DETECTORS:
            r = R["signal"][m]["test"][d]
            s, e = r["sample"], r["event"]
            L.append(f"| {m} | {LABEL[d]} | {f3(s['precision'])} / {f3(s['recall'])} / {f3(s['f1'])} | {f3(s['false_alarm_rate'], 4)} | "
                     f"{f3(e['event_f1'])} {ci(e['event_f1_ci95_run_bootstrap'])} | {f3(e['macro_recall'])} | {f3(e['episode_precision'])} {ci(e['episode_precision_ci95'])} | "
                     f"{f3(e['false_alarms_per_hour'], 1)} {ci(e['false_alarms_per_hour_ci95'], 1)} | {e['missed_events']} | {e['events']} |")
    L.append("")

    L += ["## 2. Per fault type (test runs): timely recall [Wilson 95 %], median delay (samples)", ""]
    for m in CFG["measurands"]:
        L += [f"### {m}", "", "| Fault type | n | " + " | ".join(LABEL[d] for d in DETECTORS) + " |", "|---|---|" + "---|" * len(DETECTORS)]
        for c in SIGNAL_FAULT_TYPES:
            if c not in R["signal"][m]["test"]["hybrid"]["per_class"]:
                continue
            cells = []
            for d in DETECTORS:
                p = R["signal"][m]["test"][d]["per_class"][c]
                cells.append(f"{p['detected']}/{p['events']} {ci(p['recall_ci95'])}, {f3(p['median_delay_samples'], 0)}")
            L.append(f"| `{c}` | {R['signal'][m]['test']['hybrid']['per_class'][c]['events']} | " + " | ".join(cells) + " |")
        hp = R["signal"][m]["test"]["hybrid"]["per_class"]
        L += ["", "Hybrid category attribution (detected events whose first alarm carries the matching category): " +
              ", ".join(f"{c} {hp[c]['correct_category']}/{hp[c]['detected']}" for c in hp) + ".",
              "Offset/gain eventually detected at any time after onset (hybrid): " +
              ", ".join(f"{c} {hp[c]['eventually_detected']}/{hp[c]['events']}" for c in hp if c in ("offset_shift", "gain_change")) + ".", ""]

    L += ["## 3. False alarms during fault-free transitions and settling (test runs)", "",
          "False-alarm episodes per hour of fault-free operation in each context [exact 95 % CI]:", "",
          "| Measurand | Context (hours) | " + " | ".join(LABEL[d] for d in DETECTORS) + " |", "|---|---|" + "---|" * len(DETECTORS)]
    for m in CFG["measurands"]:
        for c in (*CONTEXTS, "protocol_plateau_settling"):
            h = R["signal"][m]["test"]["hybrid"]["false_alarms_by_context"][c]["exposure_hours"]
            cells = []
            for d in DETECTORS:
                x = R["signal"][m]["test"][d]["false_alarms_by_context"][c]
                cells.append(f"{f3(x['per_hour'], 1)} {ci(x['per_hour_ci95'], 1)}")
            L.append(f"| {m} | {c} ({h:.2f} h) | " + " | ".join(cells) + " |")
    L += ["", "Fault-free scenario groups (false-alarm episodes per hour):", "", "| Measurand | Scenario group | hours | " + " | ".join(LABEL[d] for d in DETECTORS) + " |", "|---|---|---|" + "---|" * len(DETECTORS)]
    for m in CFG["measurands"]:
        for g, v in R["signal"][m]["test"]["hybrid"]["fault_free_scenarios"].items():
            L.append(f"| {m} | `{g}` | {v['hours']:.2f} | " + " | ".join(f"{R['signal'][m]['test'][d]['fault_free_scenarios'][g]['per_hour']:.1f}" for d in DETECTORS) + " |")
    L.append("")

    L += ["## 4. Integrity track (deterministic rules, identical for every detector; test runs)", "",
          "| Measurand | Precision | Recall | FAR | Per-class recall |", "|---|---|---|---|---|"]
    for m in CFG["measurands"]:
        it = R["integrity"][m]
        L.append(f"| {m} | {f3(it['overall']['precision'])} | {f3(it['overall']['recall'])} | {f3(it['overall']['false_alarm_rate'], 4)} | " +
                 ", ".join(f"{k} {v['detected']}/{v['rows']}" for k, v in it["per_class"].items()) + " |")
    L.append("")

    L += ["## 5. Selection on validation runs (test not used)", ""]
    for m in CFG["measurands"]:
        sel = R["signal"][m]["selection"]
        hs = sel["hybrid"]["selected"]
        L.append(f"- **{m}**: hybrid segment mode `{hs['settings']['segment_mode']}` (MAD threshold {hs['settings']['segment_mad_threshold']}), stuck mode `{hs['settings']['stuck_mode']}`, targeted-GBT config #{hs['gbt_candidate']} at validation FAR target {hs['far_target']} (threshold {hs['settings']['gbt_threshold']:.4g}); "
                 f"validation event F1 {hs['validation']['event_f1']:.3f}, FA/h {hs['validation']['false_alarms_per_hour']:.1f}. CUSUM mode `{sel['cusum']['selected']['mode']}`, transition window {sel['cusum']['selected']['window']}, k = {sel['cusum']['selected']['k']}, h = {sel['cusum']['selected']['h']} "
                 f"(tuning: {sel['cusum']['tuning_runs']['controls']} controls, {sel['cusum']['tuning_runs']['drift_runs']} drift runs; FA {sel['cusum']['selected']['false_alarms']}, detected {sel['cusum']['selected']['detected']}).")
    L += ["", "Validation evidence for the two investigations (hybrid with the selected targeted GBT and threshold; best configuration per option, full grid in `metrics.json`):", "",
          "| Measurand | Option | Best val event F1 | at MAD / stuck mode | Val stuck recall | Val FA/h | Val settling FA/h |", "|---|---|---|---|---|---|---|"]
    for m in CFG["measurands"]:
        tab = R["signal"][m]["selection"]["hybrid"]["investigation_table"]
        for field, label in (("segment_mode", "segment"), ("stuck_mode", "stuck"), ("segment_mad_threshold", "MAD")):
            for opt in dict.fromkeys(t[field] for t in tab):
                b = max((t for t in tab if t[field] == opt), key=lambda t: t["event_f1"])
                L.append(f"| {m} | {label} = `{opt}` | {b['event_f1']:.3f} | {b['segment_mad_threshold']} / {b['stuck_mode']} | {f3(b['stuck_recall'], 2)} | {b['false_alarms_per_hour']:.1f} | {f3(b['settling_fa_per_hour'], 1)} |")
    L += ["", "## 6. Investigations", "", *R["investigations"], "", "## 7. Verdict (test runs)", "", *R["verdict"], "",
          "## 8. Limitations", "", *[f"- {x}" for x in R["limitations"]], ""]
    path.write_text("\n".join(L), encoding="utf-8")


# ==============================================================================
# Main
# ==============================================================================

def main():
    global CFG
    CFG = load_json(WORKSPACE_ROOT / "config" / "hybrid_fault_detection_config.json")
    base_cfg = load_json(WORKSPACE_ROOT / "config" / "default_config.json")
    v3cfg = load_json(WORKSPACE_ROOT / CFG["dataset_config"])
    v2cfg = load_json(WORKSPACE_ROOT / "config" / "synthetic_suite_config.json")
    if set(v3cfg["seed_roots"].values()) & set(v2cfg["seed_roots"].values()):
        print("ABORT: v3 seed roots overlap v2."); return 1
    root = WORKSPACE_ROOT / CFG["dataset_root"]
    for sub in ("models", "plots", "predictions", "config"):
        (OUT / sub).mkdir(parents=True, exist_ok=(sub != "models"))
    for c in ("hybrid_fault_detection_config.json", Path(CFG["dataset_config"]).name):
        shutil.copy(WORKSPACE_ROOT / "config" / c, OUT / "config")

    manifest_bytes = (root / "metadata" / "suite_manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    frames, metas = {}, {}
    for f in manifest["files"]:
        if _sha256_bytes((root / f["csv_file"]).read_bytes()) != f["csv_sha256"]:
            print("ABORT: checksum mismatch", f["csv_file"]); return 1
        frames[f["scenario_id"]] = pd.read_csv(root / f["csv_file"])
        metas[f["scenario_id"]] = load_json(root / f["metadata_file"])
    print(f"Loaded {len(frames)} v3 scenarios (checksums verified).")

    R = {"run_info": {"command": "python scripts/run_hybrid_fault_detection.py", "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                      "dataset_root": CFG["dataset_root"], "suite_id": manifest["suite_id"], "manifest_sha256": _sha256_bytes(manifest_bytes),
                      "seed_roots": v3cfg["seed_roots"], "v2_seed_roots": v2cfg["seed_roots"],
                      "versions": {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__,
                                   "scipy": scipy.__version__, "scikit_learn": sklearn.__version__}},
         "signal": {}, "integrity": {}}
    state = {}
    gp = CFG["gbt_persistent"]

    # ---------------------------------------------------------------- training & selection
    for m in CFG["measurands"]:
        fr = {sid: df for sid, df in frames.items() if metas[sid]["measurand"] == m}
        dev_of = {sid: metas[sid]["sensor_error_model"]["device_id"] for sid in fr}
        cal_rows = pd.concat([df[df.partition == "calibration"] for df in fr.values()], ignore_index=True)
        builder = CausalFeatureBuilder(m).fit(cal_rows)
        sig, _ = build_signal_dataset({k: v[v.partition == "calibration"] for k, v in fr.items()}, m, builder)
        events = [dict(e, scenario_id=sid) for sid in fr for e in metas[sid]["fault_events"] if e["fault_type"] in SIGNAL_FAULT_TYPES]
        onset_seq = {e["event_id"]: e["onset_sequence_number"] for e in events}

        engine = CalibrationEngine()
        cal_models = {}
        for sid, dev in dev_of.items():
            if sid.startswith(("SWEEP_", "PLATEAUS_")):
                d = fr[sid]
                d = d[(d.partition == "calibration") & np.isfinite(d[m])]
                if m == "temperature_C":
                    d = d[d.protocol_phase == "plateau_stable"]
                cal_models[dev] = engine.select_best_model(d[m].to_numpy(), d[f"reference_{m}"].to_numpy(),
                                                           max_degree=base_cfg["calibration"]["max_polynomial_degree"])

        template = HybridSettings("setpoint_blocks", "rule", 1.0, CFG["stuck_rule_alpha"], 0.5, 15.0,
                                  CFG["cusum"]["baseline_fraction"], CFG["cusum"]["min_baseline"], CFG["cusum"]["min_series"],
                                  0, episode_gap=CFG["episode_gap_samples"])
        mads = tuple(sorted(set(CFG["segment_mad_thresholds"]) | {base_cfg["quality"]["mad_threshold"]}))
        detectors = {dev: HybridDetector(m, builder, None, cal_models[dev], base_cfg, template, mads) for dev in cal_models}

        def components(partition):
            out = []
            for sid, df in fr.items():
                for _, run in df[df.partition == partition].groupby("experiment_id", sort=False):
                    out.append(detectors[dev_of[sid]].components(run))
            return out

        comps_val = components("validation")
        E_val = EvalSet(comps_val, events, CFG, m)
        feats_val = pd.concat([c["features"] for c in comps_val], ignore_index=True)
        train = sig.reset_index(drop=True)
        print(f"[{m}] train records {len(train)}, validation records {len(E_val.df)}, validation events {len(E_val.windows)}")

        gbt_all, gbt_trials = select_threshold_detector(GBTDetector, CFG["gbt_all_grid"], train, lambda d: d.score(feats_val), E_val, CFG["individual_far_target"])
        ifo, if_trials = select_threshold_detector(IsolationForestDetector, CFG["iforest_grid"], train, lambda d: d.score(feats_val), E_val, CFG["individual_far_target"])
        cands = [TargetedGBTDetector(params=p, seed=CFG["random_seed"], target_types=tuple(gp["target_types"]),
                                     excluded_types=tuple(gp["excluded_types"]), onset_window=gp["onset_window_samples"],
                                     persistent_types=tuple(gp["persistent_types"]), monotone_increasing=tuple(gp["monotone_increasing"])).fit(train, onset_seq)
                 for p in gp["grid"]]

        runs_cv = [(run.reset_index(drop=True), dev_of[sid], metas[sid]) for sid, df in fr.items()
                   for _, run in df[df.partition.isin(["calibration", "validation"])].groupby("experiment_id", sort=False)]
        c_best, c_grid, c_runs = cusum_tuning(m, runs_cv, cal_models, CFG["cusum"], CFG["cusum_transition_exclusion_samples"][m])
        transition = c_best["window"]

        # hybrid grid on validation
        trials = []
        best = None
        for ci_, cand in enumerate(cands):
            score_val = cand.score(feats_val)
            for far in gp["far_targets"]:
                thr = threshold_at_false_alarm_rate(score_val, E_val.truth, far)
                for seg, mad in [(sg, md) for sg in CFG["segment_modes"] for md in CFG["segment_mad_thresholds"]]:
                    for stuck in CFG["stuck_modes"]:
                        st = HybridSettings(seg, stuck, thr, CFG["stuck_rule_alpha"], c_best["k"], c_best["h"],
                                            CFG["cusum"]["baseline_fraction"], CFG["cusum"]["min_baseline"], CFG["cusum"]["min_series"],
                                            transition, cusum_mode=c_best["mode"], segment_mad_threshold=mad,
                                            episode_gap=CFG["episode_gap_samples"])
                        alarm = np.concatenate([combine(c["segment"][(seg, mad)], stuck_rule_flags(c["features"], st.stuck_alpha),
                                                        score_val[sl] > thr, c["identical_run"], c.get("drift_inputs"), st,
                                                        c["experiment_id"])["alarm"] for c, sl in zip(comps_val, E_val.slices)])
                        q = quick_score(alarm, E_val)
                        stuck_w = [w for w in E_val.windows if w["event"]["fault_type"] == "stuck_signal"]
                        q["stuck_recall"] = (np.mean([alarm[w["positions"]].any() for w in stuck_w]) if stuck_w else None)
                        settle = (E_val.df["protocol_phase"] == "plateau_settling").to_numpy() & ~E_val.truth
                        eps = alarm_episodes(alarm, E_val.exp, E_val.gap)
                        tr = classify_episodes(eps, E_val.active)
                        q["settling_fa_per_hour"] = (sum(1 for e, t in zip(eps, tr) if not t and settle[e["start"]]) / (settle.sum() / 3600.0)) if settle.any() else None
                        trial = {"gbt_candidate": ci_, "far_target": far, "settings": st.to_dict(), "segment_mode": seg,
                                 "segment_mad_threshold": mad, "stuck_mode": stuck, **q}
                        trials.append(trial)
                        key = (round(q["event_f1"], 6), -q["false_alarms_per_hour"])
                        if best is None or key > best[0]:
                            best = (key, trial)
        sel = best[1]
        inv = [{k: t[k] for k in ("segment_mode", "segment_mad_threshold", "stuck_mode", "event_f1", "stuck_recall", "false_alarms_per_hour", "settling_fa_per_hour")}
               for t in trials if t["gbt_candidate"] == sel["gbt_candidate"] and t["far_target"] == sel["far_target"]]
        gbt_p = cands[sel["gbt_candidate"]]
        gbt_p.threshold = sel["settings"]["gbt_threshold"]
        settings = HybridSettings(**sel["settings"])
        cusum_settings = HybridSettings("setpoint_blocks", "rule", 1.0, CFG["stuck_rule_alpha"], c_best["k"], c_best["h"],
                                        CFG["cusum"]["baseline_fraction"], CFG["cusum"]["min_baseline"], CFG["cusum"]["min_series"],
                                        transition, cusum_mode=c_best["mode"])
        R["signal"][m] = {"selection": {
            "feature_floor": builder.floor,
            "gbt_all": {"params": gbt_all.params, "threshold": gbt_all.threshold, "trials": gbt_trials},
            "iforest": {"params": ifo.params, "threshold": ifo.threshold, "trials": if_trials},
            "gbt_persistent_training": [c.training_summary for c in cands],
            "cusum": {"selected": c_best, "grid": c_grid, "tuning_runs": c_runs},
            "hybrid": {"selected": {"gbt_candidate": sel["gbt_candidate"], "far_target": sel["far_target"], "settings": sel["settings"],
                                    "validation": {k: sel[k] for k in ("event_f1", "macro_event_recall", "episode_precision", "false_alarms_per_hour", "stuck_recall", "settling_fa_per_hour")}},
                       "trials": trials, "investigation_table": inv}}}
        state[m] = {"fr": fr, "dev_of": dev_of, "builder": builder, "events": events, "cal_models": cal_models, "gbt_all": gbt_all,
                    "iforest": ifo, "gbt_p": gbt_p, "settings": settings, "cusum_settings": cusum_settings, "transition": transition}

    # ---------------------------------------------------------------- freeze
    frozen = {m: {"hybrid_settings": state[m]["settings"].to_dict(),
                  "targeted_gbt": {"params": state[m]["gbt_p"].params, "threshold": state[m]["gbt_p"].threshold},
                  "gbt_all": {"params": state[m]["gbt_all"].params, "threshold": state[m]["gbt_all"].threshold},
                  "iforest": {"params": state[m]["iforest"].params, "threshold": state[m]["iforest"].threshold},
                  "cusum": {"k": state[m]["cusum_settings"].cusum_k, "h": state[m]["cusum_settings"].cusum_h,
                            "mode": state[m]["cusum_settings"].cusum_mode, "transition_exclusion": state[m]["cusum_settings"].transition_exclusion},
                  "feature_floor": state[m]["builder"].floor,
                  "calibration_models": {d: {"type": mod.model_type, "coefficients": mod.coefficients} for d, mod in state[m]["cal_models"].items()}}
              for m in CFG["measurands"]}
    frozen_bytes = json.dumps(jsonable(frozen), indent=2, sort_keys=True).encode("utf-8")
    (OUT / "frozen_settings.json").write_bytes(frozen_bytes)
    R["run_info"]["frozen_settings_sha256"] = hashlib.sha256(frozen_bytes).hexdigest()
    R["run_info"]["frozen_at_utc"] = datetime.now(timezone.utc).isoformat()
    for m in CFG["measurands"]:
        s = state[m]
        joblib.dump({"feature_builder": s["builder"], "gbt_all": s["gbt_all"], "iforest": s["iforest"], "targeted_gbt": s["gbt_p"],
                     "calibration_models": s["cal_models"], "hybrid_settings": s["settings"], "cusum_settings": s["cusum_settings"]},
                    OUT / "models" / f"{m}_detectors.joblib")
    print(f"Settings frozen: {R['run_info']['frozen_settings_sha256'][:16]}…")
    if "--selection-only" in sys.argv:
        with open(OUT / "selection_only_metrics.json", "w", encoding="utf-8") as f:
            json.dump(jsonable(R), f, indent=2)
        print(f"Selection-only run (no test records processed): {OUT}")
        return 0
    print("Scoring test runs once.")

    # ---------------------------------------------------------------- test (once)
    R["run_info"]["test_started_utc"] = datetime.now(timezone.utc).isoformat()
    for m in CFG["measurands"]:
        s = state[m]
        comps = []
        for sid, df in s["fr"].items():
            hd = HybridDetector(m, s["builder"], s["gbt_p"], s["cal_models"][s["dev_of"][sid]], base_cfg, s["settings"],
                                (base_cfg["quality"]["mad_threshold"], s["settings"].segment_mad_threshold))
            for _, run in df[df.partition == "test"].groupby("experiment_id", sort=False):
                comps.append((hd, hd.components(run)))
        E = EvalSet([c for _, c in comps], s["events"], CFG, m)
        alarms, category = {d: [] for d in DETECTORS}, []
        for hd, c in comps:
            res = hd.apply(c)
            alarms["hybrid"].append(res["alarm"]); category.append(res["category"])
            alarms["segment_setpoint"].append(c["segment"][("setpoint_blocks", base_cfg["quality"]["mad_threshold"])])
            alarms["gbt_all"].append(s["gbt_all"].score(c["features"]) > s["gbt_all"].threshold)
            alarms["iforest"].append(s["iforest"].score(c["features"]) > s["iforest"].threshold)
            alarms["gbt_persistent"].append(c["gbt_score"] > s["gbt_p"].threshold)
            alarms["stuck_rule"].append(stuck_rule_flags(c["features"], CFG["stuck_rule_alpha"]))
            di = c.get("drift_inputs")
            alarms["cusum"].append(drift_component(di["t_s"], di["err"], drift_usable(di, s["cusum_settings"].transition_exclusion), [],
                                                   s["cusum_settings"], di["segment_starts"]))
        alarms = {d: np.concatenate(v) for d, v in alarms.items()}
        category = np.concatenate(category)
        R["signal"][m]["test"] = {d: full_eval(alarms[d], E, CFG, category if d == "hybrid" else None) for d in DETECTORS}
        out = E.df[["scenario_id", "experiment_id", "sequence_number", "protocol_phase", "signal_fault_type", "label_process_event"]].copy()
        for d in DETECTORS:
            out[f"{d}_alarm"] = alarms[d]
        out["hybrid_category"] = category
        out.to_csv(OUT / "predictions" / f"{m}_test_alarms.csv", index=False)

        # integrity track on raw test records
        flags, labs = [], []
        for _, c in comps:
            flags.append(c["integrity"])
            labs.append([";".join(t for t in x.split(";") if t in INTEGRITY_FAULT_TYPES) or "none" for x in c["run"]["label_fault_type"]])
        flags = np.concatenate(flags); labs = np.concatenate(labs)
        integ = {"overall": binary_metrics(flags, labs != "none"), "per_class": {}}
        for t in INTEGRITY_FAULT_TYPES:
            rows = np.array([t in x.split(";") for x in labs])
            if rows.any():
                integ["per_class"][t] = {"rows": int(rows.sum()), "detected": int(flags[rows].sum())}
        R["integrity"][m] = integ
        print(f"[{m}] test scored: {len(E.df)} records, {len(E.windows)} signal events")

    # ---------------------------------------------------------------- investigations & verdict (from numbers)
    inv = []
    for m in CFG["measurands"]:
        t = R["signal"][m]["test"]
        st = {d: t[d]["per_class"].get("stuck_signal") for d in ("gbt_all", "gbt_persistent", "stuck_rule", "hybrid")}
        if st["hybrid"]:
            inv.append(f"- **Stuck ({m}, test):** GBT(all) {st['gbt_all']['detected']}/{st['gbt_all']['events']}, targeted GBT {st['gbt_persistent']['detected']}/{st['gbt_persistent']['events']}, "
                       f"stuck rule {st['stuck_rule']['detected']}/{st['stuck_rule']['events']} (median delay {f3(st['stuck_rule']['median_delay_samples'], 0)}), hybrid {st['hybrid']['detected']}/{st['hybrid']['events']}.")
    for m in CFG["measurands"]:
        t = R["signal"][m]["test"]
        a = t["segment_setpoint"]["false_alarms_by_context"]["protocol_plateau_settling"]
        b = t["hybrid"]["false_alarms_by_context"]["protocol_plateau_settling"]
        if a["exposure_hours"] > 0:
            inv.append(f"- **Settling ({m}, test, {a['exposure_hours']:.2f} h fault-free settling):** existing segment detector {f3(a['per_hour'], 1)} false-alarm episodes/h {ci(a['per_hour_ci95'], 1)}; hybrid {f3(b['per_hour'], 1)} {ci(b['per_hour_ci95'], 1)} with segment mode `{state[m]['settings'].segment_mode}`.")
    R["investigations"] = inv
    verdict = []
    for m in CFG["measurands"]:
        t = R["signal"][m]["test"]
        f1 = {d: t[d]["event"]["event_f1"] for d in DETECTORS}
        best_ind = max((d for d in DETECTORS if d != "hybrid"), key=lambda d: f1[d])
        h_ci, b_ci = t["hybrid"]["event"]["event_f1_ci95_run_bootstrap"], t[best_ind]["event"]["event_f1_ci95_run_bootstrap"]
        overlap = h_ci[0] is not None and b_ci[0] is not None and not (h_ci[0] > b_ci[1] or b_ci[0] > h_ci[1])
        verdict.append(f"- {m}: hybrid event F1 {f1['hybrid']:.3f} {ci(h_ci)} vs best individual detector ({LABEL[best_ind]}) {f1[best_ind]:.3f} {ci(b_ci)}; "
                       f"FA/h hybrid {t['hybrid']['event']['false_alarms_per_hour']:.1f} vs {t[best_ind]['event']['false_alarms_per_hour']:.1f}. "
                       + ("Bootstrap intervals overlap: the difference is not established." if overlap else "Bootstrap intervals do not overlap."))
    verdict.append("- These statements cover only the simulated fault and noise models of the v3 suite; event counts per class and measurand are 6–48, so per-class intervals are wide.")
    R["verdict"] = verdict
    R["limitations"] = [
        "Synthetic data only; the generator and the detectors share simulated noise models, which favours learned components.",
        "The segment component uses whole protocol segments (non-causal within a segment): its decisions are final only when the segment ends. The GBT, stuck-rule and CUSUM components are causal.",
        "The drift component needs a reference instrument and a static calibration (laboratory verification); drift cannot be separated from a true process change without a reference.",
        "Offset and gain faults are only distinguishable near onset; a persistent fault missed at onset is usually caught later by the CUSUM, but that is counted as a late detection, not a timely one.",
        "Protocol information (set-point index, protocol phase) is used for segmentation and transition masking, as an operator schedule would provide; it is not used as a model feature.",
        "Thresholds were selected at validation operating points; test false-alarm rates can differ.",
        "Stuck detection by the identical-run rule is impossible when the expected repeat probability is high (coarse quantisation, very low noise).",
        "Not integrated into the application, the R1-R5 decision engine or any calibration step.",
        "Drift alarms are latched until the next re-baseline point or the end of the run, so sample-level false-alarm rates of the hybrid and of the CUSUM are inflated after any CUSUM alarm (including alarms triggered by real spikes or offsets); episode-level metrics are the intended operating measure.",
        "Category attribution is reliable for spikes, stuck signals and drift but weak for offset and gain changes (the segment detector often fires first on the step and labels it 'transient').",
        "Mixed-fault runs place several faults in one run, so a 'timely' offset detection can be triggered by a co-occurring transient fault inside the 60-sample window.",
        "The selected MAD thresholds for current and temperature (7.0) lie on the upper edge of the validation grid; the current CUSUM tuning detected only 3/6 tuning drift runs with 1 false alarm.",
        "The temperature hybrid chose 'phase_blocks_stationary_only', which removes transient detection during ramps and settling; spikes there are left to other components and are often missed (24/48 temperature spikes detected).",
    ]

    with open(OUT / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(jsonable(R), f, indent=2)
    write_report(R, OUT / "REPORT.md")
    plot_recall(R["signal"], OUT / "plots" / "event_recall_by_class.png")
    plot_fa(R["signal"], OUT / "plots" / "false_alarms_by_context.png")
    print(f"\nOutput: {OUT}")
    for v in verdict:
        print(v)
    return 0


if __name__ == "__main__":
    sys.exit(main())
