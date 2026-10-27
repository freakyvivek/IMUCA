"""
IMUCA Measurement Metrics and Statistical Evaluation Module.

Section 8 Specification:
- Computes signed bias, absolute error, MAE, RMSE, relative error, and percentage error.
- Enforces strict protection against division by zero in relative/percentage errors.
- Evaluates sample standard deviation with (n - 1) Bessel's correction.
- Calculates ISO 5725 repeatability statistics and pooled standard deviations.
- Conducts residual diagnostics, normality checks, and autocorrelation checks.
- Computes Student's t-based confidence intervals for sample means.
- Explicitly documents metrological distinctions: bias != repeatability != uncertainty != RMSE.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple, Union
import numpy as np
import scipy.stats as stats
import math


@dataclass
class DescriptiveStatistics:
    """Summary descriptive statistics of repeated measurement observations."""
    n: int
    mean: float
    sample_std_dev: float           # s with (n - 1) Bessel's correction
    sample_variance: float          # s^2 with (n - 1)
    standard_error_mean: float      # s / sqrt(n)
    median: float
    range_val: float
    min_val: float
    max_val: float
    degrees_of_freedom: int         # nu = n - 1
    confidence_interval_95: Tuple[float, float]
    raw_values: List[float] = field(default_factory=list)


@dataclass
class ErrorMetrics:
    """Accuracy and error metrics comparing measured values against reference values."""
    n: int
    mean_bias: float                # Signed mean error: sum(y_i - y_ref_i) / n
    mae: float                      # Mean Absolute Error
    rmse: float                     # Root Mean Square Error (NOT measurement uncertainty!)
    max_absolute_error: float
    valid_relative_count: int
    zero_reference_count: int
    mean_relative_error: Optional[float]
    mean_percentage_error: Optional[float]
    max_percentage_error: Optional[float]
    signed_errors: List[float] = field(default_factory=list)
    absolute_errors: List[float] = field(default_factory=list)
    percentage_errors: List[float] = field(default_factory=list)


@dataclass
class RepeatabilityMetrics:
    """ISO 5725 repeatability evaluation for multi-run or multi-point series."""
    repeatability_std_dev: float    # s_r
    repeatability_limit: float      # r = 2.8 * s_r
    relative_standard_dev_pct: float# RSD = s / mean * 100 %
    num_series: int
    degrees_of_freedom: int


@dataclass
class ResidualAnalysisMetrics:
    """Diagnostic evaluation of regression/calibration residuals."""
    n: int
    max_abs_residual: float
    mean_residual: float
    residual_std_dev: float
    durbin_watson_stat: float       # Test for residual autocorrelation
    shapiro_wilk_p_value: Optional[float]
    is_normally_distributed: bool
    residuals: List[float] = field(default_factory=list)


# ==============================================================================
# Descriptive Statistics and Repeatability
# ==============================================================================

def compute_descriptive_statistics(
    readings: Union[List[float], np.ndarray],
    confidence_level: float = 0.95
) -> DescriptiveStatistics:
    """
    Calculate sample descriptive statistics for repeated observations.
    Uses sample standard deviation with (n - 1) denominator (ISO 5725 / GUM Section 4.2).
    """
    arr = np.asarray(readings, dtype=float)
    arr = arr[np.isfinite(arr)]
    n = len(arr)

    if n == 0:
        raise ValueError("Cannot calculate descriptive statistics on empty or non-finite dataset.")

    mean_val = float(np.mean(arr))
    med_val = float(np.median(arr))
    min_v = float(np.min(arr))
    max_v = float(np.max(arr))
    rng_v = float(max_v - min_v)

    if n == 1:
        return DescriptiveStatistics(
            n=1,
            mean=mean_val,
            sample_std_dev=0.0,
            sample_variance=0.0,
            standard_error_mean=0.0,
            median=med_val,
            range_val=0.0,
            min_val=min_v,
            max_val=max_v,
            degrees_of_freedom=0,
            confidence_interval_95=(mean_val, mean_val),
            raw_values=arr.tolist()
        )

    df = n - 1
    # Sample variance with (n - 1) Bessel's correction
    var_val = float(np.var(arr, ddof=1))
    std_val = float(np.sqrt(var_val))
    sem_val = float(std_val / np.sqrt(n))

    # Student's t critical value for confidence interval
    t_crit = float(stats.t.ppf((1.0 + confidence_level) / 2.0, df=df))
    ci = (mean_val - t_crit * sem_val, mean_val + t_crit * sem_val)

    return DescriptiveStatistics(
        n=n,
        mean=mean_val,
        sample_std_dev=std_val,
        sample_variance=var_val,
        standard_error_mean=sem_val,
        median=med_val,
        range_val=rng_v,
        min_val=min_v,
        max_val=max_v,
        degrees_of_freedom=df,
        confidence_interval_95=ci,
        raw_values=arr.tolist()
    )


def compute_pooled_repeatability(
    groups: List[Union[List[float], np.ndarray]]
) -> RepeatabilityMetrics:
    """
    Calculate pooled repeatability standard deviation s_r according to ISO 5725-2.
    s_r = sqrt( sum( (n_i - 1) * s_i^2 ) / sum(n_i - 1) )
    Repeatability limit r = 2.8 * s_r
    """
    valid_groups = []
    for g in groups:
        arr = np.asarray(g, dtype=float)
        arr = arr[np.isfinite(arr)]
        if len(arr) >= 2:
            valid_groups.append(arr)

    if not valid_groups:
        raise ValueError("At least one group with >= 2 observations is required to compute repeatability.")

    sum_df_var = 0.0
    total_df = 0
    all_means = []

    for arr in valid_groups:
        ni = len(arr)
        df_i = ni - 1
        var_i = float(np.var(arr, ddof=1))
        sum_df_var += df_i * var_i
        total_df += df_i
        all_means.append(float(np.mean(arr)))

    s_r = float(np.sqrt(sum_df_var / total_df))
    r_limit = 2.8 * s_r
    grand_mean = float(np.mean(all_means))
    rsd_pct = (s_r / abs(grand_mean) * 100.0) if abs(grand_mean) > 1e-12 else 0.0

    return RepeatabilityMetrics(
        repeatability_std_dev=s_r,
        repeatability_limit=r_limit,
        relative_standard_dev_pct=rsd_pct,
        num_series=len(valid_groups),
        degrees_of_freedom=total_df
    )


# ==============================================================================
# Error Metrics (Accuracy vs Reference)
# ==============================================================================

def compute_error_metrics(
    measured: Union[List[float], np.ndarray],
    reference: Union[List[float], np.ndarray],
    zero_threshold: float = 1e-6
) -> ErrorMetrics:
    """
    Compute signed error, MAE, RMSE, and guarded relative/percentage errors.
    
    CRITICAL METROLOGY NOTE:
    RMSE is a statistical measure of model error or fit residual.
    It is NOT equal to measurement uncertainty.
    """
    m = np.asarray(measured, dtype=float)
    r = np.asarray(reference, dtype=float)

    if len(m) != len(r):
        raise ValueError(f"Length mismatch: measured has {len(m)} items, reference has {len(r)} items.")

    valid_mask = np.isfinite(m) & np.isfinite(r)
    m = m[valid_mask]
    r = r[valid_mask]
    n = len(m)

    if n == 0:
        raise ValueError("No valid finite pairs available to compute error metrics.")

    signed_errors = m - r
    abs_errors = np.abs(signed_errors)

    bias = float(np.mean(signed_errors))
    mae = float(np.mean(abs_errors))
    rmse = float(np.sqrt(np.mean(signed_errors ** 2)))
    max_ae = float(np.max(abs_errors))

    # Guarded relative / percentage errors
    safe_rel_mask = np.abs(r) > zero_threshold
    zero_count = int(np.sum(~safe_rel_mask))
    valid_rel_count = int(np.sum(safe_rel_mask))

    if valid_rel_count > 0:
        rel_errors = signed_errors[safe_rel_mask] / r[safe_rel_mask]
        pct_errors = rel_errors * 100.0
        mean_rel = float(np.mean(rel_errors))
        mean_pct = float(np.mean(pct_errors))
        max_pct = float(np.max(np.abs(pct_errors)))
    else:
        mean_rel = None
        mean_pct = None
        max_pct = None

    # Full list of percentage errors (with NaN where reference is zero)
    all_pct = np.full(n, np.nan)
    all_pct[safe_rel_mask] = (signed_errors[safe_rel_mask] / r[safe_rel_mask]) * 100.0

    return ErrorMetrics(
        n=n,
        mean_bias=bias,
        mae=mae,
        rmse=rmse,
        max_absolute_error=max_ae,
        valid_relative_count=valid_rel_count,
        zero_reference_count=zero_count,
        mean_relative_error=mean_rel,
        mean_percentage_error=mean_pct,
        max_percentage_error=max_pct,
        signed_errors=signed_errors.tolist(),
        absolute_errors=abs_errors.tolist(),
        percentage_errors=all_pct.tolist()
    )


# ==============================================================================
# Residual Diagnostics
# ==============================================================================

def compute_residual_diagnostics(
    residuals: Union[List[float], np.ndarray]
) -> ResidualAnalysisMetrics:
    """
    Perform residual diagnostics on calibration fit or trend regression.
    Evaluates:
    - Maximum absolute residual
    - Residual standard deviation
    - Durbin-Watson statistic for autocorrelation: d = sum((e_t - e_{t-1})^2) / sum(e_t^2)
    - Normality test (Shapiro-Wilk)
    """
    res = np.asarray(residuals, dtype=float)
    res = res[np.isfinite(res)]
    n = len(res)

    if n < 3:
        raise ValueError("At least 3 residuals required for residual analysis.")

    max_abs = float(np.max(np.abs(res)))
    mean_r = float(np.mean(res))
    std_r = float(np.std(res, ddof=1)) if n > 1 else 0.0

    # Durbin-Watson test for lag-1 autocorrelation (approx 2.0 indicates no autocorrelation)
    diff = np.diff(res)
    sum_diff_sq = np.sum(diff ** 2)
    sum_res_sq = np.sum(res ** 2)
    dw = float(sum_diff_sq / sum_res_sq) if sum_res_sq > 1e-12 else 2.0

    # Shapiro-Wilk test for normality (valid for 3 <= n <= 5000)
    shapiro_p = None
    is_normal = True
    if 3 <= n <= 5000:
        try:
            stat, shapiro_p = stats.shapiro(res)
            is_normal = (shapiro_p >= 0.05)
        except Exception:
            shapiro_p = None
            is_normal = True

    return ResidualAnalysisMetrics(
        n=n,
        max_abs_residual=max_abs,
        mean_residual=mean_r,
        residual_std_dev=std_r,
        durbin_watson_stat=dw,
        shapiro_wilk_p_value=shapiro_p,
        is_normally_distributed=is_normal,
        residuals=res.tolist()
    )
