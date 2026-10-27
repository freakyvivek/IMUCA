"""
Unit Tests for IMUCA Measurement Metrics and Statistical Functions.
"""

import pytest
import numpy as np
from src.imuca.measurement_metrics import (
    compute_descriptive_statistics,
    compute_pooled_repeatability,
    compute_error_metrics,
    compute_residual_diagnostics
)


def test_descriptive_statistics_bessel_correction():
    # Known 10 readings: [5.02, 5.01, 5.03, 5.02, 5.04, 5.01, 5.02, 5.03, 5.02, 5.01]
    readings = [5.02, 5.01, 5.03, 5.02, 5.04, 5.01, 5.02, 5.03, 5.02, 5.01]
    stats = compute_descriptive_statistics(readings)

    assert stats.n == 10
    assert pytest.approx(stats.mean, rel=1e-4) == 5.021
    # Check sample std dev has (n-1) denominator: s = 0.009944 V (9.944 mV)
    assert pytest.approx(stats.sample_std_dev, rel=1e-3) == 0.009944
    assert pytest.approx(stats.sample_variance, rel=1e-3) == 9.8889e-5
    # Standard error of mean: s / sqrt(10) = 0.003145 V (3.145 mV)
    assert pytest.approx(stats.standard_error_mean, rel=1e-3) == 0.003145
    assert stats.degrees_of_freedom == 9
    assert pytest.approx(stats.range_val, rel=1e-4) == 0.030

    # 95% Confidence Interval must contain true mean
    ci_low, ci_high = stats.confidence_interval_95
    assert ci_low < stats.mean < ci_high


def test_error_metrics_and_zero_reference_guard():
    measured = [1.02, 2.04, 0.05, 4.08]
    reference = [1.00, 2.00, 0.00, 4.00]  # Point 3 has 0.00 reference

    metrics = compute_error_metrics(measured, reference, zero_threshold=1e-4)
    assert metrics.n == 4
    # Signed errors: [+0.02, +0.04, +0.05, +0.08] -> sum = 0.19, mean = 0.0475
    assert pytest.approx(metrics.mean_bias, rel=1e-4) == 0.0475
    assert pytest.approx(metrics.mae, rel=1e-4) == 0.0475
    # RMSE: sqrt((0.02^2 + 0.04^2 + 0.05^2 + 0.08^2)/4) = sqrt(0.0109/4) = 0.05220
    assert pytest.approx(metrics.rmse, rel=1e-3) == 0.05220

    # Zero reference guard: point 3 must be excluded from percentage error
    assert metrics.zero_reference_count == 1
    assert metrics.valid_relative_count == 3
    # At point 3 (zero ref), percentage error must be NaN
    assert np.isnan(metrics.percentage_errors[2])
    # Other points: 2.0%, 2.0%, 2.0% -> mean = 2.0%
    assert pytest.approx(metrics.mean_percentage_error, rel=1e-3) == 2.0


def test_pooled_repeatability():
    # 3 groups with 3 readings each
    g1 = [1.01, 1.02, 1.01]
    g2 = [2.03, 2.02, 2.04]
    g3 = [3.05, 3.06, 3.05]

    rep = compute_pooled_repeatability([g1, g2, g3])
    assert rep.num_series == 3
    assert rep.degrees_of_freedom == 6
    assert rep.repeatability_std_dev > 0.0
    assert pytest.approx(rep.repeatability_limit, rel=1e-3) == 2.8 * rep.repeatability_std_dev


def test_residual_diagnostics():
    # Residuals from an unbiased linear fit
    residuals = [0.01, -0.02, 0.01, 0.00, -0.01, 0.02, -0.01]
    diag = compute_residual_diagnostics(residuals)

    assert diag.n == 7
    assert pytest.approx(diag.max_abs_residual) == 0.02
    assert abs(diag.mean_residual) < 1e-4
    assert diag.durbin_watson_stat > 0.0
    assert diag.is_normally_distributed
