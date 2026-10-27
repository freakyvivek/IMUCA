"""
Statistical Analysis Module for IMUCA.
Implements Equations 9.1 to 9.3: Sample statistics with (n-1) Bessel's correction,
standard error of the mean, and reproducible calculation traces.
"""

from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
import numpy as np


@dataclass
class StatisticsResult:
    n: int
    mean: float
    std_dev: float           # Sample SD (n-1 denominator)
    variance: float          # Sample variance (n-1 denominator)
    std_error: float         # Standard error of mean: s / sqrt(n)
    range_val: float
    min_val: float
    max_val: float
    median: float
    degrees_of_freedom: int  # nu = n - 1
    sum_x: float
    sum_sq_diff: float       # Sum of (x_i - mean)^2
    deviations: List[float] = field(default_factory=list)
    squared_deviations: List[float] = field(default_factory=list)
    raw_values: List[float] = field(default_factory=list)


def calculate_descriptive_statistics(
    readings: Union[List[float], np.ndarray]
) -> StatisticsResult:
    """
    Calculate full sample descriptive statistics for a series of repeated observations.
    
    Uses sample standard deviation with (n - 1) denominator strictly following metrology standards (GUM / ISO 5725).
    
    Args:
        readings: 1D array or list of repeated observations.
        
    Returns:
        StatisticsResult containing all computed statistical properties and calculation trace.
        
    Raises:
        ValueError: If readings contains fewer than 1 observation or non-numeric entries.
    """
    arr = np.array(readings, dtype=float)
    if len(arr) == 0:
        raise ValueError("Cannot calculate statistics on an empty dataset.")
        
    n = len(arr)
    sum_x = float(np.sum(arr))
    mean = float(sum_x / n)
    
    if n == 1:
        # Single reading: dispersion undefined
        return StatisticsResult(
            n=1,
            mean=mean,
            std_dev=0.0,
            variance=0.0,
            std_error=0.0,
            range_val=0.0,
            min_val=mean,
            max_val=mean,
            median=mean,
            degrees_of_freedom=0,
            sum_x=sum_x,
            sum_sq_diff=0.0,
            deviations=[0.0],
            squared_deviations=[0.0],
            raw_values=arr.tolist()
        )
        
    deviations = (arr - mean).tolist()
    sq_deviations = ((arr - mean) ** 2).tolist()
    sum_sq_diff = float(np.sum((arr - mean) ** 2))
    
    # Sample variance with (n - 1) Bessel's correction
    variance = float(sum_sq_diff / (n - 1))
    std_dev = float(np.sqrt(variance))
    std_error = float(std_dev / np.sqrt(n))
    
    min_val = float(np.min(arr))
    max_val = float(np.max(arr))
    range_val = float(max_val - min_val)
    median = float(np.median(arr))
    df = n - 1
    
    return StatisticsResult(
        n=n,
        mean=mean,
        std_dev=std_dev,
        variance=variance,
        std_error=std_error,
        range_val=range_val,
        min_val=min_val,
        max_val=max_val,
        median=median,
        degrees_of_freedom=df,
        sum_x=sum_x,
        sum_sq_diff=sum_sq_diff,
        deviations=deviations,
        squared_deviations=sq_deviations,
        raw_values=arr.tolist()
    )
