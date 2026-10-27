"""
IMUCA Metrological Validation, Guard-Banded Conformity, and Drift Analysis Module.

Section 11 Specification:
- Implements guard-banded conformity assessment in accordance with ILAC-G8:09/2019 and ISO 14253-1.
- Implements 3-band decision rules: PASS, CONDITIONAL/MARGINAL, and FAIL.
- Implements linear drift tracking with parameter errors and time-to-breach forecasting.
- Implements CUSUM change-point and persistent systematic drift detection.
- Clearly isolates simulated algorithm verification from physical hardware evidence.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple, Union
import numpy as np
import scipy.stats as stats
import math


@dataclass
class ConformityAssessmentResult:
    """Guard-banded conformity evaluation for a single operating point."""
    nominal_ref: float
    measured_mean: float
    expanded_uncertainty: float    # U (k=2)
    tolerance_span: float          # Half-width T
    lower_spec_limit: float        # LSL = Ref - T
    upper_spec_limit: float        # USL = Ref + T
    guard_band: float              # g = U
    acceptance_lower: float        # LSL + g
    acceptance_upper: float        # USL - g
    simple_conformity: str         # 'PASS' or 'FAIL'
    guard_banded_conformity: str   # 'PASS', 'CONDITIONAL', 'FAIL'
    error_plus_uncertainty: float  # |measured - ref| + U
    remaining_margin: float        # T - (|error| + U)


@dataclass
class DriftAnalysisResult:
    """Statistical evaluation of temporal drift."""
    n: int
    duration_s: float
    initial_estimate: float
    drift_rate_per_s: float
    drift_rate_std_error: float
    p_value: float
    is_drift_significant: bool     # p < 0.05
    cusum_detected_shift: bool
    shift_sample_index: Optional[int]
    forecast_seconds_to_breach: Optional[float]
    summary_message: str


# ==============================================================================
# ILAC-G8 Guard-Banded Decision Rules
# ==============================================================================

def evaluate_guard_banded_conformity(
    measured_value: float,
    reference_value: float,
    expanded_uncertainty: float,
    tolerance_percent: float = 1.0,
    guard_band_factor: float = 1.0
) -> ConformityAssessmentResult:
    """
    Perform guard-banded conformity assessment (ILAC-G8:09/2019).
    
    Decision rules:
    - PASS: Measured value lies within the reduced acceptance interval [LSL + g, USL - g].
    - CONDITIONAL: Measured value is inside [LSL, USL], but uncertainty interval extends outside.
    - FAIL: Measured value is outside [LSL, USL].
    """
    t_span = abs(reference_value) * (tolerance_percent / 100.0)
    lsl = reference_value - t_span
    usl = reference_value + t_span

    u = abs(expanded_uncertainty)
    g = guard_band_factor * u

    acc_lower = lsl + g
    acc_upper = usl - g

    # Simple conformity (ignores uncertainty)
    is_simple_pass = (lsl <= measured_value <= usl)
    simple_status = "PASS" if is_simple_pass else "FAIL"

    # Guard-banded conformity
    if acc_lower <= measured_value <= acc_upper:
        gb_status = "PASS"
    elif is_simple_pass:
        gb_status = "CONDITIONAL"
    else:
        gb_status = "FAIL"

    abs_err = abs(measured_value - reference_value)
    err_plus_u = abs_err + u
    margin = t_span - err_plus_u

    return ConformityAssessmentResult(
        nominal_ref=reference_value,
        measured_mean=measured_value,
        expanded_uncertainty=u,
        tolerance_span=t_span,
        lower_spec_limit=lsl,
        upper_spec_limit=usl,
        guard_band=g,
        acceptance_lower=acc_lower,
        acceptance_upper=acc_upper,
        simple_conformity=simple_status,
        guard_banded_conformity=gb_status,
        error_plus_uncertainty=err_plus_u,
        remaining_margin=margin
    )


# ==============================================================================
# Drift Analysis and Breach Forecasting
# ==============================================================================

def analyze_temporal_drift(
    timestamps_s: Union[List[float], np.ndarray],
    measurements: Union[List[float], np.ndarray],
    nominal_target: float,
    upper_limit: Optional[float] = None,
    lower_limit: Optional[float] = None,
    alpha: float = 0.05,
    cusum_k_sigma: float = 0.5,
    cusum_h_sigma: float = 4.0,
    cusum_sigma: Optional[float] = None
) -> DriftAnalysisResult:
    """
    Analyze linear drift rate and forecast time to tolerance breach.
    Also executes CUSUM (Cumulative Sum) change detection to catch systematic steps.

    CUSUM parameters (defaults reproduce the Milestone-1 behaviour):
    - cusum_k_sigma: reference value k in units of the noise standard deviation.
    - cusum_h_sigma: decision interval h in units of the noise standard deviation.
    - cusum_sigma: noise standard deviation to use. If None, the standard deviation of the
      residuals of the whole-run linear fit is used (offline, non-causal estimate).
    """
    t = np.asarray(timestamps_s, dtype=float)
    y = np.asarray(measurements, dtype=float)
    valid = np.isfinite(t) & np.isfinite(y)
    t = t[valid]
    y = y[valid]
    n = len(t)

    if n < 5:
        raise ValueError("At least 5 time series points required to analyze drift.")

    duration = float(np.max(t) - np.min(t))

    # Linear regression: y(t) = y0 + d * t
    slope, intercept, r_value, p_value, std_err = stats.linregress(t, y)
    is_sig = (p_value < alpha) and (abs(slope) > 1e-12)

    # CUSUM algorithm for persistent step/drift detection
    # Target is nominal_target; detect deviations exceeding 3 * std_dev
    residuals = y - (intercept + slope * t)
    if cusum_sigma is not None:
        s_noise = float(cusum_sigma)
    else:
        s_noise = float(np.std(residuals, ddof=1)) if n > 2 else 1e-6
    k_cusum = cusum_k_sigma * s_noise
    h_threshold = cusum_h_sigma * s_noise

    cusum_pos = 0.0
    cusum_neg = 0.0
    shift_idx = None
    shift_detected = False

    for i in range(n):
        dev = y[i] - nominal_target
        cusum_pos = max(0.0, cusum_pos + dev - k_cusum)
        cusum_neg = max(0.0, cusum_neg - dev - k_cusum)
        if cusum_pos > h_threshold or cusum_neg > h_threshold:
            shift_detected = True
            if shift_idx is None:
                shift_idx = i

    # Breach forecasting
    t_breach = None
    curr_y = float(y[-1])
    curr_t = float(t[-1])

    if is_sig:
        if slope > 0 and upper_limit is not None:
            if curr_y >= upper_limit:
                t_breach = 0.0
            else:
                t_breach = float((upper_limit - curr_y) / slope)
        elif slope < 0 and lower_limit is not None:
            if curr_y <= lower_limit:
                t_breach = 0.0
            else:
                t_breach = float((curr_y - lower_limit) / abs(slope))

    summary = (
        f"Drift rate: {slope * 3600.0:.4f}/hour (p={p_value:.3e}). "
        f"{'Statistically significant drift detected.' if is_sig else 'No significant drift.'}"
    )
    if t_breach == 0.0:
        summary += " Tolerance limit already breached."
    elif t_breach is not None:
        summary += f" Forecasted time to breach: {t_breach:.1f} s."

    return DriftAnalysisResult(
        n=n,
        duration_s=duration,
        initial_estimate=float(intercept),
        drift_rate_per_s=float(slope),
        drift_rate_std_error=float(std_err),
        p_value=float(p_value),
        is_drift_significant=is_sig,
        cusum_detected_shift=shift_detected,
        shift_sample_index=shift_idx,
        forecast_seconds_to_breach=t_breach,
        summary_message=summary
    )
