"""
IMUCA Hardware Adapter and Measurement Source Boundary.

Complies with IMUCA Physical Hardware Integration Specification (docs/HARDWARE_READINESS.md).
Separates physical and simulated device acquisition from metrology calculations,
detection algorithms, and UI logic.

Features:
- Standard ASCII packet framing: $IMUCA,<seq_id>,<elapsed_ms>,<voltage_mv>,<current_ma>,<temp_c>,<status_flags>*<crc16>\\r\\n
- CCITT CRC-16 (polynomial 0x1021) verification and computation.
- Status bitmask parsing (INA219 OVF, COMM_ERR, DS18B20 CRC_ERR, DISCONN, RANGE_EXCEEDED, CLOCK_UNCERTAIN).
- Abstract MeasurementSource base class.
- SimulationReplaySource for deterministic synthetic replay and uploaded CSV streams.
- SerialHardwareAdapter for UART/USB-CDC physical hardware with connection/disconnection,
  timeout handling, packet loss logging, and graceful absence of pyserial.
- Clear simulation vs physical hardware demarcation (is_simulated flag, connection status).
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from enum import IntFlag
from typing import Optional, Dict, Any, List, Tuple, Generator
from datetime import datetime, timezone
from pathlib import Path
import math
import numpy as np
import pandas as pd

from src.imuca.schema import (
    MeasurementRecord,
    CANONICAL_COLUMNS,
    convert_voltage,
    convert_current,
    convert_temperature
)


# ==============================================================================
# Hardware Status Bitmask Definition (docs/HARDWARE_READINESS.md Section 3.2)
# ==============================================================================

class HardwareFlags(IntFlag):
    """8-bit hardware status flags reported in telemetry packets."""
    NOMINAL = 0x00
    INA219_OVF = 0x01          # Math overflow from INA219 bus/shunt register
    INA219_COMM_ERR = 0x02     # I2C bus NACK, arbitration lost, or bus timeout
    DS18B20_CRC_ERR = 0x04     # 1-Wire scratchpad 8-bit CRC mismatch
    DS18B20_DISCONN = 0x08     # 1-Wire sensor disconnected (pull-up +85°C / -127°C)
    RANGE_EXCEEDED = 0x10      # Reading exceeded safe operating range
    CLOCK_UNCERTAIN = 0x20     # Microcontroller timer overflow or clock resynchronization
    RESERVED_40 = 0x40         # Reserved for future auxiliary ADC channels
    RESERVED_80 = 0x80         # Reserved


def decode_status_flags(flags: int) -> List[str]:
    """Decode raw status byte into a list of human-readable flag names."""
    if flags == 0:
        return ["NOMINAL"]
    decoded = []
    for flag in HardwareFlags:
        if flag != HardwareFlags.NOMINAL and (flags & flag.value):
            decoded.append(flag.name)
    return decoded if decoded else [f"UNKNOWN_0x{flags:02X}"]


# ==============================================================================
# CCITT CRC-16 Checksum (Polynomial 0x1021)
# ==============================================================================

def compute_crc16_ccitt(data: bytes, initial: int = 0xFFFF) -> int:
    """
    Compute standard CCITT CRC-16 with polynomial 0x1021 over raw bytes.
    Matches the microcontroller firmware specification.
    """
    crc = initial
    poly = 0x1021
    for byte in data:
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ poly) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def format_crc16_hex(crc: int) -> str:
    """Format CRC-16 as 4-character uppercase hexadecimal string."""
    return f"{crc:04X}"


# ==============================================================================
# Telemetry Measurement Packet
# ==============================================================================

@dataclass
class MeasurementPacket:
    """
    Structured packet received from an acquisition source (hardware or simulation).
    Guarantees explicit metadata: timestamp, engineering units, status flags, and origin.
    """
    sequence_number: int
    elapsed_ms: float
    voltage_V: Optional[float]
    current_mA: Optional[float]
    temperature_C: Optional[float]
    status_flags: int
    flag_names: List[str]
    timestamp_utc: str
    is_simulated: bool
    data_source: str
    raw_frame: Optional[str] = None
    reference_voltage_V: Optional[float] = None
    reference_current_mA: Optional[float] = None
    reference_temperature_C: Optional[float] = None
    device_id: str = "DEV_UNKNOWN"
    experiment_id: str = "EXP_DEFAULT"

    def to_record(self) -> MeasurementRecord:
        """Convert telemetry packet to canonical MeasurementRecord."""
        status_str = "OK" if self.status_flags == 0 else ";".join(self.flag_names)
        return MeasurementRecord(
            experiment_id=self.experiment_id,
            device_id=self.device_id,
            timestamp_utc=self.timestamp_utc,
            sequence_number=self.sequence_number,
            elapsed_ms=self.elapsed_ms,
            voltage_V=self.voltage_V,
            current_mA=self.current_mA,
            temperature_C=self.temperature_C,
            status=status_str,
            data_source=self.data_source,
            reference_voltage_V=self.reference_voltage_V,
            reference_current_mA=self.reference_current_mA,
            reference_temperature_C=self.reference_temperature_C,
            notes=f"Simulated={self.is_simulated}; Flags=0x{self.status_flags:02X}"
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ==============================================================================
# Packet Serialization & Parsing (Section 3.1)
# ==============================================================================

def format_telemetry_frame(
    seq_id: int,
    elapsed_ms: float,
    voltage_mv: float,
    current_ma: float,
    temp_c: float,
    status_flags: int = 0
) -> str:
    """
    Format packet in compliance with IMUCA firmware serial protocol:
    $IMUCA,<seq_id>,<elapsed_ms>,<voltage_mv>,<current_ma>,<temp_c>,<status_flags>*<crc16>\\r\\n
    """
    payload = f"IMUCA,{seq_id},{elapsed_ms:.1f},{voltage_mv:.3f},{current_ma:.3f},{temp_c:.3f},{status_flags}"
    crc = compute_crc16_ccitt(payload.encode("ascii"))
    return f"${payload}*{format_crc16_hex(crc)}\r\n"


class PacketParsingError(Exception):
    """Base exception for telemetry frame decoding issues."""
    pass


class PacketChecksumError(PacketParsingError):
    """Raised when CRC-16 checksum fails."""
    pass


class PacketFormatError(PacketParsingError):
    """Raised when telemetry framing is malformed."""
    pass


def parse_telemetry_frame(raw_line: str, is_simulated: bool = False, source_tag: str = "serial") -> MeasurementPacket:
    """
    Parse a raw ASCII telemetry frame into a MeasurementPacket.
    Validates delimiters, payload, and CRC-16 CCITT checksum.
    """
    clean_line = raw_line.strip()
    if not clean_line.startswith("$") or "*" not in clean_line:
        raise PacketFormatError(f"Missing start '$' or CRC '*' delimiter in line: '{clean_line}'")

    body, crc_str = clean_line[1:].split("*", 1)
    crc_str = crc_str.strip()

    if len(crc_str) != 4:
        raise PacketFormatError(f"CRC-16 string must be 4 hex digits, got '{crc_str}'")

    try:
        expected_crc = int(crc_str, 16)
    except ValueError:
        raise PacketFormatError(f"Invalid CRC-16 hex value: '{crc_str}'")

    calculated_crc = compute_crc16_ccitt(body.encode("ascii"))
    if calculated_crc != expected_crc:
        raise PacketChecksumError(
            f"CRC-16 mismatch: computed 0x{calculated_crc:04X}, received 0x{expected_crc:04X}"
        )

    fields = body.split(",")
    if len(fields) != 7 or fields[0] != "IMUCA":
        raise PacketFormatError(f"Invalid packet structure: expected 7 fields starting with IMUCA, got {len(fields)}")

    try:
        seq_id = int(fields[1])
        elapsed_ms = float(fields[2])
        voltage_mv = float(fields[3])
        current_ma = float(fields[4])
        temp_c = float(fields[5])
        status_flags = int(fields[6], 0)  # supports hex or decimal
    except ValueError as e:
        raise PacketFormatError(f"Failed to parse numeric telemetry fields: {e}")

    # Voltage converted from millivolts to Volts for SI canonical alignment
    voltage_v = voltage_mv / 1000.0 if math.isfinite(voltage_mv) else None
    current_ma_val = current_ma if math.isfinite(current_ma) else None
    temp_c_val = temp_c if math.isfinite(temp_c) else None

    timestamp_utc = datetime.now(timezone.utc).isoformat()
    flag_names = decode_status_flags(status_flags)

    return MeasurementPacket(
        sequence_number=seq_id,
        elapsed_ms=elapsed_ms,
        voltage_V=voltage_v,
        current_mA=current_ma_val,
        temperature_C=temp_c_val,
        status_flags=status_flags,
        flag_names=flag_names,
        timestamp_utc=timestamp_utc,
        is_simulated=is_simulated,
        data_source=source_tag,
        raw_frame=raw_line
    )


# ==============================================================================
# Abstract Measurement Source Interface
# ==============================================================================

@dataclass
class SourceStatus:
    """Status summary of a measurement acquisition source."""
    source_type: str            # 'SIMULATION_REPLAY' | 'SERIAL_HARDWARE' | 'CSV_FILE'
    connection_state: str       # 'CONNECTED' | 'DISCONNECTED' | 'SIMULATION_MODE' | 'ERROR'
    device_name: str
    port_or_path: str
    packets_read: int
    packets_dropped: int
    crc_errors: int
    last_error_message: str = ""
    is_hardware_connected: bool = False


class MeasurementSource(ABC):
    """Abstract interface defining contract between measurement acquisition and metrology pipeline."""

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to data stream or file."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Release underlying stream or port."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Return True if stream is open and readable."""
        pass

    @abstractmethod
    def read_packet(self, timeout_s: float = 1.0) -> Optional[MeasurementPacket]:
        """Read the next measurement packet, or None if stream ended or timeout."""
        pass

    @abstractmethod
    def get_status(self) -> SourceStatus:
        """Return operational and diagnostic status."""
        pass


# ==============================================================================
# Simulation Replay Source
# ==============================================================================

class SimulationReplaySource(MeasurementSource):
    """
    Replays measurements deterministically from synthetic datasets or custom CSV files.
    Always flags is_simulated=True and connection_state='SIMULATION_MODE'.
    """

    def __init__(
        self,
        dataframe_or_path: Union[pd.DataFrame, str, Path],
        loop: bool = False,
        source_name: str = "Synthetic Scenario Replay"
    ):
        self.source_name = source_name
        self.loop = loop
        self._connected = False
        self._packets_read = 0
        self._packets_dropped = 0
        self._crc_errors = 0
        self._cursor = 0
        self._last_error = ""

        if isinstance(dataframe_or_path, (str, Path)):
            self.path_str = str(dataframe_or_path)
            self.df = pd.read_csv(dataframe_or_path)
        else:
            self.path_str = "in_memory_dataframe"
            self.df = dataframe_or_path.copy()

        # Harmonize column names
        self._prepare_dataframe()

    def _prepare_dataframe(self) -> None:
        if "sequence_number" not in self.df.columns:
            self.df["sequence_number"] = np.arange(len(self.df), dtype=int)
        if "elapsed_ms" not in self.df.columns:
            self.df["elapsed_ms"] = np.arange(len(self.df), dtype=float) * 1000.0

    def connect(self) -> bool:
        self._connected = True
        self._cursor = 0
        return True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def read_packet(self, timeout_s: float = 1.0) -> Optional[MeasurementPacket]:
        if not self._connected or self.df.empty:
            return None

        if self._cursor >= len(self.df):
            if self.loop:
                self._cursor = 0
            else:
                return None

        row = self.df.iloc[self._cursor]
        self._cursor += 1
        self._packets_read += 1

        seq_id = int(row.get("sequence_number", self._cursor - 1))
        elapsed_ms = float(row.get("elapsed_ms", (self._cursor - 1) * 1000.0))

        v_val = row.get("voltage_V", None)
        i_val = row.get("current_mA", None)
        t_val = row.get("temperature_C", None)

        ref_v = row.get("reference_voltage_V", None)
        ref_i = row.get("reference_current_mA", None)
        ref_t = row.get("reference_temperature_C", None)

        status_raw = str(row.get("status", "OK"))
        status_flags = 0
        if status_raw != "OK" and status_raw != "nan":
            # Map known status strings to flags if possible
            if "OVF" in status_raw:
                status_flags |= HardwareFlags.INA219_OVF
            if "COMM" in status_raw:
                status_flags |= HardwareFlags.INA219_COMM_ERR
            if "CRC" in status_raw:
                status_flags |= HardwareFlags.DS18B20_CRC_ERR
            if "DISCONN" in status_raw:
                status_flags |= HardwareFlags.DS18B20_DISCONN

        flag_names = decode_status_flags(status_flags)
        timestamp_utc = str(row.get("timestamp_utc", datetime.now(timezone.utc).isoformat()))
        exp_id = str(row.get("experiment_id", "SIM_RUN_01"))
        dev_id = str(row.get("device_id", "SIM_DEV_01"))

        return MeasurementPacket(
            sequence_number=seq_id,
            elapsed_ms=elapsed_ms,
            voltage_V=float(v_val) if v_val is not None and pd.notna(v_val) else None,
            current_mA=float(i_val) if i_val is not None and pd.notna(i_val) else None,
            temperature_C=float(t_val) if t_val is not None and pd.notna(t_val) else None,
            status_flags=status_flags,
            flag_names=flag_names,
            timestamp_utc=timestamp_utc,
            is_simulated=True,
            data_source="simulation_replay",
            raw_frame=None,
            reference_voltage_V=float(ref_v) if ref_v is not None and pd.notna(ref_v) else None,
            reference_current_mA=float(ref_i) if ref_i is not None and pd.notna(ref_i) else None,
            reference_temperature_C=float(ref_t) if ref_t is not None and pd.notna(ref_t) else None,
            device_id=dev_id,
            experiment_id=exp_id
        )

    def get_status(self) -> SourceStatus:
        return SourceStatus(
            source_type="SIMULATION_REPLAY",
            connection_state="SIMULATION_MODE",
            device_name=self.source_name,
            port_or_path=self.path_str,
            packets_read=self._packets_read,
            packets_dropped=self._packets_dropped,
            crc_errors=self._crc_errors,
            last_error_message=self._last_error,
            is_hardware_connected=False
        )

    def get_full_dataframe(self) -> pd.DataFrame:
        """Return the complete underlying replay dataframe."""
        return self.df.copy()


# ==============================================================================
# Serial Hardware Adapter (UART / USB-CDC Bridge)
# ==============================================================================

class SerialHardwareAdapter(MeasurementSource):
    """
    Physical hardware interface adapter for 32-bit MCU (ARM Cortex-M / ESP32 / RP2040).
    Communicates via UART/USB-CDC serial port with CCITT CRC-16 telemetry frames.

    Designed with strict defensive boundaries:
    - Never fakes physical hardware connection.
    - If pyserial is missing or port is unavailable, accurately reports DISCONNECTED.
    - Robustly logs acquisition timeouts, frame parsing errors, and CRC mismatches.
    """

    def __init__(
        self,
        port: str = "COM3",
        baud_rate: int = 115200,
        timeout_s: float = 1.0,
        device_id: str = "IMUCA_HW_DEV_01"
    ):
        self.port = port
        self.baud_rate = baud_rate
        self.timeout_s = timeout_s
        self.device_id = device_id
        self._serial_handle = None
        self._connected = False
        self._packets_read = 0
        self._packets_dropped = 0
        self._crc_errors = 0
        self._last_error = ""

    def connect(self) -> bool:
        """
        Attempt to establish connection to physical hardware UART.
        Returns False and sets descriptive error message if unavailable.
        """
        try:
            import serial
        except ImportError:
            self._last_error = "pyserial library is not installed. Run 'pip install pyserial' for hardware bridge."
            self._connected = False
            return False

        try:
            self._serial_handle = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                timeout=self.timeout_s,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            self._connected = self._serial_handle.is_open
            self._last_error = ""
            return self._connected
        except Exception as e:
            self._last_error = f"Cannot open hardware serial port '{self.port}': {e}"
            self._connected = False
            self._serial_handle = None
            return False

    def disconnect(self) -> None:
        if self._serial_handle is not None:
            try:
                self._serial_handle.close()
            except Exception:
                pass
        self._serial_handle = None
        self._connected = False

    def is_connected(self) -> bool:
        if self._serial_handle is None:
            return False
        try:
            return bool(self._serial_handle.is_open)
        except Exception:
            return False

    def read_packet(self, timeout_s: float = 1.0) -> Optional[MeasurementPacket]:
        if not self.is_connected():
            return None

        try:
            line_bytes = self._serial_handle.readline()
            if not line_bytes:
                return None  # timeout
            raw_line = line_bytes.decode("ascii", errors="replace")
            packet = parse_telemetry_frame(raw_line, is_simulated=False, source_tag=f"serial:{self.port}")
            packet.device_id = self.device_id
            self._packets_read += 1
            return packet
        except PacketChecksumError as e:
            self._crc_errors += 1
            self._packets_dropped += 1
            self._last_error = f"CRC error: {e}"
            return None
        except PacketParsingError as e:
            self._packets_dropped += 1
            self._last_error = f"Framing error: {e}"
            return None
        except Exception as e:
            self._packets_dropped += 1
            self._last_error = f"Serial I/O error: {e}"
            return None

    def get_status(self) -> SourceStatus:
        conn_state = "CONNECTED" if self.is_connected() else "DISCONNECTED"
        return SourceStatus(
            source_type="SERIAL_HARDWARE",
            connection_state=conn_state,
            device_name=f"INA219/DS18B20 Telemetry Bridge ({self.device_id})",
            port_or_path=f"{self.port} @ {self.baud_rate} baud",
            packets_read=self._packets_read,
            packets_dropped=self._packets_dropped,
            crc_errors=self._crc_errors,
            last_error_message=self._last_error,
            is_hardware_connected=self.is_connected()
        )

    def run_preflight_check(self) -> Dict[str, Any]:
        """
        Perform pre-flight verification of physical connection and environment.
        Used by Dashboard Tab 9 (Hardware Readiness).
        """
        has_pyserial = False
        try:
            import serial
            has_pyserial = True
        except ImportError:
            pass

        available_ports = []
        if has_pyserial:
            try:
                import serial.tools.list_ports
                available_ports = [p.device for p in serial.tools.list_ports.comports()]
            except Exception:
                pass

        return {
            "pyserial_installed": has_pyserial,
            "target_port": self.port,
            "baud_rate": self.baud_rate,
            "available_system_ports": available_ports,
            "port_detected": self.port in available_ports,
            "connection_status": "CONNECTED" if self.is_connected() else "DISCONNECTED",
            "validation_status": "NOT_YET_VALIDATED_ON_PHYSICAL_SENSORS",
            "advisory_message": (
                "Hardware adapter is configured and ready. Physical sensors are currently "
                "DISCONNECTED. Please connect the target microcontroller over USB-UART "
                "to transition from SIMULATION MODE to PHYSICAL MEASUREMENT."
            )
        }
