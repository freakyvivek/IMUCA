"""
IMUCA Unified End-to-End Metrology Orchestrator.

Integrates the complete IMUCA pipeline:
1. Data source acquisition (Simulation replay or Physical Serial adapter).
2. Schema validation and canonical SI unit alignment (Section 4).
3. Data quality & integrity pre-checks (Section 7).
4. Statistical measurement metrics & error analysis (Section 8).
5. GUM-compliant uncertainty budget (Type A + Type B, Welch-Satterthwaite, Student-t) (Section 9).
6. Calibration regression & residual analysis (Section 10).
7. ILAC-G8 guard-banded conformity assessment (Section 11).
8. Multi-track fault detection (Integrity rules, Segment MAD, Causal GBT, Tuned CUSUM, and Hybrid M7).
9. Alarm lifecycle management (Activation, provisional/confirmed category, persistence, clearance).
10. Audit logging and export formatting.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List, Tuple, Union
from pathlib import Path
from datetime import datetime, timezone
import math
import os
import joblib
import numpy as np
import pandas as pd

from src.imuca.schema import (
    MeasurementRecord,
    CANONICAL_COLUMNS,
    validate_schema,
    SchemaValidationResult,
    convert_voltage,
    convert_current,
    convert_temperature
)
from src.imuca.hardware_adapter import (
    MeasurementSource,
    SimulationReplaySource,
    SerialHardwareAdapter,
    MeasurementPacket,
    decode_status_flags,
    HardwareFlags
)
from src.imuca.data_quality import (
    DataQualityAssessor,
    QualityAssessmentReport,
    QualityIssue
)
from src.imuca.measurement_metrics import (
    compute_descriptive_statistics,
    compute_error_metrics,
    DescriptiveStatistics,
    ErrorMetrics
)
from src.imuca.uncertainty import (
    evaluate_type_a,
    evaluate_type_b,
    evaluate_shunt_current_uncertainty,
    build_uncertainty_budget,
    round_uncertainty_metrology,
    UncertaintyBudget,
    UncertaintyComponent
)
from src.imuca.calibration import (
    CalibrationEngine,
    CalibrationModel
)
from src.imuca.validation import (
    evaluate_guard_banded_conformity,
    analyze_temporal_drift,
    ConformityAssessmentResult,
    DriftAnalysisResult
)
from src.imuca.cusum_tuning import run_cusum
from src.imuca.detection_metrics import alarm_episodes


# ==============================================================================
# Pipeline Configuration & Result Classes
# ==============================================================================

@dataclass
class PipelineConfig:
    """Execution parameters for the end-to-end metrology and anomaly detection pipeline."""
    measurand: str = "voltage_V"                 # 'voltage_V' | 'current_mA' | 'temperature_C'
    tolerance_percent: float = 1.0               # Spec tolerance band (+/- % of reading)
    confidence_level: float = 0.95               # Default 95% confidence
    coverage_k: Optional[float] = None           # None = Auto (Student's t via nu_eff)
    calibration_model_type: str = "linear"       # 'uncalibrated' | 'linear' | 'polynomial'
    f_test_alpha: float = 0.05
    mad_threshold: float = 3.5
    nominal_shunt_resistance_ohm: float = 0.100  # INA219 shunt nominal
    shunt_tolerance_percent: float = 0.5         # Shunt tolerance %
    shunt_tcr_ppm: float = 150.0                 # Shunt TCR in ppm/°C
    temp_delta_degc: float = 3.0                 # Ambient temperature uncertainty
    frozen_bundle_dir: str = "results/hybrid_frozen_20261027_210333"
    enable_ml_detectors: bool = True
    enable_cusum: bool = True
    enable_hybrid_m7: bool = True


@dataclass
class PipelineResult:
    """Complete diagnostic and analytical results produced by the unified pipeline."""
    measurand: str
    unit: str
    raw_records_count: int
    clean_records_count: int
    schema_validation: SchemaValidationResult
    quality_report: QualityAssessmentReport
    descriptive_statistics: DescriptiveStatistics
    error_metrics: Optional[ErrorMetrics]
    calibration_model: Optional[CalibrationModel]
    uncertainty_budget: UncertaintyBudget
    conformity_result: Optional[ConformityAssessmentResult]
    drift_result: Optional[DriftAnalysisResult]
    detector_alarms: Dict[str, np.ndarray]
    alarm_episodes_df: pd.DataFrame
    annotated_df: pd.DataFrame
    audit_log: List[str]
    is_simulated: bool
    data_source_description: str
    assumptions_and_limitations: List[str]

    def to_summary_dict(self) -> Dict[str, Any]:
        """Convert key metrics to a serializable summary dictionary."""
        return {
            "measurand": self.measurand,
            "unit": self.unit,
            "raw_records": self.raw_records_count,
            "clean_records": self.clean_records_count,
            "is_simulated": self.is_simulated,
            "data_source": self.data_source_description,
            "mean": self.descriptive_statistics.mean,
            "std_dev": self.descriptive_statistics.sample_std_dev,
            "combined_uncertainty": self.uncertainty_budget.combined_standard_uncertainty,
            "expanded_uncertainty": self.uncertainty_budget.expanded_uncertainty,
            "coverage_k": self.uncertainty_budget.coverage_factor_k,
            "reported_result": self.uncertainty_budget.reported_result_string,
            "dominant_uncertainty_source": self.uncertainty_budget.dominant_component.name,
            "dominant_variance_percent": self.uncertainty_budget.dominant_component.variance_share_percent,
            "guard_banded_conformity": self.conformity_result.guard_banded_conformity if self.conformity_result else "NOT_ASSESSED",
            "total_alarm_episodes": len(self.alarm_episodes_df),
            "quality_issues_count": len(self.quality_report.issues)
        }


# ==============================================================================
# Metrology Orchestrator Engine
# ==============================================================================

class MetrologyOrchestrator:
    """
    Coordinates end-to-end data processing, calibration, uncertainty analysis,
    and multi-detector fault detection across physical and simulated streams.
    """

    MEASURAND_UNITS = {
        "voltage_V": "V",
        "current_mA": "mA",
        "temperature_C": "°C"
    }

    MEASURAND_RANGES = {
        "voltage_V": (0.0, 32.0),
        "current_mA": (0.0, 5000.0),
        "temperature_C": (-40.0, 125.0)
    }

    def __init__(self, workspace_root: Optional[Union[str, Path]] = None):
        self.workspace_root = Path(workspace_root) if workspace_root else Path.cwd()
        self._cached_detectors: Dict[str, Any] = {}

    def _resolve_data(
        self,
        data: Union[pd.DataFrame, str, Path, MeasurementSource]
    ) -> Tuple[pd.DataFrame, bool, str]:
        """Resolve various input types to a pandas DataFrame with simulation metadata."""
        if isinstance(data, MeasurementSource):
            if isinstance(data, SimulationReplaySource):
                df = data.get_full_dataframe()
                is_sim = True
                desc = f"Simulation Replay: {data.source_name}"
            else:
                # Read all available packets from source
                packets = []
                while True:
                    pkt = data.read_packet(timeout_s=0.1)
                    if pkt is None:
                        break
                    packets.append(pkt.to_dict())
                df = pd.DataFrame(packets) if packets else pd.DataFrame(columns=CANONICAL_COLUMNS)
                is_sim = not data.get_status().is_hardware_connected
                desc = f"Hardware Source: {data.get_status().port_or_path}"
        elif isinstance(data, (str, Path)):
            path = Path(data)
            df = pd.read_csv(path)
            is_sim = True  # File import without hardware connection is synthetic or recorded
            desc = f"CSV File: {path.name}"
        elif isinstance(data, pd.DataFrame):
            df = data.copy()
            # If explicit data_source or simulation flag exists, inspect it
            is_sim = True
            if "data_source" in df.columns:
                sources = df["data_source"].astype(str).unique()
                if any("serial" in s.lower() for s in sources):
                    is_sim = False
            desc = "In-Memory Dataset"
        else:
            raise TypeError(f"Unsupported data source type: {type(data)}")

        return df, is_sim, desc

    def _load_frozen_bundle(self, bundle_dir_str: str, measurand: str) -> Optional[Dict[str, Any]]:
        """Load frozen detector bundle (joblib) for the specified measurand."""
        cache_key = f"{bundle_dir_str}:{measurand}"
        if cache_key in self._cached_detectors:
            return self._cached_detectors[cache_key]

        bundle_dir = self.workspace_root / bundle_dir_str
        model_path = bundle_dir / "models" / f"{measurand}_detectors.joblib"
        if not model_path.exists():
            return None

        try:
            bundle = joblib.load(model_path)
            self._cached_detectors[cache_key] = bundle
            return bundle
        except Exception:
            return None

    def execute(
        self,
        data: Union[pd.DataFrame, str, Path, MeasurementSource],
        config: Optional[PipelineConfig] = None
    ) -> PipelineResult:
        """
        Execute the full unified metrology and anomaly detection pipeline.
        """
        cfg = config or PipelineConfig()
        m = cfg.measurand
        unit = self.MEASURAND_UNITS.get(m, "arb")
        audit_log: List[str] = []
        assumptions: List[str] = []

        now_utc = datetime.now(timezone.utc).isoformat()
        audit_log.append(f"[{now_utc}] Pipeline started for measurand='{m}' ({unit}).")

        # 1. Ingestion & Simulation Isolation
        raw_df, is_simulated, source_desc = self._resolve_data(data)
        raw_count = len(raw_df)
        audit_log.append(f"Ingested {raw_count} raw records from {source_desc}. Simulated={is_simulated}.")

        # 2. Schema Validation (Section 4)
        schema_res = validate_schema(raw_df, allow_missing_measurands=True)
        if not schema_res.is_valid:
            audit_log.append(f"Schema validation flagged {schema_res.error_record_count} error records.")
        else:
            audit_log.append("Schema validation passed: canonical columns conform.")

        # Ensure essential columns
        df = raw_df.copy()
        if "sequence_number" not in df.columns:
            df["sequence_number"] = np.arange(len(df), dtype=int)
        if "elapsed_ms" not in df.columns:
            df["elapsed_ms"] = np.arange(len(df), dtype=float) * 1000.0
        if "status" not in df.columns:
            df["status"] = "OK"

        # 3. Data Quality & Pre-Inference Integrity Checks (Section 7)
        range_limits = self.MEASURAND_RANGES.get(m, (-1e9, 1e9))
        quality_assessor = DataQualityAssessor(mad_threshold=cfg.mad_threshold)
        quality_report = quality_assessor.assess(
            df=df,
            measurand_col=m,
            range_limits=range_limits,
            ground_truth_fault_col="is_injected_fault" if "is_injected_fault" in df.columns else None
        )
        audit_log.append(
            f"Quality assessment completed: {quality_report.clean_records_count} clean records, "
            f"{quality_report.flagged_records_count} flagged records ({len(quality_report.issues)} total issues)."
        )

        # Integrity records filter: non-finite, status error, sequence violations
        # These leave the signal stream for clean metrological analysis
        annotated_df = quality_report.annotated_dataframe.copy()
        if m not in annotated_df.columns:
            annotated_df[m] = np.nan
        is_err = annotated_df["is_error"].to_numpy(dtype=bool) if "is_error" in annotated_df.columns else np.zeros(len(annotated_df), dtype=bool)
        m_vals = pd.to_numeric(annotated_df[m], errors="coerce").to_numpy(dtype=float)
        is_integrity_fault = (
            annotated_df[m].isna() |
            ~np.isfinite(m_vals) |
            is_err
        )
        clean_df = annotated_df[~is_integrity_fault].copy().reset_index(drop=True)
        clean_count = len(clean_df)
        audit_log.append(f"Integrity filtering retained {clean_count}/{raw_count} records for metrology and inference.")

        # 4. Descriptive Statistics & Error Analysis (Section 8)
        readings = clean_df[m].to_numpy(dtype=float) if (clean_count > 0 and m in clean_df.columns) else np.array([0.0])
        stats_res = compute_descriptive_statistics(readings)

        ref_col = f"reference_{m}"
        has_reference = ref_col in clean_df.columns and clean_df[ref_col].notna().any()
        error_metrics: Optional[ErrorMetrics] = None
        cal_model: Optional[CalibrationModel] = None

        if has_reference:
            ref_readings = clean_df[ref_col].to_numpy(dtype=float)
            error_metrics = compute_error_metrics(readings, ref_readings)
            audit_log.append(f"Reference measurements present: Mean Bias = {error_metrics.mean_bias:.4g} {unit}, RMSE = {error_metrics.rmse:.4g} {unit}.")

            # 5. Calibration Regression (Section 10)
            cal_engine = CalibrationEngine(f_test_alpha=cfg.f_test_alpha)
            if len(readings) >= 3:
                try:
                    cal_model = cal_engine.fit_linear(readings, ref_readings)
                    audit_log.append(f"Calibration linear model fitted: y_corr = {cal_model.formula_string} (R² = {cal_model.r_squared:.6f}).")
                except Exception as e:
                    audit_log.append(f"Calibration model fitting failed: {e}")
        else:
            audit_log.append("Operating in Single-Sensor Mode: No reference measurements available. Calibration model uncalibrated.")

        # 6. Uncertainty Budget (Section 9 - GUM JCGM 100:2008)
        assumptions.append("Type A: Repeated observations are independent, identically distributed, and approximately normal.")
        assumptions.append("Type B: Manufacturer specification limits represent bounds of a rectangular uniform distribution.")
        assumptions.append("Input quantities are treated as mutually uncorrelated (first-order GUM summation in quadrature).")

        components: List[UncertaintyComponent] = []

        # Type A Component
        if len(readings) >= 2:
            type_a_comp = evaluate_type_a(readings, unit=unit, name=f"Repeatability s(mean) on {m}")
            components.append(type_a_comp)
        else:
            assumptions.append("Type A: Insufficient observations (N < 2); nominal repeatability floor assigned.")
            components.append(UncertaintyComponent(
                name="Repeatability floor",
                source_category="REPEATABILITY",
                uncertainty_type="A",
                distribution="NORMAL",
                input_value=1e-4,
                unit=unit,
                divisor=1.0,
                standard_uncertainty=1e-4,
                sensitivity_coefficient=1.0,
                uncertainty_contribution=1e-4,
                degrees_of_freedom=1.0,
                notes="Single observation floor"
            ))

        nominal_val = float(stats_res.mean) if np.isfinite(stats_res.mean) else 1.0

        # Measurand-specific Type B components
        if m == "voltage_V":
            # INA219 12-bit SAR ADC quantization: 4 mV LSB -> a = 2 mV half-width
            components.append(evaluate_type_b(
                name="INA219 ADC resolution",
                limit_value=0.002,  # 2 mV
                distribution="RECTANGULAR",
                unit="V",
                source_category="RESOLUTION",
                notes="Quantization half-width (4 mV LSB / 2)"
            ))
            # INA219 datasheet gain accuracy: +/- 0.5% max
            v_spec_half = abs(nominal_val) * (0.005)
            components.append(evaluate_type_b(
                name="INA219 manufacturer accuracy",
                limit_value=v_spec_half,
                distribution="RECTANGULAR",
                unit="V",
                source_category="TOLERANCE",
                notes="+/- 0.5% of reading over operating temperature"
            ))
            if has_reference:
                components.append(evaluate_type_b(
                    name="Reference standard calibration",
                    limit_value=0.002,  # 2 mV expanded at k=2
                    distribution="NORMAL",
                    unit="V",
                    source_category="REFERENCE_STANDARD",
                    notes="ISO 17025 certificate expanded uncertainty (k = 2)"
                ))
            # Environmental temperature
            v_temp = abs(nominal_val) * (0.00005 * cfg.temp_delta_degc)  # 50 ppm/°C
            components.append(evaluate_type_b(
                name="Ambient temperature effect",
                limit_value=v_temp,
                distribution="RECTANGULAR",
                unit="V",
                source_category="ENVIRONMENT",
                notes=f"+/- {cfg.temp_delta_degc} °C at 50 ppm/°C"
            ))

        elif m == "current_mA":
            # Current indirect model: I = V_shunt / R_shunt
            # Shunt resistor tolerance: 0.100 Ohm +/- 0.5%
            # INA219 shunt LSB: 10 uV -> 0.1 mA
            components.append(evaluate_type_b(
                name="INA219 shunt ADC resolution",
                limit_value=0.05,  # 0.05 mA half-width
                distribution="RECTANGULAR",
                unit="mA",
                source_category="RESOLUTION",
                notes="10 uV LSB over 0.100 Ohm shunt"
            ))
            # Shunt resistance tolerance
            shunt_u = evaluate_type_b(
                name="Shunt resistance tolerance",
                limit_value=abs(nominal_val) * (cfg.shunt_tolerance_percent / 100.0),
                distribution="RECTANGULAR",
                unit="mA",
                source_category="SHUNT_RESISTOR",
                notes=f"+/- {cfg.shunt_tolerance_percent}% R_shunt tolerance"
            )
            components.append(shunt_u)
            # Shunt self-heating and TCR drift
            tcr_frac = (cfg.shunt_tcr_ppm * 1e-6) * cfg.temp_delta_degc
            components.append(evaluate_type_b(
                name="Shunt TCR temperature drift",
                limit_value=abs(nominal_val) * tcr_frac,
                distribution="RECTANGULAR",
                unit="mA",
                source_category="SHUNT_RESISTOR",
                notes=f"{cfg.shunt_tcr_ppm} ppm/°C over +/- {cfg.temp_delta_degc} °C"
            ))

        elif m == "temperature_C":
            # DS18B20 12-bit programmable ADC: 0.0625 °C LSB -> half-width 0.03125 °C
            components.append(evaluate_type_b(
                name="DS18B20 quantization",
                limit_value=0.03125,
                distribution="RECTANGULAR",
                unit="°C",
                source_category="RESOLUTION",
                notes="12-bit programmable resolution (0.0625 °C / 2)"
            ))
            # DS18B20 manufacturer accuracy: +/- 0.5 °C from -10 to +85 °C
            components.append(evaluate_type_b(
                name="DS18B20 datasheet tolerance",
                limit_value=0.5,
                distribution="RECTANGULAR",
                unit="°C",
                source_category="TOLERANCE",
                notes="Manufacturer accuracy +/- 0.5 °C"
            ))
            # Thermal gradient / installation coupling
            components.append(evaluate_type_b(
                name="Thermal probe coupling",
                limit_value=0.2,
                distribution="RECTANGULAR",
                unit="°C",
                source_category="ENVIRONMENT",
                notes="Estimated immersion thermal gradient"
            ))

        budget = build_uncertainty_budget(
            measurand_name=m,
            nominal_value=nominal_val,
            measurand_unit=unit,
            components=components,
            confidence_level=cfg.confidence_level,
            force_k=cfg.coverage_k
        )
        audit_log.append(f"Uncertainty budget built: u_c = {budget.combined_standard_uncertainty:.4g} {unit}, U = {budget.expanded_uncertainty:.4g} {unit} (k={budget.coverage_factor_k:.2f}).")

        # 7. ILAC-G8 Guard-Banded Conformity (Section 11)
        conformity_res: Optional[ConformityAssessmentResult] = None
        if has_reference and len(readings) > 0:
            ref_mean = float(np.mean(clean_df[ref_col].to_numpy(dtype=float)))
            conformity_res = evaluate_guard_banded_conformity(
                measured_value=float(stats_res.mean),
                reference_value=ref_mean,
                expanded_uncertainty=budget.expanded_uncertainty,
                tolerance_percent=cfg.tolerance_percent,
                guard_band_factor=1.0
            )
            audit_log.append(f"ILAC-G8 conformity: {conformity_res.guard_banded_conformity} (margin = {conformity_res.remaining_margin:.4g} {unit}).")

        # Temporal drift check
        drift_res: Optional[DriftAnalysisResult] = None
        if len(readings) >= 10:
            t_s = clean_df["elapsed_ms"].to_numpy(dtype=float) / 1000.0
            t_span = abs(nominal_val) * (cfg.tolerance_percent / 100.0)
            drift_res = analyze_temporal_drift(
                timestamps_s=t_s,
                measurements=readings,
                nominal_target=nominal_val,
                upper_limit=nominal_val + t_span,
                lower_limit=nominal_val - t_span
            )
            if drift_res.is_drift_significant:
                audit_log.append(f"Significant temporal drift detected: {drift_res.drift_rate_per_s:.4g} {unit}/s (p={drift_res.p_value:.2e}).")

        # 8. Multi-Track Fault Detection (Tracks 1 to 4)
        n_raw = len(df)
        detector_alarms: Dict[str, np.ndarray] = {
            "integrity": is_integrity_fault.to_numpy(dtype=bool),
            "segment_mad": np.zeros(n_raw, dtype=bool),
            "ml_gbt": np.zeros(n_raw, dtype=bool),
            "cusum": np.zeros(n_raw, dtype=bool),
            "hybrid_m7": np.zeros(n_raw, dtype=bool)
        }
        category_col = np.array(["none"] * n_raw, dtype=object)
        category_col[detector_alarms["integrity"]] = "integrity"

        frozen_bundle = self._load_frozen_bundle(cfg.frozen_bundle_dir, m) if cfg.enable_hybrid_m7 or cfg.enable_ml_detectors else None

        # Track 1: Segment MAD on clean records
        if clean_count > 0:
            med = float(np.median(readings))
            mad = float(np.median(np.abs(readings - med)))
            clean_indices = np.flatnonzero(~is_integrity_fault)
            if mad > 1e-12:
                mod_z = 0.6745 * np.abs(readings - med) / mad
                seg_alarm = mod_z > cfg.mad_threshold
                detector_alarms["segment_mad"][clean_indices[seg_alarm]] = True
                category_col[clean_indices[seg_alarm]] = "transient"

        # Track 2: ML GBT Detector
        if frozen_bundle is not None and cfg.enable_ml_detectors and "feature_builder" in frozen_bundle and "targeted_gbt" in frozen_bundle:
            builder = frozen_bundle["feature_builder"]
            gbt = frozen_bundle["targeted_gbt"]
            st_cfg = frozen_bundle.get("hybrid_settings")
            try:
                feats, _, _ = builder.transform_run(df)
                if not feats.empty and gbt is not None:
                    scores = gbt.score(feats)
                    threshold = getattr(st_cfg, "gbt_threshold", 0.5) if st_cfg else 0.5
                    gbt_mask = scores > threshold
                    gbt_indices = feats.index.to_numpy()[gbt_mask]
                    detector_alarms["ml_gbt"][gbt_indices] = True
            except Exception as e:
                audit_log.append(f"ML GBT detector evaluation warning: {e}")

        # Track 3: Tuned CUSUM on clean records
        if cfg.enable_cusum and clean_count >= 30 and has_reference:
            err = clean_df[m].to_numpy(dtype=float) - clean_df[ref_col].to_numpy(dtype=float)
            t_s = clean_df["elapsed_ms"].to_numpy(dtype=float) / 1000.0
            k_val = 0.5
            h_val = 5.0
            if frozen_bundle:
                cs = frozen_bundle.get("cusum_settings") if isinstance(frozen_bundle, dict) else getattr(frozen_bundle, "cusum_settings", None)
                if cs is not None:
                    if isinstance(cs, dict):
                        k_val = float(cs.get("k", cs.get("cusum_k", 0.5)))
                        h_val = float(cs.get("h", cs.get("cusum_h", 5.0)))
                    else:
                        k_val = float(getattr(cs, "cusum_k", getattr(cs, "k", 0.5)))
                        h_val = float(getattr(cs, "cusum_h", getattr(cs, "h", 5.0)))
            cusum_out = run_cusum(t_s, err, k_val, h_val, baseline_fraction=0.1, sigma_mode="baseline_window")
            if cusum_out["alarm"]:
                alarm_time = cusum_out["alarm_time_s"]
                cusum_mask = t_s >= alarm_time
                clean_indices = np.flatnonzero(~is_integrity_fault)
                detector_alarms["cusum"][clean_indices[cusum_mask]] = True

        # Track 4: Hybrid M7 Multi-Track Fusion
        if frozen_bundle is not None and cfg.enable_hybrid_m7 and "hybrid_settings" in frozen_bundle:
            try:
                from src.imuca.hybrid_detector import HybridDetector
                builder = frozen_bundle["feature_builder"]
                gbt = frozen_bundle["targeted_gbt"]
                cal_models = frozen_bundle.get("calibration_models", {})
                dev_id = str(df.get("device_id", pd.Series(["DEV_01"])).iloc[0])
                cal_mod = cal_models.get(dev_id, None)
                base_cfg = {
                    "mad_threshold": cfg.mad_threshold,
                    "max_acceptable_gap_factor": 2.5,
                    "nominal_sampling_period_s": 1.0,
                    "range_limits": {m: list(range_limits)},
                    "max_rate_of_change": None
                }
                hd = HybridDetector(
                    measurand=m,
                    feature_builder=builder,
                    persistent_gbt=gbt,
                    calibration_model=cal_mod,
                    base_cfg=base_cfg,
                    settings=frozen_bundle["hybrid_settings"],
                    score_cache=False
                )
                annotated_run = hd.annotate(df)
                if "hybrid_signal_alarm" in annotated_run.columns:
                    detector_alarms["hybrid_m7"] = annotated_run["hybrid_signal_alarm"].to_numpy(dtype=bool) | annotated_run["hybrid_integrity_alarm"].to_numpy(dtype=bool)
                    category_col = annotated_run["hybrid_category"].to_numpy(dtype=object)
            except Exception as e:
                audit_log.append(f"Hybrid M7 execution warning: {e}")
                # Fallback hybrid is OR of components
                detector_alarms["hybrid_m7"] = (
                    detector_alarms["integrity"] |
                    detector_alarms["segment_mad"] |
                    detector_alarms["ml_gbt"] |
                    detector_alarms["cusum"]
                )

        # 9. Unified Alarm Episodes Lifecycle
        primary_alarm = detector_alarms["hybrid_m7"]
        exp_ids = df.get("experiment_id", pd.Series(["EXP_01"] * n_raw)).to_numpy()
        eps = alarm_episodes(primary_alarm, exp_ids, gap=2)

        episode_rows = []
        seq_arr = df["sequence_number"].to_numpy()
        time_arr = df["elapsed_ms"].to_numpy(dtype=float) / 1000.0

        for idx, ep in enumerate(eps):
            s_idx = ep["start"]
            e_idx = ep["end"]
            cat = str(category_col[s_idx])
            fired_components = [det_name for det_name, mask in detector_alarms.items() if mask[s_idx:e_idx + 1].any()]
            dur_samples = int(e_idx - s_idx + 1)
            dur_s = float(time_arr[e_idx] - time_arr[s_idx])

            episode_rows.append({
                "episode_id": f"EP_{idx + 1:03d}",
                "category": cat,
                "start_seq": int(seq_arr[s_idx]),
                "end_seq": int(seq_arr[e_idx]),
                "start_time_s": float(time_arr[s_idx]),
                "end_time_s": float(time_arr[e_idx]),
                "duration_samples": dur_samples,
                "duration_s": dur_s,
                "components": "; ".join(fired_components),
                "is_cleared": e_idx < (n_raw - 1)
            })

        alarm_episodes_df = pd.DataFrame(episode_rows) if episode_rows else pd.DataFrame(columns=[
            "episode_id", "category", "start_seq", "end_seq", "start_time_s", "end_time_s",
            "duration_samples", "duration_s", "components", "is_cleared"
        ])
        audit_log.append(f"Alarm management aggregated {len(alarm_episodes_df)} distinct alarm episodes.")

        # Update annotated DataFrame with predicted alarms (never mixing ground-truth labels)
        for det_name, mask in detector_alarms.items():
            annotated_df[f"alarm_{det_name}"] = mask
        annotated_df["predicted_alarm_category"] = category_col

        audit_log.append("Pipeline execution completed successfully.")

        return PipelineResult(
            measurand=m,
            unit=unit,
            raw_records_count=raw_count,
            clean_records_count=clean_count,
            schema_validation=schema_res,
            quality_report=quality_report,
            descriptive_statistics=stats_res,
            error_metrics=error_metrics,
            calibration_model=cal_model,
            uncertainty_budget=budget,
            conformity_result=conformity_res,
            drift_result=drift_res,
            detector_alarms=detector_alarms,
            alarm_episodes_df=alarm_episodes_df,
            annotated_df=annotated_df,
            audit_log=audit_log,
            is_simulated=is_simulated,
            data_source_description=source_desc,
            assumptions_and_limitations=assumptions
        )
