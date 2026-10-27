"""
Data Loader Module for IMUCA.
Handles CSV ingestion, column schema detection, and input normalization.
"""

from typing import Union, Tuple, Optional, List
import io
import os
import pandas as pd


def load_csv(
    source: Union[str, io.BytesIO, io.StringIO, pd.DataFrame]
) -> pd.DataFrame:
    """
    Load a CSV dataset from a file path, file-like object, or existing DataFrame.
    
    Args:
        source: File path, BytesIO/StringIO buffer, or DataFrame.
        
    Returns:
        pd.DataFrame containing raw measurement data.
        
    Raises:
        ValueError: If file cannot be read or is empty.
    """
    if isinstance(source, pd.DataFrame):
        return source.copy()
    
    try:
        if isinstance(source, str):
            if not os.path.exists(source):
                raise FileNotFoundError(f"File not found: {source}")
            df = pd.read_csv(source)
        else:
            df = pd.read_csv(source)
            
        if df.empty:
            raise ValueError("The provided CSV file is empty.")
            
        # Clean column names (strip whitespace)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        if isinstance(e, (FileNotFoundError, ValueError)):
            raise e
        raise ValueError(f"Error parsing CSV file: {str(e)}")


def detect_measurement_columns(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str], List[str]]:
    """
    Automatically identify reference, DUT, and repeat observation columns.
    
    Returns:
        (reference_col, dut_col, list_of_repeat_cols)
    """
    cols = list(df.columns)
    ref_col = None
    dut_col = None
    repeat_cols = []
    
    # Identify reference column
    for c in cols:
        c_lower = c.lower()
        if any(k in c_lower for k in ["ref", "standard", "nominal", "target", "x_ref", "true"]):
            ref_col = c
            break
            
    # Identify DUT column
    for c in cols:
        c_lower = c.lower()
        if c != ref_col and any(k in c_lower for k in ["dut", "meas", "reading", "indicated", "x_dut", "ind"]):
            dut_col = c
            break
            
    # Identify Repeat columns
    for c in cols:
        c_lower = c.lower()
        if (c != ref_col and c != dut_col) and any(k in c_lower for k in ["repeat", "rpt", "trial", "obs", "run"]):
            repeat_cols.append(c)
            
    # Fallback heuristics for 2-column datasets (e.g. Reference, DUT)
    if ref_col is None and len(cols) >= 2:
        ref_col = cols[0]
    if dut_col is None and len(cols) >= 2:
        dut_col = cols[1] if cols[1] != ref_col else (cols[0] if len(cols) > 1 else None)
        
    return ref_col, dut_col, repeat_cols


def detect_drift_columns(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    """
    Identify session/time and error columns for drift analysis.
    
    Returns:
        (session_col, error_col)
    """
    cols = list(df.columns)
    session_col = None
    error_col = None
    
    for c in cols:
        c_lower = c.lower()
        if any(k in c_lower for k in ["session", "time", "date", "run", "idx", "index", "t"]):
            session_col = c
            break
            
    for c in cols:
        c_lower = c.lower()
        if c != session_col and any(k in c_lower for k in ["error", "err", "e_mv", "mean_error", "e"]):
            error_col = c
            break
            
    if session_col is None and len(cols) >= 2:
        session_col = cols[0]
    if error_col is None and len(cols) >= 2:
        error_col = cols[1]
        
    return session_col, error_col
