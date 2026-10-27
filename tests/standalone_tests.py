"""
Standalone Unit Test Suite for IMUCA (Pure Python / NumPy / SciPy without test framework overhead).
"""

import math
import os
import sys

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np

from src.statistics import calculate_descriptive_statistics
from src.type_a import evaluate_type_a
from src.type_b import get_default_type_b_sources, evaluate_type_b
from src.budget import build_uncertainty_budget
from src.coverage import evaluate_expanded_uncertainty, round_uncertainty_metrology
from src.calibration import evaluate_calibration_sweep, evaluate_single_point_conformity
from src.drift import analyze_within_run_trend, evaluate_drift_history
from src.limits import EngineeringLimits
from src.rules import evaluate_decision_rules
from src.loader import load_csv, detect_measurement_columns
from src.validator import validate_dataset


def approx(a, b, rel=1e-2, abs_tol=1e-4):
    return math.isclose(a, b, rel_tol=rel, abs_tol=abs_tol)


def test_statistics():
    readings = [5.02, 5.01, 5.03, 5.02, 5.04, 5.01, 5.02, 5.03, 5.02, 5.01]
    stats = calculate_descriptive_statistics(readings)
    assert stats.n == 10, f"Expected n=10, got {stats.n}"
    assert approx(stats.mean, 5.021, rel=1e-4), f"Mean error: {stats.mean}"
    assert approx(stats.std_dev, 0.009944, rel=1e-2), f"SD error: {stats.std_dev}"
    assert approx(stats.variance, 9.8889e-5, rel=1e-2), f"Variance error: {stats.variance}"
    assert approx(stats.std_error, 0.003145, rel=1e-2), f"Std error: {stats.std_error}"
    assert stats.degrees_of_freedom == 9
    assert approx(stats.range_val, 0.030, rel=1e-3)
    print("  [PASS] test_statistics")


def test_uncertainty():
    readings = [5.02, 5.01, 5.03, 5.02, 5.04, 5.01, 5.02, 5.03, 5.02, 5.01]
    type_a = evaluate_type_a(readings)
    assert approx(type_a.standard_uncertainty_mv, 3.145, rel=1e-2)
    assert type_a.degrees_of_freedom == 9

    sources = get_default_type_b_sources(reading_v=5.021)
    type_b = evaluate_type_b(sources, reading_v=5.021)
    assert approx(type_b.combined_type_b_mv, 4.234, rel=1e-2)

    budget = build_uncertainty_budget(type_a, type_b, confidence_level=0.95, force_k=2.0)
    assert approx(budget.combined_uncertainty_mv, 5.274, rel=1e-2), f"u_c was {budget.combined_uncertainty_mv}"
    assert approx(budget.coverage.expanded_uncertainty_mv, 10.55, rel=1e-2)
    assert approx(budget.coverage.effective_degrees_of_freedom, 71.2, abs_tol=1.0)
    assert budget.dominant_source.source_name == "Repeatability"
    assert approx(budget.dominant_source.variance_contribution_percent, 35.6, abs_tol=0.5)

    v_rnd, u_rnd, fmt = round_uncertainty_metrology(5.021, 0.01055)
    assert u_rnd == 0.011
    assert v_rnd == 5.021
    print("  [PASS] test_uncertainty")


def test_calibration():
    refs = [0.500, 1.000, 1.500, 2.000, 2.500, 3.000, 3.500, 4.000, 4.500, 5.000]
    duts = [0.51,  1.01,  1.51,  2.01,  2.51,  3.02,  3.52,  4.02,  4.52,  5.02]
    cal = evaluate_calibration_sweep(refs, duts, tolerance_percent=1.0, resolution_v=0.01)

    assert approx(cal.zero_offset_mv, 6.67, rel=1e-2), f"Offset was {cal.zero_offset_mv}"
    assert approx(cal.gain_error_percent, 0.303, rel=1e-2), f"Gain error was {cal.gain_error_percent}"
    assert approx(cal.r_squared, 0.999997, abs_tol=1e-4)
    assert cal.pass_count == 8
    assert cal.marginal_count == 1
    assert cal.fail_count == 1
    assert cal.overall_status == "FAIL"

    res = cal.residuals
    assert approx(res.max_residual_mv, 4.24, rel=1e-2)
    assert not res.is_nonlinearity_present

    gb = evaluate_single_point_conformity(5.000, 5.021, 0.0105, tolerance_percent=1.0)
    assert gb["simple_conformity"] == "PASS"
    assert gb["guard_banded_conformity"] == "PASS"
    assert approx(gb["total_error_plus_uncertainty_mv"], 31.5, abs_tol=0.2)
    print("  [PASS] test_calibration")


def test_drift():
    readings = [5.02, 5.01, 5.03, 5.02, 5.04, 5.01, 5.02, 5.03, 5.02, 5.01]
    w_trend = analyze_within_run_trend(readings)
    assert approx(w_trend.slope_mv_per_reading, -0.303, rel=1e-2)
    assert approx(w_trend.std_err_slope, 1.156, rel=1e-2)
    assert approx(w_trend.p_value, 0.80, abs_tol=0.03)
    assert not w_trend.is_significant

    sessions = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    errors_mv = [21.0, 22.0, 21.0, 24.0, 25.0, 26.0, 26.0, 28.0, 29.0, 31.0]
    drift = evaluate_drift_history(sessions, errors_mv, drift_threshold_mv_per_session=0.50, tolerance_mv=50.0)

    assert approx(drift.slope_b, 1.10, rel=1e-2)
    assert approx(drift.std_err_b, 0.085, rel=1e-2)
    assert approx(drift.r_squared, 0.954, abs_tol=0.01)
    assert drift.p_value < 1e-5
    assert drift.is_drift_significant
    assert drift.rule_status == "POSSIBLE DRIFT"
    assert approx(drift.projected_breach_session, 28.0, abs_tol=1.0)
    print("  [PASS] test_drift")


def test_decision_engine():
    limits = EngineeringLimits(
        u_allowable_mv=25.0,
        tolerance_mv=50.0,
        drift_threshold_mv=0.50,
        s_allowable_mv=15.0
    )

    # Demo A: Single session (no history)
    res_a = evaluate_decision_rules(
        expanded_uncertainty_mv=10.55,
        absolute_error_mv=21.0,
        sample_std_dev_mv=9.944,
        limits=limits,
        has_drift_history=False,
        sweep_nonconforming_points=[1]
    )
    assert res_a.headline_status == "ACCEPTABLE"
    assert res_a.primary_triggered_rule == "R5"
    assert res_a.calibration_status_badge == "PASS"

    # Demo B: With history
    res_b = evaluate_decision_rules(
        expanded_uncertainty_mv=10.55,
        absolute_error_mv=21.0,
        sample_std_dev_mv=9.944,
        limits=limits,
        drift_slope_mv_per_session=1.10,
        drift_p_value=1.3e-6,
        has_drift_history=True,
        projected_breach_session=28.0
    )
    assert res_b.headline_status == "ATTENTION REQUIRED"
    assert res_b.primary_triggered_rule == "R3"
    assert "SIGNIFICANT UPWARD DRIFT" in res_b.drift_status_badge
    print("  [PASS] test_decision_engine")


def test_validation():
    path = os.path.join("data", "demo_measurements.csv")
    df = load_csv(path)
    res = validate_dataset(df, min_val=0.0, max_val=20.0)
    assert res.is_valid
    assert res.valid_rows_count == 10

    inv_path = os.path.join("data", "sample_invalid_data.csv")
    df_inv = load_csv(inv_path)
    res_inv = validate_dataset(df_inv, columns_to_check=["DUT_V"], min_val=0.0, max_val=20.0)
    assert res_inv.skipped_rows_count > 0
    assert len(res_inv.outlier_indices) >= 1
    print("  [PASS] test_validation")


if __name__ == "__main__":
    print("==================================================")
    print(" RUNNING IMUCA GOLDEN REFERENCE VERIFICATION SUITE")
    print("==================================================")
    test_statistics()
    test_uncertainty()
    test_calibration()
    test_drift()
    test_decision_engine()
    test_validation()
    print("\nALL 6 VERIFICATION TEST SUITES PASSED (100%)!")
