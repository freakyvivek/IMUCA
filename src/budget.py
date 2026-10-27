"""
Uncertainty Budget Module for IMUCA.
Implements Equations 9.7 to 9.8 and Table 12.1: Complete uncertainty budget compilation,
variance contribution ranking, combined standard uncertainty (RSS), and dominant source detection.
"""

from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from src.type_a import TypeAResult
from src.type_b import TypeBResult, TypeBSource
from src.coverage import evaluate_expanded_uncertainty, CoverageResult


@dataclass
class BudgetEntry:
    source_name: str
    uncertainty_type: str        # 'A' or 'B'
    input_value_display: str     # e.g. "9.944 mV" or "0.01 V"
    input_value_mv: float
    distribution_name: str       # e.g. "Normal", "Rectangular"
    divisor: float
    divisor_display: str         # e.g. "sqrt(10)", "sqrt(3)", "2"
    standard_uncertainty_v: float
    standard_uncertainty_mv: float
    sensitivity_coefficient: float # c_i
    scaled_uncertainty_v: float
    scaled_uncertainty_mv: float # c_i * u_i in mV
    degrees_of_freedom: Union[float, int]
    degrees_of_freedom_display: str # e.g. "9", "inf"
    variance_contribution_percent: float # (c_i * u_i)^2 / u_c^2 * 100 %
    is_dominant: bool = False


@dataclass
class UncertaintyBudget:
    entries: List[BudgetEntry]
    combined_uncertainty_v: float  # u_c
    combined_uncertainty_mv: float
    dominant_source: BudgetEntry
    coverage: CoverageResult
    budget_dataframe: pd.DataFrame
    total_variance_sum_mv2: float


def build_uncertainty_budget(
    type_a: Optional[TypeAResult],
    type_b: TypeBResult,
    confidence_level: float = 0.95,
    force_k: Optional[float] = None
) -> UncertaintyBudget:
    """
    Build complete uncertainty budget table, calculate combined uncertainty (RSS),
    variance percentage shares, effective degrees of freedom, and expanded uncertainty.
    
    Args:
        type_a: TypeAResult (can be None if only Type B is available).
        type_b: TypeBResult containing evaluated Type B components.
        confidence_level: Target confidence level (default 0.95).
        force_k: Optional explicit coverage factor override (e.g. k=2.0).
        
    Returns:
        UncertaintyBudget object.
    """
    raw_entries: List[Dict[str, Any]] = []
    
    # 1. Type A entry
    if type_a is not None:
        u_a_v = type_a.standard_uncertainty
        u_a_mv = type_a.standard_uncertainty_mv
        s_mv = type_a.sample_std_dev_mv
        n = type_a.n
        raw_entries.append({
            "source_name": "Repeatability",
            "type": "A",
            "input_val_disp": f"{s_mv:.3f} mV",
            "input_val_mv": s_mv,
            "dist": "Normal",
            "div": np.sqrt(n),
            "div_disp": f"√{n}",
            "u_v": u_a_v,
            "u_mv": u_a_mv,
            "c_i": 1.0,
            "c_u_v": u_a_v,
            "c_u_mv": u_a_mv,
            "nu": type_a.degrees_of_freedom,
            "nu_disp": str(type_a.degrees_of_freedom)
        })
        
    # 2. Type B entries
    for b in type_b.sources:
        div_disp = "√3" if b.distribution == "rectangular" else (
            "√6" if b.distribution == "triangular" else (
                "2" if b.distribution == "normal_k2" else (
                    "3" if b.distribution == "normal_k3" else (
                        "√2" if b.distribution == "u_shaped" else f"{b.divisor:.3f}"
                    )
                )
            )
        )
        nu_disp = "∞" if not np.isfinite(b.degrees_of_freedom) else str(int(b.degrees_of_freedom))
        
        raw_entries.append({
            "source_name": b.name,
            "type": "B",
            "input_val_disp": f"{b.half_width_mv:.3f} mV",
            "input_val_mv": b.half_width_mv,
            "dist": b.distribution.capitalize().replace("_", " "),
            "div": b.divisor,
            "div_disp": div_disp,
            "u_v": b.standard_uncertainty_v,
            "u_mv": b.standard_uncertainty_mv,
            "c_i": b.sensitivity_coefficient,
            "c_u_v": b.sensitivity_coefficient * b.standard_uncertainty_v,
            "c_u_mv": b.scaled_uncertainty_mv,
            "nu": b.degrees_of_freedom,
            "nu_disp": nu_disp
        })
        
    # 3. Combined Uncertainty u_c = sqrt( SUM (c_i * u_i)^2 )
    scaled_mv_sq = [(e["c_u_mv"]) ** 2 for e in raw_entries]
    total_var_mv2 = float(np.sum(scaled_mv_sq))
    u_c_mv = float(np.sqrt(total_var_mv2))
    u_c_v = u_c_mv / 1000.0
    
    # 4. Variance Shares h_i = (c_i * u_i)^2 / u_c^2 * 100 %
    budget_entries: List[BudgetEntry] = []
    for i, e in enumerate(raw_entries):
        var_contrib_pct = (scaled_mv_sq[i] / total_var_mv2 * 100.0) if total_var_mv2 > 0 else 0.0
        be = BudgetEntry(
            source_name=e["source_name"],
            uncertainty_type=e["type"],
            input_value_display=e["input_val_disp"],
            input_value_mv=e["input_val_mv"],
            distribution_name=e["dist"],
            divisor=e["div"],
            divisor_display=e["div_disp"],
            standard_uncertainty_v=e["u_v"],
            standard_uncertainty_mv=e["u_mv"],
            sensitivity_coefficient=e["c_i"],
            scaled_uncertainty_v=e["c_u_v"],
            scaled_uncertainty_mv=e["c_u_mv"],
            degrees_of_freedom=e["nu"],
            degrees_of_freedom_display=e["nu_disp"],
            variance_contribution_percent=var_contrib_pct
        )
        budget_entries.append(be)
        
    # Sort by contribution descending
    budget_entries.sort(key=lambda x: x.variance_contribution_percent, reverse=True)
    if budget_entries:
        budget_entries[0].is_dominant = True
        dominant_source = budget_entries[0]
    else:
        dominant_source = None
        
    # 5. Coverage and Expanded Uncertainty
    all_u_v = [e.standard_uncertainty_v for e in budget_entries]
    all_nu = [e.degrees_of_freedom for e in budget_entries]
    mean_read = type_b.reading_v
    coverage = evaluate_expanded_uncertainty(
        u_c_v=u_c_v,
        uncertainties_v=all_u_v,
        degrees_of_freedom=all_nu,
        mean_reading_v=mean_read,
        confidence_level=confidence_level,
        force_k=force_k
    )
    
    # Construct DataFrame for presentation
    df_rows = []
    for be in budget_entries:
        df_rows.append({
            "Source": be.source_name,
            "Type": be.uncertainty_type,
            "Input Value (mV)": round(be.input_value_mv, 3),
            "Distribution": be.distribution_name,
            "Divisor": be.divisor_display,
            "u_i (mV)": round(be.standard_uncertainty_mv, 3),
            "c_i": be.sensitivity_coefficient,
            "c_i * u_i (mV)": round(be.scaled_uncertainty_mv, 3),
            "ν_i": be.degrees_of_freedom_display,
            "Contribution (%)": round(be.variance_contribution_percent, 1),
            "Dominant": "★ DOMINANT" if be.is_dominant else ""
        })
    df_budget = pd.DataFrame(df_rows)
    
    return UncertaintyBudget(
        entries=budget_entries,
        combined_uncertainty_v=u_c_v,
        combined_uncertainty_mv=u_c_mv,
        dominant_source=dominant_source,
        coverage=coverage,
        budget_dataframe=df_budget,
        total_variance_sum_mv2=total_var_mv2
    )
