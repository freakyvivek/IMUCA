# IMUCA — Data Schema Specification and Unit Conventions

## 1. Canonical Record Schema

Every measurement record processed or emitted by IMUCA adheres to the following canonical schema:

| Column Name | Data Type | Nullable | Required | SI-Compatible Unit | Description |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `experiment_id` | `string` | No | Yes | N/A | Unique identifier for the test run or calibration campaign. |
| `device_id` | `string` | No | Yes | N/A | Hardware instrument serial number or device identifier. |
| `timestamp_utc` | `string (ISO 8601)` | No | Yes | UTC timestamp | Timestamp formatted as `YYYY-MM-DDTHH:MM:SS.sssZ`. |
| `sequence_number` | `integer` | No | Yes | Index | Monotonically increasing counter ($1, 2, 3, \dots$). |
| `elapsed_ms` | `float` | No | Yes | $\text{ms}$ ($10^{-3}\text{ s}$) | Milliseconds elapsed since start of acquisition session. |
| `voltage_V` | `float` | Yes | No | $\text{V}$ (Volt) | Observed DUT DC voltage reading. |
| `current_mA` | `float` | Yes | No | $\text{mA}$ ($10^{-3}\text{ A}$) | Observed DUT DC current reading. |
| `temperature_C` | `float` | Yes | No | $^\circ\text{C}$ (Celsius) | Observed DUT temperature reading ($T_K = T_C + 273.15$). |
| `status` | `string` | No | Yes | Code | Sensor hardware status (`OK`, `DISCONNECTED`, `ERROR_TIMEOUT`). |
| `data_source` | `string` | No | Yes | Identifier | Provenance tag (`synthetic`, `csv_import`, `serial_stream`). |
| `reference_voltage_V` | `float` | Yes | No | $\text{V}$ (Volt) | Coincident calibrated reference multimeter voltage reading. |
| `reference_current_mA` | `float` | Yes | No | $\text{mA}$ | Coincident calibrated reference ammeter current reading. |
| `reference_temperature_C`| `float` | Yes | No | $^\circ\text{C}$ | Coincident calibrated reference thermometer reading. |
| `environmental_temperature_C`| `float` | Yes | No | $^\circ\text{C}$ | Independently measured ambient room temperature. |
| `notes` | `string` | Yes | No | Text | Optional experimental or environmental annotations. |

---

## 2. Simulation Ground-Truth Separation

For synthetic datasets and simulated experiments, true values are stored in strictly separate columns:

- `true_voltage_V`
- `true_current_mA`
- `true_temperature_C`
- `is_injected_fault` (boolean)

> **Metrological Integrity Rule**:
> Ground-truth columns (`true_*`) represent mathematical setpoints and must **never** be used in place of reference instrument readings (`reference_*`). Reference instrument readings are subject to independent calibration uncertainties, whereas ground truth is used solely for algorithm verification.

---

## 3. SI Unit Conventions and Conversions

All calculations internal to the metrology engines use SI units. Display values use SI-prefixed multiples:

| Measurand | Display Unit | SI Base Unit | Transformation Function |
| :--- | :---: | :---: | :--- |
| **Voltage** | $\text{V}$ or $\text{mV}$ | $\text{V}$ | $V = V_{\text{mV}} \times 10^{-3}$ |
| **Current** | $\text{mA}$ | $\text{A}$ | $I = I_{\text{mA}} \times 10^{-3}$ |
| **Temperature** | $^\circ\text{C}$ | $\text{K}$ | $T_K = T_C + 273.15$ |

---

## 4. Quality Flags and Non-Destructive Audit Retention

Raw records are immutable. When anomalies or schema violations are detected, records are retained in the dataset with diagnostic annotations:

| Quality Flag | Severity | Trigger Condition | Handling Action |
| :--- | :---: | :--- | :--- |
| `CLEAN` | Info | All checks pass nominal criteria. | Record included in all analyses. |
| `MISSING_<COL>` | Warning | Value is null/empty. | Retained; omitted from calculation of that specific measurand. |
| `NON_FINITE` | Error | Value is `NaN`, `Inf`, or non-numeric string. | Retained; flagged as unusable for quantitative statistics. |
| `OUT_OF_RANGE` | Error | Value exceeds physical sensor span. | Retained; flagged for sensor over-range or saturation. |
| `OUTLIER_MAD_<Z>`| Warning | Median Absolute Deviation $|M_i| > 3.5$. | **Never silently deleted**. Marked for engineering review. |
| `ABRUPT_CHANGE` | Warning | $|\Delta x / \Delta t| > \text{threshold}$. | Flagged as possible step discontinuity or loose connection. |
| `DUPLICATE_SEQ` | Error | Sequence counter duplicate detected. | Flagged as communications collision or buffer repeat. |
| `SEQUENCE_GAP_<N>`| Warning | Counter skipped $N$ samples. | Flagged as communication packet dropout. |
| `BACKWARDS_TIME` | Error | Elapsed timestamp decreased. | Flagged as clock reset or sequence reordering. |
| `STATUS_<CODE>` | Error | Sensor hardware reported non-OK status. | Flagged as hardware fault (e.g. sensor disconnected). |
