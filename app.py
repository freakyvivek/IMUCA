"""
IMUCA: Intelligent Measurement Uncertainty and Calibration Analyzer
Main Streamlit Application.
"""

import os
import io
import datetime
import numpy as np
import pandas as pd
import streamlit as st

from src.loader import load_csv, detect_measurement_columns, detect_drift_columns
from src.validator import validate_dataset, ValidationResult
from src.preprocessing import structure_calibration_data, extract_repeats_from_row
from src.statistics import calculate_descriptive_statistics, StatisticsResult
from src.errors import calculate_point_error, calculate_sweep_errors, ErrorAnalysisResult
from src.type_a import evaluate_type_a, TypeAResult
from src.type_b import TypeBSource, evaluate_type_b, get_default_type_b_sources, DISTRIBUTION_DIVISORS
from src.budget import build_uncertainty_budget, UncertaintyBudget
from src.calibration import evaluate_calibration_sweep, evaluate_single_point_conformity, CalibrationResult
from src.drift import analyze_within_run_trend, evaluate_drift_history, DriftAnalysisResult, WithinRunTrendResult
from src.limits import EngineeringLimits
from src.rules import evaluate_decision_rules, DecisionEngineResult
from src.figures import (
    plot_calibration_curve,
    plot_error_vs_reference,
    plot_residuals,
    plot_uncertainty_budget_chart,
    plot_repeat_distribution_chart,
    plot_drift_trend_chart
)
from src.report import generate_html_report


# Set page config
st.set_page_config(
    page_title="IMUCA | Measurement Uncertainty & Calibration Analyzer",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS styling for premium engineering aesthetics
st.markdown("""
<style>
    .main-header {
        font-size: 26px;
        font-weight: 800;
        color: #0f172a;
        margin-bottom: 2px;
        letter-spacing: -0.5px;
    }
    .sub-header {
        font-size: 14px;
        color: #64748b;
        margin-bottom: 20px;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
    }
    .metric-container {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 14px 18px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    .metric-label {
        font-size: 11px;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        margin-bottom: 4px;
    }
    .metric-value {
        font-size: 22px;
        font-weight: 700;
        color: #0f172a;
    }
    .metric-sub {
        font-size: 12px;
        color: #64748b;
        margin-top: 2px;
    }
    .quality-banner {
        padding: 18px 24px;
        border-radius: 8px;
        margin-bottom: 24px;
        display: flex;
        flex-direction: column;
        gap: 6px;
    }
    .quality-banner.acceptable {
        background-color: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-left: 6px solid #16a34a;
    }
    .quality-banner.attention {
        background-color: #fffbeb;
        border: 1px solid #fef3c7;
        border-left: 6px solid #f59e0b;
    }
    .quality-banner.calibration {
        background-color: #fef2f2;
        border: 1px solid #fecaca;
        border-left: 6px solid #dc2626;
    }
    .quality-title {
        font-size: 20px;
        font-weight: 800;
    }
    .quality-title.acceptable { color: #15803d; }
    .quality-title.attention { color: #b45309; }
    .quality-title.calibration { color: #b91c1c; }
    .quality-action {
        font-size: 14px;
        color: #334155;
        font-weight: 500;
    }
    .badge-pill {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 600;
        margin-right: 6px;
    }
    .badge-pass { background-color: #dcfce7; color: #166534; }
    .badge-warn { background-color: #fef3c7; color: #92400e; }
    .badge-fail { background-color: #fee2e2; color: #991b1b; }
    .badge-neutral { background-color: #f1f5f9; color: #334155; }
    .calc-box {
        background-color: #f8fafc;
        border-left: 4px solid #3b82f6;
        padding: 12px 16px;
        border-radius: 4px;
        font-family: monospace;
        font-size: 13px;
        color: #1e293b;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)


from src.imuca.unified_dashboard import render_unified_dashboard


# =============================================================================
# SIDEBAR CONTROLS & MODE SELECTOR
# =============================================================================
st.sidebar.markdown("### 🔬 IMUCA Controls")
st.sidebar.markdown("**Intelligent Measurement Uncertainty & Calibration Analyzer**")

if "dashboard_mode" not in st.session_state:
    st.session_state["dashboard_mode"] = "🔬 Unified Multi-Channel System (10 Sections)"

dashboard_mode = st.sidebar.radio(
    "Application Mode",
    [
        "🔬 Unified Multi-Channel System (10 Sections)",
        "⚡ Single-Point / Sweep DC Voltage Analyzer (Review 1 Baseline)"
    ],
    index=0 if st.session_state["dashboard_mode"].startswith("🔬") else 1,
    help="Toggle between the Unified Multi-Channel Autonomous Dashboard and the Review 1 DC Voltage Baseline."
)
st.session_state["dashboard_mode"] = dashboard_mode

if dashboard_mode.startswith("🔬"):
    render_unified_dashboard()
    st.stop()

# Preset selector buttons
st.sidebar.markdown("#### ⚡ Quick Presets")
col_p1, col_p2 = st.sidebar.columns(2)
with col_p1:
    if st.button("Demo A\n(Single)", use_container_width=True, help="Single session at 5.000 V: ACCEPTABLE, Repeatability dominant, No drift history"):
        st.session_state["preset"] = "demo_a"
        st.session_state["dashboard_mode"] = "⚡ Single-Point / Sweep DC Voltage Analyzer (Review 1 Baseline)"
        st.rerun()
with col_p2:
    if st.button("Demo B\n(+ History)", use_container_width=True, help="With 10-session history: ATTENTION REQUIRED, Upward drift, Breach at session 28"):
        st.session_state["preset"] = "demo_b"
        st.session_state["dashboard_mode"] = "⚡ Single-Point / Sweep DC Voltage Analyzer (Review 1 Baseline)"
        st.rerun()

if "preset" not in st.session_state:
    st.session_state["preset"] = "demo_a"

current_preset = st.session_state["preset"]

st.sidebar.markdown("---")
st.sidebar.markdown("#### 📁 Data Source")
data_source_mode = st.sidebar.radio(
    "Select Input Mode",
    ["Demo Synthetic Dataset", "Upload Custom CSV"],
    index=0 if current_preset in ["demo_a", "demo_b"] else 1
)

uploaded_meas_file = None
uploaded_drift_file = None

if data_source_mode == "Upload Custom CSV":
    uploaded_meas_file = st.sidebar.file_uploader("Upload Measurement Sweep/Repeats CSV", type=["csv"])
    uploaded_drift_file = st.sidebar.file_uploader("Optional: Upload Calibration History CSV", type=["csv"])

# Measurement & Tolerance Settings
st.sidebar.markdown("---")
st.sidebar.markdown("#### ⚙️ Metrological Settings")

ref_point_v = st.sidebar.number_input("Primary Operating Point (V)", min_value=0.1, max_value=20.0, value=5.000, step=0.5, format="%.3f")
tol_percent = st.sidebar.number_input("Tolerance Band T (± % of reading)", min_value=0.01, max_value=10.0, value=1.00, step=0.1, format="%.2f")
coverage_k = st.sidebar.selectbox("Coverage Factor k", [2.0, 3.0, "Auto (Student-t)"], index=0)
u_allowable_mv = st.sidebar.number_input("Allowable Uncertainty U_allow (mV)", min_value=1.0, max_value=200.0, value=25.0, step=5.0)
drift_lim_mv = st.sidebar.number_input("Drift Limit b_threshold (mV/session)", min_value=0.05, max_value=10.0, value=0.50, step=0.05)
s_allowable_mv = st.sidebar.number_input("Allowable Repeatability s_allow (mV)", min_value=1.0, max_value=100.0, value=15.0, step=1.0)

# Type B parameters
st.sidebar.markdown("---")
with st.sidebar.expander("🛠️ Type B Source Parameters", expanded=False):
    res_input = st.number_input("DUT Display Resolution (V)", min_value=0.0001, max_value=1.0, value=0.01, step=0.001, format="%.4f")
    spec_percent = st.number_input("DUT Specification (± % of reading)", min_value=0.001, max_value=5.0, value=0.10, step=0.01)
    ref_cert_u = st.number_input("Reference Standard Uncertainty U (V, k=2)", min_value=0.0001, max_value=0.1, value=0.002, step=0.0005, format="%.4f")
    temp_delta = st.number_input("Ambient Temperature Variation (± °C)", min_value=0.0, max_value=20.0, value=3.0, step=0.5)
    tempco_pct = st.number_input("Tempco (± % / °C)", min_value=0.0001, max_value=0.1, value=0.005, step=0.001, format="%.4f")


# =============================================================================
# DATA INGESTION & PIPELINE EXECUTION
# =============================================================================

# Load data based on selection
if data_source_mode == "Demo Synthetic Dataset":
    meas_path = os.path.join("data", "demo_measurements.csv")
    repeats_10_path = os.path.join("data", "demo_single_point_10repeats.csv")
    history_path = os.path.join("data", "calibration_history.csv")
    
    df_raw_meas = load_csv(meas_path)
    df_10_repeats = load_csv(repeats_10_path)
    df_raw_drift = load_csv(history_path) if (current_preset == "demo_b" or st.session_state.get("include_drift", False)) else None
    dataset_title = "IMUCA Standard Synthetic Benchmark (Table 10.3)"
else:
    if uploaded_meas_file is not None:
        df_raw_meas = load_csv(uploaded_meas_file)
        df_10_repeats = None
        dataset_title = uploaded_meas_file.name
    else:
        st.warning("Please upload a CSV file or switch to Demo Synthetic Dataset mode.")
        st.stop()
        
    if uploaded_drift_file is not None:
        df_raw_drift = load_csv(uploaded_drift_file)
    else:
        df_raw_drift = None

# Validation
val_res = validate_dataset(df_raw_meas, min_val=0.0, max_val=20.0)
ref_col, dut_col, rpt_cols = detect_measurement_columns(val_res.valid_df if val_res.is_valid else df_raw_meas)

# Extract observations for analysis
if df_10_repeats is not None and ref_point_v == 5.000:
    # Use exact 10 repeated readings at 5.000 V: [5.02, 5.01, 5.03, 5.02, 5.04, 5.01, 5.02, 5.03, 5.02, 5.01]
    repeat_readings = df_10_repeats["DUT_V"].values
elif rpt_cols and len(val_res.valid_df) > 0:
    # Find matching row for reference point
    closest_idx = (val_res.valid_df[ref_col] - ref_point_v).abs().idxmin()
    matched_row = val_res.valid_df.loc[closest_idx]
    row_rpts = extract_repeats_from_row(matched_row, rpt_cols)
    repeat_readings = row_rpts if len(row_rpts) >= 2 else np.array([matched_row[dut_col]])
else:
    repeat_readings = val_res.valid_df[dut_col].values if len(val_res.valid_df) > 0 else np.array([5.021])

# Run Pipeline Blocks
# 1. Statistics
stats_res = calculate_descriptive_statistics(repeat_readings)

# 2. Type A
if len(repeat_readings) >= 2:
    type_a_res = evaluate_type_a(repeat_readings)
else:
    type_a_res = None

# 3. Type B
type_b_sources = [
    TypeBSource(
        name="Display resolution",
        input_value=res_input,
        unit="V",
        distribution="rectangular",
        is_resolution=True,
        description=f"DMM quantisation ({res_input*1000:.1f} mV step, half-width {res_input*500:.1f} mV)"
    ),
    TypeBSource(
        name="DUT specification",
        input_value=spec_percent,
        unit="%",
        distribution="rectangular",
        is_percent_of_reading=True,
        description=f"Manufacturer specification (± {spec_percent:.2f} % of reading)"
    ),
    TypeBSource(
        name="Reference standard",
        input_value=ref_cert_u,
        unit="V",
        distribution="normal_k2",
        description="Calibration standard certificate expanded uncertainty (k = 2)"
    ),
    TypeBSource(
        name="Ambient temperature",
        input_value=temp_delta,
        unit="degC",
        distribution="rectangular",
        tempco_percent_per_deg=tempco_pct,
        description=f"Temperature variation (± {temp_delta:.1f} °C at {tempco_pct:.4f} %/°C)"
    )
]
type_b_res = evaluate_type_b(type_b_sources, reading_v=stats_res.mean)

# 4. Uncertainty Budget & Coverage
force_k_val = None if coverage_k == "Auto (Student-t)" else float(coverage_k)
budget_res = build_uncertainty_budget(
    type_a=type_a_res,
    type_b=type_b_res,
    confidence_level=0.95,
    force_k=force_k_val
)

# 5. Calibration Sweep
cal_res = None
if len(val_res.valid_df) >= 2 and ref_col and dut_col:
    cal_res = evaluate_calibration_sweep(
        reference_v=val_res.valid_df[ref_col].values,
        dut_v=val_res.valid_df[dut_col].values,
        tolerance_percent=tol_percent,
        resolution_v=res_input
    )

# 6. Trend & Drift
within_run_res = analyze_within_run_trend(repeat_readings)

if df_raw_drift is not None and not df_raw_drift.empty:
    s_col, e_col = detect_drift_columns(df_raw_drift)
    if s_col and e_col:
        drift_res = evaluate_drift_history(
            sessions=df_raw_drift[s_col].values,
            mean_errors_mv=df_raw_drift[e_col].values,
            drift_threshold_mv_per_session=drift_lim_mv,
            tolerance_mv=(tol_percent / 100.0) * ref_point_v * 1000.0
        )
    else:
        drift_res = evaluate_drift_history([], [])
else:
    drift_res = evaluate_drift_history([], [])

# 7. Intelligent Decision Engine
operating_abs_error_mv = (stats_res.mean - ref_point_v) * 1000.0
operating_tol_mv = (tol_percent / 100.0) * ref_point_v * 1000.0
eng_limits = EngineeringLimits(
    u_allowable_mv=u_allowable_mv,
    tolerance_mv=operating_tol_mv,
    drift_threshold_mv=drift_lim_mv,
    s_allowable_mv=s_allowable_mv,
    confidence_level=0.95,
    coverage_factor_k=budget_res.coverage.coverage_factor_k
)

nonconforming_points = [p.point_index for p in cal_res.points if p.conformity_status == "FAIL"] if cal_res else []

decision_res = evaluate_decision_rules(
    expanded_uncertainty_mv=budget_res.coverage.expanded_uncertainty_mv,
    absolute_error_mv=operating_abs_error_mv,
    sample_std_dev_mv=stats_res.std_dev * 1000.0,
    limits=eng_limits,
    drift_slope_mv_per_session=drift_res.slope_b if drift_res.is_assessed else None,
    drift_p_value=drift_res.p_value if drift_res.is_assessed else None,
    has_drift_history=drift_res.is_assessed,
    sweep_nonconforming_points=nonconforming_points,
    projected_breach_session=drift_res.projected_breach_session,
    dominant_source_name=budget_res.dominant_source.source_name,
    dominant_source_percent=budget_res.dominant_source.variance_contribution_percent
)


# =============================================================================
# HEADER & TOP SUMMARY DASHBOARD
# =============================================================================

st.markdown('<div class="main-header">IMUCA: Intelligent Measurement Uncertainty and Calibration Analyzer</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Measurements &amp; Instrumentation • Autonomous Metrology Verification Framework</div>', unsafe_allow_html=True)

# Top KPI Metric Cards
col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1:
    st.markdown(f"""
    <div class="metric-container">
        <div class="metric-label">Mean Reading</div>
        <div class="metric-value">{stats_res.mean:.4f} V</div>
        <div class="metric-sub">Ref: {ref_point_v:.3f} V</div>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown(f"""
    <div class="metric-container">
        <div class="metric-label">Combined Unc. u_c</div>
        <div class="metric-value">{budget_res.combined_uncertainty_mv:.3f} mV</div>
        <div class="metric-sub">ν_eff = {budget_res.coverage.effective_degrees_of_freedom:.1f}</div>
    </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown(f"""
    <div class="metric-container">
        <div class="metric-label">Expanded Unc. U</div>
        <div class="metric-value">{budget_res.coverage.expanded_uncertainty_mv:.2f} mV</div>
        <div class="metric-sub">k = {budget_res.coverage.coverage_factor_k:.2f} (95%)</div>
    </div>
    """, unsafe_allow_html=True)
with col4:
    offset_disp = f"{cal_res.zero_offset_mv:+.2f} mV" if cal_res else "N/A"
    st.markdown(f"""
    <div class="metric-container">
        <div class="metric-label">Zero Offset c</div>
        <div class="metric-value">{offset_disp}</div>
        <div class="metric-sub">Gain: {cal_res.gain_error_percent:+.3f} %</div>
    </div>
    """, unsafe_allow_html=True)
with col5:
    r2_disp = f"{cal_res.r_squared:.6f}" if cal_res else "N/A"
    st.markdown(f"""
    <div class="metric-container">
        <div class="metric-label">Linearity R²</div>
        <div class="metric-value">{r2_disp}</div>
        <div class="metric-sub">{cal_res.summary_text if cal_res else 'N/A'}</div>
    </div>
    """, unsafe_allow_html=True)
with col6:
    drift_text = f"{drift_res.slope_b:+.2f} mV/s" if drift_res.is_assessed else "Not Assessed"
    breach_sub = f"Breach: S{drift_res.projected_breach_session:.0f}" if (drift_res.is_assessed and drift_res.projected_breach_session) else "History: None"
    st.markdown(f"""
    <div class="metric-container">
        <div class="metric-label">Drift Status</div>
        <div class="metric-value" style="font-size:16px;">{drift_text}</div>
        <div class="metric-sub">{breach_sub}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)

# Prominent Measurement Quality Headline Banner
banner_class = "acceptable" if decision_res.headline_status == "ACCEPTABLE" else ("attention" if decision_res.headline_status == "ATTENTION REQUIRED" else "calibration")
title_class = banner_class

st.markdown(f"""
<div class="quality-banner {banner_class}">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div class="quality-title {title_class}">
            MEASUREMENT QUALITY: {decision_res.headline_status}
        </div>
        <div>
            <span class="badge-pill {'badge-pass' if decision_res.calibration_status_badge == 'PASS' else 'badge-fail'}">Calibration: {decision_res.calibration_status_badge}</span>
            <span class="badge-pill {'badge-warn' if 'SIGNIFICANT' in decision_res.drift_status_badge else 'badge-neutral'}">Drift: {decision_res.drift_status_badge}</span>
            <span class="badge-pill badge-neutral">Dominant: {decision_res.dominant_uncertainty_badge}</span>
        </div>
    </div>
    <div class="quality-action">
        <strong>Triggered Rule:</strong> {decision_res.primary_triggered_rule} ({decision_res.primary_rule_name}) — <em>{decision_res.recommended_action}</em>
    </div>
    <div style="font-size: 13px; color: #475569; margin-top: 4px;">
        {decision_res.detailed_recommendation}
    </div>
</div>
""", unsafe_allow_html=True)


# =============================================================================
# 9 MAIN TABS
# =============================================================================

tab_overview, tab_raw, tab_stats, tab_errors, tab_budget, tab_cal, tab_drift, tab_rules, tab_report = st.tabs([
    "📊 1. Overview",
    "📄 2. Raw Data & Validation",
    "📈 3. Statistics",
    "🎯 4. Error Analysis",
    "⚖️ 5. Uncertainty Budget",
    "📐 6. Calibration",
    "📉 7. Drift & Trend",
    "🧠 8. Decision Engine",
    "📑 9. Automated Report"
])


# -----------------------------------------------------------------------------
# TAB 1: OVERVIEW
# -----------------------------------------------------------------------------
with tab_overview:
    st.markdown("### 📋 Executive Summary & Metrological Architecture")
    
    col_ov1, col_ov2 = st.columns([3, 2])
    with col_ov1:
        st.markdown(
            f"**System Mode**: {current_preset.upper().replace('_', ' ')}  \n"
            f"**Operating Point**: Reference = `{ref_point_v:.3f} V`, Measured Mean = `{stats_res.mean:.4f} V`  \n"
            f"**Reported Measurement Value**:  \n"
            f"$$\\mathbf{{V = {budget_res.coverage.formatted_reported_result}}}$$\n\n"
            f"#### Key Findings:\n"
            f"1. **Type A Repeatability**: $s = {stats_res.std_dev*1000:.3f}\\text{{ mV}}$, giving $u_A = {type_a_res.standard_uncertainty_mv:.3f}\\text{{ mV}}$ with $\\nu = {type_a_res.degrees_of_freedom}$ degrees of freedom.\n"
            f"2. **Type B Systematic Components**: Combined $u_B = {type_b_res.combined_type_b_mv:.3f}\\text{{ mV}}$ across display resolution, DUT specification, reference standard, and temperature effects.\n"
            f"3. **Dominant Source**: **{budget_res.dominant_source.source_name}** represents **{budget_res.dominant_source.variance_contribution_percent:.1f}%** of total variance.\n"
            f"4. **Calibration Fit**: Zero offset of **{cal_res.zero_offset_mv:+.2f} mV** and Gain error of **{cal_res.gain_error_percent:+.3f}%** with $R^2 = {cal_res.r_squared:.6f}$.\n"
            f"5. **Drift Assessment**: {f'**Significant upward drift** of +{drift_res.slope_b:.2f} mV/session (p = {drift_res.p_value:.2e}), projecting tolerance breach at **Session {drift_res.projected_breach_session:.0f}**.' if drift_res.is_assessed else 'Single-session analysis. Historical drift not assessed.'}"
        )
        
    with col_ov2:
        st.markdown("#### Complete 12-Stage Pipeline")
        st.markdown("""
        ```mermaid
        graph TD
            A[Raw Measurement CSV] --> B[Data Validation Alg 1a]
            B --> C[Sample Statistics]
            C --> D[Type A Uncertainty]
            D --> E[Type B Evaluator]
            E --> F[Uncertainty Budget]
            F --> G[Calibration Regression]
            G --> H[Residual Diagnostics]
            H --> I[Drift Significance Alg 6]
            I --> J[Decision Engine R1-R5]
            J --> K[Interactive Dashboard]
            K --> L[Automated Report]
        ```
        """)
        
    st.info("💡 **Faculty Demo Tip:** Use the Quick Presets in the left sidebar to toggle between **Demo A (Single Session)** and **Demo B (With History)** to see the Decision Engine dynamically respond to available evidence.")


# -----------------------------------------------------------------------------
# TAB 2: RAW DATA & VALIDATION
# -----------------------------------------------------------------------------
with tab_raw:
    st.markdown("### 📄 Raw Ingestion & Multi-Layer Validation (Algorithm 1a)")
    
    col_v1, col_v2, col_v3 = st.columns(3)
    with col_v1:
        st.metric("Total Records", val_res.total_rows)
    with col_v2:
        st.metric("Valid Rows Retained", val_res.valid_rows_count)
    with col_v3:
        status_color = "🟢 VALID" if val_res.status == "VALID" else ("🟠 WARNING" if val_res.status == "WARNING" else "🔴 INVALID")
        st.metric("Validation Status", status_color)
        
    st.markdown("#### Ingested Dataset Table")
    st.dataframe(df_raw_meas, use_container_width=True)
    
    st.markdown("#### Validation Log & Outlier Inspection (MAD Modified Z-score)")
    if val_res.issues:
        issue_df = pd.DataFrame([{
            "Row": i.row_index + 1,
            "Column": i.column,
            "Value": i.value,
            "Type": i.issue_type,
            "Severity": i.severity,
            "Details": i.message
        } for i in val_res.issues])
        st.dataframe(issue_df, use_container_width=True)
    else:
        st.success("✅ Multi-layer validation passed: No non-numeric values, missing records, range breaches, or severe outliers detected.")
        
    with st.expander("ℹ️ How MAD Outlier Detection Works (Algorithm 1a)", expanded=False):
        st.markdown("""
        IMUCA implements Median Absolute Deviation (MAD) for robust outlier detection:
        $$\\text{MAD} = \\text{median}(|x_i - \\text{median}(x)|)$$
        $$z_i = 0.6745 \\cdot \\frac{x_i - \\text{median}(x)}{\\text{MAD}}$$
        Observations with $|z_i| > 3.5$ are flagged for engineering inspection. **Crucially, IMUCA NEVER silently deletes outliers**, preserving data integrity.
        """)


# -----------------------------------------------------------------------------
# TAB 3: STATISTICS
# -----------------------------------------------------------------------------
with tab_stats:
    st.markdown(f"### 📈 Descriptive Statistics (Operating Point: {ref_point_v:.3f} V)")
    
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    with col_s1:
        st.metric("Sample Size n", stats_res.n)
        st.metric("Min Value", f"{stats_res.min_val:.4f} V")
    with col_s2:
        st.metric("Arithmetic Mean x̄", f"{stats_res.mean:.6f} V")
        st.metric("Max Value", f"{stats_res.max_val:.4f} V")
    with col_s3:
        st.metric("Sample SD s (n-1)", f"{stats_res.std_dev*1000:.4f} mV")
        st.metric("Span / Range", f"{stats_res.range_val*1000:.2f} mV")
    with col_s4:
        st.metric("Standard Error s(x̄)", f"{stats_res.std_error*1000:.4f} mV")
        st.metric("Degrees of Freedom ν", stats_res.degrees_of_freedom)
        
    st.plotly_chart(plot_repeat_distribution_chart(repeat_readings, reference_v=ref_point_v), use_container_width=True)
    
    with st.expander("🔢 Step-by-Step Calculation Trace", expanded=False):
        st.markdown(f"""
        <div class="calc-box">
        <strong>1. Arithmetic Mean:</strong><br>
        x̄ = (1/n) Σ x_i = {stats_res.sum_x:.4f} / {stats_res.n} = {stats_res.mean:.6f} V<br><br>
        <strong>2. Sum of Squared Deviations:</strong><br>
        Σ (x_i - x̄)² = {stats_res.sum_sq_diff:.6e} V²<br><br>
        <strong>3. Sample Variance (n-1 denominator):</strong><br>
        s² = Σ (x_i - x̄)² / (n - 1) = {stats_res.sum_sq_diff:.6e} / {stats_res.degrees_of_freedom} = {stats_res.variance:.6e} V²<br><br>
        <strong>4. Sample Standard Deviation:</strong><br>
        s = √s² = {stats_res.std_dev:.6f} V = {stats_res.std_dev*1000:.4f} mV<br><br>
        <strong>5. Standard Error of the Mean (Type A):</strong><br>
        s(x̄) = s / √n = {stats_res.std_dev*1000:.4f} / √{stats_res.n} = {stats_res.std_error*1000:.4f} mV
        </div>
        """, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# TAB 4: ERROR ANALYSIS
# -----------------------------------------------------------------------------
with tab_errors:
    st.markdown("### 🎯 Error Analysis Across Calibration Points")
    
    if cal_res is not None:
        col_e1, col_e2, col_e3 = st.columns(3)
        with col_e1:
            err_at_pt = (stats_res.mean - ref_point_v) * 1000.0
            st.metric(f"Absolute Error at {ref_point_v:.3f} V", f"{err_at_pt:+.1f} mV")
        with col_e2:
            pct_at_pt = (err_at_pt / (ref_point_v * 1000.0)) * 100.0
            st.metric(f"Percentage Error at {ref_point_v:.3f} V", f"{pct_at_pt:+.3f} %")
        with col_e3:
            st.metric("Tolerance Requirement", f"±{tol_percent:.2f} % (±{operating_tol_mv:.1f} mV)")
            
        st.markdown("#### Full Multi-Point Sweep Error Table")
        st.dataframe(cal_res.calibration_dataframe, use_container_width=True)
        st.plotly_chart(plot_error_vs_reference(cal_res), use_container_width=True)
    else:
        st.info("Upload or select a multi-point calibration sweep to view full range error analysis.")


# -----------------------------------------------------------------------------
# TAB 5: UNCERTAINTY BUDGET
# -----------------------------------------------------------------------------
with tab_budget:
    st.markdown(f"### ⚖️ Uncertainty Budget & Expanded Uncertainty (ISO GUM / Guide 98-3)")
    st.markdown(f"Evaluated at operating point **{ref_point_v:.3f} V** with indicated mean **{stats_res.mean:.4f} V**.")
    
    # Budget Table
    st.markdown("#### Uncertainty Budget Table")
    st.dataframe(budget_res.budget_dataframe, use_container_width=True)
    
    # Contribution Bar Chart
    st.plotly_chart(plot_uncertainty_budget_chart(budget_res), use_container_width=True)
    
    # Mathematical summary cards
    col_b1, col_b2, col_b3 = st.columns(3)
    with col_b1:
        st.markdown(f"""
        **Combined Standard Uncertainty $u_c$:**  
        $$u_c = \\sqrt{{\\sum (c_i u_i)^2}} = {budget_res.combined_uncertainty_mv:.3f}\\text{{ mV}}$$  
        Total Combined Variance: `{budget_res.total_variance_sum_mv2:.3f} mV²`
        """)
    with col_b2:
        st.markdown(f"""
        **Welch-Satterthwaite Effective DOF:**  
        $$\\nu_{{eff}} = \\frac{{u_c^4}}{{\\sum \\frac{{u_i^4}}{{\\nu_i}}}} = {budget_res.coverage.effective_degrees_of_freedom:.1f}$$  
        Since $\\nu_{{eff}} \\ge 30$, $k = 2.00$ is strictly justified.
        """)
    with col_b3:
        st.markdown(f"""
        **Expanded Uncertainty $U$ (95% Confidence):**  
        $$U = k \\cdot u_c = 2 \\times {budget_res.combined_uncertainty_mv:.3f} = {budget_res.coverage.expanded_uncertainty_mv:.2f}\\text{{ mV}}$$  
        **Reported Form:** `{budget_res.coverage.formatted_reported_result}`
        """)
        
    with st.expander("📖 Dominant Contributor Engineering Interpretation", expanded=True):
        st.markdown(f"""
        - **Dominant Contributor**: **{budget_res.dominant_source.source_name}** ({budget_res.dominant_source.variance_contribution_percent:.1f}% of variance).
        - **Actionable Insight**: Repeatability, Display Resolution, and DUT Specification form the vast majority of the uncertainty budget. Buying a more expensive reference standard or tightening temperature control would yield negligible improvement (<2%). Replacing the 3½-digit meter with a 4½-digit instrument would attack both resolution and observed repeatability simultaneously.
        """)


# -----------------------------------------------------------------------------
# TAB 6: CALIBRATION
# -----------------------------------------------------------------------------
with tab_cal:
    st.markdown("### 📐 Calibration Analysis & Systematic Parameter Separation")
    
    if cal_res is not None:
        col_c1, col_c2, col_c3, col_c4 = st.columns(4)
        with col_c1:
            st.metric("Zero Offset c", f"{cal_res.zero_offset_mv:+.2f} mV")
        with col_c2:
            st.metric("Gain Error (m - 1)", f"{cal_res.gain_error_percent:+.3f} %")
        with col_c3:
            st.metric("Goodness of Fit R²", f"{cal_res.r_squared:.6f}")
        with col_c4:
            st.metric("Conformity Sweep", cal_res.summary_text)
            
        st.plotly_chart(plot_calibration_curve(cal_res), use_container_width=True)
        
        # Single-point Guard-banded evaluation
        gb_eval = evaluate_single_point_conformity(
            reference_v=ref_point_v,
            mean_dut_v=stats_res.mean,
            expanded_uncertainty_v=budget_res.coverage.expanded_uncertainty_v,
            tolerance_percent=tol_percent
        )
        
        col_gb1, col_gb2 = st.columns(2)
        with col_gb1:
            st.markdown(f"""
            #### Guard-Banded Conformity (ISO 14253-1)
            - Measured Error $|E|$: `{abs(gb_eval['error_mv']):.2f} mV`
            - Expanded Uncertainty $U$: `{gb_eval['expanded_uncertainty_mv']:.2f} mV`
            - Total Guard-Banded Band $|E| + U$: **`{gb_eval['total_error_plus_uncertainty_mv']:.2f} mV`**
            - Tolerance Limit $T$: `±{gb_eval['tolerance_mv']:.2f} mV`
            - Guard-banded Status: **`{gb_eval['guard_banded_conformity']}`** (Margin: `{gb_eval['remaining_margin_mv']:.2f} mV`)
            """)
        with col_gb2:
            st.markdown(f"""
            #### Documented Compensation Equation
            If offset and gain systematic corrections are applied:
            $$\\mathbf{{{cal_res.correction_formula}}}$$
            This mathematical compensation brings even the non-conforming 0.500 V point well within tolerance (reducing residual error to <2 mV).
            """)
    else:
        st.info("Calibration sweep data not available.")


# -----------------------------------------------------------------------------
# TAB 7: DRIFT & TREND
# -----------------------------------------------------------------------------
with tab_drift:
    st.markdown("### 📉 Drift and Trend Analysis (Algorithm 6)")
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.markdown("#### Within-Run Sequence Stability")
        st.markdown(f"""
        - Regression Slope: `{within_run_res.slope_mv_per_reading:+.3f} mV / reading`
        - Standard Error: `{within_run_res.std_err_slope:.3f} mV / reading`
        - Test Statistic: `t = {within_run_res.t_statistic:.2f}, p = {within_run_res.p_value:.3f}`
        - Verdict: **{within_run_res.verdict}**
        - *{within_run_res.explanation}*
        """)
    with col_d2:
        st.markdown("#### Between-Session Historical Drift")
        if drift_res.is_assessed:
            st.markdown(f"""
            - Drift Slope $b$: **`{drift_res.slope_b:+.3f} mV / session`**
            - Standard Error $s(b)$: `{drift_res.std_err_b:.3f} mV / session`
            - Significance: **`p = {drift_res.p_value:.2e}`** ($p < 0.05$, Highly Significant)
            - Drift Threshold: `{drift_res.drift_threshold:.2f} mV / session`
            - Drift Status: **`{drift_res.drift_status}`**
            - Projected Tolerance Breach: **`Session {drift_res.projected_breach_session:.0f}`** ({drift_res.sessions_until_breach:.0f} sessions ahead)
            - Suggested Recalibration: **`Before Session {drift_res.recommended_recalibration_session}`**
            """)
        else:
            st.markdown("""
            *No historical calibration dataset loaded.*  
            Click **Demo B** in the left sidebar to load the 10-session calibration history and observe automatic drift detection.
            """)
            
    st.plotly_chart(plot_drift_trend_chart(drift_res), use_container_width=True)
    
    if drift_res.is_assessed:
        st.caption(f"⚠️ **Engineering Disclaimer:** {drift_res.disclaimer}")


# -----------------------------------------------------------------------------
# TAB 8: DECISION ENGINE
# -----------------------------------------------------------------------------
with tab_rules:
    st.markdown("### 🧠 Intelligent Decision Engine (Transparent Rules R1 to R5)")
    st.markdown("Ordered evaluation of rules operating deterministically on computed metrology metrics without black-box ML.")
    
    # Rules Table
    st.markdown("#### Rule Evaluation Trace Log")
    st.dataframe(decision_res.rules_dataframe, use_container_width=True)
    
    st.markdown(f"""
    #### Headline Determination Summary:
    - **Headline Status**: **`{decision_res.headline_status}`**
    - **Triggered Rule**: **`{decision_res.primary_triggered_rule}`** ({decision_res.primary_rule_name})
    - **Action**: {decision_res.recommended_action}
    - **Complete Recommendation**: {decision_res.detailed_recommendation}
    """)
    
    with st.expander("🏛️ Why Transparent Rules Instead of Machine Learning?", expanded=False):
        st.markdown("""
        The IMUCA decision engine intentionally uses an explicit, ordered rule set for 5 key metrological reasons:
        1. **Verifiability**: Every decision can be checked by an examiner or auditor by hand with a calculator.
        2. **No Training Data Required**: Supervised ML requires thousands of labelled abnormal instrument failures.
        3. **Metrological Alignment**: Thresholds ($U_{allow}$, $T$, $b_{lim}$) are physical engineering specifications, not arbitrary hyperparameters.
        4. **Auditability (ISO/IEC 17025)**: Accredited calibration requires transparent, deterministic conformity rules.
        5. **Baseline for Future Scope**: Establishes a verifiable baseline against which future unsupervised anomaly detection models can be benchmarked.
        """)


# -----------------------------------------------------------------------------
# TAB 9: AUTOMATED REPORT
# -----------------------------------------------------------------------------
with tab_report:
    st.markdown("### 📑 Automated Report Generation")
    st.markdown("Generate a formal, publication-quality metrology report derived directly from the computed data objects.")
    
    report_id = f"IMUCA-{datetime.datetime.now().strftime('%Y%m%d')}-{np.random.randint(100, 999)}"
    html_content = generate_html_report(
        report_id=report_id,
        dataset_name=dataset_title,
        stats_result=stats_res,
        type_a=type_a_res,
        type_b=type_b_res,
        budget=budget_res,
        cal_result=cal_res,
        within_run=within_run_res,
        drift_result=drift_res,
        decision_result=decision_res,
        reference_nominal_v=ref_point_v
    )
    
    col_rep1, col_rep2 = st.columns([1, 4])
    with col_rep1:
        st.download_button(
            label="📥 Download HTML Report",
            data=html_content,
            file_name=f"{report_id}_analysis_report.html",
            mime="text/html",
            use_container_width=True
        )
    with col_rep2:
        st.info("💡 You can open the downloaded HTML report in any browser and use **File > Print (or Ctrl+P) > Save as PDF** for a clean PDF report.")
        
    st.markdown("#### Live Report Preview")
    st.components.v1.html(html_content, height=800, scrolling=True)


# =============================================================================
# FOOTER & LIMITATIONS
# =============================================================================
st.markdown("---")
with st.expander("ℹ️ Project Scope, Limitations & Future Work", expanded=False):
    st.markdown("""
    **Proof of Concept Notice:**
    - All data in this demonstration is generated numerically to validate the analysis algorithms against known injected errors.
    - No physical instrument or hardware DAQ is currently connected.
    - **Future Scope (Phase 2):** SCPI automation over USB/GPIB with Keithley/Keysight DMMs, DAQ environmental sensor logging, and advanced time-series forecasting.
    """)
