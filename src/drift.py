"""
Drift and Trend Analysis Module for IMUCA.
Implements Equations 9.15 and Algorithm 6: Within-run sequence stability tests,
between-session linear drift regression, significance testing, and projected tolerance breach forecasting.
"""

from typing import List, Tuple, Dict, Any, Union, Optional
from dataclasses import dataclass
import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class WithinRunTrendResult:
    is_assessed: bool
    slope_mv_per_reading: float
    std_err_slope: float
    t_statistic: float
    p_value: float
    is_significant: bool       # p < 0.05
    verdict: str              # 'NO SIGNIFICANT TREND' or 'SIGNIFICANT WITHIN-RUN TREND DETECTED'
    explanation: str


@dataclass
class DriftAnalysisResult:
    is_assessed: bool
    num_sessions: int
    sessions: np.ndarray
    mean_errors_mv: np.ndarray
    slope_b: float             # mV / session
    intercept_a: float         # mV
    std_err_b: float           # s(b)
    r_squared: float           # R^2
    p_value: float             # p
    drift_threshold: float     # b_lim (e.g. 0.50 mV/session)
    tolerance_mv: float        # T (e.g. 50 mV)
    is_drift_significant: bool # |b| > b_threshold and p < 0.05
    drift_status: str          # 'SIGNIFICANT UPWARD DRIFT DETECTED', 'SIGNIFICANT DOWNWARD DRIFT DETECTED', 'NO SIGNIFICANT DRIFT', 'NOT ASSESSED'
    rule_status: str           # 'POSSIBLE DRIFT' or 'NO SIGNIFICANT DRIFT'
    projected_breach_session: Optional[float]
    sessions_until_breach: Optional[float]
    recommended_recalibration_session: Optional[int]
    confidence_interval_slope_95: Tuple[float, float]
    history_dataframe: pd.DataFrame
    disclaimer: str = (
        "Linear extrapolation is a planning aid for condition-based calibration, "
        "not a guaranteed physical prediction."
    )


def analyze_within_run_trend(
    readings: Union[List[float], np.ndarray]
) -> WithinRunTrendResult:
    """
    Check whether repeated readings taken within a single session show a systematic trend
    (indicating thermal settling or unstable contact rather than pure random scatter).
    """
    arr = np.array(readings, dtype=float)
    if len(arr) < 3:
        return WithinRunTrendResult(
            is_assessed=False,
            slope_mv_per_reading=0.0,
            std_err_slope=0.0,
            t_statistic=0.0,
            p_value=1.0,
            is_significant=False,
            verdict="INSUFFICIENT REPEATS",
            explanation="At least 3 repeated readings are required to test within-run stability."
        )
        
    seq = np.arange(1, len(arr) + 1, dtype=float)
    arr_mv = arr * 1000.0
    reg = stats.linregress(seq, arr_mv)
    
    slope = float(reg.slope)
    stderr = float(reg.stderr) if reg.stderr is not None else 0.0
    pval = float(reg.pvalue)
    t_stat = (slope / stderr) if stderr > 1e-12 else 0.0
    
    is_sig = pval < 0.05
    if is_sig:
        verdict = "SIGNIFICANT WITHIN-RUN TREND DETECTED"
        expl = (
            f"Slope = {slope:+.3f} mV/reading (p = {pval:.4f} < 0.05). "
            f"Readings show systematic drift during measurement run. Investigate thermal settling or loose connections."
        )
    else:
        verdict = "NO SIGNIFICANT TREND"
        expl = (
            f"Slope = {slope:+.3f} mV/reading, s(b) = {stderr:.3f} mV/reading (t = {t_stat:.2f}, p = {pval:.2f}). "
            f"No significant within-run trend detected; repeat readings satisfy independent observation assumptions."
        )
        
    return WithinRunTrendResult(
        is_assessed=True,
        slope_mv_per_reading=slope,
        std_err_slope=stderr,
        t_statistic=t_stat,
        p_value=pval,
        is_significant=is_sig,
        verdict=verdict,
        explanation=expl
    )


def evaluate_drift_history(
    sessions: Union[List[float], np.ndarray],
    mean_errors_mv: Union[List[float], np.ndarray],
    drift_threshold_mv_per_session: float = 0.50,
    tolerance_mv: float = 50.0
) -> DriftAnalysisResult:
    """
    Perform linear regression on historical calibration errors to detect systematic drift
    and forecast projected tolerance breach according to IMUCA Algorithm 6.
    """
    t_arr = np.array(sessions, dtype=float)
    e_arr = np.array(mean_errors_mv, dtype=float)
    
    if len(t_arr) != len(e_arr):
        raise ValueError("Sessions and Error arrays must have equal length.")
        
    if len(t_arr) < 3:
        # Insufficient history
        return DriftAnalysisResult(
            is_assessed=False,
            num_sessions=len(t_arr),
            sessions=t_arr,
            mean_errors_mv=e_arr,
            slope_b=0.0,
            intercept_a=0.0,
            std_err_b=0.0,
            r_squared=0.0,
            p_value=1.0,
            drift_threshold=drift_threshold_mv_per_session,
            tolerance_mv=tolerance_mv,
            is_drift_significant=False,
            drift_status="NOT ASSESSED",
            rule_status="NO SIGNIFICANT DRIFT",
            projected_breach_session=None,
            sessions_until_breach=None,
            recommended_recalibration_session=None,
            confidence_interval_slope_95=(0.0, 0.0),
            history_dataframe=pd.DataFrame()
        )
        
    # 1. Linear regression: E = a + b * t
    reg = stats.linregress(t_arr, e_arr)
    b = float(reg.slope)
    a = float(reg.intercept)
    s_b = float(reg.stderr) if reg.stderr is not None else 0.0
    r2 = float(reg.rvalue ** 2)
    pval = float(reg.pvalue)
    
    # 95% confidence interval for slope
    df_resid = len(t_arr) - 2
    t_crit = float(stats.t.ppf(0.975, df=df_resid)) if df_resid > 0 else 2.0
    ci_slope = (b - t_crit * s_b, b + t_crit * s_b)
    
    # 2. Significance test: |b| > b_lim AND p < 0.05
    is_drift = (abs(b) > drift_threshold_mv_per_session) and (pval < 0.05)
    
    if is_drift:
        rule_status = "POSSIBLE DRIFT"
        if b > 0:
            drift_status = "SIGNIFICANT UPWARD DRIFT DETECTED"
        else:
            drift_status = "SIGNIFICANT DOWNWARD DRIFT DETECTED"
    else:
        rule_status = "NO SIGNIFICANT DRIFT"
        drift_status = "NO SIGNIFICANT TREND"
        
    # 3. Projected tolerance breach session: t_breach = (T - a) / b
    projected_breach = None
    sessions_until_breach = None
    rec_session = None
    
    if is_drift and abs(b) > 1e-6:
        # If drifting upward toward +T
        target_tol = tolerance_mv if b > 0 else -tolerance_mv
        t_breach_raw = (target_tol - a) / b
        projected_breach = float(np.round(t_breach_raw, 1))
        last_session = float(t_arr[-1])
        sessions_until_breach = float(np.round(t_breach_raw - last_session, 1))
        
        # Suggest recalibration with ~4-5 sessions safety margin before breach
        margin = max(3, int(np.ceil(t_crit * s_b / b * 5))) if b > 0 else 4
        rec_session = max(int(last_session) + 1, int(np.floor(t_breach_raw)) - margin)
        
    df_hist = pd.DataFrame({
        "Session": t_arr.astype(int),
        "Mean_Error_mV": e_arr,
        "Fitted_Error_mV": a + b * t_arr,
        "Residual_mV": e_arr - (a + b * t_arr)
    })
    
    return DriftAnalysisResult(
        is_assessed=True,
        num_sessions=len(t_arr),
        sessions=t_arr,
        mean_errors_mv=e_arr,
        slope_b=b,
        intercept_a=a,
        std_err_b=s_b,
        r_squared=r2,
        p_value=pval,
        drift_threshold=drift_threshold_mv_per_session,
        tolerance_mv=tolerance_mv,
        is_drift_significant=is_drift,
        drift_status=drift_status,
        rule_status=rule_status,
        projected_breach_session=projected_breach,
        sessions_until_breach=sessions_until_breach,
        recommended_recalibration_session=rec_session,
        confidence_interval_slope_95=ci_slope,
        history_dataframe=df_hist
    )
