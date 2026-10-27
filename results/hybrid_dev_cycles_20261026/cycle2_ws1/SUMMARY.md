# Development cycle `cycle2_ws1` (profile `cycle1_lifecycle_attribution`) — v3 VALIDATION runs only

> Development evidence. Settings were selected on these validation runs (and CUSUM on calibration+validation), so the numbers are optimistic; independent evidence comes only from the final fresh-suite evaluation.

- Written 2026-10-26T06:39:36.183534+00:00; code hashes recorded in `metrics.json`.

## Overall (validation)

| Measurand | Detector | Event F1 [CI] | Macro recall | Episode precision | FA/h [CI] | Missed | Class. accuracy | Post-fault alarm records/h | Median delay |
|---|---|---|---|---|---|---|---|---|---|
| voltage_V | Hybrid M6 | 0.851 [0.75, 0.93] | 0.919 | 0.792 | 2.9 [1.6, 4.8] | 3 | 0.824 | 2.1 | 0 |
| voltage_V | Hybrid M5 (frozen) | 0.868 [0.78, 0.95] | 0.912 | 0.828 | 1.9 [0.9, 3.6] | 4 | 0.800 | 4.7 | 0 |
| voltage_V | Segment detector (existing) | 0.718 [0.60, 0.83] | 0.595 | 0.906 | 1.0 [0.3, 2.3] | 14 | – | 0.0 | 0 |
| voltage_V | GBT (all faults) | 0.588 [0.46, 0.73] | 0.491 | 0.735 | 2.5 [1.3, 4.3] | 27 | – | 0.0 | 1 |
| voltage_V | Tuned CUSUM | 0.885 [0.80, 0.94] | 0.794 | 1.000 | 0.0 [0.0, 0.7] | 16 | – | 125.8 | 0 |
| current_mA | Hybrid M6 | 0.776 [0.68, 0.88] | 0.757 | 0.797 | 2.3 [1.2, 4.0] | 7 | 0.872 | 6.1 | 0 |
| current_mA | Hybrid M5 (frozen) | 0.788 [0.70, 0.90] | 0.757 | 0.821 | 1.9 [0.9, 3.5] | 7 | 0.872 | 0.2 | 0 |
| current_mA | Segment detector (existing) | 0.545 [0.39, 0.68] | 0.634 | 0.477 | 8.8 [6.4, 11.7] | 14 | – | 3.0 | 0 |
| current_mA | GBT (all faults) | 0.893 [0.80, 0.97] | 0.884 | 0.903 | 1.3 [0.5, 2.7] | 8 | – | 5.3 | 0 |
| current_mA | Tuned CUSUM | 0.394 [0.16, 0.60] | 0.245 | 1.000 | 0.0 [0.0, 0.7] | 40 | – | 35.4 | 0 |
| temperature_C | Hybrid M6 | 0.686 [0.55, 0.80] | 0.854 | 0.573 | 5.3 [3.8, 7.3] | 9 | 0.733 | 68.3 | 0 |
| temperature_C | Hybrid M5 (frozen) | 0.727 [0.59, 0.84] | 0.685 | 0.775 | 1.3 [0.6, 2.4] | 20 | 0.676 | 105.3 | 0 |
| temperature_C | Segment detector (existing) | 0.566 [0.42, 0.68] | 0.632 | 0.512 | 5.4 [3.9, 7.4] | 18 | – | 15.2 | 0 |
| temperature_C | GBT (all faults) | 0.641 [0.46, 0.78] | 0.600 | 0.688 | 3.5 [2.3, 5.1] | 23 | – | 0.0 | 0 |
| temperature_C | Tuned CUSUM | 0.588 [0.35, 0.77] | 0.417 | 1.000 | 0.0 [0.0, 0.5] | 32 | – | 102.1 | 0 |

## Per fault type (validation): detected/events [Wilson 95 %], median delay

### voltage_V

| Fault type | n | Hybrid M6 | Hybrid M5 (frozen) | Segment detector (existing) | GBT (all faults) |
|---|---|---|---|---|---|
| `abrupt_change` | 9 | 8/9 [0.56, 0.98], 0 | 8/9 [0.56, 0.98], 0 | 8/9 [0.56, 0.98], 0 | 4/9 [0.19, 0.73], 7 |
| `gain_change` | 3 | 2/3 [0.21, 0.94], 3 | 2/3 [0.21, 0.94], 12 | 0/3 [0.00, 0.56], – | 1/3 [0.06, 0.79], 5 |
| `gradual_drift` | 3 | 3/3 [0.44, 1.00], 71 | 3/3 [0.44, 1.00], 85 | 2/3 [0.21, 0.94], 104 | 0/3 [0.00, 0.56], – |
| `isolated_spike` | 24 | 23/24 [0.80, 0.99], 0 | 22/24 [0.74, 0.98], 0 | 23/24 [0.80, 0.99], 0 | 8/24 [0.18, 0.53], 0 |
| `offset_shift` | 6 | 6/6 [0.61, 1.00], 0 | 6/6 [0.61, 1.00], 0 | 5/6 [0.44, 0.97], 0 | 5/6 [0.44, 0.97], 0 |
| `stuck_signal` | 9 | 9/9 [0.70, 1.00], 4 | 9/9 [0.70, 1.00], 5 | 2/9 [0.06, 0.55], 3 | 9/9 [0.70, 1.00], 4 |

### current_mA

| Fault type | n | Hybrid M6 | Hybrid M5 (frozen) | Segment detector (existing) | GBT (all faults) |
|---|---|---|---|---|---|
| `abrupt_change` | 9 | 9/9 [0.70, 1.00], 0 | 9/9 [0.70, 1.00], 0 | 9/9 [0.70, 1.00], 0 | 8/9 [0.56, 0.98], 0 |
| `gain_change` | 3 | 1/3 [0.06, 0.79], 0 | 1/3 [0.06, 0.79], 0 | 2/3 [0.21, 0.94], 0 | 2/3 [0.21, 0.94], 0 |
| `gradual_drift` | 3 | 1/3 [0.06, 0.79], 27 | 1/3 [0.06, 0.79], 27 | 1/3 [0.06, 0.79], 26 | 3/3 [0.44, 1.00], 212 |
| `isolated_spike` | 24 | 21/24 [0.69, 0.96], 0 | 21/24 [0.69, 0.96], 0 | 22/24 [0.74, 0.98], 0 | 18/24 [0.55, 0.88], 0 |
| `offset_shift` | 6 | 6/6 [0.61, 1.00], 0 | 6/6 [0.61, 1.00], 0 | 4/6 [0.30, 0.90], 14 | 6/6 [0.61, 1.00], 0 |
| `stuck_signal` | 9 | 9/9 [0.70, 1.00], 4 | 9/9 [0.70, 1.00], 4 | 2/9 [0.06, 0.55], 1 | 9/9 [0.70, 1.00], 4 |

### temperature_C

| Fault type | n | Hybrid M6 | Hybrid M5 (frozen) | Segment detector (existing) | GBT (all faults) |
|---|---|---|---|---|---|
| `abrupt_change` | 9 | 8/9 [0.56, 0.98], 0 | 6/9 [0.35, 0.88], 0 | 7/9 [0.45, 0.94], 0 | 7/9 [0.45, 0.94], 0 |
| `gain_change` | 3 | 2/3 [0.21, 0.94], 7 | 2/3 [0.21, 0.94], 7 | 1/3 [0.06, 0.79], 0 | 2/3 [0.21, 0.94], 0 |
| `gradual_drift` | 3 | 3/3 [0.44, 1.00], 74 | 2/3 [0.21, 0.94], 140 | 3/3 [0.44, 1.00], 74 | 2/3 [0.21, 0.94], 155 |
| `isolated_spike` | 24 | 19/24 [0.60, 0.91], 0 | 12/24 [0.31, 0.69], 0 | 19/24 [0.60, 0.91], 0 | 13/24 [0.35, 0.72], 0 |
| `offset_shift` | 6 | 6/6 [0.61, 1.00], 18 | 5/6 [0.44, 0.97], 1 | 4/6 [0.30, 0.90], 0 | 3/6 [0.19, 0.81], 0 |
| `stuck_signal` | 9 | 7/9 [0.45, 0.94], 8 | 7/9 [0.45, 0.94], 5 | 2/9 [0.06, 0.55], 35 | 4/9 [0.19, 0.73], 10 |

## Selected settings

- **voltage_V**: segment `phase_blocks` MAD 3.5, extra `none` (curvature z 8.0), stuck `gbt`, GBT thr 0.9482; CUSUM `segment` window 5 min_baseline 30 min_series 60 k 0.5 h 15; lifecycle `hysteresis` (W 30, z 2.0); attribution `first_alarm` (L 30, k 4.0).
  - CUSUM tuning: 20 controls, 6 drift runs; selected FA 0, pre-onset 0, detected 6, median delay 66.
- **current_mA**: segment `setpoint_blocks` MAD 7.0, extra `none` (curvature z 8.0), stuck `gbt`, GBT thr 0.9073; CUSUM `segment` window 135 min_baseline 30 min_series 60 k 1.0 h 10; lifecycle `latched` (W 60, z 2.0); attribution `first_alarm` (L 30, k 4.0).
  - CUSUM tuning: 20 controls, 6 drift runs; selected FA 1, pre-onset 0, detected 3, median delay 85.
- **temperature_C**: segment `setpoint_blocks` MAD 3.5, extra `none` (curvature z 8.0), stuck `gbt`, GBT thr 0.8543; CUSUM `run` window 120 min_baseline 30 min_series 60 k 0.75 h 10; lifecycle `hysteresis` (W 60, z 2.0); attribution `first_alarm` (L 30, k 4.0).
  - CUSUM tuning: 22 controls, 6 drift runs; selected FA 0, pre-onset 0, detected 4, median delay 128.

## Workstream evidence (validation)

### WS1 lifecycle: full-hybrid trials

| Measurand | Lifecycle | Event F1 | FA/h | Post-fault alarm records (total) | True episodes with >60 overhang |
|---|---|---|---|---|---|
| voltage_V | {'drift_lifecycle': 'latched'} | 0.851 | 2.9 | 24 | 0 |
| voltage_V | {'drift_lifecycle': 'hysteresis', 'clear_window': 30, 'clear_z': 2.0} | 0.851 | 2.9 | 11 | 0 |
| voltage_V | {'drift_lifecycle': 'hysteresis', 'clear_window': 60, 'clear_z': 1.5} | 0.851 | 2.9 | 24 | 0 |
| voltage_V | {'drift_lifecycle': 'hysteresis', 'clear_window': 60, 'clear_z': 2.0} | 0.851 | 2.9 | 24 | 0 |
| voltage_V | {'drift_lifecycle': 'hysteresis', 'clear_window': 60, 'clear_z': 3.0} | 0.851 | 2.9 | 24 | 0 |
| voltage_V | {'drift_lifecycle': 'hysteresis', 'clear_window': 120, 'clear_z': 2.0} | 0.851 | 2.9 | 24 | 0 |
| current_mA | {'drift_lifecycle': 'latched'} | 0.776 | 2.3 | 32 | 0 |
| current_mA | {'drift_lifecycle': 'hysteresis', 'clear_window': 30, 'clear_z': 2.0} | 0.776 | 2.3 | 32 | 0 |
| current_mA | {'drift_lifecycle': 'hysteresis', 'clear_window': 60, 'clear_z': 1.5} | 0.776 | 2.3 | 32 | 0 |
| current_mA | {'drift_lifecycle': 'hysteresis', 'clear_window': 60, 'clear_z': 2.0} | 0.776 | 2.3 | 32 | 0 |
| current_mA | {'drift_lifecycle': 'hysteresis', 'clear_window': 60, 'clear_z': 3.0} | 0.776 | 2.3 | 32 | 0 |
| current_mA | {'drift_lifecycle': 'hysteresis', 'clear_window': 120, 'clear_z': 2.0} | 0.776 | 2.3 | 32 | 0 |
| temperature_C | {'drift_lifecycle': 'latched'} | 0.686 | 5.3 | 554 | 1 |
| temperature_C | {'drift_lifecycle': 'hysteresis', 'clear_window': 30, 'clear_z': 2.0} | 0.668 | 5.9 | 125 | 0 |
| temperature_C | {'drift_lifecycle': 'hysteresis', 'clear_window': 60, 'clear_z': 1.5} | 0.686 | 5.3 | 492 | 1 |
| temperature_C | {'drift_lifecycle': 'hysteresis', 'clear_window': 60, 'clear_z': 2.0} | 0.686 | 5.3 | 490 | 1 |
| temperature_C | {'drift_lifecycle': 'hysteresis', 'clear_window': 60, 'clear_z': 3.0} | 0.672 | 5.7 | 137 | 0 |
| temperature_C | {'drift_lifecycle': 'hysteresis', 'clear_window': 120, 'clear_z': 2.0} | 0.686 | 5.3 | 524 | 1 |

### WS1 attribution trials (classification accuracy of detected events)

| Measurand | Attribution | Accuracy | offset | gain | spike | abrupt |
|---|---|---|---|---|---|---|
| voltage_V | {'attribution': 'first_alarm'} | 0.824 | 1/6 | 1/2 | 23/23 | 8/8 |
| voltage_V | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 4.0} | 0.824 | 5/6 | 0/2 | 23/23 | 5/8 |
| voltage_V | {'attribution': 'confirmed', 'confirm_window': 30, 'confirm_k': 3.0} | 0.804 | 5/6 | 0/2 | 23/23 | 4/8 |
| voltage_V | {'attribution': 'confirmed', 'confirm_window': 30, 'confirm_k': 4.0} | 0.804 | 5/6 | 0/2 | 23/23 | 4/8 |
| voltage_V | {'attribution': 'confirmed', 'confirm_window': 30, 'confirm_k': 6.0} | 0.804 | 5/6 | 0/2 | 23/23 | 4/8 |
| voltage_V | {'attribution': 'confirmed', 'confirm_window': 60, 'confirm_k': 4.0} | 0.824 | 4/6 | 0/2 | 23/23 | 6/8 |
| current_mA | {'attribution': 'first_alarm'} | 0.872 | 3/6 | 0/1 | 20/21 | 9/9 |
| current_mA | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 4.0} | 0.872 | 3/6 | 1/1 | 20/21 | 8/9 |
| current_mA | {'attribution': 'confirmed', 'confirm_window': 30, 'confirm_k': 3.0} | 0.851 | 2/6 | 1/1 | 20/21 | 8/9 |
| current_mA | {'attribution': 'confirmed', 'confirm_window': 30, 'confirm_k': 4.0} | 0.851 | 2/6 | 1/1 | 20/21 | 8/9 |
| current_mA | {'attribution': 'confirmed', 'confirm_window': 30, 'confirm_k': 6.0} | 0.872 | 2/6 | 1/1 | 21/21 | 8/9 |
| current_mA | {'attribution': 'confirmed', 'confirm_window': 60, 'confirm_k': 4.0} | 0.851 | 2/6 | 0/1 | 20/21 | 9/9 |
| temperature_C | {'attribution': 'first_alarm'} | 0.733 | 0/6 | 1/2 | 19/19 | 7/8 |
| temperature_C | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 4.0} | 0.733 | 1/6 | 1/2 | 19/19 | 6/8 |
| temperature_C | {'attribution': 'confirmed', 'confirm_window': 30, 'confirm_k': 3.0} | 0.733 | 1/6 | 1/2 | 19/19 | 6/8 |
| temperature_C | {'attribution': 'confirmed', 'confirm_window': 30, 'confirm_k': 4.0} | 0.733 | 1/6 | 1/2 | 19/19 | 6/8 |
| temperature_C | {'attribution': 'confirmed', 'confirm_window': 30, 'confirm_k': 6.0} | 0.733 | 1/6 | 1/2 | 19/19 | 6/8 |
| temperature_C | {'attribution': 'confirmed', 'confirm_window': 60, 'confirm_k': 4.0} | 0.711 | 0/6 | 1/2 | 19/19 | 6/8 |

### WS2 transient options (best per option; transient component alone)

| Measurand | Segment mode | Extra | Best F1 | at MAD | Spike recall stationary | Spike recall non-stationary | FA/h ramp | FA/h settling | FA/h post-event |
|---|---|---|---|---|---|---|---|---|---|
| voltage_V | setpoint_blocks | {"transient_extra": "none"} | 0.915 | 3.5 | 1.00 | 0.00 (1) | 0.0 | 11.6 | 29.0 |
| voltage_V | phase_blocks | {"transient_extra": "none"} | 0.924 | 3.5 | 1.00 | 0.00 (1) | 0.0 | 0.0 | 19.4 |
| voltage_V | phase_blocks_stationary_only | {"transient_extra": "none"} | 0.923 | 3.5 | 1.00 | 0.00 (1) | 0.0 | 0.0 | 19.4 |
| current_mA | setpoint_blocks | {"transient_extra": "none"} | 0.903 | 7.0 | 0.83 | – (0) | – | – | 1.9 |
| current_mA | phase_blocks | {"transient_extra": "none"} | 0.903 | 7.0 | 0.83 | – (0) | – | – | 1.9 |
| current_mA | phase_blocks_stationary_only | {"transient_extra": "none"} | 0.903 | 7.0 | 0.83 | – (0) | – | – | 1.9 |
| temperature_C | setpoint_blocks | {"transient_extra": "none"} | 0.620 | 3.5 | 0.93 | 0.56 (9) | 0.0 | 13.9 | 17.6 |
| temperature_C | phase_blocks | {"transient_extra": "none"} | 0.591 | 3.5 | 0.87 | 0.56 (9) | 0.0 | 13.3 | 17.1 |
| temperature_C | phase_blocks_stationary_only | {"transient_extra": "none"} | 0.546 | 3.5 | 0.87 | 0.00 (9) | 0.0 | 0.0 | 6.2 |

### WS3 MAD threshold (best transient F1 per threshold)

| Measurand | MAD | Best transient F1 | FA/h |
|---|---|---|---|
| voltage_V | 3.5 | 0.924 | 0.8 |
| voltage_V | 5.0 | 0.881 | 0.6 |
| voltage_V | 7.0 | 0.869 | 0.4 |
| current_mA | 3.5 | 0.637 | 8.8 |
| current_mA | 5.0 | 0.791 | 3.4 |
| current_mA | 7.0 | 0.903 | 0.8 |
| temperature_C | 3.5 | 0.620 | 5.4 |
| temperature_C | 5.0 | 0.593 | 5.6 |
| temperature_C | 7.0 | 0.542 | 5.0 |

### WS3 CUSUM (best configuration per mode and exclusion window)

| Measurand | Mode | Window | min_baseline | min_series | k | h | ARL0 ok | FA | pre-onset | detected | median delay |
|---|---|---|---|---|---|---|---|---|---|---|---|
| voltage_V | run | 5 | 30 | 60 | 0.5 | 20 | True | 0 | 0 | 6 | 74 |
| voltage_V | segment | 5 | 30 | 60 | 0.5 | 15 | True | 0 | 0 | 6 | 66 |
| current_mA | run | 45 | 30 | 60 | 0.75 | 6 | True | 8 | 2 | 4 | 24 |
| current_mA | run | 135 | 30 | 60 | 1.0 | 6 | True | 6 | 0 | 6 | 54 |
| current_mA | segment | 45 | 30 | 60 | 0.75 | 20 | True | 6 | 1 | 5 | 31 |
| current_mA | segment | 135 | 30 | 60 | 1.0 | 10 | True | 1 | 0 | 3 | 85 |
| temperature_C | run | 60 | 30 | 60 | 0.5 | 20 | True | 4 | 0 | 4 | 94 |
| temperature_C | run | 120 | 30 | 60 | 0.75 | 10 | True | 0 | 0 | 4 | 128 |
| temperature_C | run | 210 | 30 | 60 | 0.75 | 10 | True | 0 | 0 | 2 | 180 |
| temperature_C | segment | 60 | 30 | 60 | 0.5 | 15 | True | 4 | 0 | 4 | 135 |
| temperature_C | segment | 120 | 30 | 60 | 0.75 | 12 | True | 0 | 0 | 4 | 172 |
| temperature_C | segment | 210 | 30 | 60 | 0.75 | 10 | True | 0 | 0 | 2 | 226 |

### Strata (hybrid M6, validation): recall by noise group / variant / magnitude

- voltage_V: noise_group: noise_high 16/18, noise_low 17/18, noise_mid 18/18; variant: VA 17/18, VB 18/18, VC 16/18; magnitude_bin: 10-30 sigma 27/29, <10 sigma 7/7, >=30 sigma 3/3
- current_mA: noise_group: noise_high 13/18, noise_low 17/18, noise_mid 17/18; variant: IA 17/18, IB 17/18, IC 13/18; magnitude_bin: 10-30 sigma 20/22, <10 sigma 1/2, >=30 sigma 15/15
- temperature_C: noise_group: noise_high 14/18, noise_low 15/18, noise_mid 16/18; variant: TA 15/18, TB 16/18, TC 14/18; magnitude_bin: 10-30 sigma 13/16, <10 sigma 2/2, >=30 sigma 18/21