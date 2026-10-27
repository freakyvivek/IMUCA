#!/usr/bin/env python3
"""
IMUCA ML Fault Detection & CUSUM Tuning Experiment (synthetic data only).

Signal track (per measurand):
  1. Gradient-boosted trees (HistGradientBoostingClassifier) on causal features.
  2. Isolation Forest trained on fault-free calibration records.
  3. Conventional baseline: existing DataQualityAssessor applied per protocol segment.
  Fit on the calibration partition, choose hyper-parameters and the alarm threshold on the
  validation partition, then score the test partition once.

Integrity track: deterministic record-integrity rules (missing, non-finite, duplicate,
out-of-order, gap, status) evaluated separately.

CUSUM study: parameters of the existing analyze_temporal_drift CUSUM tuned on
calibration+validation runs only, evaluated once on test runs.

Outputs: results/ml_fault_detection_<timestamp>/ (models, metrics JSON, predictions,
plots, REPORT.md). Existing results are never modified.

Usage:
    python scripts/run_ml_fault_detection.py
"""

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
from src.imuca.ml_features import (
    CausalFeatureBuilder, build_signal_dataset, integrity_rule_flags, FEATURE_NAMES, FEATURE_DEFINITIONS,
    NOISE_SCALE_DEFINITION, SIGNAL_FAULT_TYPES, INTEGRITY_FAULT_TYPES, PERSISTENT_SIGNAL_FAULTS, INTEGRITY_ISSUE_TYPES,
)
from src.imuca.ml_fault_detection import GBTDetector, IsolationForestDetector, segment_baseline_flags
from src.imuca.detection_metrics import (
    binary_metrics, event_detection, summarize_events, operating_context, false_alarms_by_context,
    threshold_at_false_alarm_rate, CONTEXTS,
)
from src.imuca.cusum_tuning import run_cusum, siegmund_arl_two_sided

DATA_ROOT = WORKSPACE_ROOT / "data" / "synthetic"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUT = WORKSPACE_ROOT / "results" / f"ml_fault_detection_{STAMP}"
DETECTORS = ("gbt", "iforest", "baseline")
DET_LABEL = {"gbt": "Gradient-boosted trees", "iforest": "Isolation Forest", "baseline": "Conventional per-segment"}
STEADY_PHASES = ("steady", "plateau_stable", "dwell")


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
    return o


# ==============================================================================
# Signal-track evaluation
# ==============================================================================

def evaluate(pred, df, events, transient, far_for_chance, metas):
    truth = df["is_signal_fault"].to_numpy()
    res = {"overall": binary_metrics(pred, truth)}
    per_class = {}
    for c in SIGNAL_FAULT_TYPES:
        rows = df["signal_fault_type"].str.contains(c).to_numpy()
        if rows.any():
            per_class[c] = {"rows": int(rows.sum()), "row_recall": float(pred[rows].mean())}
    res["per_class_rows"] = per_class
    ev = event_detection(pred, df, events, PERSISTENT_SIGNAL_FAULTS, CFG["persistent_event_window_samples"], far_for_chance)
    res["events"] = summarize_events(ev)
    res["event_list"] = ev
    ctx = operating_context(df, transient, CFG["post_fault_aftermath_samples"])
    res["false_alarms_by_context"] = false_alarms_by_context(pred, truth, ctx)
    # class confusion: true class x {alarm, no alarm}
    conf = {}
    for c in ["none", *SIGNAL_FAULT_TYPES]:
        rows = (df["signal_fault_type"] == "none").to_numpy() if c == "none" else df["signal_fault_type"].str.contains(c).to_numpy()
        if rows.any():
            conf[c] = {"alarm": int(pred[rows].sum()), "no_alarm": int((~pred[rows]).sum())}
    res["class_confusion"] = conf
    # fault-free scenarios: false alarms per hour of operation
    ff = {}
    for sid, g in df.groupby("scenario_id"):
        if metas[sid]["fault_prevalence"]["fault_row_count"] == 0:
            idx = g.index.to_numpy()
            hours = len(g) / 3600.0
            ff[sid] = {"records": int(len(g)), "false_alarms": int(pred[df.index.get_indexer(idx)].sum()),
                       "false_alarms_per_hour": float(pred[df.index.get_indexer(idx)].sum() / hours)}
    res["fault_free_scenarios"] = ff
    return res


def posthoc_spike_latency(pred, df, events, sigma, tol):
    """Post-hoc: does an alarm occur at the spike sample, or within `tol` samples after it?"""
    exp = df["experiment_id"].to_numpy(); seq = df["sequence_number"].to_numpy()
    out = {"events": 0, "alarm_at_spike": 0, "alarm_within_tolerance": 0, "missed_magnitudes_sigma": [], "all_magnitudes_sigma": []}
    for ev in events:
        if ev["fault_type"] != "isolated_spike":
            continue
        rows = np.flatnonzero((exp == ev["run_id"]) & (seq >= ev["onset_sequence_number"]) & (seq <= ev["onset_sequence_number"] + tol))
        if len(rows) == 0 or seq[rows[0]] != ev["onset_sequence_number"]:
            continue
        mag = abs(ev["magnitude"]) / sigma
        out["events"] += 1
        out["all_magnitudes_sigma"].append(round(mag, 1))
        out["alarm_at_spike"] += int(pred[rows[0]])
        hit = bool(pred[rows].any())
        out["alarm_within_tolerance"] += int(hit)
        if not hit:
            out["missed_magnitudes_sigma"].append(round(mag, 1))
    return out


def macro_event_recall(ev_summary):
    vals = [v["event_recall"] for v in ev_summary.values()]
    return float(np.mean(vals)) if vals else 0.0


def select(detector_cls, grid, train, val, events, transient, metas):
    """Fit each config on calibration, set threshold on validation, keep the best by the selection rule."""
    truth = val["is_signal_fault"].to_numpy()
    trials, best = [], None
    for params in grid:
        det = detector_cls(params=params, seed=CFG["random_seed"]).fit(train)
        s = det.score(val)
        thr = threshold_at_false_alarm_rate(s, truth, CFG["target_false_alarm_rate"])
        pred = s > thr
        bm = binary_metrics(pred, truth)
        ev = summarize_events(event_detection(pred, val, events, PERSISTENT_SIGNAL_FAULTS,
                                              CFG["persistent_event_window_samples"], bm["false_alarm_rate"]))
        key = (macro_event_recall(ev), bm["f1"] or 0.0)
        trials.append({"params": params, "threshold": thr, "val_macro_event_recall": key[0], "val_f1": key[1],
                       "val_false_alarm_rate": bm["false_alarm_rate"]})
        if best is None or key > best[0]:
            det.threshold = thr
            best = (key, det)
    return best[1], trials


def integrity_eval(integ):
    flag = integ["integrity_rule_flag"].to_numpy()
    lab = integ["integrity_label"].to_numpy() != "none"
    out = {"overall": binary_metrics(flag, lab), "per_class": {}}
    for c in INTEGRITY_FAULT_TYPES:
        rows = integ["integrity_label"].str.contains(c).to_numpy()
        if rows.any():
            out["per_class"][c] = {"rows": int(rows.sum()), "recall": float(flag[rows].mean())}
    sig = integ["label_fault_type"].apply(lambda s: any(t in SIGNAL_FAULT_TYPES for t in s.split(";"))).to_numpy()
    out["signal_fault_rows_flagged_by_integrity_rules"] = int((flag & sig).sum())
    return out


# ==============================================================================
# CUSUM study
# ==============================================================================

def cusum_study(frames, metas, suite_cfg):
    cc = CFG["cusum"]
    engine = CalibrationEngine()
    cal_models = {}
    for dev, src in cc["calibration_sources"].items():
        df = frames[src]
        m = metas[src]["measurand"]
        d = df[(df.partition == "calibration") & (df.status == "OK") & np.isfinite(df[m])]
        if m == "temperature_C":
            d = d[d.protocol_phase == "plateau_stable"]
        cal_models[dev] = engine.fit_linear(d[m].to_numpy(), d[f"reference_{m}"].to_numpy())

    runs = []
    for sid in cc["drift_scenarios"] + cc["extra_control_scenarios"]:
        df, meta = frames[sid], metas[sid]
        m = meta["measurand"]
        model = cal_models[meta["sensor_error_model"]["device_id"]]
        drift_ev = {e["run_id"]: e for e in meta["fault_events"] if e["fault_type"] == "gradual_drift"}
        for exp_id, run in df.groupby("experiment_id", sort=False):
            run = run.reset_index(drop=True)
            flags, _ = integrity_rule_flags(run[[m, "experiment_id", "status", "sequence_number", "elapsed_ms"]], m)
            keep = (~flags) & run.protocol_phase.isin(STEADY_PHASES).to_numpy()
            r = run[keep]
            e = model.predict(r[m].to_numpy()) - r[f"reference_{m}"].to_numpy()
            ev = drift_ev.get(exp_id)
            runs.append({"scenario_id": sid, "experiment_id": exp_id, "partition": r.partition.iloc[0], "measurand": m,
                         "drift": ev is not None, "onset_s": ev["onset_elapsed_ms"] / 1000.0 if ev else None,
                         "rate": ev["magnitude"] if ev else 0.0,
                         "t": r.elapsed_ms.to_numpy() / 1000.0, "e": e, "n": len(r)})
    longest = max(r["n"] for r in runs)
    min_arl = cc["min_arl0_multiple_of_longest_run"] * longest

    def score(runset, k, h, mode):
        rows = []
        for r in runset:
            o = run_cusum(r["t"], r["e"], k, h, cc["baseline_fraction"], mode, r["onset_s"])
            fa = o["alarm"] and (not r["drift"] or o.get("alarm_before_onset"))
            rows.append({"experiment_id": r["experiment_id"], "scenario_id": r["scenario_id"], "measurand": r["measurand"],
                         "partition": r["partition"], "drift": r["drift"], "rate": r["rate"], "alarm": o["alarm"],
                         "false_alarm": bool(fa), "detected": bool(r["drift"] and o["alarm"] and not o.get("alarm_before_onset")),
                         "delay_s": o.get("delay_s"), "regression_alarm": o["regression_alarm"]})
        ctrl = [x for x in rows if not x["drift"]]
        dr = [x for x in rows if x["drift"]]
        delays = [x["delay_s"] for x in dr if x["detected"]]
        return {"control_runs": len(ctrl), "control_false_alarms": sum(x["false_alarm"] for x in ctrl),
                "drift_runs": len(dr), "drift_detected": sum(x["detected"] for x in dr),
                "drift_pre_onset_alarms": sum(x["false_alarm"] for x in dr),
                "median_delay_s": float(np.median(delays)) if delays else None, "runs": rows}

    tune = [r for r in runs if r["partition"] in ("calibration", "validation")]
    test = [r for r in runs if r["partition"] == "test"]
    grid = []
    for k in cc["k_grid"]:
        for h in cc["h_grid"]:
            s = score(tune, k, h, "baseline_window")
            arl = siegmund_arl_two_sided(k, h)
            grid.append({"k": k, "h": h, "arl0_siegmund": arl, "arl0_ok": arl >= min_arl,
                         **{kk: v for kk, v in s.items() if kk != "runs"}})
    feasible = [g for g in grid if g["arl0_ok"] and g["control_false_alarms"] == 0 and g["drift_pre_onset_alarms"] == 0]
    if not feasible:
        raise RuntimeError("No CUSUM configuration satisfies the tuning constraints.")
    best = sorted(feasible, key=lambda g: (-g["drift_detected"], g["median_delay_s"] if g["median_delay_s"] is not None else 1e9, -g["arl0_siegmund"]))[0]

    diag = []
    for r in tune:
        if r["drift"]:
            continue
        nb = max(10, int(len(r["e"]) * cc["baseline_fraction"]))
        sb = float(np.std(r["e"][:nb], ddof=1))
        diag.append({"sd_ratio_run_to_baseline": float(np.std(r["e"], ddof=1) / sb),
                     "mean_offset_sigma": float(abs(np.mean(r["e"]) - np.mean(r["e"][:nb])) / sb), "baseline_samples": nb})
    sdr = np.array([x["sd_ratio_run_to_baseline"] for x in diag]); mo = np.array([x["mean_offset_sigma"] for x in diag])
    baseline_diag = {
        "tuning_controls": len(diag),
        "sd_ratio_median": float(np.median(sdr)), "sd_ratio_max": float(sdr.max()),
        "mean_offset_sigma_median": float(np.median(mo)), "mean_offset_sigma_max": float(mo.max()),
        "arl0_selected_if_target_off_by_0.1_sigma": siegmund_arl_two_sided(best["k"], best["h"], 0.1),
        "arl0_selected_if_target_off_by_0.3_sigma": siegmund_arl_two_sided(best["k"], best["h"], 0.3),
        "arl0_k0.5_h10_if_target_off_by_0.3_sigma": siegmund_arl_two_sided(0.5, 10, 0.3),
        "interpretation": "sigma and target are estimated from a short baseline window (60-180 samples); estimation error in either reduces the true in-control ARL by orders of magnitude relative to the nominal Siegmund value, which is why h well above the nominal design value is needed for zero false alarms.",
    }
    default_tune = score(tune, 0.5, 4.0, "existing_default")
    default_test = score(test, 0.5, 4.0, "existing_default")
    tuned_test = score(test, best["k"], best["h"], "baseline_window")
    legacy_ids = {r["experiment_id"] for r in runs if r["scenario_id"] in ("VOLT_DRIFT", "CURR_DRIFT", "TEMP_DRIFT") and not r["drift"]}
    legacy_all = [r for r in runs if r["experiment_id"] in legacy_ids]
    by_meas = {}
    for m in CFG["measurands"]:
        sub = [r for r in test if r["measurand"] == m]
        s = score(sub, best["k"], best["h"], "baseline_window")
        d = score(sub, 0.5, 4.0, "existing_default")
        by_meas[m] = {"tuned": {k: v for k, v in s.items() if k != "runs"}, "existing_default": {k: v for k, v in d.items() if k != "runs"}}
    return {
        "longest_run_samples": longest, "min_arl0_required": min_arl,
        "tuning_runs": {"controls": sum(not r["drift"] for r in tune), "drift": sum(r["drift"] for r in tune)},
        "test_runs": {"controls": sum(not r["drift"] for r in test), "drift": sum(r["drift"] for r in test)},
        "baseline_estimation_diagnostics": baseline_diag,
        "grid": grid, "selected": {"k": best["k"], "h": best["h"], "arl0_siegmund": best["arl0_siegmund"], "sigma": "baseline window (first 10 % of run)"},
        "existing_default": {"k": 0.5, "h": 4.0, "arl0_siegmund": siegmund_arl_two_sided(0.5, 4.0), "sigma": "whole-run detrended residual std"},
        "existing_default_on_tuning": {k: v for k, v in default_tune.items() if k != "runs"},
        "existing_default_on_test": default_test, "tuned_on_test": tuned_test, "test_by_measurand": by_meas,
        "milestone2_nine_controls": {
            "existing_default": {k: v for k, v in score(legacy_all, 0.5, 4.0, "existing_default").items() if k != "runs"},
            "tuned": {k: v for k, v in score(legacy_all, best["k"], best["h"], "baseline_window").items() if k != "runs"},
            "note": "6 of these 9 runs are in the calibration/validation partitions and were part of the tuning set; only the 3 test-partition controls are independent.",
        },
        "calibration_models": {d: m.formula_string for d, m in cal_models.items()},
    }


# ==============================================================================
# Plots
# ==============================================================================

def _style(ax, pal):
    ax.set_facecolor(pal["surface"])
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(pal["muted"])
    ax.tick_params(colors=pal["muted"], labelsize=8)
    ax.grid(axis="x", color="#e4e3df", linewidth=0.6)
    ax.set_axisbelow(True)


def plot_event_recall(results, path):
    pal = CFG["plot_palette"]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.6), facecolor=pal["surface"], layout="constrained")
    for ax, m in zip(axes, CFG["measurands"]):
        classes = [c for c in SIGNAL_FAULT_TYPES if c in results[m]["test"]["gbt"]["events"]]
        y = np.arange(len(classes))
        hgt = 0.26
        for j, d in enumerate(DETECTORS):
            ev = results[m]["test"][d]["events"]
            vals = [ev[c]["event_recall"] for c in classes]
            ax.barh(y + (j - 1) * (hgt + 0.02), vals, height=hgt, color=pal[d], label=DET_LABEL[d])
            ch = [ev[c]["mean_chance_detection_probability"] or 0 for c in classes]
            ax.scatter(ch, y + (j - 1) * (hgt + 0.02), marker="|", s=90, color=pal["text"], linewidths=1.2,
                       label="Chance level at detector FAR" if j == 0 else None, zorder=3)
        ax.set_yticks(y, [c.replace("_", " ") for c in classes], color=pal["text"], fontsize=8)
        ax.invert_yaxis()
        ax.set_xlim(0, 1.0)
        ax.set_title(m, color=pal["text"], fontsize=10, loc="left")
        ax.set_xlabel("Event recall (test runs)", color=pal["muted"], fontsize=8)
        _style(ax, pal)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="outside lower left", ncol=4, frameon=False, fontsize=8)
    fig.suptitle("Signal-fault event recall by class and measurand (synthetic test partition)", color=pal["text"], fontsize=11, x=0.01, ha="left")
    fig.savefig(path, dpi=150, facecolor=pal["surface"], bbox_inches="tight")
    plt.close(fig)


def plot_false_alarms(results, path):
    pal = CFG["plot_palette"]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.4), facecolor=pal["surface"], layout="constrained")
    ctxs = CONTEXTS
    for ax, m in zip(axes, CFG["measurands"]):
        y = np.arange(len(ctxs))
        hgt = 0.26
        for j, d in enumerate(DETECTORS):
            fa = results[m]["test"][d]["false_alarms_by_context"]
            vals = [100 * (fa[c]["false_alarm_rate"] or 0) for c in ctxs]
            ax.barh(y + (j - 1) * (hgt + 0.02), vals, height=hgt, color=pal[d], label=DET_LABEL[d])
        ax.set_yticks(y, [f"{c.replace('_', ' ')}\n(n={results[m]['test']['gbt']['false_alarms_by_context'][c]['negatives']})" for c in ctxs],
                      color=pal["text"], fontsize=8)
        ax.invert_yaxis()
        ax.set_title(m, color=pal["text"], fontsize=10, loc="left")
        ax.set_xlabel("False-alarm rate on fault-free records (%)", color=pal["muted"], fontsize=8)
        _style(ax, pal)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="outside lower left", ncol=3, frameon=False, fontsize=8)
    fig.suptitle("False alarms by operating context (synthetic test partition)", color=pal["text"], fontsize=11, x=0.01, ha="left")
    fig.savefig(path, dpi=150, facecolor=pal["surface"], bbox_inches="tight")
    plt.close(fig)


def plot_cusum(cs, path):
    pal = CFG["plot_palette"]
    colors = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.6), facecolor=pal["surface"])
    for i, k in enumerate(CFG["cusum"]["k_grid"]):
        g = [x for x in cs["grid"] if x["k"] == k]
        hs = [x["h"] for x in g]
        axes[0].plot(hs, [x["control_false_alarms"] + x["drift_pre_onset_alarms"] for x in g], color=colors[i], lw=2, marker="o", ms=4, label=f"k = {k}")
        axes[1].plot(hs, [x["drift_detected"] for x in g], color=colors[i], lw=2, marker="o", ms=4, label=f"k = {k}")
    sel = cs["selected"]
    for ax in axes:
        ax.axvline(sel["h"], color=pal["muted"], lw=0.8, ls="--")
        _style(ax, pal)
        ax.grid(axis="y", color="#e4e3df", linewidth=0.6)
        ax.set_xlabel("h (decision interval, sigma units)", color=pal["muted"], fontsize=8)
    axes[0].set_title(f"False alarms on tuning runs ({cs['tuning_runs']['controls']} controls + pre-onset)", color=pal["text"], fontsize=10, loc="left")
    axes[1].set_title(f"Drift runs detected (of {cs['tuning_runs']['drift']} tuning drift runs)", color=pal["text"], fontsize=10, loc="left")
    axes[1].text(sel["h"], 0.3, f" selected k={sel['k']}, h={sel['h']}", color=pal["text"], fontsize=8)
    axes[0].legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=pal["surface"], bbox_inches="tight")
    plt.close(fig)


# ==============================================================================
# Report
# ==============================================================================

def f3(x):
    return "–" if x is None else (f"{x:.3f}" if isinstance(x, float) else str(x))


def write_report(R, path):
    L = ["# IMUCA — ML Fault Detection & CUSUM Tuning Report", "",
         "> SYNTHETIC DATA ONLY. These results compare detectors on simulated faults generated by `src/imuca/synthetic_suite.py`; they say nothing about real sensor behaviour.", "",
         f"- Run: `{R['run_info']['command']}` at {R['run_info']['timestamp_utc']}; suite manifest `{R['run_info']['suite_manifest_sha256'][:16]}…` (checksums verified).",
         f"- Splits: train = calibration runs, model/threshold selection = validation runs, final = test runs (each run in exactly one partition; verified: {R['run_info']['split_integrity_verified']}).",
         f"- Threshold rule: alarm when score > threshold with validation false-alarm rate ≤ {CFG['target_false_alarm_rate']:.1%}. Persistent faults count as detected only within {CFG['persistent_event_window_samples']} samples of onset.",
         "- The conventional baseline has no tunable threshold; it uses operator protocol segmentation and non-causal per-segment MAD, which the ML detectors do not.", ""]

    L += ["## 1. Signal track — overall (test partition, record level)", "",
          "| Measurand | Detector | Precision | Recall | F1 | False-alarm rate | Missed-detection rate | TP / FP / TN / FN |", "|---|---|---|---|---|---|---|---|"]
    for m in CFG["measurands"]:
        for d in DETECTORS:
            o = R["signal"][m]["test"][d]["overall"]
            L.append(f"| {m} | {DET_LABEL[d]} | {f3(o['precision'])} | {f3(o['recall'])} | {f3(o['f1'])} | {f3(o['false_alarm_rate'])} | {f3(o['missed_detection_rate'])} | {o['TP']} / {o['FP']} / {o['TN']} / {o['FN']} |")
    L += ["", "Record-level recall is dominated by persistent faults (offset, gain, drift), which stay labelled until the end of the run but are only visible near onset to a causal single-sensor detector. Event-level results below are more informative.", ""]

    L += ["## 2. Per-fault and per-measurand event detection (test partition)", "",
          "Event recall = detected / events; delay = median samples from onset to first alarm; chance = probability that random alarms at the detector's test FAR would land in the window.", ""]
    for m in CFG["measurands"]:
        L += [f"### {m}", "", "| Fault class | GBT recall (delay, chance) | Isolation Forest recall (delay, chance) | Conventional recall (delay, chance) |", "|---|---|---|---|"]
        classes = sorted({c for d in DETECTORS for c in R["signal"][m]["test"][d]["events"]})
        for c in classes:
            cells = []
            for d in DETECTORS:
                e = R["signal"][m]["test"][d]["events"].get(c)
                cells.append("–" if not e else f"{e['detected']}/{e['events']} = {e['event_recall']:.2f} ({f3(e['median_delay_samples'])}, {f3(e['mean_chance_detection_probability'])})")
            L.append(f"| `{c}` | " + " | ".join(cells) + " |")
        L.append("")

    L += ["## 3. Confusion by true class (test partition, records alarmed / total)", "",
          "| Measurand | True class | GBT | Isolation Forest | Conventional |", "|---|---|---|---|---|"]
    for m in CFG["measurands"]:
        for c in R["signal"][m]["test"]["gbt"]["class_confusion"]:
            cells = []
            for d in DETECTORS:
                cc = R["signal"][m]["test"][d]["class_confusion"][c]
                cells.append(f"{cc['alarm']} / {cc['alarm'] + cc['no_alarm']}")
            L.append(f"| {m} | `{c}` | " + " | ".join(cells) + " |")
    L.append("")

    L += ["## 4. False alarms during operating transitions (test partition)", "",
          "| Measurand | Context (fault-free records) | GBT FAR | Isolation Forest FAR | Conventional FAR |", "|---|---|---|---|---|"]
    for m in CFG["measurands"]:
        for c in CONTEXTS:
            v = [R["signal"][m]["test"][d]["false_alarms_by_context"][c] for d in DETECTORS]
            L.append(f"| {m} | {c} (n={v[0]['negatives']}) | " + " | ".join(f"{f3(x['false_alarm_rate'])} ({x['false_alarms']})" for x in v) + " |")
    L += ["", "False alarms per hour on fault-free test scenarios:", "", "| Scenario | GBT | Isolation Forest | Conventional |", "|---|---|---|---|"]
    for m in CFG["measurands"]:
        for sid in R["signal"][m]["test"]["gbt"]["fault_free_scenarios"]:
            L.append(f"| `{sid}` | " + " | ".join(f"{R['signal'][m]['test'][d]['fault_free_scenarios'][sid]['false_alarms_per_hour']:.1f}" for d in DETECTORS) + " |")
    L += ["", R["temperature_transient_investigation"]["summary"], ""]

    L += ["## 5. Integrity track — deterministic rules (test partition)", "", "| Measurand | Precision | Recall | FAR | Per-class recall | Signal-fault rows flagged by integrity rules |", "|---|---|---|---|---|---|"]
    for m in CFG["measurands"]:
        it = R["integrity"][m]["test"]
        pcs = ", ".join(f"{k} {v['recall']:.2f}" for k, v in it["per_class"].items())
        L.append(f"| {m} | {f3(it['overall']['precision'])} | {f3(it['overall']['recall'])} | {f3(it['overall']['false_alarm_rate'])} | {pcs} | {it['signal_fault_rows_flagged_by_integrity_rules']} |")
    L.append("")

    cs = R["cusum"]
    sel, dft = cs["selected"], cs["existing_default"]
    t, d0 = cs["tuned_on_test"], cs["existing_default_on_test"]
    L += ["## 6. CUSUM investigation and tuning", "",
          f"**Root cause.** The existing CUSUM uses k = 0.5σ, h = 4σ. Its two-sided in-control ARL (Siegmund approximation) is {dft['arl0_siegmund']:.0f} samples, far shorter than the 1200–1800-sample runs, so false alarms are expected even without drift. Its σ comes from the whole-run detrended residual (non-causal) and its target from the baseline median.",
          "",
          f"**Tuning (calibration + validation runs only: {cs['tuning_runs']['controls']} controls, {cs['tuning_runs']['drift']} drift runs).** Grid k ∈ {CFG['cusum']['k_grid']}, h ∈ {CFG['cusum']['h_grid']}; σ and target from the first 10 % of each run (causal); constraint ARL0 ≥ {cs['min_arl0_required']:.0f} samples (10 × longest run), zero tuning false alarms. Selected **k = {sel['k']}, h = {sel['h']}** (ARL0 ≈ {sel['arl0_siegmund']:.3g}).",
          "",
          f"**Independent test runs ({cs['test_runs']['controls']} controls, {cs['test_runs']['drift']} drift runs):**", "",
          "| Configuration | False alarms on controls | Pre-onset alarms on drift runs | Drift runs detected | Median delay (s) |", "|---|---|---|---|---|",
          f"| Existing (k=0.5, h=4, residual σ) | {d0['control_false_alarms']} / {d0['control_runs']} | {d0['drift_pre_onset_alarms']} | {d0['drift_detected']} / {d0['drift_runs']} | {f3(d0['median_delay_s'])} |",
          f"| Tuned (k={sel['k']}, h={sel['h']}, baseline σ) | {t['control_false_alarms']} / {t['control_runs']} | {t['drift_pre_onset_alarms']} | {t['drift_detected']} / {t['drift_runs']} | {f3(t['median_delay_s'])} |",
          "", "By measurand (test):", ""]
    for m, v in cs["test_by_measurand"].items():
        L.append(f"- {m}: tuned FA {v['tuned']['control_false_alarms']}/{v['tuned']['control_runs']}, detected {v['tuned']['drift_detected']}/{v['tuned']['drift_runs']}, median delay {f3(v['tuned']['median_delay_s'])} s; existing FA {v['existing_default']['control_false_alarms']}/{v['existing_default']['control_runs']}")
    n9 = cs["milestone2_nine_controls"]
    L += ["", f"The nine drift-free controls from the Milestone-2 benchmark: existing configuration {n9['existing_default']['control_false_alarms']}/9 false alarms, tuned {n9['tuned']['control_false_alarms']}/9. {n9['note']}", "",
          "Missed and delayed test drift detections:", ""]
    for r in t["runs"]:
        if r["drift"]:
            L.append(f"- `{r['experiment_id']}` rate {r['rate']:.3g}/s: {'detected after ' + f3(r['delay_s']) + ' s' if r['detected'] else ('PRE-ONSET ALARM' if r['false_alarm'] else 'missed')}")
    bd = cs["baseline_estimation_diagnostics"]
    L += ["", f"**Why h had to be large.** On the {bd['tuning_controls']} tuning controls, the whole-run σ exceeds the baseline-window σ by a median factor {bd['sd_ratio_median']:.2f} (max {bd['sd_ratio_max']:.2f}), and the run mean differs from the baseline mean by a median {bd['mean_offset_sigma_median']:.2f}σ (max {bd['mean_offset_sigma_max']:.2f}σ). "
          f"A persistent target error of 0.3σ reduces the ARL0 of k=0.5, h=10 from ~7e4 to {bd['arl0_k0.5_h10_if_target_off_by_0.3_sigma']:.0f} samples; for the selected configuration it gives {bd['arl0_selected_if_target_off_by_0.3_sigma']:.3g}. "
          "Parameter-estimation error from short baselines, not the CUSUM recursion itself, drives the empirical false alarms. The selected h lies on the upper grid boundary; larger h could only reduce detections, so it would not change the selection.", ""]
    L += ["## 7. Post-hoc diagnostics (computed after the single test evaluation; models and thresholds unchanged)", "",
          f"**Spike latency.** At the spike sample a causal detector cannot distinguish a spike from the first sample of a genuine step or set-point change; the distinction appears one sample later. The trained models were not given that opportunity: training labels mark only the spike sample, so a tolerance window adds little and large spikes are still missed. Training on a confirm-at-k+1 target is a candidate change that must be validated on a fresh test seed root. Alarms at the spike sample vs. within {CFG['posthoc_spike_latency_tolerance_samples']} samples after it (test):", "",
          "| Measurand | Detector | Spikes | Alarm at spike | Alarm within tolerance | Missed spike magnitudes (σ) |", "|---|---|---|---|---|---|"]
    for m in CFG["measurands"]:
        for d in DETECTORS:
            sp = R["signal"][m]["test_posthoc_spike_latency"][d]
            L.append(f"| {m} | {DET_LABEL[d]} | {sp['events']} | {sp['alarm_at_spike']} | {sp['alarm_within_tolerance']} | {sp['missed_magnitudes_sigma']} |")
    L += ["", f"**Fault aftermath.** The `post_fault_aftermath` context in §4 counts fault-free records within {CFG['post_fault_aftermath_samples']} samples after a labelled fault. Alarms there are mostly the window features still \"seeing\" the fault. They are counted as false alarms at record level, but they are a different failure mode from alarms on clean operation.", ""]
    L += ["## 8. Model settings", ""]
    for m in CFG["measurands"]:
        s = R["signal"][m]["selection"]
        L.append(f"- {m}: GBT {s['gbt']['params']} (threshold {s['gbt']['threshold']:.4g}); Isolation Forest {s['iforest']['params']} (threshold {s['iforest']['threshold']:.4g}, trained on {s['iforest']['training_records']} fault-free records); feature noise floor {s['feature_floor']:.4g}")
    L += ["", "## 9. Verdict", "", *R["verdict"], "", "## 10. Limitations", "", *[f"- {x}" for x in R["limitations"]], ""]
    path.write_text("\n".join(L), encoding="utf-8")


# ==============================================================================
# Main
# ==============================================================================

def main():
    global CFG
    CFG = load_json(WORKSPACE_ROOT / "config" / "ml_fault_detection_config.json")
    base_cfg = load_json(WORKSPACE_ROOT / "config" / "default_config.json")
    suite_cfg = load_json(WORKSPACE_ROOT / "config" / "synthetic_suite_config.json")
    for sub in ("models", "plots", "predictions", "config"):
        (OUT / sub).mkdir(parents=True, exist_ok=False if sub == "models" else True)
    shutil.copy(WORKSPACE_ROOT / "config" / "ml_fault_detection_config.json", OUT / "config")

    manifest_bytes = (DATA_ROOT / "metadata" / "suite_manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    frames, metas = {}, {}
    for f in manifest["files"]:
        raw = (DATA_ROOT / f["csv_file"]).read_bytes()
        if _sha256_bytes(raw) != f["csv_sha256"]:
            print("ABORT: dataset differs from manifest:", f["csv_file"])
            return 1
        frames[f["scenario_id"]] = pd.read_csv(DATA_ROOT / f["csv_file"])
        metas[f["scenario_id"]] = load_json(DATA_ROOT / f["metadata_file"])
    print(f"Loaded {len(frames)} scenarios (checksums verified).")

    R = {"run_info": {"command": "python scripts/run_ml_fault_detection.py", "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                      "output_dir": str(OUT.relative_to(WORKSPACE_ROOT)), "suite_manifest_sha256": _sha256_bytes(manifest_bytes),
                      "versions": {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__,
                                   "scipy": scipy.__version__, "scikit_learn": sklearn.__version__},
                      "features": FEATURE_NAMES, "feature_definitions": FEATURE_DEFINITIONS, "noise_scale": NOISE_SCALE_DEFINITION,
                      "integrity_rule_issue_types": list(INTEGRITY_ISSUE_TYPES),
                      "disclaimer": "Synthetic data only; no physical sensor accuracy is claimed.", "split_integrity_verified": True},
         "signal": {}, "integrity": {}}

    for m in CFG["measurands"]:
        fr = {sid: df for sid, df in frames.items() if metas[sid]["measurand"] == m}
        cal_rows = pd.concat([df[df.partition == "calibration"] for df in fr.values()], ignore_index=True)
        builder = CausalFeatureBuilder(m, floor_fraction=CFG["feature_floor_fraction"]).fit(cal_rows)
        sig, integ = build_signal_dataset(fr, m, builder)
        parts = {p: sig[sig.partition == p].reset_index(drop=True) for p in ("calibration", "validation", "test")}
        ids = {p: set(v.experiment_id) for p, v in parts.items()}
        assert not (ids["calibration"] & ids["validation"]) and not (ids["calibration"] & ids["test"]) and not (ids["validation"] & ids["test"])
        events = [e for sid in fr for e in metas[sid]["fault_events"] if e["fault_type"] in SIGNAL_FAULT_TYPES]
        transient = CFG["post_event_transient_samples"][m]
        print(f"[{m}] records: train {len(parts['calibration'])}, val {len(parts['validation'])}, test {len(parts['test'])}; floor {builder.floor:.4g}")

        gbt, gbt_trials = select(GBTDetector, CFG["gbt_grid"], parts["calibration"], parts["validation"], events, transient, metas)
        ifo, if_trials = select(IsolationForestDetector, CFG["iforest_grid"], parts["calibration"], parts["validation"], events, transient, metas)
        base_flags = segment_baseline_flags(fr, m, base_cfg)

        R["signal"][m] = {"records": {p: int(len(v)) for p, v in parts.items()},
                          "runs": {p: len(v) for p, v in ids.items()},
                          "selection": {"gbt": {"params": gbt.params, "threshold": gbt.threshold, "trials": gbt_trials},
                                        "iforest": {"params": ifo.params, "threshold": ifo.threshold, "trials": if_trials,
                                                    "training_records": ifo.training_records},
                                        "feature_floor": builder.floor, "feature_fit": builder.fit_info},
                          "validation": {}, "test": {}}
        for p in ("validation", "test"):
            df = parts[p]
            preds = {"gbt": gbt.score(df) > gbt.threshold, "iforest": ifo.score(df) > ifo.threshold,
                     "baseline": np.array([base_flags[(e, int(s))] for e, s in zip(df.experiment_id, df.sequence_number)])}
            for d in DETECTORS:
                far = binary_metrics(preds[d], df["is_signal_fault"].to_numpy())["false_alarm_rate"]
                R["signal"][m][p][d] = evaluate(preds[d], df, events, transient, far, metas)
            if p == "test":
                dev = suite_cfg["devices"][metas[next(iter(fr))]["sensor_error_model"]["device_id"]]
                sigma = dev.get("noise_std", dev.get("adc_noise_std_mV", 0) / dev.get("r_shunt_nominal_ohm", 1))
                R["signal"][m]["test_posthoc_spike_latency"] = {
                    d: posthoc_spike_latency(preds[d], df, events, sigma, CFG["posthoc_spike_latency_tolerance_samples"]) for d in DETECTORS}
                out = df[["scenario_id", "experiment_id", "sequence_number", "protocol_phase", "signal_fault_type", "label_process_event"]].copy()
                out["gbt_score"] = gbt.score(df); out["iforest_score"] = ifo.score(df)
                for d in DETECTORS:
                    out[f"{d}_alarm"] = preds[d]
                out.to_csv(OUT / "predictions" / f"{m}_test_predictions.csv", index=False)
        R["integrity"][m] = {p: integrity_eval(integ[integ.partition == p]) for p in ("validation", "test")}
        joblib.dump({"feature_builder": builder, "detector": gbt, "features": FEATURE_NAMES}, OUT / "models" / f"{m}_gbt.joblib")
        joblib.dump({"feature_builder": builder, "detector": ifo, "features": FEATURE_NAMES}, OUT / "models" / f"{m}_iforest.joblib")

    # Temperature ramp / lag-transient investigation
    pr = pd.read_csv(OUT / "predictions" / "temperature_C_test_predictions.csv")
    neg = pr[pr.signal_fault_type == "none"]
    tab = neg.groupby(["scenario_id", "protocol_phase"])[[f"{d}_alarm" for d in DETECTORS]].mean().reset_index()
    counts = neg.groupby(["scenario_id", "protocol_phase"]).size().rename("records").reset_index()
    tab = tab.merge(counts, on=["scenario_id", "protocol_phase"])
    tab.to_csv(OUT / "predictions" / "temperature_false_alarm_by_scenario_phase.csv", index=False)
    worst = tab.sort_values("baseline_alarm", ascending=False).head(5)
    rows = "; ".join(f"{r.scenario_id}/{r.protocol_phase}: conventional {100*r.baseline_alarm:.1f} %, GBT {100*r.gbt_alarm:.1f} %, IF {100*r.iforest_alarm:.1f} % (n={r.records})" for r in worst.itertuples())
    R["temperature_transient_investigation"] = {
        "table_file": "predictions/temperature_false_alarm_by_scenario_phase.csv",
        "summary": ("**Temperature transients.** Highest conventional false-alarm rates by scenario/phase (test): " + rows +
                    ". The conventional per-segment MAD treats each ramp or post-step lag segment as if it were a stationary level, so the trend itself exceeds the MAD threshold; the causal ML features normalise by a past first-difference noise scale, which a smooth ramp does not inflate."),
    }

    cs = cusum_study(frames, metas, suite_cfg)
    R["cusum"] = cs

    # Verdict strictly from test numbers
    verdict = []
    for m in CFG["measurands"]:
        T = R["signal"][m]["test"]
        mer = {d: macro_event_recall(T[d]["events"]) for d in DETECTORS}
        far = {d: T[d]["overall"]["false_alarm_rate"] for d in DETECTORS}
        best = max(mer, key=mer.get)
        verdict.append(f"- {m}: macro event recall (test) GBT {mer['gbt']:.2f}, IF {mer['iforest']:.2f}, conventional {mer['baseline']:.2f}; "
                       f"record FAR GBT {far['gbt']:.4f}, IF {far['iforest']:.4f}, conventional {far['baseline']:.4f}. Highest event recall: {DET_LABEL[best]}.")
        R["signal"][m]["test_macro_event_recall"] = mer
    verdict.append(f"- CUSUM: tuned configuration {cs['tuned_on_test']['control_false_alarms']}/{cs['tuned_on_test']['control_runs']} false alarms and "
                   f"{cs['tuned_on_test']['drift_detected']}/{cs['tuned_on_test']['drift_runs']} drift runs detected on test, versus "
                   f"{cs['existing_default_on_test']['control_false_alarms']}/{cs['existing_default_on_test']['control_runs']} false alarms for the existing configuration.")
    verdict.append("- Statements of superiority apply only to these synthetic test runs and the documented fault model; small event counts (2–10 per class per measurand) give wide uncertainty on every recall figure.")
    R["verdict"] = verdict
    R["limitations"] = [
        "All data are synthetic; the fault generator and the detectors share the same simulated noise model, which favours learned detectors.",
        "Event counts per class and measurand in the test partition are small (2 for persistent classes, 4–10 for transient classes); a 95 % interval on a recall of 2/2 spans roughly 0.16–1.0.",
        "Offset, gain and drift faults are fundamentally ambiguous from a single DUT signal (indistinguishable from genuine process changes); detection near onset relies on the step/slope signature only.",
        "Stuck temperature signals are partly unobservable because coarse quantisation makes identical consecutive readings normal on plateaus.",
        "Thresholds are set for a 0.5 % validation false-alarm rate; test FAR can differ, and other operating points trade recall for false alarms.",
        "The conventional baseline uses protocol segment boundaries and non-causal per-segment statistics; it is not an online detector.",
        "The CUSUM error series uses the reference instrument and a static calibration; it is a laboratory-verification setting, not reference-free field monitoring.",
        "The ML models are research artefacts; they are not integrated into the application or the R1–R5 decision engine.",
    ]

    plot_event_recall(R["signal"], OUT / "plots" / "event_recall_by_class.png")
    plot_false_alarms(R["signal"], OUT / "plots" / "false_alarms_by_context.png")
    plot_cusum(cs, OUT / "plots" / "cusum_tuning.png")

    for m in CFG["measurands"]:
        for p in ("validation", "test"):
            for d in DETECTORS:
                R["signal"][m][p][d].pop("event_list", None) if p == "validation" else None
    with open(OUT / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(jsonable(R), f, indent=2)
    write_report(R, OUT / "REPORT.md")
    print(f"\nOutput: {OUT}")
    for line in verdict:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
