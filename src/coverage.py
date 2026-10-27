"""
Coverage and Expanded Uncertainty Module for IMUCA.
Implements Equations 9.9 to 9.10: Welch-Satterthwaite effective degrees of freedom,
Student-t coverage factors, and metrological rounding.
"""

from typing import List, Tuple, Union, Optional
from dataclasses import dataclass
import numpy as np
from scipy import stats


@dataclass
class CoverageResult:
    u_c_v: float
    u_c_mv: float
    effective_degrees_of_freedom: float  # nu_eff
    coverage_factor_k: float             # k
    confidence_level: float              # e.g. 0.95
    expanded_uncertainty_v: float        # U = k * u_c
    expanded_uncertainty_mv: float
    rounded_expanded_uncertainty_v: float # Rounded to 2 sig figs
    rounded_expanded_uncertainty_mv: float
    reported_mean_v: float
    formatted_reported_result: str       # e.g. "(5.021 +/- 0.011) V, k = 2"


def round_uncertainty_metrology(val_v: float, uncertainty_v: float) -> Tuple[float, float, str]:
    """
    Rounds expanded uncertainty upward to 2 significant figures, and rounds the
    measurement value to the corresponding decimal place according to ISO/IEC Guide 98-3 (GUM).
    
    Returns:
        (rounded_val, rounded_uncertainty, formatted_string)
    """
    if uncertainty_v <= 0 or not np.isfinite(uncertainty_v):
        return val_v, uncertainty_v, f"{val_v:.6f}"
        
    # Find order of magnitude of uncertainty
    order = int(np.floor(np.log10(uncertainty_v)))
    # For 2 significant digits:
    scale = 10 ** (order - 1)
    # Metrological practice: round up to 2 sig figs
    u_rounded = np.ceil(uncertainty_v / scale - 1e-9) * scale
    
    # Decimal places required
    decimals = max(0, -order + 1)
    
    # Round mean to same decimal places
    v_rounded = round(val_v, decimals)
    
    fmt = f"({v_rounded:.{decimals}f} +/- {u_rounded:.{decimals}f}) V"
    return v_rounded, u_rounded, fmt


def calculate_welch_satterthwaite(
    uncertainties_v: List[float],
    degrees_of_freedom: List[Union[float, int]],
    u_c_v: float
) -> float:
    """
    Calculate Welch-Satterthwaite effective degrees of freedom:
    nu_eff = u_c^4 / SUM( u_i^4 / nu_i )
    """
    if u_c_v <= 0:
        return 0.0
        
    denom = 0.0
    for u_i, nu_i in zip(uncertainties_v, degrees_of_freedom):
        if np.isfinite(nu_i) and nu_i > 0 and u_i > 0:
            denom += (u_i ** 4) / float(nu_i)
            
    if denom <= 1e-15:
        return 1000.0  # Infinite / large sample size approximation
        
    nu_eff = (u_c_v ** 4) / denom
    return float(nu_eff)


def evaluate_expanded_uncertainty(
    u_c_v: float,
    uncertainties_v: List[float],
    degrees_of_freedom: List[Union[float, int]],
    mean_reading_v: float,
    confidence_level: float = 0.95,
    force_k: Optional[float] = None
) -> CoverageResult:
    """
    Calculate effective degrees of freedom, coverage factor k, expanded uncertainty U,
    and formatted reported result.
    """
    u_c_mv = u_c_v * 1000.0
    nu_eff = calculate_welch_satterthwaite(uncertainties_v, degrees_of_freedom, u_c_v)
    
    if force_k is not None:
        k = float(force_k)
    else:
        if nu_eff >= 30:
            k = 2.0
        elif nu_eff > 1:
            # Two-sided Student-t critical value
            alpha = 1.0 - confidence_level
            k = float(stats.t.ppf(1.0 - alpha / 2.0, df=nu_eff))
        else:
            k = 2.0
            
    U_v = k * u_c_v
    U_mv = U_v * 1000.0
    
    v_rnd, u_rnd, fmt_str = round_uncertainty_metrology(mean_reading_v, U_v)
    fmt_reported = f"{fmt_str}, k = {k:.2f} (approx. {confidence_level*100:.0f}% confidence)"
    
    return CoverageResult(
        u_c_v=u_c_v,
        u_c_mv=u_c_mv,
        effective_degrees_of_freedom=nu_eff,
        coverage_factor_k=k,
        confidence_level=confidence_level,
        expanded_uncertainty_v=U_v,
        expanded_uncertainty_mv=U_mv,
        rounded_expanded_uncertainty_v=u_rnd,
        rounded_expanded_uncertainty_mv=u_rnd * 1000.0,
        reported_mean_v=v_rnd,
        formatted_reported_result=fmt_reported
    )
