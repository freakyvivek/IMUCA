"""
Validation Module for IMUCA.
Implements Algorithm 1a: Multi-layer data validation, non-destructive outlier detection (MAD),
and range verification.
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import numpy as np
import pandas as pd


@dataclass
class ValidationIssue:
    row_index: int
    column: str
    value: Any
    issue_type: str  # 'NON-NUMERIC', 'MISSING', 'OUT_OF_RANGE', 'OUTLIER'
    severity: str    # 'INVALID' (skipped) or 'WARNING' (flagged, retained)
    message: str


@dataclass
class ValidationResult:
    is_valid: bool
    status: str  # 'VALID', 'WARNING', 'INVALID'
    total_rows: int
    valid_rows_count: int
    skipped_rows_count: int
    warning_rows_count: int
    valid_df: pd.DataFrame
    issues: List[ValidationIssue] = field(default_factory=list)
    outlier_indices: List[int] = field(default_factory=list)
    summary_messages: List[str] = field(default_factory=list)


def validate_dataset(
    df: pd.DataFrame,
    columns_to_check: Optional[List[str]] = None,
    min_val: float = 0.0,
    max_val: float = 20.0,
    mad_threshold: float = 3.5,
    check_outliers: bool = True
) -> ValidationResult:
    """
    Validates measurement dataset according to IMUCA Algorithm 1a.
    
    Checks:
    1. Missing values
    2. Non-numeric strings / conversion errors
    3. Range violations (e.g. 0V to 20V instrument span)
    4. Outlier detection using Median Absolute Deviation (MAD) (FLAGGED, NOT DELETED)
    
    Args:
        df: Raw pandas DataFrame.
        columns_to_check: Specific numerical columns to validate. If None, checks all columns.
        min_val: Minimum allowable numerical value.
        max_val: Maximum allowable numerical value.
        mad_threshold: Modified z-score threshold for MAD outlier flagging (default 3.5).
        check_outliers: Whether to run MAD outlier detection on numeric columns.
        
    Returns:
        ValidationResult object.
    """
    if df.empty:
        return ValidationResult(
            is_valid=False,
            status="INVALID",
            total_rows=0,
            valid_rows_count=0,
            skipped_rows_count=0,
            warning_rows_count=0,
            valid_df=pd.DataFrame(),
            issues=[],
            summary_messages=["Dataset is empty."]
        )
        
    cols = columns_to_check if columns_to_check is not None else list(df.columns)
    issues: List[ValidationIssue] = []
    skipped_row_indices = set()
    
    # Pass 1: Missing, Non-numeric, and Range checks
    for idx, row in df.iterrows():
        for col in cols:
            val = row[col]
            
            # Check missing
            if pd.isna(val) or val == "" or str(val).strip() == "-" or str(val).strip() == "–":
                # Only invalidate if it's not an optional repeat column with '-'
                if "repeat" in col.lower() or "rpt" in col.lower():
                    # Missing repeat at a sweep point is acceptable in calibration tables
                    continue
                issues.append(ValidationIssue(
                    row_index=idx,
                    column=col,
                    value=val,
                    issue_type="MISSING",
                    severity="INVALID",
                    message=f"Row {idx+1}: Missing value in required column '{col}'."
                ))
                skipped_row_indices.add(idx)
                continue
                
            # Check numeric
            try:
                num_val = float(str(val).replace(",", "").strip())
            except (ValueError, TypeError):
                issues.append(ValidationIssue(
                    row_index=idx,
                    column=col,
                    value=val,
                    issue_type="NON-NUMERIC",
                    severity="INVALID",
                    message=f"Row {idx+1}: Non-numeric value '{val}' in column '{col}'."
                ))
                skipped_row_indices.add(idx)
                continue
                
            # Check range
            if num_val < min_val or num_val > max_val:
                issues.append(ValidationIssue(
                    row_index=idx,
                    column=col,
                    value=num_val,
                    issue_type="OUT_OF_RANGE",
                    severity="INVALID",
                    message=f"Row {idx+1}: Value {num_val} in column '{col}' outside valid span [{min_val}, {max_val}]."
                ))
                skipped_row_indices.add(idx)
                
    # Filter rows that were not skipped
    valid_indices = [i for i in df.index if i not in skipped_row_indices]
    valid_df = df.loc[valid_indices].copy()
    
    # Cast valid columns to float
    for col in cols:
        if col in valid_df.columns:
            valid_df[col] = pd.to_numeric(valid_df[col], errors="coerce")
            
    # Pass 2: Outlier detection using MAD on retained rows
    outlier_indices: List[int] = []
    if check_outliers and len(valid_df) >= 3:
        for col in cols:
            series = valid_df[col].dropna()
            if len(series) < 3:
                continue
            med = float(np.median(series))
            abs_dev = np.abs(series - med)
            mad = float(np.median(abs_dev))
            
            if mad > 1e-12:
                # Modified Z-score (Iglewicz and Hoaglin, 1993)
                # z = 0.6745 * (x - median) / MAD
                z_scores = 0.6745 * abs_dev / mad
                for orig_idx, z in z_scores.items():
                    if z > mad_threshold:
                        outlier_indices.append(orig_idx)
                        issues.append(ValidationIssue(
                            row_index=orig_idx,
                            column=col,
                            value=valid_df.loc[orig_idx, col],
                            issue_type="OUTLIER",
                            severity="WARNING",
                            message=f"Row {orig_idx+1}: Statistical outlier detected in '{col}' (value={valid_df.loc[orig_idx, col]}, modified z={z:.2f} > {mad_threshold}). Flagged for inspection; NOT deleted."
                        ))
                        
    # Determine overall status
    has_invalid = any(i.severity == "INVALID" for i in issues)
    has_warning = any(i.severity == "WARNING" for i in issues)
    
    if len(valid_df) == 0:
        overall_status = "INVALID"
        is_valid = False
    elif has_invalid or has_warning:
        overall_status = "WARNING" if len(valid_df) > 0 else "INVALID"
        is_valid = len(valid_df) > 0
    else:
        overall_status = "VALID"
        is_valid = True
        
    summary_messages = []
    if overall_status == "VALID":
        summary_messages.append(f"All {len(df)} records are valid, numeric, within span [{min_val}, {max_val}], and verified.")
    else:
        if skipped_row_indices:
            summary_messages.append(f"Skipped {len(skipped_row_indices)} invalid records (non-numeric, missing, or out of range).")
        if outlier_indices:
            summary_messages.append(f"Flagged {len(set(outlier_indices))} potential outlier observations for inspection without silent deletion.")
            
    return ValidationResult(
        is_valid=is_valid,
        status=overall_status,
        total_rows=len(df),
        valid_rows_count=len(valid_df),
        skipped_rows_count=len(skipped_row_indices),
        warning_rows_count=len(set(outlier_indices)),
        valid_df=valid_df,
        issues=issues,
        outlier_indices=list(set(outlier_indices)),
        summary_messages=summary_messages
    )
