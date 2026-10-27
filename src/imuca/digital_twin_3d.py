"""
IMUCA 3D Digital Twin Visualizer.

Generates an industrial, interactive 3D WebGL scene representing the IMUCA
measurement architecture:
1. Physical Sensors (Voltage divider, 4-wire Kelvin shunt, DS18B20 temperature probe).
2. Monitored thermal heatsink and electrical DUT.
3. Central DAQ / MCU Controller.
4. Physical Demarcation Barrier.
5. Traceable Primary Reference Standard (Fluke 8508A / Keysight DMM).
6. Metrology Pipeline and Hybrid M7 Fault Engine.
7. Real-time telemetry buses with directional data flow pulses.

Styled in a dark graphite industrial SCADA theme with dynamic status highlighting
(Nominal = Cyan/Blue, Warning = Amber, Fault = Red).
"""

from __future__ import annotations
from typing import Optional, Dict, Any, List, Tuple
import math
import numpy as np
import plotly.graph_objects as go

from src.imuca.replay_engine import ReplayTelemetry


# ==============================================================================
# 3D Geometry Utilities (Boxes, Cylinders, Grid, Lines)
# ==============================================================================

def create_box_mesh(
    x_min: float, x_max: float,
    y_min: float, y_max: float,
    z_min: float, z_max: float,
    color: str,
    opacity: float = 1.0,
    name: str = "",
    hoverinfo: str = "text",
    hovertext: str = ""
) -> go.Mesh3d:
    """Create a 3D box mesh with 8 vertices and 12 triangles."""
    # 8 vertices of a cuboid
    x = [x_min, x_max, x_max, x_min, x_min, x_max, x_max, x_min]
    y = [y_min, y_min, y_max, y_max, y_min, y_min, y_max, y_max]
    z = [z_min, z_min, z_min, z_min, z_max, z_max, z_max, z_max]
    
    # 12 triangulation faces (indices into vertices)
    i = [7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2]
    j = [3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3]
    k = [0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6]
    
    return go.Mesh3d(
        x=x, y=y, z=z,
        i=i, j=j, k=k,
        color=color,
        opacity=opacity,
        name=name,
        showlegend=False,
        hoverinfo=hoverinfo,
        hovertext=hovertext if hovertext else name,
        flatshading=True,
        lighting=dict(ambient=0.6, diffuse=0.8, specular=0.2, roughness=0.5)
    )


def create_box_wireframe(
    x_min: float, x_max: float,
    y_min: float, y_max: float,
    z_min: float, z_max: float,
    color: str,
    width: int = 3,
    name: str = ""
) -> go.Scatter3d:
    """Create wireframe edge outline for a 3D box."""
    # Sequence of connected edges
    x_lines = [
        x_min, x_max, x_max, x_min, x_min, None,
        x_min, x_max, x_max, x_min, x_min, None,
        x_min, x_min, None, x_max, x_max, None,
        x_max, x_max, None, x_min, x_min
    ]
    y_lines = [
        y_min, y_min, y_max, y_max, y_min, None,
        y_min, y_min, y_max, y_max, y_min, None,
        y_min, y_min, None, y_min, y_min, None,
        y_max, y_max, None, y_max, y_max
    ]
    z_lines = [
        z_min, z_min, z_min, z_min, z_min, None,
        z_max, z_max, z_max, z_max, z_max, None,
        z_min, z_max, None, z_min, z_max, None,
        z_min, z_max, None, z_min, z_max
    ]
    return go.Scatter3d(
        x=x_lines, y=y_lines, z=z_lines,
        mode="lines",
        line=dict(color=color, width=width),
        name=name,
        showlegend=False,
        hoverinfo="none"
    )


def create_cylinder_mesh(
    x_c: float, y_c: float,
    z_min: float, z_max: float,
    radius: float,
    num_sides: int = 16,
    color: str = "#94a3b8",
    opacity: float = 1.0,
    name: str = "",
    hovertext: str = ""
) -> go.Mesh3d:
    """Create a vertical cylinder mesh (probe tube / connector pin)."""
    angles = np.linspace(0, 2 * np.pi, num_sides, endpoint=False)
    x_circle = x_c + radius * np.cos(angles)
    y_circle = y_c + radius * np.sin(angles)
    
    # Vertices: bottom circle, top circle, bottom center, top center
    x_verts = list(x_circle) + list(x_circle) + [x_c, x_c]
    y_verts = list(y_circle) + list(y_circle) + [y_c, y_c]
    z_verts = [z_min] * num_sides + [z_max] * num_sides + [z_min, z_max]
    
    idx_b_center = 2 * num_sides
    idx_t_center = 2 * num_sides + 1
    
    i_faces = []
    j_faces = []
    k_faces = []
    
    for n in range(num_sides):
        nxt = (n + 1) % num_sides
        # Side rectangle 1
        i_faces.append(n)
        j_faces.append(nxt)
        k_faces.append(num_sides + n)
        # Side rectangle 2
        i_faces.append(nxt)
        j_faces.append(num_sides + nxt)
        k_faces.append(num_sides + n)
        # Bottom cap
        i_faces.append(idx_b_center)
        j_faces.append(nxt)
        k_faces.append(n)
        # Top cap
        i_faces.append(idx_t_center)
        j_faces.append(num_sides + n)
        k_faces.append(num_sides + nxt)
        
    return go.Mesh3d(
        x=x_verts, y=y_verts, z=z_verts,
        i=i_faces, j=j_faces, k=k_faces,
        color=color,
        opacity=opacity,
        name=name,
        showlegend=False,
        hoverinfo="text",
        hovertext=hovertext if hovertext else name,
        flatshading=True,
        lighting=dict(ambient=0.7, diffuse=0.8, specular=0.3)
    )


# ==============================================================================
# Industrial SCADA Color Palette & Theme
# ==============================================================================

STATUS_COLORS = {
    "nominal": {
        "primary": "#00f0ff",      # Radiant Cyan
        "mesh": "#0ea5e9",         # Sky Blue
        "glow": "#38bdf8",         # Bright Blue
        "wire": "#0284c7"
    },
    "warning": {
        "primary": "#f59e0b",      # Amber Warning
        "mesh": "#d97706",
        "glow": "#fbbf24",
        "wire": "#b45309"
    },
    "fault": {
        "primary": "#ef4444",      # Crimson Fault
        "mesh": "#dc2626",
        "glow": "#f87171",
        "wire": "#991b1b"
    },
    "selected": {
        "primary": "#ffffff",      # White Selection Highlight
        "mesh": "#f8fafc",
        "glow": "#38bdf8",
        "wire": "#00f0ff"
    }
}


# ==============================================================================
# Main 3D Digital Twin Scene Builder
# ==============================================================================

def build_digital_twin_3d_figure(
    telemetry: Optional[ReplayTelemetry] = None,
    selected_component: str = "controller",
    camera_preset: str = "perspective",
    show_data_flow: bool = True
) -> go.Figure:
    """
    Construct the complete interactive 3D WebGL Digital Twin scene.
    
    Parameters:
    - telemetry: ReplayTelemetry snapshot containing live readings, alarm states,
      and component health statuses.
    - selected_component: ID of component currently inspected by user.
    - camera_preset: "perspective" | "top" | "front" | "voltage" | "current" | "temperature" | "reference".
    - show_data_flow: Whether to render animated telemetry conduits and directional pulses.
    """
    fig = go.Figure()
    
    # Extract status for each component
    status_map = telemetry.component_status if telemetry else {}
    ctrl_st = status_map.get("controller", "nominal")
    volt_st = status_map.get("voltage_channel", "nominal")
    curr_st = status_map.get("current_shunt", "nominal")
    temp_st = status_map.get("temperature_probe", "nominal")
    ref_st = status_map.get("reference_standard", "nominal")
    soft_st = status_map.get("software_kernel", "nominal")
    
    # -------------------------------------------------------------------------
    # 1. Baseplate & Demarcation Zones
    # -------------------------------------------------------------------------
    # Main platform base: X in [-10, 11], Y in [-6.5, 6.5], Z = 0
    fig.add_trace(create_box_mesh(
        -10.2, 11.2, -6.6, 6.6, -0.15, 0.0,
        color="#0b0f19", opacity=1.0, name="Baseplate"
    ))
    
    # Floor Grid Lines
    grid_x = []
    grid_y = []
    grid_z = []
    for gx in np.linspace(-10, 11, 22):
        grid_x.extend([gx, gx, None])
        grid_y.extend([-6.5, 6.5, None])
        grid_z.extend([0.005, 0.005, None])
    for gy in np.linspace(-6.5, 6.5, 14):
        grid_x.extend([-10, 11, None])
        grid_y.extend([gy, gy, None])
        grid_z.extend([0.005, 0.005, None])
        
    fig.add_trace(go.Scatter3d(
        x=grid_x, y=grid_y, z=grid_z,
        mode="lines",
        line=dict(color="#1e293b", width=1.5),
        showlegend=False, hoverinfo="none"
    ))
    
    # Zone 1: Sensors & Physical Acquisition Plate (X in [-9.8, -0.6])
    fig.add_trace(create_box_mesh(
        -9.8, -0.6, -6.2, 6.2, 0.008, 0.02,
        color="#0f172a", opacity=0.9, name="Zone 1: Physical Acquisition"
    ))
    fig.add_trace(create_box_wireframe(
        -9.8, -0.6, -6.2, 6.2, 0.008, 0.02,
        color="#0284c7", width=2.5
    ))
    
    # Zone 2: Embedded Controller & Telemetry Gateway (X in [-0.4, 3.4])
    fig.add_trace(create_box_mesh(
        -0.4, 3.4, -6.2, 6.2, 0.008, 0.02,
        color="#131b2e", opacity=0.9, name="Zone 2: Controller & Gateway"
    ))
    fig.add_trace(create_box_wireframe(
        -0.4, 3.4, -6.2, 6.2, 0.008, 0.02,
        color="#06b6d4", width=2.5
    ))
    
    # Zone 3: Software Metrology & Fault Detection Kernel (X in [3.6, 10.8])
    fig.add_trace(create_box_mesh(
        3.6, 10.8, -6.2, 6.2, 0.008, 0.02,
        color="#16152b", opacity=0.9, name="Zone 3: Metrology & Fault Kernel"
    ))
    fig.add_trace(create_box_wireframe(
        3.6, 10.8, -6.2, 6.2, 0.008, 0.02,
        color="#8b5cf6", width=2.5
    ))
    
    # Floor Zone Labels (3D Text billboard)
    fig.add_trace(go.Scatter3d(
        x=[-5.2, 1.5, 7.2],
        y=[-6.0, -6.0, -6.0],
        z=[0.05, 0.05, 0.05],
        mode="text",
        text=[
            "ZONE 1: SENSORS & TRANSDUCERS (SUT)",
            "ZONE 2: EMBEDDED DAQ CONTROLLER",
            "ZONE 3: METROLOGY & FAULT KERNEL"
        ],
        textfont=dict(size=9, color="#64748b", family="monospace"),
        showlegend=False, hoverinfo="none"
    ))
    
    # -------------------------------------------------------------------------
    # 2. Physical Demarcation Barrier (Hardware vs Software)
    # -------------------------------------------------------------------------
    # Vertical translucent barrier at X = 3.5, Z in [0, 2.2]
    barrier_color = "#3b82f6" if selected_component != "demarcation_barrier" else "#ffffff"
    fig.add_trace(create_box_mesh(
        3.42, 3.52, -5.8, 5.8, 0.02, 2.2,
        color=barrier_color, opacity=0.25,
        name="Demarcation Boundary",
        hovertext="PHYSICAL DEMARCATION BOUNDARY<br>Hardware Acquisition Interface <=> Software Metrology Processing"
    ))
    fig.add_trace(create_box_wireframe(
        3.42, 3.52, -5.8, 5.8, 0.02, 2.2,
        color="#38bdf8", width=3
    ))
    # Demarcation Barrier Banner Text
    fig.add_trace(go.Scatter3d(
        x=[3.47], y=[0.0], z=[2.3],
        mode="text",
        text=["--- PHYSICAL DEMARCATION BOUNDARY (HARDWARE <=> PIPELINE) ---"],
        textfont=dict(size=10, color="#38bdf8", family="monospace"),
        showlegend=False, hoverinfo="none"
    ))
    
    # -------------------------------------------------------------------------
    # 3. Component: Measurement Controller Unit (MCU / DAQ Unit)
    # -------------------------------------------------------------------------
    c_color = STATUS_COLORS[ctrl_st]["mesh"]
    c_wire = STATUS_COLORS[ctrl_st]["primary"] if selected_component != "controller" else "#ffffff"
    
    # Enclosure Box: X in [0.2, 2.8], Y in [-1.8, 1.8], Z in [0.05, 1.25]
    ctrl_hover = (
        f"<b>IMUCA EMBEDDED DAQ CONTROLLER</b><br>"
        f"Status: {ctrl_st.upper()}<br>"
        f"Architecture: 32-bit ARM Cortex-M / UART<br>"
        f"Telemetry: $IMUCA framing @ 115200 baud<br>"
        f"Hardware CRC: CCITT CRC-16 (0x1021)"
    )
    fig.add_trace(create_box_mesh(
        0.2, 2.8, -1.8, 1.8, 0.05, 1.25,
        color=c_color, opacity=0.95,
        name="Controller Unit", hovertext=ctrl_hover
    ))
    fig.add_trace(create_box_wireframe(
        0.2, 2.8, -1.8, 1.8, 0.05, 1.25,
        color=c_wire, width=4 if selected_component == "controller" else 2.5
    ))
    
    # Controller Top Cooling Fins (Aluminum ribs)
    for fin_y in np.linspace(-1.4, 1.4, 7):
        fig.add_trace(create_box_mesh(
            0.5, 2.5, fin_y - 0.04, fin_y + 0.04, 1.25, 1.38,
            color="#334155", opacity=1.0, name="Fins"
        ))
        
    # Controller Status Beacon (LED on top)
    beacon_color = STATUS_COLORS[ctrl_st]["primary"]
    fig.add_trace(create_cylinder_mesh(
        1.5, 0.0, 1.25, 1.65, radius=0.22,
        color=beacon_color, opacity=0.9,
        name="Status Beacon",
        hovertext=f"DAQ Health Beacon: {ctrl_st.upper()}"
    ))
    
    # Terminal block connectors on input face (X = 0.2)
    for term_y in [-1.2, -0.4, 0.4, 1.2]:
        fig.add_trace(create_box_mesh(
            0.05, 0.22, term_y - 0.2, term_y + 0.2, 0.2, 0.7,
            color="#047857", opacity=1.0, name="Terminal Block"
        ))
        
    # Controller 3D Label
    fig.add_trace(go.Scatter3d(
        x=[1.5], y=[0.0], z=[1.85],
        mode="text",
        text=[f"DAQ CONTROLLER [{ctrl_st.upper()}]"],
        textfont=dict(size=11, color=c_wire, family="monospace"),
        showlegend=False, hoverinfo="none"
    ))
    
    # -------------------------------------------------------------------------
    # 4. Component: Voltage Measurement Channel (DUT)
    # -------------------------------------------------------------------------
    v_color = STATUS_COLORS[volt_st]["mesh"]
    v_wire = STATUS_COLORS[volt_st]["primary"] if selected_component != "voltage_channel" else "#ffffff"
    v_reading = f"{telemetry.voltage_V:.4f} V" if (telemetry and telemetry.voltage_V is not None) else "5.000 V (Nom)"
    v_err_str = f"Error: {telemetry.voltage_error_mV:+.2f} mV" if (telemetry and telemetry.voltage_error_mV is not None) else "Ref: N/A"
    
    v_hover = (
        f"<b>DC VOLTAGE MEASUREMENT CHANNEL (SUT)</b><br>"
        f"Indicated: {v_reading}<br>"
        f"{v_err_str}<br>"
        f"Transducer: TI INA219 Bus Divider<br>"
        f"Resolution: 12-bit SAR (4 mV LSB)<br>"
        f"Channel Status: {volt_st.upper()}"
    )
    # Attenuator / Divider Enclosure: X in [-7.5, -4.5], Y in [-5.2, -2.8], Z in [0.05, 0.95]
    fig.add_trace(create_box_mesh(
        -7.5, -4.5, -5.2, -2.8, 0.05, 0.95,
        color=v_color, opacity=0.9,
        name="Voltage Channel", hovertext=v_hover
    ))
    fig.add_trace(create_box_wireframe(
        -7.5, -4.5, -5.2, -2.8, 0.05, 0.95,
        color=v_wire, width=4 if selected_component == "voltage_channel" else 2.5
    ))
    
    # High-Voltage Test Terminals (Red + / Black -)
    fig.add_trace(create_cylinder_mesh(
        -5.2, -4.6, 0.95, 1.35, radius=0.15,
        color="#ef4444", name="V+ Terminal", hovertext="V+ Input Terminal"
    ))
    fig.add_trace(create_cylinder_mesh(
        -5.2, -3.4, 0.95, 1.35, radius=0.15,
        color="#1e293b", name="V- Terminal", hovertext="V- Ground Terminal"
    ))
    
    # Voltage Channel 3D Readout Billboard
    fig.add_trace(go.Scatter3d(
        x=[-6.0], y=[-4.0], z=[1.6],
        mode="text",
        text=[f"VOLTAGE SUT\n{v_reading}\n[{volt_st.upper()}]"],
        textfont=dict(size=10, color=v_wire, family="monospace"),
        showlegend=False, hoverinfo="none"
    ))
    
    # -------------------------------------------------------------------------
    # 5. Component: Current Measurement Channel (4-Wire Kelvin Shunt)
    # -------------------------------------------------------------------------
    i_color = STATUS_COLORS[curr_st]["mesh"]
    i_wire = STATUS_COLORS[curr_st]["primary"] if selected_component != "current_shunt" else "#ffffff"
    i_reading = f"{telemetry.current_mA:.2f} mA" if (telemetry and telemetry.current_mA is not None) else "1000.0 mA (Nom)"
    i_err_str = f"Error: {telemetry.current_error_mA:+.2f} mA" if (telemetry and telemetry.current_error_mA is not None) else "Ref: N/A"
    
    i_hover = (
        f"<b>PRECISION KELVIN CURRENT SHUNT (SUT)</b><br>"
        f"Indicated: {i_reading}<br>"
        f"{i_err_str}<br>"
        f"Nominal Resistance: 0.100 Ω ± 0.5%<br>"
        f"Connection: 4-Wire Kelvin Sensing<br>"
        f"Sensor: TI INA219 Shunt ADC (10 μV LSB)<br>"
        f"Channel Status: {curr_st.upper()}"
    )
    # Shunt Block: X in [-7.5, -4.5], Y in [-1.2, 1.2], Z in [0.05, 0.85]
    fig.add_trace(create_box_mesh(
        -7.5, -4.5, -1.2, 1.2, 0.05, 0.85,
        color=i_color, opacity=0.9,
        name="Current Shunt", hovertext=i_hover
    ))
    fig.add_trace(create_box_wireframe(
        -7.5, -4.5, -1.2, 1.2, 0.05, 0.85,
        color=i_wire, width=4 if selected_component == "current_shunt" else 2.5
    ))
    
    # Heavy Copper Busbars on sides (X = -7.5 and -4.5)
    fig.add_trace(create_box_mesh(
        -7.7, -7.5, -1.0, 1.0, 0.15, 0.75,
        color="#d97706", name="Copper Busbar In"
    ))
    fig.add_trace(create_box_mesh(
        -4.5, -4.3, -1.0, 1.0, 0.15, 0.75,
        color="#d97706", name="Copper Busbar Out"
    ))
    # 4-Wire Kelvin Sense Screws (Brass bolts)
    for bx, by in [(-6.4, -0.6), (-6.4, 0.6), (-5.6, -0.6), (-5.6, 0.6)]:
        fig.add_trace(create_cylinder_mesh(
            bx, by, 0.85, 1.15, radius=0.12,
            color="#fbbf24", name="Kelvin Terminal"
        ))
        
    # Current Channel 3D Readout Billboard
    fig.add_trace(go.Scatter3d(
        x=[-6.0], y=[0.0], z=[1.5],
        mode="text",
        text=[f"CURRENT SHUNT (0.100 Ω)\n{i_reading}\n[{curr_st.upper()}]"],
        textfont=dict(size=10, color=i_wire, family="monospace"),
        showlegend=False, hoverinfo="none"
    ))
    
    # -------------------------------------------------------------------------
    # 6. Component: Temperature Probe & Monitored Thermal Mass
    # -------------------------------------------------------------------------
    t_color = STATUS_COLORS[temp_st]["mesh"]
    t_wire = STATUS_COLORS[temp_st]["primary"] if selected_component != "temperature_probe" else "#ffffff"
    t_reading = f"{telemetry.temperature_C:.3f} °C" if (telemetry and telemetry.temperature_C is not None) else "25.000 °C (Nom)"
    t_err_str = f"Error: {telemetry.temperature_error_degc:+.3f} °C" if (telemetry and telemetry.temperature_error_degc is not None) else "Ref: N/A"
    
    t_hover = (
        f"<b>TEMPERATURE PROBE & THERMAL OBJECT</b><br>"
        f"Indicated: {t_reading}<br>"
        f"{t_err_str}<br>"
        f"Sensor: Maxim Integrated DS18B20 1-Wire<br>"
        f"Probe: Stainless Steel Cylinder (6x50 mm)<br>"
        f"Object: Finned Aluminum Heat Source<br>"
        f"Resolution: 12-bit (0.0625 °C LSB)<br>"
        f"Channel Status: {temp_st.upper()}"
    )
    # Aluminum Thermal Heat Sink: X in [-7.5, -4.5], Y in [2.8, 5.2], Z in [0.05, 1.1]
    fig.add_trace(create_box_mesh(
        -7.5, -4.5, 2.8, 5.2, 0.05, 1.1,
        color="#334155", opacity=1.0,
        name="Thermal Object", hovertext=t_hover
    ))
    # Heatsink Vertical Cooling Fins
    for hf_y in np.linspace(3.1, 4.9, 6):
        fig.add_trace(create_box_mesh(
            -7.3, -4.7, hf_y - 0.05, hf_y + 0.05, 1.1, 1.45,
            color="#475569", opacity=1.0, name="Heatsink Fins"
        ))
        
    # Stainless Steel Probe Cylinder inserted into thermowell
    fig.add_trace(create_cylinder_mesh(
        -6.0, 4.0, 0.3, 1.95, radius=0.20,
        color=t_color, opacity=0.95,
        name="DS18B20 Probe", hovertext=t_hover
    ))
    fig.add_trace(create_box_wireframe(
        -7.5, -4.5, 2.8, 5.2, 0.05, 1.1,
        color=t_wire, width=4 if selected_component == "temperature_probe" else 2.5
    ))
    
    # Temperature Channel 3D Readout Billboard
    fig.add_trace(go.Scatter3d(
        x=[-6.0], y=[4.0], z=[2.25],
        mode="text",
        text=[f"TEMP PROBE (DS18B20)\n{t_reading}\n[{temp_st.upper()}]"],
        textfont=dict(size=10, color=t_wire, family="monospace"),
        showlegend=False, hoverinfo="none"
    ))
    
    # -------------------------------------------------------------------------
    # 7. Component: Traceable Primary Reference Standard (Fluke / Keysight DMM)
    # -------------------------------------------------------------------------
    # Position: X in [5.2, 9.8], Y in [-5.2, -1.8], Z in [0.05, 1.65]
    ref_wire = "#eab308" if selected_component != "reference_standard" else "#ffffff"
    ref_hover = (
        f"<b>PRIMARY REFERENCE INSTRUMENT</b><br>"
        f"Standard: 8.5-Digit High-Precision Bench DMM<br>"
        f"Traceability: ISO/IEC 17025 Accredited Calibration<br>"
        f"Reference Uncertainty: u_ref = 0.001 V (k=2, Normal)<br>"
        f"Role: Ground-truth metrological comparator<br>"
        f"Distinct from Sensor Under Test (SUT)"
    )
    # Bench Chassis (Dark Navy / Gray with gold bezel)
    fig.add_trace(create_box_mesh(
        5.2, 9.8, -5.2, -1.8, 0.05, 1.65,
        color="#1e293b", opacity=0.98,
        name="Reference Standard", hovertext=ref_hover
    ))
    fig.add_trace(create_box_wireframe(
        5.2, 9.8, -5.2, -1.8, 0.05, 1.65,
        color=ref_wire, width=4 if selected_component == "reference_standard" else 3.0
    ))
    
    # Front Bezel & Digital Readout Display (X = 5.2 face)
    fig.add_trace(create_box_mesh(
        5.15, 5.22, -4.8, -2.8, 0.6, 1.4,
        color="#022c22", opacity=1.0, name="DMM Display"
    ))
    
    # Gold Calibration Certificate Badge on top
    fig.add_trace(create_box_mesh(
        6.5, 8.5, -4.5, -2.5, 1.65, 1.70,
        color="#eab308", opacity=1.0,
        name="Calibration Seal",
        hovertext="ISO/IEC 17025 CALIBRATION SEAL: CERTIFIED TRACEABLE STANDARD"
    ))
    
    # Gold Reference Terminals (4-Wire Binding Posts on front)
    for term_y in [-2.6, -2.3, -2.0]:
        fig.add_trace(create_cylinder_mesh(
            5.1, term_y, 0.3, 0.7, radius=0.08,
            color="#fbbf24", name="Ref Terminal"
        ))
        
    # Reference Standard 3D Readout Billboard
    ref_val_str = f"REF: {telemetry.measurand_ref:.4f} {telemetry.measurand_unit}" if (telemetry and telemetry.measurand_ref is not None) else "TRACEABLE DMM STANDARD"
    fig.add_trace(go.Scatter3d(
        x=[7.5], y=[-3.5], z=[2.0],
        mode="text",
        text=[f"PRIMARY REFERENCE STANDARD\n{ref_val_str}\n[TRACEABLE DMM]"],
        textfont=dict(size=10, color="#fbbf24", family="monospace"),
        showlegend=False, hoverinfo="none"
    ))
    
    # -------------------------------------------------------------------------
    # 8. Component: Software Metrology & Fault Detection Kernel
    # -------------------------------------------------------------------------
    # Position: X in [5.2, 9.8], Y in [1.8, 5.2], Z in [0.05, 1.5]
    soft_color = STATUS_COLORS[soft_st]["mesh"]
    soft_wire = STATUS_COLORS[soft_st]["primary"] if selected_component != "software_kernel" else "#ffffff"
    
    soft_hover = (
        f"<b>SOFTWARE METROLOGY & FAULT KERNEL</b><br>"
        f"Kernel Status: {soft_st.upper()}<br>"
        f"Active Track 1: Data Integrity & Framing<br>"
        f"Active Track 2: Segment MAD Outlier Filter<br>"
        f"Active Track 3: Gradient Boosted Trees (GBT)<br>"
        f"Active Track 4: Tuned CUSUM Temporal Drift<br>"
        f"Active Track 5: Hybrid M7 Fusion Engine<br>"
        f"Metrology: GUM JCGM 100:2008 & ILAC-G8"
    )
    fig.add_trace(create_box_mesh(
        5.2, 9.8, 1.8, 5.2, 0.05, 1.5,
        color=soft_color, opacity=0.9,
        name="Software Kernel", hovertext=soft_hover
    ))
    fig.add_trace(create_box_wireframe(
        5.2, 9.8, 1.8, 5.2, 0.05, 1.5,
        color=soft_wire, width=4 if selected_component == "software_kernel" else 2.5
    ))
    
    # 3D Stack of Processing Layers (Transparent glowing slabs)
    layer_colors = ["#38bdf8", "#818cf8", "#a855f7", "#ec4899"]
    for l_idx, l_z in enumerate(np.linspace(0.3, 1.3, 4)):
        fig.add_trace(create_box_mesh(
            5.6, 9.4, 2.2, 4.8, l_z, l_z + 0.15,
            color=layer_colors[l_idx], opacity=0.4,
            name=f"Pipeline Layer {l_idx+1}"
        ))
        
    # Software Kernel 3D Readout Billboard
    alarm_summary = telemetry.alarm_category.upper() if (telemetry and telemetry.has_any_alarm) else "NOMINAL"
    fig.add_trace(go.Scatter3d(
        x=[7.5], y=[3.5], z=[1.9],
        mode="text",
        text=[f"METROLOGY & FAULT ENGINE\nState: {alarm_summary}\n[HYBRID M7 ACTIVE]"],
        textfont=dict(size=10, color=soft_wire, family="monospace"),
        showlegend=False, hoverinfo="none"
    ))
    
    # -------------------------------------------------------------------------
    # 9. Telemetry Conduits & Data Flow Lines
    # -------------------------------------------------------------------------
    if show_data_flow:
        wire_color = "#00f0ff"
        pulse_color = "#38bdf8"
        
        # Conduits from Sensors to Controller
        routes = [
            # Voltage to Controller
            [(-4.5, -4.0, 0.5), (-1.5, -4.0, 0.5), (0.05, -1.2, 0.5)],
            # Current Shunt to Controller
            [(-4.5, 0.0, 0.5), (-1.5, 0.0, 0.5), (0.05, -0.4, 0.5)],
            # Temperature Probe to Controller
            [(-4.5, 4.0, 0.5), (-1.5, 4.0, 0.5), (0.05, 1.2, 0.5)],
            # Controller to Demarcation Boundary to Metrology Kernel
            [(2.8, 0.0, 0.6), (3.45, 0.0, 0.6), (5.2, 3.5, 0.6)],
            # Reference Standard comparator link
            [(5.2, -3.5, 0.6), (4.2, -3.5, 0.6), (4.2, 2.5, 0.6), (5.2, 2.5, 0.6)]
        ]
        
        flow_x, flow_y, flow_z = [], [], []
        pulse_x, pulse_y, pulse_z = [], [], []
        
        for route in routes:
            for pt in route:
                flow_x.append(pt[0])
                flow_y.append(pt[1])
                flow_z.append(pt[2])
            flow_x.append(None)
            flow_y.append(None)
            flow_z.append(None)
            
            # Midpoints for directional telemetry markers
            for p_i in range(len(route) - 1):
                mx = 0.5 * (route[p_i][0] + route[p_i+1][0])
                my = 0.5 * (route[p_i][1] + route[p_i+1][1])
                mz = 0.5 * (route[p_i][2] + route[p_i+1][2])
                pulse_x.append(mx)
                pulse_y.append(my)
                pulse_z.append(mz)
                
        fig.add_trace(go.Scatter3d(
            x=flow_x, y=flow_y, z=flow_z,
            mode="lines",
            line=dict(color=wire_color, width=3),
            name="Telemetry Bus",
            showlegend=False, hoverinfo="none"
        ))
        
        # Glowing directional data packets
        fig.add_trace(go.Scatter3d(
            x=pulse_x, y=pulse_y, z=pulse_z,
            mode="markers",
            marker=dict(size=5, color=pulse_color, symbol="diamond"),
            name="Telemetry Stream",
            showlegend=False,
            hoverinfo="text",
            hovertext="Telemetry Stream: $IMUCA CCITT CRC-16 Frame Ingestion"
        ))
        
    # -------------------------------------------------------------------------
    # 10. Camera View Presets & Dark Industrial Layout
    # -------------------------------------------------------------------------
    camera_views = {
        "perspective": dict(
            eye=dict(x=1.55, y=-1.75, z=1.25),
            center=dict(x=0.05, y=0.0, z=0.05),
            up=dict(x=0, y=0, z=1)
        ),
        "top": dict(
            eye=dict(x=0.0, y=0.0, z=2.45),
            center=dict(x=0.0, y=0.0, z=0.0),
            up=dict(x=0, y=1, z=0)
        ),
        "front": dict(
            eye=dict(x=0.0, y=-2.45, z=0.55),
            center=dict(x=0.0, y=0.0, z=0.2),
            up=dict(x=0, y=0, z=1)
        ),
        "voltage": dict(
            eye=dict(x=-0.85, y=-1.45, z=0.75),
            center=dict(x=-0.4, y=-0.35, z=0.1),
            up=dict(x=0, y=0, z=1)
        ),
        "current": dict(
            eye=dict(x=-0.85, y=-0.65, z=0.75),
            center=dict(x=-0.4, y=0.0, z=0.1),
            up=dict(x=0, y=0, z=1)
        ),
        "temperature": dict(
            eye=dict(x=-0.85, y=0.95, z=0.75),
            center=dict(x=-0.4, y=0.35, z=0.1),
            up=dict(x=0, y=0, z=1)
        ),
        "reference": dict(
            eye=dict(x=1.35, y=-1.15, z=0.85),
            center=dict(x=0.45, y=-0.30, z=0.1),
            up=dict(x=0, y=0, z=1)
        )
    }
    
    selected_cam = camera_views.get(camera_preset, camera_views["perspective"])
    
    fig.update_layout(
        scene=dict(
            xaxis=dict(
                title=dict(text="System Longitudinal Axis (X)", font=dict(color="#64748b", size=10)),
                backgroundcolor="#0a0e17",
                gridcolor="#1e293b",
                showbackground=True,
                zerolinecolor="#334155",
                range=[-10.5, 11.5]
            ),
            yaxis=dict(
                title=dict(text="Channel Lateral Axis (Y)", font=dict(color="#64748b", size=10)),
                backgroundcolor="#0a0e17",
                gridcolor="#1e293b",
                showbackground=True,
                zerolinecolor="#334155",
                range=[-7.0, 7.0]
            ),
            zaxis=dict(
                title=dict(text="Elevation (Z)", font=dict(color="#64748b", size=10)),
                backgroundcolor="#0a0e17",
                gridcolor="#1e293b",
                showbackground=True,
                zerolinecolor="#334155",
                range=[-0.2, 2.8]
            ),
            camera=selected_cam,
            aspectmode="manual",
            aspectratio=dict(x=2.2, y=1.4, z=0.8)
        ),
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="#0b0f19",
        plot_bgcolor="#0b0f19",
        height=580,
        showlegend=False
    )
    
    return fig
