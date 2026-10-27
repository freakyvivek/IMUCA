"""
Residual Analysis Module for IMUCA.
Implements Equation 9.14: Regression residuals, peak residual error,
and quantisation / nonlinearity diagnostics.
"""

from typing import List, Tuple, Dict, Any, Union
from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass
class ResidualAnalysisResult:
    residuals_v: np.ndarray
    residuals_mv: np.ndarray
    max_residual_v: float
    max_residual_mv: float
    rms_residual_mv: float
    resolution_limit_v: float
    resolution_limit_mv: float       # resolution / 2
    is_nonlinearity_present: bool     # max_residual > resolution / 2
    diagnostic_message: str
    residuals_dataframe: pd.DataFrame


def analyze_residuals(
    reference_v: np.ndarray,
    dut_v: np.ndarray,
    slope_m: float,
    intercept_c: float,
    resolution_v: float = 0.01
) -> ResidualAnalysisResult:
    """
    Calculate residuals r_i = X_DUT,i - (m * X_REF,i + c) and evaluate nonlinearity against resolution limits.
    """
    fitted_dut = slope_m * reference_v + intercept_c
    residuals_v = dut_v - fitted_dut
    residuals_mv = residuals_v * 1000.0
    
    max_res_v = float(np.max(np.abs(residuals_v)))
    max_res_mv = max_res_v * 1000.0
    rms_res_mv = float(np.sqrt(np.mean(residuals_mv ** 2)))
    
    half_res_v = resolution_v / 2.0
    half_res_mv = half_res_v * 1000.0
    
    is_nonlinearity = max_res_v > half_res_v
    
    if is_nonlinearity:
        diag = (
            f"Nonlinearity present: Peak residual of {max_res_mv:.2f} mV exceeds "
            f"half-resolution limit ({half_res_mv:.2f} mV). Higher-order polynomial fit may be required."
        )
    else:
        diag = (
            f"Linear model adequate: Peak residual of {max_res_mv:.2f} mV is within "
            f"half-resolution limit ({half_res_mv:.2f} mV), confirming deviations are dominated by quantisation."
        )
        
    df_res = pd.DataFrame({
        "Point": np.arange(1, len(reference_v) + 1),
        "Reference_V": reference_v,
        "DUT_V": dut_v,
        "Fitted_DUT_V": fitted_dut,
        "Residual_V": residuals_v,
        "Residual_mV": residuals_mv
    })
    
    return ResidualAnalysisResult(
        residuals_v=residuals_v,
        residuals_mv=residuals_mv,
        max_residual_v=max_res_v,
        max_residual_mv=max_res_mv,
        rms_residual_mv=rms_res_mv,
        resolution_limit_v=half_res_v,
        resolution_limit_mv=half_res_mv,
        is_nonlinearity_present=is_nonlinearity,
        diagnostic_message=diag,
        residuals_dataframe=df_res
    )
