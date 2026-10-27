"""
Standalone Test Suite for IMUCA.
Executes all test assertions directly without external test runner dependencies.
"""

import sys
import traceback

def run_all():
    passed = 0
    failed = 0
    
    # 1. Statistics tests
    print("=== Testing Statistics Module ===")
    from tests.test_statistics import (
        test_descriptive_statistics_golden_values,
        test_statistics_single_observation,
        test_statistics_empty_dataset
    )
    for test_fn in [test_descriptive_statistics_golden_values, test_statistics_single_observation, test_statistics_empty_dataset]:
        try:
            test_fn()
            print(f"  [PASS] {test_fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {test_fn.__name__}: {e}")
            traceback.print_exc()
            failed += 1
            
    # 2. Uncertainty tests
    print("\n=== Testing Uncertainty Module ===")
    from tests.test_uncertainty import (
        test_type_a_uncertainty,
        test_type_b_uncertainty,
        test_uncertainty_budget_and_combination,
        test_metrological_rounding
    )
    for test_fn in [test_type_a_uncertainty, test_type_b_uncertainty, test_uncertainty_budget_and_combination, test_metrological_rounding]:
        try:
            test_fn()
            print(f"  [PASS] {test_fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {test_fn.__name__}: {e}")
            traceback.print_exc()
            failed += 1

    # 3. Calibration tests
    print("\n=== Testing Calibration Module ===")
    from tests.test_calibration import (
        test_calibration_sweep_regression,
        test_residual_analysis,
        test_single_point_guard_banded_conformity
    )
    for test_fn in [test_calibration_sweep_regression, test_residual_analysis, test_single_point_guard_banded_conformity]:
        try:
            test_fn()
            print(f"  [PASS] {test_fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {test_fn.__name__}: {e}")
            traceback.print_exc()
            failed += 1

    # 4. Drift tests
    print("\n=== Testing Drift Module ===")
    from tests.test_drift import (
        test_within_run_trend,
        test_between_session_drift
    )
    for test_fn in [test_within_run_trend, test_between_session_drift]:
        try:
            test_fn()
            print(f"  [PASS] {test_fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {test_fn.__name__}: {e}")
            traceback.print_exc()
            failed += 1

    # 5. Decision Engine tests
    print("\n=== Testing Decision Engine Module ===")
    from tests.test_decision_engine import (
        test_demo_a_single_session_decision,
        test_demo_b_with_drift_history_decision,
        test_rule_r1_high_uncertainty,
        test_rule_r2_calibration_required,
        test_rule_r4_repeatability_concern
    )
    for test_fn in [
        test_demo_a_single_session_decision,
        test_demo_b_with_drift_history_decision,
        test_rule_r1_high_uncertainty,
        test_rule_r2_calibration_required,
        test_rule_r4_repeatability_concern
    ]:
        try:
            test_fn()
            print(f"  [PASS] {test_fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {test_fn.__name__}: {e}")
            traceback.print_exc()
            failed += 1

    # 6. Validation tests
    print("\n=== Testing Validation Module ===")
    from tests.test_validation import (
        test_valid_demo_dataset,
        test_invalid_data_flagging_and_handling,
        test_column_detection
    )
    for test_fn in [
        test_valid_demo_dataset,
        test_invalid_data_flagging_and_handling,
        test_column_detection
    ]:
        try:
            test_fn()
            print(f"  [PASS] {test_fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {test_fn.__name__}: {e}")
            traceback.print_exc()
            failed += 1

    print("\n==========================================")
    print(f"Total Tests Executed: {passed + failed}")
    print(f"PASSED: {passed}")
    print(f"FAILED: {failed}")
    print("==========================================")
    
    if failed > 0:
        sys.exit(1)
    else:
        print("All test cases passed successfully matching golden reference values!")
        sys.exit(0)

if __name__ == "__main__":
    run_all()
