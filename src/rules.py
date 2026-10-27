"""
Intelligent Decision Engine Module for IMUCA.
Implements Algorithm 7 and Chapter 16: Transparent, ordered rule-based decision engine (R1 to R5)
operating on computed metrology metrics without black-box ML.
"""

from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
import pandas as pd
from src.limits import EngineeringLimits
from src.actions import ACTION_DEFINITIONS, synthesize_recommendation


@dataclass
class RuleEvaluationRecord:
    rule_id: str             # 'R1', 'R2', 'R3', 'R4', 'R5'
    rule_name: str           # e.g. 'Uncertainty Check'
    condition_desc: str      # e.g. 'U > U_allowable'
    computed_value_str: str  # e.g. 'U = 10.55 mV'
    limit_value_str: str     # e.g. '25.00 mV'
    fired: bool              # True if condition met
    evaluation_status: str   # 'TRIGGERED', 'PASSED', 'NOT EVALUATED'
    rule_status: str         # 'HIGH UNCERTAINTY', 'CALIBRATION REQUIRED', etc.
    action_text: str


@dataclass
class DecisionEngineResult:
    headline_status: str               # 'ACCEPTABLE', 'ATTENTION REQUIRED', 'CALIBRATION REQUIRED'
    primary_triggered_rule: str        # 'R1', 'R2', 'R3', 'R4', 'R5'
    primary_rule_name: str
    primary_status_label: str          # 'MEASUREMENT ACCEPTABLE', 'POSSIBLE DRIFT', etc.
    recommended_action: str
    detailed_recommendation: str
    calibration_status_badge: str      # 'PASS', 'MARGINAL', 'FAIL'
    drift_status_badge: str            # 'NOT ASSESSED', 'NO SIGNIFICANT DRIFT', 'SIGNIFICANT UPWARD DRIFT'
    dominant_uncertainty_badge: str    # e.g. 'Repeatability (35.6 %)'
    all_fired_rules: List[str]
    rule_evaluation_records: List[RuleEvaluationRecord]
    rules_dataframe: pd.DataFrame


def evaluate_decision_rules(
    expanded_uncertainty_mv: float,
    absolute_error_mv: float,
    sample_std_dev_mv: float,
    limits: EngineeringLimits,
    drift_slope_mv_per_session: Optional[float] = None,
    drift_p_value: Optional[float] = None,
    has_drift_history: bool = False,
    sweep_nonconforming_points: Optional[List[int]] = None,
    projected_breach_session: Optional[float] = None,
    dominant_source_name: str = "Repeatability",
    dominant_source_percent: float = 35.6
) -> DecisionEngineResult:
    """
    Execute the transparent ordered rule-based decision engine (R1 -> R2 -> R3 -> R4 -> R5).
    
    Evaluates:
    - R1: Uncertainty Check: U > U_allowable
    - R2: Conformity Check: |E| > T OR (|E| + U) > T
    - R3: Drift Check: History exists AND |b| > b_lim AND p < 0.05
    - R4: Repeatability Check: s > s_allowable
    - R5: Default: None of R1-R4 fired -> MEASUREMENT ACCEPTABLE
    
    Returns:
        DecisionEngineResult containing headline status, fired rule log, and recommended actions.
    """
    records: List[RuleEvaluationRecord] = []
    fired_rules: List[str] = []
    
    U = expanded_uncertainty_mv
    E = absolute_error_mv
    s = sample_std_dev_mv
    
    # -------------------------------------------------------------
    # RULE R1 - UNCERTAINTY CHECK
    # -------------------------------------------------------------
    r1_fired = (U > limits.u_allowable_mv)
    r1_rec = RuleEvaluationRecord(
        rule_id="R1",
        rule_name="Uncertainty Check",
        condition_desc="U > U_allowable",
        computed_value_str=f"U = {U:.2f} mV",
        limit_value_str=f"{limits.u_allowable_mv:.2f} mV",
        fired=r1_fired,
        evaluation_status="TRIGGERED" if r1_fired else "PASSED",
        rule_status=ACTION_DEFINITIONS["R1"]["status"],
        action_text=ACTION_DEFINITIONS["R1"]["action"]
    )
    records.append(r1_rec)
    if r1_fired:
        fired_rules.append("R1")
        
    # -------------------------------------------------------------
    # RULE R2 - CONFORMITY CHECK (Guard-banded and Simple)
    # -------------------------------------------------------------
    total_err_band = abs(E) + U
    r2_fired = (abs(E) > limits.tolerance_mv) or (total_err_band > limits.tolerance_mv)
    r2_rec = RuleEvaluationRecord(
        rule_id="R2",
        rule_name="Conformity Check",
        condition_desc="|E| > T  OR  (|E| + U) > T",
        computed_value_str=f"|E| = {abs(E):.1f} mV, |E|+U = {total_err_band:.1f} mV",
        limit_value_str=f"T = {limits.tolerance_mv:.1f} mV",
        fired=r2_fired,
        evaluation_status="TRIGGERED" if r2_fired else "PASSED",
        rule_status=ACTION_DEFINITIONS["R2"]["status"],
        action_text=ACTION_DEFINITIONS["R2"]["action"]
    )
    records.append(r2_rec)
    if r2_fired:
        fired_rules.append("R2")
        
    # -------------------------------------------------------------
    # RULE R3 - DRIFT CHECK
    # -------------------------------------------------------------
    if has_drift_history and drift_slope_mv_per_session is not None and drift_p_value is not None:
        b = drift_slope_mv_per_session
        p = drift_p_value
        r3_fired = (abs(b) > limits.drift_threshold_mv) and (p < 0.05)
        comp_str = f"|b| = {abs(b):.2f} mV/session, p = {p:.2e}"
        eval_stat = "TRIGGERED" if r3_fired else "PASSED"
    else:
        r3_fired = False
        comp_str = "No history available"
        eval_stat = "NOT EVALUATED"
        
    r3_rec = RuleEvaluationRecord(
        rule_id="R3",
        rule_name="Drift Check",
        condition_desc="|b| > b_threshold  AND  p_drift < 0.05",
        computed_value_str=comp_str,
        limit_value_str=f"b_lim = {limits.drift_threshold_mv:.2f} mV/session, p < 0.05",
        fired=r3_fired,
        evaluation_status=eval_stat,
        rule_status=ACTION_DEFINITIONS["R3"]["status"],
        action_text=ACTION_DEFINITIONS["R3"]["action"]
    )
    records.append(r3_rec)
    if r3_fired:
        fired_rules.append("R3")
        
    # -------------------------------------------------------------
    # RULE R4 - REPEATABILITY CHECK
    # -------------------------------------------------------------
    r4_fired = (s > limits.s_allowable_mv)
    r4_rec = RuleEvaluationRecord(
        rule_id="R4",
        rule_name="Repeatability Check",
        condition_desc="s > s_allowable",
        computed_value_str=f"s = {s:.3f} mV",
        limit_value_str=f"{limits.s_allowable_mv:.1f} mV",
        fired=r4_fired,
        evaluation_status="TRIGGERED" if r4_fired else "PASSED",
        rule_status=ACTION_DEFINITIONS["R4"]["status"],
        action_text=ACTION_DEFINITIONS["R4"]["action"]
    )
    records.append(r4_rec)
    if r4_fired:
        fired_rules.append("R4")
        
    # -------------------------------------------------------------
    # RULE R5 - DEFAULT ACCEPTABLE
    # -------------------------------------------------------------
    if len(fired_rules) == 0:
        r5_fired = True
        fired_rules.append("R5")
        r5_eval = "TRIGGERED"
    else:
        r5_fired = False
        r5_eval = "NOT REACHED"
        
    r5_rec = RuleEvaluationRecord(
        rule_id="R5",
        rule_name="Default (No violations)",
        condition_desc="None of R1 to R4 fired",
        computed_value_str="All metrics within limits",
        limit_value_str="–",
        fired=r5_fired,
        evaluation_status=r5_eval,
        rule_status=ACTION_DEFINITIONS["R5"]["status"],
        action_text=ACTION_DEFINITIONS["R5"]["action"]
    )
    records.append(r5_rec)
    
    # -------------------------------------------------------------
    # HEADLINE STATUS DETERMINATION (Ordered severity R1 > R2 > R3 > R4 > R5)
    # -------------------------------------------------------------
    primary_rule = fired_rules[0]
    primary_def = ACTION_DEFINITIONS[primary_rule]
    headline_status = primary_def["headline"]
    status_label = primary_def["status"]
    action_text = primary_def["action"]
    
    has_nonconforming_sweep = bool(sweep_nonconforming_points and len(sweep_nonconforming_points) > 0)
    detailed_rec = synthesize_recommendation(
        headline_status=headline_status,
        triggered_rules=fired_rules,
        has_sweep_failure=has_nonconforming_sweep,
        sweep_nonconforming_points=sweep_nonconforming_points,
        projected_breach_session=projected_breach_session,
        dominant_source_name=dominant_source_name
    )
    
    # Badges
    cal_badge = "PASS" if not r2_fired else "FAIL"
    if has_drift_history and drift_slope_mv_per_session is not None:
        if r3_fired:
            drift_badge = "SIGNIFICANT UPWARD DRIFT" if drift_slope_mv_per_session > 0 else "SIGNIFICANT DOWNWARD DRIFT"
        else:
            drift_badge = "NO SIGNIFICANT DRIFT"
    else:
        drift_badge = "NOT ASSESSED"
        
    dom_badge = f"{dominant_source_name} ({dominant_source_percent:.1f} %)"
    
    # Construct rules trace DataFrame
    df_rows = []
    for r in records:
        df_rows.append({
            "Rule ID": r.rule_id,
            "Rule Name": r.rule_name,
            "Condition": r.condition_desc,
            "Computed Value": r.computed_value_str,
            "Threshold Limit": r.limit_value_str,
            "Outcome": r.evaluation_status,
            "Recommended Action": r.action_text
        })
    df_rules = pd.DataFrame(df_rows)
    
    return DecisionEngineResult(
        headline_status=headline_status,
        primary_triggered_rule=primary_rule,
        primary_rule_name=ACTION_DEFINITIONS[primary_rule]["status"],
        primary_status_label=status_label,
        recommended_action=action_text,
        detailed_recommendation=detailed_rec,
        calibration_status_badge=cal_badge,
        drift_status_badge=drift_badge,
        dominant_uncertainty_badge=dom_badge,
        all_fired_rules=fired_rules,
        rule_evaluation_records=records,
        rules_dataframe=df_rules
    )
