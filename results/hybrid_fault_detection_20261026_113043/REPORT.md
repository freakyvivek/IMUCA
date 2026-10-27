# IMUCA — Hybrid Fault Detector Report (v3 independent test)

> SYNTHETIC DATA ONLY. Results describe detectors on simulated faults from `config/synthetic_suite_v3_config.json`; no real-sensor performance is claimed.

- Run: `python scripts/run_hybrid_fault_detection.py` at 2026-10-26T06:00:45.879496+00:00
- Data: `data/synthetic_v3` (suite `IMUCA_SYNTH_SUITE_V3_HYBRID`, manifest `b659f64211d8c484…`, checksums verified); seed roots {'calibration': 31012027, 'validation': 41022027, 'test': 59033027} (v2 roots {'calibration': 20261101, 'validation': 20261102, 'test': 77031119}).
- Settings frozen before test scoring: `frozen_settings.json` SHA-256 `bcfb2b3bea0b177370ada88437d4f6aa1eb63201dea1003a6fbf66d28d10a326` written 2026-10-26T06:03:55.354810+00:00; test components first computed 2026-10-26T06:03:56.171105+00:00.
- Episode = consecutive alarmed records (gap ≤ 2) = one operator-facing alarm. True episode = overlaps a fault-active record (+2 samples). Timely event detection: transient/stuck = event records + 2 samples; offset/gain = first 60 samples; drift = onset → end of run.
- Intervals: Wilson 95 % for proportions, exact Poisson (Garwood) 95 % for false alarms per hour, run-level bootstrap 95 % for event F1.

## 1. Overall comparison (test runs, signal track)

| Measurand | Detector | Sample P / R / F1 | Sample FAR | Event F1 [95 % CI] | Macro timely recall | Episode precision [CI] | False alarms / h [CI] | Missed events | Events |
|---|---|---|---|---|---|---|---|---|---|
| voltage_V | Hybrid | 0.731 / 0.250 / 0.372 | 0.0267 | 0.814 [0.74, 0.88] | 0.767 | 0.866 [0.79, 0.92] | 1.5 [0.8, 2.4] | 16 | 108 |
| voltage_V | Segment detector (existing) | 0.708 / 0.088 / 0.156 | 0.0105 | 0.562 [0.46, 0.66] | 0.439 | 0.780 [0.68, 0.85] | 2.0 [1.2, 3.0] | 39 | 108 |
| voltage_V | GBT (all faults) | 0.955 / 0.093 / 0.170 | 0.0013 | 0.650 [0.53, 0.75] | 0.481 | 1.000 [0.94, 1.00] | 0.0 [0.0, 0.4] | 56 | 108 |
| voltage_V | Isolation Forest | 0.160 / 0.003 / 0.006 | 0.0050 | 0.228 [0.14, 0.30] | 0.229 | 0.227 [0.16, 0.31] | 9.1 [7.3, 11.1] | 94 | 108 |
| voltage_V | Targeted GBT (offset/gain/stuck) | 0.928 / 0.042 / 0.081 | 0.0010 | 0.319 [0.26, 0.38] | 0.198 | 0.828 [0.65, 0.92] | 0.5 [0.2, 1.2] | 87 | 108 |
| voltage_V | Stuck rule | 0.983 / 0.050 / 0.095 | 0.0002 | 0.323 [0.28, 0.38] | 0.194 | 0.950 [0.76, 0.99] | 0.1 [0.0, 0.6] | 88 | 108 |
| voltage_V | Tuned CUSUM | 0.476 / 0.296 / 0.365 | 0.0945 | 0.750 [0.67, 0.82] | 0.645 | 0.897 [0.79, 0.95] | 0.6 [0.2, 1.3] | 45 | 108 |
| current_mA | Hybrid | 0.866 / 0.148 / 0.253 | 0.0062 | 0.852 [0.77, 0.93] | 0.803 | 0.908 [0.84, 0.95] | 1.1 [0.5, 1.9] | 12 | 108 |
| current_mA | Segment detector (existing) | 0.655 / 0.107 / 0.183 | 0.0152 | 0.543 [0.44, 0.64] | 0.578 | 0.511 [0.44, 0.58] | 8.3 [6.6, 10.3] | 29 | 108 |
| current_mA | GBT (all faults) | 0.860 / 0.153 / 0.260 | 0.0067 | 0.767 [0.68, 0.84] | 0.737 | 0.800 [0.73, 0.85] | 3.1 [2.1, 4.4] | 27 | 108 |
| current_mA | Isolation Forest | 0.151 / 0.003 / 0.006 | 0.0049 | 0.227 [0.16, 0.29] | 0.281 | 0.191 [0.14, 0.26] | 12.0 [10.0, 14.4] | 92 | 108 |
| current_mA | Targeted GBT (offset/gain/stuck) | 0.992 / 0.050 / 0.095 | 0.0001 | 0.480 [0.36, 0.59] | 0.316 | 1.000 [0.90, 1.00] | 0.0 [0.0, 0.4] | 78 | 108 |
| current_mA | Stuck rule | 0.988 / 0.053 / 0.100 | 0.0002 | 0.306 [0.29, 0.35] | 0.181 | 1.000 [0.82, 1.00] | 0.0 [0.0, 0.4] | 89 | 108 |
| current_mA | Tuned CUSUM | 0.329 / 0.049 / 0.085 | 0.0268 | 0.401 [0.26, 0.51] | 0.251 | 1.000 [0.85, 1.00] | 0.0 [0.0, 0.4] | 80 | 108 |
| temperature_C | Hybrid | 0.324 / 0.255 / 0.285 | 0.1133 | 0.651 [0.54, 0.74] | 0.639 | 0.664 [0.57, 0.74] | 3.1 [2.2, 4.2] | 44 | 108 |
| temperature_C | Segment detector (existing) | 0.340 / 0.182 / 0.237 | 0.0757 | 0.542 [0.44, 0.64] | 0.565 | 0.521 [0.44, 0.60] | 5.3 [4.1, 6.8] | 46 | 108 |
| temperature_C | GBT (all faults) | 0.823 / 0.076 / 0.139 | 0.0035 | 0.675 [0.58, 0.76] | 0.655 | 0.697 [0.62, 0.76] | 3.7 [2.7, 5.0] | 38 | 108 |
| temperature_C | Isolation Forest | 0.410 / 0.018 / 0.034 | 0.0054 | 0.641 [0.53, 0.74] | 0.520 | 0.835 [0.74, 0.90] | 1.1 [0.6, 1.9] | 45 | 108 |
| temperature_C | Targeted GBT (offset/gain/stuck) | 0.708 / 0.055 / 0.101 | 0.0048 | 0.528 [0.39, 0.64] | 0.447 | 0.645 [0.53, 0.74] | 2.1 [1.4, 3.1] | 72 | 108 |
| temperature_C | Stuck rule | 0.751 / 0.050 / 0.094 | 0.0036 | 0.366 [0.27, 0.46] | 0.296 | 0.477 [0.38, 0.58] | 3.7 [2.7, 4.9] | 83 | 108 |
| temperature_C | Tuned CUSUM | 0.418 / 0.470 / 0.442 | 0.1399 | 0.632 [0.48, 0.76] | 0.471 | 0.960 [0.80, 0.99] | 0.1 [0.0, 0.4] | 58 | 108 |

## 2. Per fault type (test runs): timely recall [Wilson 95 %], median delay (samples)

### voltage_V

| Fault type | n | Hybrid | Segment detector (existing) | GBT (all faults) | Isolation Forest | Targeted GBT (offset/gain/stuck) | Stuck rule | Tuned CUSUM |
|---|---|---|---|---|---|---|---|---|
| `isolated_spike` | 48 | 45/48 [0.83, 0.98], 0 | 45/48 [0.83, 0.98], 0 | 16/48 [0.22, 0.47], 0 | 2/48 [0.01, 0.14], 0 | 1/48 [0.00, 0.11], 0 | 0/48 [0.00, 0.07], – | 27/48 [0.42, 0.69], 0 |
| `stuck_signal` | 18 | 17/18 [0.74, 0.99], 6 | 2/18 [0.03, 0.33], 2 | 16/18 [0.67, 0.97], 5 | 1/18 [0.01, 0.26], 35 | 17/18 [0.74, 0.99], 6 | 18/18 [0.82, 1.00], 6 | 4/18 [0.09, 0.45], 0 |
| `offset_shift` | 12 | 6/12 [0.25, 0.75], 0 | 5/12 [0.19, 0.68], 0 | 4/12 [0.14, 0.61], 10 | 4/12 [0.14, 0.61], 31 | 2/12 [0.05, 0.45], 37 | 2/12 [0.05, 0.45], 30 | 7/12 [0.32, 0.81], 0 |
| `gain_change` | 6 | 2/6 [0.10, 0.70], 0 | 2/6 [0.10, 0.70], 0 | 3/6 [0.19, 0.81], 0 | 1/6 [0.03, 0.56], 26 | 0/6 [0.00, 0.39], – | 0/6 [0.00, 0.39], – | 4/6 [0.30, 0.90], 0 |
| `gradual_drift` | 6 | 6/6 [0.61, 1.00], 104 | 0/6 [0.00, 0.39], – | 1/6 [0.03, 0.56], 154 | 4/6 [0.30, 0.90], 44 | 0/6 [0.00, 0.39], – | 0/6 [0.00, 0.39], – | 6/6 [0.61, 1.00], 104 |
| `abrupt_change` | 18 | 16/18 [0.67, 0.97], 0 | 15/18 [0.61, 0.94], 0 | 12/18 [0.44, 0.84], 0 | 2/18 [0.03, 0.33], 23 | 1/18 [0.01, 0.26], 5 | 0/18 [0.00, 0.18], – | 15/18 [0.61, 0.94], 0 |

Hybrid category attribution (detected events whose first alarm carries the matching category): abrupt_change 15/16, gain_change 0/2, gradual_drift 6/6, isolated_spike 45/45, offset_shift 0/6, stuck_signal 14/17.
Offset/gain eventually detected at any time after onset (hybrid): gain_change 2/6, offset_shift 9/12.

### current_mA

| Fault type | n | Hybrid | Segment detector (existing) | GBT (all faults) | Isolation Forest | Targeted GBT (offset/gain/stuck) | Stuck rule | Tuned CUSUM |
|---|---|---|---|---|---|---|---|---|
| `isolated_spike` | 48 | 46/48 [0.86, 0.99], 0 | 45/48 [0.83, 0.98], 0 | 35/48 [0.59, 0.83], 0 | 1/48 [0.00, 0.11], 0 | 3/48 [0.02, 0.17], 0 | 0/48 [0.00, 0.07], – | 15/48 [0.20, 0.45], 0 |
| `stuck_signal` | 18 | 18/18 [0.82, 1.00], 4 | 6/18 [0.16, 0.56], 5 | 18/18 [0.82, 1.00], 4 | 5/18 [0.12, 0.51], 30 | 16/18 [0.67, 0.97], 12 | 18/18 [0.82, 1.00], 4 | 3/18 [0.06, 0.39], 0 |
| `offset_shift` | 12 | 7/12 [0.32, 0.81], 10 | 7/12 [0.32, 0.81], 3 | 5/12 [0.19, 0.68], 0 | 2/12 [0.05, 0.45], 38 | 4/12 [0.14, 0.61], 16 | 1/12 [0.01, 0.35], 5 | 1/12 [0.01, 0.35], 10 |
| `gain_change` | 6 | 4/6 [0.30, 0.90], 0 | 3/6 [0.19, 0.81], 0 | 5/6 [0.44, 0.97], 0 | 1/6 [0.03, 0.56], 49 | 2/6 [0.10, 0.70], 2 | 0/6 [0.00, 0.39], – | 0/6 [0.00, 0.39], – |
| `gradual_drift` | 6 | 4/6 [0.30, 0.90], 72 | 1/6 [0.03, 0.56], 64 | 4/6 [0.30, 0.90], 95 | 6/6 [0.61, 1.00], 83 | 0/6 [0.00, 0.39], – | 0/6 [0.00, 0.39], – | 4/6 [0.30, 0.90], 72 |
| `abrupt_change` | 18 | 17/18 [0.74, 0.99], 0 | 17/18 [0.74, 0.99], 0 | 14/18 [0.55, 0.91], 0 | 1/18 [0.01, 0.26], 26 | 5/18 [0.12, 0.51], 0 | 0/18 [0.00, 0.18], – | 5/18 [0.12, 0.51], 0 |

Hybrid category attribution (detected events whose first alarm carries the matching category): abrupt_change 14/17, gain_change 1/4, gradual_drift 4/4, isolated_spike 45/46, offset_shift 2/7, stuck_signal 16/18.
Offset/gain eventually detected at any time after onset (hybrid): gain_change 4/6, offset_shift 7/12.

### temperature_C

| Fault type | n | Hybrid | Segment detector (existing) | GBT (all faults) | Isolation Forest | Targeted GBT (offset/gain/stuck) | Stuck rule | Tuned CUSUM |
|---|---|---|---|---|---|---|---|---|
| `isolated_spike` | 48 | 24/48 [0.36, 0.64], 0 | 28/48 [0.44, 0.71], 0 | 26/48 [0.40, 0.67], 0 | 31/48 [0.50, 0.77], 0 | 6/48 [0.06, 0.25], 0 | 0/48 [0.00, 0.07], – | 25/48 [0.38, 0.66], 0 |
| `stuck_signal` | 18 | 12/18 [0.44, 0.84], 9 | 10/18 [0.34, 0.75], 15 | 12/18 [0.44, 0.84], 8 | 8/18 [0.25, 0.66], 26 | 11/18 [0.39, 0.80], 10 | 17/18 [0.74, 0.99], 9 | 3/18 [0.06, 0.39], 0 |
| `offset_shift` | 12 | 8/12 [0.39, 0.86], 2 | 5/12 [0.19, 0.68], 0 | 10/12 [0.55, 0.95], 2 | 5/12 [0.19, 0.68], 0 | 8/12 [0.39, 0.86], 20 | 6/12 [0.25, 0.75], 32 | 5/12 [0.19, 0.68], 0 |
| `gain_change` | 6 | 4/6 [0.30, 0.90], 2 | 2/6 [0.10, 0.70], 34 | 3/6 [0.19, 0.81], 15 | 3/6 [0.19, 0.81], 24 | 3/6 [0.19, 0.81], 13 | 0/6 [0.00, 0.39], – | 3/6 [0.19, 0.81], 1 |
| `gradual_drift` | 6 | 4/6 [0.30, 0.90], 34 | 5/6 [0.44, 0.97], 26 | 3/6 [0.19, 0.81], 21 | 2/6 [0.10, 0.70], 22 | 3/6 [0.19, 0.81], 41 | 2/6 [0.10, 0.70], 88 | 4/6 [0.30, 0.90], 128 |
| `abrupt_change` | 18 | 12/18 [0.44, 0.84], 0 | 12/18 [0.44, 0.84], 0 | 16/18 [0.67, 0.97], 0 | 14/18 [0.55, 0.91], 0 | 5/18 [0.12, 0.51], 3 | 0/18 [0.00, 0.18], – | 10/18 [0.34, 0.75], 0 |

Hybrid category attribution (detected events whose first alarm carries the matching category): abrupt_change 4/12, gain_change 1/4, gradual_drift 1/4, isolated_spike 16/24, offset_shift 3/8, stuck_signal 9/12.
Offset/gain eventually detected at any time after onset (hybrid): gain_change 4/6, offset_shift 10/12.

## 3. False alarms during fault-free transitions and settling (test runs)

False-alarm episodes per hour of fault-free operation in each context [exact 95 % CI]:

| Measurand | Context (hours) | Hybrid | Segment detector (existing) | GBT (all faults) | Isolation Forest | Targeted GBT (offset/gain/stuck) | Stuck rule | Tuned CUSUM |
|---|---|---|---|---|---|---|---|---|
| voltage_V | steady (6.78 h) | 1.0 [0.4, 2.1] | 1.8 [0.9, 3.1] | 0.0 [0.0, 0.5] | 0.1 [0.0, 0.8] | 0.0 [0.0, 0.5] | 0.1 [0.0, 0.8] | 0.6 [0.2, 1.5] |
| voltage_V | ramp (0.35 h) | 14.2 [4.6, 33.2] | 0.0 [0.0, 10.5] | 0.0 [0.0, 10.5] | 2.8 [0.1, 15.9] | 14.2 [4.6, 33.2] | 0.0 [0.0, 10.5] | 0.0 [0.0, 10.5] |
| voltage_V | post_event_transient (0.16 h) | 12.3 [1.5, 44.5] | 43.2 [17.3, 88.9] | 0.0 [0.0, 22.7] | 517.8 [413.0, 641.1] | 0.0 [0.0, 22.7] | 0.0 [0.0, 22.7] | 0.0 [0.0, 22.7] |
| voltage_V | post_fault_aftermath (0.56 h) | 1.8 [0.0, 10.0] | 1.8 [0.0, 10.0] | 0.0 [0.0, 6.6] | 10.7 [3.9, 23.4] | 0.0 [0.0, 6.6] | 0.0 [0.0, 6.6] | 3.6 [0.4, 12.9] |
| voltage_V | protocol_plateau_settling (0.18 h) | 0.0 [0.0, 20.8] | 11.3 [1.4, 40.8] | 0.0 [0.0, 20.8] | 0.0 [0.0, 20.8] | 0.0 [0.0, 20.8] | 0.0 [0.0, 20.8] | 0.0 [0.0, 20.8] |
| current_mA | steady (3.65 h) | 0.0 [0.0, 1.0] | 4.7 [2.7, 7.5] | 0.8 [0.2, 2.4] | 0.0 [0.0, 1.0] | 0.0 [0.0, 1.0] | 0.0 [0.0, 1.0] | 0.0 [0.0, 1.0] |
| current_mA | ramp (0.00 h) | – – | – – | – – | – – | – – | – – | – – |
| current_mA | post_event_transient (3.88 h) | 2.8 [1.4, 5.1] | 16.0 [12.3, 20.5] | 6.2 [4.0, 9.2] | 29.4 [24.2, 35.3] | 0.0 [0.0, 1.0] | 0.0 [0.0, 1.0] | 0.0 [0.0, 1.0] |
| current_mA | post_fault_aftermath (0.52 h) | 0.0 [0.0, 7.0] | 11.4 [4.2, 24.9] | 9.5 [3.1, 22.2] | 17.2 [7.8, 32.6] | 0.0 [0.0, 7.0] | 0.0 [0.0, 7.0] | 0.0 [0.0, 7.0] |
| current_mA | protocol_plateau_settling (0.00 h) | – – | – – | – – | – – | – – | – – | – – |
| temperature_C | steady (4.03 h) | 1.0 [0.3, 2.5] | 0.7 [0.2, 2.2] | 0.7 [0.2, 2.2] | 0.2 [0.0, 1.4] | 0.5 [0.1, 1.8] | 1.7 [0.7, 3.6] | 0.2 [0.0, 1.4] |
| temperature_C | ramp (2.51 h) | 0.4 [0.0, 2.2] | 0.4 [0.0, 2.2] | 0.0 [0.0, 1.5] | 0.4 [0.0, 2.2] | 0.4 [0.0, 2.2] | 0.0 [0.0, 1.5] | 0.0 [0.0, 1.5] |
| temperature_C | post_event_transient (3.33 h) | 7.8 [5.1, 11.4] | 18.3 [14.0, 23.5] | 11.4 [8.1, 15.7] | 3.6 [1.9, 6.3] | 4.2 [2.3, 7.1] | 11.1 [7.8, 15.3] | 0.0 [0.0, 1.1] |
| temperature_C | post_fault_aftermath (0.51 h) | 15.8 [6.8, 31.1] | 3.9 [0.5, 14.2] | 11.8 [4.3, 25.7] | 0.0 [0.0, 7.3] | 19.7 [9.5, 36.3] | 3.9 [0.5, 14.2] | 0.0 [0.0, 7.3] |
| temperature_C | protocol_plateau_settling (3.07 h) | 2.0 [0.7, 4.3] | 14.4 [10.4, 19.3] | 5.2 [3.0, 8.5] | 0.0 [0.0, 1.2] | 2.3 [0.9, 4.7] | 3.3 [1.6, 6.0] | 0.0 [0.0, 1.2] |

Fault-free scenario groups (false-alarm episodes per hour):

| Measurand | Scenario group | hours | Hybrid | Segment detector (existing) | GBT (all faults) | Isolation Forest | Targeted GBT (offset/gain/stuck) | Stuck rule | Tuned CUSUM |
|---|---|---|---|---|---|---|---|---|---|
| voltage_V | `FD_INTEGRITY_MIX` | 0.95 | 1.1 | 0.0 | 0.0 | 11.6 | 0.0 | 0.0 | 1.1 |
| voltage_V | `FD_NONE` | 1.00 | 1.0 | 1.0 | 0.0 | 10.0 | 1.0 | 1.0 | 0.0 |
| voltage_V | `SWEEP` | 0.18 | 0.0 | 5.5 | 0.0 | 38.2 | 0.0 | 0.0 | 0.0 |
| voltage_V | `VOLT_LONG_TRANSITIONS` | 1.00 | 0.0 | 3.0 | 0.0 | 19.0 | 0.0 | 0.0 | 0.0 |
| current_mA | `CURR_LONG_TRANSITIONS` | 1.00 | 0.0 | 10.0 | 0.0 | 23.0 | 0.0 | 0.0 | 0.0 |
| current_mA | `FD_INTEGRITY_MIX` | 0.95 | 0.0 | 16.9 | 4.2 | 14.8 | 0.0 | 0.0 | 0.0 |
| current_mA | `FD_NONE` | 1.00 | 0.0 | 12.0 | 8.0 | 14.0 | 0.0 | 0.0 | 0.0 |
| current_mA | `SWEEP` | 0.28 | 0.0 | 10.8 | 0.0 | 10.8 | 0.0 | 0.0 | 0.0 |
| temperature_C | `FD_INTEGRITY_MIX` | 0.94 | 8.5 | 8.5 | 9.6 | 4.3 | 5.3 | 4.3 | 0.0 |
| temperature_C | `FD_NONE` | 1.00 | 8.0 | 8.0 | 6.0 | 3.0 | 5.0 | 4.0 | 0.0 |
| temperature_C | `PLATEAUS` | 1.75 | 0.0 | 8.0 | 4.0 | 0.6 | 0.0 | 9.1 | 0.0 |
| temperature_C | `TEMP_LONG_TRANSITIONS` | 0.92 | 0.0 | 8.7 | 0.0 | 0.0 | 0.0 | 4.4 | 0.0 |
| temperature_C | `TEMP_RAMPS_FAST_PROBE` | 0.99 | 1.0 | 4.1 | 0.0 | 0.0 | 0.0 | 3.0 | 1.0 |

## 4. Integrity track (deterministic rules, identical for every detector; test runs)

| Measurand | Precision | Recall | FAR | Per-class recall |
|---|---|---|---|---|
| voltage_V | 1.000 | 1.000 | 0.0000 | missing_samples 37/37, duplicate_sequence 12/12, communication_gap 12/12, invalid_status 22/22, non_finite 12/12 |
| current_mA | 1.000 | 1.000 | 0.0000 | missing_samples 34/34, duplicate_sequence 12/12, communication_gap 12/12, invalid_status 25/25, non_finite 12/12 |
| temperature_C | 1.000 | 1.000 | 0.0000 | missing_samples 42/42, duplicate_sequence 12/12, communication_gap 12/12, invalid_status 23/23, non_finite 12/12 |

## 5. Selection on validation runs (test not used)

- **voltage_V**: hybrid segment mode `phase_blocks` (MAD threshold 5.0), stuck mode `gbt`, targeted-GBT config #1 at validation FAR target 0.002 (threshold 0.983); validation event F1 0.868, FA/h 1.9. CUSUM mode `segment`, transition window 5, k = 0.5, h = 15 (tuning: 20 controls, 6 drift runs; FA 0, detected 6).
- **current_mA**: hybrid segment mode `setpoint_blocks` (MAD threshold 7.0), stuck mode `rule`, targeted-GBT config #0 at validation FAR target 0.001 (threshold 0.9838); validation event F1 0.788, FA/h 1.9. CUSUM mode `segment`, transition window 135, k = 1.0, h = 10 (tuning: 20 controls, 6 drift runs; FA 1, detected 3).
- **temperature_C**: hybrid segment mode `phase_blocks_stationary_only` (MAD threshold 7.0), stuck mode `gbt`, targeted-GBT config #0 at validation FAR target 0.001 (threshold 0.8543); validation event F1 0.727, FA/h 1.3. CUSUM mode `run`, transition window 120, k = 0.75, h = 10 (tuning: 22 controls, 6 drift runs; FA 0, detected 4).

Validation evidence for the two investigations (hybrid with the selected targeted GBT and threshold; best configuration per option, full grid in `metrics.json`):

| Measurand | Option | Best val event F1 | at MAD / stuck mode | Val stuck recall | Val FA/h | Val settling FA/h |
|---|---|---|---|---|---|---|
| voltage_V | segment = `setpoint_blocks` | 0.840 | 5.0 / gbt | 1.00 | 1.9 | 0.0 |
| voltage_V | segment = `phase_blocks` | 0.868 | 5.0 / gbt | 1.00 | 1.9 | 0.0 |
| voltage_V | segment = `phase_blocks_stationary_only` | 0.840 | 5.0 / gbt | 1.00 | 1.9 | 0.0 |
| voltage_V | stuck = `gbt` | 0.868 | 5.0 / gbt | 1.00 | 1.9 | 0.0 |
| voltage_V | stuck = `rule` | 0.864 | 5.0 / rule | 1.00 | 1.9 | 0.0 |
| voltage_V | stuck = `gbt_or_rule` | 0.864 | 5.0 / gbt_or_rule | 1.00 | 1.9 | 0.0 |
| voltage_V | MAD = `3.5` | 0.857 | 3.5 / gbt | 1.00 | 2.1 | 0.0 |
| voltage_V | MAD = `5.0` | 0.868 | 5.0 / gbt | 1.00 | 1.9 | 0.0 |
| voltage_V | MAD = `7.0` | 0.866 | 7.0 / gbt | 1.00 | 1.7 | 0.0 |
| current_mA | segment = `setpoint_blocks` | 0.788 | 7.0 / rule | 1.00 | 1.9 | – |
| current_mA | segment = `phase_blocks` | 0.788 | 7.0 / rule | 1.00 | 1.9 | – |
| current_mA | segment = `phase_blocks_stationary_only` | 0.788 | 7.0 / rule | 1.00 | 1.9 | – |
| current_mA | stuck = `gbt` | 0.772 | 7.0 / gbt | 0.78 | 1.7 | – |
| current_mA | stuck = `rule` | 0.788 | 7.0 / rule | 1.00 | 1.9 | – |
| current_mA | stuck = `gbt_or_rule` | 0.788 | 7.0 / gbt_or_rule | 1.00 | 1.9 | – |
| current_mA | MAD = `3.5` | 0.630 | 3.5 / rule | 1.00 | 9.9 | – |
| current_mA | MAD = `5.0` | 0.718 | 5.0 / rule | 1.00 | 4.6 | – |
| current_mA | MAD = `7.0` | 0.788 | 7.0 / rule | 1.00 | 1.9 | – |
| temperature_C | segment = `setpoint_blocks` | 0.688 | 7.0 / gbt | 0.78 | 4.6 | 13.3 |
| temperature_C | segment = `phase_blocks` | 0.675 | 3.5 / gbt | 0.78 | 5.2 | 13.3 |
| temperature_C | segment = `phase_blocks_stationary_only` | 0.727 | 7.0 / gbt | 0.78 | 1.3 | 0.0 |
| temperature_C | stuck = `gbt` | 0.727 | 7.0 / gbt | 0.78 | 1.3 | 0.0 |
| temperature_C | stuck = `rule` | 0.623 | 7.0 / rule | 0.78 | 7.5 | 15.6 |
| temperature_C | stuck = `gbt_or_rule` | 0.641 | 7.0 / gbt_or_rule | 1.00 | 7.5 | 15.6 |
| temperature_C | MAD = `3.5` | 0.713 | 3.5 / gbt | 0.78 | 1.8 | 0.0 |
| temperature_C | MAD = `5.0` | 0.692 | 5.0 / gbt | 0.78 | 1.8 | 0.0 |
| temperature_C | MAD = `7.0` | 0.727 | 7.0 / gbt | 0.78 | 1.3 | 0.0 |

## 6. Investigations

- **Stuck (voltage_V, test):** GBT(all) 16/18, targeted GBT 17/18, stuck rule 18/18 (median delay 6), hybrid 17/18.
- **Stuck (current_mA, test):** GBT(all) 18/18, targeted GBT 16/18, stuck rule 18/18 (median delay 4), hybrid 18/18.
- **Stuck (temperature_C, test):** GBT(all) 12/18, targeted GBT 11/18, stuck rule 17/18 (median delay 9), hybrid 12/18.
- **Settling (voltage_V, test, 0.18 h fault-free settling):** existing segment detector 11.3 false-alarm episodes/h [1.4, 40.8]; hybrid 0.0 [0.0, 20.8] with segment mode `phase_blocks`.
- **Settling (temperature_C, test, 3.07 h fault-free settling):** existing segment detector 14.4 false-alarm episodes/h [10.4, 19.3]; hybrid 2.0 [0.7, 4.3] with segment mode `phase_blocks_stationary_only`.

## 7. Verdict (test runs)

- voltage_V: hybrid event F1 0.814 [0.74, 0.88] vs best individual detector (Tuned CUSUM) 0.750 [0.67, 0.82]; FA/h hybrid 1.5 vs 0.6. Bootstrap intervals overlap: the difference is not established.
- current_mA: hybrid event F1 0.852 [0.77, 0.93] vs best individual detector (GBT (all faults)) 0.767 [0.68, 0.84]; FA/h hybrid 1.1 vs 3.1. Bootstrap intervals overlap: the difference is not established.
- temperature_C: hybrid event F1 0.651 [0.54, 0.74] vs best individual detector (GBT (all faults)) 0.675 [0.58, 0.76]; FA/h hybrid 3.1 vs 3.7. Bootstrap intervals overlap: the difference is not established.
- These statements cover only the simulated fault and noise models of the v3 suite; event counts per class and measurand are 6–48, so per-class intervals are wide.

## 8. Limitations

- Synthetic data only; the generator and the detectors share simulated noise models, which favours learned components.
- The segment component uses whole protocol segments (non-causal within a segment): its decisions are final only when the segment ends. The GBT, stuck-rule and CUSUM components are causal.
- The drift component needs a reference instrument and a static calibration (laboratory verification); drift cannot be separated from a true process change without a reference.
- Offset and gain faults are only distinguishable near onset; a persistent fault missed at onset is usually caught later by the CUSUM, but that is counted as a late detection, not a timely one.
- Protocol information (set-point index, protocol phase) is used for segmentation and transition masking, as an operator schedule would provide; it is not used as a model feature.
- Thresholds were selected at validation operating points; test false-alarm rates can differ.
- Stuck detection by the identical-run rule is impossible when the expected repeat probability is high (coarse quantisation, very low noise).
- Not integrated into the application, the R1-R5 decision engine or any calibration step.
- Drift alarms are latched until the next re-baseline point or the end of the run, so sample-level false-alarm rates of the hybrid and of the CUSUM are inflated after any CUSUM alarm (including alarms triggered by real spikes or offsets); episode-level metrics are the intended operating measure.
- Category attribution is reliable for spikes, stuck signals and drift but weak for offset and gain changes (the segment detector often fires first on the step and labels it 'transient').
- Mixed-fault runs place several faults in one run, so a 'timely' offset detection can be triggered by a co-occurring transient fault inside the 60-sample window.
- The selected MAD thresholds for current and temperature (7.0) lie on the upper edge of the validation grid; the current CUSUM tuning detected only 3/6 tuning drift runs with 1 false alarm.
- The temperature hybrid chose 'phase_blocks_stationary_only', which removes transient detection during ramps and settling; spikes there are left to other components and are often missed (24/48 temperature spikes detected).
- The first full run (results/hybrid_fault_detection_20261026_112521) scored the test runs but crashed while plotting; it was re-run unchanged. Its frozen settings and every test alarm are identical to this run (checked).
