"""
Type A Uncertainty Evaluation Module for IMUCA.
Implements Equation 9.4: Type A standard uncertainty from repeated observations.
"""

from typing import Union, List, Optional
from dataclasses import dataclass
import numpy as np
from src.statistics import calculate_descriptive_statistics, StatisticsResult


@dataclass
class TypeAResult:
    n: int
    mean: float
    sample_std_dev: float      # s (in original units, e.g. V)
    sample_std_dev_mv: float   # s (in mV)
    standard_uncertainty: float # u_A = s / sqrt(n) (in original units, e.g. V)
    standard_uncertainty_mv: float # u_A (in mV)
    degrees_of_freedom: int    # nu_A = n - 1
    stats: StatisticsResult
    formula_latex: str = r"u_A = \frac{s}{\sqrt{n}}"
    calculation_steps: str = ""


def evaluate_type_a(
    readings: Union[List[float], np.ndarray]
) -> TypeAResult:
    """
    Evaluate Type A standard uncertainty from a series of repeated measurements.
    
    Args:
        readings: 1D array or list of repeated observations.
        
    Returns:
        TypeAResult containing standard uncertainty, sample SD, degrees of freedom, and full trace.
        
    Raises:
        ValueError: If n < 2 (Type A requires at least 2 repeat observations).
    """
    arr = np.array(readings, dtype=float)
    if len(arr) < 2:
        raise ValueError(f"Type A uncertainty requires at least 2 repeated observations (got n={len(arr)}).")
        
    stats = calculate_descriptive_statistics(arr)
    n = stats.n
    s = stats.std_dev
    u_A = stats.std_error
    nu_A = stats.degrees_of_freedom
    
    s_mv = s * 1000.0
    u_A_mv = u_A * 1000.0
    
    steps = (
        f"1. Number of observations n = {n}\n"
        f"2. Mean x_bar = {stats.mean:.6f} V\n"
        f"3. Sum of squared deviations = {stats.sum_sq_diff:.6e} V^2\n"
        f"4. Sample standard deviation s = sqrt(SS / (n-1)) = {s:.6f} V ({s_mv:.4f} mV)\n"
        f"5. Type A standard uncertainty u_A = s / sqrt({n}) = {u_A:.6f} V ({u_A_mv:.4f} mV)\n"
        f"6. Degrees of freedom nu_A = n - 1 = {nu_A}"
    )
    
    return TypeAResult(
        n=n,
        mean=stats.mean,
        sample_std_dev=s,
        sample_std_dev_mv=s_mv,
        standard_uncertainty=u_A,
        standard_uncertainty_mv=u_A_mv,
        degrees_of_freedom=nu_A,
        stats=stats,
        calculation_steps=steps
    )
