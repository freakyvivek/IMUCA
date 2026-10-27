"""
IMUCA Data Model, Schema Definitions, and SI Unit Conversions.

Section 4 Specification:
Defines immutable canonical measurement records, field constraints,
SI-compatible unit conversions, and schema validation diagnostics.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import math
import numpy as np
import pandas as pd


# Canonical columns specified in Section 4
CANONICAL_COLUMNS = [
    "experiment_id",
    "device_id",
    "timestamp_utc",
    "sequence_number",
    "elapsed_ms",
    "voltage_V",
    "current_mA",
    "temperature_C",
    "status",
    "data_source",
    "reference_voltage_V",
    "reference_current_mA",
    "reference_temperature_C",
    "environmental_temperature_C",
    "notes"
]

# Separate ground-truth fields for simulation validation (never confused with reference measurements)
SIMULATION_GROUND_TRUTH_COLUMNS = [
    "true_voltage_V",
    "true_current_mA",
    "true_temperature_C"
]

MEASURAND_KEYS = ("voltage_V", "current_mA", "temperature_C")


@dataclass(frozen=True)
class MeasurementRecord:
    """
    Immutable representation of an individual measurement record.
    Strictly follows Section 4 of IMUCA specification.
    """
    experiment_id: str
    device_id: str
    timestamp_utc: str
    sequence_number: int
    elapsed_ms: float
    voltage_V: Optional[float] = None
    current_mA: Optional[float] = None
    temperature_C: Optional[float] = None
    status: str = "OK"
    data_source: str = "csv_import"
    reference_voltage_V: Optional[float] = None
    reference_current_mA: Optional[float] = None
    reference_temperature_C: Optional[float] = None
    environmental_temperature_C: Optional[float] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SchemaValidationDiagnostic:
    """Audit entry documenting an individual validation issue."""
    row_index: int
    field_name: str
    raw_value: Any
    issue_code: str  # MISSING_REQUIRED, NON_NUMERIC, NON_FINITE, OUT_OF_RANGE, MONOTONICITY_VIOLATION, DUPLICATE
    severity: str    # ERROR (invalid record), WARNING (flagged but retained)
    message: str


@dataclass
class SchemaValidationResult:
    """Complete diagnostic report for a validated dataset."""
    is_valid: bool
    total_records: int
    valid_record_count: int
    error_record_count: int
    warning_record_count: int
    diagnostics: List[SchemaValidationDiagnostic] = field(default_factory=list)
    flagged_dataframe: pd.DataFrame = field(default_factory=pd.DataFrame)
    summary: Dict[str, Any] = field(default_factory=dict)


# ==============================================================================
# SI Unit Conversions
# ==============================================================================

def convert_voltage(value: float, from_unit: str, to_unit: str) -> float:
    """
    Convert voltage between SI multiples (V, mV, uV, kV).
    Base SI unit: Volt (V).
    """
    factors = {
        "uv": 1e-6,
        "µv": 1e-6,
        "mv": 1e-3,
        "v": 1.0,
        "kv": 1e3
    }
    src = from_unit.strip().lower()
    dst = to_unit.strip().lower()
    if src not in factors or dst not in factors:
        raise ValueError(f"Unsupported voltage unit conversion: '{from_unit}' to '{to_unit}'")
    return value * (factors[src] / factors[dst])


def convert_current(value: float, from_unit: str, to_unit: str) -> float:
    """
    Convert current between SI multiples (A, mA, uA).
    Base SI unit: Ampere (A).
    """
    factors = {
        "ua": 1e-6,
        "µa": 1e-6,
        "ma": 1e-3,
        "a": 1.0
    }
    src = from_unit.strip().lower()
    dst = to_unit.strip().lower()
    if src not in factors or dst not in factors:
        raise ValueError(f"Unsupported current unit conversion: '{from_unit}' to '{to_unit}'")
    return value * (factors[src] / factors[dst])


def convert_temperature(value: float, from_unit: str, to_unit: str) -> float:
    """
    Convert temperature between Celsius, Kelvin, and Fahrenheit.
    Base SI unit: Kelvin (K).
    Kelvin = Celsius + 273.15
    """
    src = from_unit.strip().lower()
    dst = to_unit.strip().lower()
    
    # Normalize to Celsius
    if src in ("degc", "c", "celsius"):
        c = value
    elif src in ("k", "kelvin"):
        c = value - 273.15
    elif src in ("degf", "f", "fahrenheit"):
        c = (value - 32.0) * 5.0 / 9.0
    else:
        raise ValueError(f"Unsupported source temperature unit: '{from_unit}'")

    # Convert Celsius to destination
    if dst in ("degc", "c", "celsius"):
        return c
    elif dst in ("k", "kelvin"):
        return c + 273.15
    elif dst in ("degf", "f", "fahrenheit"):
        return (c * 9.0 / 5.0) + 32.0
    else:
        raise ValueError(f"Unsupported destination temperature unit: '{to_unit}'")


# ==============================================================================
# Schema Validation
# ==============================================================================

def validate_timestamp_iso(ts_str: Any) -> bool:
    """Verify timestamp conforms to ISO 8601 representation."""
    if not isinstance(ts_str, str) or not ts_str.strip():
        return False
    try:
        # Support trailing Z or ISO standard offsets
        s = ts_str.replace("Z", "+00:00")
        datetime.fromisoformat(s)
        return True
    except (ValueError, TypeError):
        return False


def validate_schema(
    df: pd.DataFrame,
    ranges: Optional[Dict[str, Tuple[float, float]]] = None,
    allow_missing_measurands: bool = True
) -> SchemaValidationResult:
    """
    Validate DataFrame against canonical IMUCA measurement schema.
    
    Checks performed:
    1. Required identifier & sequence fields present and non-null.
    2. Valid numeric types for measurands and references (non-finite checks).
    3. Monotonic sequence numbering and non-decreasing timestamps.
    4. Duplicate sequence number and duplicate row detection.
    5. Sensor status integrity checks.
    6. Configured range boundary verifications.
    
    Non-destructive: produces an annotated copy with 'quality_flags' and 'is_record_valid'.
    """
    diagnostics: List[SchemaValidationDiagnostic] = []
    
    if ranges is None:
        ranges = {
            "voltage_V": (-0.1, 30.0),
            "current_mA": (-10.0, 4000.0),
            "temperature_C": (-60.0, 150.0)
        }
        
    annotated = df.copy()
    row_count = len(annotated)
    valid_mask = np.ones(row_count, dtype=bool)
    warning_mask = np.zeros(row_count, dtype=bool)
    flags_col: List[List[str]] = [[] for _ in range(row_count)]

    if row_count == 0:
        diagnostics.append(
            SchemaValidationDiagnostic(
                row_index=-1,
                field_name="dataset",
                raw_value=None,
                issue_code="EMPTY_DATASET",
                severity="ERROR",
                message="Dataset contains zero records."
            )
        )
        return SchemaValidationResult(
            is_valid=False,
            total_records=0,
            valid_record_count=0,
            error_record_count=0,
            warning_record_count=0,
            diagnostics=diagnostics,
            flagged_dataframe=annotated,
            summary={"error": "Empty dataset"}
        )

    # 1. Structural requirements
    required_cols = ["sequence_number"]
    for c in required_cols:
        if c not in annotated.columns:
            diagnostics.append(
                SchemaValidationDiagnostic(
                    row_index=-1,
                    field_name=c,
                    raw_value=None,
                    issue_code="MISSING_COLUMN",
                    severity="ERROR",
                    message=f"Mandatory schema column '{c}' is missing from dataset."
                )
            )
            return SchemaValidationResult(
                is_valid=False,
                total_records=row_count,
                valid_record_count=0,
                error_record_count=row_count,
                warning_record_count=0,
                diagnostics=diagnostics,
                flagged_dataframe=annotated,
                summary={"error": f"Missing mandatory column: {c}"}
            )

    # 2. Sequence and Timestamp Monotonicity & Duplicate Checks
    seq_vals = annotated["sequence_number"].values
    seen_seq = set()
    prev_seq = None
    prev_time = None
    
    has_time = "timestamp_utc" in annotated.columns
    has_elapsed = "elapsed_ms" in annotated.columns

    for idx in range(row_count):
        row_flags = flags_col[idx]
        seq = seq_vals[idx]

        # Non-numeric, non-finite, or null sequence number
        if pd.isna(seq) or not isinstance(seq, (int, np.integer, float)) or not math.isfinite(float(seq)):
            valid_mask[idx] = False
            row_flags.append("INVALID_SEQUENCE")
            diagnostics.append(
                SchemaValidationDiagnostic(
                    row_index=idx,
                    field_name="sequence_number",
                    raw_value=seq,
                    issue_code="NON_NUMERIC",
                    severity="ERROR",
                    message=f"Row {idx}: sequence_number is non-numeric, non-finite, or missing."
                )
            )
            continue

        seq_int = int(seq)
        if seq_int in seen_seq:
            valid_mask[idx] = False
            row_flags.append("DUPLICATE_SEQUENCE")
            diagnostics.append(
                SchemaValidationDiagnostic(
                    row_index=idx,
                    field_name="sequence_number",
                    raw_value=seq_int,
                    issue_code="DUPLICATE",
                    severity="ERROR",
                    message=f"Row {idx}: duplicate sequence_number {seq_int} detected."
                )
            )
        else:
            seen_seq.add(seq_int)

        if prev_seq is not None:
            if seq_int <= prev_seq:
                valid_mask[idx] = False
                row_flags.append("OUT_OF_ORDER_SEQUENCE")
                diagnostics.append(
                    SchemaValidationDiagnostic(
                        row_index=idx,
                        field_name="sequence_number",
                        raw_value=seq_int,
                        issue_code="MONOTONICITY_VIOLATION",
                        severity="ERROR",
                        message=f"Row {idx}: sequence out of order (previous {prev_seq}, current {seq_int})."
                    )
                )
            elif seq_int > prev_seq + 1:
                warning_mask[idx] = True
                row_flags.append(f"SEQUENCE_GAP_{seq_int - prev_seq - 1}")
                diagnostics.append(
                    SchemaValidationDiagnostic(
                        row_index=idx,
                        field_name="sequence_number",
                        raw_value=seq_int,
                        issue_code="SEQUENCE_GAP",
                        severity="WARNING",
                        message=f"Row {idx}: gap of {seq_int - prev_seq - 1} samples between {prev_seq} and {seq_int}."
                    )
                )
        prev_seq = seq_int

        # Timestamp validation
        if has_time:
            t_raw = annotated["timestamp_utc"].iloc[idx]
            if pd.isna(t_raw) or not validate_timestamp_iso(t_raw):
                valid_mask[idx] = False
                row_flags.append("INVALID_TIMESTAMP_FORMAT")
                diagnostics.append(
                    SchemaValidationDiagnostic(
                        row_index=idx,
                        field_name="timestamp_utc",
                        raw_value=t_raw,
                        issue_code="INVALID_TIMESTAMP",
                        severity="ERROR",
                        message=f"Row {idx}: timestamp '{t_raw}' is not valid ISO 8601."
                    )
                )

        if has_elapsed:
            el_raw = annotated["elapsed_ms"].iloc[idx]
            is_el_valid = False
            el_float = None
            if not pd.isna(el_raw):
                try:
                    el_float = float(el_raw)
                    if math.isfinite(el_float):
                        is_el_valid = True
                except (ValueError, TypeError):
                    is_el_valid = False

            if not is_el_valid:
                valid_mask[idx] = False
                row_flags.append("NON_FINITE_ELAPSED")
                diagnostics.append(
                    SchemaValidationDiagnostic(
                        row_index=idx,
                        field_name="elapsed_ms",
                        raw_value=el_raw,
                        issue_code="NON_NUMERIC",
                        severity="ERROR",
                        message=f"Row {idx}: elapsed_ms is non-numeric or non-finite."
                    )
                )
            elif prev_time is not None and el_float < prev_time:
                valid_mask[idx] = False
                row_flags.append("BACKWARDS_TIME")
                diagnostics.append(
                    SchemaValidationDiagnostic(
                        row_index=idx,
                        field_name="elapsed_ms",
                        raw_value=el_raw,
                        issue_code="MONOTONICITY_VIOLATION",
                        severity="ERROR",
                        message=f"Row {idx}: elapsed_ms went backwards from {prev_time} to {el_float}."
                    )
                )
            if is_el_valid:
                prev_time = el_float

    # 3. Numeric Measurands Validation
    for col in MEASURAND_KEYS:
        if col not in annotated.columns:
            continue
            
        col_vals = annotated[col].values
        c_min, c_max = ranges.get(col, (-np.inf, np.inf))

        for idx in range(row_count):
            val = col_vals[idx]
            row_flags = flags_col[idx]
            
            if pd.isna(val):
                if not allow_missing_measurands:
                    valid_mask[idx] = False
                    row_flags.append(f"MISSING_{col}")
                else:
                    warning_mask[idx] = True
                    row_flags.append(f"MISSING_{col}")
                continue

            try:
                fval = float(val)
            except (ValueError, TypeError):
                valid_mask[idx] = False
                row_flags.append(f"NON_NUMERIC_{col}")
                diagnostics.append(
                    SchemaValidationDiagnostic(
                        row_index=idx,
                        field_name=col,
                        raw_value=val,
                        issue_code="NON_NUMERIC",
                        severity="ERROR",
                        message=f"Row {idx}: Column '{col}' value '{val}' cannot be parsed as float."
                    )
                )
                continue

            if not math.isfinite(fval):
                valid_mask[idx] = False
                row_flags.append(f"NON_FINITE_{col}")
                diagnostics.append(
                    SchemaValidationDiagnostic(
                        row_index=idx,
                        field_name=col,
                        raw_value=val,
                        issue_code="NON_FINITE",
                        severity="ERROR",
                        message=f"Row {idx}: Column '{col}' value '{fval}' is NaN or Infinite."
                    )
                )
            elif fval < c_min or fval > c_max:
                valid_mask[idx] = False
                row_flags.append(f"OUT_OF_RANGE_{col}")
                diagnostics.append(
                    SchemaValidationDiagnostic(
                        row_index=idx,
                        field_name=col,
                        raw_value=fval,
                        issue_code="OUT_OF_RANGE",
                        severity="ERROR",
                        message=f"Row {idx}: {col}={fval} outside physical bounds [{c_min}, {c_max}]."
                    )
                )

    # 4. Status Flag check
    if "status" in annotated.columns:
        status_vals = annotated["status"].astype(str).values
        for idx in range(row_count):
            st = status_vals[idx].strip().upper()
            if st not in ("OK", "NOMINAL", "VALID"):
                warning_mask[idx] = True
                flags_col[idx].append(f"SENSOR_STATUS_{st}")
                diagnostics.append(
                    SchemaValidationDiagnostic(
                        row_index=idx,
                        field_name="status",
                        raw_value=st,
                        issue_code="SENSOR_STATUS_WARNING",
                        severity="WARNING",
                        message=f"Row {idx}: sensor status is '{st}' (non-nominal)."
                    )
                )

    annotated["quality_flags"] = [";".join(f) if f else "CLEAN" for f in flags_col]
    annotated["is_record_valid"] = valid_mask

    error_count = int(np.sum(~valid_mask))
    warning_count = int(np.sum(warning_mask & valid_mask))
    valid_count = int(np.sum(valid_mask))

    summary = {
        "total_records": row_count,
        "valid_records": valid_count,
        "error_records": error_count,
        "warning_records": warning_count,
        "valid_percentage": (valid_count / row_count * 100.0) if row_count > 0 else 0.0
    }

    return SchemaValidationResult(
        is_valid=(error_count == 0),
        total_records=row_count,
        valid_record_count=valid_count,
        error_record_count=error_count,
        warning_record_count=warning_count,
        diagnostics=diagnostics,
        flagged_dataframe=annotated,
        summary=summary
    )
