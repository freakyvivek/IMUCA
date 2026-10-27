#!/usr/bin/env python3
"""
IMUCA Conventional Baseline on the v2 Synthetic Benchmark Suite.

Runs the EXISTING conventional pipeline (DataIngestionPipeline, DataQualityAssessor,
CalibrationEngine, measurement metrics, GUM uncertainty budget, analyze_temporal_drift)
on data/synthetic/{voltage,current,temperature,fault_detection}/ and reports:

- Measurement ERROR metrics (bias, MAE, RMSE, max error) against the simulated reference
  and, separately, against simulation ground truth.
- Measurement UNCERTAINTY (GUM budget) with an explicit completeness statement, plus the
  empirical coverage of the stated U against ground truth on the test partition.
- Calibration improvement on independent validation runs and final held-out test runs.
- Repeatability, residual diagnostics, drift-rate estimation error and run-level drift detection.
- Fault-detection precision / recall / false-alarm / missed-detection rates (sample and event level).

No ML model is trained. Results go to a new timestamped directory; earlier results are never overwritten.

Usage:
    python scripts/run_synthetic_benchmark.py
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
import scipy.stats as stats

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from src.imuca import (
    DataIngestionPipeline,
    DataQualityAssessor,
    CalibrationEngine,
    compute_error_metrics,
    compute_descriptive_statistics,
    compute_pooled_repeatability,
    compute_residual_diagnostics,
    evaluate_type_a,
    evaluate_type_b,
    evaluate_shunt_current_uncertainty,
    build_uncertainty_budget,
    analyze_temporal_drift,
    MetrologyReportGenerator,
    UncertaintyComponent,
)
from src.imuca.synthetic_suite import iter_run_csv_buffers, _sha256_bytes, NO_LABEL

DATA_ROOT = WORKSPACE_ROOT / "data" / "synthetic"
META_DIR = DATA_ROOT / "metadata"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUT_DIR = WORKSPACE_ROOT / "results" / f"synthetic_benchmark_{STAMP}"
PROC_DIR = WORKSPACE_ROOT / "data" / "processed" / f"synthetic_suite_{STAMP}"


# ==============================================================================
# Helpers
# ==============================================================================

def load_json(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def em(measured, reference):
    """Error metrics as a plain dict (NaN-safe)."""
    m = compute_error_metrics(np.asarray(measured, float), np.asarray(reference, float))
    return {"n": m.n, "bias": m.mean_bias, "mae": m.mae, "rmse": m.rmse, "max_abs_error": m.max_absolute_error}


def both_errors(pred, df, m):
    return {"vs_reference": em(pred, df[f"reference_{m}"]), "vs_true": em(pred, df[f"true_{m}"])}


def reduction(before, after):
    return 100.0 * (before - after) / before if before > 0 else 0.0


def jsonable(o):
    if isinstance(o, dict):
        return {str(k): jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jsonable(v) for v in o]
    if isinstance(o, (np.bool_, bool)):
        return bool(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else float(o)
    return o


def design_row(x, degree):
    return np.array([x ** p for p in range(degree + 1)], dtype=float)


def fit_uncertainty(model, x):
    """Standard uncertainty of the fitted calibration curve at x from the coefficient covariance."""
    cov = np.asarray(model.covariance_matrix)
    xs = np.atleast_1d(np.asarray(x, float))
    return np.array([np.sqrt(max(0.0, design_row(v, model.degree) @ cov @ design_row(v, model.degree))) for v in xs])


def ingest_scenario(csv_path, pipe):
    """Ingest a scenario run-by-run through the existing pipeline; return audit + raw frame."""
    raw = pd.read_csv(csv_path)
    audit = {"runs": 0, "valid_runs": 0, "records": 0, "error_records": 0, "warning_records": 0, "issue_codes": {}}
    for exp_id, buf in iter_run_csv_buffers(str(csv_path)):
        _, diag = pipe.load_csv(buf, source_id=exp_id)
        sv = diag.schema_validation
        audit["runs"] += 1
        audit["valid_runs"] += int(sv.is_valid)
        audit["records"] += sv.total_records
        audit["error_records"] += sv.error_record_count
        audit["warning_records"] += sv.warning_record_count
        for d in sv.diagnostics:
            audit["issue_codes"][d.issue_code] = audit["issue_codes"].get(d.issue_code, 0) + 1
    return raw, audit


def qa_flags(df, m, base_cfg):
    """Existing DataQualityAssessor per run; returns (is_error, is_warning) aligned with df."""
    mc = base_cfg["measurands"][m]
    assessor = DataQualityAssessor(mad_threshold=base_cfg["quality"]["mad_threshold"],
                                   nominal_sampling_period_s=1.0 / base_cfg["quality"]["nominal_sampling_rate_hz"])
    err = np.zeros(len(df), bool)
    warn = np.zeros(len(df), bool)
    for _, idx in df.groupby("experiment_id", sort=False).indices.items():
        rep = assessor.assess(df.iloc[idx].reset_index(drop=True), measurand_col=m,
                              range_limits=(mc["min_range"], mc["max_range"]),
                              max_rate_of_change=mc["max_rate_of_change_per_sec"], ground_truth_fault_col=None)
        err[idx] = rep.annotated_dataframe["is_error"].to_numpy()
        warn[idx] = rep.annotated_dataframe["is_warning"].to_numpy()
    return err, warn


# ==============================================================================
# Calibration scenarios
# ==============================================================================

def analyze_calibration(sid, df, meta, base_cfg, suite_cfg, reporter):
    m = meta["measurand"]
    unit = meta["measurand_unit"]
    dev = meta["sensor_error_model"]["parameters"]
    stable_only = meta["analysis"].get("stable_phase_only", False)
    err, _ = qa_flags(df, m, base_cfg)
    usable = (~err) & np.isfinite(df[m]) & np.isfinite(df[f"reference_{m}"])
    if stable_only:
        usable &= (df["protocol_phase"] == "plateau_stable")
    d = {p: df[usable & (df.partition == p)] for p in ("calibration", "validation", "test")}

    engine = CalibrationEngine(f_test_alpha=base_cfg["calibration"]["f_test_alpha"])
    x_cal, y_cal = d["calibration"][m].to_numpy(), d["calibration"][f"reference_{m}"].to_numpy()
    models = {"linear": engine.fit_linear(x_cal, y_cal),
              "auto": engine.select_best_model(x_cal, y_cal, max_degree=base_cfg["calibration"]["max_polynomial_degree"])}

    val = d["validation"]
    val_eval = {"uncalibrated": both_errors(val[m], val, m)}
    for name, mod in models.items():
        val_eval[name] = both_errors(mod.predict(val[m].to_numpy()), val, m)
    chosen_name = min(models, key=lambda k: val_eval[k]["vs_reference"]["rmse"])
    model = models[chosen_name]

    # Test: once, per operating condition
    tst = d["test"]
    pred_tst = model.predict(tst[m].to_numpy())
    test_eval = {"all": {"uncalibrated": both_errors(tst[m], tst, m), "calibrated": both_errors(pred_tst, tst, m)}}
    for cond, idx in tst.groupby("operating_condition_id").indices.items():
        sub = tst.iloc[idx]
        test_eval[cond] = {"uncalibrated": both_errors(sub[m], sub, m), "calibrated": both_errors(pred_tst[idx], sub, m)}
    extrap, warns = model.check_extrapolation(tst[m].to_numpy())

    # Repeatability (ISO 5725 pooled over dwell/plateau groups, calibration partition)
    groups = [g[m].to_numpy() for _, g in d["calibration"].groupby(["experiment_id", "setpoint_index"])]
    rep = compute_pooled_repeatability(groups)
    q = dev.get("quantization_step", dev.get("adc_quantization_mV", 0) / dev.get("r_shunt_nominal_ohm", 1))
    sigma = dev.get("noise_std", dev.get("adc_noise_std_mV", 0) / dev.get("r_shunt_nominal_ohm", 1))

    # Residual diagnostics (calibration fit, time order)
    resid = y_cal - model.predict(x_cal)
    rd = compute_residual_diagnostics(resid)

    # GUM budget for a single calibrated reading at a representative operating point
    x0 = float(np.median(np.unique(np.round(d["calibration"][f"reference_{m}"], 6))))
    near = d["calibration"].iloc[(d["calibration"][f"reference_{m}"] - x0).abs().argsort()[:20]]
    u_ref_x0 = float(near["reference_expanded_uncertainty_k2"].mean()) / 2.0
    u_fit_x0 = float(fit_uncertainty(model, x0)[0])
    comps = [
        UncertaintyComponent(name="Repeatability (pooled s_r, single reading)", source_category="REPEATABILITY",
                             uncertainty_type="A", distribution="NORMAL", input_value=rep.repeatability_std_dev, unit=unit,
                             divisor=1.0, standard_uncertainty=rep.repeatability_std_dev, sensitivity_coefficient=1.0,
                             uncertainty_contribution=rep.repeatability_std_dev, degrees_of_freedom=float(rep.degrees_of_freedom)),
        evaluate_type_b("DUT resolution (configured quantisation step)", limit_value=q / 2.0, distribution="RECTANGULAR", unit=unit, source_category="RESOLUTION"),
        evaluate_type_b("Reference instrument (stated U, k=2)", limit_value=2.0 * u_ref_x0, distribution="NORMAL", unit=unit, source_category="REFERENCE_STANDARD"),
        UncertaintyComponent(name="Calibration-curve fit (coefficient covariance)", source_category="CALIBRATION_FIT",
                             uncertainty_type="A", distribution="NORMAL", input_value=u_fit_x0, unit=unit, divisor=1.0,
                             standard_uncertainty=u_fit_x0, sensitivity_coefficient=1.0, uncertainty_contribution=u_fit_x0,
                             degrees_of_freedom=float(len(x_cal) - model.degree - 1)),
    ]
    budget = build_uncertainty_budget(f"Calibrated {m}", x0, unit, comps,
                                      confidence_level=base_cfg["uncertainty"]["confidence_level"], force_k=2.0)
    unquantified = ["DUT long-term stability between calibration and use",
                    "DUT sensitivity to ambient temperature outside calibration conditions",
                    "Model inadequacy (residual nonlinearity not captured by the chosen model)"]
    if dev.get("thermal_resistance_C_per_W", 0) > 0:
        unquantified.append("Load-history-dependent shunt self-heating")
    if "time_constant_s" in dev:
        unquantified.append("Dynamic (lag) error during temperature changes")

    # Empirical coverage of U (same budget structure evaluated per test reading)
    u_row = np.sqrt(rep.repeatability_std_dev ** 2 + q ** 2 / 12.0 + (tst["reference_expanded_uncertainty_k2"].to_numpy() / 2.0) ** 2
                    + fit_uncertainty(model, tst[m].to_numpy()) ** 2)
    U_row = 2.0 * u_row
    cov = {}
    for cond, idx in [("all", np.arange(len(tst)))] + list(tst.groupby("operating_condition_id").indices.items()):
        e_true = np.abs(pred_tst[idx] - tst[f"true_{m}"].to_numpy()[idx])
        e_ref = np.abs(pred_tst[idx] - tst[f"reference_{m}"].to_numpy()[idx])
        cov[cond] = {"fraction_abs_error_vs_true_within_U": float(np.mean(e_true <= U_row[idx])),
                     "fraction_abs_error_vs_reference_within_U": float(np.mean(e_ref <= U_row[idx])),
                     "mean_U": float(np.mean(U_row[idx]))}

    # Processed output (derived data kept apart from raw inputs)
    out = tst[["experiment_id", "partition", "operating_condition_id", "sequence_number", m, f"reference_{m}", f"true_{m}"]].copy()
    out[f"calibrated_{m}"] = pred_tst
    out["stated_expanded_uncertainty_k2"] = U_row
    out.to_csv(PROC_DIR / f"{sid}_test_calibrated.csv", index=False)

    try:
        reporter.generate_plots(experiment_id=f"{sid}_TEST", ref_values=tst[f"reference_{m}"].to_numpy(),
                                dut_uncal=tst[m].to_numpy(), dut_cal=pred_tst, time_s=np.arange(len(tst), dtype=float),
                                uncertainty_half_width=float(np.median(U_row)), measurand_name=m, measurand_unit=unit)
    except Exception as exc:  # plotting must never invalidate numeric results
        print(f"    (plot skipped for {sid}: {exc})")

    return {
        "scenario_id": sid, "measurand": m, "unit": unit, "device_id": meta["sensor_error_model"]["device_id"],
        "rows_used": {p: int(len(v)) for p, v in d.items()},
        "row_selection": "QA errors excluded" + ("; protocol_phase == plateau_stable only" if stable_only else ""),
        "fit_target": "reference instrument reading (not ground truth)",
        "candidate_models": {k: {"type": v.model_type, "degree": v.degree, "formula": v.formula_string, "r_squared": v.r_squared,
                                 "bic": v.bic, "f_p_value": v.f_p_value} for k, v in models.items()},
        "selected_model": chosen_name, "selected_model_type": model.model_type,
        "selection_rule": "lowest validation RMSE vs reference among {linear, F-test/BIC auto-selected polynomial}",
        "validation": val_eval,
        "validation_rmse_reduction_vs_reference_percent": reduction(val_eval["uncalibrated"]["vs_reference"]["rmse"], val_eval[chosen_name]["vs_reference"]["rmse"]),
        "validation_rmse_reduction_vs_true_percent": reduction(val_eval["uncalibrated"]["vs_true"]["rmse"], val_eval[chosen_name]["vs_true"]["rmse"]),
        "test": test_eval,
        "test_extrapolated_readings": int(extrap.sum()), "test_domain_warnings": warns,
        "repeatability": {"pooled_s_r": rep.repeatability_std_dev, "repeatability_limit_r": rep.repeatability_limit,
                          "degrees_of_freedom": rep.degrees_of_freedom, "groups": rep.num_series,
                          "expected_from_generator_sqrt_sigma2_plus_q2_over_12": float(np.sqrt(sigma ** 2 + q ** 2 / 12.0))},
        "residual_diagnostics": {"mean": rd.mean_residual, "std": rd.residual_std_dev, "max_abs": rd.max_abs_residual,
                                 "durbin_watson": rd.durbin_watson_stat, "shapiro_p": rd.shapiro_wilk_p_value},
        "uncertainty_budget_at_x0": {
            "x0": x0, "u_c": budget.combined_standard_uncertainty, "nu_eff": budget.effective_degrees_of_freedom,
            "k": budget.coverage_factor_k, "U": budget.expanded_uncertainty,
            "components": [{"name": c.name, "type": c.uncertainty_type, "u": c.standard_uncertainty, "share_percent": c.variance_share_percent} for c in budget.components],
            "dominant": budget.dominant_component.name,
            "completeness": "INCOMPLETE",
            "unquantified_components": unquantified,
        },
        "empirical_coverage_test": cov,
        "_model": model,
    }


def shunt_model_budget(base_cfg, suite_cfg):
    """Uncalibrated indirect-model budget I = V/R at 1000 mA (existing GUM function)."""
    dev = suite_cfg["devices"]["DUT_I01"]
    shunt = base_cfg["measurands"]["current_mA"]["shunt_model"]
    r = shunt["r_shunt_nominal_ohm"]
    v = 1.0 * r
    u_v = np.sqrt((dev["adc_noise_std_mV"] * 1e-3) ** 2 + (dev["adc_quantization_mV"] * 1e-3) ** 2 / 12.0)
    u_r = r * shunt["r_shunt_tolerance_percent"] / 100.0 / np.sqrt(3.0)
    i_a, comps = evaluate_shunt_current_uncertainty(v_shunt_v=v, r_shunt_ohm=r, u_v_shunt_v=u_v, u_r_shunt_ohm=u_r)
    b = build_uncertainty_budget("DC current (uncalibrated shunt model)", i_a, "A", comps, force_k=2.0)
    return {"nominal_A": i_a, "u_c_mA": 1000 * b.combined_standard_uncertainty, "U_mA": 1000 * b.expanded_uncertainty,
            "dominant": b.dominant_component.name,
            "components": [{"name": c.name, "share_percent": c.variance_share_percent} for c in b.components],
            "inputs": {"u_V_shunt_V": u_v, "u_R_ohm": u_r, "R_tolerance_source": "config/default_config.json shunt_model (rectangular)"},
            "completeness": "INCOMPLETE: ADC gain/offset, TCR and self-heating not included"}


# ==============================================================================
# Repeatability, drift, dynamic, fault detection
# ==============================================================================

def analyze_repeatability(sid, df, meta):
    m = meta["measurand"]
    dev = meta["sensor_error_model"]["parameters"]
    expected = float(np.sqrt(dev["noise_std"] ** 2 + dev["quantization_step"] ** 2 / 12.0))
    out = {"scenario_id": sid, "expected_sd_from_generator": expected, "runs": []}
    for exp_id, run in df.groupby("experiment_id", sort=False):
        ds = compute_descriptive_statistics(run[m])
        ua = evaluate_type_a(run[m].to_numpy(), unit=meta["measurand_unit"])
        n = ds.n
        lo = ds.sample_std_dev * np.sqrt((n - 1) / stats.chi2.ppf(0.975, n - 1))
        hi = ds.sample_std_dev * np.sqrt((n - 1) / stats.chi2.ppf(0.025, n - 1))
        out["runs"].append({"experiment_id": exp_id, "partition": run.partition.iloc[0], "n": n, "mean": ds.mean,
                            "s": ds.sample_std_dev, "s_95ci": [lo, hi], "expected_sd_in_ci": bool(lo <= expected <= hi),
                            "u_A_of_mean": ua.standard_uncertainty,
                            "bias_vs_reference": em(run[m], run[f"reference_{m}"])["bias"],
                            "bias_vs_true": em(run[m], run[f"true_{m}"])["bias"]})
    return out


def analyze_drift(sid, df, meta):
    m = meta["measurand"]
    tol = float(meta["analysis"]["tolerance"])
    events = {e["run_id"]: e for e in meta["fault_events"] if e["fault_type"] == "gradual_drift"}
    runs = []
    for exp_id, run in df.groupby("experiment_id", sort=False):
        ok = np.isfinite(run[m]) & (run.status == "OK")
        r = run[ok]
        t = r.elapsed_ms.to_numpy() / 1000.0
        e = (r[m] - r[f"reference_{m}"]).to_numpy()
        base = float(np.median(e[: max(5, len(e) // 10)]))
        res = analyze_temporal_drift(t, e, nominal_target=base, upper_limit=base + tol, lower_limit=base - tol)
        ev = events.get(exp_id)
        true_rate = ev["magnitude"] if ev else 0.0
        entry = {"experiment_id": exp_id, "partition": r.partition.iloc[0], "drift_injected": ev is not None,
                 "true_rate_per_s": true_rate, "estimated_rate_full_run_per_s": res.drift_rate_per_s,
                 "rate_std_error": res.drift_rate_std_error, "p_value": res.p_value,
                 "regression_alarm": bool(res.is_drift_significant), "cusum_alarm": bool(res.cusum_detected_shift),
                 "cusum_first_alarm_index": res.shift_sample_index,
                 "forecast_seconds_to_breach": res.forecast_seconds_to_breach}
        if ev:
            post = t >= ev["onset_elapsed_ms"] / 1000.0
            lr = stats.linregress(t[post], e[post])
            entry["onset_s"] = ev["onset_elapsed_ms"] / 1000.0
            entry["estimated_rate_post_onset_per_s"] = lr.slope
            entry["rate_error_post_onset_percent"] = 100.0 * (lr.slope - true_rate) / abs(true_rate)
            entry["rate_error_full_run_percent"] = 100.0 * (res.drift_rate_per_s - true_rate) / abs(true_rate)
            if res.shift_sample_index is not None:
                delay = float(t[res.shift_sample_index] - entry["onset_s"])
                entry["cusum_alarm_before_onset"] = delay < 0
                if delay >= 0:
                    entry["cusum_delay_s"] = delay
        runs.append(entry)
    det = {}
    for alarm in ("regression_alarm", "cusum_alarm"):
        tp = sum(r["drift_injected"] and r[alarm] for r in runs)
        fn = sum(r["drift_injected"] and not r[alarm] for r in runs)
        fp = sum((not r["drift_injected"]) and r[alarm] for r in runs)
        tn = sum((not r["drift_injected"]) and not r[alarm] for r in runs)
        det[alarm] = {"TP": tp, "FN": fn, "FP": fp, "TN": tn}
    return {"scenario_id": sid, "measurand": m, "error_series": "observed - reference", "tolerance": tol,
            "runs": runs, "run_level_detection": det}


def segment_ids(df):
    """Contiguous protocol segments (set-point/plateau/ramp blocks) within each run."""
    key = df["experiment_id"].astype(str) + "|" + df["setpoint_index"].astype(str)
    return (key != key.shift()).cumsum().to_numpy()


def analyze_faults(sid, df, meta, base_cfg):
    m = meta["measurand"]
    mc = base_cfg["measurands"][m]
    assessor = DataQualityAssessor(mad_threshold=base_cfg["quality"]["mad_threshold"],
                                   nominal_sampling_period_s=1.0 / base_cfg["quality"]["nominal_sampling_rate_hz"])
    gt = df["is_injected_fault"].to_numpy()
    out = {"scenario_id": sid, "measurand": m, "analysis": meta["analysis"], "modes": {}}
    for mode, groups in (("whole_run", df.groupby("experiment_id", sort=False).indices),
                         ("per_protocol_segment", pd.Series(np.arange(len(df))).groupby(segment_ids(df)).indices)):
        pred = np.zeros(len(df), bool)
        for _, idx in groups.items():
            idx = np.asarray(idx)
            sub = df.iloc[idx].reset_index(drop=True)
            rep = assessor.assess(sub, measurand_col=m, range_limits=(mc["min_range"], mc["max_range"]),
                                  max_rate_of_change=mc["max_rate_of_change_per_sec"], ground_truth_fault_col=None)
            pred[idx] = (rep.annotated_dataframe["is_error"] | rep.annotated_dataframe["is_warning"]).to_numpy()
        res = {}
        for part in ("calibration", "validation", "test", "all"):
            sel = np.ones(len(df), bool) if part == "all" else (df.partition == part).to_numpy()
            res[part] = confusion(pred[sel], gt[sel], df[sel], meta)
        out["modes"][mode] = res
    return out


def confusion(pred, gt, df, meta):
    tp = int(np.sum(pred & gt)); fp = int(np.sum(pred & ~gt)); tn = int(np.sum(~pred & ~gt)); fn = int(np.sum(~pred & gt))
    # False alarms adjacent to a genuine process event (set-point change, true step, load step)
    proc = (df["label_process_event"] != NO_LABEL).to_numpy()
    near_proc = proc.copy()
    for s in range(1, 4):
        near_proc[s:] |= proc[:-s]
    per_class = {}
    ids = df["label_fault_event_id"].to_numpy()
    types = df["label_fault_type"].to_numpy()
    for t in sorted({x for s in types if s != NO_LABEL for x in s.split(";")}):
        rows = np.array([t in s.split(";") for s in types])
        per_class[t] = {"rows": int(rows.sum()), "row_recall": float(pred[rows].mean())}
    ev_total, ev_hit, delays = 0, 0, []
    present = set(df["experiment_id"])
    for ev in meta["fault_events"]:
        if ev["run_id"] not in present:
            continue
        rows = np.array([ev["event_id"] in s.split(";") for s in ids])
        if not rows.any():
            continue
        ev_total += 1
        hit = pred[rows]
        if hit.any():
            ev_hit += 1
            delays.append(int(np.argmax(hit)))
        per_class.setdefault(ev["fault_type"], {}).setdefault("events", 0)
        per_class[ev["fault_type"]]["events"] += 1
        per_class[ev["fault_type"]].setdefault("events_detected", 0)
        per_class[ev["fault_type"]]["events_detected"] += int(hit.any())
    return {
        "TP": tp, "FP": fp, "TN": tn, "FN": fn,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "false_alarm_rate": fp / (fp + tn) if fp + tn else None,
        "missed_detection_rate": fn / (tp + fn) if tp + fn else None,
        "false_alarms_near_process_events": int(np.sum(pred & ~gt & near_proc)),
        "event_recall": ev_hit / ev_total if ev_total else None,
        "events": ev_total, "events_detected": ev_hit,
        "median_detection_delay_samples": float(np.median(delays)) if delays else None,
        "per_class": per_class,
    }


def analyze_dynamic(sid, df, meta, cal_results):
    m = meta["measurand"]
    src = meta["analysis"]["calibration_source"]
    model = cal_results[src]["_model"]
    ok = np.isfinite(df[m]) & (df.status == "OK")
    d = df[ok].copy()
    d["calibrated"] = model.predict(d[m].to_numpy())
    out = {"scenario_id": sid, "calibration_source": src, "model": model.formula_string, "by_partition": {}}
    for part, g in d.groupby("partition"):
        phases = {}
        for ph, gg in g.groupby("protocol_phase"):
            phases[ph] = {"uncalibrated": both_errors(gg[m], gg, m), "static_calibration": both_errors(gg["calibrated"], gg, m)}
        out["by_partition"][part] = {"all": {"uncalibrated": both_errors(g[m], g, m), "static_calibration": both_errors(g["calibrated"], g, m)},
                                     "by_phase": phases}
    dev = meta["sensor_error_model"]["parameters"]
    if "time_constant_s" in dev and dev.get("model") == "first_order_lag":
        rates = {}
        for exp_id, r in d.groupby("experiment_id"):
            prof = next(x["profile"] for x in meta["runs"] if x["experiment_id"] == exp_id)
            rates[exp_id] = {"heat_rate_per_s": prof["heat_rate_per_s"],
                             "expected_steady_lag_error_heating": -dev["time_constant_s"] * prof["heat_rate_per_s"] * (1 + dev["gain_error"]),
                             "observed_mean_calibrated_error_vs_true_heating": float((r.loc[r.protocol_phase == "heating_ramp", "calibrated"] - r.loc[r.protocol_phase == "heating_ramp", f"true_{m}"]).mean())}
        out["lag_check"] = rates
    if m == "current_mA":
        tau = dev["thermal_time_constant_s"]
        trans = np.zeros(len(d), bool)
        for _, idx in d.groupby("experiment_id").indices.items():
            r = d.iloc[idx]
            ev = np.flatnonzero((r["label_process_event"] == "load_step").to_numpy())
            mask = np.zeros(len(r), bool)
            for k in ev:
                mask[k:k + int(3 * tau)] = True
            trans[idx] = mask
        te = d[trans]; st = d[~trans]
        out["thermal_transient_split"] = {
            "within_3_tau_after_load_step": both_errors(te["calibrated"], te, m),
            "steady_after_3_tau": both_errors(st["calibrated"], st, m)}
    return out


# ==============================================================================
# Markdown summary
# ==============================================================================

def fmt(x, nd=4):
    if x is None:
        return "–"
    if isinstance(x, float):
        return f"{x:.{nd}g}"
    return str(x)


def write_summary(res, path):
    L = ["# IMUCA Synthetic Benchmark — Conventional Baseline Summary", "",
         f"> {res['run_info']['disclaimer']}", "",
         f"- Run: `{res['run_info']['command']}` at {res['run_info']['timestamp_utc']}",
         f"- Suite manifest SHA-256: `{res['run_info']['suite_manifest_sha256'][:16]}…`, generator v{res['run_info']['generator_version']}, {res['run_info']['scenarios']} scenarios / {res['run_info']['records']:,} records",
         f"- All CSVs verified against manifest checksums: **{res['run_info']['checksums_verified']}**",
         "", "**Error vs uncertainty.** Bias/MAE/RMSE below are *measurement error* metrics, computed against the simulated reference and, separately, against simulation ground truth. *U* is a GUM expanded uncertainty (k = 2) from an explicitly INCOMPLETE budget; its empirical coverage against ground truth is reported, not assumed.", ""]

    ing = res["ingestion"]
    L += ["## 1. Ingestion through the existing pipeline (run by run)", "",
          "| Scenario group | Runs | Valid runs | Records | Error records | Warning records |", "|---|---|---|---|---|---|"]
    for grp in ("voltage", "current", "temperature", "fault_detection"):
        rows = [v for v in ing.values() if v["group"] == grp]
        L.append(f"| {grp} | {sum(r['runs'] for r in rows)} | {sum(r['valid_runs'] for r in rows)} | {sum(r['records'] for r in rows):,} | {sum(r['error_records'] for r in rows)} | {sum(r['warning_records'] for r in rows)} |")
    L += ["", "Error/warning records occur only in scenarios with injected record faults (non-finite, duplicates, gaps, invalid status, out-of-range spikes). All fault-free runs validate with zero errors. Malformed fixtures: " +
          ", ".join(f"`{k}` → {'flagged' if v['valid'] else 'rejected'}" for k, v in res["malformed"].items()), ""]

    L += ["## 2. Calibration (fit on calibration runs → select on validation runs → test once)", "",
          "| Scenario | Model | Val RMSE uncal → cal (vs ref) | Val RMSE reduction | Test RMSE uncal → cal (vs true) | Test bias cal (vs true) | s_r (expected) | U(k=2) at x0 | Coverage of U vs true (test) |",
          "|---|---|---|---|---|---|---|---|---|"]
    for sid, c in res["calibration"].items():
        u = c["unit"]
        v = c["validation"]
        t = c["test"]["all"]
        L.append(f"| `{sid}` | {c['selected_model_type']} | {fmt(v['uncalibrated']['vs_reference']['rmse'])} → {fmt(v[c['selected_model']]['vs_reference']['rmse'])} {u} | "
                 f"{c['validation_rmse_reduction_vs_reference_percent']:.1f} % | {fmt(t['uncalibrated']['vs_true']['rmse'])} → {fmt(t['calibrated']['vs_true']['rmse'])} {u} | "
                 f"{fmt(t['calibrated']['vs_true']['bias'])} {u} | {fmt(c['repeatability']['pooled_s_r'])} ({fmt(c['repeatability']['expected_from_generator_sqrt_sigma2_plus_q2_over_12'])}) | "
                 f"{fmt(c['uncertainty_budget_at_x0']['U'])} {u} | {100 * c['empirical_coverage_test']['all']['fraction_abs_error_vs_true_within_U']:.1f} % |")
    L += ["", "Test breakdown by operating condition (calibrated RMSE vs true; coverage of U vs true):", ""]
    for sid, c in res["calibration"].items():
        parts = [f"{k}: {fmt(v['calibrated']['vs_true']['rmse'])} {c['unit']} ({100 * c['empirical_coverage_test'][k]['fraction_abs_error_vs_true_within_U']:.0f} %)"
                 for k, v in c["test"].items() if k != "all"]
        L.append(f"- `{sid}` — " + "; ".join(parts))
    sb = res["shunt_model_budget"]
    L += ["", f"Uncalibrated shunt-model budget at 1 A (existing `evaluate_shunt_current_uncertainty`): u_c = {sb['u_c_mA']:.3g} mA, U = {sb['U_mA']:.3g} mA, dominant: {sb['dominant']}. {sb['completeness']}.", ""]

    L += ["## 3. Repeatability (VOLT_REPEATABILITY)", "", "| Run | n | s | 95 % CI of σ | expected σ in CI | u_A of mean |", "|---|---|---|---|---|---|"]
    r = res["repeatability"]["VOLT_REPEATABILITY"]
    for run in r["runs"]:
        L.append(f"| {run['experiment_id'].split('-')[-1]} | {run['n']} | {fmt(run['s'])} V | [{fmt(run['s_95ci'][0])}, {fmt(run['s_95ci'][1])}] V | {run['expected_sd_in_ci']} | {fmt(run['u_A_of_mean'])} V |")
    L += ["", f"Expected σ from generator: {fmt(r['expected_sd_from_generator'])} V (√(σ² + q²/12)).", ""]

    L += ["## 4. Drift (error series = observed − reference)", "",
          "| Scenario | Run | Drift injected | True rate | Est. rate (full run) | Est. rate (post-onset, oracle segment) | Rate error post-onset | Regression alarm | CUSUM alarm | CUSUM delay |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for sid, dres in res["drift"].items():
        for run in dres["runs"]:
            L.append(f"| `{sid}` | {run['experiment_id'].split('-')[-1]} | {run['drift_injected']} | {fmt(run['true_rate_per_s'])} | {fmt(run['estimated_rate_full_run_per_s'])} | "
                     f"{fmt(run.get('estimated_rate_post_onset_per_s'))} | {fmt(run.get('rate_error_post_onset_percent'), 3)}{' %' if 'rate_error_post_onset_percent' in run else ''} | {run['regression_alarm']} | {run['cusum_alarm']} | {'pre-onset alarm' if run.get('cusum_alarm_before_onset') else fmt(run.get('cusum_delay_s'))}{' s' if 'cusum_delay_s' in run else ''} |")
    L += ["", "Rates are in measurand units per second. Run-level detection (all partitions):", ""]
    for sid, dres in res["drift"].items():
        L.append(f"- `{sid}`: regression {dres['run_level_detection']['regression_alarm']}, CUSUM {dres['run_level_detection']['cusum_alarm']}")
    L.append("")

    L += ["## 5. Fault detection — existing `DataQualityAssessor` (test partition)", "",
          "| Scenario | Mode | Precision | Recall | False-alarm rate | Missed-detection rate | Event recall | FA near process events |",
          "|---|---|---|---|---|---|---|---|"]
    for sid, f in res["fault_detection"].items():
        for mode, mr in f["modes"].items():
            t = mr["test"]
            L.append(f"| `{sid}` | {mode} | {fmt(t['precision'], 3)} | {fmt(t['recall'], 3)} | {fmt(t['false_alarm_rate'], 3)} | {fmt(t['missed_detection_rate'], 3)} | {fmt(t['event_recall'], 3)} ({t['events_detected']}/{t['events']}) | {t['false_alarms_near_process_events']} |")
    L += ["", "Per-class event recall on the fault-detection benchmark (test partition, whole-run mode, pooled over measurands):", "",
          "| Fault class | Events detected / total | Row recall |", "|---|---|---|"]
    agg = {}
    for sid, f in res["fault_detection"].items():
        if f["analysis"]["type"] != "fault_detection":
            continue
        for cls, pc in f["modes"]["whole_run"]["test"]["per_class"].items():
            a = agg.setdefault(cls, [0, 0, 0, 0.0])
            a[0] += pc.get("events_detected", 0); a[1] += pc.get("events", 0); a[2] += pc["rows"]; a[3] += pc["row_recall"] * pc["rows"]
    for cls, a in sorted(agg.items()):
        L.append(f"| `{cls}` | {a[0]} / {a[1]} | {a[3] / a[2]:.3f} |")
    L.append("")

    L += ["## 6. Dynamic scenarios with a static calibration", ""]
    for sid, dy in res["dynamic"].items():
        tst = dy["by_partition"].get("test", {})
        L.append(f"- `{sid}` (calibration from `{dy['calibration_source']}`): test RMSE vs true uncal {fmt(tst['all']['uncalibrated']['vs_true']['rmse'])} → static-cal {fmt(tst['all']['static_calibration']['vs_true']['rmse'])}")
        for ph, v in tst.get("by_phase", {}).items():
            L.append(f"  - {ph}: static-cal bias vs true {fmt(v['static_calibration']['vs_true']['bias'])}, RMSE {fmt(v['static_calibration']['vs_true']['rmse'])}")
        if "thermal_transient_split" in dy:
            ts = dy["thermal_transient_split"]
            L.append(f"  - within 3τ after load step: RMSE vs true {fmt(ts['within_3_tau_after_load_step']['vs_true']['rmse'])}; steady: {fmt(ts['steady_after_3_tau']['vs_true']['rmse'])} (all partitions)")
    L += ["", "## 7. Limitations", ""] + [f"- {x}" for x in res["limitations"]] + [""]
    path.write_text("\n".join(L), encoding="utf-8")


# ==============================================================================
# Main
# ==============================================================================

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=False)
    PROC_DIR.mkdir(parents=True, exist_ok=False)
    base_cfg = load_json(WORKSPACE_ROOT / "config" / "default_config.json")
    suite_cfg = load_json(WORKSPACE_ROOT / "config" / "synthetic_suite_config.json")
    manifest_bytes = (META_DIR / "suite_manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)

    # Raw inputs must match the manifest (immutability check)
    bad = [f["csv_file"] for f in manifest["files"] if _sha256_bytes((DATA_ROOT / f["csv_file"]).read_bytes()) != f["csv_sha256"]]
    if bad:
        print("ABORT: raw datasets differ from manifest:", bad)
        return 1

    pipe = DataIngestionPipeline()
    reporter = MetrologyReportGenerator(output_dir=str(OUT_DIR / "plots"))
    res = {"run_info": {
        "command": "python scripts/run_synthetic_benchmark.py",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "output_dir": str(OUT_DIR.relative_to(WORKSPACE_ROOT)), "processed_dir": str(PROC_DIR.relative_to(WORKSPACE_ROOT)),
        "suite_manifest_sha256": _sha256_bytes(manifest_bytes), "generator_version": manifest["generator_version"],
        "scenarios": manifest["scenario_count"], "records": manifest["total_records"], "checksums_verified": True,
        "versions": {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__},
        "disclaimer": "SYNTHETIC BENCHMARK: conventional-algorithm verification on simulated data only. No physical sensor performance is claimed.",
        "ml_models_trained": False},
        "ingestion": {}, "calibration": {}, "repeatability": {}, "drift": {}, "fault_detection": {}, "dynamic": {}}

    frames, metas = {}, {}
    for f in manifest["files"]:
        sid = f["scenario_id"]
        raw, audit = ingest_scenario(DATA_ROOT / f["csv_file"], pipe)
        audit["group"] = f["group"]
        res["ingestion"][sid] = audit
        frames[sid] = raw
        metas[sid] = load_json(DATA_ROOT / f["metadata_file"])
    print(f"Ingested {len(frames)} scenarios through DataIngestionPipeline.load_csv (run by run).")

    mal = load_json(META_DIR / "malformed_manifest.json")
    res["malformed"] = {}
    for name, exp in mal.items():
        _, diag = pipe.load_csv(str(DATA_ROOT / "malformed" / name))
        sv = diag.schema_validation
        res["malformed"][name] = {"valid": sv.is_valid, "expected_valid": exp["expect_valid"],
                                  "issue_codes": sorted({d.issue_code for d in sv.diagnostics}),
                                  "matches_expectation": sv.is_valid == exp["expect_valid"]}

    order = sorted(metas, key=lambda s: {"calibration": 0, "repeatability": 1, "drift": 2, "integrity": 3, "fault_detection": 4, "dynamic": 5}[metas[s]["analysis"]["type"]])
    for sid in order:
        meta, df = metas[sid], frames[sid]
        kind = meta["analysis"]["type"]
        if kind == "calibration":
            res["calibration"][sid] = analyze_calibration(sid, df, meta, base_cfg, suite_cfg, reporter)
        elif kind == "repeatability":
            res["repeatability"][sid] = analyze_repeatability(sid, df, meta)
        elif kind == "drift":
            res["drift"][sid] = analyze_drift(sid, df, meta)
        elif kind in ("integrity", "fault_detection"):
            res["fault_detection"][sid] = analyze_faults(sid, df, meta, base_cfg)
        elif kind == "dynamic":
            res["dynamic"][sid] = analyze_dynamic(sid, df, meta, res["calibration"])
        print(f"  [{kind:15s}] {sid}")

    res["shunt_model_budget"] = shunt_model_budget(base_cfg, suite_cfg)
    res["limitations"] = [
        "All data are synthetic; results verify algorithms against their own simulated assumptions, not physical instruments.",
        "Calibration is fitted against the simulated reference, whose realised systematic error is non-zero; the error floor vs ground truth includes it.",
        "Uncertainty budgets are INCOMPLETE (stability, ambient sensitivity, model inadequacy, lag and self-heating are not quantified); coverage below 95 % in held-out conditions is the expected symptom.",
        "DataQualityAssessor is a pointwise screen: persistent faults (offset, gain, drift) are mostly invisible to it, and global MAD on multi-level runs is insensitive to small spikes.",
        "Drift p-values assume independent residuals; quantisation and the slow ambient sinusoid make them approximate.",
        "The existing CUSUM in analyze_temporal_drift uses k = 0.5 s and h = 4 s (in-control ARL about 170 samples), so it alarms on drift-free runs of 1200-1800 samples; its alarms are not used as evidence of drift.",
        "Full-run drift slopes are biased low because the run includes the drift-free pre-onset segment; post-onset slopes use the known onset (oracle segmentation) and measure estimator accuracy only.",
        "Repeatability in CURR_SWEEP_SELFHEAT is inflated by the thermal transient inside each dwell; it is not pure noise.",
        "Per-protocol-segment QA treats ramps and post-step lag transients as segments, so MAD flags legitimate dynamics there (high false-alarm rate for temperature).",
        "Within-run ingestion only: scenario CSVs hold several runs and must be split by experiment_id before calling the existing pipeline.",
        "Event detection counts any flag inside the event window; it does not require a correct fault class.",
    ]

    for c in res["calibration"].values():
        c.pop("_model", None)
    with open(OUT_DIR / "benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(jsonable(res), f, indent=2)
    write_summary(res, OUT_DIR / "BENCHMARK_SUMMARY.md")
    print(f"\nResults: {OUT_DIR / 'benchmark_results.json'}\nSummary: {OUT_DIR / 'BENCHMARK_SUMMARY.md'}\nProcessed: {PROC_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
