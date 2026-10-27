"""
Error Analysis Module for IMUCA.
Implements Equations 9.11 to 9.12: Absolute error, relative error, and percentage error.
"""

from typing import Dict, List, Optional, Union
from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass
class PointError:
    point_index: int
    reference_val: float
    dut_val: float
    absolute_error: float      # E = DUT - REF (in V or same unit)
    absolute_error_mv: float   # E in mV
    relative_error: float      # E / REF
    percentage_error: float    # (E / REF) * 100 %


@dataclass
class ErrorAnalysisResult:
    point_errors: List[PointError]
    mean_absolute_error: float
    max_absolute_error: float
    mean_percentage_error: float
    max_percentage_error: float
    error_dataframe: pd.DataFrame


def calculate_point_error(
    reference_val: float,
    dut_val: float,
    point_index: int = 1
) -> PointError:
    """
    Calculate absolute, relative, and percentage errors for a single operating point.
    """
    abs_err = dut_val - reference_val
    abs_err_mv = abs_err * 1000.0
    
    if abs(reference_val) > 1e-15:
        rel_err = abs_err / reference_val
        pct_err = rel_err * 100.0
    else:
        rel_err = 0.0
        pct_err = 0.0
        
    return PointError(
        point_index=point_index,
        reference_val=reference_val,
        dut_val=dut_val,
        absolute_error=abs_err,
        absolute_error_mv=abs_err_mv,
        relative_error=rel_err,
        percentage_error=pct_err
    )


def calculate_sweep_errors(
    reference_vals: Union[List[float], np.ndarray],
    dut_vals: Union[List[float], np.ndarray]
) -> ErrorAnalysisResult:
    """
    Calculate errors across a multi-point calibration sweep.
    """
    refs = np.array(reference_vals, dtype=float)
    duts = np.array(dut_vals, dtype=float)
    
    if len(refs) != len(duts):
        raise ValueError("Reference and DUT arrays must have equal length.")
    if len(refs) == 0:
        raise ValueError("Cannot calculate errors for empty arrays.")
        
    point_errors: List[PointError] = []
    rows = []
    
    for i in range(len(refs)):
        pe = calculate_point_error(refs[i], duts[i], point_index=i+1)
        point_errors.append(pe)
        rows.append({
            "Point": pe.point_index,
            "Reference_V": pe.reference_val,
            "DUT_V": pe.dut_val,
            "Absolute_Error_V": pe.absolute_error,
            "Absolute_Error_mV": pe.absolute_error_mv,
            "Relative_Error": pe.relative_error,
            "Percentage_Error_%": pe.percentage_error
        })
        
    df = pd.DataFrame(rows)
    abs_errs_mv = np.array([p.absolute_error_mv for p in point_errors])
    pct_errs = np.array([p.percentage_error for p in point_errors])
    
    return ErrorAnalysisResult(
        point_errors=point_errors,
        mean_absolute_error=float(np.mean(np.abs(abs_errs_mv))),
        max_absolute_error=float(np.max(np.abs(abs_errs_mv))),
        mean_percentage_error=float(np.mean(np.abs(pct_errs))),
        max_percentage_error=float(np.max(np.abs(pct_errs))),
        error_dataframe=df
    )
