"""
Unit and integration tests for IMUCA Hardware Adapter (src/imuca/hardware_adapter.py).

Verifies:
- CCITT CRC-16 polynomial 0x1021 implementation.
- Status bitmask decoding (INA219 OVF/COMM, DS18B20 CRC/DISCONN, etc.).
- Packet framing serialization ($IMUCA,...*CRC\\r\\n).
- Packet framing parsing, unit conversion, and error handling.
- Corrupted CRC detection.
- SimulationReplaySource packet generation and DataFrame access.
- SerialHardwareAdapter graceful disconnect / preflight status without physical hardware.
"""

import pytest
import numpy as np
import pandas as pd

from src.imuca.hardware_adapter import (
    compute_crc16_ccitt,
    format_crc16_hex,
    HardwareFlags,
    decode_status_flags,
    format_telemetry_frame,
    parse_telemetry_frame,
    PacketChecksumError,
    PacketFormatError,
    MeasurementPacket,
    SimulationReplaySource,
    SerialHardwareAdapter
)


def test_crc16_ccitt_known_vector():
    """Verify CRC-16 CCITT computation against standard ASCII test strings."""
    # "123456789" is standard CCITT vector: with poly 0x1021 and init 0xFFFF -> 0x29B1
    data = b"123456789"
    crc = compute_crc16_ccitt(data, initial=0xFFFF)
    assert format_crc16_hex(crc) == "29B1"


def test_status_flags_decoding():
    """Verify hardware bitmask decoding."""
    assert decode_status_flags(0) == ["NOMINAL"]
    flags = HardwareFlags.INA219_OVF | HardwareFlags.DS18B20_CRC_ERR
    decoded = decode_status_flags(flags)
    assert "INA219_OVF" in decoded
    assert "DS18B20_CRC_ERR" in decoded
    assert len(decoded) == 2


def test_telemetry_frame_roundtrip():
    """Verify serialization to ASCII frame and successful parsing with CRC validation."""
    frame = format_telemetry_frame(
        seq_id=42,
        elapsed_ms=10500.0,
        voltage_mv=5012.4,
        current_ma=982.15,
        temp_c=24.625,
        status_flags=0
    )
    assert frame.startswith("$IMUCA,42,10500.0,5012.400,982.150,24.625,0*")
    assert frame.endswith("\r\n")

    packet = parse_telemetry_frame(frame, is_simulated=True)
    assert packet.sequence_number == 42
    assert packet.elapsed_ms == 10500.0
    assert pytest.approx(packet.voltage_V, abs=1e-5) == 5.0124
    assert pytest.approx(packet.current_mA, abs=1e-3) == 982.15
    assert pytest.approx(packet.temperature_C, abs=1e-3) == 24.625
    assert packet.status_flags == 0
    assert packet.flag_names == ["NOMINAL"]
    assert packet.is_simulated is True


def test_telemetry_frame_crc_corruption():
    """Verify PacketChecksumError when frame body or CRC is altered."""
    frame = format_telemetry_frame(seq_id=1, elapsed_ms=1000.0, voltage_mv=3300.0, current_ma=100.0, temp_c=25.0)
    # Corrupt one digit in the payload
    corrupted_frame = frame.replace("3300.0", "3400.0")
    with pytest.raises(PacketChecksumError):
        parse_telemetry_frame(corrupted_frame)


def test_telemetry_frame_malformed():
    """Verify PacketFormatError on invalid delimiters or field counts."""
    with pytest.raises(PacketFormatError):
        parse_telemetry_frame("INVALID_NO_DOLLAR*1234\r\n")

    with pytest.raises(PacketFormatError):
        parse_telemetry_frame("$IMUCA,1,2,3*12\r\n")  # CRC too short


def test_simulation_replay_source():
    """Verify SimulationReplaySource loads DataFrame, reads sequential packets, and handles end-of-stream."""
    df = pd.DataFrame({
        "sequence_number": [0, 1, 2],
        "elapsed_ms": [0.0, 1000.0, 2000.0],
        "voltage_V": [5.01, 5.02, 5.00],
        "current_mA": [100.0, 101.5, 99.8],
        "temperature_C": [25.0, 25.1, 25.2],
        "status": ["OK", "OK", "INA219_OVF"]
    })

    source = SimulationReplaySource(df, loop=False, source_name="TestReplay")
    assert not source.is_connected()
    assert source.connect() is True
    assert source.is_connected() is True

    status = source.get_status()
    assert status.source_type == "SIMULATION_REPLAY"
    assert status.connection_state == "SIMULATION_MODE"
    assert status.is_hardware_connected is False

    pkt0 = source.read_packet()
    assert pkt0 is not None
    assert pkt0.sequence_number == 0
    assert pkt0.voltage_V == 5.01
    assert pkt0.is_simulated is True

    pkt1 = source.read_packet()
    assert pkt1.sequence_number == 1

    pkt2 = source.read_packet()
    assert pkt2.sequence_number == 2
    assert "INA219_OVF" in pkt2.flag_names

    # End of stream
    pkt3 = source.read_packet()
    assert pkt3 is None

    source.disconnect()
    assert not source.is_connected()


def test_serial_hardware_adapter_preflight_and_disconnected():
    """Verify SerialHardwareAdapter preflight check and safe disconnected state without hardware."""
    adapter = SerialHardwareAdapter(port="COM99", baud_rate=115200)
    # Attempting to connect to COM99 should fail gracefully without unhandled exception
    connected = adapter.connect()
    assert connected is False
    assert adapter.is_connected() is False

    status = adapter.get_status()
    assert status.connection_state == "DISCONNECTED"
    assert status.is_hardware_connected is False

    preflight = adapter.run_preflight_check()
    assert preflight["target_port"] == "COM99"
    assert preflight["validation_status"] == "NOT_YET_VALIDATED_ON_PHYSICAL_SENSORS"
    assert preflight["connection_status"] == "DISCONNECTED"
    assert "Hardware adapter is configured and ready" in preflight["advisory_message"]
