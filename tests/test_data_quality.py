"""
Unit Tests for IMUCA Data Quality and Integrity Assessment Module.
"""

import pytest
import numpy as np
import pandas as pd
from src.imuca.data_quality import DataQualityAssessor
from src.imuca.synthetic_data import SyntheticDataGenerator, SyntheticScenarioConfig


def test_mad_outlier_detection_preserves_data():
    # Clean nominal observations with one severe outlier (row 5)
    values = [5.01, 5.02, 5.01, 5.02, 5.03, 9.85, 5.02, 5.01, 5.02, 5.01]
    df = pd.DataFrame({
        "sequence_number": list(range(1, 11)),
        "elapsed_ms": [i * 1000.0 for i in range(10)],
        "voltage_V": values,
        "status": ["OK"] * 10
    })

    assessor = DataQualityAssessor(mad_threshold=3.5)
    report = assessor.assess(df, measurand_col="voltage_V", range_limits=(0.0, 10.0))

    # Raw rows must not be deleted
    assert len(report.annotated_dataframe) == 10
    assert report.annotated_dataframe["voltage_V"].iloc[5] == 9.85

    # Outlier at row 5 must be flagged
    outlier_issues = [i for i in report.issues if i.issue_type == "OUTLIER"]
    assert len(outlier_issues) >= 1
    assert outlier_issues[0].record_index == 5
    assert "OUTLIER_MAD" in report.annotated_dataframe["quality_flags"].iloc[5]


def test_sequence_integrity_and_duplicate_detection():
    df = pd.DataFrame({
        "sequence_number": [1, 2, 2, 4, 3],  # duplicate at 2, gap after 2, out of order at 4->3
        "elapsed_ms": [0.0, 1000.0, 2000.0, 3000.0, 4000.0],
        "voltage_V": [5.0, 5.0, 5.0, 5.0, 5.0],
        "status": ["OK"] * 5
    })

    assessor = DataQualityAssessor()
    report = assessor.assess(df, measurand_col="voltage_V", range_limits=(0.0, 10.0))

    types = [i.issue_type for i in report.issues]
    assert "DUPLICATE_SEQ" in types
    assert "SEQUENCE_GAP" in types
    assert "OUT_OF_ORDER" in types


def test_fault_detection_confusion_matrix_against_injected_faults():
    # Generate reproducible fault stress scenario
    gen = SyntheticDataGenerator(seed=104)
    scenarios = gen.create_standard_scenarios()
    df, meta = gen.generate_scenario(scenarios["fault_stress_scenario"])

    assessor = DataQualityAssessor()
    report = assessor.assess(
        df,
        measurand_col="voltage_V",
        range_limits=(0.0, 15.0),
        max_rate_of_change=1.0,
        ground_truth_fault_col="is_injected_fault"
    )

    metrics = report.detection_metrics
    assert metrics is not None
    # We should have high recall and precision for known injected anomalies
    assert metrics.recall >= 0.80
    assert metrics.precision >= 0.75
    assert metrics.missed_detection_rate <= 0.20
    assert metrics.true_positives >= 8
