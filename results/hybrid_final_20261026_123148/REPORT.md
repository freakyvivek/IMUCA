# IMUCA — Milestone 6 final evaluation on a fresh independent suite (scored once)

> SYNTHETIC DATA ONLY. Frozen detectors evaluated once on a suite generated after freezing, with new seed roots for every run.

- Command: `python scripts/run_hybrid_iteration.py final --frozen results/hybrid_frozen_20261026_123033 --suite-config config/synthetic_suite_v4_config.json --data-root data/synthetic_v4` at 2026-10-26T07:02:54.997604+00:00
- Frozen bundle `results\hybrid_frozen_20261026_123033` (frozen_settings SHA-256 `b0b38a7961f4265f3d4108d732f2fa76f1c7b9df4e05732751ca1cfe10253514`); source-code hashes verified identical to the frozen state.
- Suite `IMUCA_SYNTH_SUITE_V4_FINAL_TEST` (manifest SHA-256 `cc68811e57386421…`), seed roots {'calibration': 61014027, 'validation': 71024027, 'test': 83054027}.

## Overall (test runs)

| Measurand | Detector | Event F1 [CI] | Macro recall | Episode precision | FA/h [CI] | Missed | Class. accuracy | Post-fault alarm records/h | Median delay |
|---|---|---|---|---|---|---|---|---|---|
| voltage_V | Hybrid M6 | 0.847 [0.79, 0.90] | 0.870 | 0.825 | 2.3 [1.6, 3.2] | 15 | 0.905 | 0.6 | 0 |
| voltage_V | Hybrid M5 (frozen) | 0.815 [0.75, 0.87] | 0.797 | 0.834 | 1.8 [1.2, 2.6] | 25 | 0.847 | 11.9 | 0 |
| voltage_V | Segment detector (existing) | 0.643 [0.56, 0.72] | 0.509 | 0.873 | 1.1 [0.7, 1.8] | 53 | – | 0.0 | 0 |
| voltage_V | GBT (all faults) | 0.577 [0.48, 0.67] | 0.449 | 0.806 | 1.3 [0.8, 2.1] | 94 | – | 0.9 | 0 |
| voltage_V | Isolation Forest | 0.236 [0.17, 0.30] | 0.261 | 0.216 | 8.8 [7.3, 10.4] | 139 | – | 0.3 | 12 |
| voltage_V | Targeted GBT | 0.414 [0.34, 0.49] | 0.301 | 0.662 | 1.5 [1.0, 2.3] | 120 | – | 0.7 | 7 |
| voltage_V | Stuck rule | 0.341 [0.29, 0.41] | 0.213 | 0.853 | 0.3 [0.1, 0.8] | 131 | – | 0.0 | 7 |
| voltage_V | Curvature detector | 0.308 [0.21, 0.40] | 0.194 | 0.755 | 0.9 [0.5, 1.5] | 126 | – | 0.0 | 1 |
| voltage_V | Tuned CUSUM | 0.922 [0.88, 0.95] | 0.867 | 0.983 | 0.1 [0.0, 0.4] | 38 | – | 292.9 | 0 |
| current_mA | Hybrid M6 | 0.867 [0.82, 0.91] | 0.882 | 0.853 | 1.7 [1.1, 2.5] | 23 | 0.813 | 0.0 | 0 |
| current_mA | Hybrid M5 (frozen) | 0.858 [0.80, 0.91] | 0.805 | 0.919 | 0.9 [0.5, 1.5] | 20 | 0.894 | 0.0 | 0 |
| current_mA | Segment detector (existing) | 0.590 [0.51, 0.66] | 0.603 | 0.578 | 7.5 [6.1, 9.0] | 41 | – | 2.6 | 0 |
| current_mA | GBT (all faults) | 0.754 [0.69, 0.81] | 0.709 | 0.805 | 3.0 [2.1, 4.0] | 41 | – | 1.4 | 0 |
| current_mA | Isolation Forest | 0.284 [0.22, 0.34] | 0.312 | 0.260 | 11.1 [9.5, 12.9] | 133 | – | 0.2 | 18 |
| current_mA | Targeted GBT | 0.596 [0.52, 0.67] | 0.457 | 0.856 | 0.9 [0.5, 1.5] | 94 | – | 0.0 | 4 |
| current_mA | Stuck rule | 0.294 [0.28, 0.33] | 0.176 | 0.900 | 0.2 [0.0, 0.6] | 134 | – | 0.0 | 4 |
| current_mA | Curvature detector | 0.294 [0.22, 0.37] | 0.205 | 0.518 | 3.6 [2.7, 4.7] | 111 | – | 0.0 | 0 |
| current_mA | Tuned CUSUM | 0.778 [0.69, 0.85] | 0.645 | 0.979 | 0.1 [0.0, 0.4] | 64 | – | 93.7 | 0 |
| temperature_C | Hybrid M6 | 0.767 [0.71, 0.82] | 0.784 | 0.750 | 3.0 [2.2, 4.0] | 37 | 0.728 | 41.0 | 0 |
| temperature_C | Hybrid M5 (frozen) | 0.655 [0.58, 0.72] | 0.697 | 0.617 | 3.8 [2.9, 4.9] | 59 | 0.476 | 98.1 | 0 |
| temperature_C | Segment detector (existing) | 0.590 [0.51, 0.66] | 0.606 | 0.574 | 4.9 [3.9, 6.1] | 60 | – | 28.2 | 0 |
| temperature_C | GBT (all faults) | 0.706 [0.64, 0.77] | 0.683 | 0.731 | 3.7 [2.8, 4.7] | 53 | – | 1.1 | 0 |
| temperature_C | Isolation Forest | 0.468 [0.37, 0.55] | 0.368 | 0.644 | 2.6 [1.9, 3.5] | 92 | – | 3.4 | 0 |
| temperature_C | Targeted GBT | 0.459 [0.37, 0.54] | 0.385 | 0.567 | 2.8 [2.0, 3.7] | 112 | – | 3.8 | 8 |
| temperature_C | Stuck rule | 0.397 [0.31, 0.47] | 0.306 | 0.566 | 2.6 [1.9, 3.6] | 126 | – | 0.1 | 9 |
| temperature_C | Curvature detector | 0.552 [0.47, 0.62] | 0.387 | 0.957 | 0.2 [0.1, 0.6] | 77 | – | 0.0 | 0 |
| temperature_C | Tuned CUSUM | 0.714 [0.61, 0.80] | 0.569 | 0.957 | 0.1 [0.0, 0.4] | 78 | – | 116.7 | 0 |

## Per fault type: detected/events [Wilson 95 %], median delay (samples)

### voltage_V

| Fault type | n | Hybrid M6 | Hybrid M5 (frozen) | Segment detector (existing) | GBT (all faults) | Tuned CUSUM |
|---|---|---|---|---|---|---|
| `abrupt_change` | 27 | 25/27 [0.77, 0.98], 0 | 25/27 [0.77, 0.98], 0 | 25/27 [0.77, 0.98], 0 | 12/27 [0.28, 0.63], 0 | 25/27 [0.77, 0.98], 0 |
| `gain_change` | 9 | 6/9 [0.35, 0.88], 0 | 4/9 [0.19, 0.73], 0 | 3/9 [0.12, 0.65], 0 | 4/9 [0.19, 0.73], 0 | 9/9 [0.70, 1.00], 0 |
| `gradual_drift` | 9 | 9/9 [0.70, 1.00], 55 | 9/9 [0.70, 1.00], 73 | 3/9 [0.12, 0.65], 58 | 2/9 [0.06, 0.55], 74 | 9/9 [0.70, 1.00], 55 |
| `isolated_spike` | 72 | 68/72 [0.87, 0.98], 0 | 63/72 [0.78, 0.93], 0 | 68/72 [0.87, 0.98], 0 | 18/72 [0.16, 0.36], 0 | 44/72 [0.50, 0.72], 0 |
| `offset_shift` | 18 | 13/18 [0.49, 0.88], 0 | 11/18 [0.39, 0.80], 0 | 8/18 [0.25, 0.66], 0 | 8/18 [0.25, 0.66], 0 | 16/18 [0.67, 0.97], 0 |
| `stuck_signal` | 27 | 26/27 [0.82, 0.99], 7 | 25/27 [0.77, 0.98], 7 | 2/27 [0.02, 0.23], 12 | 24/27 [0.72, 0.96], 5 | 21/27 [0.59, 0.89], 0 |

### current_mA

| Fault type | n | Hybrid M6 | Hybrid M5 (frozen) | Segment detector (existing) | GBT (all faults) | Tuned CUSUM |
|---|---|---|---|---|---|---|
| `abrupt_change` | 27 | 24/27 [0.72, 0.96], 0 | 25/27 [0.77, 0.98], 0 | 25/27 [0.77, 0.98], 0 | 17/27 [0.44, 0.78], 0 | 16/27 [0.41, 0.75], 0 |
| `gain_change` | 9 | 7/9 [0.45, 0.94], 0 | 5/9 [0.27, 0.81], 0 | 4/9 [0.19, 0.73], 0 | 3/9 [0.12, 0.65], 0 | 6/9 [0.35, 0.88], 18 |
| `gradual_drift` | 9 | 9/9 [0.70, 1.00], 69 | 6/9 [0.35, 0.88], 140 | 3/9 [0.12, 0.65], 35 | 7/9 [0.45, 0.94], 62 | 9/9 [0.70, 1.00], 69 |
| `isolated_spike` | 72 | 57/72 [0.68, 0.87], 0 | 65/72 [0.81, 0.95], 0 | 70/72 [0.90, 0.99], 0 | 53/72 [0.62, 0.82], 0 | 48/72 [0.55, 0.76], 0 |
| `offset_shift` | 18 | 15/18 [0.61, 0.94], 0 | 14/18 [0.55, 0.91], 0 | 13/18 [0.49, 0.88], 0 | 14/18 [0.55, 0.91], 0 | 13/18 [0.49, 0.88], 0 |
| `stuck_signal` | 27 | 27/27 [0.88, 1.00], 5 | 27/27 [0.88, 1.00], 4 | 6/27 [0.11, 0.41], 8 | 27/27 [0.88, 1.00], 4 | 6/27 [0.11, 0.41], 0 |

### temperature_C

| Fault type | n | Hybrid M6 | Hybrid M5 (frozen) | Segment detector (existing) | GBT (all faults) | Tuned CUSUM |
|---|---|---|---|---|---|---|
| `abrupt_change` | 27 | 20/27 [0.55, 0.87], 0 | 18/27 [0.48, 0.81], 0 | 20/27 [0.55, 0.87], 0 | 25/27 [0.77, 0.98], 0 | 17/27 [0.44, 0.78], 0 |
| `gain_change` | 9 | 7/9 [0.45, 0.94], 1 | 7/9 [0.45, 0.94], 1 | 5/9 [0.27, 0.81], 49 | 5/9 [0.27, 0.81], 0 | 5/9 [0.27, 0.81], 2 |
| `gradual_drift` | 9 | 8/9 [0.56, 0.98], 142 | 6/9 [0.35, 0.88], 60 | 6/9 [0.35, 0.88], 4 | 5/9 [0.27, 0.81], 71 | 8/9 [0.56, 0.98], 151 |
| `isolated_spike` | 72 | 56/72 [0.67, 0.86], 0 | 37/72 [0.40, 0.63], 0 | 50/72 [0.58, 0.79], 0 | 39/72 [0.43, 0.65], 0 | 38/72 [0.41, 0.64], 0 |
| `offset_shift` | 18 | 14/18 [0.55, 0.91], 0 | 14/18 [0.55, 0.91], 0 | 11/18 [0.39, 0.80], 0 | 12/18 [0.44, 0.84], 0 | 12/18 [0.44, 0.84], 0 |
| `stuck_signal` | 27 | 20/27 [0.55, 0.87], 10 | 21/27 [0.59, 0.89], 8 | 10/27 [0.22, 0.56], 20 | 23/27 [0.68, 0.94], 10 | 4/27 [0.06, 0.32], 0 |

## Fault classification (detected events with correct category)

| Measurand | Detector | Accuracy [CI] | per class |
|---|---|---|---|
| voltage_V | Hybrid M6 | 0.905 [0.85, 0.94] | abrupt_change 24/25, gain_change 4/6, gradual_drift 7/9, isolated_spike 64/68, offset_shift 8/13, stuck_signal 26/26 |
| voltage_V | Hybrid M5 (frozen) | 0.847 [0.78, 0.90] | abrupt_change 25/25, gain_change 0/4, gradual_drift 9/9, isolated_spike 63/63, offset_shift 0/11, stuck_signal 19/25 |
| current_mA | Hybrid M6 | 0.813 [0.74, 0.87] | abrupt_change 17/24, gain_change 3/7, gradual_drift 9/9, isolated_spike 55/57, offset_shift 6/15, stuck_signal 23/27 |
| current_mA | Hybrid M5 (frozen) | 0.894 [0.83, 0.93] | abrupt_change 22/25, gain_change 2/5, gradual_drift 6/6, isolated_spike 65/65, offset_shift 6/14, stuck_signal 26/27 |
| temperature_C | Hybrid M6 | 0.728 [0.64, 0.80] | abrupt_change 10/20, gain_change 1/7, gradual_drift 6/8, isolated_spike 55/56, offset_shift 1/14, stuck_signal 18/20 |
| temperature_C | Hybrid M5 (frozen) | 0.476 [0.38, 0.57] | abrupt_change 1/18, gain_change 2/7, gradual_drift 4/6, isolated_spike 26/37, offset_shift 2/14, stuck_signal 14/21 |

## False alarms per hour by operating context

| Measurand | Detector | steady | ramp | settling | post-event transient |
|---|---|---|---|---|---|
| voltage_V | Hybrid M6 | 2.1 (10.35 h) | 0.0 (0.61 h) | 20.5 (0.24 h) | 42.5 (0.19 h) |
| voltage_V | Hybrid M5 (frozen) | 1.2 (10.35 h) | 9.8 (0.61 h) | 0.0 (0.24 h) | 42.5 (0.19 h) |
| voltage_V | Segment detector (existing) | 0.7 (10.35 h) | 0.0 (0.61 h) | 4.1 (0.24 h) | 47.9 (0.19 h) |
| voltage_V | GBT (all faults) | 1.7 (10.35 h) | 0.0 (0.61 h) | 0.0 (0.24 h) | 0.0 (0.19 h) |
| voltage_V | Tuned CUSUM | 0.1 (10.35 h) | 0.0 (0.61 h) | 0.0 (0.24 h) | 0.0 (0.19 h) |
| voltage_V | Curvature detector | 1.3 (10.35 h) | 0.0 (0.61 h) | 45.0 (0.24 h) | 0.0 (0.19 h) |
| current_mA | Hybrid M6 | 0.2 (5.54 h) | – (0.00 h) | – (0.00 h) | 3.6 (5.03 h) |
| current_mA | Hybrid M5 (frozen) | 0.2 (5.54 h) | – (0.00 h) | – (0.00 h) | 2.4 (5.03 h) |
| current_mA | Segment detector (existing) | 4.2 (5.54 h) | – (0.00 h) | – (0.00 h) | 14.9 (5.03 h) |
| current_mA | GBT (all faults) | 1.6 (5.54 h) | – (0.00 h) | – (0.00 h) | 5.2 (5.03 h) |
| current_mA | Tuned CUSUM | 0.2 (5.54 h) | – (0.00 h) | – (0.00 h) | 0.0 (5.03 h) |
| current_mA | Curvature detector | 9.6 (5.54 h) | – (0.00 h) | – (0.00 h) | 0.0 (5.03 h) |
| temperature_C | Hybrid M6 | 1.2 (5.08 h) | 2.1 (3.27 h) | 3.1 (3.81 h) | 5.4 (4.24 h) |
| temperature_C | Hybrid M5 (frozen) | 1.2 (5.08 h) | 1.2 (3.27 h) | 3.1 (3.81 h) | 9.9 (4.24 h) |
| temperature_C | Segment detector (existing) | 0.0 (5.08 h) | 0.0 (3.27 h) | 10.5 (3.81 h) | 17.5 (4.24 h) |
| temperature_C | GBT (all faults) | 0.2 (5.08 h) | 0.3 (3.27 h) | 3.4 (3.81 h) | 10.4 (4.24 h) |
| temperature_C | Tuned CUSUM | 0.4 (5.08 h) | 0.0 (3.27 h) | 0.0 (3.81 h) | 0.0 (4.24 h) |
| temperature_C | Curvature detector | 0.0 (5.08 h) | 0.9 (3.27 h) | 0.0 (3.81 h) | 0.2 (4.24 h) |

## Spike recall by protocol phase

| Measurand | Detector | stationary | non-stationary |
|---|---|---|---|
| voltage_V | Hybrid M6 | 65/66 | 3/6 |
| voltage_V | Hybrid M5 (frozen) | 60/66 | 3/6 |
| voltage_V | Segment detector (existing) | 65/66 | 3/6 |
| voltage_V | Curvature detector | 20/66 | 1/6 |
| current_mA | Hybrid M6 | 57/72 | 0/0 |
| current_mA | Hybrid M5 (frozen) | 65/72 | 0/0 |
| current_mA | Segment detector (existing) | 70/72 | 0/0 |
| current_mA | Curvature detector | 34/72 | 0/0 |
| temperature_C | Hybrid M6 | 38/41 | 18/31 |
| temperature_C | Hybrid M5 (frozen) | 35/41 | 2/31 |
| temperature_C | Segment detector (existing) | 38/41 | 12/31 |
| temperature_C | Curvature detector | 32/41 | 18/31 |

## Strata (recall)

- voltage_V, Hybrid M6: noise_group: noise_high 47/54, noise_low 49/54, noise_mid 51/54; variant: VA 49/54, VB 51/54, VC 47/54; magnitude_bin: 10-30 sigma 71/79, <10 sigma 16/19, >=30 sigma 19/19
- voltage_V, Hybrid M5 (frozen): noise_group: noise_high 43/54, noise_low 45/54, noise_mid 49/54; variant: VA 45/54, VB 49/54, VC 43/54; magnitude_bin: 10-30 sigma 68/79, <10 sigma 12/19, >=30 sigma 19/19
- current_mA, Hybrid M6: noise_group: noise_high 46/54, noise_low 45/54, noise_mid 48/54; variant: IA 45/54, IB 48/54, IC 46/54; magnitude_bin: 10-30 sigma 53/65, <10 sigma 6/13, >=30 sigma 37/39
- current_mA, Hybrid M5 (frozen): noise_group: noise_high 45/54, noise_low 51/54, noise_mid 46/54; variant: IA 51/54, IB 46/54, IC 45/54; magnitude_bin: 10-30 sigma 58/65, <10 sigma 7/13, >=30 sigma 39/39
- temperature_C, Hybrid M6: noise_group: noise_high 32/54, noise_low 45/54, noise_mid 48/54; variant: TA 45/54, TB 48/54, TC 32/54; magnitude_bin: 10-30 sigma 33/48, <10 sigma 6/15, >=30 sigma 51/54
- temperature_C, Hybrid M5 (frozen): noise_group: noise_high 13/54, noise_low 44/54, noise_mid 46/54; variant: TA 44/54, TB 46/54, TC 13/54; magnitude_bin: 10-30 sigma 28/48, <10 sigma 4/15, >=30 sigma 37/54

## Integrity track

- voltage_V: precision 1.000, recall 1.000, FAR 0.0000; missing_samples 50/50, duplicate_sequence 18/18, communication_gap 18/18, invalid_status 35/35, non_finite 18/18
- current_mA: precision 1.000, recall 1.000, FAR 0.0000; missing_samples 60/60, duplicate_sequence 18/18, communication_gap 18/18, invalid_status 37/37, non_finite 18/18
- temperature_C: precision 1.000, recall 1.000, FAR 0.0000; missing_samples 44/44, duplicate_sequence 18/18, communication_gap 18/18, invalid_status 36/36, non_finite 18/18

## Verdict

- voltage_V: M6 F1 0.847 [0.79, 0.90] vs M5 0.815 [0.75, 0.87] (overlapping); best single detector Tuned CUSUM 0.922 [0.88, 0.95] (overlapping with M6). FA/h M6 2.3, M5 1.8, Tuned CUSUM 0.1.
- current_mA: M6 F1 0.867 [0.82, 0.91] vs M5 0.858 [0.80, 0.91] (overlapping); best single detector Tuned CUSUM 0.778 [0.69, 0.85] (overlapping with M6). FA/h M6 1.7, M5 0.9, Tuned CUSUM 0.1.
- temperature_C: M6 F1 0.767 [0.71, 0.82] vs M5 0.655 [0.58, 0.72] (overlapping); best single detector Tuned CUSUM 0.714 [0.61, 0.80] (overlapping with M6). FA/h M6 3.0, M5 3.8, Tuned CUSUM 0.1.
- Overlapping run-bootstrap intervals mean the difference is not established.