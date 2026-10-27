#!/usr/bin/env python3
"""
IMUCA Milestone 6: hybrid-detector improvement loop (synthetic data only).

Stages
  validate  --profile P --tag T   Develop/select on v3 calibration+validation runs only; writes a
                                  cycle report to results/hybrid_dev_cycles_20261026/<T>/.
  freeze    --profile P           Same selection, then writes results/hybrid_frozen_<timestamp>/ with
                                  frozen settings, models, selection records and source-code hashes.
  final     --frozen DIR --suite-config CFG --data-root ROOT
                                  Verifies code hashes, refuses to re-score an already evaluated
                                  (bundle, suite) pair, scores the fresh suite's test runs ONCE and
                                  writes results/hybrid_final_<timestamp>/.

No stage reads the v3 test partition.
"""

import argparse
import hashlib
import json
import os
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
from src.imuca.ml_features import CausalFeatureBuilder, build_signal_dataset, integrity_rule_flags, SIGNAL_FAULT_TYPES, INTEGRITY_FAULT_TYPES
from src.imuca.ml_fault_detection import GBTDetector, IsolationForestDetector, TargetedGBTDetector
from src.imuca.detection_metrics import (binary_metrics, threshold_at_false_alarm_rate, alarm_episodes, classify_episodes,
                                         wilson_interval)
from src.imuca.hybrid_detector import (HybridDetector, HybridSettings, combine, drift_component, drift_usable,
                                       setpoint_change_positions, stuck_rule_flags, transient_flags, NONSTATIONARY_PHASES,
                                       STUCK_EVIDENCE_RUN)
from src.imuca.hybrid_evaluation import (EvalSet, quick_score, full_eval, classification_accuracy, lifecycle_stats,
                                         event_strata, TRANSIENT_CLASSES, PERSISTENT_STUCK_CLASSES)
from src.imuca.cusum_tuning import siegmund_arl_two_sided, cusum_max_statistic, first_crossings

CYCLE_ROOT = WORKSPACE_ROOT / "results" / "hybrid_dev_cycles_20261027"
SCORE_BASE = 2.5   # segment scores computed once at this MAD threshold; any threshold >= SCORE_BASE is then exact
CODE_FILES = ["src/imuca/hybrid_detector.py", "src/imuca/hybrid_evaluation.py", "src/imuca/ml_features.py",
              "src/imuca/ml_fault_detection.py", "src/imuca/detection_metrics.py", "src/imuca/cusum_tuning.py",
              "src/imuca/data_quality.py", "src/imuca/validation.py", "src/imuca/calibration.py",
              "scripts/run_hybrid_iteration.py", "config/hybrid_iteration_config.json"]
DETECTORS = ("hybrid_m7", "hybrid_m6", "hybrid_m5", "segment_setpoint", "gbt_all", "iforest", "gbt_persistent", "stuck_rule", "curvature", "cusum")
LABEL = {"hybrid_m7": "Hybrid M7 (iterated)", "hybrid_m6": "Hybrid M6 (frozen)", "hybrid_m5": "Hybrid M5 (frozen)",
         "segment_setpoint": "Segment detector (existing)", "gbt_all": "GBT (all faults)",
         "iforest": "Isolation Forest", "gbt_persistent": "Targeted GBT",
         "stuck_rule": "Stuck rule", "curvature": "Curvature detector", "cusum": "Tuned CUSUM"}


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


def profile(cfg, name):
    p = dict(cfg["profiles"][name])
    if "extends" in p:
        base = profile(cfg, p.pop("extends"))
        base.update(p)
        return base
    return p


def code_hashes():
    return {f: _sha256_bytes((WORKSPACE_ROOT / f).read_bytes()) for f in CODE_FILES}


def load_suite(root):
    manifest_bytes = (root / "metadata" / "suite_manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    frames, metas = {}, {}
    for f in manifest["files"]:
        if _sha256_bytes((root / f["csv_file"]).read_bytes()) != f["csv_sha256"]:
            raise SystemExit(f"checksum mismatch: {f['csv_file']}")
        frames[f["scenario_id"]] = pd.read_csv(root / f["csv_file"])
        metas[f["scenario_id"]] = load_json(root / f["metadata_file"])
    return manifest, _sha256_bytes(manifest_bytes), frames, metas


def noise_ranks(devices):
    ranks = {}
    for m in ("voltage_V", "current_mA", "temperature_C"):
        devs = [(d, p.get("noise_std", p.get("adc_noise_std_mV", 0) / p.get("r_shunt_nominal_ohm", 1))) for d, p in devices.items() if p["measurand"] == m]
        for i, (d, _) in enumerate(sorted(devs, key=lambda t: t[1])):
            ranks[d] = ("noise_low", "noise_mid", "noise_high")[min(i, 2)] if len(devs) >= 3 else "noise_single"
    return ranks


# ==============================================================================
# Training / component preparation (v3 calibration)
# ==============================================================================

def prepare(m, frames, metas, CFG, base_cfg, suite_cfg):
    fr = {sid: df for sid, df in frames.items() if metas[sid]["measurand"] == m}
    dev_of = {sid: metas[sid]["sensor_error_model"]["device_id"] for sid in fr}
    builder = CausalFeatureBuilder(m).fit(pd.concat([df[df.partition == "calibration"] for df in fr.values()], ignore_index=True))
    sig, _ = build_signal_dataset({k: v[v.partition == "calibration"] for k, v in fr.items()}, m, builder)
    events = [dict(e) for sid in fr for e in metas[sid]["fault_events"] if e["fault_type"] in SIGNAL_FAULT_TYPES]
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
    gp = CFG["gbt_persistent"]
    cands = [TargetedGBTDetector(params=p, seed=CFG["random_seed"], target_types=tuple(gp["target_types"]),
                                 excluded_types=tuple(gp["excluded_types"]), onset_window=gp["onset_window_samples"],
                                 persistent_types=tuple(gp["persistent_types"]), monotone_increasing=tuple(gp["monotone_increasing"])).fit(sig.reset_index(drop=True), onset_seq)
             for p in gp["grid"]]
    info = {}
    ranks = noise_ranks(suite_cfg["devices"])
    for sid in fr:
        info.update(event_strata(metas[sid], suite_cfg["devices"], ranks))
    return {"fr": fr, "dev_of": dev_of, "builder": builder, "sig": sig.reset_index(drop=True), "events": events,
            "cal_models": cal_models, "cands": cands, "event_info": info}


def components(P, m, partition, base_cfg, cache_tag=None):
    cache = None
    if cache_tag:
        key = hashlib.sha256(("|".join(code_hashes()[f] for f in CODE_FILES[:9]) + m + partition + cache_tag).encode()).hexdigest()[:20]
        cache = Path(os.environ.get("TEMP", "/tmp")) / "imuca_m6_cache" / f"{m}_{partition}_{key}.joblib"
        if cache.exists():
            return joblib.load(cache)
    template = HybridSettings("setpoint_blocks", "rule", 1.0, 1e-4, 0.5, 15.0)
    out = []
    for sid, df in P["fr"].items():
        dev = P["dev_of"][sid]
        hd = HybridDetector(m, P["builder"], None, P["cal_models"].get(dev), base_cfg, template, score_cache=True,
                            score_base_threshold=SCORE_BASE)
        for _, run in df[df.partition == partition].groupby("experiment_id", sort=False):
            out.append(hd.components(run))
    if cache is not None:
        cache.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(out, cache)
    return out


# ==============================================================================
# CUSUM tuning (fast, equivalent to analyze_temporal_drift's CUSUM; tested)
# ==============================================================================

def cusum_series(P, m, partitions):
    series = []
    for sid, df in P["fr"].items():
        dev = P["dev_of"][sid]
        if dev not in P["cal_models"]:
            continue
        meta_ev = [e for e in P["events"] if e["fault_type"] == "gradual_drift"]
        for exp_id, run in df[df.partition.isin(partitions)].groupby("experiment_id", sort=False):
            run = run.reset_index(drop=True)
            flags, _ = integrity_rule_flags(run, m)
            clean = run.loc[~flags].reset_index(drop=True)
            types = {t for s in clean["label_fault_type"] for t in s.split(";") if t in SIGNAL_FAULT_TYPES}
            if types and types != {"gradual_drift"}:
                continue
            err = P["cal_models"][dev].predict(clean[m].to_numpy(float)) - clean[f"reference_{m}"].to_numpy(float)
            ev = [e for e in meta_ev if e["run_id"] == exp_id]
            series.append({"err": err, "seq": clean["sequence_number"].to_numpy(),
                           "di": {"finite": np.isfinite(err), "protocol": clean[["setpoint_index", "protocol_phase", "sequence_number"]]},
                           "segment_starts": setpoint_change_positions(clean), "drift": bool(ev),
                           "onset": ev[0]["onset_sequence_number"] if ev else None, "n": int(np.isfinite(err).sum()),
                           "experiment_id": exp_id})
    return series


def tune_cusum(series, cc, windows):
    longest = max(s["n"] for s in series)
    min_arl = cc["min_arl0_multiple_of_longest_series"] * longest
    acc = {}
    for mode in cc["modes"]:
        for w in windows:
            for s in series:
                usable = drift_usable(s["di"], w)
                n = len(s["err"])
                if mode == "segment" and len(s["segment_starts"]):
                    cuts = [0, *[int(x) for x in s["segment_starts"]], n]
                    bounds = [(a, b) for a, b in zip(cuts[:-1], cuts[1:]) if b > a]
                else:
                    bounds = [(0, n)]
                for mb in cc["min_baseline"]:
                    subs = []
                    for a, b in bounds:
                        idx = np.flatnonzero(usable[a:b]) + a
                        if len(idx) < 3:
                            continue
                        nb = max(mb, int(len(idx) * cc["baseline_fraction"]))
                        base = s["err"][idx[:nb]]
                        if len(base) < 2 or not np.std(base, ddof=1) > 0:
                            continue
                        subs.append((idx, float(np.mean(base)), float(np.std(base, ddof=1))))
                    for k in cc["k"]:
                        crossings = []
                        for idx, tgt, sg in subs:
                            fc = first_crossings(cusum_max_statistic(s["err"][idx], tgt, sg, k), cc["h"])
                            crossings.append((len(idx), {h: (None if v is None else int(s["seq"][idx[v]])) for h, v in fc.items()}))
                        for ms in cc["min_series"]:
                            for h in cc["h"]:
                                seqs = [c[h] for n_i, c in crossings if n_i >= ms and c[h] is not None]
                                first = min(seqs) if seqs else None
                                a = acc.setdefault((mode, w, mb, ms, k, h), {"fa": 0, "pre": 0, "det": 0, "delays": []})
                                if first is None:
                                    continue
                                if not s["drift"]:
                                    a["fa"] += 1
                                elif first < s["onset"]:
                                    a["pre"] += 1
                                else:
                                    a["det"] += 1
                                    a["delays"].append(first - s["onset"])
    grid = []
    for (mode, w, mb, ms, k, h), a in acc.items():
        arl = siegmund_arl_two_sided(k, h)
        grid.append({"mode": mode, "window": w, "min_baseline": mb, "min_series": ms, "k": k, "h": h, "arl0": arl,
                     "arl0_ok": arl >= min_arl, "false_alarms": a["fa"], "pre_onset": a["pre"], "detected": a["det"],
                     "median_delay": float(np.median(a["delays"])) if a["delays"] else None})
    ok = [g for g in grid if g["arl0_ok"]] or grid
    best = sorted(ok, key=lambda g: (g["false_alarms"] + g["pre_onset"], -g["detected"],
                                     g["median_delay"] if g["median_delay"] is not None else 1e9, -g["arl0"],
                                     g["window"], g["min_baseline"], g["min_series"]))[0]
    return best, grid, {"controls": sum(not s["drift"] for s in series), "drift_runs": sum(s["drift"] for s in series),
                        "longest_series": longest, "min_arl0": min_arl}


# ==============================================================================
# Hybrid assembly helpers
# ==============================================================================

def settings_from(sel, cfg_cusum_best, overrides=None):
    d = dict(segment_mode=sel["segment_mode"], stuck_mode=sel["stuck_mode"], gbt_threshold=sel["gbt_threshold"],
             stuck_alpha=sel["stuck_alpha"], cusum_k=cfg_cusum_best["k"], cusum_h=cfg_cusum_best["h"],
             cusum_baseline_fraction=0.1, cusum_min_baseline=cfg_cusum_best["min_baseline"],
             cusum_min_series=cfg_cusum_best["min_series"], transition_exclusion=cfg_cusum_best["window"],
             cusum_mode=cfg_cusum_best["mode"], segment_mad_threshold=sel["mad"], episode_gap=2)
    d.update(sel.get("extra", {}))
    d.update(overrides or {})
    return HybridSettings(**d)


def run_hybrid(comps, scores, st):
    res = [combine(transient_flags(c, st), stuck_rule_flags(c["features"], st.stuck_alpha), sc > st.gbt_threshold,
                   c["identical_run"], c.get("drift_inputs"), st, c["experiment_id"], c.get("signal"))
           for c, sc in zip(comps, scores)]
    return np.concatenate([r["alarm"] for r in res]), np.concatenate([r["category"] for r in res])


def persistent_stuck_alarm(comps, scores, thr, stuck_mode, alpha, suppress_nonstat=False):
    out = []
    for c, sc in zip(comps, scores):
        g = sc > thr
        ev = c["identical_run"] >= STUCK_EVIDENCE_RUN
        if suppress_nonstat:
            g = g & (ev | ~np.isin(c["signal"]["protocol_phase"], NONSTATIONARY_PHASES))
        rule = stuck_rule_flags(c["features"], alpha)
        stuck = {"gbt": g & ev, "rule": rule, "gbt_or_rule": rule | (g & ev)}[stuck_mode]
        out.append((g & ~ev) | stuck)
    return np.concatenate(out)


def context_fa(alarm, E):
    eps = alarm_episodes(alarm, E.exp, E.gap)
    true = classify_episodes(eps, E.active)
    neg = ~E.truth
    phase = E.df["protocol_phase"].to_numpy()
    out = {}
    for name, mask in (("ramp", np.isin(phase, ("ramp", "heating_ramp", "cooling_ramp"))),
                       ("settling", phase == "plateau_settling"),
                       ("post_event_transient", E.context == "post_event_transient"),
                       ("steady", E.context == "steady")):
        expo = float(np.sum(mask & neg)) / 3600.0
        n = sum(1 for e, t in zip(eps, true) if not t and mask[e["start"]])
        out[name] = {"hours": expo, "false_alarms": n, "per_hour": n / expo if expo else None}
    return out


def spike_recall_by_phase(alarm, E):
    from src.imuca.detection_metrics import detect_with_windows
    det = detect_with_windows(alarm, E.windows, E.seq)
    phase = E.df["protocol_phase"].to_numpy()
    out = {"stationary": [0, 0], "nonstationary": [0, 0]}
    for d, w in zip(det, E.windows):
        if d["fault_type"] != "isolated_spike":
            continue
        grp = "nonstationary" if phase[w["positions"][0]] in NONSTATIONARY_PHASES else "stationary"
        out[grp][0] += d["detected"]; out[grp][1] += 1
    return {k: {"detected": v[0], "events": v[1], "recall": v[0] / v[1] if v[1] else None} for k, v in out.items()}


def select_threshold_detector(cls, grid, train, feats_val, E_val, far_target, seed):
    best, trials = None, []
    for params in grid:
        det = cls(params=params, seed=seed).fit(train)
        s = det.score(feats_val)
        thr = threshold_at_false_alarm_rate(s, E_val.truth, far_target)
        q = quick_score(s > thr, E_val)
        trials.append({"params": params, "threshold": thr, **q})
        key = (q["macro_event_recall"], q["event_f1"])
        if best is None or key > best[0]:
            det.threshold = thr
            best = (key, det)
    return best[1], trials


# ==============================================================================
# Selection on validation (shared by validate and freeze)
# ==============================================================================

def develop(CFG, prof, base_cfg, suite_cfg, frames, metas, cache_tag):
    out, state = {}, {}
    m5_dir = WORKSPACE_ROOT / CFG["m5_bundle_dir"]
    for m in CFG["measurands"]:
        print(f"[{m}] preparing (v3 calibration) ...", flush=True)
        P = prepare(m, frames, metas, CFG, base_cfg, suite_cfg)
        comps = components(P, m, "validation", base_cfg, cache_tag)
        E = EvalSet(comps, P["events"], CFG, m, P["event_info"])
        feats = pd.concat([c["features"] for c in comps], ignore_index=True)
        cand_scores = [[cand.score(c["features"]) for c in comps] for cand in P["cands"]]

        # --- CUSUM (calibration + validation runs)
        series = cusum_series(P, m, ["calibration", "validation"])
        c_best, c_grid, c_runs = tune_cusum(series, prof["cusum"], prof["cusum"]["windows"][m])
        print(f"[{m}] CUSUM {dict((k, c_best[k]) for k in ('mode', 'window', 'min_baseline', 'min_series', 'k', 'h', 'false_alarms', 'pre_onset', 'detected'))}", flush=True)

        # --- transient component
        trans_trials = []
        for seg in prof["segment_modes"]:
            for mad in prof["mad_grid"]:
                for extra in [dict(x, transient_transition_window=w, settling_suppression=sup)
                              for x in prof["transient_extra"]
                              for w in prof.get("transient_transition_windows", [0])
                              for sup in prof.get("settling_suppression", [False])]:
                    st = HybridSettings(seg, "rule", 1.0, CFG["stuck_rule_alpha"], 0.5, 15.0, segment_mad_threshold=mad, **extra)
                    alarm = np.concatenate([transient_flags(c, st) for c in comps])
                    q = quick_score(alarm, E, TRANSIENT_CLASSES)
                    q.update({"segment_mode": seg, "mad": mad, "extra": extra, "context_fa": context_fa(alarm, E),
                              "spike_recall_by_phase": spike_recall_by_phase(alarm, E)})
                    trans_trials.append(q)
        t_best = sorted(trans_trials, key=lambda q: (-round(q["event_f1"], 6), q["false_alarms_per_hour"]))[0]

        # --- persistent + stuck component
        ps_trials = []
        all_val_scores = [np.concatenate(s) for s in cand_scores]
        for ci, sc in enumerate(cand_scores):
            for far in CFG["gbt_persistent"]["far_targets"]:
                thr = threshold_at_false_alarm_rate(all_val_scores[ci], E.truth, far)
                for sm, sup in [(a, b) for a in prof["stuck_modes"] for b in prof.get("suppress_persistent_nonstationary", [False])]:
                    alarm = persistent_stuck_alarm(comps, sc, thr, sm, CFG["stuck_rule_alpha"], sup)
                    q = quick_score(alarm, E, PERSISTENT_STUCK_CLASSES)
                    q.update({"candidate": ci, "far_target": far, "threshold": thr, "stuck_mode": sm, "suppress_nonstat": sup})
                    ps_trials.append(q)
        p_best = sorted(ps_trials, key=lambda q: (-round(q["event_f1"], 6), q["false_alarms_per_hour"]))[0]

        # --- joint refinement: top transient x top persistent candidates on the FULL hybrid objective
        kt, kp = CFG["joint_top_k"]["transient"], CFG["joint_top_k"]["persistent"]
        top_t = sorted(trans_trials, key=lambda q: (-round(q["event_f1"], 6), q["false_alarms_per_hour"]))[:kt]
        top_p = sorted(ps_trials, key=lambda q: (-round(q["event_f1"], 6), q["false_alarms_per_hour"]))[:kp]
        joint = []
        for tt in top_t:
            for pp in top_p:
                sel_j = {"segment_mode": tt["segment_mode"], "mad": tt["mad"], "extra": dict(tt["extra"], suppress_persistent_nonstationary=pp["suppress_nonstat"]),
                         "stuck_mode": pp["stuck_mode"], "gbt_threshold": pp["threshold"], "stuck_alpha": CFG["stuck_rule_alpha"]}
                alarm, _ = run_hybrid(comps, cand_scores[pp["candidate"]], settings_from(sel_j, c_best, {"drift_lifecycle": "latched", "attribution": "first_alarm"}))
                q = quick_score(alarm, E)
                joint.append({**q, "transient": {k: tt[k] for k in ("segment_mode", "mad", "extra")},
                              "persistent": {k: pp[k] for k in ("candidate", "far_target", "threshold", "stuck_mode", "suppress_nonstat")}})
        j_best = sorted(joint, key=lambda q: (-round(q["event_f1"], 6), q["false_alarms_per_hour"]))[0]
        t_best = next(t for t in trans_trials if all(t[k] == j_best["transient"][k] for k in ("segment_mode", "mad", "extra")))
        p_best = next(t for t in ps_trials if all(t[k] == j_best["persistent"][k] for k in ("candidate", "far_target", "stuck_mode", "suppress_nonstat")))
        sel = {"segment_mode": t_best["segment_mode"], "mad": t_best["mad"],
               "extra": dict(t_best["extra"], suppress_persistent_nonstationary=p_best["suppress_nonstat"]),
               "stuck_mode": p_best["stuck_mode"], "gbt_threshold": p_best["threshold"], "stuck_alpha": CFG["stuck_rule_alpha"]}
        scores = cand_scores[p_best["candidate"]]

        # --- lifecycle (full hybrid, first-alarm attribution)
        lc_trials = []
        for lc in prof["lifecycle"]:
            st = settings_from(sel, c_best, dict(lc, attribution="first_alarm"))
            alarm, _ = run_hybrid(comps, scores, st)
            q = quick_score(alarm, E)
            q.update({"lifecycle": lc, "overhang": lifecycle_stats(alarm, E)})
            lc_trials.append(q)
        top_f1 = max(q["event_f1"] for q in lc_trials)
        near = [q for q in lc_trials if q["event_f1"] >= top_f1 - CFG["lifecycle_f1_tolerance"]]
        def lc_sort_key(q):
            is_latched = 1 if q["lifecycle"].get("drift_lifecycle") == "latched" else 0
            return (q["overhang"]["true_episode_overhang_samples_total"], q["false_alarms_per_hour"], is_latched, -round(q["event_f1"], 6))
        l_best = sorted(near, key=lc_sort_key)[0]
        # --- attribution (alarms unchanged; maximise classification accuracy)
        at_trials = []
        for at in prof["attribution"]:
            st = settings_from(sel, c_best, dict(l_best["lifecycle"], **at))
            alarm, cat = run_hybrid(comps, scores, st)
            ca = classification_accuracy(alarm, cat, E)
            at_trials.append({"attribution": at, "accuracy": ca["accuracy"], "per_class": ca["per_class"]})
        def at_sort_key(t):
            acc = t["accuracy"] or 0.0
            is_first = 1 if t["attribution"].get("attribution") == "first_alarm" else 0
            return (-round(acc, 6), is_first, t["attribution"].get("confirm_delay", 0))
        a_best = sorted(at_trials, key=at_sort_key)[0]
        final_settings = settings_from(sel, c_best, dict(l_best["lifecycle"], **a_best["attribution"]))

        # --- individual detectors (for comparison) and M5 bundle
        train = P["sig"]
        gbt_all, gbt_trials = select_threshold_detector(GBTDetector, CFG["gbt_all_grid"], train, feats, E, CFG["individual_far_target"], CFG["random_seed"])
        ifo, if_trials = select_threshold_detector(IsolationForestDetector, CFG["iforest_grid"], train, feats, E, CFG["individual_far_target"], CFG["random_seed"])
        gbt_p = P["cands"][p_best["candidate"]]
        gbt_p.threshold = p_best["threshold"]
        m5 = joblib.load(m5_dir / "models" / f"{m}_detectors.joblib")
        m6_dir = WORKSPACE_ROOT / CFG.get("m6_bundle_dir", "results/hybrid_frozen_20261026_123033")
        m6 = joblib.load(m6_dir / "models" / f"{m}_detectors.joblib")
        for dev, mod in m5["calibration_models"].items():
            if dev in P["cal_models"]:
                assert np.allclose(mod.coefficients, P["cal_models"][dev].coefficients), "M5 calibration differs"
        assert m5["feature_builder"].floor == P["builder"].floor, "M5 feature floor differs"
        cusum_alone = settings_from(sel, c_best, {"drift_lifecycle": final_settings.drift_lifecycle,
                                                  "clear_window": final_settings.clear_window, "clear_z": final_settings.clear_z})
        detectors = {"P": P, "gbt_all": gbt_all, "iforest": ifo, "gbt_p": gbt_p, "m6": m6, "m5": m5, "settings": final_settings,
                     "cusum_settings": cusum_alone, "cusum_best": c_best}
        alarms, cat_m7, cat_m6, cat_m5 = score_all(comps, detectors, base_cfg)
        evals = {d: full_eval(alarms[d], E, cat_m7 if d == "hybrid_m7" else (cat_m6 if d == "hybrid_m6" else (cat_m5 if d == "hybrid_m5" else None)),
                              CFG["bootstrap_resamples"], CFG["random_seed"]) for d in DETECTORS}
        out[m] = {"selected_settings": final_settings.to_dict(), "gbt_persistent": {"params": gbt_p.params, "threshold": gbt_p.threshold,
                                                                                   "candidate": p_best["candidate"], "far_target": p_best["far_target"]},
                  "cusum": {"selected": c_best, "tuning_runs": c_runs,
                            "best_per_mode_window": best_per(c_grid, ("mode", "window"))},
                  "transient_trials": trans_trials, "transient_selected": t_best, "joint_trials": joint,
                  "persistent_stuck_trials": ps_trials, "persistent_stuck_selected": p_best,
                  "lifecycle_trials": lc_trials, "lifecycle_selected": l_best["lifecycle"],
                  "attribution_trials": at_trials, "attribution_selected": a_best["attribution"],
                  "gbt_all": {"params": gbt_all.params, "threshold": gbt_all.threshold, "trials": gbt_trials},
                  "iforest": {"params": ifo.params, "threshold": ifo.threshold, "trials": if_trials},
                  "validation": evals,
                  "validation_context_fa": {d: context_fa(alarms[d], E) for d in ("hybrid_m7", "hybrid_m6", "hybrid_m5", "segment_setpoint", "curvature")},
                  "validation_spike_by_phase": {d: spike_recall_by_phase(alarms[d], E) for d in ("hybrid_m7", "hybrid_m6", "hybrid_m5", "segment_setpoint")}}
        state[m] = detectors
        print(f"[{m}] validation event F1: M7 {evals['hybrid_m7']['event']['event_f1']:.3f} vs M6 {evals['hybrid_m6']['event']['event_f1']:.3f} vs M5 {evals['hybrid_m5']['event']['event_f1']:.3f}", flush=True)
    return out, state


def best_per(grid, keys):
    groups = {}
    for g in grid:
        groups.setdefault(tuple(g[k] for k in keys), []).append(g)
    return [sorted(v, key=lambda g: (not g["arl0_ok"], g["false_alarms"] + g["pre_onset"], -g["detected"],
                                     g["median_delay"] or 1e9))[0] for v in groups.values()]


def score_all(comps, D, base_cfg):
    """Alarm streams of every detector on the given components (aligned to integrity-clean records)."""
    m5 = D["m5"]
    m5_st = m5["hybrid_settings"]
    m6 = D.get("m6")
    m6_st = m6["hybrid_settings"] if m6 is not None else None
    alarms = {d: [] for d in DETECTORS}
    cat_m7, cat_m6, cat_m5 = [], [], []
    for c in comps:
        f = c["features"]
        r7 = combine(transient_flags(c, D["settings"]), stuck_rule_flags(f, D["settings"].stuck_alpha), D["gbt_p"].score(f) > D["gbt_p"].threshold,
                     c["identical_run"], c.get("drift_inputs"), D["settings"], c["experiment_id"], c.get("signal"))
        alarms["hybrid_m7"].append(r7["alarm"]); cat_m7.append(r7["category"])
        if m6 is not None:
            r6 = combine(transient_flags(c, m6_st), stuck_rule_flags(f, m6_st.stuck_alpha), m6["targeted_gbt"].score(f) > m6["targeted_gbt"].threshold,
                         c["identical_run"], c.get("drift_inputs"), m6_st, c["experiment_id"], c.get("signal"))
            alarms["hybrid_m6"].append(r6["alarm"]); cat_m6.append(r6["category"])
        r5 = combine(transient_flags(c, m5_st), stuck_rule_flags(f, m5_st.stuck_alpha), m5["targeted_gbt"].score(f) > m5["targeted_gbt"].threshold,
                     c["identical_run"], c.get("drift_inputs"), m5_st, c["experiment_id"], c.get("signal"))
        alarms["hybrid_m5"].append(r5["alarm"]); cat_m5.append(r5["category"])
        seg_default = HybridSettings("setpoint_blocks", "rule", 1.0, 1e-4, 0.5, 15.0, segment_mad_threshold=base_cfg["quality"]["mad_threshold"])
        alarms["segment_setpoint"].append(transient_flags(c, seg_default))
        alarms["gbt_all"].append(D["gbt_all"].score(f) > D["gbt_all"].threshold)
        alarms["iforest"].append(D["iforest"].score(f) > D["iforest"].threshold)
        alarms["gbt_persistent"].append(D["gbt_p"].score(f) > D["gbt_p"].threshold)
        alarms["stuck_rule"].append(stuck_rule_flags(f, D["settings"].stuck_alpha))
        curv_thr = D["settings"].curvature_threshold if D["settings"].transient_extra != "none" else 10.0
        alarms["curvature"].append(c["curvature_z"] > curv_thr)
        di = c.get("drift_inputs")
        cs = D["cusum_settings"]
        alarms["cusum"].append(drift_component(di["t_s"], di["err"], drift_usable(di, cs.transition_exclusion), [], cs, di["segment_starts"])
                               if di is not None else np.zeros(len(f), bool))
    return ({d: np.concatenate(v) for d, v in alarms.items()},
            np.concatenate(cat_m7),
            np.concatenate(cat_m6) if cat_m6 else None,
            np.concatenate(cat_m5))


# ==============================================================================
# Reports
# ==============================================================================

def f3(x, nd=3):
    if x is None:
        return "–"
    return f"{x:.{nd}f}" if isinstance(x, (float, np.floating)) else str(x)


def ci(t, nd=2):
    return "–" if t is None or t[0] is None else f"[{t[0]:.{nd}f}, {t[1]:.{nd}f}]"


def overall_table(R, key, dets):
    L = ["| Measurand | Detector | Event F1 [CI] | Macro recall | Episode precision | FA/h [CI] | Missed | Class. accuracy | Post-fault alarm records/h | Median delay |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for m, v in R.items():
        for d in dets:
            r = v[key][d]
            e = r["event"]
            ca = r.get("classification", {}).get("accuracy")
            L.append(f"| {m} | {LABEL[d]} | {f3(e['event_f1'])} {ci(e['event_f1_ci95_run_bootstrap'])} | {f3(e['macro_recall'])} | {f3(e['episode_precision'])} | "
                     f"{f3(e['false_alarms_per_hour'], 1)} {ci(e['false_alarms_per_hour_ci95'], 1)} | {e['missed_events']} | {f3(ca)} | "
                     f"{f3(r['lifecycle']['alarm_records_after_fault_end_per_hour'], 1)} | {f3(e['median_delay_samples_non_drift'], 0)} |")
    return L


def per_class_table(R, key, dets):
    L = []
    for m, v in R.items():
        L += [f"### {m}", "", "| Fault type | n | " + " | ".join(LABEL[d] for d in dets) + " |", "|---|---|" + "---|" * len(dets)]
        classes = list(v[key][dets[0]]["per_class"])
        for c in classes:
            n = v[key][dets[0]]["per_class"][c]["events"]
            cells = []
            for d in dets:
                p = v[key][d]["per_class"][c]
                cells.append(f"{p['detected']}/{p['events']} {ci(p['recall_ci95'])}, {f3(p['median_delay_samples'], 0)}")
            L.append(f"| `{c}` | {n} | " + " | ".join(cells) + " |")
        L.append("")
    return L


def write_cycle_report(R, tag, prof_name, path, hashes):
    L = [f"# Development cycle `{tag}` (profile `{prof_name}`) — v3 VALIDATION runs only", "",
         "> Development evidence. Settings were selected on these validation runs (and CUSUM on calibration+validation), so the numbers are optimistic; independent evidence comes only from the final fresh-suite evaluation.", "",
         f"- Written {datetime.now(timezone.utc).isoformat()}; code hashes recorded in `metrics.json`.", "",
         "## Overall (validation)", ""] + overall_table(R, "validation", ("hybrid_m7", "hybrid_m6", "hybrid_m5", "segment_setpoint", "gbt_all", "cusum")) + [""]
    L += ["## Per fault type (validation): detected/events [Wilson 95 %], median delay", ""] + per_class_table(R, "validation", ("hybrid_m7", "hybrid_m6", "hybrid_m5", "segment_setpoint", "gbt_all"))
    L += ["## Selected settings", ""]
    for m, v in R.items():
        s = v["selected_settings"]
        L.append(f"- **{m}**: segment `{s['segment_mode']}` MAD {s['segment_mad_threshold']}, extra `{s['transient_extra']}` (curvature z {s['curvature_threshold']}), stuck `{s['stuck_mode']}`, "
                 f"GBT thr {s['gbt_threshold']:.4g}; CUSUM `{s['cusum_mode']}` window {s['transition_exclusion']} min_baseline {s['cusum_min_baseline']} min_series {s['cusum_min_series']} k {s['cusum_k']} h {s['cusum_h']}; "
                 f"lifecycle `{s['drift_lifecycle']}` (W {s['clear_window']}, z {s['clear_z']}); attribution `{s['attribution']}` (L {s['confirm_window']}, k {s['confirm_k']}).")
        c = v["cusum"]
        L.append(f"  - CUSUM tuning: {c['tuning_runs']['controls']} controls, {c['tuning_runs']['drift_runs']} drift runs; selected FA {c['selected']['false_alarms']}, pre-onset {c['selected']['pre_onset']}, detected {c['selected']['detected']}, median delay {f3(c['selected']['median_delay'], 0)}.")
    L += ["", "## Workstream evidence (validation)", "", "### WS1 lifecycle: full-hybrid trials", "",
          "| Measurand | Lifecycle | Event F1 | FA/h | Post-fault alarm records (total) | True episodes with >60 overhang |", "|---|---|---|---|---|---|"]
    for m, v in R.items():
        for t in v["lifecycle_trials"]:
            L.append(f"| {m} | {t['lifecycle']} | {t['event_f1']:.3f} | {t['false_alarms_per_hour']:.1f} | {t['overhang']['true_episode_overhang_samples_total']} | {t['overhang']['true_episodes_with_overhang_over_60']} |")
    L += ["", "### WS1 attribution trials (classification accuracy of detected events)", "", "| Measurand | Attribution | Accuracy | offset | gain | spike | abrupt |", "|---|---|---|---|---|---|---|"]
    for m, v in R.items():
        for t in v["attribution_trials"]:
            pc = t["per_class"]
            g = lambda k: f"{pc[k]['correct']}/{pc[k]['detected']}" if k in pc else "–"
            L.append(f"| {m} | {t['attribution']} | {f3(t['accuracy'])} | {g('offset_shift')} | {g('gain_change')} | {g('isolated_spike')} | {g('abrupt_change')} |")
    L += ["", "### WS2 transient options (best per option; transient component alone)", "",
          "| Measurand | Segment mode | Extra | Best F1 | at MAD | Spike recall stationary | Spike recall non-stationary | FA/h ramp | FA/h settling | FA/h post-event |", "|---|---|---|---|---|---|---|---|---|---|"]
    for m, v in R.items():
        groups = {}
        for t in v["transient_trials"]:
            groups.setdefault((t["segment_mode"], json.dumps(t["extra"], sort_keys=True)), []).append(t)
        for (seg, ex), ts in groups.items():
            b = max(ts, key=lambda t: t["event_f1"])
            sp = b["spike_recall_by_phase"]; cf = b["context_fa"]
            L.append(f"| {m} | {seg} | {ex} | {b['event_f1']:.3f} | {b['mad']} | {f3(sp['stationary']['recall'], 2)} | {f3(sp['nonstationary']['recall'], 2)} ({sp['nonstationary']['events']}) | "
                     f"{f3(cf['ramp']['per_hour'], 1)} | {f3(cf['settling']['per_hour'], 1)} | {f3(cf['post_event_transient']['per_hour'], 1)} |")
    L += ["", "### WS3 MAD threshold (best transient F1 per threshold)", "", "| Measurand | MAD | Best transient F1 | FA/h |", "|---|---|---|---|"]
    for m, v in R.items():
        by = {}
        for t in v["transient_trials"]:
            by.setdefault(t["mad"], []).append(t)
        for mad, ts in sorted(by.items()):
            b = max(ts, key=lambda t: t["event_f1"])
            L.append(f"| {m} | {mad} | {b['event_f1']:.3f} | {b['false_alarms_per_hour']:.1f} |")
    L += ["", "### WS3 CUSUM (best configuration per mode and exclusion window)", "", "| Measurand | Mode | Window | min_baseline | min_series | k | h | ARL0 ok | FA | pre-onset | detected | median delay |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for m, v in R.items():
        for g in v["cusum"]["best_per_mode_window"]:
            L.append(f"| {m} | {g['mode']} | {g['window']} | {g['min_baseline']} | {g['min_series']} | {g['k']} | {g['h']} | {g['arl0_ok']} | {g['false_alarms']} | {g['pre_onset']} | {g['detected']} | {f3(g['median_delay'], 0)} |")
    L += ["", "### Strata (hybrid M7, validation): recall by noise group / variant / magnitude", ""]
    for m, v in R.items():
        s = v["validation"]["hybrid_m7"]["strata"]
        L.append(f"- {m}: " + "; ".join(f"{k}: " + ", ".join(f"{g} {x['detected']}/{x['events']}" for g, x in grp.items()) for k, grp in s.items()))
    path.write_text("\n".join(L), encoding="utf-8")


# ==============================================================================
# Stages
# ==============================================================================

def stage_develop(args, freeze):
    CFG = load_json(WORKSPACE_ROOT / "config" / "hybrid_iteration_config.json")
    base_cfg = load_json(WORKSPACE_ROOT / "config" / "default_config.json")
    suite_cfg = load_json(WORKSPACE_ROOT / CFG["dev_dataset_config"])
    prof = profile(CFG, args.profile)
    manifest, msha, frames, metas = load_suite(WORKSPACE_ROOT / CFG["dev_dataset_root"])
    frames = {k: v[v.partition.isin(["calibration", "validation"])].reset_index(drop=True) for k, v in frames.items()}  # test never loaded into detectors
    R, state = develop(CFG, prof, base_cfg, suite_cfg, frames, metas, args.profile)
    hashes = code_hashes()
    if not freeze:
        out = CYCLE_ROOT / args.tag
        out.mkdir(parents=True, exist_ok=False)
        with open(out / "metrics.json", "w", encoding="utf-8") as f:
            json.dump(jsonable({"profile": args.profile, "profile_spec": prof, "code_hashes": hashes, "dev_manifest_sha256": msha, "results": R}), f, indent=2)
        write_cycle_report(R, args.tag, args.profile, out / "SUMMARY.md", hashes)
        print(f"Cycle report: {out / 'SUMMARY.md'}")
        return 0
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = WORKSPACE_ROOT / "results" / f"hybrid_frozen_{stamp}"
    (out / "models").mkdir(parents=True)
    frozen = {"profile": args.profile, "profile_spec": prof, "selection_rules": CFG["selection_rules"], "code_hashes": hashes,
              "dev_dataset": {"root": CFG["dev_dataset_root"], "manifest_sha256": msha, "partitions_used": ["calibration", "validation"]},
              "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
              "measurands": {m: {"hybrid_settings": state[m]["settings"].to_dict(),
                                 "cusum_alone_settings": state[m]["cusum_settings"].to_dict(),
                                 "targeted_gbt": {"params": state[m]["gbt_p"].params, "threshold": state[m]["gbt_p"].threshold},
                                 "gbt_all": {"params": state[m]["gbt_all"].params, "threshold": state[m]["gbt_all"].threshold},
                                 "iforest": {"params": state[m]["iforest"].params, "threshold": state[m]["iforest"].threshold},
                                 "feature_floor": state[m]["P"]["builder"].floor,
                                 "calibration_models": {d: {"type": mm.model_type, "coefficients": mm.coefficients} for d, mm in state[m]["P"]["cal_models"].items()}}
                             for m in CFG["measurands"]}}
    fb = json.dumps(jsonable(frozen), indent=2, sort_keys=True).encode("utf-8")
    (out / "frozen_settings.json").write_bytes(fb)
    for m in CFG["measurands"]:
        s = state[m]
        joblib.dump({"feature_builder": s["P"]["builder"], "targeted_gbt": s["gbt_p"], "gbt_all": s["gbt_all"], "iforest": s["iforest"],
                     "calibration_models": s["P"]["cal_models"], "hybrid_settings": s["settings"], "cusum_settings": s["cusum_settings"]},
                    out / "models" / f"{m}_detectors.joblib")
    with open(out / "validation_metrics.json", "w", encoding="utf-8") as f:
        json.dump(jsonable(R), f, indent=2)
    write_cycle_report(R, f"freeze_{stamp}", args.profile, out / "VALIDATION_SUMMARY.md", hashes)
    sha = hashlib.sha256(fb).hexdigest()
    (out / "FROZEN.txt").write_text(f"frozen_settings.json sha256 {sha}\n", encoding="utf-8")
    print(f"Frozen bundle: {out}  sha256 {sha}")
    return 0


def changed_code(frozen_hashes, current_hashes):
    """Source files whose hash differs from the frozen state (empty list = code is frozen)."""
    return sorted(f for f, h in frozen_hashes.items() if current_hashes.get(f) != h)


def previous_evaluation(results_root, frozen_sha, manifest_sha):
    """Return the directory of a completed final evaluation of the same (bundle, suite) pair, if any."""
    for d in sorted(Path(results_root).glob("hybrid_final_*/evaluation_complete.json")):
        done = load_json(d)
        if done["frozen_settings_sha256"] == frozen_sha and done["suite_manifest_sha256"] == manifest_sha:
            return d.parent
    return None


def stage_final(args):
    frozen_dir = Path(args.frozen).resolve()
    fb = (frozen_dir / "frozen_settings.json").read_bytes()
    frozen = json.loads(fb)
    fsha = hashlib.sha256(fb).hexdigest()
    changed = changed_code(frozen["code_hashes"], code_hashes())
    if changed:
        raise SystemExit(f"ABORT: code changed since freezing: {changed}")
    CFG = load_json(WORKSPACE_ROOT / "config" / "hybrid_iteration_config.json")
    base_cfg = load_json(WORKSPACE_ROOT / "config" / "default_config.json")
    dev_cfg = load_json(WORKSPACE_ROOT / CFG["dev_dataset_config"])
    suite_cfg = load_json(Path(args.suite_config).resolve())
    used = set()
    for c in ("config/synthetic_suite_config.json", "config/synthetic_suite_v4_config.json", CFG["dev_dataset_config"]):
        p = WORKSPACE_ROOT / c
        if p.exists():
            used |= set(load_json(p)["seed_roots"].values())
    if set(suite_cfg["seed_roots"].values()) & used:
        raise SystemExit("ABORT: final-suite seed roots overlap earlier suites")
    root = Path(args.data_root).resolve()
    manifest, msha, frames, metas = load_suite(root)
    if manifest["config_sha256"] != hashlib.sha256(json.dumps(suite_cfg, sort_keys=True).encode()).hexdigest():
        raise SystemExit("ABORT: data root does not match the suite configuration")
    prev = previous_evaluation(WORKSPACE_ROOT / "results", fsha, msha)
    if prev is not None and not args.allow_identical_rerun:
        raise SystemExit(f"ABORT: this frozen bundle was already evaluated on this suite ({prev.name}); evaluate once only.")
    parts = {p for df in frames.values() for p in df.partition.unique()}
    if parts != {"test"}:
        raise SystemExit(f"ABORT: final suite must contain test runs only, found {parts}")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = WORKSPACE_ROOT / "results" / f"hybrid_final_{stamp}"
    for sub in ("predictions", "plots", "config"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    shutil.copy(Path(args.suite_config).resolve(), out / "config")
    shutil.copy(frozen_dir / "frozen_settings.json", out / "config")
    R = {}
    m5_dir = WORKSPACE_ROOT / CFG["m5_bundle_dir"]
    for m in CFG["measurands"]:
        b = joblib.load(frozen_dir / "models" / f"{m}_detectors.joblib")
        fr = {sid: df for sid, df in frames.items() if metas[sid]["measurand"] == m}
        events = [dict(e) for sid in fr for e in metas[sid]["fault_events"] if e["fault_type"] in SIGNAL_FAULT_TYPES]
        info = {}
        for sid in fr:
            info.update(event_strata(metas[sid], suite_cfg["devices"], noise_ranks(suite_cfg["devices"])))
        comps = []
        integ_flags, integ_labels = [], []
        for sid, df in fr.items():
            dev = metas[sid]["sensor_error_model"]["device_id"]
            hd = HybridDetector(m, b["feature_builder"], None, b["calibration_models"].get(dev), base_cfg, b["hybrid_settings"], score_cache=True,
                                score_base_threshold=SCORE_BASE)
            for _, run in df.groupby("experiment_id", sort=False):
                c = hd.components(run)
                comps.append(c)
                integ_flags.append(c["integrity"])
                integ_labels.append([";".join(t for t in x.split(";") if t in INTEGRITY_FAULT_TYPES) or "none" for x in c["run"]["label_fault_type"]])
        E = EvalSet(comps, events, CFG, m, info)
        m6_dir = WORKSPACE_ROOT / CFG.get("m6_bundle_dir", "results/hybrid_frozen_20261026_123033")
        D = {"settings": b["hybrid_settings"], "gbt_p": b["targeted_gbt"], "gbt_all": b["gbt_all"], "iforest": b["iforest"],
             "cusum_settings": b["cusum_settings"], "m6": joblib.load(m6_dir / "models" / f"{m}_detectors.joblib"),
             "m5": joblib.load(m5_dir / "models" / f"{m}_detectors.joblib")}
        alarms, cat7, cat6, cat5 = score_all(comps, D, base_cfg)
        R[m] = {"test": {d: full_eval(alarms[d], E, cat7 if d == "hybrid_m7" else (cat6 if d == "hybrid_m6" else (cat5 if d == "hybrid_m5" else None)),
                                     CFG["bootstrap_resamples"], CFG["random_seed"]) for d in DETECTORS},
                "context_fa": {d: context_fa(alarms[d], E) for d in DETECTORS},
                "spike_by_phase": {d: spike_recall_by_phase(alarms[d], E) for d in ("hybrid_m7", "hybrid_m6", "hybrid_m5", "segment_setpoint", "curvature")}}
        fl = np.concatenate(integ_flags); lb = np.concatenate(integ_labels)
        R[m]["integrity"] = {"overall": binary_metrics(fl, lb != "none"),
                             "per_class": {t: {"rows": int(sum(t in x for x in lb)), "detected": int(fl[[t in x for x in lb]].sum())} for t in INTEGRITY_FAULT_TYPES}}
        pred = E.df[["scenario_id", "experiment_id", "sequence_number", "protocol_phase", "signal_fault_type"]].copy()
        for d in DETECTORS:
            pred[f"{d}_alarm"] = alarms[d]
        pred["hybrid_m7_category"] = cat7
        pred["hybrid_m6_category"] = cat6
        pred["hybrid_m5_category"] = cat5
        pred.to_csv(out / "predictions" / f"{m}_test_alarms.csv", index=False)
        print(f"[{m}] scored {len(E.df)} records, {len(E.windows)} events: M7 F1 {R[m]['test']['hybrid_m7']['event']['event_f1']:.3f}, M6 F1 {R[m]['test']['hybrid_m6']['event']['event_f1']:.3f}, M5 F1 {R[m]['test']['hybrid_m5']['event']['event_f1']:.3f}", flush=True)
    info = {"command": " ".join(["python", "scripts/run_hybrid_iteration.py", *sys.argv[1:]]), "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "frozen_dir": str(frozen_dir.relative_to(WORKSPACE_ROOT)), "frozen_settings_sha256": fsha, "suite_id": manifest["suite_id"],
            "suite_manifest_sha256": msha, "seed_roots": suite_cfg["seed_roots"], "code_hashes_verified": True,
            "versions": {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__, "scikit_learn": sklearn.__version__}}
    with open(out / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(jsonable({"run_info": info, "results": R}), f, indent=2)
    write_final_report(info, R, out / "REPORT.md")
    plot_final(R, out / "plots")
    (out / "evaluation_complete.json").write_text(json.dumps({"frozen_settings_sha256": fsha, "suite_manifest_sha256": msha,
                                                              "completed_utc": datetime.now(timezone.utc).isoformat()}, indent=2), encoding="utf-8")
    print(f"Final evaluation: {out}")
    return 0


def write_final_report(info, R, path):
    dets_main = ("hybrid_m7", "hybrid_m6", "hybrid_m5", "segment_setpoint", "gbt_all", "cusum")
    L = ["# IMUCA — Milestone 7 final evaluation on a fresh independent suite (scored once)", "",
         "> SYNTHETIC DATA ONLY. Frozen detectors evaluated once on a suite generated after freezing, with new seed roots for every run.", "",
         f"- Command: `{info['command']}` at {info['timestamp_utc']}",
         f"- Frozen bundle `{info['frozen_dir']}` (frozen_settings SHA-256 `{info['frozen_settings_sha256']}`); source-code hashes verified identical to the frozen state.",
         f"- Suite `{info['suite_id']}` (manifest SHA-256 `{info['suite_manifest_sha256'][:16]}…`), seed roots {info['seed_roots']}.", "",
         "## Overall (test runs)", ""] + overall_table(R, "test", DETECTORS) + [""]
    L += ["## Per fault type: detected/events [Wilson 95 %], median delay (samples)", ""] + per_class_table(R, "test", dets_main)
    L += ["## Fault classification (detected events with correct category)", "", "| Measurand | Detector | Accuracy [CI] | per class |", "|---|---|---|---|"]
    for m, v in R.items():
        for d in ("hybrid_m7", "hybrid_m6", "hybrid_m5"):
            c = v["test"][d]["classification"]
            L.append(f"| {m} | {LABEL[d]} | {f3(c['accuracy'])} {ci(c['accuracy_ci95'])} | " + ", ".join(f"{k} {x['correct']}/{x['detected']}" for k, x in c["per_class"].items()) + " |")
    L += ["", "## False alarms per hour by operating context", "", "| Measurand | Detector | steady | ramp | settling | post-event transient |", "|---|---|---|---|---|---|"]
    for m, v in R.items():
        for d in dets_main + ("curvature",):
            cf = v["context_fa"][d]
            L.append(f"| {m} | {LABEL[d]} | " + " | ".join(f"{f3(cf[k]['per_hour'], 1)} ({cf[k]['hours']:.2f} h)" for k in ("steady", "ramp", "settling", "post_event_transient")) + " |")
    L += ["", "## Spike recall by protocol phase", "", "| Measurand | Detector | stationary | non-stationary |", "|---|---|---|---|"]
    for m, v in R.items():
        for d, s in v["spike_by_phase"].items():
            L.append(f"| {m} | {LABEL[d]} | {s['stationary']['detected']}/{s['stationary']['events']} | {s['nonstationary']['detected']}/{s['nonstationary']['events']} |")
    L += ["", "## Strata (recall)", ""]
    for m, v in R.items():
        for d in ("hybrid_m7", "hybrid_m6", "hybrid_m5"):
            s = v["test"][d]["strata"]
            L.append(f"- {m}, {LABEL[d]}: " + "; ".join(f"{k}: " + ", ".join(f"{g} {x['detected']}/{x['events']}" for g, x in grp.items()) for k, grp in s.items()))
    L += ["", "## Integrity track", ""]
    for m, v in R.items():
        it = v["integrity"]
        L.append(f"- {m}: precision {f3(it['overall']['precision'])}, recall {f3(it['overall']['recall'])}, FAR {f3(it['overall']['false_alarm_rate'], 4)}; " +
                 ", ".join(f"{k} {x['detected']}/{x['rows']}" for k, x in it["per_class"].items()))
    L += ["", "## Verdict", ""]
    for m, v in R.items():
        a, b, b5 = v["test"]["hybrid_m7"]["event"], v["test"]["hybrid_m6"]["event"], v["test"]["hybrid_m5"]["event"]
        best_ind = max((d for d in DETECTORS if not d.startswith("hybrid")), key=lambda d: v["test"][d]["event"]["event_f1"])
        c = v["test"][best_ind]["event"]
        def ov(x, y):
            return x[0] is not None and y[0] is not None and not (x[0] > y[1] or y[0] > x[1])
        L.append(f"- {m}: M7 F1 {a['event_f1']:.3f} {ci(a['event_f1_ci95_run_bootstrap'])} vs M6 {b['event_f1']:.3f} {ci(b['event_f1_ci95_run_bootstrap'])} "
                 f"({'overlapping' if ov(a['event_f1_ci95_run_bootstrap'], b['event_f1_ci95_run_bootstrap']) else 'non-overlapping'}); "
                 f"vs M5 {b5['event_f1']:.3f} {ci(b5['event_f1_ci95_run_bootstrap'])} "
                 f"({'overlapping' if ov(a['event_f1_ci95_run_bootstrap'], b5['event_f1_ci95_run_bootstrap']) else 'non-overlapping'}); "
                 f"best single detector {LABEL[best_ind]} {c['event_f1']:.3f} {ci(c['event_f1_ci95_run_bootstrap'])} "
                 f"({'overlapping' if ov(a['event_f1_ci95_run_bootstrap'], c['event_f1_ci95_run_bootstrap']) else 'non-overlapping'} with M7). "
                 f"FA/h M7 {a['false_alarms_per_hour']:.1f}, M6 {b['false_alarms_per_hour']:.1f}, M5 {b5['false_alarms_per_hour']:.1f}, {LABEL[best_ind]} {c['false_alarms_per_hour']:.1f}.")
    L.append("- Overlapping run-bootstrap intervals mean the difference is not established.")
    path.write_text("\n".join(L), encoding="utf-8")


def plot_final(R, outdir):
    CFG = load_json(WORKSPACE_ROOT / "config" / "hybrid_iteration_config.json")
    pal = CFG["plot_palette"]
    show = ("hybrid_m7", "hybrid_m6", "hybrid_m5", "segment_setpoint", "gbt_all")
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.8), facecolor=pal["surface"], layout="constrained")
    for ax, m in zip(axes, R):
        classes = list(R[m]["test"]["hybrid_m7"]["per_class"])
        y = np.arange(len(classes)); h = 0.16
        for j, d in enumerate(show):
            pc = R[m]["test"][d]["per_class"]
            vals = np.array([pc[c]["recall"] for c in classes])
            lo = np.array([pc[c]["recall_ci95"][0] for c in classes]); hi = np.array([pc[c]["recall_ci95"][1] for c in classes])
            yy = y + (j - 2.0) * (h + 0.02)
            ax.barh(yy, vals, height=h, color=pal[d], label=LABEL[d])
            ax.errorbar(vals, yy, xerr=[np.maximum(vals - lo, 0), np.maximum(hi - vals, 0)], fmt="none", ecolor=pal["muted"], elinewidth=0.8)
        ax.set_yticks(y, [f"{c.replace('_', ' ')} (n={R[m]['test']['hybrid_m7']['per_class'][c]['events']})" for c in classes], color=pal["text"], fontsize=8)
        ax.invert_yaxis(); ax.set_xlim(0, 1)
        ax.set_title(m, color=pal["text"], fontsize=10, loc="left")
        ax.set_xlabel("Timely event recall (95 % Wilson)", color=pal["muted"], fontsize=8)
        ax.set_facecolor(pal["surface"])
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.grid(axis="x", color=pal["grid"], linewidth=0.6); ax.set_axisbelow(True)
        ax.tick_params(colors=pal["muted"], labelsize=8)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="outside lower left", ncol=5, frameon=False, fontsize=8)
    fig.suptitle("Event recall by fault class on the fresh test suite (scored once)", color=pal["text"], fontsize=11, x=0.01, ha="left")
    fig.savefig(outdir / "event_recall_by_class.png", dpi=150, facecolor=pal["surface"])
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=["validate", "freeze", "final"])
    ap.add_argument("--profile")
    ap.add_argument("--tag")
    ap.add_argument("--frozen")
    ap.add_argument("--suite-config")
    ap.add_argument("--data-root")
    ap.add_argument("--allow-identical-rerun", action="store_true", help="only for re-running an interrupted, bit-identical final evaluation")
    args = ap.parse_args()
    if args.stage == "validate":
        return stage_develop(args, freeze=False)
    if args.stage == "freeze":
        return stage_develop(args, freeze=True)
    return stage_final(args)


if __name__ == "__main__":
    sys.exit(main())
