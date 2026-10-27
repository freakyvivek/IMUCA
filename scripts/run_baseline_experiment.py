#!/usr/bin/env python3
"""
IMUCA Baseline Metrology Experiment Runner.

Executes reproducible synthetic experiments across the three measurands:
1. DC Voltage: Calibration sweep, repeatability, and GUM budget evaluation.
2. DC Current: Indirect shunt resistor measurement model, sensitivity analysis, and train/test calibration.
3. Temperature: Temporal sensor aging drift tracking, time-to-breach forecast, and CUSUM change detection.
4. Anomaly Screening: Data-quality assessment against known injected faults (Precision, Recall, FAR, MDR).

Outputs:
- Machine-readable CSVs in data/synthetic/ and data/processed/
- JSON audit reports, Markdown executive summaries, and publication plots in results/
"""

import os
import sys
import json
from pathlib import Path
import numpy as np
import pandas as pd

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from src.imuca import (
    SyntheticDataGenerator,
    DataQualityAssessor,
    compute_error_metrics,
    compute_descriptive_statistics,
    compute_residual_diagnostics,
    evaluate_type_a,
    evaluate_type_b,
    evaluate_shunt_current_uncertainty,
    build_uncertainty_budget,
    CalibrationEngine,
    evaluate_guard_banded_conformity,
    analyze_temporal_drift,
    MetrologyReportGenerator
)


def load_config() -> dict:
    config_path = WORKSPACE_ROOT / "config" / "default_config.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def run_voltage_experiment(gen: SyntheticDataGenerator, reporter: MetrologyReportGenerator, config: dict):
    print("\n" + "=" * 70)
    print("EXPERIMENT 1: DC Voltage Calibration Sweep & GUM Uncertainty Budget")
    print("=" * 70)

    scenarios = gen.create_standard_scenarios()
    sc_cfg = scenarios["nominal_voltage_baseline"]
    df, meta = gen.generate_scenario(sc_cfg)

    # 1. Save synthetic raw data
    raw_path, meta_path = gen.save_dataset(df, meta, str(WORKSPACE_ROOT / "data" / "synthetic"))
    print(f"  [+] Generated synthetic dataset: {os.path.basename(raw_path)}")

    # 2. Data Quality Assessment
    v_cfg = config.get("measurands", {}).get("voltage_V", {})
    assessor = DataQualityAssessor(mad_threshold=config.get("quality", {}).get("mad_threshold", 3.5))
    dq_report = assessor.assess(
        df,
        measurand_col="voltage_V",
        range_limits=(v_cfg.get("min_range", 0.0), v_cfg.get("max_range", 26.0)),
        ground_truth_fault_col="is_injected_fault"
    )
    print(f"  [+] Quality screening: {dq_report.clean_records_count}/{dq_report.total_records} clean records")

    # 3. Baseline Error Metrics
    err_uncal = compute_error_metrics(df["voltage_V"].values, df["reference_voltage_V"].values)
    print(f"  [+] Uncalibrated Bias: {err_uncal.mean_bias*1000:.3f} mV | MAE: {err_uncal.mae*1000:.3f} mV | RMSE: {err_uncal.rmse*1000:.3f} mV")

    # 4. Calibration Train/Validation Separation (60% Train, 40% Validation)
    engine = CalibrationEngine()
    cal_comp = engine.evaluate_train_validation_split(
        x_dut=df["voltage_V"].values,
        y_ref=df["reference_voltage_V"].values,
        train_ratio=config.get("calibration", {}).get("default_train_ratio", 0.6),
        model_type="auto",
        random_seed=42
    )
    print(f"  [+] Calibration Model: {cal_comp.model.model_type} (R^2 = {cal_comp.model.r_squared:.6f})")
    print(f"  [+] Held-out MAE reduction: {cal_comp.mae_reduction_percent:.1f}% | RMSE reduction: {cal_comp.rmse_reduction_percent:.1f}%")

    # 5. GUM Uncertainty Budget Evaluation at 5.000 V
    v_5v_readings = df[np.isclose(df["reference_voltage_V"], 5.0, atol=0.05)]["voltage_V"].values
    if len(v_5v_readings) >= 2:
        u_type_a = evaluate_type_a(v_5v_readings, unit="V", name="Repeatability (Type A)")
    else:
        u_type_a = evaluate_type_a(df["voltage_V"].values[:10], unit="V", name="Repeatability (Type A)")

    u_res = evaluate_type_b("Display Resolution", limit_value=0.001, distribution="RECTANGULAR", unit="V")
    u_mfg = evaluate_type_b("DUT Specification Tolerance", limit_value=5.0 * 0.001, distribution="RECTANGULAR", unit="V")
    u_ref = evaluate_type_b("Reference Standard (Calibrated)", limit_value=0.001, distribution="NORMAL", unit="V")
    u_env = evaluate_type_b("Ambient Temperature Effect", limit_value=0.0005, distribution="RECTANGULAR", unit="V")

    budget = build_uncertainty_budget(
        measurand_name="DC Voltage",
        nominal_value=5.000,
        measurand_unit="V",
        components=[u_type_a, u_res, u_mfg, u_ref, u_env],
        confidence_level=0.95,
        force_k=2.0,
        run_monte_carlo=True,
        mc_trials=10000
    )
    print(f"  [+] Combined Uncertainty u_c: {budget.combined_standard_uncertainty*1000:.3f} mV")
    print(f"  [+] Expanded Uncertainty U (k=2.0): {budget.expanded_uncertainty*1000:.3f} mV")
    print(f"  [+] Dominant Contributor: {budget.dominant_component.name} ({budget.dominant_component.variance_share_percent:.1f}%)")
    print(f"  [+] Result: {budget.reported_result_string}")

    # 6. Apply calibration to full dataset and export
    df_processed = df.copy()
    df_processed["calibrated_voltage_V"] = cal_comp.model.predict(df["voltage_V"].values)
    err_cal = compute_error_metrics(df_processed["calibrated_voltage_V"].values, df["reference_voltage_V"].values)

    proc_path = WORKSPACE_ROOT / "data" / "processed" / "voltage_baseline_processed.csv"
    df_processed.to_csv(proc_path, index=False)

    # 7. Generate Diagnostic Plots and Reports
    plots = reporter.generate_plots(
        experiment_id="EXP_01_VOLTAGE",
        ref_values=df["reference_voltage_V"].values,
        dut_uncal=df["voltage_V"].values,
        dut_cal=df_processed["calibrated_voltage_V"].values,
        time_s=df["elapsed_ms"].values / 1000.0,
        uncertainty_half_width=budget.expanded_uncertainty,
        measurand_name="DC Voltage",
        measurand_unit="V"
    )

    json_path = reporter.generate_json_report(
        experiment_id="EXP_01_VOLTAGE",
        config=sc_cfg.to_dict(),
        quality_report=dq_report,
        uncalibrated_metrics=err_uncal,
        calibrated_metrics=err_cal,
        uncertainty_budget=budget,
        calibration_comparison=cal_comp
    )
    md_path = reporter.generate_markdown_summary("EXP_01_VOLTAGE", json_path, plots)
    print(f"  [+] Exported JSON report: {os.path.basename(json_path)}")
    print(f"  [+] Exported Markdown summary: {os.path.basename(md_path)}")


def run_current_experiment(gen: SyntheticDataGenerator, reporter: MetrologyReportGenerator, config: dict):
    print("\n" + "=" * 70)
    print("EXPERIMENT 2: DC Current Indirect Shunt Model & Calibration")
    print("=" * 70)

    scenarios = gen.create_standard_scenarios()
    sc_cfg = scenarios["current_calibration_sweep"]
    df, meta = gen.generate_scenario(sc_cfg)

    raw_path, meta_path = gen.save_dataset(df, meta, str(WORKSPACE_ROOT / "data" / "synthetic"))
    print(f"  [+] Generated synthetic dataset: {os.path.basename(raw_path)}")

    # Data quality
    assessor = DataQualityAssessor()
    dq_report = assessor.assess(
        df,
        measurand_col="current_mA",
        range_limits=(0.0, 3200.0),
        ground_truth_fault_col="is_injected_fault"
    )

    # Error metrics
    err_uncal = compute_error_metrics(df["current_mA"].values, df["reference_current_mA"].values)
    print(f"  [+] Uncalibrated Bias: {err_uncal.mean_bias:.2f} mA | MAE: {err_uncal.mae:.2f} mA | RMSE: {err_uncal.rmse:.2f} mA")

    # Calibration train/validation
    engine = CalibrationEngine()
    cal_comp = engine.evaluate_train_validation_split(
        x_dut=df["current_mA"].values,
        y_ref=df["reference_current_mA"].values,
        train_ratio=0.6,
        model_type="auto",
        random_seed=42
    )
    print(f"  [+] Model: {cal_comp.model.model_type} | Post-cal MAE reduction: {cal_comp.mae_reduction_percent:.1f}%")

    # Indirect Shunt Resistor Uncertainty Model: I = V_shunt / R_shunt
    # At nominal 1000 mA (1.0 A) with R_shunt = 0.100 Ohm -> V_shunt = 0.100 V
    # u(V_shunt) = 0.05 mV = 0.00005 V, u(R_shunt) = 0.5% of 0.100 Ohm = 0.0005 Ohm
    nom_i, shunt_comps = evaluate_shunt_current_uncertainty(
        v_shunt_v=0.100,
        r_shunt_ohm=0.100,
        u_v_shunt_v=0.00005,
        u_r_shunt_ohm=0.0005
    )
    # Scale shunt component sensitivity coefficients from A to mA:
    # d(I_mA)/dV = 1000 * c_V, d(I_mA)/dR = 1000 * c_R
    from src.imuca.uncertainty import UncertaintyComponent
    shunt_comps_ma = [
        UncertaintyComponent(
            name=c.name,
            source_category=c.source_category,
            uncertainty_type=c.uncertainty_type,
            distribution=c.distribution,
            input_value=c.input_value,
            unit=c.unit,
            divisor=c.divisor,
            standard_uncertainty=c.standard_uncertainty,
            sensitivity_coefficient=c.sensitivity_coefficient * 1000.0,
            uncertainty_contribution=abs(c.sensitivity_coefficient * 1000.0) * c.standard_uncertainty,
            degrees_of_freedom=c.degrees_of_freedom,
            notes=c.notes
        )
        for c in shunt_comps
    ]
    u_type_a = evaluate_type_a(df["current_mA"].values[:10], unit="mA", name="Current Repeatability (Type A)")

    all_comps = [u_type_a] + shunt_comps_ma
    budget = build_uncertainty_budget(
        measurand_name="DC Current",
        nominal_value=nom_i * 1000.0, # in mA
        measurand_unit="mA",
        components=all_comps,
        confidence_level=0.95,
        force_k=2.0
    )
    print(f"  [+] Shunt Model Combined Uncertainty u_c(I): {budget.combined_standard_uncertainty:.2f} mA")
    print(f"  [+] Shunt Model Expanded Uncertainty U (k=2): {budget.expanded_uncertainty:.2f} mA")
    print(f"  [+] Dominant Source: {budget.dominant_component.name} ({budget.dominant_component.variance_share_percent:.1f}%)")

    # Apply calibration to full dataset
    df_processed = df.copy()
    df_processed["calibrated_current_mA"] = cal_comp.model.predict(df["current_mA"].values)
    err_cal = compute_error_metrics(df_processed["calibrated_current_mA"].values, df["reference_current_mA"].values)

    proc_path = WORKSPACE_ROOT / "data" / "processed" / "current_baseline_processed.csv"
    df_processed.to_csv(proc_path, index=False)

    plots = reporter.generate_plots(
        experiment_id="EXP_02_CURRENT",
        ref_values=df["reference_current_mA"].values,
        dut_uncal=df["current_mA"].values,
        dut_cal=df_processed["calibrated_current_mA"].values,
        time_s=df["elapsed_ms"].values / 1000.0,
        uncertainty_half_width=budget.expanded_uncertainty,
        measurand_name="DC Current",
        measurand_unit="mA"
    )

    json_path = reporter.generate_json_report(
        experiment_id="EXP_02_CURRENT",
        config=sc_cfg.to_dict(),
        quality_report=dq_report,
        uncalibrated_metrics=err_uncal,
        calibrated_metrics=err_cal,
        uncertainty_budget=budget,
        calibration_comparison=cal_comp
    )
    reporter.generate_markdown_summary("EXP_02_CURRENT", json_path, plots)
    print(f"  [+] Exported reports and plots for EXP_02_CURRENT")


def run_temperature_experiment(gen: SyntheticDataGenerator, reporter: MetrologyReportGenerator, config: dict):
    print("\n" + "=" * 70)
    print("EXPERIMENT 3: Temperature Aging Drift & Breach Forecasting")
    print("=" * 70)

    scenarios = gen.create_standard_scenarios()
    sc_cfg = scenarios["temperature_drift_scenario"]
    df, meta = gen.generate_scenario(sc_cfg)

    raw_path, meta_path = gen.save_dataset(df, meta, str(WORKSPACE_ROOT / "data" / "synthetic"))
    print(f"  [+] Generated synthetic dataset: {os.path.basename(raw_path)}")

    # Data Quality
    assessor = DataQualityAssessor()
    dq_report = assessor.assess(
        df,
        measurand_col="temperature_C",
        range_limits=(-55.0, 125.0)
    )

    # Drift Analysis
    # Nominal temperature 45.0 °C. Tolerance +/- 2.0% -> USL = 45.9 °C
    drift_res = analyze_temporal_drift(
        timestamps_s=df["elapsed_ms"].values / 1000.0,
        measurements=df["temperature_C"].values,
        nominal_target=45.0,
        upper_limit=48.5
    )
    print(f"  [+] Linear Drift Rate: {drift_res.drift_rate_per_s*1000:.3f} mK/s ({drift_res.drift_rate_per_s*3600:.2f} °C/hour)")
    print(f"  [+] Statistically Significant Drift: {drift_res.is_drift_significant} (p-value: {drift_res.p_value:.3e})")
    if drift_res.forecast_seconds_to_breach:
        print(f"  [+] Forecasted Time-to-Breach: {drift_res.forecast_seconds_to_breach:.1f} seconds")
    print(f"  [+] CUSUM Shift Detected: {drift_res.cusum_detected_shift}")

    # Uncertainty Budget for DS18B20 Temperature
    u_res = evaluate_type_b("Digital Quantization (12-bit)", limit_value=0.0625, distribution="RECTANGULAR", unit="degC")
    u_mfg = evaluate_type_b("Sensor Calibration Tolerance", limit_value=0.50, distribution="NORMAL", unit="degC")
    u_self_heat = evaluate_type_b("Self-Heating Dissipation", limit_value=0.08, distribution="RECTANGULAR", unit="degC")
    u_env_gradient = evaluate_type_b("Thermal Gradient", limit_value=0.10, distribution="TRIANGULAR", unit="degC")

    budget = build_uncertainty_budget(
        measurand_name="Temperature",
        nominal_value=45.0,
        measurand_unit="degC",
        components=[u_res, u_mfg, u_self_heat, u_env_gradient],
        confidence_level=0.95,
        force_k=2.0
    )
    print(f"  [+] Temperature Expanded Uncertainty U (k=2): +/- {budget.expanded_uncertainty:.3f} °C")

    err_uncal = compute_error_metrics(df["temperature_C"].values, df["reference_temperature_C"].values)

    plots = reporter.generate_plots(
        experiment_id="EXP_03_TEMPERATURE",
        ref_values=df["reference_temperature_C"].values,
        dut_uncal=df["temperature_C"].values,
        dut_cal=None,
        time_s=df["elapsed_ms"].values / 1000.0,
        uncertainty_half_width=budget.expanded_uncertainty,
        measurand_name="Temperature",
        measurand_unit="°C"
    )

    json_path = reporter.generate_json_report(
        experiment_id="EXP_03_TEMPERATURE",
        config=sc_cfg.to_dict(),
        quality_report=dq_report,
        uncalibrated_metrics=err_uncal,
        calibrated_metrics=None,
        uncertainty_budget=budget,
        drift_result=drift_res
    )
    reporter.generate_markdown_summary("EXP_03_TEMPERATURE", json_path, plots)
    print(f"  [+] Exported reports and plots for EXP_03_TEMPERATURE")


def run_fault_detection_experiment(gen: SyntheticDataGenerator, reporter: MetrologyReportGenerator, config: dict):
    print("\n" + "=" * 70)
    print("EXPERIMENT 4: Data Quality & Fault Detection Benchmark")
    print("=" * 70)

    scenarios = gen.create_standard_scenarios()
    sc_cfg = scenarios["fault_stress_scenario"]
    df, meta = gen.generate_scenario(sc_cfg)

    raw_path, meta_path = gen.save_dataset(df, meta, str(WORKSPACE_ROOT / "data" / "synthetic"))
    print(f"  [+] Generated synthetic fault stress dataset: {os.path.basename(raw_path)}")

    assessor = DataQualityAssessor(mad_threshold=3.5)
    dq_report = assessor.assess(
        df,
        measurand_col="voltage_V",
        range_limits=(0.0, 15.0),
        max_rate_of_change=1.0,
        ground_truth_fault_col="is_injected_fault"
    )

    det = dq_report.detection_metrics
    print(f"  [+] Total Records: {dq_report.total_records} | Injected Faults: {meta['summary_statistics']['injected_fault_count']}")
    print(f"  [+] Confusion Matrix: TP={det.true_positives}, FP={det.false_positives}, TN={det.true_negatives}, FN={det.false_negatives}")
    print(f"  [+] Detection Precision: {det.precision*100:.1f}%")
    print(f"  [+] Detection Recall:    {det.recall*100:.1f}%")
    print(f"  [+] False Alarm Rate:   {det.false_alarm_rate*100:.2f}%")
    print(f"  [+] Missed Detection:   {det.missed_detection_rate*100:.2f}%")
    print(f"  [+] F1-Score:           {det.f1_score:.3f}")


def main():
    print("======================================================================")
    print("   IMUCA: Autonomous Metrology Foundation Baseline Experiment Suite   ")
    print("======================================================================")
    config = load_config()
    gen = SyntheticDataGenerator(seed=config.get("system", {}).get("default_random_seed", 42))
    reporter = MetrologyReportGenerator(output_dir=str(WORKSPACE_ROOT / "results"))

    run_voltage_experiment(gen, reporter, config)
    run_current_experiment(gen, reporter, config)
    run_temperature_experiment(gen, reporter, config)
    run_fault_detection_experiment(gen, reporter, config)

    print("\n" + "=" * 70)
    print("SUCCESS: All 4 baseline metrology experiments executed cleanly.")
    print("Results and plots saved to 'results/' directory.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
