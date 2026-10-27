"""
Tests for IMUCA Data Model, Schema Validation, and SI Conversions.
"""

import pytest
import numpy as np
import pandas as pd
from src.imuca.schema import (
    MeasurementRecord,
    validate_schema,
    convert_voltage,
    convert_current,
    convert_temperature
)


def test_si_unit_conversions():
    # Voltage conversions
    assert pytest.approx(convert_voltage(5000.0, "mV", "V")) == 5.0
    assert pytest.approx(convert_voltage(3.3, "V", "mV")) == 3300.0
    assert pytest.approx(convert_voltage(1.2, "V", "uV")) == 1.2e6
    assert pytest.approx(convert_voltage(1000.0, "V", "kV")) == 1.0

    # Current conversions
    assert pytest.approx(convert_current(250.0, "mA", "A")) == 0.25
    assert pytest.approx(convert_current(1.5, "A", "mA")) == 1500.0
    assert pytest.approx(convert_current(100.0, "uA", "mA")) == 0.1

    # Temperature conversions
    assert pytest.approx(convert_temperature(0.0, "degC", "K")) == 273.15
    assert pytest.approx(convert_temperature(100.0, "degC", "K")) == 373.15
    assert pytest.approx(convert_temperature(298.15, "K", "degC")) == 25.0
    assert pytest.approx(convert_temperature(32.0, "degF", "degC")) == 0.0
    assert pytest.approx(convert_temperature(212.0, "degF", "degC")) == 100.0


def test_measurement_record_immutable():
    rec = MeasurementRecord(
        experiment_id="EXP001",
        device_id="DEV_INA219",
        timestamp_utc="2026-10-25T10:00:00Z",
        sequence_number=1,
        elapsed_ms=0.0,
        voltage_V=5.01,
        current_mA=120.5,
        temperature_C=24.5
    )
    assert rec.voltage_V == 5.01
    assert rec.sequence_number == 1
    # Check frozen dataclass immutability
    with pytest.raises(Exception):
        rec.voltage_V = 5.02  # type: ignore


def test_schema_valid_dataframe():
    df = pd.DataFrame({
        "experiment_id": ["EXP1", "EXP1"],
        "device_id": ["D1", "D1"],
        "timestamp_utc": ["2026-10-25T10:00:00Z", "2026-10-25T10:00:01Z"],
        "sequence_number": [1, 2],
        "elapsed_ms": [0.0, 1000.0],
        "voltage_V": [5.01, 5.02],
        "current_mA": [100.0, 102.5],
        "temperature_C": [24.0, 24.1],
        "status": ["OK", "OK"]
    })
    result = validate_schema(df)
    assert result.is_valid
    assert result.valid_record_count == 2
    assert result.error_record_count == 0
    assert result.flagged_dataframe["quality_flags"].iloc[0] == "CLEAN"


def test_schema_duplicate_and_out_of_order_sequence():
    df = pd.DataFrame({
        "sequence_number": [1, 2, 2, 1],  # duplicate 2, out of order 1
        "elapsed_ms": [0.0, 1000.0, 2000.0, 3000.0],
        "voltage_V": [5.0, 5.1, 5.2, 5.3]
    })
    result = validate_schema(df)
    assert not result.is_valid
    assert result.error_record_count >= 2
    codes = [d.issue_code for d in result.diagnostics]
    assert "DUPLICATE" in codes
    assert "MONOTONICITY_VIOLATION" in codes


def test_schema_non_finite_and_out_of_range():
    df = pd.DataFrame({
        "sequence_number": [1, 2, 3],
        "elapsed_ms": [0.0, 1000.0, 2000.0],
        "voltage_V": [5.0, np.nan, 999.0],  # NaN allowed with warning; 999 out of range
        "current_mA": [10.0, 20.0, np.inf]  # Inf must fail
    })
    result = validate_schema(df)
    assert not result.is_valid
    codes = [d.issue_code for d in result.diagnostics]
    assert "OUT_OF_RANGE" in codes
    assert "NON_FINITE" in codes
