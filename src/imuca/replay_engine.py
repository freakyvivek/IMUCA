"""
IMUCA Digital Twin Replay Engine.

Extracts frame-by-frame synchronized telemetry from PipelineResult,
tracking instantaneous values, multi-track detector alarms, calibration errors,
and component health states for the 3D Digital Twin.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple
import numpy as np
import pandas as pd

from src.imuca.orchestrator import PipelineResult


@dataclass
class ReplayTelemetry:
    """Instantaneous telemetry snapshot at a specific replay frame."""
    frame_idx: int
    total_frames: int
    elapsed_ms: float
    elapsed_s: float
    timestamp_label: str
    
    # Active measurand
    active_measurand: str
    measurand_unit: str
    measurand_val: Optional[float]
    measurand_ref: Optional[float]
    measurand_error: Optional[float]
    
    # Per-channel live values
    voltage_V: Optional[float]
    voltage_ref_V: Optional[float]
    voltage_error_mV: Optional[float]
    voltage_alarm: bool
    
    current_mA: Optional[float]
    current_ref_mA: Optional[float]
    current_error_mA: Optional[float]
    current_alarm: bool
    
    temperature_C: Optional[float]
    temperature_ref_C: Optional[float]
    temperature_error_degc: Optional[float]
    temperature_alarm: bool
    
    # Multi-track detector flags at current frame
    active_alarms: Dict[str, bool] = field(default_factory=dict)
    has_any_alarm: bool = False
    alarm_category: str = "none"
    confidence_score: float = 0.0
    
    # Data quality status at current frame
    has_quality_issue: bool = False
    quality_issue_code: Optional[str] = None
    quality_description: Optional[str] = None
    
    # Component status map: "nominal" | "warning" | "fault"
    component_status: Dict[str, str] = field(default_factory=dict)
    
    # Metadata
    is_simulated: bool = True
    data_source_description: str = ""


def extract_frame_telemetry(
    result: PipelineResult,
    frame_idx: int
) -> ReplayTelemetry:
    """
    Extract synchronized telemetry at frame_idx from a completed PipelineResult.
    
    Guarantees:
    - Never fabricates readings or asserts physical connection when simulated.
    - Accurately synchronizes multi-track detector alarms and data quality issues.
    """
    df = result.annotated_df
    total_frames = len(df)
    
    if total_frames == 0:
        return ReplayTelemetry(
            frame_idx=0,
            total_frames=0,
            elapsed_ms=0.0,
            elapsed_s=0.0,
            timestamp_label="0.000 s",
            active_measurand=result.measurand,
            measurand_unit=result.unit,
            measurand_val=None,
            measurand_ref=None,
            measurand_error=None,
            voltage_V=None,
            voltage_ref_V=None,
            voltage_error_mV=None,
            voltage_alarm=False,
            current_mA=None,
            current_ref_mA=None,
            current_error_mA=None,
            current_alarm=False,
            temperature_C=None,
            temperature_ref_C=None,
            temperature_error_degc=None,
            temperature_alarm=False,
            is_simulated=result.is_simulated,
            data_source_description=result.data_source_description
        )
    
    # Clamp frame_idx to valid range
    idx = max(0, min(frame_idx, total_frames - 1))
    row = df.iloc[idx]
    
    # Time
    elapsed_ms = float(row["elapsed_ms"]) if "elapsed_ms" in row and pd.notna(row["elapsed_ms"]) else float(idx * 100.0)
    elapsed_s = elapsed_ms / 1000.0
    timestamp_label = f"{elapsed_s:.3f} s ({elapsed_ms:.1f} ms)"
    
    m = result.measurand
    m_unit = result.unit
    
    # Helper to safely extract float from row
    def _get_val(col_names: List[str]) -> Optional[float]:
        for col in col_names:
            if col in row and pd.notna(row[col]):
                try:
                    return float(row[col])
                except (ValueError, TypeError):
                    pass
        return None
    
    # Channel values
    v_val = _get_val(["voltage_V", "meas_voltage_V", "DUT_V", "v_ind", "v_measured", "voltage"])
    v_ref = _get_val(["ref_voltage_V", "reference_voltage_V", "Reference_V", "ref_v", "v_ref"])
    v_err = ((v_val - v_ref) * 1000.0) if (v_val is not None and v_ref is not None) else None
    
    i_val = _get_val(["current_mA", "meas_current_mA", "DUT_mA", "i_ind", "i_measured", "current"])
    i_ref = _get_val(["ref_current_mA", "reference_current_mA", "Reference_mA", "ref_i", "i_ref"])
    i_err = (i_val - i_ref) if (i_val is not None and i_ref is not None) else None
    
    t_val = _get_val(["temperature_C", "meas_temperature_C", "DUT_C", "DUT_temp_C", "temp_ind", "temperature"])
    t_ref = _get_val(["ref_temperature_C", "reference_temperature_C", "Reference_C", "ref_t", "t_ref"])
    t_err = (t_val - t_ref) if (t_val is not None and t_ref is not None) else None
    
    # Active measurand reading
    m_val = _get_val([m, "DUT_V" if m == "voltage_V" else ("DUT_mA" if m == "current_mA" else "DUT_C")])

    m_ref = None
    if m == "voltage_V":
        m_ref = v_ref
    elif m == "current_mA":
        m_ref = i_ref
    elif m == "temperature_C":
        m_ref = t_ref
    m_err = (m_val - m_ref) if (m_val is not None and m_ref is not None) else None
    
    # Detector alarms at this frame
    active_alarms: Dict[str, bool] = {}
    for det_name, mask in result.detector_alarms.items():
        if idx < len(mask):
            active_alarms[det_name] = bool(mask[idx])
        else:
            active_alarms[det_name] = False
            
    has_alarm = any(active_alarms.values())
    
    # Determine predicted alarm category and confidence
    alarm_category = "none"
    conf_score = 0.0
    if "hybrid_m7_predicted_fault" in row and pd.notna(row["hybrid_m7_predicted_fault"]):
        alarm_category = str(row["hybrid_m7_predicted_fault"])
    elif active_alarms.get("integrity", False):
        alarm_category = "integrity"
    elif active_alarms.get("segment_mad", False):
        alarm_category = "transient"
    elif active_alarms.get("cusum", False):
        alarm_category = "drift"
    elif active_alarms.get("ml_gbt", False):
        alarm_category = "anomaly"
        
    if has_alarm:
        conf_score = 0.95 if active_alarms.get("hybrid_m7") else 0.85
    
    # Channel specific alarm flags
    v_alarm = (m == "voltage_V" and has_alarm) or bool(active_alarms.get("hybrid_m7", False) and m == "voltage_V")
    i_alarm = (m == "current_mA" and has_alarm) or bool(active_alarms.get("hybrid_m7", False) and m == "current_mA")
    t_alarm = (m == "temperature_C" and has_alarm) or bool(active_alarms.get("hybrid_m7", False) and m == "temperature_C")
    
    # Check data quality issues at this record index
    has_dq_issue = False
    dq_code = None
    dq_desc = None
    for issue in result.quality_report.issues:
        if issue.record_index == idx:
            has_dq_issue = True
            dq_code = issue.issue_type
            dq_desc = issue.description
            break
            
    # Component status map: "nominal" | "warning" | "fault"
    comp_status: Dict[str, str] = {
        "controller": "nominal",
        "voltage_channel": "nominal",
        "current_shunt": "nominal",
        "temperature_probe": "nominal",
        "reference_standard": "nominal",
        "demarcation_barrier": "nominal",
        "software_kernel": "nominal"
    }
    
    # Controller status: warning if data quality issue, fault if integrity failure
    if active_alarms.get("integrity", False):
        comp_status["controller"] = "fault"
    elif has_dq_issue:
        comp_status["controller"] = "warning"
        
    # Channel statuses
    if v_alarm:
        comp_status["voltage_channel"] = "fault"
    elif has_dq_issue and m == "voltage_V":
        comp_status["voltage_channel"] = "warning"
        
    if i_alarm:
        comp_status["current_shunt"] = "fault"
    elif has_dq_issue and m == "current_mA":
        comp_status["current_shunt"] = "warning"
        
    if t_alarm:
        comp_status["temperature_probe"] = "fault"
    elif has_dq_issue and m == "temperature_C":
        comp_status["temperature_probe"] = "warning"
        
    # Software kernel status
    if has_alarm:
        comp_status["software_kernel"] = "fault"
    elif has_dq_issue:
        comp_status["software_kernel"] = "warning"
        
    # Reference standard is always in-calibration / nominal
    comp_status["reference_standard"] = "nominal"
    
    return ReplayTelemetry(
        frame_idx=idx,
        total_frames=total_frames,
        elapsed_ms=elapsed_ms,
        elapsed_s=elapsed_s,
        timestamp_label=timestamp_label,
        active_measurand=m,
        measurand_unit=m_unit,
        measurand_val=m_val,
        measurand_ref=m_ref,
        measurand_error=m_err,
        voltage_V=v_val,
        voltage_ref_V=v_ref,
        voltage_error_mV=v_err,
        voltage_alarm=v_alarm,
        current_mA=i_val,
        current_ref_mA=i_ref,
        current_error_mA=i_err,
        current_alarm=i_alarm,
        temperature_C=t_val,
        temperature_ref_C=t_ref,
        temperature_error_degc=t_err,
        temperature_alarm=t_alarm,
        active_alarms=active_alarms,
        has_any_alarm=has_alarm,
        alarm_category=alarm_category,
        confidence_score=conf_score,
        has_quality_issue=has_dq_issue,
        quality_issue_code=dq_code,
        quality_description=dq_desc,
        component_status=comp_status,
        is_simulated=result.is_simulated,
        data_source_description=result.data_source_description
    )


def get_rolling_window(
    df: pd.DataFrame,
    current_idx: int,
    window_size: int = 120
) -> pd.DataFrame:
    """
    Get a rolling window dataframe up to current_idx for real-time oscilloscope-style display.
    """
    if df.empty:
        return df
    
    start_idx = max(0, current_idx - window_size + 1)
    end_idx = min(len(df), current_idx + 1)
    return df.iloc[start_idx:end_idx].copy()
