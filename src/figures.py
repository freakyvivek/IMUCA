"""
Visualization and Interactive Graphing Module for IMUCA.
Implements Chapter 15: Interactive Plotly figures with clean engineering styling,
zoom/pan, hover annotations, and conformity color coding.
"""

from typing import List, Optional, Tuple, Dict, Any, Union
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from src.budget import UncertaintyBudget
from src.calibration import CalibrationResult
from src.drift import DriftAnalysisResult


# Color palette for metrological status
COLORS = {
    "pass": "#10b981",       # Emerald green
    "marginal": "#f59e0b",   # Amber
    "fail": "#ef4444",       # Crimson red
    "ideal": "#64748b",      # Slate gray
    "fit": "#2563eb",        # Royal blue
    "dominant": "#dc2626",   # Strong red
    "normal_bar": "#3b82f6", # Blue
    "tolerance": "#f43f5e",  # Rose
    "guard": "#fbbf24",      # Amber/Yellow
    "bg": "#ffffff",
    "grid": "#f1f5f9"
}


def plot_calibration_curve(cal_result: CalibrationResult) -> go.Figure:
    """
    Plot Reference vs DUT Indication with Ideal 1:1 Line and Fitted Calibration Line.
    """
    refs = [p.reference_v for p in cal_result.points]
    duts = [p.dut_v for p in cal_result.points]
    statuses = [p.conformity_status for p in cal_result.points]
    
    min_x, max_x = min(refs), max(refs)
    span_x = np.linspace(min_x * 0.9, max_x * 1.05, 100)
    ideal_y = span_x
    fit_y = cal_result.slope_m * span_x + cal_result.intercept_c
    
    fig = go.Figure()
    
    # Ideal 1:1 Line
    fig.add_trace(go.Scatter(
        x=span_x,
        y=ideal_y,
        mode="lines",
        name="Ideal Line (1:1)",
        line=dict(color=COLORS["ideal"], dash="dash", width=1.5),
        hoverinfo="skip"
    ))
    
    # Fitted Regression Line
    fig.add_trace(go.Scatter(
        x=span_x,
        y=fit_y,
        mode="lines",
        name=f"Fitted Line: Y = {cal_result.slope_m:.4f}X + {cal_result.intercept_c*1000:+.2f} mV",
        line=dict(color=COLORS["fit"], width=2.5),
        hoverinfo="skip"
    ))
    
    # Data Points with Conformity Color Coding
    point_colors = [COLORS["pass"] if s == "PASS" else (COLORS["marginal"] if s == "MARGINAL" else COLORS["fail"]) for s in statuses]
    hover_texts = [
        f"<b>Point {p.point_index}</b><br>"
        f"Ref: {p.reference_v:.3f} V<br>"
        f"DUT: {p.dut_v:.2f} V<br>"
        f"Error: {p.absolute_error_mv:+.1f} mV ({p.percentage_error:+.3f} %)<br>"
        f"Status: <b>{p.conformity_status}</b>"
        for p in cal_result.points
    ]
    
    fig.add_trace(go.Scatter(
        x=refs,
        y=duts,
        mode="markers",
        name="Calibration Points",
        marker=dict(size=11, color=point_colors, line=dict(width=1.5, color="#0f172a")),
        text=hover_texts,
        hoverinfo="text"
    ))
    
    fig.update_layout(
        title=dict(
            text=f"<b>Calibration Curve: Reference vs DUT Indication</b> (R² = {cal_result.r_squared:.6f})",
            x=0.05
        ),
        xaxis_title="Reference Standard Voltage (V)",
        yaxis_title="DUT Indicated Voltage (V)",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=60, b=40),
        height=450
    )
    return fig


def plot_error_vs_reference(cal_result: CalibrationResult) -> go.Figure:
    """
    Plot Percentage Error vs Reference Voltage with +/- T and +/- 0.8T tolerance bands.
    """
    refs = [p.reference_v for p in cal_result.points]
    pct_errors = [p.percentage_error for p in cal_result.points]
    tol_pct = cal_result.points[0].tolerance_percent if cal_result.points else 1.0
    statuses = [p.conformity_status for p in cal_result.points]
    
    min_x, max_x = min(refs), max(refs)
    x_range = [min_x - 0.2, max_x + 0.2]
    
    fig = go.Figure()
    
    # Zero error line
    fig.add_trace(go.Scatter(
        x=x_range,
        y=[0, 0],
        mode="lines",
        name="Zero Error",
        line=dict(color="#94a3b8", width=1.5, dash="dot"),
        hoverinfo="skip"
    ))
    
    # Upper & Lower Tolerance Limit (+/- T)
    fig.add_trace(go.Scatter(
        x=x_range,
        y=[tol_pct, tol_pct],
        mode="lines",
        name=f"Tolerance Limit (±{tol_pct:.1f} %)",
        line=dict(color=COLORS["tolerance"], dash="dash", width=2),
        hoverinfo="skip"
    ))
    fig.add_trace(go.Scatter(
        x=x_range,
        y=[-tol_pct, -tol_pct],
        mode="lines",
        showlegend=False,
        line=dict(color=COLORS["tolerance"], dash="dash", width=2),
        hoverinfo="skip"
    ))
    
    # Guard-band Limits (+/- 0.8 T)
    guard_pct = 0.8 * tol_pct
    fig.add_trace(go.Scatter(
        x=x_range,
        y=[guard_pct, guard_pct],
        mode="lines",
        name=f"Guard Band (±{guard_pct:.1f} %)",
        line=dict(color=COLORS["guard"], dash="dot", width=1.5),
        hoverinfo="skip"
    ))
    fig.add_trace(go.Scatter(
        x=x_range,
        y=[-guard_pct, -guard_pct],
        mode="lines",
        showlegend=False,
        line=dict(color=COLORS["guard"], dash="dot", width=1.5),
        hoverinfo="skip"
    ))
    
    # Points
    point_colors = [COLORS["pass"] if s == "PASS" else (COLORS["marginal"] if s == "MARGINAL" else COLORS["fail"]) for s in statuses]
    hover_texts = [
        f"<b>Point {p.point_index} ({p.reference_v:.3f} V)</b><br>"
        f"Percentage Error: <b>{p.percentage_error:+.3f} %</b><br>"
        f"Absolute Error: {p.absolute_error_mv:+.1f} mV<br>"
        f"Conformity: <b>{p.conformity_status}</b>"
        for p in cal_result.points
    ]
    
    fig.add_trace(go.Scatter(
        x=refs,
        y=pct_errors,
        mode="lines+markers",
        name="Observed Error (%)",
        line=dict(color="#475569", width=1.5),
        marker=dict(size=11, color=point_colors, line=dict(width=1.5, color="#0f172a")),
        text=hover_texts,
        hoverinfo="text"
    ))
    
    fig.update_layout(
        title=dict(
            text=f"<b>Measurement Error vs Reference Voltage</b> ({cal_result.summary_text})",
            x=0.05
        ),
        xaxis_title="Reference Standard Voltage (V)",
        yaxis_title="Measurement Error (% of reading)",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=60, b=40),
        height=450
    )
    return fig


def plot_residuals(cal_result: CalibrationResult) -> go.Figure:
    """
    Plot Residual Error (mV) vs Reference Voltage with +/- Resolution/2 limit lines.
    """
    res = cal_result.residuals
    df_res = res.residuals_dataframe
    refs = df_res["Reference_V"].values
    res_mv = df_res["Residual_mV"].values
    half_res_mv = res.resolution_limit_mv
    
    min_x, max_x = min(refs), max(refs)
    x_range = [min_x - 0.2, max_x + 0.2]
    
    fig = go.Figure()
    
    # Zero line
    fig.add_trace(go.Scatter(
        x=x_range,
        y=[0, 0],
        mode="lines",
        name="Zero Residual",
        line=dict(color="#94a3b8", width=1.5, dash="dot"),
        hoverinfo="skip"
    ))
    
    # Half-resolution quantization bounds (+/- 5 mV)
    fig.add_trace(go.Scatter(
        x=x_range,
        y=[half_res_mv, half_res_mv],
        mode="lines",
        name=f"Quantisation Bound (+/- {half_res_mv:.1f} mV)",
        line=dict(color="#e11d48", dash="dash", width=1.5),
        hoverinfo="skip"
    ))
    fig.add_trace(go.Scatter(
        x=x_range,
        y=[-half_res_mv, -half_res_mv],
        mode="lines",
        showlegend=False,
        line=dict(color="#e11d48", dash="dash", width=1.5),
        hoverinfo="skip"
    ))
    
    # Residual points
    hover_texts = [
        f"<b>Point {row['Point']} ({row['Reference_V']:.3f} V)</b><br>"
        f"Residual: <b>{row['Residual_mV']:+.2f} mV</b><br>"
        f"DUT: {row['DUT_V']:.2f} V | Fit: {row['Fitted_DUT_V']:.4f} V"
        for _, row in df_res.iterrows()
    ]
    
    fig.add_trace(go.Scatter(
        x=refs,
        y=res_mv,
        mode="lines+markers",
        name="Fitted Residual",
        line=dict(color="#2563eb", width=2),
        marker=dict(size=9, color="#1d4ed8"),
        text=hover_texts,
        hoverinfo="text"
    ))
    
    fig.update_layout(
        title=dict(
            text=f"<b>Residual Error Plot</b> (Max |Residual| = {res.max_residual_mv:.2f} mV)",
            x=0.05
        ),
        xaxis_title="Reference Standard Voltage (V)",
        yaxis_title="Residual Error (mV)",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=60, b=40),
        height=420
    )
    return fig


def plot_uncertainty_budget_chart(budget: UncertaintyBudget) -> go.Figure:
    """
    Plot Horizontal Bar Chart of Uncertainty Contributions, highlighting dominant source in red.
    """
    entries = sorted(budget.entries, key=lambda x: x.variance_contribution_percent)
    names = [e.source_name for e in entries]
    pcts = [e.variance_contribution_percent for e in entries]
    u_mvs = [e.standard_uncertainty_mv for e in entries]
    bar_colors = [COLORS["dominant"] if e.is_dominant else COLORS["normal_bar"] for e in entries]
    
    hover_texts = [
        f"<b>{e.source_name}</b><br>"
        f"Type: {e.uncertainty_type}<br>"
        f"Standard Uncertainty u: {e.standard_uncertainty_mv:.3f} mV<br>"
        f"Variance Share: <b>{e.variance_contribution_percent:.1f} %</b><br>"
        f"Distribution: {e.distribution_name} (Divisor: {e.divisor_display})<br>"
        f"{'★ DOMINANT CONTRIBUTOR' if e.is_dominant else ''}"
        for e in entries
    ]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=names,
        x=pcts,
        orientation="h",
        marker=dict(color=bar_colors, line=dict(width=1, color="#0f172a")),
        text=[f"{p:.1f} %  ({u:.3f} mV)" for p, u in zip(pcts, u_mvs)],
        textposition="auto",
        hovertext=hover_texts,
        hoverinfo="text"
    ))
    
    fig.update_layout(
        title=dict(
            text=f"<b>Uncertainty Budget: Variance Contribution (%)</b> (Dominant: {budget.dominant_source.source_name})",
            x=0.05
        ),
        xaxis_title="Contribution to Combined Variance (%)",
        yaxis_title="Uncertainty Source",
        template="plotly_white",
        margin=dict(l=150, r=40, t=60, b=40),
        height=380
    )
    return fig


def plot_repeat_distribution_chart(readings: Union[List[float], np.ndarray], reference_v: float = 5.000) -> go.Figure:
    """
    Plot run-sequence chart and box plot of repeat readings.
    """
    arr = np.array(readings, dtype=float)
    seq = np.arange(1, len(arr) + 1)
    mean_val = float(np.mean(arr))
    sd_val = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
    
    fig = go.Figure()
    
    # Mean line
    fig.add_trace(go.Scatter(
        x=[0.5, len(arr) + 0.5],
        y=[mean_val, mean_val],
        mode="lines",
        name=f"Mean ({mean_val:.4f} V)",
        line=dict(color="#10b981", width=2, dash="dash")
    ))
    
    # +/- 1 SD band
    fig.add_trace(go.Scatter(
        x=[0.5, len(arr) + 0.5],
        y=[mean_val + sd_val, mean_val + sd_val],
        mode="lines",
        name=f"+/- 1 SD (s = {sd_val*1000:.2f} mV)",
        line=dict(color="#94a3b8", width=1.5, dash="dot")
    ))
    fig.add_trace(go.Scatter(
        x=[0.5, len(arr) + 0.5],
        y=[mean_val - sd_val, mean_val - sd_val],
        mode="lines",
        showlegend=False,
        line=dict(color="#94a3b8", width=1.5, dash="dot")
    ))
    
    # Points
    fig.add_trace(go.Scatter(
        x=seq,
        y=arr,
        mode="lines+markers",
        name="Observations",
        line=dict(color="#3b82f6", width=2),
        marker=dict(size=10, color="#1e40af")
    ))
    
    fig.update_layout(
        title=dict(
            text=f"<b>Repeated Observations Run Sequence (n = {len(arr)})</b>",
            x=0.05
        ),
        xaxis_title="Reading Sequence Index",
        yaxis_title="Measured Voltage (V)",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=60, b=40),
        height=380
    )
    return fig


def plot_drift_trend_chart(drift_result: DriftAnalysisResult) -> go.Figure:
    """
    Plot Between-Session Drift Trend, Linear Regression Fit, and Projected Breach.
    """
    if not drift_result.is_assessed:
        fig = go.Figure()
        fig.add_annotation(
            text="No calibration history loaded for drift analysis.",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#64748b")
        )
        fig.update_layout(template="plotly_white", height=400)
        return fig
        
    t_hist = drift_result.sessions
    e_hist = drift_result.mean_errors_mv
    b = drift_result.slope_b
    a = drift_result.intercept_a
    tol_mv = drift_result.tolerance_mv
    breach = drift_result.projected_breach_session
    
    # Create span including history + projection
    max_t = int(np.ceil(breach + 3)) if breach is not None else int(t_hist[-1] + 5)
    t_span = np.linspace(1, max_t, 150)
    e_fitted = a + b * t_span
    
    fig = go.Figure()
    
    # Tolerance limit line (+T)
    fig.add_trace(go.Scatter(
        x=[1, max_t],
        y=[tol_mv, tol_mv],
        mode="lines",
        name=f"Tolerance Limit (+{tol_mv:.0f} mV)",
        line=dict(color=COLORS["tolerance"], dash="dash", width=2)
    ))
    
    # Regression fit line
    fig.add_trace(go.Scatter(
        x=t_span,
        y=e_fitted,
        mode="lines",
        name=f"Linear Fit: {b:+.2f} mV/session (R² = {drift_result.r_squared:.3f})",
        line=dict(color=COLORS["fit"], width=2.5)
    ))
    
    # Historical data points
    hover_hist = [
        f"<b>Session {int(s)}</b><br>"
        f"Mean Error: <b>{e:+.1f} mV</b><br>"
        f"Fitted: {a + b * s:+.2f} mV"
        for s, e in zip(t_hist, e_hist)
    ]
    fig.add_trace(go.Scatter(
        x=t_hist,
        y=e_hist,
        mode="markers",
        name="Historical Sessions",
        marker=dict(size=10, color="#1e293b", line=dict(width=1.5, color="#ffffff")),
        text=hover_hist,
        hoverinfo="text"
    ))
    
    # Breach marker
    if breach is not None:
        fig.add_trace(go.Scatter(
            x=[breach],
            y=[tol_mv],
            mode="markers+text",
            name=f"Projected Breach (Session {breach:.0f})",
            marker=dict(size=14, color=COLORS["fail"], symbol="x", line=dict(width=2.5)),
            text=[f"  Breach: Session {breach:.0f}"],
            textposition="top right"
        ))
        
    fig.update_layout(
        title=dict(
            text=f"<b>Measurement Drift Trend & Tolerance Breach Forecast</b> (p = {drift_result.p_value:.2e})",
            x=0.05
        ),
        xaxis_title="Calibration Session Index",
        yaxis_title="Mean Error at 5.000 V (mV)",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=60, b=40),
        height=450
    )
    return fig
