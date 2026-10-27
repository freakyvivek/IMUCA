"""
Preprocessing Module for IMUCA.
Handles unit normalization, repeat sequence structuring, and calibration dataset alignment.
"""

from typing import List, Optional, Tuple, Dict, Any
import numpy as np
import pandas as pd


def extract_repeats_from_row(row: pd.Series, repeat_cols: List[str]) -> np.ndarray:
    """
    Extract numeric repeat readings from row columns.
    """
    repeats = []
    for col in repeat_cols:
        val = row.get(col)
        if pd.notna(val) and val != "" and str(val).strip() not in ["-", "–"]:
            try:
                repeats.append(float(val))
            except (ValueError, TypeError):
                pass
    return np.array(repeats, dtype=float)


def normalize_voltage_units(value: float, unit_from: str, unit_to: str = "V") -> float:
    """
    Convert voltage between units (V, mV, uV).
    """
    conversions_to_v = {
        "V": 1.0,
        "mV": 1e-3,
        "uV": 1e-6,
        "kV": 1e3
    }
    v_val = value * conversions_to_v.get(unit_from, 1.0)
    return v_val / conversions_to_v.get(unit_to, 1.0)


def structure_calibration_data(
    df: pd.DataFrame,
    ref_col: str,
    dut_col: str,
    repeat_cols: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Standardize calibration sweep DataFrame with columns:
    [Point, Reference_V, DUT_V, Repeats_Array]
    """
    structured_rows = []
    r_cols = repeat_cols or []
    
    for idx, row in df.iterrows():
        ref_val = float(row[ref_col])
        dut_val = float(row[dut_col])
        
        # Check if repeats exist in row
        row_repeats = extract_repeats_from_row(row, r_cols)
        if len(row_repeats) == 0:
            row_repeats = np.array([dut_val])
            
        structured_rows.append({
            "Point": idx + 1,
            "Reference_V": ref_val,
            "DUT_V": dut_val,
            "Repeats": row_repeats,
            "Num_Repeats": len(row_repeats)
        })
        
    return pd.DataFrame(structured_rows)
