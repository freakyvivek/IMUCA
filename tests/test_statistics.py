"""
Unit Tests for Statistics Module against IMUCA Report Golden Values.
"""

import pytest
import numpy as np
from src.statistics import calculate_descriptive_statistics


# Synthetic repeat readings at 5.000 V from Section 11.1
DEMO_READINGS = [5.02, 5.01, 5.03, 5.02, 5.04, 5.01, 5.02, 5.03, 5.02, 5.01]


def test_descriptive_statistics_golden_values():
    stats = calculate_descriptive_statistics(DEMO_READINGS)
    
    assert stats.n == 10
    # Mean: 5.021 V
    assert pytest.approx(stats.mean, rel=1e-4) == 5.021
    # Sample SD: 9.944 mV (0.009944 V)
    assert pytest.approx(stats.std_dev, rel=1e-3) == 0.009944
    # Sample variance: 9.8889e-5 V^2
    assert pytest.approx(stats.variance, rel=1e-3) == 9.8889e-5
    # Standard error: 3.145 mV (0.003145 V)
    assert pytest.approx(stats.std_error, rel=1e-3) == 0.003145
    # Degrees of freedom: 9
    assert stats.degrees_of_freedom == 9
    # Range: 5.04 - 5.01 = 0.03 V (30 mV)
    assert pytest.approx(stats.range_val, rel=1e-4) == 0.030


def test_statistics_single_observation():
    stats = calculate_descriptive_statistics([5.000])
    assert stats.n == 1
    assert stats.mean == 5.000
    assert stats.std_dev == 0.0
    assert stats.degrees_of_freedom == 0


def test_statistics_empty_dataset():
    with pytest.raises(ValueError):
        calculate_descriptive_statistics([])
