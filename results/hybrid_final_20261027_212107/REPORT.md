# IMUCA — Milestone 7 final evaluation on a fresh independent suite (scored once)

> SYNTHETIC DATA ONLY. Frozen detectors evaluated once on a suite generated after freezing, with new seed roots for every run.

- Command: `python scripts/run_hybrid_iteration.py final --frozen results/hybrid_frozen_20261027_210333 --suite-config config/synthetic_suite_v5_config.json --data-root data/synthetic_v5` at 2026-10-27T15:53:58.624572+00:00
- Frozen bundle `results\hybrid_frozen_20261027_210333` (frozen_settings SHA-256 `816270d89b31d9772c2d4006071a4c88c803ac5607551395e85be5af846aa2e9`); source-code hashes verified identical to the frozen state.
- Suite `IMUCA_SYNTH_SUITE_V5_FINAL_TEST` (manifest SHA-256 `e46746bbfad9e789…`), seed roots {'calibration': 62015028, 'validation': 72025028, 'test': 84055028}.

## Overall (test runs)

| Measurand | Detector | Event F1 [CI] | Macro recall | Episode precision | FA/h [CI] | Missed | Class. accuracy | Post-fault alarm records/h | Median delay |
|---|---|---|---|---|---|---|---|---|---|
| voltage_V | Hybrid M7 (iterated) | 0.825 [0.76, 0.88] | 0.870 | 0.785 | 2.6 [1.9, 3.6] | 17 | 0.828 | 0.0 | 0 |
| voltage_V | Hybrid M6 (frozen) | 0.825 [0.76, 0.88] | 0.870 | 0.785 | 2.6 [1.9, 3.6] | 17 | 0.800 | 0.0 | 0 |
| voltage_V | Hybrid M5 (frozen) | 0.820 [0.77, 0.87] | 0.787 | 0.856 | 1.6 [1.0, 2.4] | 27 | 0.852 | 0.0 | 0 |
| voltage_V | Segment detector (existing) | 0.630 [0.55, 0.71] | 0.495 | 0.867 | 1.1 [0.7, 1.8] | 55 | – | 3.4 | 0 |
| voltage_V | GBT (all faults) | 0.546 [0.47, 0.62] | 0.422 | 0.771 | 1.6 [1.0, 2.4] | 93 | – | 0.7 | 2 |
| voltage_V | Isolation Forest | 0.217 [0.15, 0.28] | 0.216 | 0.219 | 8.9 [7.4, 10.5] | 143 | – | 0.1 | 29 |
| voltage_V | Targeted GBT | 0.387 [0.32, 0.46] | 0.263 | 0.732 | 1.0 [0.6, 1.7] | 123 | – | 0.0 | 7 |
| voltage_V | Stuck rule | 0.292 [0.26, 0.33] | 0.185 | 0.690 | 0.9 [0.5, 1.5] | 133 | – | 0.0 | 7 |
| voltage_V | Curvature detector | 0.282 [0.19, 0.38] | 0.182 | 0.629 | 1.5 [1.0, 2.3] | 122 | – | 0.0 | 1 |
| voltage_V | Tuned CUSUM | 0.910 [0.87, 0.95] | 0.848 | 0.982 | 0.1 [0.0, 0.4] | 38 | – | 222.4 | 0 |
| current_mA | Hybrid M7 (iterated) | 0.911 [0.87, 0.94] | 0.935 | 0.888 | 1.3 [0.8, 2.1] | 14 | 0.892 | 11.3 | 0 |
| current_mA | Hybrid M6 (frozen) | 0.913 [0.87, 0.95] | 0.935 | 0.893 | 1.3 [0.8, 2.0] | 14 | 0.804 | 1.5 | 0 |
| current_mA | Hybrid M5 (frozen) | 0.831 [0.77, 0.89] | 0.770 | 0.903 | 1.0 [0.6, 1.7] | 23 | 0.906 | 8.3 | 0 |
| current_mA | Segment detector (existing) | 0.508 [0.44, 0.57] | 0.524 | 0.492 | 9.0 [7.5, 10.6] | 49 | – | 1.5 | 0 |
| current_mA | GBT (all faults) | 0.831 [0.77, 0.89] | 0.796 | 0.869 | 1.9 [1.2, 2.7] | 39 | – | 0.8 | 0 |
| current_mA | Isolation Forest | 0.224 [0.16, 0.29] | 0.262 | 0.195 | 12.2 [10.5, 14.1] | 138 | – | 0.1 | 23 |
| current_mA | Targeted GBT | 0.630 [0.55, 0.70] | 0.487 | 0.892 | 0.7 [0.3, 1.2] | 91 | – | 1.5 | 3 |
| current_mA | Stuck rule | 0.332 [0.29, 0.38] | 0.204 | 0.900 | 0.2 [0.0, 0.6] | 131 | – | 0.0 | 5 |
| current_mA | Curvature detector | 0.288 [0.21, 0.36] | 0.215 | 0.439 | 3.7 [2.8, 4.8] | 122 | – | 0.0 | 0 |
| current_mA | Tuned CUSUM | 0.738 [0.68, 0.79] | 0.620 | 0.911 | 0.3 [0.1, 0.8] | 80 | – | 116.6 | 0 |
| temperature_C | Hybrid M7 (iterated) | 0.750 [0.68, 0.81] | 0.728 | 0.773 | 2.9 [2.1, 3.8] | 38 | 0.798 | 12.9 | 0 |
| temperature_C | Hybrid M6 (frozen) | 0.752 [0.68, 0.81] | 0.728 | 0.778 | 2.8 [2.1, 3.8] | 38 | 0.815 | 18.1 | 0 |
| temperature_C | Hybrid M5 (frozen) | 0.598 [0.51, 0.67] | 0.556 | 0.646 | 3.4 [2.6, 4.5] | 79 | 0.578 | 38.5 | 0 |
| temperature_C | Segment detector (existing) | 0.612 [0.55, 0.67] | 0.644 | 0.584 | 4.9 [3.8, 6.1] | 61 | – | 15.6 | 0 |
| temperature_C | GBT (all faults) | 0.649 [0.58, 0.71] | 0.609 | 0.696 | 4.2 [3.3, 5.4] | 72 | – | 0.7 | 0 |
| temperature_C | Isolation Forest | 0.456 [0.38, 0.53] | 0.340 | 0.693 | 2.2 [1.5, 3.0] | 91 | – | 1.9 | 0 |
| temperature_C | Targeted GBT | 0.459 [0.36, 0.55] | 0.360 | 0.632 | 2.4 [1.7, 3.3] | 119 | – | 8.4 | 8 |
| temperature_C | Stuck rule | 0.400 [0.32, 0.47] | 0.290 | 0.643 | 2.5 [1.8, 3.4] | 129 | – | 1.7 | 9 |
| temperature_C | Curvature detector | 0.527 [0.45, 0.60] | 0.373 | 0.901 | 0.6 [0.3, 1.1] | 74 | – | 0.0 | 0 |
| temperature_C | Tuned CUSUM | 0.586 [0.47, 0.68] | 0.414 | 1.000 | 0.0 [0.0, 0.2] | 100 | – | 96.9 | 0 |

## Per fault type: detected/events [Wilson 95 %], median delay (samples)

### voltage_V

| Fault type | n | Hybrid M7 (iterated) | Hybrid M6 (frozen) | Hybrid M5 (frozen) | Segment detector (existing) | GBT (all faults) | Tuned CUSUM |
|---|---|---|---|---|---|---|---|
| `abrupt_change` | 27 | 26/27 [0.82, 0.99], 0 | 26/27 [0.82, 0.99], 0 | 26/27 [0.82, 0.99], 0 | 26/27 [0.82, 0.99], 0 | 15/27 [0.37, 0.72], 0 | 27/27 [0.88, 1.00], 0 |
| `gain_change` | 9 | 6/9 [0.35, 0.88], 0 | 6/9 [0.35, 0.88], 0 | 3/9 [0.12, 0.65], 0 | 3/9 [0.12, 0.65], 0 | 1/9 [0.02, 0.44], 0 | 9/9 [0.70, 1.00], 0 |
| `gradual_drift` | 9 | 9/9 [0.70, 1.00], 78 | 9/9 [0.70, 1.00], 78 | 9/9 [0.70, 1.00], 106 | 1/9 [0.02, 0.44], 72 | 2/9 [0.06, 0.55], 350 | 9/9 [0.70, 1.00], 85 |
| `isolated_spike` | 72 | 65/72 [0.81, 0.95], 0 | 65/72 [0.81, 0.95], 0 | 60/72 [0.73, 0.90], 0 | 63/72 [0.78, 0.93], 0 | 17/72 [0.15, 0.35], 0 | 49/72 [0.57, 0.78], 0 |
| `offset_shift` | 18 | 13/18 [0.49, 0.88], 0 | 13/18 [0.49, 0.88], 0 | 12/18 [0.44, 0.84], 0 | 9/18 [0.29, 0.71], 0 | 8/18 [0.25, 0.66], 2 | 16/18 [0.67, 0.97], 0 |
| `stuck_signal` | 27 | 26/27 [0.82, 0.99], 6 | 26/27 [0.82, 0.99], 6 | 25/27 [0.77, 0.98], 8 | 5/27 [0.08, 0.37], 4 | 26/27 [0.82, 0.99], 7 | 14/27 [0.34, 0.69], 0 |

### current_mA

| Fault type | n | Hybrid M7 (iterated) | Hybrid M6 (frozen) | Hybrid M5 (frozen) | Segment detector (existing) | GBT (all faults) | Tuned CUSUM |
|---|---|---|---|---|---|---|---|
| `abrupt_change` | 27 | 25/27 [0.77, 0.98], 0 | 25/27 [0.77, 0.98], 0 | 25/27 [0.77, 0.98], 0 | 26/27 [0.82, 0.99], 0 | 18/27 [0.48, 0.81], 0 | 15/27 [0.37, 0.72], 0 |
| `gain_change` | 9 | 9/9 [0.70, 1.00], 0 | 9/9 [0.70, 1.00], 0 | 6/9 [0.35, 0.88], 0 | 5/9 [0.27, 0.81], 0 | 8/9 [0.56, 0.98], 0 | 9/9 [0.70, 1.00], 0 |
| `gradual_drift` | 9 | 9/9 [0.70, 1.00], 72 | 9/9 [0.70, 1.00], 72 | 5/9 [0.27, 0.81], 167 | 0/9 [0.00, 0.30], – | 6/9 [0.35, 0.88], 90 | 9/9 [0.70, 1.00], 72 |
| `isolated_spike` | 72 | 64/72 [0.80, 0.94], 0 | 64/72 [0.80, 0.94], 0 | 66/72 [0.83, 0.96], 0 | 69/72 [0.88, 0.99], 0 | 48/72 [0.55, 0.76], 0 | 36/72 [0.39, 0.61], 0 |
| `offset_shift` | 18 | 15/18 [0.61, 0.94], 0 | 15/18 [0.61, 0.94], 0 | 10/18 [0.34, 0.75], 0 | 10/18 [0.34, 0.75], 0 | 16/18 [0.67, 0.97], 0 | 10/18 [0.34, 0.75], 0 |
| `stuck_signal` | 27 | 26/27 [0.82, 0.99], 4 | 26/27 [0.82, 0.99], 4 | 27/27 [0.88, 1.00], 4 | 3/27 [0.04, 0.28], 19 | 27/27 [0.88, 1.00], 4 | 3/27 [0.04, 0.28], 0 |

### temperature_C

| Fault type | n | Hybrid M7 (iterated) | Hybrid M6 (frozen) | Hybrid M5 (frozen) | Segment detector (existing) | GBT (all faults) | Tuned CUSUM |
|---|---|---|---|---|---|---|---|
| `abrupt_change` | 27 | 22/27 [0.63, 0.92], 0 | 22/27 [0.63, 0.92], 0 | 14/27 [0.34, 0.69], 0 | 16/27 [0.41, 0.75], 0 | 17/27 [0.44, 0.78], 0 | 16/27 [0.41, 0.75], 0 |
| `gain_change` | 9 | 5/9 [0.27, 0.81], 0 | 5/9 [0.27, 0.81], 0 | 5/9 [0.27, 0.81], 0 | 5/9 [0.27, 0.81], 23 | 4/9 [0.19, 0.73], 0 | 1/9 [0.02, 0.44], 41 |
| `gradual_drift` | 9 | 8/9 [0.56, 0.98], 113 | 8/9 [0.56, 0.98], 113 | 6/9 [0.35, 0.88], 34 | 9/9 [0.70, 1.00], 5 | 8/9 [0.56, 0.98], 82 | 7/9 [0.45, 0.94], 169 |
| `isolated_spike` | 72 | 60/72 [0.73, 0.90], 0 | 60/72 [0.73, 0.90], 0 | 31/72 [0.32, 0.55], 0 | 50/72 [0.58, 0.79], 0 | 31/72 [0.32, 0.55], 0 | 23/72 [0.22, 0.43], 0 |
| `offset_shift` | 18 | 11/18 [0.39, 0.80], 0 | 11/18 [0.39, 0.80], 0 | 9/18 [0.29, 0.71], 0 | 13/18 [0.49, 0.88], 0 | 8/18 [0.25, 0.66], 0 | 7/18 [0.20, 0.61], 0 |
| `stuck_signal` | 27 | 18/27 [0.48, 0.81], 10 | 18/27 [0.48, 0.81], 10 | 18/27 [0.48, 0.81], 8 | 8/27 [0.16, 0.48], 24 | 22/27 [0.63, 0.92], 10 | 8/27 [0.16, 0.48], 0 |

## Fault classification (detected events with correct category)

| Measurand | Detector | Accuracy [CI] | per class |
|---|---|---|---|
| voltage_V | Hybrid M7 (iterated) | 0.828 [0.76, 0.88] | abrupt_change 24/26, gain_change 3/6, gradual_drift 8/9, isolated_spike 60/65, offset_shift 7/13, stuck_signal 18/26 |
| voltage_V | Hybrid M6 (frozen) | 0.800 [0.73, 0.86] | abrupt_change 23/26, gain_change 3/6, gradual_drift 8/9, isolated_spike 59/65, offset_shift 5/13, stuck_signal 18/26 |
| voltage_V | Hybrid M5 (frozen) | 0.852 [0.78, 0.90] | abrupt_change 24/26, gain_change 0/3, gradual_drift 9/9, isolated_spike 60/60, offset_shift 2/12, stuck_signal 20/25 |
| current_mA | Hybrid M7 (iterated) | 0.892 [0.83, 0.93] | abrupt_change 21/25, gain_change 7/9, gradual_drift 9/9, isolated_spike 60/64, offset_shift 10/15, stuck_signal 25/26 |
| current_mA | Hybrid M6 (frozen) | 0.804 [0.73, 0.86] | abrupt_change 21/25, gain_change 2/9, gradual_drift 9/9, isolated_spike 58/64, offset_shift 4/15, stuck_signal 25/26 |
| current_mA | Hybrid M5 (frozen) | 0.906 [0.85, 0.94] | abrupt_change 24/25, gain_change 2/6, gradual_drift 5/5, isolated_spike 65/66, offset_shift 3/10, stuck_signal 27/27 |
| temperature_C | Hybrid M7 (iterated) | 0.798 [0.72, 0.86] | abrupt_change 14/22, gain_change 3/5, gradual_drift 4/8, isolated_spike 53/60, offset_shift 8/11, stuck_signal 17/18 |
| temperature_C | Hybrid M6 (frozen) | 0.815 [0.74, 0.87] | abrupt_change 16/22, gain_change 2/5, gradual_drift 4/8, isolated_spike 57/60, offset_shift 5/11, stuck_signal 17/18 |
| temperature_C | Hybrid M5 (frozen) | 0.578 [0.47, 0.68] | abrupt_change 3/14, gain_change 2/5, gradual_drift 1/6, isolated_spike 24/31, offset_shift 4/9, stuck_signal 14/18 |

## False alarms per hour by operating context

| Measurand | Detector | steady | ramp | settling | post-event transient |
|---|---|---|---|---|---|
| voltage_V | Hybrid M7 (iterated) | 2.9 (9.98 h) | 0.0 (0.49 h) | 42.1 (0.24 h) | 38.8 (0.18 h) |
| voltage_V | Hybrid M6 (frozen) | 2.9 (9.98 h) | 0.0 (0.49 h) | 42.1 (0.24 h) | 38.8 (0.18 h) |
| voltage_V | Hybrid M5 (frozen) | 1.1 (9.98 h) | 6.1 (0.49 h) | 12.6 (0.24 h) | 44.4 (0.18 h) |
| voltage_V | Segment detector (existing) | 0.9 (9.98 h) | 0.0 (0.49 h) | 0.0 (0.24 h) | 38.8 (0.18 h) |
| voltage_V | GBT (all faults) | 1.9 (9.98 h) | 0.0 (0.49 h) | 0.0 (0.24 h) | 0.0 (0.18 h) |
| voltage_V | Tuned CUSUM | 0.1 (9.98 h) | 0.0 (0.49 h) | 0.0 (0.24 h) | 0.0 (0.18 h) |
| voltage_V | Curvature detector | 1.8 (9.98 h) | 10.2 (0.49 h) | 71.5 (0.24 h) | 0.0 (0.18 h) |
| current_mA | Hybrid M7 (iterated) | 0.7 (5.56 h) | – (0.00 h) | – (0.00 h) | 1.7 (5.44 h) |
| current_mA | Hybrid M6 (frozen) | 0.7 (5.56 h) | – (0.00 h) | – (0.00 h) | 1.5 (5.44 h) |
| current_mA | Hybrid M5 (frozen) | 0.2 (5.56 h) | – (0.00 h) | – (0.00 h) | 1.8 (5.44 h) |
| current_mA | Segment detector (existing) | 6.8 (5.56 h) | – (0.00 h) | – (0.00 h) | 16.0 (5.44 h) |
| current_mA | GBT (all faults) | 0.4 (5.56 h) | – (0.00 h) | – (0.00 h) | 3.1 (5.44 h) |
| current_mA | Tuned CUSUM | 0.7 (5.56 h) | – (0.00 h) | – (0.00 h) | 0.2 (5.44 h) |
| current_mA | Curvature detector | 9.9 (5.56 h) | – (0.00 h) | – (0.00 h) | 0.0 (5.44 h) |
| temperature_C | Hybrid M7 (iterated) | 1.7 (5.20 h) | 3.2 (3.17 h) | 1.3 (3.79 h) | 5.7 (4.04 h) |
| temperature_C | Hybrid M6 (frozen) | 1.5 (5.20 h) | 3.2 (3.17 h) | 1.3 (3.79 h) | 5.7 (4.04 h) |
| temperature_C | Hybrid M5 (frozen) | 1.2 (5.20 h) | 1.6 (3.17 h) | 1.6 (3.79 h) | 9.2 (4.04 h) |
| temperature_C | Segment detector (existing) | 0.8 (5.20 h) | 0.0 (3.17 h) | 10.6 (3.79 h) | 17.3 (4.04 h) |
| temperature_C | GBT (all faults) | 1.2 (5.20 h) | 0.3 (3.17 h) | 3.2 (3.79 h) | 9.2 (4.04 h) |
| temperature_C | Tuned CUSUM | 0.0 (5.20 h) | 0.0 (3.17 h) | 0.0 (3.79 h) | 0.0 (4.04 h) |
| temperature_C | Curvature detector | 0.2 (5.20 h) | 1.6 (3.17 h) | 0.0 (3.79 h) | 1.0 (4.04 h) |

## Spike recall by protocol phase

| Measurand | Detector | stationary | non-stationary |
|---|---|---|---|
| voltage_V | Hybrid M7 (iterated) | 61/61 | 4/11 |
| voltage_V | Hybrid M6 (frozen) | 61/61 | 4/11 |
| voltage_V | Hybrid M5 (frozen) | 57/61 | 3/11 |
| voltage_V | Segment detector (existing) | 60/61 | 3/11 |
| voltage_V | Curvature detector | 21/61 | 3/11 |
| current_mA | Hybrid M7 (iterated) | 64/72 | 0/0 |
| current_mA | Hybrid M6 (frozen) | 64/72 | 0/0 |
| current_mA | Hybrid M5 (frozen) | 66/72 | 0/0 |
| current_mA | Segment detector (existing) | 69/72 | 0/0 |
| current_mA | Curvature detector | 22/72 | 0/0 |
| temperature_C | Hybrid M7 (iterated) | 29/35 | 31/37 |
| temperature_C | Hybrid M6 (frozen) | 29/35 | 31/37 |
| temperature_C | Hybrid M5 (frozen) | 27/35 | 4/37 |
| temperature_C | Segment detector (existing) | 29/35 | 21/37 |
| temperature_C | Curvature detector | 27/35 | 30/37 |

## Strata (recall)

- voltage_V, Hybrid M7 (iterated): noise_group: noise_high 42/54, noise_low 51/54, noise_mid 52/54; variant: FD5_VA_ABRUPT_CHANGE 6/6, FD5_VA_GAIN_CHANGE 1/3, FD5_VA_GRADUAL_DRIFT 3/3, FD5_VA_ISOLATED_SPIKE 15/15, FD5_VA_MIXED 18/18, FD5_VA_OFFSET_SHIFT 2/3, FD5_VA_STUCK_SIGNAL 6/6, FD5_VB_ABRUPT_CHANGE 6/6, FD5_VB_GAIN_CHANGE 2/3, FD5_VB_GRADUAL_DRIFT 3/3, FD5_VB_ISOLATED_SPIKE 15/15, FD5_VB_MIXED 18/18, FD5_VB_OFFSET_SHIFT 2/3, FD5_VB_STUCK_SIGNAL 6/6, FD5_VC_ABRUPT_CHANGE 5/6, FD5_VC_GAIN_CHANGE 3/3, FD5_VC_GRADUAL_DRIFT 3/3, FD5_VC_ISOLATED_SPIKE 10/15, FD5_VC_MIXED 15/18, FD5_VC_OFFSET_SHIFT 1/3, FD5_VC_STUCK_SIGNAL 5/6; magnitude_bin: 10-30 sigma 66/75, <10 sigma 16/20, >=30 sigma 22/22
- voltage_V, Hybrid M6 (frozen): noise_group: noise_high 42/54, noise_low 51/54, noise_mid 52/54; variant: FD5_VA_ABRUPT_CHANGE 6/6, FD5_VA_GAIN_CHANGE 1/3, FD5_VA_GRADUAL_DRIFT 3/3, FD5_VA_ISOLATED_SPIKE 15/15, FD5_VA_MIXED 18/18, FD5_VA_OFFSET_SHIFT 2/3, FD5_VA_STUCK_SIGNAL 6/6, FD5_VB_ABRUPT_CHANGE 6/6, FD5_VB_GAIN_CHANGE 2/3, FD5_VB_GRADUAL_DRIFT 3/3, FD5_VB_ISOLATED_SPIKE 15/15, FD5_VB_MIXED 18/18, FD5_VB_OFFSET_SHIFT 2/3, FD5_VB_STUCK_SIGNAL 6/6, FD5_VC_ABRUPT_CHANGE 5/6, FD5_VC_GAIN_CHANGE 3/3, FD5_VC_GRADUAL_DRIFT 3/3, FD5_VC_ISOLATED_SPIKE 10/15, FD5_VC_MIXED 15/18, FD5_VC_OFFSET_SHIFT 1/3, FD5_VC_STUCK_SIGNAL 5/6; magnitude_bin: 10-30 sigma 66/75, <10 sigma 16/20, >=30 sigma 22/22
- voltage_V, Hybrid M5 (frozen): noise_group: noise_high 38/54, noise_low 48/54, noise_mid 49/54; variant: FD5_VA_ABRUPT_CHANGE 6/6, FD5_VA_GAIN_CHANGE 1/3, FD5_VA_GRADUAL_DRIFT 3/3, FD5_VA_ISOLATED_SPIKE 14/15, FD5_VA_MIXED 17/18, FD5_VA_OFFSET_SHIFT 1/3, FD5_VA_STUCK_SIGNAL 6/6, FD5_VB_ABRUPT_CHANGE 6/6, FD5_VB_GAIN_CHANGE 1/3, FD5_VB_GRADUAL_DRIFT 3/3, FD5_VB_ISOLATED_SPIKE 15/15, FD5_VB_MIXED 17/18, FD5_VB_OFFSET_SHIFT 2/3, FD5_VB_STUCK_SIGNAL 5/6, FD5_VC_ABRUPT_CHANGE 5/6, FD5_VC_GAIN_CHANGE 1/3, FD5_VC_GRADUAL_DRIFT 3/3, FD5_VC_ISOLATED_SPIKE 10/15, FD5_VC_MIXED 13/18, FD5_VC_OFFSET_SHIFT 1/3, FD5_VC_STUCK_SIGNAL 5/6; magnitude_bin: 10-30 sigma 63/75, <10 sigma 13/20, >=30 sigma 22/22
- current_mA, Hybrid M7 (iterated): noise_group: noise_high 48/54, noise_low 51/54, noise_mid 49/54; variant: FD5_IA_ABRUPT_CHANGE 5/6, FD5_IA_GAIN_CHANGE 3/3, FD5_IA_GRADUAL_DRIFT 3/3, FD5_IA_ISOLATED_SPIKE 15/15, FD5_IA_MIXED 16/18, FD5_IA_OFFSET_SHIFT 3/3, FD5_IA_STUCK_SIGNAL 6/6, FD5_IB_ABRUPT_CHANGE 5/6, FD5_IB_GAIN_CHANGE 3/3, FD5_IB_GRADUAL_DRIFT 3/3, FD5_IB_ISOLATED_SPIKE 13/15, FD5_IB_MIXED 16/18, FD5_IB_OFFSET_SHIFT 3/3, FD5_IB_STUCK_SIGNAL 6/6, FD5_IC_ABRUPT_CHANGE 6/6, FD5_IC_GAIN_CHANGE 3/3, FD5_IC_GRADUAL_DRIFT 3/3, FD5_IC_ISOLATED_SPIKE 12/15, FD5_IC_MIXED 16/18, FD5_IC_OFFSET_SHIFT 2/3, FD5_IC_STUCK_SIGNAL 6/6; magnitude_bin: 10-30 sigma 56/64, <10 sigma 6/10, >=30 sigma 42/43
- current_mA, Hybrid M6 (frozen): noise_group: noise_high 48/54, noise_low 51/54, noise_mid 49/54; variant: FD5_IA_ABRUPT_CHANGE 5/6, FD5_IA_GAIN_CHANGE 3/3, FD5_IA_GRADUAL_DRIFT 3/3, FD5_IA_ISOLATED_SPIKE 15/15, FD5_IA_MIXED 16/18, FD5_IA_OFFSET_SHIFT 3/3, FD5_IA_STUCK_SIGNAL 6/6, FD5_IB_ABRUPT_CHANGE 5/6, FD5_IB_GAIN_CHANGE 3/3, FD5_IB_GRADUAL_DRIFT 3/3, FD5_IB_ISOLATED_SPIKE 13/15, FD5_IB_MIXED 16/18, FD5_IB_OFFSET_SHIFT 3/3, FD5_IB_STUCK_SIGNAL 6/6, FD5_IC_ABRUPT_CHANGE 6/6, FD5_IC_GAIN_CHANGE 3/3, FD5_IC_GRADUAL_DRIFT 3/3, FD5_IC_ISOLATED_SPIKE 12/15, FD5_IC_MIXED 16/18, FD5_IC_OFFSET_SHIFT 2/3, FD5_IC_STUCK_SIGNAL 6/6; magnitude_bin: 10-30 sigma 56/64, <10 sigma 6/10, >=30 sigma 42/43
- current_mA, Hybrid M5 (frozen): noise_group: noise_high 37/54, noise_low 53/54, noise_mid 49/54; variant: FD5_IA_ABRUPT_CHANGE 6/6, FD5_IA_GAIN_CHANGE 3/3, FD5_IA_GRADUAL_DRIFT 3/3, FD5_IA_ISOLATED_SPIKE 15/15, FD5_IA_MIXED 17/18, FD5_IA_OFFSET_SHIFT 3/3, FD5_IA_STUCK_SIGNAL 6/6, FD5_IB_ABRUPT_CHANGE 6/6, FD5_IB_GAIN_CHANGE 3/3, FD5_IB_GRADUAL_DRIFT 0/3, FD5_IB_ISOLATED_SPIKE 15/15, FD5_IB_MIXED 18/18, FD5_IB_OFFSET_SHIFT 1/3, FD5_IB_STUCK_SIGNAL 6/6, FD5_IC_ABRUPT_CHANGE 4/6, FD5_IC_GAIN_CHANGE 0/3, FD5_IC_GRADUAL_DRIFT 2/3, FD5_IC_ISOLATED_SPIKE 11/15, FD5_IC_MIXED 14/18, FD5_IC_OFFSET_SHIFT 0/3, FD5_IC_STUCK_SIGNAL 6/6; magnitude_bin: 10-30 sigma 52/64, <10 sigma 7/10, >=30 sigma 42/43
- temperature_C, Hybrid M7 (iterated): noise_group: noise_high 39/54, noise_low 42/54, noise_mid 43/54; variant: FD5_TA_ABRUPT_CHANGE 6/6, FD5_TA_GAIN_CHANGE 2/3, FD5_TA_GRADUAL_DRIFT 3/3, FD5_TA_ISOLATED_SPIKE 11/15, FD5_TA_MIXED 14/18, FD5_TA_OFFSET_SHIFT 1/3, FD5_TA_STUCK_SIGNAL 5/6, FD5_TB_ABRUPT_CHANGE 5/6, FD5_TB_GAIN_CHANGE 1/3, FD5_TB_GRADUAL_DRIFT 3/3, FD5_TB_ISOLATED_SPIKE 13/15, FD5_TB_MIXED 14/18, FD5_TB_OFFSET_SHIFT 2/3, FD5_TB_STUCK_SIGNAL 5/6, FD5_TC_ABRUPT_CHANGE 3/6, FD5_TC_GAIN_CHANGE 2/3, FD5_TC_GRADUAL_DRIFT 2/3, FD5_TC_ISOLATED_SPIKE 13/15, FD5_TC_MIXED 13/18, FD5_TC_OFFSET_SHIFT 1/3, FD5_TC_STUCK_SIGNAL 5/6; magnitude_bin: 10-30 sigma 34/54, <10 sigma 4/8, >=30 sigma 55/55
- temperature_C, Hybrid M6 (frozen): noise_group: noise_high 39/54, noise_low 42/54, noise_mid 43/54; variant: FD5_TA_ABRUPT_CHANGE 6/6, FD5_TA_GAIN_CHANGE 2/3, FD5_TA_GRADUAL_DRIFT 3/3, FD5_TA_ISOLATED_SPIKE 11/15, FD5_TA_MIXED 14/18, FD5_TA_OFFSET_SHIFT 1/3, FD5_TA_STUCK_SIGNAL 5/6, FD5_TB_ABRUPT_CHANGE 5/6, FD5_TB_GAIN_CHANGE 1/3, FD5_TB_GRADUAL_DRIFT 3/3, FD5_TB_ISOLATED_SPIKE 13/15, FD5_TB_MIXED 14/18, FD5_TB_OFFSET_SHIFT 2/3, FD5_TB_STUCK_SIGNAL 5/6, FD5_TC_ABRUPT_CHANGE 3/6, FD5_TC_GAIN_CHANGE 2/3, FD5_TC_GRADUAL_DRIFT 2/3, FD5_TC_ISOLATED_SPIKE 13/15, FD5_TC_MIXED 13/18, FD5_TC_OFFSET_SHIFT 1/3, FD5_TC_STUCK_SIGNAL 5/6; magnitude_bin: 10-30 sigma 34/54, <10 sigma 4/8, >=30 sigma 55/55
- temperature_C, Hybrid M5 (frozen): noise_group: noise_high 10/54, noise_low 29/54, noise_mid 44/54; variant: FD5_TA_ABRUPT_CHANGE 4/6, FD5_TA_GAIN_CHANGE 1/3, FD5_TA_GRADUAL_DRIFT 3/3, FD5_TA_ISOLATED_SPIKE 6/15, FD5_TA_MIXED 9/18, FD5_TA_OFFSET_SHIFT 1/3, FD5_TA_STUCK_SIGNAL 5/6, FD5_TB_ABRUPT_CHANGE 5/6, FD5_TB_GAIN_CHANGE 3/3, FD5_TB_GRADUAL_DRIFT 3/3, FD5_TB_ISOLATED_SPIKE 11/15, FD5_TB_MIXED 14/18, FD5_TB_OFFSET_SHIFT 3/3, FD5_TB_STUCK_SIGNAL 5/6, FD5_TC_ABRUPT_CHANGE 1/6, FD5_TC_GAIN_CHANGE 1/3, FD5_TC_GRADUAL_DRIFT 0/3, FD5_TC_ISOLATED_SPIKE 1/15, FD5_TC_MIXED 2/18, FD5_TC_OFFSET_SHIFT 0/3, FD5_TC_STUCK_SIGNAL 5/6; magnitude_bin: 10-30 sigma 25/54, <10 sigma 3/8, >=30 sigma 26/55

## Integrity track

- voltage_V: precision 1.000, recall 1.000, FAR 0.0000; missing_samples 51/51, duplicate_sequence 18/18, communication_gap 18/18, invalid_status 37/37, non_finite 18/18
- current_mA: precision 1.000, recall 1.000, FAR 0.0000; missing_samples 55/55, duplicate_sequence 18/18, communication_gap 18/18, invalid_status 35/35, non_finite 18/18
- temperature_C: precision 1.000, recall 1.000, FAR 0.0000; missing_samples 46/46, duplicate_sequence 18/18, communication_gap 18/18, invalid_status 39/39, non_finite 18/18

## Verdict

- voltage_V: M7 F1 0.825 [0.76, 0.88] vs M6 0.825 [0.76, 0.88] (overlapping); vs M5 0.820 [0.77, 0.87] (overlapping); best single detector Tuned CUSUM 0.910 [0.87, 0.95] (overlapping with M7). FA/h M7 2.6, M6 2.6, M5 1.6, Tuned CUSUM 0.1.
- current_mA: M7 F1 0.911 [0.87, 0.94] vs M6 0.913 [0.87, 0.95] (overlapping); vs M5 0.831 [0.77, 0.89] (overlapping); best single detector GBT (all faults) 0.831 [0.77, 0.89] (overlapping with M7). FA/h M7 1.3, M6 1.3, M5 1.0, GBT (all faults) 1.9.
- temperature_C: M7 F1 0.750 [0.68, 0.81] vs M6 0.752 [0.68, 0.81] (overlapping); vs M5 0.598 [0.51, 0.67] (non-overlapping); best single detector GBT (all faults) 0.649 [0.58, 0.71] (overlapping with M7). FA/h M7 2.9, M6 2.8, M5 3.4, GBT (all faults) 4.2.
- Overlapping run-bootstrap intervals mean the difference is not established.