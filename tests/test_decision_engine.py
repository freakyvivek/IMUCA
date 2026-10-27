"""
Unit Tests for Transparent Ordered Decision Engine (R1 to R5).
"""

import pytest
from src.limits import EngineeringLimits
from src.rules import evaluate_decision_rules


def test_demo_a_single_session_decision():
    """
    Demo A: Single session at 5.000 V without history.
    Expected: MEASUREMENT ACCEPTABLE, headline ACCEPTABLE, R5 triggered.
    """
    limits = EngineeringLimits(
        u_allowable_mv=25.0,
        tolerance_mv=50.0,
        drift_threshold_mv=0.50,
        s_allowable_mv=15.0
    )
    
    # 5.000 V point: U = 10.55 mV, E = +21.0 mV, s = 9.944 mV, no drift history
    res = evaluate_decision_rules(
        expanded_uncertainty_mv=10.55,
        absolute_error_mv=21.0,
        sample_std_dev_mv=9.944,
        limits=limits,
        drift_slope_mv_per_session=None,
        drift_p_value=None,
        has_drift_history=False,
        sweep_nonconforming_points=[1] # Point 1 (0.5V) failed sweep
    )
    
    assert res.headline_status == "ACCEPTABLE"
    assert res.primary_triggered_rule == "R5"
    assert res.primary_status_label == "MEASUREMENT ACCEPTABLE"
    assert res.calibration_status_badge == "PASS"
    assert res.drift_status_badge == "NOT ASSESSED"
    assert "0.5 V" in res.detailed_recommendation or "sweep" in res.detailed_recommendation.lower()


def test_demo_b_with_drift_history_decision():
    """
    Demo B: 10-session history supplied.
    Expected: POSSIBLE DRIFT, headline ATTENTION REQUIRED, R3 triggered, projected breach.
    """
    limits = EngineeringLimits(
        u_allowable_mv=25.0,
        tolerance_mv=50.0,
        drift_threshold_mv=0.50,
        s_allowable_mv=15.0
    )
    
    # With 10 sessions: b = 1.10 mV/session, p = 1.3e-06
    res = evaluate_decision_rules(
        expanded_uncertainty_mv=10.55,
        absolute_error_mv=21.0,
        sample_std_dev_mv=9.944,
        limits=limits,
        drift_slope_mv_per_session=1.10,
        drift_p_value=1.3e-6,
        has_drift_history=True,
        projected_breach_session=28.0
    )
    
    assert res.headline_status == "ATTENTION REQUIRED"
    assert res.primary_triggered_rule == "R3"
    assert "POSSIBLE DRIFT" in res.primary_status_label
    assert "SIGNIFICANT UPWARD DRIFT" in res.drift_status_badge
    assert "Shorten" in res.recommended_action
    assert "28" in res.detailed_recommendation


def test_rule_r1_high_uncertainty():
    limits = EngineeringLimits(u_allowable_mv=25.0, tolerance_mv=50.0)
    res = evaluate_decision_rules(
        expanded_uncertainty_mv=30.0,  # > 25.0
        absolute_error_mv=10.0,
        sample_std_dev_mv=5.0,
        limits=limits
    )
    assert res.headline_status == "ATTENTION REQUIRED"
    assert res.primary_triggered_rule == "R1"
    assert res.primary_status_label == "HIGH UNCERTAINTY"


def test_rule_r2_calibration_required():
    limits = EngineeringLimits(u_allowable_mv=25.0, tolerance_mv=50.0)
    res = evaluate_decision_rules(
        expanded_uncertainty_mv=10.0,
        absolute_error_mv=45.0,  # |E| + U = 55.0 > 50.0
        sample_std_dev_mv=5.0,
        limits=limits
    )
    assert res.headline_status == "CALIBRATION REQUIRED"
    assert res.primary_triggered_rule == "R2"
    assert res.calibration_status_badge == "FAIL"


def test_rule_r4_repeatability_concern():
    limits = EngineeringLimits(u_allowable_mv=25.0, tolerance_mv=50.0, s_allowable_mv=15.0)
    res = evaluate_decision_rules(
        expanded_uncertainty_mv=10.0,
        absolute_error_mv=10.0,
        sample_std_dev_mv=20.0,  # > 15.0
        limits=limits
    )
    assert res.headline_status == "ATTENTION REQUIRED"
    assert res.primary_triggered_rule == "R4"
    assert res.primary_status_label == "REPEATABILITY CONCERN"
