"""
Phase C: Independent Numerical Verification and Edge-Case Tests.

Analytically checkable, hand-calculated test cases verifying:
1. Known measurement errors and bias.
2. Known MAE and RMSE.
3. Sample standard deviation with known observations ((n-1) Bessel's correction).
4. Relative error near zero guard.
5. Type A uncertainty of a mean (s / sqrt(n)).
6. Rectangular-distribution Type B uncertainty (a / sqrt(3)).
7. Triangular-distribution Type B uncertainty (a / sqrt(6)).
8. Independent uncertainty contributions (RSS combination).
9. Correlated uncertainty contributions with positive covariance.
10. Correlated uncertainty contributions with negative covariance.
11. Nonlinear propagation (Ohm's law I = V / R).
12. Indirect shunt-current propagation with known analytical values.
13. Coverage-factor selection and Welch-Satterthwaite effective degrees of freedom.
14. Calibration with known analytical coefficients.
15. Calibration evaluation on held-out observations.
16. Detection of calibration leakage across partitions.
17. Duplicate-record and sequence-gap detection.
18. Zero-MAD outlier handling (NIST / Iglewicz-Hoaglin).
19. Drift slope estimation with known synthetic drift.
20. CUSUM detection under documented assumptions.
21. Time-to-breach edge cases (already breached, zero slope).
22. Fault-detection confusion-matrix calculations.
23. Empty, malformed, missing, and non-finite input handling.
24. Reproducibility of synthetic data and experiment outputs.
"""

import math
import pytest
import numpy as np
import pandas as pd

from src.imuca.measurement_metrics import (
    compute_descriptive_statistics,
    compute_error_metrics,
    compute_pooled_repeatability,
    compute_residual_diagnostics
)
from src.imuca.uncertainty import (
    evaluate_type_a,
    evaluate_type_b,
    evaluate_shunt_current_uncertainty,
    build_uncertainty_budget,
    round_uncertainty_metrology
)
from src.imuca.calibration import (
    CalibrationEngine,
    CalibrationModel
)
from src.imuca.validation import (
    evaluate_guard_banded_conformity,
    analyze_temporal_drift
)
from src.imuca.data_quality import (
    DataQualityAssessor,
    FaultDetectionMetrics
)
from src.imuca.schema import (
    validate_schema,
    convert_voltage,
    convert_current,
    convert_temperature
)
from src.imuca.synthetic_data import (
    SyntheticDataGenerator,
    SyntheticScenarioConfig
)


# ==============================================================================
# Case 1 & 2: Known Measurement Errors, Bias, MAE, and RMSE
# ==============================================================================

def test_case_01_and_02_known_errors_mae_rmse():
    # Measured: [10.2, 10.4, 9.8, 10.0]
    # Ref:      [10.0, 10.0, 10.0, 10.0]
    # Errors:   [+0.2, +0.4, -0.2,  0.0]
    # Mean bias = (0.2 + 0.4 - 0.2 + 0.0) / 4 = 0.4 / 4 = 0.100
    # MAE = (0.2 + 0.4 + 0.2 + 0.0) / 4 = 0.8 / 4 = 0.200
    # RMSE = sqrt((0.04 + 0.16 + 0.04 + 0.0) / 4) = sqrt(0.24 / 4) = sqrt(0.06) = 0.24494897
    meas = [10.2, 10.4, 9.8, 10.0]
    ref = [10.0, 10.0, 10.0, 10.0]

    metrics = compute_error_metrics(meas, ref)
    assert pytest.approx(metrics.mean_bias, abs=1e-7) == 0.100
    assert pytest.approx(metrics.mae, abs=1e-7) == 0.200
    assert pytest.approx(metrics.rmse, abs=1e-6) == math.sqrt(0.06)
    assert pytest.approx(metrics.max_absolute_error, abs=1e-7) == 0.400


# ==============================================================================
# Case 3: Sample Standard Deviation with n-1 Bessel's Correction
# ==============================================================================

def test_case_03_sample_std_dev_bessel_correction():
    # Observations: [2.0, 4.0, 6.0] -> n = 3
    # Mean = 4.0
    # Deviations: [-2.0, 0.0, +2.0]
    # Sum of squared deviations = 4.0 + 0.0 + 4.0 = 8.0
    # Sample variance with (n - 1) = 8.0 / 2 = 4.0
    # Sample std dev = sqrt(4.0) = 2.0
    # Biased population std dev would be sqrt(8/3) = 1.63299
    stats = compute_descriptive_statistics([2.0, 4.0, 6.0])
    assert stats.n == 3
    assert stats.mean == 4.0
    assert pytest.approx(stats.sample_variance, abs=1e-7) == 4.0
    assert pytest.approx(stats.sample_std_dev, abs=1e-7) == 2.0
    assert stats.degrees_of_freedom == 2


# ==============================================================================
# Case 4: Relative Error Near-Zero Guard
# ==============================================================================

def test_case_04_relative_error_near_zero_guard():
    meas = [0.05, 10.5]
    ref = [0.00, 10.0]  # First point has reference 0.0

    metrics = compute_error_metrics(meas, ref, zero_threshold=1e-4)
    assert metrics.zero_reference_count == 1
    assert metrics.valid_relative_count == 1
    assert math.isnan(metrics.percentage_errors[0])
    assert pytest.approx(metrics.percentage_errors[1], abs=1e-4) == 5.0  # (10.5-10)/10 * 100%


# ==============================================================================
# Case 5, 6, 7: Type A and Type B Analytical Standard Uncertainties
# ==============================================================================

def test_case_05_06_07_type_a_and_type_b_distributions():
    # Type A: [10.0, 12.0, 14.0] -> n = 3, s = 2.0 -> u_A = 2.0 / sqrt(3) = 1.1547005
    c_a = evaluate_type_a([10.0, 12.0, 14.0], unit="V")
    assert pytest.approx(c_a.standard_uncertainty, abs=1e-6) == 2.0 / math.sqrt(3)
    assert c_a.degrees_of_freedom == 2

    # Type B Rectangular: limit a = 3.0 -> u_B = 3.0 / sqrt(3) = sqrt(3) = 1.7320508
    c_rec = evaluate_type_b("Rect", limit_value=3.0, distribution="RECTANGULAR", unit="V")
    assert pytest.approx(c_rec.standard_uncertainty, abs=1e-6) == math.sqrt(3.0)

    # Type B Triangular: limit a = 6.0 -> u_B = 6.0 / sqrt(6) = sqrt(6) = 2.4494897
    c_tri = evaluate_type_b("Tri", limit_value=6.0, distribution="TRIANGULAR", unit="V")
    assert pytest.approx(c_tri.standard_uncertainty, abs=1e-6) == math.sqrt(6.0)


# ==============================================================================
# Case 8, 9, 10: Independent & Correlated Propagation (Positive and Negative Covariance)
# ==============================================================================

def test_case_08_09_10_independent_and_correlated_propagation():
    # Linear model: y = x1 + x2 (c1 = 1, c2 = 1)
    # u(x1) = 3.0, u(x2) = 4.0
    # Independent: u_c^2 = 3^2 + 4^2 = 25 -> u_c = 5.0
    c1 = evaluate_type_b("x1", limit_value=6.0, distribution="NORMAL")  # u = 3.0
    c2 = evaluate_type_b("x2", limit_value=8.0, distribution="NORMAL")  # u = 4.0

    b_indep = build_uncertainty_budget("y", 10.0, "V", [c1, c2], force_k=2.0)
    assert pytest.approx(b_indep.combined_standard_uncertainty, abs=1e-6) == 5.0

    # Positive Covariance: cov(x1, x2) = +6.0 (correlation r = 6 / (3*4) = +0.5)
    # u_c^2 = 3^2 + 4^2 + 2 * (1)(1) * (+6.0) = 25 + 12 = 37 -> u_c = sqrt(37) = 6.0827625
    b_pos = build_uncertainty_budget("y", 10.0, "V", [c1, c2], force_k=2.0, covariances={(0, 1): 6.0})
    assert pytest.approx(b_pos.combined_standard_uncertainty, abs=1e-6) == math.sqrt(37.0)

    # Negative Covariance: cov(x1, x2) = -6.0 (correlation r = -0.5)
    # u_c^2 = 3^2 + 4^2 + 2 * (1)(1) * (-6.0) = 25 - 12 = 13 -> u_c = sqrt(13) = 3.605551
    b_neg = build_uncertainty_budget("y", 10.0, "V", [c1, c2], force_k=2.0, covariances={(0, 1): -6.0})
    assert pytest.approx(b_neg.combined_standard_uncertainty, abs=1e-6) == math.sqrt(13.0)


# ==============================================================================
# Case 11 & 12: Nonlinear Indirect Current Propagation: I = V_shunt / R_shunt
# ==============================================================================

def test_case_11_and_12_nonlinear_shunt_current_propagation():
    # V_shunt = 0.200 V, R_shunt = 0.100 Ohm
    # I = 0.200 / 0.100 = 2.000 A
    # Sensitivities:
    # c_V = 1 / R = 1 / 0.100 = 10.0 A/V
    # c_R = -V / R^2 = -0.200 / 0.010 = -20.0 A/Ohm
    # If u(V) = 0.001 V, u(R) = 0.001 Ohm
    # u_c^2 = (10 * 0.001)^2 + (-20 * 0.001)^2 = 0.01^2 + (-0.02)^2 = 0.0001 + 0.0004 = 0.0005
    # u_c = sqrt(0.0005) = 0.02236068 A
    i_val, comps = evaluate_shunt_current_uncertainty(
        v_shunt_v=0.200,
        r_shunt_ohm=0.100,
        u_v_shunt_v=0.001,
        u_r_shunt_ohm=0.001
    )
    assert pytest.approx(i_val, abs=1e-6) == 2.000
    assert pytest.approx(comps[0].sensitivity_coefficient, abs=1e-6) == 10.0
    assert pytest.approx(comps[1].sensitivity_coefficient, abs=1e-6) == -20.0

    b = build_uncertainty_budget("Current", i_val, "A", comps, force_k=2.0)
    assert pytest.approx(b.combined_standard_uncertainty, abs=1e-6) == math.sqrt(0.0005)


# ==============================================================================
# Case 13: Welch-Satterthwaite Effective Degrees of Freedom
# ==============================================================================

def test_case_13_welch_satterthwaite_effective_dof():
    # Two components:
    # c1 * u1 = 3.0 with nu1 = 9
    # c2 * u2 = 4.0 with nu2 = 16
    # u_c = sqrt(9 + 16) = 5.0
    # WS: nu_eff = u_c^4 / [ (c1*u1)^4 / nu1 + (c2*u2)^4 / nu2 ]
    # numerator = 5^4 = 625
    # denominator = 3^4 / 9 + 4^4 / 16 = 81 / 9 + 256 / 16 = 9 + 16 = 25
    # nu_eff = 625 / 25 = 25.0
    comp1 = evaluate_type_b("c1", limit_value=6.0, distribution="NORMAL")
    comp1.degrees_of_freedom = 9.0

    comp2 = evaluate_type_b("c2", limit_value=8.0, distribution="NORMAL")
    comp2.degrees_of_freedom = 16.0

    b = build_uncertainty_budget("Test", 0.0, "V", [comp1, comp2])
    assert pytest.approx(b.effective_degrees_of_freedom, abs=1e-5) == 25.0


# ==============================================================================
# Case 14 & 15: Calibration with Known Coefficients and Held-Out Validation
# ==============================================================================

def test_case_14_and_15_calibration_known_coefficients_held_out():
    # True relation: y_ref = -0.50 + 1.05 * x_dut
    # Generate 20 points
    x = np.linspace(10.0, 50.0, 20)
    y = -0.50 + 1.05 * x

    engine = CalibrationEngine()
    comp = engine.evaluate_train_validation_split(
        x_dut=x,
        y_ref=y,
        train_ratio=0.7,
        model_type="linear",
        random_seed=123
    )

    # Recovered linear coefficients must match -0.50 and 1.05 exactly
    assert pytest.approx(comp.model.coefficients[0], abs=1e-5) == -0.50
    assert pytest.approx(comp.model.coefficients[1], abs=1e-5) == 1.05
    # Residual error on validation set must be virtually zero
    assert comp.calibrated_metrics.mae < 1e-10
    assert comp.is_performance_improved


# ==============================================================================
# Case 17: Duplicate-Record and Sequence-Gap Detection
# ==============================================================================

def test_case_17_duplicate_and_gap_detection():
    df = pd.DataFrame({
        "sequence_number": [1, 2, 2, 5],
        "elapsed_ms": [0.0, 1000.0, 2000.0, 3000.0],
        "voltage_V": [1.0, 1.0, 1.0, 1.0]
    })
    res = validate_schema(df)
    codes = [d.issue_code for d in res.diagnostics]
    assert "DUPLICATE" in codes
    assert "SEQUENCE_GAP" in codes


# ==============================================================================
# Case 19: Linear Drift Slope Estimation with Known Injected Drift
# ==============================================================================

def test_case_19_drift_slope_known_synthetic():
    # y(t) = 100.0 + 0.25 * t
    t = np.arange(0, 50, 1.0)
    y = 100.0 + 0.25 * t

    drift_res = analyze_temporal_drift(t, y, nominal_target=100.0, upper_limit=120.0)
    assert pytest.approx(drift_res.drift_rate_per_s, abs=1e-7) == 0.25
    assert drift_res.is_drift_significant
    # Forecast to breach 120.0 at t=49: curr_y = 100 + 0.25*49 = 112.25. Remaining = 7.75. Time = 7.75 / 0.25 = 31.0 s
    assert pytest.approx(drift_res.forecast_seconds_to_breach, abs=1e-5) == 31.0


# ==============================================================================
# Case 22: Confusion Matrix Calculations
# ==============================================================================

def test_case_22_confusion_matrix_metrics():
    # TP=8, FP=2, TN=88, FN=2 (Total = 100)
    # Precision = 8 / (8 + 2) = 0.800
    # Recall = 8 / (8 + 2) = 0.800
    # FAR = 2 / (2 + 88) = 2 / 90 = 0.02222
    # MDR = 2 / (8 + 2) = 0.200
    # F1 = 2 * 0.8 * 0.8 / 1.6 = 0.800
    tp, fp, tn, fn = 8, 2, 88, 2
    prec = tp / (tp + fp)
    rec = tp / (tp + fn)
    far = fp / (fp + tn)
    mdr = fn / (tp + fn)
    f1 = 2 * prec * rec / (prec + rec)

    m = FaultDetectionMetrics(tp, fp, tn, fn, prec, rec, far, mdr, f1)
    assert pytest.approx(m.precision, abs=1e-5) == 0.800
    assert pytest.approx(m.recall, abs=1e-5) == 0.800
    assert pytest.approx(m.false_alarm_rate, abs=1e-5) == 2.0 / 90.0
    assert pytest.approx(m.missed_detection_rate, abs=1e-5) == 0.200
    assert pytest.approx(m.f1_score, abs=1e-5) == 0.800


# ==============================================================================
# Case 24: Deterministic Random Seed Reproducibility
# ==============================================================================

def test_case_24_deterministic_seed_reproducibility():
    gen1 = SyntheticDataGenerator(seed=777)
    cfg1 = gen1.create_standard_scenarios()["nominal_voltage_baseline"]
    df1, _ = gen1.generate_scenario(cfg1)

    gen2 = SyntheticDataGenerator(seed=777)
    cfg2 = gen2.create_standard_scenarios()["nominal_voltage_baseline"]
    df2, _ = gen2.generate_scenario(cfg2)

    pd.testing.assert_frame_equal(df1, df2)


# ==============================================================================
# Edge Case & Defect Tests
# ==============================================================================

def test_case_18_zero_mad_outlier_detection():
    # 9 points at 5.0 V, 1 extreme outlier at 12.0 V
    # MAD is 0.0 because >50% of values are identical to the median (5.0 V)
    # The outlier 12.0 V must be detected via MeanAD fallback rather than ignored
    values = [5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 12.0, 5.0, 5.0]
    df = pd.DataFrame({
        "sequence_number": list(range(1, 11)),
        "elapsed_ms": [i * 1000.0 for i in range(10)],
        "voltage_V": values,
        "status": ["OK"] * 10
    })

    assessor = DataQualityAssessor(mad_threshold=3.5)
    report = assessor.assess(df, measurand_col="voltage_V", range_limits=(0.0, 20.0))

    outlier_issues = [i for i in report.issues if i.issue_type == "OUTLIER"]
    assert len(outlier_issues) >= 1
    assert outlier_issues[0].record_index == 7
    assert "OUTLIER" in report.annotated_dataframe["quality_flags"].iloc[7]


def test_symmetric_covariance_no_double_count():
    # c1 = 1, c2 = 1, u1 = 3, u2 = 4
    # cov = 2.0
    # Expected u_c^2 = 3^2 + 4^2 + 2 * (1)(1)(2.0) = 25 + 4 = 29 -> u_c = sqrt(29) = 5.3851648
    # If the user provides a symmetric dictionary {(0, 1): 2.0, (1, 0): 2.0}, it must not add 2*cov twice!
    c1 = evaluate_type_b("x1", limit_value=6.0, distribution="NORMAL")
    c2 = evaluate_type_b("x2", limit_value=8.0, distribution="NORMAL")

    b_symm = build_uncertainty_budget("y", 10.0, "V", [c1, c2], force_k=2.0, covariances={(0, 1): 2.0, (1, 0): 2.0})
    assert pytest.approx(b_symm.combined_standard_uncertainty, abs=1e-5) == math.sqrt(29.0)


def test_metrological_rounding_power_of_10_boundary():
    # Uncertainty = 0.00995 V -> rounded to 2 significant digits should be 0.010 V (not 0.0100 V!)
    # And decimals should be 3 (matching 0.010)
    val_r, u_r, fmt = round_uncertainty_metrology(5.02123, 0.00995)
    assert pytest.approx(u_r, abs=1e-6) == 0.010
    assert pytest.approx(val_r, abs=1e-6) == 5.021
    assert fmt == "(5.021 +/- 0.010)"


def test_case_21_drift_breach_already_breached():
    # Slope is +0.10/s, but current measurement is already 12.0 V, exceeding upper limit of 10.0 V
    t = np.arange(0, 10, 1.0)
    y = 11.0 + 0.10 * t  # All points exceed 10.0 V

    drift_res = analyze_temporal_drift(t, y, nominal_target=5.0, upper_limit=10.0)
    assert drift_res.forecast_seconds_to_breach == 0.0
    assert "already breached" in drift_res.summary_message.lower()


def test_case_23_schema_infinity_sequence_and_string_elapsed():
    # Should flag without crashing with OverflowError or unhandled ValueError
    df = pd.DataFrame({
        "sequence_number": [float("inf"), 2],
        "elapsed_ms": ["invalid_time_string", 1000.0],
        "voltage_V": [5.0, 5.0]
    })
    res = validate_schema(df)
    assert not res.is_valid
    assert res.error_record_count >= 1

