"""
Unit Tests for Drift and Within-Run Trend Analysis against Golden Reference Values.
"""

import pytest
import numpy as np
from src.drift import analyze_within_run_trend, evaluate_drift_history


# Synthetic repeat readings at 5.000 V (Section 14.1)
DEMO_READINGS = [5.02, 5.01, 5.03, 5.02, 5.04, 5.01, 5.02, 5.03, 5.02, 5.01]

# Synthetic 10-session calibration history (Table 14.1)
SESSIONS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
ERRORS_MV = [21.0, 22.0, 21.0, 24.0, 25.0, 26.0, 26.0, 28.0, 29.0, 31.0]


def test_within_run_trend():
    res = analyze_within_run_trend(DEMO_READINGS)
    assert res.is_assessed
    # Slope: -0.303 mV/reading
    assert pytest.approx(res.slope_mv_per_reading, rel=1e-2) == -0.303
    # Standard error: 1.156 mV/reading
    assert pytest.approx(res.std_err_slope, rel=1e-2) == 1.156
    # p = 0.80 -> not significant
    assert pytest.approx(res.p_value, abs=0.02) == 0.80
    assert not res.is_significant
    assert res.verdict == "NO SIGNIFICANT TREND"


def test_between_session_drift():
    drift = evaluate_drift_history(
        sessions=SESSIONS,
        mean_errors_mv=ERRORS_MV,
        drift_threshold_mv_per_session=0.50,
        tolerance_mv=50.0
    )
    assert drift.is_assessed
    # Drift slope: +1.10 mV/session
    assert pytest.approx(drift.slope_b, rel=1e-2) == 1.10
    # Standard error of slope: 0.085 mV/session
    assert pytest.approx(drift.std_err_b, rel=1e-2) == 0.085
    # R^2: 0.954
    assert pytest.approx(drift.r_squared, abs=0.01) == 0.954
    # p-value: approx 1.3e-06 (< 0.001)
    assert drift.p_value < 1e-5
    
    # Significant upward drift detected
    assert drift.is_drift_significant
    assert drift.rule_status == "POSSIBLE DRIFT"
    assert "SIGNIFICANT UPWARD DRIFT" in drift.drift_status
    
    # Projected tolerance breach: session 28
    assert pytest.approx(drift.projected_breach_session, abs=1.0) == 28.0
