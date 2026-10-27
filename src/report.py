"""
Automated Report Generation Module for IMUCA.
Implements Chapter 17: Structured, high-fidelity engineering report generation in HTML format
with clean typography, print optimization, and complete numerical traceability.
"""

from typing import Optional, Dict, Any, List
import datetime
import html
from src.statistics import StatisticsResult
from src.type_a import TypeAResult
from src.type_b import TypeBResult
from src.budget import UncertaintyBudget
from src.calibration import CalibrationResult
from src.drift import DriftAnalysisResult, WithinRunTrendResult
from src.rules import DecisionEngineResult


def generate_html_report(
    report_id: str,
    dataset_name: str,
    stats_result: StatisticsResult,
    type_a: Optional[TypeAResult],
    type_b: TypeBResult,
    budget: UncertaintyBudget,
    cal_result: Optional[CalibrationResult],
    within_run: Optional[WithinRunTrendResult],
    drift_result: Optional[DriftAnalysisResult],
    decision_result: DecisionEngineResult,
    reference_nominal_v: float = 5.000,
    dut_description: str = "3.5-digit DMM, 20 V range, resolution 0.01 V",
    reference_description: str = "5.000 V standard, U = 0.002 V (k = 2)"
) -> str:
    """
    Generate an HTML report using identical computed objects from the dashboard.
    """
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    # Uncertainty budget table rows
    budget_rows_html = ""
    for b in budget.entries:
        highlight_style = "background-color: #fee2e2; font-weight: bold;" if b.is_dominant else ""
        dom_star = " <span style='color: #dc2626;'>★ DOMINANT</span>" if b.is_dominant else ""
        budget_rows_html += f"""
        <tr style="{highlight_style}">
            <td>{html.escape(b.source_name)}{dom_star}</td>
            <td style="text-align:center;">{b.uncertainty_type}</td>
            <td style="text-align:right;">{b.input_value_mv:.3f}</td>
            <td>{b.distribution_name}</td>
            <td style="text-align:center;">{b.divisor_display}</td>
            <td style="text-align:right;">{b.standard_uncertainty_mv:.3f}</td>
            <td style="text-align:center;">{b.sensitivity_coefficient:.1f}</td>
            <td style="text-align:right;">{b.scaled_uncertainty_mv:.3f}</td>
            <td style="text-align:center;">{b.degrees_of_freedom_display}</td>
            <td style="text-align:right;">{b.variance_contribution_percent:.1f} %</td>
        </tr>
        """
        
    # Calibration sweep rows
    cal_rows_html = ""
    if cal_result is not None:
        for pt in cal_result.points:
            color = "#10b981" if pt.conformity_status == "PASS" else ("#f59e0b" if pt.conformity_status == "MARGINAL" else "#ef4444")
            cal_rows_html += f"""
            <tr>
                <td style="text-align:center;">{pt.point_index}</td>
                <td style="text-align:right;">{pt.reference_v:.3f}</td>
                <td style="text-align:right;">{pt.dut_v:.2f}</td>
                <td style="text-align:right;">{pt.absolute_error_mv:+.1f}</td>
                <td style="text-align:right;">{pt.relative_error*1000:.2f}</td>
                <td style="text-align:right;">{pt.percentage_error:+.3f} %</td>
                <td style="text-align:center; font-weight:bold; color:{color};">{pt.conformity_status}</td>
            </tr>
            """
            
    # Decision rules trace rows
    rules_rows_html = ""
    for r in decision_result.rule_evaluation_records:
        color = "#dc2626" if r.evaluation_status == "TRIGGERED" and r.rule_id != "R5" else ("#16a34a" if r.rule_id == "R5" and r.evaluation_status == "TRIGGERED" else "#64748b")
        rules_rows_html += f"""
        <tr>
            <td style="text-align:center; font-weight:bold;">{r.rule_id}</td>
            <td>{html.escape(r.rule_name)}</td>
            <td><code>{html.escape(r.condition_desc)}</code></td>
            <td>{html.escape(r.computed_value_str)}</td>
            <td>{html.escape(r.limit_value_str)}</td>
            <td style="text-align:center; font-weight:bold; color:{color};">{r.evaluation_status}</td>
        </tr>
        """
        
    # Headline color
    hl_color = "#16a34a" if decision_result.headline_status == "ACCEPTABLE" else ("#d97706" if decision_result.headline_status == "ATTENTION REQUIRED" else "#dc2626")
    
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>IMUCA Analysis Report - {report_id}</title>
    <style>
        body {{
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;
            color: #1e293b;
            background-color: #f8fafc;
            line-height: 1.5;
            margin: 0;
            padding: 20px;
        }}
        .report-container {{
            max-width: 950px;
            margin: 0 auto;
            background: #ffffff;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }}
        .header {{
            border-bottom: 2px solid #0f172a;
            padding-bottom: 15px;
            margin-bottom: 25px;
        }}
        .header h1 {{
            margin: 0 0 5px 0;
            font-size: 24px;
            color: #0f172a;
            letter-spacing: -0.5px;
        }}
        .header .subtitle {{
            font-size: 14px;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 600;
        }}
        .meta-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px 30px;
            background: #f1f5f9;
            padding: 15px 20px;
            border-radius: 6px;
            font-size: 13px;
            margin-bottom: 25px;
        }}
        .meta-grid div span {{
            color: #64748b;
            font-weight: 500;
        }}
        .section-title {{
            font-size: 16px;
            font-weight: 700;
            color: #0f172a;
            border-bottom: 1px solid #e2e8f0;
            padding-bottom: 6px;
            margin-top: 30px;
            margin-bottom: 15px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .metric-cards {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }}
        .metric-card {{
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            padding: 12px;
            border-radius: 6px;
            text-align: center;
        }}
        .metric-card .title {{
            font-size: 11px;
            color: #64748b;
            text-transform: uppercase;
            font-weight: 600;
        }}
        .metric-card .val {{
            font-size: 18px;
            font-weight: 700;
            color: #0f172a;
            margin-top: 4px;
        }}
        .decision-banner {{
            background: #f8fafc;
            border-left: 6px solid {hl_color};
            padding: 18px 24px;
            border-radius: 4px;
            margin-bottom: 25px;
        }}
        .decision-banner .headline {{
            font-size: 20px;
            font-weight: 800;
            color: {hl_color};
            margin-bottom: 6px;
        }}
        .decision-banner .recommendation {{
            font-size: 14px;
            color: #334155;
            font-weight: 500;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            margin-bottom: 20px;
        }}
        th, td {{
            padding: 8px 10px;
            border: 1px solid #e2e8f0;
        }}
        th {{
            background-color: #f1f5f9;
            color: #334155;
            font-weight: 600;
            text-align: left;
        }}
        .disclaimer-box {{
            background-color: #fffbeb;
            border: 1px solid #fef3c7;
            border-left: 4px solid #f59e0b;
            padding: 12px 16px;
            font-size: 12px;
            color: #92400e;
            border-radius: 4px;
            margin-top: 30px;
        }}
        @media print {{
            body {{ background: #fff; padding: 0; }}
            .report-container {{ box-shadow: none; padding: 0; max-width: 100%; }}
        }}
    </style>
</head>
<body>
    <div class="report-container">
        <div class="header">
            <div class="subtitle">Measurements &amp; Instrumentation • Intelligent Analysis Engine</div>
            <h1>IMUCA Measurement &amp; Calibration Report</h1>
        </div>
        
        <div class="meta-grid">
            <div><span>Report ID:</span> <strong>{report_id}</strong></div>
            <div><span>Generated:</span> {now_str}</div>
            <div><span>Data Source:</span> {html.escape(dataset_name)}</div>
            <div><span>Measurand:</span> DC Voltage (0.5 V to 5.0 V)</div>
            <div><span>Device Under Test:</span> {html.escape(dut_description)}</div>
            <div><span>Reference Standard:</span> {html.escape(reference_description)}</div>
        </div>
        
        <div class="decision-banner">
            <div class="headline">MEASUREMENT QUALITY: {decision_result.headline_status}</div>
            <div class="recommendation"><strong>Triggered Rule:</strong> {decision_result.primary_triggered_rule} ({decision_result.primary_rule_name})</div>
            <div class="recommendation" style="margin-top:4px;"><strong>Recommended Action:</strong> {html.escape(decision_result.detailed_recommendation)}</div>
        </div>
        
        <div class="metric-cards">
            <div class="metric-card">
                <div class="title">Mean Reading</div>
                <div class="val">{stats_result.mean:.4f} V</div>
            </div>
            <div class="metric-card">
                <div class="title">Combined Unc. u_c</div>
                <div class="val">{budget.combined_uncertainty_mv:.3f} mV</div>
            </div>
            <div class="metric-card">
                <div class="title">Expanded Unc. U (k=2)</div>
                <div class="val">{budget.coverage.expanded_uncertainty_mv:.2f} mV</div>
            </div>
            <div class="metric-card">
                <div class="title">Reported Result</div>
                <div class="val" style="font-size:14px;">{budget.coverage.formatted_reported_result.split(',')[0]}</div>
            </div>
        </div>
        
        <div class="section-title">1. Statistical &amp; Uncertainty Evaluation (5.000 V Point)</div>
        <table>
            <tr>
                <th>Quantity</th>
                <th>Symbol</th>
                <th>Value</th>
                <th>Remarks</th>
            </tr>
            <tr>
                <td>Reference Value</td>
                <td>X_REF</td>
                <td>{reference_nominal_v:.3f} V</td>
                <td>Traceable calibration standard</td>
            </tr>
            <tr>
                <td>Number of Observations</td>
                <td>n</td>
                <td>{stats_result.n}</td>
                <td>Repeatability condition observations</td>
            </tr>
            <tr>
                <td>Sample Mean</td>
                <td>x̄</td>
                <td>{stats_result.mean:.6f} V</td>
                <td>Best estimate of measurand</td>
            </tr>
            <tr>
                <td>Sample Standard Deviation</td>
                <td>s</td>
                <td>{stats_result.std_dev*1000:.3f} mV</td>
                <td>Dispersion with (n-1) Bessel's correction</td>
            </tr>
            <tr>
                <td>Type A Standard Uncertainty</td>
                <td>u_A</td>
                <td>{type_a.standard_uncertainty_mv:.3f} mV</td>
                <td>u_A = s / √n (ν = {type_a.degrees_of_freedom})</td>
            </tr>
            <tr>
                <td>Combined Standard Uncertainty</td>
                <td>u_c</td>
                <td>{budget.combined_uncertainty_mv:.3f} mV</td>
                <td>Root-sum-of-squares (RSS) combination</td>
            </tr>
            <tr>
                <td>Effective Degrees of Freedom</td>
                <td>ν_eff</td>
                <td>{budget.coverage.effective_degrees_of_freedom:.1f}</td>
                <td>Welch-Satterthwaite formula</td>
            </tr>
            <tr>
                <td>Coverage Factor</td>
                <td>k</td>
                <td>{budget.coverage.coverage_factor_k:.2f}</td>
                <td>Approximately 95 % level of confidence</td>
            </tr>
            <tr>
                <td>Expanded Uncertainty</td>
                <td>U</td>
                <td>{budget.coverage.expanded_uncertainty_mv:.2f} mV</td>
                <td>U = k · u_c (Reported as ±{budget.coverage.rounded_expanded_uncertainty_mv:.1f} mV)</td>
            </tr>
        </table>
        
        <div class="section-title">2. Uncertainty Budget (Ranked by Variance Contribution)</div>
        <table>
            <thead>
                <tr>
                    <th>Uncertainty Source</th>
                    <th>Type</th>
                    <th>Input Value (mV)</th>
                    <th>Distribution</th>
                    <th>Divisor</th>
                    <th>u_i (mV)</th>
                    <th>c_i</th>
                    <th>c_i · u_i (mV)</th>
                    <th>ν_i</th>
                    <th>Variance Share</th>
                </tr>
            </thead>
            <tbody>
                {budget_rows_html}
            </tbody>
        </table>
        <p style="font-size:12px; color:#64748b; margin-top:-10px;">
            <strong>Dominant Contributor:</strong> {budget.dominant_source.source_name} accounts for {budget.dominant_source.variance_contribution_percent:.1f} % of total combined variance.
        </p>
        
        {f'''
        <div class="section-title">3. Calibration Sweep &amp; Conformity Analysis</div>
        <p style="font-size:13px;">
            <strong>Linear Fit:</strong> <code>XDUT = {cal_result.slope_m:.6f} · XREF {cal_result.intercept_c*1000:+.2f} mV</code> |
            <strong>R²:</strong> {cal_result.r_squared:.6f} |
            <strong>Zero Offset:</strong> {cal_result.zero_offset_mv:+.2f} mV |
            <strong>Gain Error:</strong> {cal_result.gain_error_percent:+.3f} % |
            <strong>Conformity:</strong> {cal_result.summary_text}
        </p>
        <table>
            <thead>
                <tr>
                    <th>Point</th>
                    <th>Reference (V)</th>
                    <th>DUT (V)</th>
                    <th>Abs Error (mV)</th>
                    <th>Rel Error (×10⁻³)</th>
                    <th>Pct Error (%)</th>
                    <th>Status (±1%)</th>
                </tr>
            </thead>
            <tbody>
                {cal_rows_html}
            </tbody>
        </table>
        <p style="font-size:12px; color:#64748b; margin-top:-10px;">
            <strong>Residual Diagnostics:</strong> Max residual = {cal_result.residuals.max_residual_mv:.2f} mV (Resolution threshold = {cal_result.residuals.resolution_limit_mv:.2f} mV). {cal_result.residuals.diagnostic_message}
        </p>
        ''' if cal_result is not None else ''}
        
        {f'''
        <div class="section-title">4. Trend &amp; Drift Analysis</div>
        <table style="width:100%;">
            <tr>
                <th style="width:30%;">Metric</th>
                <th style="width:35%;">Within-Run (Single Session)</th>
                <th style="width:35%;">Between-Session (10 Sessions)</th>
            </tr>
            <tr>
                <td>Regression Slope</td>
                <td>{within_run.slope_mv_per_reading:+.3f} mV / reading</td>
                <td>{drift_result.slope_b:+.3f} mV / session</td>
            </tr>
            <tr>
                <td>Standard Error of Slope</td>
                <td>{within_run.std_err_slope:.3f} mV / reading</td>
                <td>{drift_result.std_err_b:.3f} mV / session</td>
            </tr>
            <tr>
                <td>Significance (p-value)</td>
                <td>p = {within_run.p_value:.3f}</td>
                <td>p = {drift_result.p_value:.2e}</td>
            </tr>
            <tr>
                <td>Status / Verdict</td>
                <td><strong>{within_run.verdict}</strong></td>
                <td><strong>{drift_result.drift_status}</strong></td>
            </tr>
            <tr>
                <td>Tolerance Breach Forecast</td>
                <td>N/A</td>
                <td>{'Session ' + str(int(drift_result.projected_breach_session)) if drift_result.projected_breach_session else 'No breach projected'}</td>
            </tr>
        </table>
        ''' if (within_run is not None and drift_result is not None and drift_result.is_assessed) else ''}
        
        <div class="section-title">5. Intelligent Decision Engine Audit Log (Rules R1 to R5)</div>
        <table>
            <thead>
                <tr>
                    <th>Rule ID</th>
                    <th>Rule Name</th>
                    <th>Condition Evaluated</th>
                    <th>Computed Metric</th>
                    <th>Allowable Limit</th>
                    <th>Outcome</th>
                </tr>
            </thead>
            <tbody>
                {rules_rows_html}
            </tbody>
        </table>
        
        <div class="disclaimer-box">
            <strong>Metrological Notice &amp; Scope:</strong> All calculations in this report are based on a synthetic proof-of-concept dataset designed for academic demonstration of Measurements and Instrumentation. No physical hardware validation has been completed at this review stage.
        </div>
    </div>
</body>
</html>
"""
    return html_template
