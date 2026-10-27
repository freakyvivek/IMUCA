# IMUCA Physical Hardware Integration Readiness Assessment

**Project:** IMUCA (Intelligent Measurement, Uncertainty, Calibration and Analysis)  
**Target Hardware:** Texas Instruments INA219 (DC Voltage/Current), Maxim Integrated DS18B20 (Temperature), 32-bit Microcontroller (ARM Cortex-M / ESP32 / RP2040 / ATmega), UART/USB-CDC Interface.  
**Assessment Date:** 2026-10-25  
**Auditor:** Scientific Metrology & Embedded Systems Specialist

---

## 1. Hardware Readiness Status & Executive Summary

The IMUCA metrology software stack currently operates as a **rigorous software-only foundation**. All algorithms, calibration procedures, uncertainty propagation engines, and data schemas are validated using deterministic synthetic datasets and analytical test cases.

**Hardware Validation Status:** **NOT YET VALIDATED ON PHYSICAL SENSORS.**  
No physical measurements have been collected, and no physical sensor calibration claims can be made until the embedded firmware and hardware test benches are physically connected and verified against traceable standards.

---

## 2. Hardware Readiness Matrix

| Item | Required Evidence | Current Status | Readiness Assessment & Blockers |
|---|---|---|---|
| **1. Sensor Model & Configuration** | Confirmed part numbers: TI INA219 (SOT23-8 or module), Maxim DS18B20 (TO-92 or waterproof probe). Bus address and PGA gain settings. | **Identified in Spec / Unverified on Hardware** | Default software model assumes 32 V, 3.2 A range with 12-bit ADC mode ($128\ \text{samples}$ averaging). Physical DIP/solder jumper $I^2C$ address ($0\text{x}40$ to $0\text{x}4F$) must be confirmed by embedded team. |
| **2. Measurement Range** | Documented electrical limits: Voltage: $0 - 26\ \text{V}$, Current: $0 - 3.2\ \text{A}$, Temp: $-55^\circ\text{C}$ to $+125^\circ\text{C}$. | **Defined in Schema** | Software schema validates ranges: Voltage $[0, 32\ \text{V}]$, Current $[0, 5000\ \text{mA}]$, Temp $[-40, 125^\circ\text{C}]$. Operating limits are well within physical sensor silicon capabilities. |
| **3. Manufacturer Accuracy Spec** | Datasheet tolerance under operating temperature: INA219: $\pm 0.5\%$ max gain error over temp; DS18B20: $\pm 0.5^\circ\text{C}$ from $-10^\circ\text{C}$ to $+85^\circ\text{C}$. | **Integrated into Type B Model** | Type B uncertainty budget uses datasheet limits ($a = 0.5\%$ for current, $a = 0.5^\circ\text{C}$ for temp). Awaiting physical batch characterization. |
| **4. ADC Resolution & Quantization** | INA219: 12-bit SAR ADC ($V_{\mathrm{bus}}$ LSB: $4\ \text{mV}$, $V_{\mathrm{shunt}}$ LSB: $10\ \mu\text{V}$); DS18B20: 12-bit programmable ($0.0625^\circ\text{C}$ LSB). | **Modeled in Synthetic Engine** | Software models quantization using floor/round formulas. Needs verification of conversion time ($532\ \mu\text{s}$ per INA219 sample, $750\ \text{ms}$ per DS18B20 12-bit conversion). |
| **5. Current Shunt Resistance** | Nominal value, tolerance, power rating, and temperature coefficient of resistance (TCR). | **Nominal Configured ($0.100\ \Omega \pm 0.5\%$)** | Common blue INA219 breakout boards use cheap $0.1\ \Omega$ R100 resistors with unknown TCR ($\approx 100-200\ \text{ppm/}^\circ\text{C}$). Precise 4-wire Kelvin measurement of physical shunt is required. |
| **6. Reference Instrument** | Traceable calibration standard with known uncertainty $U_{\mathrm{ref}}$ and calibration certificate. | **Missing Specification** | Synthetic tests assume ideal reference $r_i$. For physical calibration, an ISO 17025 calibrated 6.5-digit DMM (Keysight 34461A or Fluke 8846A) with $U_{\mathrm{ref}} \le 0.005\%$ is required. |
| **7. Temperature Installation** | Sensor thermal coupling, thermal grease, heat sink immersion, thermal time constant $\tau$. | **Uncharacterized** | TO-92 probe vs immersion thermowell dynamics have not been tested. Self-heating of DS18B20 during continuous parasitic powering must be prevented. |
| **8. Firmware Protocol** | Framing format, baud rate, start/stop delimiters, CRC-16 checksum, and status bitmask. | **Protocol Specified / Awaiting Firmware** | Standard ASCII and binary packet framing specified (see Section 3). Firmware implementation in Arduino/C++ is pending. |
| **9. Timestamp Source** | Clock stability, monotonic counter, crystal oscillator accuracy ($\pm 20\ \text{ppm}$ vs ceramic resonator $\pm 0.5\%$). | **Software Fallback Implemented** | Schema accepts `elapsed_ms` from microcontroller `millis()` or host monotonic clock. Microcontroller crystal drift must be measured for long-term drift experiments. |
| **10. Calibration Procedure** | Traceable calibration sweep procedure across 10 setpoints with held-out validation points. | **Procedure Implemented in Software** | `CalibrationEngine` is ready to ingest physical calibration pairs $(x_{\mathrm{dut}}, y_{\mathrm{ref}})$ and compute linear/polynomial models with data-leakage prevention. |

---

## 3. Recommended Firmware Serial Protocol (Specification for Embedded Team)

To ensure seamless integration between the microcontroller firmware and the IMUCA ingestion pipeline, the following packet format is established:

### 3.1 Packet Framing (Human-Readable ASCII & Telemetry)

```
$IMUCA,<seq_id>,<elapsed_ms>,<voltage_mv>,<current_ma>,<temp_c>,<status_flags>*<crc16>\r\n
```

- **Preamble:** `$IMUCA,`
- `seq_id`: Unsigned 32-bit sequential integer ($0, 1, 2, \ldots, 2^{32}-1$). Detects dropped packets.
- `elapsed_ms`: Microcontroller monotonic millisecond counter ($0 - 4294967295$).
- `voltage_mv`: Measured bus voltage in millivolts (e.g. `5012.4` for $5.0124\ \text{V}$).
- `current_ma`: Measured DC current in milliamperes (e.g. `982.15`).
- `temp_c`: Measured temperature in degrees Celsius (e.g. `24.625`).
- `status_flags`: 8-bit hex integer bitmask (`0x00` = Nominal).
- `*<crc16>`: Standard CCITT CRC-16 (polynomial $0\text{x}1021$) over all characters between `$` and `*`.
- **Terminator:** `\r\n` (CR + LF).

### 3.2 Status Bitmask Definition

| Bit | Name | Description |
|---|---|---|
| **Bit 0 (0x01)** | `INA219_OVF` | Math overflow flag from INA219 bus/shunt register. |
| **Bit 1 (0x02)** | `INA219_COMM_ERR` | $I^2C$ bus NACK, arbitration lost, or bus timeout. |
| **Bit 2 (0x04)** | `DS18B20_CRC_ERR` | 1-Wire scratchpad 8-bit CRC mismatch. |
| **Bit 3 (0x08)** | `DS18B20_DISCONN` | 1-Wire sensor disconnected (pull-up read as $+85^\circ\text{C}$ or $-127^\circ\text{C}$). |
| **Bit 4 (0x10)** | `RANGE_EXCEEDED` | Reading exceeded safe operating range. |
| **Bit 5 (0x20)** | `CLOCK_UNCERTAIN` | Microcontroller timer overflow or clock resynchronization event. |
| **Bit 6-7** | `RESERVED` | Reserved for future auxiliary ADC channels. |

---

## 4. Minimum Information Required from Embedded Engineer Before Live Testing

Prior to connecting physical hardware, the embedded systems engineer must confirm:

1. **Microcontroller Model & Clock Source:** Part number (e.g. ESP32, STM32F4, ATmega328P) and clock oscillator type (crystal $\pm 10\ \text{ppm}$ vs internal RC oscillator $\pm 2\%$).
2. **Serial Baud Rate & USB UART Bridge:** Target baud rate (recommended: `115200 8-N-1` or `921600` for high-rate sampling) and USB bridge IC (FTDI FT232R, CP2102, or CH340).
3. **INA219 Configuration Register Value:**
   - Shunt voltage range ($\pm 40\ \text{mV}, \pm 80\ \text{mV}, \pm 160\ \text{mV}$, or $\pm 320\ \text{mV}$).
   - Bus voltage range ($16\ \text{V}$ or $32\ \text{V}$).
   - Averaging mode ($1, 2, 4, 8, 16, 32, 64, 128\ \text{samples}$).
4. **Physical Shunt Resistor Specification:** Measured resistance (Kelvin 4-wire measurement at $25^\circ\text{C}$), power rating ($0.5\ \text{W}, 1\ \text{W}, 2\ \text{W}$), and manufacturer temperature coefficient (TCR in $\text{ppm/}^\circ\text{C}$).
5. **DS18B20 Powering Mode:** Dedicated 3-wire power ($V_{\mathrm{DD}} = 3.3\ \text{V}$ or $5\ \text{V}$) or 2-wire parasitic power on data line. (Dedicated power is required for metrological stability).
6. **Reference DMM Calibration Certificate:** Identification of laboratory reference instrument (Model, Serial Number, Certificate Date, and 1-year specification uncertainty).

---

## 5. Phased Hardware Validation Roadmap (Milestone 2)

```
[Phase 1: Loopback & Packet Framing]
  └─ Verify UART framing, CRC verification, and drop rates under synthetic serial stream.
[Phase 2: Static Bench Characterization]
  └─ Connect INA219 & DS18B20 to precision DC calibrator (e.g. Fluke 5522A / Keysight 34461A).
  └─ Record 10-point static voltage (0-24 V) and current (0-2 A) sweeps.
[Phase 3: Thermal Chamber Sweep]
  └─ Evaluate temperature coefficient of shunt resistor across 10°C to 60°C.
  └─ Characterize DS18B20 linearity against calibrated RTD / Pt100 standard.
[Phase 4: In-Situ Calibration & Verification]
  └─ Ingest physical data into IMUCA CalibrationEngine.
  └─ Generate traceable ISO 17025-compliant uncertainty budgets.
```
