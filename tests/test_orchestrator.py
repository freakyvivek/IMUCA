"""
Unit and integration tests for IMUCA Metrology Orchestrator (src/imuca/orchestrator.py).

Verifies:
- End-to-end execution on synthetic multi-channel DataFrame.
- Correct measurand handling (voltage_V, current_mA, temperature_C).
- Metrological budget creation with Type A and Type B components.
- Graceful operation when reference values are omitted (single-sensor mode).
- Non-destructive integrity filtering.
- Alarm episode lifecycle aggregation.
"""

import pytest
import numpy as np
import pandas as pd

from src.imuca.orchestrator import (
    MetrologyOrchestrator,
    PipelineConfig,
    PipelineResult
)
from src.imuca.hardware_adapter import SimulationReplaySource


@pytest.fixture
def synthetic_multichannel_df():
    """Create deterministic multi-channel dataset with nominal values and one spike."""
    n = 100
    t = np.arange(n, dtype=float)
    # 5.0 V nominal with 2 mV noise + spike at index 50
    v = 5.0 + 0.002 * np.sin(t)
    v[50] = 5.050  # 50 mV spike

    # 1000 mA nominal with 1 mA noise
    i = 1000.0 + 0.5 * np.cos(t)

    # 25.0 °C nominal
    temp = 25.0 + 0.1 * np.sin(0.1 * t)

    return pd.DataFrame({
        "experiment_id": ["EXP_TEST_01"] * n,
        "device_id": ["DEV_TEST_01"] * n,
        "sequence_number": np.arange(n, dtype=int),
        "elapsed_ms": t * 1000.0,
        "voltage_V": v,
        "current_mA": i,
        "temperature_C": temp,
        "status": ["OK"] * n,
        "data_source": ["simulation_test"] * n,
        "reference_voltage_V": [5.0] * n,
        "reference_current_mA": [1000.0] * n,
        "reference_temperature_C": [25.0] * n
    })


def test_orchestrator_voltage_pipeline_with_reference(synthetic_multichannel_df):
    """Verify voltage pipeline execution with reference measurements and spike detection."""
    orchestrator = MetrologyOrchestrator()
    config = PipelineConfig(measurand="voltage_V", tolerance_percent=1.0)
    result = orchestrator.execute(synthetic_multichannel_df, config=config)

    assert isinstance(result, PipelineResult)
    assert result.measurand == "voltage_V"
    assert result.unit == "V"
    assert result.raw_records_count == 100
    assert result.clean_records_count == 100
    assert result.is_simulated is True

    # Uncertainty budget
    budget = result.uncertainty_budget
    assert budget.combined_standard_uncertainty > 0
    assert budget.expanded_uncertainty > budget.combined_standard_uncertainty
    assert budget.coverage_factor_k >= 1.95
    assert "V" in budget.reported_result_string

    # Error metrics and calibration
    assert result.error_metrics is not None
    assert result.calibration_model is not None

    # Guard-banded conformity
    assert result.conformity_result is not None
    assert result.conformity_result.guard_banded_conformity in ("PASS", "CONDITIONAL", "FAIL")

    # Alarm detection: spike at index 50 should trigger segment_mad
    assert bool(result.detector_alarms["segment_mad"][50]) is True
    assert len(result.alarm_episodes_df) >= 1


def test_orchestrator_current_pipeline(synthetic_multichannel_df):
    """Verify current pipeline execution including shunt resistor uncertainty."""
    orchestrator = MetrologyOrchestrator()
    config = PipelineConfig(measurand="current_mA", tolerance_percent=1.0)
    result = orchestrator.execute(synthetic_multichannel_df, config=config)

    assert result.measurand == "current_mA"
    assert result.unit == "mA"
    assert pytest.approx(result.descriptive_statistics.mean, abs=1.0) == 1000.0

    # Shunt tolerance component should be in budget
    component_names = [c.name for c in result.uncertainty_budget.components]
    assert any("Shunt" in name for name in component_names)


def test_orchestrator_temperature_pipeline(synthetic_multichannel_df):
    """Verify temperature pipeline execution with DS18B20 uncertainty budget."""
    orchestrator = MetrologyOrchestrator()
    config = PipelineConfig(measurand="temperature_C", tolerance_percent=2.0)
    result = orchestrator.execute(synthetic_multichannel_df, config=config)

    assert result.measurand == "temperature_C"
    assert result.unit == "°C"
    assert pytest.approx(result.descriptive_statistics.mean, abs=0.5) == 25.0
    component_names = [c.name for c in result.uncertainty_budget.components]
    assert any("DS18B20" in name for name in component_names)


def test_orchestrator_without_reference():
    """Verify single-sensor mode when reference values are omitted."""
    n = 20
    df = pd.DataFrame({
        "sequence_number": np.arange(n),
        "elapsed_ms": np.arange(n) * 1000.0,
        "voltage_V": 3.3 + 0.001 * np.random.randn(n),
        "status": ["OK"] * n
    })

    orchestrator = MetrologyOrchestrator()
    result = orchestrator.execute(df, config=PipelineConfig(measurand="voltage_V"))

    assert result.error_metrics is None
    assert result.calibration_model is None
    assert result.conformity_result is None
    assert result.uncertainty_budget.expanded_uncertainty > 0


def test_orchestrator_with_simulation_source(synthetic_multichannel_df):
    """Verify integration with SimulationReplaySource."""
    source = SimulationReplaySource(synthetic_multichannel_df, source_name="TestReplaySource")
    orchestrator = MetrologyOrchestrator()
    result = orchestrator.execute(source, config=PipelineConfig(measurand="voltage_V"))

    assert result.is_simulated is True
    assert "TestReplaySource" in result.data_source_description
    assert result.raw_records_count == 100
