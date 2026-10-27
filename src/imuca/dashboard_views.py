"""
IMUCA Dashboard Visualization & Plotting Components.

Provides engineering-grade Plotly charts for the 10-section Unified Metrology Dashboard:
1. Multi-channel time series (voltage, current, temperature) with alarm highlighting and ground-truth isolation.
2. Metrology & calibration curves with 1:1 ideal, fitted polynomial/linear regression, and residuals.
3. GUM uncertainty budget waterfall and variance contribution bar charts.
4. Data quality & sampling interval jitter diagnostics.
5. Multi-track comparative alarm timeline (Integrity, Segment, ML GBT, CUSUM, Hybrid M7).
"""

from typing import List, Optional, Tuple, Dict, Any, Union
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from src.imuca.uncertainty import UncertaintyBudget
from src.imuca.calibration import CalibrationModel


METROLOGY_PALETTE = {
    "voltage": "#2563eb",       # Blue
    "current": "#059669",       # Emerald green
    "temperature": "#d97706",   # Amber / Orange
    "reference": "#475569",     # Slate reference line
    "alarm": "#dc2626",         # Red
    "alarm_fill": "rgba(220, 38, 38, 0.15)",
    "ground_truth": "#9333ea",  # Purple
    "ideal": "#64748b",
    "fit": "#2563eb",
    "residual": "#0284c7",
    "upper_bound": "#e11d48",
    "lower_bound": "#e11d48",
    "grid": "#f1f5f9"
}

CATEGORY_COLORS = {
    "transient": "#f97316",   # Orange
    "stuck": "#8b5cf6",       # Purple
    "persistent": "#ef4444",  # Red
    "drift": "#3b82f6",       # Blue
    "integrity": "#991b1b",  # Dark Crimson
    "uncertain": "#6b7280",  # Grey
    "none": "#10b981"         # Green (normal)
}


def plot_multichannel_timeseries(
    df: pd.DataFrame,
    measurand: str,
    unit: str,
    show_reference: bool = True,
    show_alarms: bool = True,
    show_ground_truth: bool = False,
    alarm_mask: Optional[np.ndarray] = None,
    time_window_samples: Optional[Tuple[int, int]] = None
) -> go.Figure:
    """
    Plot time series of selected measurand with timestamps, units, and alarm overlays.
    """
    view_df = df.copy()
    if time_window_samples is not None:
        start_idx, end_idx = time_window_samples
        view_df = view_df.iloc[start_idx:end_idx].reset_index(drop=True)
        if alarm_mask is not None:
            alarm_mask = alarm_mask[start_idx:end_idx]

    t_s = view_df["elapsed_ms"].to_numpy(dtype=float) / 1000.0 if "elapsed_ms" in view_df.columns else np.arange(len(view_df))
    vals = view_df[measurand].to_numpy(dtype=float) if measurand in view_df.columns else np.zeros(len(view_df))

    fig = go.Figure()

    # Base Measurement Trace
    color = METROLOGY_PALETTE.get(measurand.split("_")[0], "#2563eb")
    fig.add_trace(go.Scatter(
        x=t_s,
        y=vals,
        mode="lines",
        name=f"Indicated {measurand} ({unit})",
        line=dict(color=color, width=2.0),
        hovertemplate=f"Time: %{{x:.2f}} s<br>{measurand}: %{{y:.4f}} {unit}<extra></extra>"
    ))

    # Reference Line (if present and requested)
    ref_col = f"reference_{measurand}"
    if show_reference and ref_col in view_df.columns and view_df[ref_col].notna().any():
        fig.add_trace(go.Scatter(
            x=t_s,
            y=view_df[ref_col].to_numpy(dtype=float),
            mode="lines",
            name=f"Reference Standard ({unit})",
            line=dict(color=METROLOGY_PALETTE["reference"], dash="dash", width=1.8),
            hovertemplate=f"Ref: %{{y:.4f}} {unit}<extra></extra>"
        ))

    # Predicted Alarms Overlay
    if show_alarms and alarm_mask is not None and np.any(alarm_mask):
        alarm_idx = np.flatnonzero(alarm_mask)
        fig.add_trace(go.Scatter(
            x=t_s[alarm_idx],
            y=vals[alarm_idx],
            mode="markers",
            name="Active Alarm (Predicted)",
            marker=dict(symbol="x", size=8, color=METROLOGY_PALETTE["alarm"], line=dict(width=1.5)),
            hovertemplate=f"ALARM ACTIVE<br>Time: %{{x:.2f}} s<br>Value: %{{y:.4f}} {unit}<extra></extra>"
        ))

    # Ground-Truth Fault Labels (Offline Inspection ONLY)
    if show_ground_truth and "label_fault_type" in view_df.columns:
        fault_mask = view_df["label_fault_type"].astype(str) != "none"
        if fault_mask.any():
            fault_idx = np.flatnonzero(fault_mask)
            fig.add_trace(go.Scatter(
                x=t_s[fault_idx],
                y=vals[fault_idx],
                mode="markers",
                name="Ground-Truth Injected Fault [OFFLINE EVAL ONLY]",
                marker=dict(symbol="circle-open", size=10, color=METROLOGY_PALETTE["ground_truth"], line=dict(width=2)),
                hovertemplate="GROUND TRUTH FAULT<br>Type: %{text}<extra></extra>",
                text=view_df.loc[fault_idx, "label_fault_type"].values
            ))

    fig.update_layout(
        title=dict(
            text=f"<b>Time Series: {measurand} [{unit}]</b>",
            x=0.03
        ),
        xaxis_title="Elapsed Time (seconds)",
        yaxis_title=f"Measured Value ({unit})",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=50, b=40),
        height=400,
        hovermode="x unified"
    )
    return fig


def plot_calibration_fit_and_residuals(
    clean_df: pd.DataFrame,
    measurand: str,
    unit: str,
    cal_model: Optional[CalibrationModel]
) -> Tuple[go.Figure, go.Figure]:
    """
    Generate calibration curve (Indicated vs Reference) and residual diagnostics plot.
    """
    ref_col = f"reference_{measurand}"
    if ref_col not in clean_df.columns or cal_model is None:
        # Fallback empty figures
        fig_cal = go.Figure()
        fig_cal.update_layout(title="No Reference Measurements Available for Calibration Curve", template="plotly_white")
        fig_res = go.Figure()
        fig_res.update_layout(title="No Reference Measurements Available for Residuals", template="plotly_white")
        return fig_cal, fig_res

    duts = clean_df[measurand].to_numpy(dtype=float)
    refs = clean_df[ref_col].to_numpy(dtype=float)
    y_pred = cal_model.predict(duts)
    residuals = y_pred - refs

    # Figure 1: Calibration Curve
    fig_cal = go.Figure()
    span_x = np.linspace(min(duts), max(duts), 100)
    span_y = cal_model.predict(span_x)

    # 1:1 Ideal Line
    fig_cal.add_trace(go.Scatter(
        x=span_x,
        y=span_x,
        mode="lines",
        name="Ideal 1:1 Line",
        line=dict(color=METROLOGY_PALETTE["ideal"], dash="dot", width=1.5)
    ))

    # Fitted Regression Model
    fig_cal.add_trace(go.Scatter(
        x=span_x,
        y=span_y,
        mode="lines",
        name=f"Fitted Model: {cal_model.formula_string}",
        line=dict(color=METROLOGY_PALETTE["fit"], width=2.5)
    ))

    # Observations
    fig_cal.add_trace(go.Scatter(
        x=duts,
        y=refs,
        mode="markers",
        name="Observed Pairs (DUT, Ref)",
        marker=dict(size=7, color="#0f172a", opacity=0.7)
    ))

    fig_cal.update_layout(
        title=dict(
            text=f"<b>Calibration Curve: Indicated vs Reference {measurand}</b> (R² = {cal_model.r_squared:.6f})",
            x=0.03
        ),
        xaxis_title=f"Indicated Sensor Reading ({unit})",
        yaxis_title=f"Reference Standard Value ({unit})",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=50, b=40),
        height=380
    )

    # Figure 2: Residual Diagnostics
    s_res = cal_model.residual_std_dev
    fig_res = go.Figure()
    fig_res.add_trace(go.Scatter(
        x=duts,
        y=residuals,
        mode="markers",
        name="Residuals (e = y_pred - y_ref)",
        marker=dict(size=7, color=METROLOGY_PALETTE["residual"], opacity=0.7)
    ))

    # Zero Line
    fig_res.add_hline(y=0.0, line_dash="solid", line_color="#475569", line_width=1.0)
    # +/- 2 s_res bounds
    fig_res.add_hline(y=2.0 * s_res, line_dash="dash", line_color="#ef4444", annotation_text="+2 s_res", annotation_position="top right")
    fig_res.add_hline(y=-2.0 * s_res, line_dash="dash", line_color="#ef4444", annotation_text="-2 s_res", annotation_position="bottom right")

    fig_res.update_layout(
        title=dict(
            text=f"<b>Residual Diagnostics: Residual vs Indicated Value</b> (s_res = {s_res:.4g} {unit})",
            x=0.03
        ),
        xaxis_title=f"Indicated Value ({unit})",
        yaxis_title=f"Residual Error ({unit})",
        template="plotly_white",
        margin=dict(l=40, r=40, t=50, b=40),
        height=320
    )

    return fig_cal, fig_res


def plot_uncertainty_budget_breakdown(budget: UncertaintyBudget) -> go.Figure:
    """
    Generate horizontal bar chart of GUM uncertainty variance contributions.
    """
    names = [c.name for c in budget.components]
    shares = [c.variance_share_percent for c in budget.components]
    types = [c.uncertainty_type for c in budget.components]
    contribs = [c.uncertainty_contribution for c in budget.components]

    colors = ["#dc2626" if c.name == budget.dominant_component.name else ("#2563eb" if c.uncertainty_type == "A" else "#0891b2") for c in budget.components]

    hover_texts = [
        f"<b>{c.name}</b><br>"
        f"Type: {c.uncertainty_type} ({c.distribution})<br>"
        f"Standard Uncertainty u: {c.standard_uncertainty:.4g} {c.unit}<br>"
        f"Sensitivity c: {c.sensitivity_coefficient:.4g}<br>"
        f"Contribution c·u: {c.uncertainty_contribution:.4g} {budget.measurand_unit}<br>"
        f"Variance Share: <b>{c.variance_share_percent:.1f} %</b>"
        for c in budget.components
    ]

    fig = go.Figure(go.Bar(
        x=shares,
        y=names,
        orientation="h",
        marker_color=colors,
        text=[f"{s:.1f} %" for s in shares],
        textposition="auto",
        hovertext=hover_texts,
        hoverinfo="text"
    ))

    fig.update_layout(
        title=dict(
            text=f"<b>Uncertainty Budget Variance Shares: u_c = {budget.combined_standard_uncertainty:.4g} {budget.measurand_unit}</b>",
            x=0.03
        ),
        xaxis_title="Variance Contribution (%)",
        yaxis=dict(autorange="reversed"),
        template="plotly_white",
        margin=dict(l=180, r=40, t=50, b=40),
        height=320
    )
    return fig


def plot_multi_track_alarms_timeline(
    df: pd.DataFrame,
    detector_alarms: Dict[str, np.ndarray],
    episode_df: pd.DataFrame
) -> go.Figure:
    """
    Generate multi-row comparative alarm timeline across Integrity, Segment, ML GBT, CUSUM, and Hybrid M7.
    """
    t_s = df["elapsed_ms"].to_numpy(dtype=float) / 1000.0 if "elapsed_ms" in df.columns else np.arange(len(df))
    tracks = [
        ("Integrity Rules", detector_alarms.get("integrity", np.zeros(len(df), bool)), "#991b1b"),
        ("Segment Detector (MAD)", detector_alarms.get("segment_mad", np.zeros(len(df), bool)), "#f97316"),
        ("ML GBT Detector", detector_alarms.get("ml_gbt", np.zeros(len(df), bool)), "#8b5cf6"),
        ("Tuned CUSUM", detector_alarms.get("cusum", np.zeros(len(df), bool)), "#3b82f6"),
        ("Hybrid M7 (Fusion)", detector_alarms.get("hybrid_m7", np.zeros(len(df), bool)), "#dc2626")
    ]

    fig = go.Figure()

    for idx, (label, mask, track_color) in enumerate(tracks):
        # Base horizontal line for the track
        y_level = len(tracks) - 1 - idx
        fig.add_trace(go.Scatter(
            x=[min(t_s), max(t_s)],
            y=[y_level, y_level],
            mode="lines",
            line=dict(color="#e2e8f0", width=6),
            hoverinfo="skip",
            showlegend=False
        ))

        # Alarmed segments on this track
        alarm_idx = np.flatnonzero(mask)
        if len(alarm_idx) > 0:
            fig.add_trace(go.Scatter(
                x=t_s[alarm_idx],
                y=[y_level] * len(alarm_idx),
                mode="markers",
                name=label,
                marker=dict(symbol="line-ns", size=16, line=dict(width=3, color=track_color)),
                hovertemplate=f"<b>{label} Active</b><br>Time: %{{x:.2f}} s<extra></extra>"
            ))

    track_labels = [t[0] for t in reversed(tracks)]
    fig.update_layout(
        title=dict(
            text="<b>Multi-Track Comparative Fault Detection Alarms</b>",
            x=0.03
        ),
        xaxis_title="Elapsed Time (seconds)",
        yaxis=dict(
            tickmode="array",
            tickvals=list(range(len(tracks))),
            ticktext=track_labels,
            range=[-0.5, len(tracks) - 0.5]
        ),
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=180, r=40, t=50, b=40),
        height=320
    )
    return fig


def plot_sampling_interval_jitter(df: pd.DataFrame) -> go.Figure:
    """
    Plot sampling interval dt distribution and jitter time series.
    """
    if "elapsed_ms" not in df.columns or len(df) < 3:
        fig = go.Figure()
        fig.update_layout(title="Insufficient Sampling Data for Jitter Diagnostics")
        return fig

    t_s = df["elapsed_ms"].to_numpy(dtype=float) / 1000.0
    dt_s = np.diff(t_s)
    nominal_dt = float(np.median(dt_s))
    jitter_ms = (dt_s - nominal_dt) * 1000.0

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=t_s[1:],
        y=jitter_ms,
        mode="lines+markers",
        name="Sampling Jitter (ms)",
        line=dict(color="#0284c7", width=1.5),
        marker=dict(size=4)
    ))
    fig.add_hline(y=0.0, line_dash="solid", line_color="#64748b", line_width=1.0)

    fig.update_layout(
        title=dict(
            text=f"<b>Sampling Period Jitter: Nominal = {nominal_dt*1000:.1f} ms</b>",
            x=0.03
        ),
        xaxis_title="Elapsed Time (seconds)",
        yaxis_title="Jitter dt - dt_nom (ms)",
        template="plotly_white",
        margin=dict(l=40, r=40, t=50, b=40),
        height=280
    )
    return fig
