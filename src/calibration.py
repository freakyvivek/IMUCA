"""
Calibration Analysis Module for IMUCA.
Implements Equations 9.13 to 9.16 and Algorithms 5: Least-squares regression,
offset/gain error separation, 3-band conformity assessment, and guard-banded tolerance evaluation.
"""

from typing import List, Tuple, Dict, Any, Union, Optional
from dataclasses import dataclass
import numpy as np
import pandas as pd
from scipy import stats
from src.residuals import analyze_residuals, ResidualAnalysisResult


@dataclass
class CalibrationPointConformity:
    point_index: int
    reference_v: float
    dut_v: float
    absolute_error_v: float
    absolute_error_mv: float
    relative_error: float
    percentage_error: float
    tolerance_percent: float
    tolerance_abs_v: float
    tolerance_abs_mv: float
    conformity_status: str     # 'PASS', 'MARGINAL', 'FAIL'
    notes: str = ""


@dataclass
class CalibrationResult:
    points: List[CalibrationPointConformity]
    slope_m: float
    intercept_c: float
    zero_offset_v: float
    zero_offset_mv: float
    gain_error_percent: float     # (m - 1) * 100 %
    r_squared: float
    std_err_slope: float
    std_err_intercept: float
    p_value: float
    overall_status: str           # 'PASS', 'MARGINAL', 'FAIL'
    pass_count: int
    marginal_count: int
    fail_count: int
    summary_text: str             # e.g. "8 PASS / 1 MARGINAL / 1 FAIL"
    correction_formula: str       # e.g. "X_corr = (X_DUT - 0.006667) / 1.003030"
    calibration_dataframe: pd.DataFrame
    residuals: ResidualAnalysisResult


def evaluate_calibration_sweep(
    reference_v: Union[List[float], np.ndarray],
    dut_v: Union[List[float], np.ndarray],
    tolerance_percent: float = 1.0,
    resolution_v: float = 0.01
) -> CalibrationResult:
    """
    Perform linear least-squares calibration regression and 3-band conformity evaluation.
    
    3-band conformity rule:
      |E%| <= 0.8 * T  -> PASS
      0.8 * T < |E%| <= T -> MARGINAL
      |E%| > T         -> FAIL
    """
    refs = np.array(reference_v, dtype=float)
    duts = np.array(dut_v, dtype=float)
    
    if len(refs) != len(duts):
        raise ValueError("Reference and DUT arrays must have equal length.")
    if len(refs) < 2:
        raise ValueError("Calibration analysis requires at least 2 points for regression.")
        
    # 1. Linear regression XDUT = m * XREF + c
    reg = stats.linregress(refs, duts)
    m = float(reg.slope)
    c = float(reg.intercept)
    r2 = float(reg.rvalue ** 2)
    s_m = float(reg.stderr) if reg.stderr is not None else 0.0
    s_c = float(reg.intercept_stderr) if reg.intercept_stderr is not None else 0.0
    p_val = float(reg.pvalue)
    
    zero_offset_v = c
    zero_offset_mv = c * 1000.0
    gain_error_pct = (m - 1.0) * 100.0
    
    # 2. Point-by-point conformity evaluation
    points: List[CalibrationPointConformity] = []
    pass_cnt = 0
    marg_cnt = 0
    fail_cnt = 0
    df_rows = []
    
    for i in range(len(refs)):
        ref_i = refs[i]
        dut_i = duts[i]
        err_v = dut_i - ref_i
        err_mv = err_v * 1000.0
        rel_err = err_v / ref_i if abs(ref_i) > 1e-12 else 0.0
        pct_err = rel_err * 100.0
        
        tol_abs_v = (tolerance_percent / 100.0) * ref_i
        tol_abs_mv = tol_abs_v * 1000.0
        
        abs_pct = abs(pct_err)
        # Account for floating-point epsilon at boundary: e.g. 1.0000000000000009 % at T=1.0%
        if abs_pct > (tolerance_percent + 1e-7):
            status = "FAIL"
            fail_cnt += 1
        elif abs_pct >= (0.8 * tolerance_percent - 1e-7):
            status = "MARGINAL"
            marg_cnt += 1
        else:
            status = "PASS"
            pass_cnt += 1
            
        pt = CalibrationPointConformity(
            point_index=i + 1,
            reference_v=ref_i,
            dut_v=dut_i,
            absolute_error_v=err_v,
            absolute_error_mv=err_mv,
            relative_error=rel_err,
            percentage_error=pct_err,
            tolerance_percent=tolerance_percent,
            tolerance_abs_v=tol_abs_v,
            tolerance_abs_mv=tol_abs_mv,
            conformity_status=status
        )
        points.append(pt)
        
        df_rows.append({
            "Point": i + 1,
            "Reference (V)": f"{ref_i:.3f}",
            "DUT (V)": f"{dut_i:.2f}",
            "Absolute Error (mV)": f"{err_mv:+.1f}",
            "Relative Error (x10^-3)": f"{rel_err*1000:.2f}",
            "Percentage Error (%)": f"{pct_err:+.3f}",
            "Tolerance (±mV)": f"±{tol_abs_mv:.1f}",
            "Status": status
        })
        
    df_cal = pd.DataFrame(df_rows)
    
    # 3. Overall sweep status
    if fail_cnt > 0:
        overall_status = "FAIL"
    elif marg_cnt > 0:
        overall_status = "MARGINAL"
    else:
        overall_status = "PASS"
        
    summary_text = f"{pass_cnt} PASS / {marg_cnt} MARGINAL / {fail_cnt} FAIL"
    correction_formula = f"X_corrected = (X_DUT - ({c:+.6f})) / {m:.6f}"
    
    # 4. Residual analysis
    residuals = analyze_residuals(
        reference_v=refs,
        dut_v=duts,
        slope_m=m,
        intercept_c=c,
        resolution_v=resolution_v
    )
    
    return CalibrationResult(
        points=points,
        slope_m=m,
        intercept_c=c,
        zero_offset_v=zero_offset_v,
        zero_offset_mv=zero_offset_mv,
        gain_error_percent=gain_error_pct,
        r_squared=r2,
        std_err_slope=s_m,
        std_err_intercept=s_c,
        p_value=p_val,
        overall_status=overall_status,
        pass_count=pass_cnt,
        marginal_count=marg_cnt,
        fail_count=fail_cnt,
        summary_text=summary_text,
        correction_formula=correction_formula,
        calibration_dataframe=df_cal,
        residuals=residuals
    )


def evaluate_single_point_conformity(
    reference_v: float,
    mean_dut_v: float,
    expanded_uncertainty_v: float,
    tolerance_percent: float = 1.0
) -> Dict[str, Any]:
    """
    Perform both simple and guard-banded conformity evaluations for a single operating point.
    
    Simple: |E| <= T
    Guard-banded: |E| + U <= T
    """
    error_v = mean_dut_v - reference_v
    error_mv = error_v * 1000.0
    u_v = expanded_uncertainty_v
    u_mv = u_v * 1000.0
    
    tol_v = (tolerance_percent / 100.0) * reference_v
    tol_mv = tol_v * 1000.0
    
    simple_pass = abs(error_v) <= tol_v
    guard_pass = (abs(error_v) + u_v) <= tol_v
    remaining_margin_mv = tol_mv - (abs(error_mv) + u_mv)
    
    return {
        "reference_v": reference_v,
        "mean_dut_v": mean_dut_v,
        "error_mv": error_mv,
        "expanded_uncertainty_mv": u_mv,
        "total_error_plus_uncertainty_mv": abs(error_mv) + u_mv,
        "tolerance_mv": tol_mv,
        "tolerance_percent": tolerance_percent,
        "simple_conformity": "PASS" if simple_pass else "FAIL",
        "guard_banded_conformity": "PASS" if guard_pass else "FAIL",
        "remaining_margin_mv": remaining_margin_mv
    }
