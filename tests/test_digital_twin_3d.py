"""
Unit & Integration Tests for IMUCA 3D Digital Twin and Replay Engine.

Verifies:
1. 3D view data preparation and geometric mesh generation.
2. Correct units, channel mappings, and telemetry extraction.
3. Replay state updates, frame clamping, and rolling time-window slicing.
4. Component status and dynamic color highlighting (nominal, warning, fault).
5. Missing and invalid measurement handling without exceptions.
6. Simulation-mode disclosure enforcement.
7. Camera view angle presets (perspective, top, front, close-ups).
8. Graceful behavior on empty or partial datasets.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import plotly.graph_objects as go

from src.imuca.orchestrator import MetrologyOrchestrator, PipelineConfig, PipelineResult
from src.imuca.replay_engine import (
    ReplayTelemetry,
    extract_frame_telemetry,
    get_rolling_window
)
from src.imuca.digital_twin_3d import (
    build_digital_twin_3d_figure,
    create_box_mesh,
    create_box_wireframe,
    create_cylinder_mesh,
    STATUS_COLORS
)
from src.imuca.dashboard_views import plot_digital_twin_rolling_timeseries


@pytest.fixture
def sample_pipeline_result():
    """Generate a realistic PipelineResult from demo_measurements.csv."""
    orch = MetrologyOrchestrator()
    data_path = Path("data/demo_measurements.csv")
    cfg = PipelineConfig(measurand="voltage_V", tolerance_percent=1.0)
    return orch.execute(data_path, config=cfg)


def test_3d_box_and_cylinder_mesh_creation():
    """Verify 3D geometry primitive generation."""
    box = create_box_mesh(
        x_min=-1.0, x_max=1.0,
        y_min=-2.0, y_max=2.0,
        z_min=0.0, z_max=1.5,
        color="#00f0ff",
        name="TestBox"
    )
    assert isinstance(box, go.Mesh3d)
    assert len(box.x) == 8
    assert len(box.i) == 12  # 12 triangles for 6 faces

    wire = create_box_wireframe(
        x_min=-1.0, x_max=1.0,
        y_min=-2.0, y_max=2.0,
        z_min=0.0, z_max=1.5,
        color="#ffffff"
    )
    assert isinstance(wire, go.Scatter3d)
    assert wire.mode == "lines"

    cyl = create_cylinder_mesh(
        x_c=0.0, y_c=0.0,
        z_min=0.0, z_max=2.0,
        radius=0.5,
        num_sides=12,
        color="#94a3b8"
    )
    assert isinstance(cyl, go.Mesh3d)
    assert len(cyl.x) == 12 * 2 + 2


def test_digital_twin_3d_figure_presets():
    """Verify 3D scene renders all camera presets cleanly."""
    for preset in ["perspective", "top", "front", "voltage", "current", "temperature", "reference"]:
        fig = build_digital_twin_3d_figure(
            telemetry=None,
            selected_component="voltage_channel",
            camera_preset=preset,
            show_data_flow=True
        )
        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 50
        assert fig.layout.paper_bgcolor == "#0b0f19"
        assert "scene" in fig.layout
        assert "camera" in fig.layout.scene


def test_replay_telemetry_extraction(sample_pipeline_result):
    """Verify frame-by-frame telemetry synchronization and clamping."""
    res = sample_pipeline_result
    n_frames = len(res.annotated_df)

    # Frame 0
    t0 = extract_frame_telemetry(res, 0)
    assert isinstance(t0, ReplayTelemetry)
    assert t0.frame_idx == 0
    assert t0.total_frames == n_frames
    assert t0.active_measurand == "voltage_V"
    assert t0.measurand_unit == "V"
    assert t0.is_simulated is True
    assert "controller" in t0.component_status
    assert "voltage_channel" in t0.component_status

    # Frame clamp out of bounds
    t_end = extract_frame_telemetry(res, 999999)
    assert t_end.frame_idx == n_frames - 1

    t_neg = extract_frame_telemetry(res, -50)
    assert t_neg.frame_idx == 0


def test_component_status_mapping_on_alarms(sample_pipeline_result):
    """Verify component health states update to fault/warning when alarms trip."""
    res = sample_pipeline_result
    # Force an alarm on hybrid_m7 and integrity at frame 2
    res.detector_alarms["hybrid_m7"] = res.detector_alarms["hybrid_m7"].copy()
    res.detector_alarms["hybrid_m7"][2] = True
    res.detector_alarms["integrity"] = res.detector_alarms["integrity"].copy()
    res.detector_alarms["integrity"][2] = True

    t2 = extract_frame_telemetry(res, 2)
    assert t2.has_any_alarm is True
    assert t2.component_status["voltage_channel"] == "fault"
    assert t2.component_status["controller"] == "fault"
    assert t2.component_status["software_kernel"] == "fault"
    assert t2.component_status["reference_standard"] == "nominal"  # Standard always nominal


def test_digital_twin_empty_dataframe_graceful_handling(sample_pipeline_result):
    """Verify empty dataframe does not cause crash or divide-by-zero."""
    # Create an empty result by clearing annotated_df from sample_pipeline_result
    from dataclasses import replace
    empty_res = replace(sample_pipeline_result, annotated_df=pd.DataFrame())

    t_empty = extract_frame_telemetry(empty_res, 0)
    assert t_empty.total_frames == 0
    assert t_empty.voltage_V is None

    fig = build_digital_twin_3d_figure(telemetry=t_empty)
    assert isinstance(fig, go.Figure)

    fig_rolling = plot_digital_twin_rolling_timeseries(
        df=pd.DataFrame(),
        measurand="voltage_V",
        unit="V",
        current_idx=0
    )
    assert isinstance(fig_rolling, go.Figure)



def test_rolling_window_slicing():
    """Verify rolling window dataframe slice calculation."""
    df = pd.DataFrame({"elapsed_ms": np.arange(100) * 100.0, "val": np.arange(100)})
    win = get_rolling_window(df, current_idx=50, window_size=20)
    assert len(win) == 20
    assert win.iloc[-1]["val"] == 50

    # Start boundary
    win_start = get_rolling_window(df, current_idx=5, window_size=20)
    assert len(win_start) == 6


def test_rolling_timeseries_plot(sample_pipeline_result):
    """Verify oscilloscope rolling trend figure generation."""
    res = sample_pipeline_result
    fig = plot_digital_twin_rolling_timeseries(
        df=res.annotated_df,
        measurand="voltage_V",
        unit="V",
        current_idx=3,
        window_samples=10,
        alarm_mask=res.detector_alarms.get("hybrid_m7")
    )
    assert isinstance(fig, go.Figure)
    assert len(fig.data) >= 2  # Indicated + cursor marker
    assert fig.layout.paper_bgcolor == "#0b0f19"
