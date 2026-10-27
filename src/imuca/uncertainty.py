"""
IMUCA Uncertainty Engine in Compliance with JCGM 100:2008 (GUM) and JCGM 101:2008.

Section 9 Specification:
- Implements Type A statistical evaluation from observations.
- Implements Type B evaluations from distributions: Rectangular, Triangular, Normal, U-shaped.
- Implements first-order GUM sensitivity coefficient propagation with optional covariance.
- Implements the indirect measurement model for current: I = V_shunt / R_shunt with analytical sensitivities.
- Implements Welch-Satterthwaite formula for effective degrees of freedom (nu_eff).
- Implements expanded uncertainty U = k * u_c and coverage factor determination.
- Implements variance percentage shares and dominant source ranking.
- Implements metrological rounding rules (2 significant digits for uncertainty).
- Implements optional Monte Carlo uncertainty propagation (JCGM 101:2008).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple, Union, Callable
import numpy as np
import scipy.stats as stats
import math


@dataclass
class UncertaintyComponent:
    """Documented uncertainty contribution in compliance with GUM Table 12.1."""
    name: str
    source_category: str          # 'REPEATABILITY', 'RESOLUTION', 'TOLERANCE', 'REFERENCE_STANDARD', 'ENVIRONMENT', 'SHUNT_RESISTOR', 'CALIBRATION_FIT'
    uncertainty_type: str         # 'A' or 'B'
    distribution: str             # 'NORMAL', 'RECTANGULAR', 'TRIANGULAR', 'U_SHAPED'
    input_value: float            # Half-width a or raw s
    unit: str
    divisor: float
    standard_uncertainty: float   # u(x_i) = input_value / divisor
    sensitivity_coefficient: float# c_i = df/dx_i
    uncertainty_contribution: float # c_i * u(x_i)
    degrees_of_freedom: float     # nu_i (inf for Type B with high confidence)
    variance_share_percent: float = 0.0 # (c_i * u_i)^2 / u_c^2 * 100 %
    notes: str = ""


@dataclass
class UncertaintyBudget:
    """Complete GUM-compliant uncertainty budget for a measurand."""
    measurand_name: str
    measurand_unit: str
    nominal_value: float
    components: List[UncertaintyComponent]
    combined_standard_uncertainty: float # u_c
    effective_degrees_of_freedom: float  # nu_eff via Welch-Satterthwaite
    coverage_factor_k: float             # k
    confidence_level: float              # e.g. 0.95
    expanded_uncertainty: float          # U = k * u_c
    dominant_component: UncertaintyComponent
    reported_result_string: str          # e.g. "(5.021 +/- 0.011) V"
    monte_carlo_result: Optional[Dict[str, float]] = None


# ==============================================================================
# Type A Evaluation
# ==============================================================================

def evaluate_type_a(
    readings: Union[List[float], np.ndarray],
    unit: str = "V",
    name: str = "Repeatability"
) -> UncertaintyComponent:
    """
    Evaluate Type A standard uncertainty from repeated observations (GUM 4.2).
    u_A = s / sqrt(n), degrees of freedom nu = n - 1.
    """
    arr = np.asarray(readings, dtype=float)
    arr = arr[np.isfinite(arr)]
    n = len(arr)

    if n < 2:
        raise ValueError("At least 2 repeated observations required to evaluate Type A uncertainty.")

    var = float(np.var(arr, ddof=1))
    s = float(np.sqrt(var))
    u_a = float(s / np.sqrt(n))
    df = float(n - 1)

    return UncertaintyComponent(
        name=name,
        source_category="REPEATABILITY",
        uncertainty_type="A",
        distribution="NORMAL",
        input_value=s,
        unit=unit,
        divisor=float(np.sqrt(n)),
        standard_uncertainty=u_a,
        sensitivity_coefficient=1.0,
        uncertainty_contribution=u_a,
        degrees_of_freedom=df,
        notes=f"Calculated from n={n} repeated observations (s={s:.6g} {unit})"
    )


# ==============================================================================
# Type B Evaluation
# ==============================================================================

def evaluate_type_b(
    name: str,
    limit_value: float,
    distribution: str = "RECTANGULAR",
    unit: str = "V",
    sensitivity_coefficient: float = 1.0,
    degrees_of_freedom: float = float("inf"),
    source_category: str = "TOLERANCE",
    notes: str = ""
) -> UncertaintyComponent:
    """
    Evaluate Type B standard uncertainty from specifications or distributions (GUM 4.3).
    - RECTANGULAR: u = a / sqrt(3)
    - TRIANGULAR: u = a / sqrt(6)
    - NORMAL: u = a / k (default k=2.0 if not specified in notes)
    - U_SHAPED: u = a / sqrt(2)
    """
    dist_norm = distribution.strip().upper()

    if dist_norm == "RECTANGULAR":
        divisor = float(np.sqrt(3.0))
    elif dist_norm == "TRIANGULAR":
        divisor = float(np.sqrt(6.0))
    elif dist_norm == "NORMAL":
        divisor = 2.0  # Standard k=2 assumption for 95% manufacturer tolerance
    elif dist_norm in ("U_SHAPED", "USHAPED"):
        divisor = float(np.sqrt(2.0))
    else:
        raise ValueError(f"Unsupported Type B distribution: '{distribution}'. Must be RECTANGULAR, TRIANGULAR, NORMAL, or U_SHAPED.")

    u_std = float(limit_value / divisor)
    u_contrib = float(abs(sensitivity_coefficient) * u_std)

    return UncertaintyComponent(
        name=name,
        source_category=source_category,
        uncertainty_type="B",
        distribution=dist_norm,
        input_value=limit_value,
        unit=unit,
        divisor=divisor,
        standard_uncertainty=u_std,
        sensitivity_coefficient=sensitivity_coefficient,
        uncertainty_contribution=u_contrib,
        degrees_of_freedom=degrees_of_freedom,
        notes=notes
    )


# ==============================================================================
# Indirect Model: Current Shunt I = V_shunt / R_shunt
# ==============================================================================

def evaluate_shunt_current_uncertainty(
    v_shunt_v: float,
    r_shunt_ohm: float,
    u_v_shunt_v: float,
    u_r_shunt_ohm: float,
    cov_v_r: float = 0.0,
    nu_v: float = float("inf"),
    nu_r: float = float("inf")
) -> Tuple[float, List[UncertaintyComponent]]:
    """
    Evaluates combined standard uncertainty for indirect current measurement:
    I = V_shunt / R_shunt
    
    Sensitivity coefficients:
    c_V = dI/dV_shunt = 1 / R_shunt
    c_R = dI/dR_shunt = -V_shunt / (R_shunt^2) = -I / R_shunt
    
    Combined variance:
    u_c^2(I) = c_V^2 * u^2(V) + c_R^2 * u^2(R) + 2 * c_V * c_R * cov(V, R)
    """
    if abs(r_shunt_ohm) < 1e-12:
        raise ValueError("Shunt resistance cannot be zero.")

    i_val = v_shunt_v / r_shunt_ohm
    c_v = 1.0 / r_shunt_ohm
    c_r = -v_shunt_v / (r_shunt_ohm ** 2)

    comp_v = UncertaintyComponent(
        name="Shunt Voltage Drop",
        source_category="SHUNT_VOLTAGE",
        uncertainty_type="B",
        distribution="NORMAL",
        input_value=u_v_shunt_v * 2.0,
        unit="V",
        divisor=2.0,
        standard_uncertainty=u_v_shunt_v,
        sensitivity_coefficient=c_v,
        uncertainty_contribution=abs(c_v) * u_v_shunt_v,
        degrees_of_freedom=nu_v,
        notes=f"c_V = 1 / R = {c_v:.4f} A/V"
    )

    comp_r = UncertaintyComponent(
        name="Shunt Resistor Tolerance",
        source_category="SHUNT_RESISTOR",
        uncertainty_type="B",
        distribution="RECTANGULAR",
        input_value=u_r_shunt_ohm * np.sqrt(3.0),
        unit="Ohm",
        divisor=float(np.sqrt(3.0)),
        standard_uncertainty=u_r_shunt_ohm,
        sensitivity_coefficient=c_r,
        uncertainty_contribution=abs(c_r) * u_r_shunt_ohm,
        degrees_of_freedom=nu_r,
        notes=f"c_R = -V / R^2 = {c_r:.4f} A/Ohm"
    )

    return i_val, [comp_v, comp_r]


# ==============================================================================
# GUM Budget Compilation and Welch-Satterthwaite Propagation
# ==============================================================================

def round_uncertainty_metrology(value: float, uncertainty: float) -> Tuple[float, float, str]:
    """
    Metrological rounding rule:
    1. Express standard or expanded uncertainty to 2 significant digits.
    2. Round the measured value to the same least significant decimal place.
    """
    if uncertainty <= 0 or not math.isfinite(uncertainty):
        return value, uncertainty, f"{value}"

    # Determine scale of uncertainty
    order = math.floor(math.log10(uncertainty))
    # 2 significant digits
    factor = 10 ** (1 - order)
    rounded_u = math.ceil(uncertainty * factor) / factor

    # Re-evaluate order in case ceiling bumped value across a decade boundary (e.g. 0.00995 -> 0.010)
    order_u = math.floor(math.log10(rounded_u))
    decimals = max(0, 1 - order_u)
    rounded_val = round(value, decimals)

    fmt_str = f"({rounded_val:.{decimals}f} +/- {rounded_u:.{decimals}f})"
    return rounded_val, rounded_u, fmt_str


def build_uncertainty_budget(
    measurand_name: str,
    nominal_value: float,
    measurand_unit: str,
    components: List[UncertaintyComponent],
    confidence_level: float = 0.95,
    force_k: Optional[float] = None,
    covariances: Optional[Dict[Tuple[int, int], float]] = None,
    run_monte_carlo: bool = False,
    mc_trials: int = 10000,
    random_seed: int = 42
) -> UncertaintyBudget:
    """
    Compile uncertainty budget in accordance with JCGM 100:2008 (GUM).
    Propagates independent components and covariance terms:
    u_c^2 = sum(c_i^2 * u_i^2) + 2 * sum_{i < j} c_i * c_j * cov(x_i, x_j)
    Computes Welch-Satterthwaite nu_eff and expanded uncertainty U = k * u_c.
    """
    if not components:
        raise ValueError("Cannot build uncertainty budget with zero components.")

    # 1. Sum variance contributions
    u_c_sq = 0.0
    scaled_contribs = []
    ws_denominator = 0.0

    for comp in components:
        c_i = comp.sensitivity_coefficient
        u_i = comp.standard_uncertainty
        contrib = c_i * u_i
        contrib_sq = contrib ** 2
        u_c_sq += contrib_sq
        scaled_contribs.append(abs(contrib))

        # Welch-Satterthwaite denominator: (c_i * u_i)^4 / nu_i
        nu_i = comp.degrees_of_freedom
        if nu_i > 0 and math.isfinite(nu_i):
            ws_denominator += (contrib_sq ** 2) / nu_i

    # Covariance terms: JCGM 100:2008 formula 13:
    # 2 * sum_{i < j} c_i * c_j * cov(x_i, x_j)
    # Robustly handles either single-entry {(i, j): cov} or symmetric {(i, j): cov, (j, i): cov}
    if covariances:
        seen_pairs = set()
        for (i, j), cov_val in covariances.items():
            if i == j:
                continue  # skip diagonal variance (already handled in individual components)
            if 0 <= i < len(components) and 0 <= j < len(components):
                pair = (min(i, j), max(i, j))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                c_i = components[i].sensitivity_coefficient
                c_j = components[j].sensitivity_coefficient
                # Check if symmetric partner exists in dictionary
                if (j, i) in covariances:
                    avg_cov = (cov_val + covariances[(j, i)]) / 2.0
                    u_c_sq += 2.0 * c_i * c_j * avg_cov
                else:
                    u_c_sq += 2.0 * c_i * c_j * cov_val

    u_c = float(np.sqrt(max(1e-15, u_c_sq)))

    # 2. Variance shares and dominant component
    updated_components = []
    max_share = -1.0
    dominant_comp = components[0]

    for comp in components:
        c_i = comp.sensitivity_coefficient
        u_i = comp.standard_uncertainty
        v_share = float(((c_i * u_i) ** 2) / (u_c ** 2) * 100.0)
        
        comp.variance_share_percent = v_share
        updated_components.append(comp)

        if v_share > max_share:
            max_share = v_share
            dominant_comp = comp

    # 3. Effective Degrees of Freedom (Welch-Satterthwaite formula)
    if ws_denominator > 1e-15:
        nu_eff = float((u_c ** 4) / ws_denominator)
    else:
        nu_eff = float("inf")

    # 4. Coverage factor k
    if force_k is not None:
        k = float(force_k)
    elif math.isfinite(nu_eff) and nu_eff < 100:
        # Use Student's t critical value for small effective degrees of freedom
        alpha = 1.0 - confidence_level
        k = float(stats.t.ppf(1.0 - alpha / 2.0, df=nu_eff))
    else:
        # Normal distribution approximation (k = 1.96 for 95%, typically reported as 2.0)
        alpha = 1.0 - confidence_level
        k = float(stats.norm.ppf(1.0 - alpha / 2.0))

    expanded_u = float(k * u_c)

    # 5. Metrological Rounding
    val_r, u_r, fmt_str = round_uncertainty_metrology(nominal_value, expanded_u)
    reported_str = f"{fmt_str} {measurand_unit} (k={k:.2f}, {confidence_level*100:.0f}% confidence)"

    # 6. Optional Monte Carlo Propagation (JCGM 101:2008)
    mc_results = None
    if run_monte_carlo:
        rng = np.random.default_rng(random_seed)
        simulated_measurand = np.full(mc_trials, nominal_value, dtype=float)

        for comp in components:
            u_i = comp.standard_uncertainty
            c_i = comp.sensitivity_coefficient
            dist = comp.distribution.upper()

            if dist == "RECTANGULAR":
                a = comp.input_value
                deviations = rng.uniform(-a, a, size=mc_trials)
            elif dist == "TRIANGULAR":
                a = comp.input_value
                deviations = rng.triangular(-a, 0, a, size=mc_trials)
            elif dist in ("U_SHAPED", "USHAPED"):
                a = comp.input_value
                # Arcsine / U-shaped distribution
                theta = rng.uniform(0, 2 * np.pi, size=mc_trials)
                deviations = a * np.sin(theta)
            else:  # Normal
                deviations = rng.normal(0.0, u_i, size=mc_trials)

            simulated_measurand += c_i * deviations

        mc_mean = float(np.mean(simulated_measurand))
        mc_std = float(np.std(simulated_measurand, ddof=1))
        p_low = (1.0 - confidence_level) / 2.0 * 100.0
        p_high = (1.0 + confidence_level) / 2.0 * 100.0
        q_low, q_high = np.percentile(simulated_measurand, [p_low, p_high])

        mc_results = {
            "trials": mc_trials,
            "mean": mc_mean,
            "standard_uncertainty": mc_std,
            "interval_low": float(q_low),
            "interval_high": float(q_high),
            "expanded_uncertainty_half_width": float(0.5 * (q_high - q_low))
        }

    return UncertaintyBudget(
        measurand_name=measurand_name,
        measurand_unit=measurand_unit,
        nominal_value=nominal_value,
        components=updated_components,
        combined_standard_uncertainty=u_c,
        effective_degrees_of_freedom=nu_eff,
        coverage_factor_k=k,
        confidence_level=confidence_level,
        expanded_uncertainty=expanded_u,
        dominant_component=dominant_comp,
        reported_result_string=reported_str,
        monte_carlo_result=mc_results
    )
