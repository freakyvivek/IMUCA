"""
Unit Tests for Calibration Regression and Conformity Assessment against Golden Reference Values.
"""

import pytest
import numpy as np
from src.calibration import evaluate_calibration_sweep, evaluate_single_point_conformity


# Synthetic 10-point sweep data from Table 10.3 & 13.1
REFS = [0.500, 1.000, 1.500, 2.000, 2.500, 3.000, 3.500, 4.000, 4.500, 5.000]
DUTS = [0.51,  1.01,  1.51,  2.01,  2.51,  3.02,  3.52,  4.02,  4.52,  5.02]


def test_calibration_sweep_regression():
    cal = evaluate_calibration_sweep(REFS, DUTS, tolerance_percent=1.0, resolution_v=0.01)
    
    # Intercept / zero offset: +6.67 mV (0.006667 V)
    assert pytest.approx(cal.zero_offset_mv, rel=1e-2) == 6.67
    # Gain error: +0.303 % (m = 1.003030)
    assert pytest.approx(cal.gain_error_percent, rel=1e-2) == 0.303
    # Linearity R^2: 0.999997
    assert pytest.approx(cal.r_squared, abs=1e-5) == 0.999997
    
    # Conformity breakdown: 8 PASS, 1 MARGINAL, 1 FAIL
    assert cal.pass_count == 8
    assert cal.marginal_count == 1
    assert cal.fail_count == 1
    assert cal.overall_status == "FAIL"
    
    # Point 1 (0.500 V): FAIL (+2.000%)
    assert cal.points[0].conformity_status == "FAIL"
    assert pytest.approx(cal.points[0].percentage_error, rel=1e-3) == 2.000
    
    # Point 2 (1.000 V): MARGINAL (+1.000%)
    assert cal.points[1].conformity_status == "MARGINAL"
    assert pytest.approx(cal.points[1].percentage_error, rel=1e-3) == 1.000
    
    # Point 10 (5.000 V): PASS (+0.400%)
    assert cal.points[9].conformity_status == "PASS"
    assert pytest.approx(cal.points[9].percentage_error, rel=1e-3) == 0.400


def test_residual_analysis():
    cal = evaluate_calibration_sweep(REFS, DUTS, tolerance_percent=1.0, resolution_v=0.01)
    res = cal.residuals
    
    # Max residual is 4.24 mV
    assert pytest.approx(res.max_residual_mv, rel=1e-2) == 4.24
    # Below half resolution (5.0 mV), so linear model is adequate
    assert not res.is_nonlinearity_present


def test_single_point_guard_banded_conformity():
    # 5.000 V point: Error = +21 mV, U = 10.5 mV, T = 50 mV
    gb = evaluate_single_point_conformity(
        reference_v=5.000,
        mean_dut_v=5.021,
        expanded_uncertainty_v=0.0105,
        tolerance_percent=1.0
    )
    assert gb["simple_conformity"] == "PASS"
    assert gb["guard_banded_conformity"] == "PASS"
    assert pytest.approx(gb["total_error_plus_uncertainty_mv"], abs=0.1) == 31.5
    assert pytest.approx(gb["remaining_margin_mv"], abs=0.1) == 18.5


# ==============================================================================
# Tests for new modular package: src.imuca.calibration
# ==============================================================================

from src.imuca.calibration import CalibrationEngine


def test_imuca_calibration_train_validation_separation():
    # Synthetic current calibration points: 120 points from 100mA to 2000mA
    # True relationship: DUT = 1.015 * Ref + 15.0 mA + noise
    rng = np.random.default_rng(42)
    refs = np.linspace(100.0, 2000.0, 50)
    duts = 1.015 * refs + 15.0 + rng.normal(0, 0.5, size=50)

    engine = CalibrationEngine()
    comp = engine.evaluate_train_validation_split(
        x_dut=duts,
        y_ref=refs,
        train_ratio=0.6,
        model_type="linear",
        random_seed=42
    )

    # 30 train, 20 validation
    assert comp.train_count == 30
    assert comp.validation_count == 20
    assert comp.is_performance_improved

    # Post-calibration MAE must be substantially reduced on held-out validation data
    assert comp.mae_reduction_percent > 90.0
    assert comp.rmse_reduction_percent > 90.0
    assert comp.calibrated_metrics.mae < 1.0  # Residual noise level ~0.5 mA


def test_imuca_polynomial_f_test_rejection():
    # Pure linear data: higher-degree polynomial must NOT be justified
    x = np.linspace(1.0, 10.0, 25)
    y = 2.0 * x + 0.5 + np.random.default_rng(10).normal(0, 0.01, size=25)

    engine = CalibrationEngine(f_test_alpha=0.05)
    best_model = engine.select_best_model(x_dut=x, y_ref=y, max_degree=3)

    # Must stay linear because quadratic term is not statistically significant
    assert best_model.degree == 1
    assert not best_model.is_polynomial_justified


def test_imuca_domain_extrapolation_detection():
    engine = CalibrationEngine()
    x_train = [1.0, 2.0, 3.0, 4.0, 5.0]
    y_train = [1.1, 2.1, 3.1, 4.1, 5.1]
    model = engine.fit_linear(x_train, y_train)

    x_test = [0.5, 3.0, 6.0]  # 0.5 and 6.0 are extrapolated
    is_extrap, warnings = model.check_extrapolation(x_test)

    assert is_extrap[0] == True
    assert is_extrap[1] == False
    assert is_extrap[2] == True
    assert len(warnings) == 1

