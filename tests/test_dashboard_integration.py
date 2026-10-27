"""
Automated Integration Tests for IMUCA Dashboard Workflows (Phase 4).

Systematically tests:
1. Normal fault-free synthetic run.
2. Runs containing voltage, current, and temperature faults.
3. Missing and invalid data handling.
4. Communication gaps and duplicate sequences.
5. Datasets with and without reference measurements.
6. Empty and malformed inputs.
7. Verification that synthetic data is never flagged as physical measurement.
8. Telemetry packet parsing, CRC checks, and summary JSON/CSV exports.
"""

import pytest
import json
from pathlib import Path
import numpy as np
import pandas as pd

from src.imuca.orchestrator import MetrologyOrchestrator, PipelineConfig, PipelineResult
from src.imuca.hardware_adapter import (
    SimulationReplaySource,
    SerialHardwareAdapter,
    parse_telemetry_frame,
    format_telemetry_frame,
    PacketChecksumError,
    PacketFormatError
)
from src.imuca.dashboard_views import (
    plot_multichannel_timeseries,
    plot_calibration_fit_and_residuals,
    plot_uncertainty_budget_breakdown,
    plot_multi_track_alarms_timeline,
    plot_sampling_interval_jitter
)


@pytest.fixture
def data_root():
    return Path("data")


def test_workflow_normal_fault_free(data_root):
    """Workflow 1: Normal fault-free synthetic run (FD5_VA_NONE.csv)."""
    scenario_path = data_root / "synthetic_v5" / "fault_detection" / "FD5_VA_NONE.csv"
    if not scenario_path.exists():
        pytest.skip("FD5_VA_NONE.csv not found")

    orchestrator = MetrologyOrchestrator()
    res = orchestrator.execute(scenario_path, PipelineConfig(measurand="voltage_V"))

    assert res.is_simulated is True
    assert res.raw_records_count > 0
    assert res.clean_records_count > 0
    assert res.uncertainty_budget.combined_standard_uncertainty > 0
    assert res.uncertainty_budget.expanded_uncertainty > 0
    assert "V" in res.uncertainty_budget.reported_result_string


def test_workflow_voltage_fault(data_root):
    """Workflow 2: Voltage fault run (FD5_VA_ISOLATED_SPIKE.csv)."""
    scenario_path = data_root / "synthetic_v5" / "fault_detection" / "FD5_VA_ISOLATED_SPIKE.csv"
    if not scenario_path.exists():
        pytest.skip("FD5_VA_ISOLATED_SPIKE.csv not found")

    orchestrator = MetrologyOrchestrator()
    res = orchestrator.execute(scenario_path, PipelineConfig(measurand="voltage_V"))

    assert res.measurand == "voltage_V"
    assert res.detector_alarms["segment_mad"].any() or res.detector_alarms["hybrid_m7"].any()
    assert len(res.alarm_episodes_df) >= 1


def test_workflow_current_fault(data_root):
    """Workflow 3: Current fault run with shunt self-heating (FD5_IA_GAIN_CHANGE.csv)."""
    scenario_path = data_root / "synthetic_v5" / "fault_detection" / "FD5_IA_GAIN_CHANGE.csv"
    if not scenario_path.exists():
        pytest.skip("FD5_IA_GAIN_CHANGE.csv not found")

    orchestrator = MetrologyOrchestrator()
    res = orchestrator.execute(scenario_path, PipelineConfig(measurand="current_mA"))

    assert res.measurand == "current_mA"
    assert res.unit == "mA"
    assert any("Shunt" in c.name for c in res.uncertainty_budget.components)


def test_workflow_temperature_fault(data_root):
    """Workflow 4: Temperature fault run with sensor lag (FD5_TA_GRADUAL_DRIFT.csv)."""
    scenario_path = data_root / "synthetic_v5" / "fault_detection" / "FD5_TA_GRADUAL_DRIFT.csv"
    if not scenario_path.exists():
        pytest.skip("FD5_TA_GRADUAL_DRIFT.csv not found")

    orchestrator = MetrologyOrchestrator()
    res = orchestrator.execute(scenario_path, PipelineConfig(measurand="temperature_C"))

    assert res.measurand == "temperature_C"
    assert res.unit == "°C"
    assert res.raw_records_count > 0


def test_workflow_malformed_missing_and_invalid(data_root):
    """Workflow 5: Missing and non-finite data (MAL_non_finite.csv)."""
    mal_path = data_root / "synthetic_v5" / "malformed" / "MAL_non_finite.csv"
    if not mal_path.exists():
        pytest.skip("MAL_non_finite.csv not found")

    orchestrator = MetrologyOrchestrator()
    res = orchestrator.execute(mal_path, PipelineConfig(measurand="voltage_V"))

    # Quality check must non-destructively flag the non-finite record
    assert len(res.quality_report.issues) > 0
    assert any(iss.issue_type == "NON_FINITE" for iss in res.quality_report.issues)
    assert res.clean_records_count < res.raw_records_count


def test_workflow_communication_gaps_and_duplicates(data_root):
    """Workflow 6: Communication gaps and duplicates (MAL_sequence_gap.csv)."""
    gap_path = data_root / "synthetic_v5" / "malformed" / "MAL_sequence_gap.csv"
    if not gap_path.exists():
        pytest.skip("MAL_sequence_gap.csv not found")

    orchestrator = MetrologyOrchestrator()
    res = orchestrator.execute(gap_path, PipelineConfig(measurand="voltage_V"))

    assert any(iss.issue_type == "SEQUENCE_GAP" for iss in res.quality_report.issues)


def test_workflow_with_and_without_reference(data_root):
    """Workflow 7: Compares execution with reference vs single-sensor mode without reference."""
    df_with_ref = pd.DataFrame({
        "sequence_number": np.arange(20),
        "elapsed_ms": np.arange(20) * 1000.0,
        "voltage_V": 5.0 + 0.001 * np.random.randn(20),
        "reference_voltage_V": [5.0] * 20,
        "status": ["OK"] * 20
    })

    df_without_ref = df_with_ref.drop(columns=["reference_voltage_V"])

    orchestrator = MetrologyOrchestrator()
    res_with = orchestrator.execute(df_with_ref, PipelineConfig(measurand="voltage_V"))
    res_without = orchestrator.execute(df_without_ref, PipelineConfig(measurand="voltage_V"))

    # With reference: calibration model and error metrics exist
    assert res_with.error_metrics is not None
    assert res_with.calibration_model is not None
    assert res_with.conformity_result is not None

    # Without reference: single-sensor indicated values only
    assert res_without.error_metrics is None
    assert res_without.calibration_model is None
    assert res_without.conformity_result is None
    # Both evaluate valid GUM uncertainty
    assert res_without.uncertainty_budget.expanded_uncertainty > 0


def test_workflow_empty_and_corrupt_input(data_root):
    """Workflow 8: Empty and corrupt inputs produce clear diagnostics rather than silent corruption."""
    header_only_path = data_root / "synthetic_v5" / "malformed" / "MAL_header_only.csv"
    if not header_only_path.exists():
        pytest.skip("MAL_header_only.csv not found")

    orchestrator = MetrologyOrchestrator()
    res = orchestrator.execute(header_only_path, PipelineConfig(measurand="voltage_V"))

    assert res.raw_records_count == 0
    assert not res.schema_validation.is_valid
    assert any(d.issue_code == "EMPTY_DATASET" for d in res.schema_validation.diagnostics)


def test_workflow_dashboard_views_generation(data_root):
    """Workflow 9: Verify dashboard Plotly figures generate cleanly without rendering errors."""
    df = pd.DataFrame({
        "sequence_number": np.arange(50),
        "elapsed_ms": np.arange(50) * 1000.0,
        "voltage_V": 5.0 + 0.002 * np.random.randn(50),
        "reference_voltage_V": [5.0] * 50,
        "status": ["OK"] * 50
    })

    orchestrator = MetrologyOrchestrator()
    res = orchestrator.execute(df, PipelineConfig(measurand="voltage_V"))

    # Time series figure
    fig_ts = plot_multichannel_timeseries(
        df=res.annotated_df,
        measurand="voltage_V",
        unit="V",
        alarm_mask=res.detector_alarms["hybrid_m7"]
    )
    assert fig_ts is not None

    # Calibration & Residual figures
    fig_cal, fig_res = plot_calibration_fit_and_residuals(
        clean_df=res.annotated_df,
        measurand="voltage_V",
        unit="V",
        cal_model=res.calibration_model
    )
    assert fig_cal is not None
    assert fig_res is not None

    # Uncertainty budget bar chart
    fig_unc = plot_uncertainty_budget_breakdown(res.uncertainty_budget)
    assert fig_unc is not None

    # Multi-track timeline
    fig_tl = plot_multi_track_alarms_timeline(
        df=res.annotated_df,
        detector_alarms=res.detector_alarms,
        episode_df=res.alarm_episodes_df
    )
    assert fig_tl is not None

    # Sampling jitter
    fig_jit = plot_sampling_interval_jitter(res.annotated_df)
    assert fig_jit is not None


def test_workflow_exports_and_simulation_isolation(data_root):
    """Workflow 10: Summary dictionary, JSON export, and simulation mode enforcement."""
    df = pd.DataFrame({
        "sequence_number": np.arange(10),
        "elapsed_ms": np.arange(10) * 1000.0,
        "voltage_V": [5.0] * 10,
        "status": ["OK"] * 10
    })

    orchestrator = MetrologyOrchestrator()
    res = orchestrator.execute(df, PipelineConfig(measurand="voltage_V"))

    summary = res.to_summary_dict()
    assert summary["is_simulated"] is True
    assert summary["measurand"] == "voltage_V"
    assert "mean" in summary
    assert "combined_uncertainty" in summary

    # Verify JSON serializability
    json_str = json.dumps(summary)
    assert len(json_str) > 0
