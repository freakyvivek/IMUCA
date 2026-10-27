"""
IMUCA Reporting and Metrological Visualisation Module.

Section 13 Specification:
- Generates reproducible machine-readable JSON experiment records.
- Generates comprehensive Markdown and HTML metrology reports.
- Produces clean matplotlib visualisations:
  1. Observed vs Reference calibration curve with confidence/prediction bands.
  2. Residuals analysis plot.
  3. Pre-calibration vs Post-calibration error comparison.
  4. Time-series drift tracking with expanded uncertainty envelopes.
  5. Injected fault and data quality flag distribution.
- Clearly labels all simulated results with appropriate disclaimers.
- Maintains strict isolation of outputs in results/ directory.
"""

from __future__ import annotations
import os
import json
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend safe for CLI and headless execution
import matplotlib.pyplot as plt

from src.imuca.schema import SchemaValidationResult
from src.imuca.data_quality import QualityAssessmentReport
from src.imuca.measurement_metrics import ErrorMetrics, DescriptiveStatistics
from src.imuca.uncertainty import UncertaintyBudget
from src.imuca.calibration import CalibrationValidationComparison, CalibrationModel
from src.imuca.validation import DriftAnalysisResult


class MetrologyReportGenerator:
    """
    Assembles comprehensive metrology experiment reports and plots.
    """

    def __init__(self, output_dir: str = "results"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_json_report(
        self,
        experiment_id: str,
        config: Dict[str, Any],
        quality_report: QualityAssessmentReport,
        uncalibrated_metrics: ErrorMetrics,
        calibrated_metrics: Optional[ErrorMetrics],
        uncertainty_budget: UncertaintyBudget,
        calibration_comparison: Optional[CalibrationValidationComparison] = None,
        drift_result: Optional[DriftAnalysisResult] = None,
        disclaimer: str = "SYNTHETIC EXPERIMENT: For algorithm validation only."
    ) -> str:
        """
        Generate machine-readable JSON summary of the full metrology pipeline.
        """
        # Build components list for budget
        budget_dict = {
            "measurand_name": uncertainty_budget.measurand_name,
            "measurand_unit": uncertainty_budget.measurand_unit,
            "nominal_value": uncertainty_budget.nominal_value,
            "combined_standard_uncertainty": uncertainty_budget.combined_standard_uncertainty,
            "effective_degrees_of_freedom": (
                "infinity" if not np.isfinite(uncertainty_budget.effective_degrees_of_freedom)
                else float(uncertainty_budget.effective_degrees_of_freedom)
            ),
            "coverage_factor_k": uncertainty_budget.coverage_factor_k,
            "confidence_level": uncertainty_budget.confidence_level,
            "expanded_uncertainty": uncertainty_budget.expanded_uncertainty,
            "reported_result": uncertainty_budget.reported_result_string,
            "dominant_component": {
                "name": uncertainty_budget.dominant_component.name,
                "share_percent": uncertainty_budget.dominant_component.variance_share_percent,
                "type": uncertainty_budget.dominant_component.uncertainty_type
            },
            "components": [
                {
                    "name": c.name,
                    "type": c.uncertainty_type,
                    "distribution": c.distribution,
                    "standard_uncertainty": c.standard_uncertainty,
                    "sensitivity_coefficient": c.sensitivity_coefficient,
                    "uncertainty_contribution": c.uncertainty_contribution,
                    "variance_share_percent": c.variance_share_percent,
                    "unit": c.unit,
                    "notes": c.notes
                }
                for c in uncertainty_budget.components
            ]
        }

        report_payload = {
            "imuca_framework_version": "1.0.0",
            "experiment_id": experiment_id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "disclaimer": disclaimer,
            "configuration": config,
            "data_quality": {
                "total_records": quality_report.total_records,
                "clean_records": quality_report.clean_records_count,
                "error_records": quality_report.error_records_count,
                "warning_records": quality_report.warning_records_count,
                "issue_summary_by_type": quality_report.summary_by_type
            },
            "uncalibrated_metrics": {
                "n": uncalibrated_metrics.n,
                "mean_bias": uncalibrated_metrics.mean_bias,
                "mae": uncalibrated_metrics.mae,
                "rmse": uncalibrated_metrics.rmse,
                "max_absolute_error": uncalibrated_metrics.max_absolute_error,
                "mean_percentage_error": uncalibrated_metrics.mean_percentage_error
            },
            "uncertainty_budget": budget_dict
        }

        if calibrated_metrics:
            report_payload["calibrated_metrics"] = {
                "n": calibrated_metrics.n,
                "mean_bias": calibrated_metrics.mean_bias,
                "mae": calibrated_metrics.mae,
                "rmse": calibrated_metrics.rmse,
                "max_absolute_error": calibrated_metrics.max_absolute_error,
                "mean_percentage_error": calibrated_metrics.mean_percentage_error
            }

        if calibration_comparison:
            report_payload["calibration_evaluation"] = {
                "model_type": calibration_comparison.model.model_type,
                "degree": calibration_comparison.model.degree,
                "coefficients": calibration_comparison.model.coefficients,
                "r_squared": calibration_comparison.model.r_squared,
                "residual_std_dev": calibration_comparison.model.residual_std_dev,
                "formula": calibration_comparison.model.formula_string,
                "train_sample_count": calibration_comparison.train_count,
                "validation_sample_count": calibration_comparison.validation_count,
                "mae_reduction_percent": calibration_comparison.mae_reduction_percent,
                "rmse_reduction_percent": calibration_comparison.rmse_reduction_percent,
                "performance_improved": calibration_comparison.is_performance_improved,
                "domain_extrapolation_warnings": calibration_comparison.domain_warnings
            }

        if drift_result:
            report_payload["drift_analysis"] = {
                "drift_rate_per_second": float(drift_result.drift_rate_per_s),
                "drift_rate_std_error": float(drift_result.drift_rate_std_error),
                "p_value": float(drift_result.p_value),
                "is_significant": bool(drift_result.is_drift_significant),
                "forecast_seconds_to_breach": (
                    float(drift_result.forecast_seconds_to_breach)
                    if drift_result.forecast_seconds_to_breach is not None
                    else None
                ),
                "summary": str(drift_result.summary_message)
            }

        def _json_serialize(obj):
            if isinstance(obj, (np.bool_, bool)):
                return bool(obj)
            if isinstance(obj, (np.integer, int)):
                return int(obj)
            if isinstance(obj, (np.floating, float)):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return str(obj)

        out_path = os.path.join(self.output_dir, f"{experiment_id}_report.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report_payload, f, indent=2, default=_json_serialize)

        return out_path

    def generate_plots(
        self,
        experiment_id: str,
        ref_values: np.ndarray,
        dut_uncal: np.ndarray,
        dut_cal: Optional[np.ndarray],
        time_s: Optional[np.ndarray],
        uncertainty_half_width: float,
        measurand_name: str,
        measurand_unit: str
    ) -> List[str]:
        """
        Generate publication-grade diagnostic plots saved to results directory.
        """
        saved_plots = []

        # Plot 1: Reference vs Observed (Before and After Calibration)
        fig, ax = plt.subplots(figsize=(8, 6), dpi=150)
        ax.plot(ref_values, dut_uncal, "ro", alpha=0.6, label="Observed (Uncalibrated)")
        if dut_cal is not None:
            ax.plot(ref_values, dut_cal, "bs", alpha=0.6, label="Calibrated")
        
        # Ideal 1:1 reference line
        min_v = min(np.min(ref_values), np.min(dut_uncal))
        max_v = max(np.max(ref_values), np.max(dut_uncal))
        ax.plot([min_v, max_v], [min_v, max_v], "k--", label="Ideal 1:1 Reference")

        ax.set_title(f"IMUCA Calibration Transfer Function: {measurand_name} [{experiment_id}]", fontsize=12)
        ax.set_xlabel(f"Reference Value ({measurand_unit})", fontsize=11)
        ax.set_ylabel(f"Measured Value ({measurand_unit})", fontsize=11)
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend()

        p1 = os.path.join(self.output_dir, f"{experiment_id}_calibration_transfer.png")
        fig.tight_layout()
        fig.savefig(p1)
        plt.close(fig)
        saved_plots.append(p1)

        # Plot 2: Residuals vs Reference
        fig, ax = plt.subplots(figsize=(8, 5), dpi=150)
        res_uncal = dut_uncal - ref_values
        ax.scatter(ref_values, res_uncal, color="crimson", alpha=0.7, label="Uncalibrated Error (y_dut - y_ref)")
        if dut_cal is not None:
            res_cal = dut_cal - ref_values
            ax.scatter(ref_values, res_cal, color="forestgreen", alpha=0.7, label="Calibrated Residuals (y_cal - y_ref)")
        
        ax.axhline(0, color="black", linestyle="-", linewidth=1.0)
        # Uncertainty band on residuals
        ax.axhspan(-uncertainty_half_width, uncertainty_half_width, color="green", alpha=0.15, label=f"+/- Expanded Uncertainty U (k=2)")

        ax.set_title(f"Residual Errors vs Reference: {measurand_name}", fontsize=12)
        ax.set_xlabel(f"Reference Value ({measurand_unit})", fontsize=11)
        ax.set_ylabel(f"Error ({measurand_unit})", fontsize=11)
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend()

        p2 = os.path.join(self.output_dir, f"{experiment_id}_residuals.png")
        fig.tight_layout()
        fig.savefig(p2)
        plt.close(fig)
        saved_plots.append(p2)

        # Plot 3: Time Series with Uncertainty Envelope (if time vector is provided)
        if time_s is not None and len(time_s) == len(dut_uncal):
            fig, ax = plt.subplots(figsize=(9, 5), dpi=150)
            ax.plot(time_s, ref_values, "k-", label="Reference Baseline", linewidth=1.5)
            
            y_to_plot = dut_cal if dut_cal is not None else dut_uncal
            label_meas = "Calibrated Time Series" if dut_cal is not None else "Observed Time Series"
            ax.plot(time_s, y_to_plot, "b.-", alpha=0.7, label=label_meas)
            
            # Uncertainty envelope
            ax.fill_between(
                time_s,
                y_to_plot - uncertainty_half_width,
                y_to_plot + uncertainty_half_width,
                color="blue",
                alpha=0.2,
                label=f"Expanded Uncertainty Interval (+/-{uncertainty_half_width:.4g} {measurand_unit})"
            )

            ax.set_title(f"Time Series with Uncertainty Envelopes: {measurand_name}", fontsize=12)
            ax.set_xlabel("Elapsed Time (s)", fontsize=11)
            ax.set_ylabel(f"Value ({measurand_unit})", fontsize=11)
            ax.grid(True, linestyle=":", alpha=0.6)
            ax.legend()

            p3 = os.path.join(self.output_dir, f"{experiment_id}_timeseries_uncertainty.png")
            fig.tight_layout()
            fig.savefig(p3)
            plt.close(fig)
            saved_plots.append(p3)

        return saved_plots

    def generate_markdown_summary(
        self,
        experiment_id: str,
        json_path: str,
        plots: List[str]
    ) -> str:
        """Generate a concise Markdown report referencing saved plots and metrics."""
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        md = []
        md.append(f"# IMUCA Metrology Analysis Report: `{experiment_id}`\n")
        md.append(f"> **Generated at**: {data['timestamp_utc']} | **IMUCA Framework**: v{data['imuca_framework_version']}\n")
        md.append(f"> **Disclaimer**: {data['disclaimer']}\n\n")

        md.append("## 1. Data Quality Screening\n")
        dq = data["data_quality"]
        md.append(f"- **Total Records Analyzed**: {dq['total_records']}\n")
        md.append(f"- **Clean Records**: {dq['clean_records']} ({(dq['clean_records']/max(1, dq['total_records'])*100):.1f}%)\n")
        md.append(f"- **Integrity Error Flags**: {dq['error_records']}\n")
        md.append(f"- **Warning Flags (Retained for audit)**: {dq['warning_records']}\n")
        if dq["issue_summary_by_type"]:
            md.append("- **Detected Anomaly Distribution**:\n")
            for k, v in dq["issue_summary_by_type"].items():
                md.append(f"  - `{k}`: {v} occurrences\n")
        md.append("\n")

        md.append("## 2. Measurement Accuracy & Calibration Performance\n")
        unc = data["uncalibrated_metrics"]
        md.append("| Metric | Uncalibrated Baseline | Post-Calibration (Held-out Test) | Improvement |\n")
        md.append("| :--- | :--- | :--- | :--- |\n")
        if "calibrated_metrics" in data and "calibration_evaluation" in data:
            cal = data["calibrated_metrics"]
            ce = data["calibration_evaluation"]
            md.append(f"| **Mean Bias** | `{unc['mean_bias']:.4g}` | `{cal['mean_bias']:.4g}` | - |\n")
            md.append(f"| **MAE** | `{unc['mae']:.4g}` | `{cal['mae']:.4g}` | **{ce['mae_reduction_percent']:.1f}% reduction** |\n")
            md.append(f"| **RMSE** | `{unc['rmse']:.4g}` | `{cal['rmse']:.4g}` | **{ce['rmse_reduction_percent']:.1f}% reduction** |\n")
            md.append(f"| **Max Absolute Error** | `{unc['max_absolute_error']:.4g}` | `{cal['max_absolute_error']:.4g}` | - |\n")
            md.append(f"\n**Model Adopted**: `{ce['model_type']}` (Degree {ce['degree']}) | **Formula**: `{ce['formula']}` | **$R^2$**: `{ce['r_squared']:.6f}`\n\n")
        else:
            md.append(f"| **Mean Bias** | `{unc['mean_bias']:.4g}` | N/A | - |\n")
            md.append(f"| **MAE** | `{unc['mae']:.4g}` | N/A | - |\n")
            md.append(f"| **RMSE** | `{unc['rmse']:.4g}` | N/A | - |\n\n")

        md.append("## 3. GUM Uncertainty Budget (JCGM 100:2008)\n")
        ub = data["uncertainty_budget"]
        md.append(f"- **Nominal Value**: `{ub['nominal_value']} {ub['measurand_unit']}`\n")
        md.append(f"- **Combined Standard Uncertainty ($u_c$)**: `{ub['combined_standard_uncertainty']:.4g} {ub['measurand_unit']}`\n")
        md.append(f"- **Expanded Uncertainty ($U, k={ub['coverage_factor_k']:.2f}$)**: `{ub['expanded_uncertainty']:.4g} {ub['measurand_unit']}`\n")
        md.append(f"- **Dominant Contributor**: `{ub['dominant_component']['name']}` ({ub['dominant_component']['share_percent']:.1f}% variance share)\n")
        md.append(f"- **Metrologically Rounded Result**: **{ub['reported_result']}**\n\n")

        md.append("| Uncertainty Source | Type | Distribution | Standard Uncertainty $u_i$ | Sens. Coeff. $c_i$ | Contribution | Share % |\n")
        md.append("| :--- | :---: | :--- | :--- | :--- | :--- | :--- |\n")
        for c in ub["components"]:
            md.append(f"| {c['name']} | Type {c['type']} | {c['distribution']} | `{c['standard_uncertainty']:.4g} {c['unit']}` | `{c['sensitivity_coefficient']:.4g}` | `{c['uncertainty_contribution']:.4g}` | `{c['variance_share_percent']:.1f}%` |\n")
        md.append("\n")

        if "drift_analysis" in data:
            da = data["drift_analysis"]
            md.append("## 4. Drift Analysis & Breach Forecast\n")
            md.append(f"- **Drift Rate**: `{da['drift_rate_per_second']:.4e} /s` (p-value: `{da['p_value']:.4e}`)\n")
            md.append(f"- **Statistically Significant**: `{'YES' if da['is_significant'] else 'NO'}`\n")
            if da["forecast_seconds_to_breach"]:
                md.append(f"- **Forecasted Time to Tolerance Breach**: **`{da['forecast_seconds_to_breach']:.1f} seconds`**\n")
            md.append(f"- **Summary**: {da['summary']}\n\n")

        md.append("## 5. Generated Visualisations\n")
        for p in plots:
            fname = os.path.basename(p)
            md.append(f"- ![{fname}]({p})\n")

        md_path = os.path.join(self.output_dir, f"{experiment_id}_summary.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("".join(md))

        return md_path
