"""
Unit Tests for Data Ingestion, Schema Detection, and Validation (Algorithm 1a).
"""

import os
import pytest
import numpy as np
import pandas as pd
from src.loader import load_csv, detect_measurement_columns, detect_drift_columns
from src.validator import validate_dataset


def test_valid_demo_dataset():
    path = os.path.join("data", "demo_measurements.csv")
    df = load_csv(path)
    res = validate_dataset(df, min_val=0.0, max_val=20.0)
    
    assert res.is_valid
    assert res.status in ["VALID", "WARNING"]
    assert res.valid_rows_count == 10
    assert res.skipped_rows_count == 0


def test_invalid_data_flagging_and_handling():
    path = os.path.join("data", "sample_invalid_data.csv")
    df = load_csv(path)
    res = validate_dataset(df, columns_to_check=["DUT_V"], min_val=0.0, max_val=20.0)
    
    # Must skip non-numeric ('INVALID_VOLTAGE'), missing, and out-of-range (<0 or >20)
    assert res.skipped_rows_count > 0
    # Must retain valid rows
    assert res.valid_rows_count > 0
    
    # Extreme outlier (9.99 V at 5.0 V) must be flagged in issues as OUTLIER without being deleted from valid_df
    outlier_issues = [i for i in res.issues if i.issue_type == "OUTLIER"]
    assert len(outlier_issues) >= 1
    assert any(i.severity == "WARNING" for i in outlier_issues)


def test_column_detection():
    df_meas = pd.DataFrame({
        "Reference_V": [1.0, 2.0],
        "DUT_V": [1.01, 2.01],
        "Repeat_1_V": [1.01, 2.01],
        "Repeat_2_V": [1.02, 2.02]
    })
    ref, dut, rpts = detect_measurement_columns(df_meas)
    assert ref == "Reference_V"
    assert dut == "DUT_V"
    assert len(rpts) == 2


# ==============================================================================
# Tests for new modular package: src.imuca.validation
# ==============================================================================

from src.imuca.validation import (
    evaluate_guard_banded_conformity,
    analyze_temporal_drift
)


def test_imuca_guard_banded_conformity_3_bands():
    # Nominal reference: 10.0 V, 1% tolerance -> [9.90, 10.10] V, T = 0.10 V
    # Case 1: PASS (measured = 10.01 V, U = 0.02 V) -> [9.99, 10.03] inside [9.92, 10.08]
    res_pass = evaluate_guard_banded_conformity(
        measured_value=10.01,
        reference_value=10.00,
        expanded_uncertainty=0.02,
        tolerance_percent=1.0
    )
    assert res_pass.simple_conformity == "PASS"
    assert res_pass.guard_banded_conformity == "PASS"

    # Case 2: CONDITIONAL / MARGINAL (measured = 10.09 V, U = 0.02 V) -> measured is inside [9.90, 10.10], but 10.09 + 0.02 = 10.11 exceeds 10.10
    res_cond = evaluate_guard_banded_conformity(
        measured_value=10.09,
        reference_value=10.00,
        expanded_uncertainty=0.02,
        tolerance_percent=1.0
    )
    assert res_cond.simple_conformity == "PASS"
    assert res_cond.guard_banded_conformity == "CONDITIONAL"

    # Case 3: FAIL (measured = 10.15 V, outside tolerance)
    res_fail = evaluate_guard_banded_conformity(
        measured_value=10.15,
        reference_value=10.00,
        expanded_uncertainty=0.02,
        tolerance_percent=1.0
    )
    assert res_fail.simple_conformity == "FAIL"
    assert res_fail.guard_banded_conformity == "FAIL"


def test_imuca_drift_analysis_and_breach_forecast():
    # Linear drift: y(t) = 5.0 + 0.01 * t + noise
    t_vals = np.arange(0, 100, 1.0)
    y_vals = 5.0 + 0.01 * t_vals + np.random.default_rng(42).normal(0, 0.005, size=len(t_vals))

    # Upper limit = 6.5 V. At t=99, y ~ 5.99 V. Remaining to breach = 6.5 - 5.99 = 0.51 V -> breach at ~51 seconds
    res = analyze_temporal_drift(
        timestamps_s=t_vals,
        measurements=y_vals,
        nominal_target=5.0,
        upper_limit=6.5
    )

    assert res.is_drift_significant
    assert pytest.approx(res.drift_rate_per_s, rel=0.05) == 0.01
    assert res.forecast_seconds_to_breach is not None
    assert 40.0 < res.forecast_seconds_to_breach < 60.0

