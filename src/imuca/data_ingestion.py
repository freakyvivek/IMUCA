"""
IMUCA Data Ingestion and Acquisition Interface.

Section 5 Specification:
- Load CSV datasets with column/unit validation.
- Preserve original input data (immutability).
- Return structured ingestion diagnostics.
- Export processed datasets separately.
- Provide common stream-processing interface prepared for future microcontroller serial acquisition.
"""

from __future__ import annotations
import os
import io
import json
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Union, Tuple, Iterator
import pandas as pd
import numpy as np

from src.imuca.schema import (
    CANONICAL_COLUMNS,
    MEASURAND_KEYS,
    validate_schema,
    SchemaValidationResult
)


# Known alternate header aliases for flexible ingestion of legacy and laboratory formats
COLUMN_ALIASES: Dict[str, List[str]] = {
    "voltage_V": ["voltage_v", "dut_v", "voltage", "v_dut", "v_meas", "v"],
    "current_mA": ["current_ma", "dut_ma", "current", "i_dut", "i_meas", "ma", "i"],
    "temperature_C": ["temperature_c", "temp_c", "temperature", "temp", "dut_c", "t"],
    "reference_voltage_V": ["reference_voltage_v", "reference_v", "ref_v", "v_ref"],
    "reference_current_mA": ["reference_current_ma", "reference_ma", "ref_ma", "i_ref"],
    "reference_temperature_C": ["reference_temperature_c", "reference_c", "ref_c", "t_ref"],
    "environmental_temperature_C": ["environmental_temperature_c", "ambient_temp_c", "env_temp_c", "t_amb"],
    "sequence_number": ["sequence_number", "seq", "sequence", "point", "observation", "index", "id"],
    "elapsed_ms": ["elapsed_ms", "time_ms", "elapsed_time_ms", "t_ms", "timestamp_ms"],
    "timestamp_utc": ["timestamp_utc", "timestamp", "datetime", "utc_time"],
    "status": ["status", "sensor_status", "state", "flag"]
}


@dataclass
class IngestionDiagnostics:
    """Detailed diagnostics of the ingestion and mapping step."""
    source_identifier: str
    raw_row_count: int
    raw_columns: List[str]
    mapped_columns: Dict[str, str]  # canonical_name -> raw_name
    unmapped_columns: List[str]
    schema_validation: SchemaValidationResult
    file_metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_successful(self) -> bool:
        return self.schema_validation.is_valid or self.schema_validation.valid_record_count > 0


class DataIngestionPipeline:
    """
    Standard ingestion pipeline for offline files and streaming data.
    Ensures raw inputs remain untouched and processed data is cleanly tracked.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def load_csv(
        self,
        file_path_or_buffer: Union[str, io.StringIO, io.BytesIO],
        source_id: Optional[str] = None
    ) -> Tuple[pd.DataFrame, IngestionDiagnostics]:
        """
        Load CSV data, map columns, validate against schema, and return cleaned dataset + diagnostics.
        The raw input is preserved and never modified in-place.
        """
        identifier = source_id or (file_path_or_buffer if isinstance(file_path_or_buffer, str) else "buffer")
        
        # 1. Read raw CSV
        try:
            raw_df = pd.read_csv(file_path_or_buffer)
        except Exception as e:
            empty_val = SchemaValidationResult(
                is_valid=False,
                total_records=0,
                valid_record_count=0,
                error_record_count=0,
                warning_record_count=0,
                diagnostics=[],
                summary={"error": f"Failed to read CSV: {str(e)}"}
            )
            return pd.DataFrame(), IngestionDiagnostics(
                source_identifier=str(identifier),
                raw_row_count=0,
                raw_columns=[],
                mapped_columns={},
                unmapped_columns=[],
                schema_validation=empty_val,
                file_metadata={"read_error": str(e)}
            )

        raw_cols = list(raw_df.columns)
        mapped_cols: Dict[str, str] = {}
        unmapped_cols: List[str] = []

        # 2. Normalize and map column names
        normalized_raw = {c.strip().lower(): c for c in raw_cols}
        
        for canon, aliases in COLUMN_ALIASES.items():
            for alias in aliases:
                if alias in normalized_raw:
                    mapped_cols[canon] = normalized_raw[alias]
                    break

        for raw_c in raw_cols:
            if raw_c not in mapped_cols.values():
                unmapped_cols.append(raw_c)

        # 3. Construct canonical representation
        working_df = pd.DataFrame()
        for canon, raw_c in mapped_cols.items():
            working_df[canon] = raw_df[raw_c]

        # Preserve unmapped columns in notes or retain for audit
        for raw_c in unmapped_cols:
            working_df[f"raw_{raw_c}"] = raw_df[raw_c]

        # Ensure minimal sequence number exists if omitted
        if "sequence_number" not in working_df.columns:
            working_df["sequence_number"] = np.arange(1, len(working_df) + 1)
            mapped_cols["sequence_number"] = "[auto-generated sequence]"

        if "elapsed_ms" not in working_df.columns:
            # Default to 1-second intervals if elapsed time is omitted
            working_df["elapsed_ms"] = np.arange(0, len(working_df)) * 1000.0

        if "status" not in working_df.columns:
            working_df["status"] = "OK"

        if "data_source" not in working_df.columns:
            working_df["data_source"] = f"csv:{os.path.basename(str(identifier))}"

        # 4. Run Schema Validation
        val_result = validate_schema(working_df)

        diagnostics = IngestionDiagnostics(
            source_identifier=str(identifier),
            raw_row_count=len(raw_df),
            raw_columns=raw_cols,
            mapped_columns=mapped_cols,
            unmapped_columns=unmapped_cols,
            schema_validation=val_result,
            file_metadata={
                "column_count": len(raw_cols),
                "mapped_count": len(mapped_cols)
            }
        )

        return val_result.flagged_dataframe, diagnostics

    def export_processed(
        self,
        df: pd.DataFrame,
        output_path: str,
        include_diagnostics: bool = True
    ) -> str:
        """
        Export processed dataset separately from raw inputs.
        Guarantees isolation of transformed data.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        df.to_csv(output_path, index=False)
        return output_path


# ==============================================================================
# Streaming Ingestion Interface (for future serial integration)
# ==============================================================================

class MeasurementStreamBuffer:
    """
    Common streaming buffer interface for real-time serial or packet ingestion.
    Validates records line-by-line or packet-by-packet as they arrive from microcontroller.
    """

    def __init__(self, buffer_size: int = 1000):
        self.buffer_size = buffer_size
        self._records: List[Dict[str, Any]] = []
        self._last_seq: Optional[int] = None
        self._last_elapsed_ms: Optional[float] = None

    def push_raw_line(self, line: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Parse raw line (e.g. JSON or comma-separated line from serial port).
        Returns: (success, parsed_record, message)
        """
        cleaned = line.strip()
        if not cleaned:
            return False, None, "Empty line"

        # Try JSON format
        if cleaned.startswith("{") and cleaned.endswith("}"):
            try:
                data = json.loads(cleaned)
                return self.push_record(data)
            except Exception as e:
                return False, None, f"JSON parse error: {str(e)}"

        # Try CSV format (seq, elapsed_ms, v, i, t, status)
        parts = [p.strip() for p in cleaned.split(",")]
        if len(parts) >= 3:
            try:
                seq = int(parts[0])
                elapsed = float(parts[1])
                v = float(parts[2]) if parts[2] not in ("", "nan", "null") else None
                i = float(parts[3]) if len(parts) > 3 and parts[3] not in ("", "nan", "null") else None
                t = float(parts[4]) if len(parts) > 4 and parts[4] not in ("", "nan", "null") else None
                status = parts[5] if len(parts) > 5 else "OK"
                
                record = {
                    "sequence_number": seq,
                    "elapsed_ms": elapsed,
                    "voltage_V": v,
                    "current_mA": i,
                    "temperature_C": t,
                    "status": status,
                    "data_source": "serial_stream"
                }
                return self.push_record(record)
            except Exception as e:
                return False, None, f"CSV line parse error: {str(e)}"

        return False, None, f"Unrecognized line format: {cleaned[:30]}"

    def push_record(self, record: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], str]:
        """Validate and append structured record to buffer."""
        seq = record.get("sequence_number")
        elapsed = record.get("elapsed_ms")

        flags = []
        if seq is not None and self._last_seq is not None:
            if seq <= self._last_seq:
                flags.append("OUT_OF_ORDER_SEQ")
            elif seq > self._last_seq + 1:
                flags.append(f"GAP_{seq - self._last_seq - 1}")
        
        if elapsed is not None and self._last_elapsed_ms is not None:
            if elapsed < self._last_elapsed_ms:
                flags.append("BACKWARDS_TIME")

        record["stream_quality_flags"] = ";".join(flags) if flags else "OK"
        self._records.append(record)
        
        if seq is not None:
            self._last_seq = int(seq)
        if elapsed is not None:
            self._last_elapsed_ms = float(elapsed)

        # Enforce buffer length
        if len(self._records) > self.buffer_size:
            self._records.pop(0)

        return True, record, "OK"

    def get_dataframe(self) -> pd.DataFrame:
        """Return buffered records as a DataFrame."""
        return pd.DataFrame(self._records)

    def clear(self):
        self._records.clear()
        self._last_seq = None
        self._last_elapsed_ms = None
