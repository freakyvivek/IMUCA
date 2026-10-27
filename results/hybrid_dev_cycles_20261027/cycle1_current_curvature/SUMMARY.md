# Development cycle `cycle1_current_curvature` (profile `m7_cycle1_current_curvature`) — v3 VALIDATION runs only

> Development evidence. Settings were selected on these validation runs (and CUSUM on calibration+validation), so the numbers are optimistic; independent evidence comes only from the final fresh-suite evaluation.

- Written 2026-10-27T15:02:52.455336+00:00; code hashes recorded in `metrics.json`.

## Overall (validation)

| Measurand | Detector | Event F1 [CI] | Macro recall | Episode precision | FA/h [CI] | Missed | Class. accuracy | Post-fault alarm records/h | Median delay |
|---|---|---|---|---|---|---|---|---|---|
| voltage_V | Hybrid M6 | 0.927 [0.85, 0.99] | 0.919 | 0.935 | 0.8 [0.2, 2.0] | 3 | 0.843 | 0.0 | 0 |
| voltage_V | Hybrid M5 (frozen) | 0.868 [0.78, 0.95] | 0.912 | 0.828 | 1.9 [0.9, 3.6] | 4 | 0.800 | 4.7 | 0 |
| voltage_V | Segment detector (existing) | 0.718 [0.60, 0.83] | 0.595 | 0.906 | 1.0 [0.3, 2.3] | 14 | – | 0.0 | 0 |
| voltage_V | GBT (all faults) | 0.588 [0.46, 0.73] | 0.491 | 0.735 | 2.5 [1.3, 4.3] | 27 | – | 0.0 | 1 |
| voltage_V | Tuned CUSUM | 0.974 [0.95, 1.00] | 0.949 | 1.000 | 0.0 [0.0, 0.7] | 4 | – | 237.5 | 0 |
| current_mA | Hybrid M6 | 0.838 [0.75, 0.92] | 0.861 | 0.817 | 2.1 [1.0, 3.8] | 6 | 0.896 | 6.1 | 0 |
| current_mA | Hybrid M5 (frozen) | 0.788 [0.70, 0.90] | 0.757 | 0.821 | 1.9 [0.9, 3.5] | 7 | 0.872 | 0.2 | 0 |
| current_mA | Segment detector (existing) | 0.545 [0.39, 0.68] | 0.634 | 0.477 | 8.8 [6.4, 11.7] | 14 | – | 3.0 | 0 |
| current_mA | GBT (all faults) | 0.893 [0.80, 0.97] | 0.884 | 0.903 | 1.3 [0.5, 2.7] | 8 | – | 5.3 | 0 |
| current_mA | Tuned CUSUM | 0.816 [0.70, 0.92] | 0.690 | 1.000 | 0.0 [0.0, 0.7] | 16 | – | 188.7 | 0 |
| temperature_C | Hybrid M6 | 0.846 [0.75, 0.93] | 0.780 | 0.923 | 0.6 [0.2, 1.4] | 8 | 0.891 | 2.2 | 0 |
| temperature_C | Hybrid M5 (frozen) | 0.727 [0.59, 0.84] | 0.685 | 0.775 | 1.3 [0.6, 2.4] | 20 | 0.676 | 105.3 | 0 |
| temperature_C | Segment detector (existing) | 0.566 [0.42, 0.68] | 0.632 | 0.512 | 5.4 [3.9, 7.4] | 18 | – | 15.2 | 0 |
| temperature_C | GBT (all faults) | 0.641 [0.46, 0.78] | 0.600 | 0.688 | 3.5 [2.3, 5.1] | 23 | – | 0.0 | 0 |
| temperature_C | Tuned CUSUM | 0.646 [0.45, 0.80] | 0.477 | 1.000 | 0.0 [0.0, 0.5] | 27 | – | 138.6 | 0 |

## Per fault type (validation): detected/events [Wilson 95 %], median delay

### voltage_V

| Fault type | n | Hybrid M6 | Hybrid M5 (frozen) | Segment detector (existing) | GBT (all faults) |
|---|---|---|---|---|---|
| `abrupt_change` | 9 | 8/9 [0.56, 0.98], 0 | 8/9 [0.56, 0.98], 0 | 8/9 [0.56, 0.98], 0 | 4/9 [0.19, 0.73], 7 |
| `gain_change` | 3 | 2/3 [0.21, 0.94], 12 | 2/3 [0.21, 0.94], 12 | 0/3 [0.00, 0.56], – | 1/3 [0.06, 0.79], 5 |
| `gradual_drift` | 3 | 3/3 [0.44, 1.00], 56 | 3/3 [0.44, 1.00], 85 | 2/3 [0.21, 0.94], 104 | 0/3 [0.00, 0.56], – |
| `isolated_spike` | 24 | 23/24 [0.80, 0.99], 0 | 22/24 [0.74, 0.98], 0 | 23/24 [0.80, 0.99], 0 | 8/24 [0.18, 0.53], 0 |
| `offset_shift` | 6 | 6/6 [0.61, 1.00], 0 | 6/6 [0.61, 1.00], 0 | 5/6 [0.44, 0.97], 0 | 5/6 [0.44, 0.97], 0 |
| `stuck_signal` | 9 | 9/9 [0.70, 1.00], 4 | 9/9 [0.70, 1.00], 5 | 2/9 [0.06, 0.55], 3 | 9/9 [0.70, 1.00], 4 |

### current_mA

| Fault type | n | Hybrid M6 | Hybrid M5 (frozen) | Segment detector (existing) | GBT (all faults) |
|---|---|---|---|---|---|
| `abrupt_change` | 9 | 9/9 [0.70, 1.00], 0 | 9/9 [0.70, 1.00], 0 | 9/9 [0.70, 1.00], 0 | 8/9 [0.56, 0.98], 0 |
| `gain_change` | 3 | 1/3 [0.06, 0.79], 0 | 1/3 [0.06, 0.79], 0 | 2/3 [0.21, 0.94], 0 | 2/3 [0.21, 0.94], 0 |
| `gradual_drift` | 3 | 3/3 [0.44, 1.00], 54 | 1/3 [0.06, 0.79], 27 | 1/3 [0.06, 0.79], 26 | 3/3 [0.44, 1.00], 212 |
| `isolated_spike` | 24 | 20/24 [0.64, 0.93], 0 | 21/24 [0.69, 0.96], 0 | 22/24 [0.74, 0.98], 0 | 18/24 [0.55, 0.88], 0 |
| `offset_shift` | 6 | 6/6 [0.61, 1.00], 0 | 6/6 [0.61, 1.00], 0 | 4/6 [0.30, 0.90], 14 | 6/6 [0.61, 1.00], 0 |
| `stuck_signal` | 9 | 9/9 [0.70, 1.00], 4 | 9/9 [0.70, 1.00], 4 | 2/9 [0.06, 0.55], 1 | 9/9 [0.70, 1.00], 4 |

### temperature_C

| Fault type | n | Hybrid M6 | Hybrid M5 (frozen) | Segment detector (existing) | GBT (all faults) |
|---|---|---|---|---|---|
| `abrupt_change` | 9 | 7/9 [0.45, 0.94], 0 | 6/9 [0.35, 0.88], 0 | 7/9 [0.45, 0.94], 0 | 7/9 [0.45, 0.94], 0 |
| `gain_change` | 3 | 1/3 [0.06, 0.79], 14 | 2/3 [0.21, 0.94], 7 | 1/3 [0.06, 0.79], 0 | 2/3 [0.21, 0.94], 0 |
| `gradual_drift` | 3 | 3/3 [0.44, 1.00], 192 | 2/3 [0.21, 0.94], 140 | 3/3 [0.44, 1.00], 74 | 2/3 [0.21, 0.94], 155 |
| `isolated_spike` | 24 | 23/24 [0.80, 0.99], 0 | 12/24 [0.31, 0.69], 0 | 19/24 [0.60, 0.91], 0 | 13/24 [0.35, 0.72], 0 |
| `offset_shift` | 6 | 5/6 [0.44, 0.97], 39 | 5/6 [0.44, 0.97], 1 | 4/6 [0.30, 0.90], 0 | 3/6 [0.19, 0.81], 0 |
| `stuck_signal` | 9 | 7/9 [0.45, 0.94], 9 | 7/9 [0.45, 0.94], 5 | 2/9 [0.06, 0.55], 35 | 4/9 [0.19, 0.73], 10 |

## Selected settings

- **voltage_V**: segment `phase_blocks` MAD 3.5, extra `none` (curvature z 8.0), stuck `gbt`, GBT thr 0.9754; CUSUM `run` window 0 min_baseline 120 min_series 30 k 0.5 h 12; lifecycle `latched` (W 60, z 2.0); attribution `confirmed` (L 20, k 4.0).
  - CUSUM tuning: 20 controls, 6 drift runs; selected FA 0, pre-onset 0, detected 6, median delay 56.
- **current_mA**: segment `setpoint_blocks` MAD 12.0, extra `curvature_nonstationary` (curvature z 6.0), stuck `gbt`, GBT thr 0.9073; CUSUM `run` window 90 min_baseline 90 min_series 30 k 2.0 h 12; lifecycle `latched` (W 60, z 2.0); attribution `first_alarm` (L 30, k 4.0).
  - CUSUM tuning: 20 controls, 6 drift runs; selected FA 0, pre-onset 0, detected 6, median delay 40.
- **temperature_C**: segment `setpoint_blocks` MAD 3.5, extra `curvature_nonstationary` (curvature z 8.0), stuck `gbt`, GBT thr 0.8543; CUSUM `run` window 120 min_baseline 10 min_series 30 k 2.0 h 10; lifecycle `latched` (W 60, z 2.0); attribution `first_alarm` (L 30, k 4.0).
  - CUSUM tuning: 22 controls, 6 drift runs; selected FA 0, pre-onset 0, detected 6, median delay 181.

## Workstream evidence (validation)

### WS1 lifecycle: full-hybrid trials

| Measurand | Lifecycle | Event F1 | FA/h | Post-fault alarm records (total) | True episodes with >60 overhang |
|---|---|---|---|---|---|
| voltage_V | {'drift_lifecycle': 'latched'} | 0.921 | 0.8 | 103 | 1 |
| voltage_V | {'drift_lifecycle': 'hysteresis', 'clear_window': 30, 'clear_z': 2.0} | 0.915 | 1.0 | 27 | 0 |
| voltage_V | {'drift_lifecycle': 'hysteresis', 'clear_window': 60, 'clear_z': 2.0} | 0.924 | 0.8 | 86 | 0 |
| voltage_V | {'drift_lifecycle': 'hysteresis', 'clear_window': 30, 'clear_sigma': 1.0} | 0.916 | 1.0 | 25 | 0 |
| voltage_V | {'drift_lifecycle': 'hysteresis', 'clear_window': 60, 'clear_sigma': 0.5} | 0.916 | 1.0 | 85 | 0 |
| voltage_V | {'drift_lifecycle': 'hysteresis', 'clear_window': 60, 'clear_sigma': 1.0} | 0.916 | 1.0 | 82 | 0 |
| voltage_V | {'drift_lifecycle': 'hysteresis', 'clear_window': 120, 'clear_sigma': 0.5} | 0.922 | 0.8 | 135 | 1 |
| voltage_V | {'drift_lifecycle': 'latched', 'explain_before': 15} | 0.927 | 0.8 | 0 | 0 |
| voltage_V | {'drift_lifecycle': 'hysteresis', 'clear_window': 30, 'clear_z': 2.0, 'explain_before': 15} | 0.923 | 1.0 | 26 | 0 |
| voltage_V | {'drift_lifecycle': 'hysteresis', 'clear_window': 60, 'clear_z': 2.0, 'explain_before': 15} | 0.929 | 0.8 | 55 | 0 |
| voltage_V | {'drift_lifecycle': 'hysteresis', 'clear_window': 30, 'clear_sigma': 1.0, 'explain_before': 15} | 0.923 | 1.0 | 24 | 0 |
| voltage_V | {'drift_lifecycle': 'hysteresis', 'clear_window': 60, 'clear_sigma': 0.5, 'explain_before': 15} | 0.923 | 1.0 | 54 | 0 |
| voltage_V | {'drift_lifecycle': 'hysteresis', 'clear_window': 60, 'clear_sigma': 1.0, 'explain_before': 15} | 0.923 | 1.0 | 51 | 0 |
| voltage_V | {'drift_lifecycle': 'hysteresis', 'clear_window': 120, 'clear_sigma': 0.5, 'explain_before': 15} | 0.928 | 0.8 | 44 | 0 |
| current_mA | {'drift_lifecycle': 'latched'} | 0.838 | 2.1 | 32 | 0 |
| current_mA | {'drift_lifecycle': 'hysteresis', 'clear_window': 30, 'clear_z': 2.0} | 0.838 | 2.1 | 32 | 0 |
| current_mA | {'drift_lifecycle': 'hysteresis', 'clear_window': 60, 'clear_z': 2.0} | 0.838 | 2.1 | 32 | 0 |
| current_mA | {'drift_lifecycle': 'hysteresis', 'clear_window': 30, 'clear_sigma': 1.0} | 0.838 | 2.1 | 32 | 0 |
| current_mA | {'drift_lifecycle': 'hysteresis', 'clear_window': 60, 'clear_sigma': 0.5} | 0.838 | 2.1 | 32 | 0 |
| current_mA | {'drift_lifecycle': 'hysteresis', 'clear_window': 60, 'clear_sigma': 1.0} | 0.838 | 2.1 | 32 | 0 |
| current_mA | {'drift_lifecycle': 'hysteresis', 'clear_window': 120, 'clear_sigma': 0.5} | 0.838 | 2.1 | 32 | 0 |
| current_mA | {'drift_lifecycle': 'latched', 'explain_before': 15} | 0.838 | 2.1 | 32 | 0 |
| current_mA | {'drift_lifecycle': 'hysteresis', 'clear_window': 30, 'clear_z': 2.0, 'explain_before': 15} | 0.838 | 2.1 | 32 | 0 |
| current_mA | {'drift_lifecycle': 'hysteresis', 'clear_window': 60, 'clear_z': 2.0, 'explain_before': 15} | 0.838 | 2.1 | 32 | 0 |
| current_mA | {'drift_lifecycle': 'hysteresis', 'clear_window': 30, 'clear_sigma': 1.0, 'explain_before': 15} | 0.838 | 2.1 | 32 | 0 |
| current_mA | {'drift_lifecycle': 'hysteresis', 'clear_window': 60, 'clear_sigma': 0.5, 'explain_before': 15} | 0.838 | 2.1 | 32 | 0 |
| current_mA | {'drift_lifecycle': 'hysteresis', 'clear_window': 60, 'clear_sigma': 1.0, 'explain_before': 15} | 0.838 | 2.1 | 32 | 0 |
| current_mA | {'drift_lifecycle': 'hysteresis', 'clear_window': 120, 'clear_sigma': 0.5, 'explain_before': 15} | 0.838 | 2.1 | 32 | 0 |
| temperature_C | {'drift_lifecycle': 'latched'} | 0.846 | 0.6 | 16 | 0 |
| temperature_C | {'drift_lifecycle': 'hysteresis', 'clear_window': 30, 'clear_z': 2.0} | 0.846 | 0.6 | 16 | 0 |
| temperature_C | {'drift_lifecycle': 'hysteresis', 'clear_window': 60, 'clear_z': 2.0} | 0.846 | 0.6 | 16 | 0 |
| temperature_C | {'drift_lifecycle': 'hysteresis', 'clear_window': 30, 'clear_sigma': 1.0} | 0.846 | 0.6 | 16 | 0 |
| temperature_C | {'drift_lifecycle': 'hysteresis', 'clear_window': 60, 'clear_sigma': 0.5} | 0.846 | 0.6 | 16 | 0 |
| temperature_C | {'drift_lifecycle': 'hysteresis', 'clear_window': 60, 'clear_sigma': 1.0} | 0.846 | 0.6 | 16 | 0 |
| temperature_C | {'drift_lifecycle': 'hysteresis', 'clear_window': 120, 'clear_sigma': 0.5} | 0.846 | 0.6 | 16 | 0 |
| temperature_C | {'drift_lifecycle': 'latched', 'explain_before': 15} | 0.846 | 0.6 | 16 | 0 |
| temperature_C | {'drift_lifecycle': 'hysteresis', 'clear_window': 30, 'clear_z': 2.0, 'explain_before': 15} | 0.846 | 0.6 | 16 | 0 |
| temperature_C | {'drift_lifecycle': 'hysteresis', 'clear_window': 60, 'clear_z': 2.0, 'explain_before': 15} | 0.846 | 0.6 | 16 | 0 |
| temperature_C | {'drift_lifecycle': 'hysteresis', 'clear_window': 30, 'clear_sigma': 1.0, 'explain_before': 15} | 0.846 | 0.6 | 16 | 0 |
| temperature_C | {'drift_lifecycle': 'hysteresis', 'clear_window': 60, 'clear_sigma': 0.5, 'explain_before': 15} | 0.846 | 0.6 | 16 | 0 |
| temperature_C | {'drift_lifecycle': 'hysteresis', 'clear_window': 60, 'clear_sigma': 1.0, 'explain_before': 15} | 0.846 | 0.6 | 16 | 0 |
| temperature_C | {'drift_lifecycle': 'hysteresis', 'clear_window': 120, 'clear_sigma': 0.5, 'explain_before': 15} | 0.846 | 0.6 | 16 | 0 |

### WS1 attribution trials (classification accuracy of detected events)

| Measurand | Attribution | Accuracy | offset | gain | spike | abrupt |
|---|---|---|---|---|---|---|
| voltage_V | {'attribution': 'first_alarm'} | 0.765 | 0/6 | 1/2 | 23/23 | 7/8 |
| voltage_V | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 4.0, 'confirm_delay': 0} | 0.784 | 4/6 | 0/2 | 23/23 | 5/8 |
| voltage_V | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 4.0, 'confirm_delay': 30} | 0.824 | 3/6 | 1/2 | 23/23 | 7/8 |
| voltage_V | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 3.0, 'confirm_delay': 45} | 0.804 | 2/6 | 1/2 | 23/23 | 7/8 |
| voltage_V | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 4.0, 'confirm_delay': 45} | 0.804 | 2/6 | 1/2 | 23/23 | 7/8 |
| voltage_V | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 6.0, 'confirm_delay': 45} | 0.804 | 2/6 | 1/2 | 23/23 | 7/8 |
| voltage_V | {'attribution': 'confirmed', 'confirm_window': 30, 'confirm_k': 4.0, 'confirm_delay': 45} | 0.784 | 1/6 | 1/2 | 23/23 | 7/8 |
| voltage_V | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 4.0, 'confirm_delay': 60} | 0.784 | 1/6 | 1/2 | 23/23 | 7/8 |
| voltage_V | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 4.0, 'confirm_delay': 0, 'attribution_source': 'error'} | 0.843 | 4/6 | 1/2 | 23/23 | 7/8 |
| voltage_V | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 4.0, 'confirm_delay': 30, 'attribution_source': 'error'} | 0.843 | 3/6 | 2/2 | 23/23 | 7/8 |
| voltage_V | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 3.0, 'confirm_delay': 45, 'attribution_source': 'error'} | 0.843 | 3/6 | 2/2 | 23/23 | 7/8 |
| voltage_V | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 4.0, 'confirm_delay': 45, 'attribution_source': 'error'} | 0.843 | 3/6 | 2/2 | 23/23 | 7/8 |
| voltage_V | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 6.0, 'confirm_delay': 45, 'attribution_source': 'error'} | 0.843 | 3/6 | 2/2 | 23/23 | 7/8 |
| voltage_V | {'attribution': 'confirmed', 'confirm_window': 30, 'confirm_k': 4.0, 'confirm_delay': 45, 'attribution_source': 'error'} | 0.843 | 3/6 | 2/2 | 23/23 | 7/8 |
| voltage_V | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 4.0, 'confirm_delay': 60, 'attribution_source': 'error'} | 0.843 | 3/6 | 2/2 | 23/23 | 7/8 |
| current_mA | {'attribution': 'first_alarm'} | 0.896 | 3/6 | 0/1 | 20/20 | 9/9 |
| current_mA | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 4.0, 'confirm_delay': 0} | 0.875 | 3/6 | 1/1 | 19/20 | 8/9 |
| current_mA | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 4.0, 'confirm_delay': 30} | 0.875 | 2/6 | 0/1 | 20/20 | 9/9 |
| current_mA | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 3.0, 'confirm_delay': 45} | 0.875 | 2/6 | 0/1 | 20/20 | 9/9 |
| current_mA | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 4.0, 'confirm_delay': 45} | 0.875 | 2/6 | 0/1 | 20/20 | 9/9 |
| current_mA | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 6.0, 'confirm_delay': 45} | 0.875 | 2/6 | 0/1 | 20/20 | 9/9 |
| current_mA | {'attribution': 'confirmed', 'confirm_window': 30, 'confirm_k': 4.0, 'confirm_delay': 45} | 0.875 | 2/6 | 0/1 | 20/20 | 9/9 |
| current_mA | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 4.0, 'confirm_delay': 60} | 0.875 | 2/6 | 0/1 | 20/20 | 9/9 |
| current_mA | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 4.0, 'confirm_delay': 0, 'attribution_source': 'error'} | 0.896 | 5/6 | 1/1 | 18/20 | 8/9 |
| current_mA | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 4.0, 'confirm_delay': 30, 'attribution_source': 'error'} | 0.854 | 5/6 | 0/1 | 18/20 | 7/9 |
| current_mA | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 3.0, 'confirm_delay': 45, 'attribution_source': 'error'} | 0.854 | 5/6 | 0/1 | 18/20 | 7/9 |
| current_mA | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 4.0, 'confirm_delay': 45, 'attribution_source': 'error'} | 0.854 | 5/6 | 0/1 | 18/20 | 7/9 |
| current_mA | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 6.0, 'confirm_delay': 45, 'attribution_source': 'error'} | 0.854 | 5/6 | 0/1 | 18/20 | 7/9 |
| current_mA | {'attribution': 'confirmed', 'confirm_window': 30, 'confirm_k': 4.0, 'confirm_delay': 45, 'attribution_source': 'error'} | 0.854 | 5/6 | 0/1 | 18/20 | 7/9 |
| current_mA | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 4.0, 'confirm_delay': 60, 'attribution_source': 'error'} | 0.854 | 5/6 | 0/1 | 18/20 | 7/9 |
| temperature_C | {'attribution': 'first_alarm'} | 0.891 | 2/5 | 1/1 | 22/23 | 6/7 |
| temperature_C | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 4.0, 'confirm_delay': 0} | 0.891 | 3/5 | 1/1 | 21/23 | 6/7 |
| temperature_C | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 4.0, 'confirm_delay': 30} | 0.870 | 2/5 | 1/1 | 21/23 | 6/7 |
| temperature_C | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 3.0, 'confirm_delay': 45} | 0.870 | 2/5 | 1/1 | 21/23 | 6/7 |
| temperature_C | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 4.0, 'confirm_delay': 45} | 0.870 | 2/5 | 1/1 | 21/23 | 6/7 |
| temperature_C | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 6.0, 'confirm_delay': 45} | 0.870 | 2/5 | 1/1 | 21/23 | 6/7 |
| temperature_C | {'attribution': 'confirmed', 'confirm_window': 30, 'confirm_k': 4.0, 'confirm_delay': 45} | 0.870 | 2/5 | 1/1 | 21/23 | 6/7 |
| temperature_C | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 4.0, 'confirm_delay': 60} | 0.870 | 2/5 | 1/1 | 21/23 | 6/7 |
| temperature_C | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 4.0, 'confirm_delay': 0, 'attribution_source': 'error'} | 0.891 | 3/5 | 1/1 | 22/23 | 5/7 |
| temperature_C | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 4.0, 'confirm_delay': 30, 'attribution_source': 'error'} | 0.891 | 3/5 | 1/1 | 22/23 | 5/7 |
| temperature_C | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 3.0, 'confirm_delay': 45, 'attribution_source': 'error'} | 0.891 | 3/5 | 1/1 | 22/23 | 5/7 |
| temperature_C | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 4.0, 'confirm_delay': 45, 'attribution_source': 'error'} | 0.891 | 3/5 | 1/1 | 22/23 | 5/7 |
| temperature_C | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 6.0, 'confirm_delay': 45, 'attribution_source': 'error'} | 0.891 | 3/5 | 1/1 | 22/23 | 5/7 |
| temperature_C | {'attribution': 'confirmed', 'confirm_window': 30, 'confirm_k': 4.0, 'confirm_delay': 45, 'attribution_source': 'error'} | 0.891 | 3/5 | 1/1 | 22/23 | 5/7 |
| temperature_C | {'attribution': 'confirmed', 'confirm_window': 20, 'confirm_k': 4.0, 'confirm_delay': 60, 'attribution_source': 'error'} | 0.891 | 3/5 | 1/1 | 22/23 | 5/7 |

### WS2 transient options (best per option; transient component alone)

| Measurand | Segment mode | Extra | Best F1 | at MAD | Spike recall stationary | Spike recall non-stationary | FA/h ramp | FA/h settling | FA/h post-event |
|---|---|---|---|---|---|---|---|---|---|
| voltage_V | setpoint_blocks | {"settling_suppression": false, "transient_extra": "none", "transient_transition_window": 0} | 0.915 | 3.5 | 1.00 | 0.00 (1) | 0.0 | 11.6 | 29.0 |
| voltage_V | setpoint_blocks | {"settling_suppression": true, "transient_extra": "none", "transient_transition_window": 0} | 0.923 | 3.5 | 1.00 | 0.00 (1) | 0.0 | 0.0 | 19.4 |
| voltage_V | setpoint_blocks | {"settling_suppression": false, "transient_extra": "none", "transient_transition_window": 60} | 0.915 | 3.5 | 1.00 | 0.00 (1) | 0.0 | 11.6 | 29.0 |
| voltage_V | setpoint_blocks | {"settling_suppression": true, "transient_extra": "none", "transient_transition_window": 60} | 0.871 | 3.5 | 0.91 | 0.00 (1) | 0.0 | 0.0 | 0.0 |
| voltage_V | setpoint_blocks | {"settling_suppression": false, "transient_extra": "none", "transient_transition_window": 120} | 0.915 | 3.5 | 1.00 | 0.00 (1) | 0.0 | 11.6 | 29.0 |
| voltage_V | setpoint_blocks | {"settling_suppression": true, "transient_extra": "none", "transient_transition_window": 120} | 0.742 | 3.5 | 0.65 | 0.00 (1) | 0.0 | 0.0 | 0.0 |
| voltage_V | setpoint_blocks | {"settling_suppression": false, "transient_extra": "none", "transient_transition_window": 210} | 0.915 | 3.5 | 1.00 | 0.00 (1) | 0.0 | 11.6 | 29.0 |
| voltage_V | setpoint_blocks | {"settling_suppression": true, "transient_extra": "none", "transient_transition_window": 210} | 0.567 | 3.5 | 0.48 | 0.00 (1) | 0.0 | 0.0 | 0.0 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.846 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 162.1 | 19.4 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.846 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 162.1 | 19.4 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.846 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 162.1 | 19.4 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.798 | 3.5 | 0.91 | 1.00 (1) | 5.6 | 162.1 | 0.0 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.846 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 162.1 | 19.4 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.693 | 3.5 | 0.65 | 1.00 (1) | 5.6 | 162.1 | 0.0 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.846 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 162.1 | 19.4 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.677 | 3.5 | 0.61 | 1.00 (1) | 5.6 | 162.1 | 0.0 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.864 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 127.3 | 19.4 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.864 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 127.3 | 19.4 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.864 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 127.3 | 19.4 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.817 | 3.5 | 0.91 | 1.00 (1) | 5.6 | 127.3 | 0.0 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.864 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 127.3 | 19.4 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.710 | 3.5 | 0.65 | 1.00 (1) | 5.6 | 127.3 | 0.0 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.864 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 127.3 | 19.4 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.692 | 3.5 | 0.61 | 1.00 (1) | 5.6 | 127.3 | 0.0 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.870 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 81.0 | 19.4 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.870 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 81.0 | 19.4 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.870 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 81.0 | 19.4 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.818 | 3.5 | 0.91 | 1.00 (1) | 5.6 | 81.0 | 0.0 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.870 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 81.0 | 19.4 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.701 | 3.5 | 0.65 | 1.00 (1) | 5.6 | 81.0 | 0.0 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.870 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 81.0 | 19.4 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.599 | 3.5 | 0.61 | 1.00 (1) | 5.6 | 81.0 | 0.0 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.765 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 162.1 | 19.4 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.765 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 162.1 | 19.4 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.765 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 162.1 | 19.4 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.717 | 3.5 | 0.91 | 1.00 (1) | 5.6 | 162.1 | 0.0 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.765 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 162.1 | 19.4 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.622 | 3.5 | 0.65 | 1.00 (1) | 5.6 | 162.1 | 0.0 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.765 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 162.1 | 19.4 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.605 | 3.5 | 0.61 | 1.00 (1) | 5.6 | 162.1 | 0.0 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.857 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 127.3 | 19.4 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.857 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 127.3 | 19.4 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.857 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 127.3 | 19.4 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.810 | 3.5 | 0.91 | 1.00 (1) | 5.6 | 127.3 | 0.0 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.857 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 127.3 | 19.4 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.704 | 3.5 | 0.65 | 1.00 (1) | 5.6 | 127.3 | 0.0 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.857 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 127.3 | 19.4 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.685 | 3.5 | 0.61 | 1.00 (1) | 5.6 | 127.3 | 0.0 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.863 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 81.0 | 19.4 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.863 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 81.0 | 19.4 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.863 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 81.0 | 19.4 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.810 | 3.5 | 0.91 | 1.00 (1) | 5.6 | 81.0 | 0.0 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.863 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 81.0 | 19.4 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.695 | 3.5 | 0.65 | 1.00 (1) | 5.6 | 81.0 | 0.0 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.863 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 81.0 | 19.4 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.594 | 3.5 | 0.61 | 1.00 (1) | 5.6 | 81.0 | 0.0 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 12.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.910 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 23.2 | 19.4 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 12.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.910 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 23.2 | 19.4 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 12.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.910 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 23.2 | 19.4 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 12.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.858 | 3.5 | 0.91 | 1.00 (1) | 5.6 | 23.2 | 0.0 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 12.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.910 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 23.2 | 19.4 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 12.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.736 | 3.5 | 0.65 | 1.00 (1) | 5.6 | 23.2 | 0.0 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 12.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.910 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 23.2 | 19.4 |
| voltage_V | setpoint_blocks | {"curvature_threshold": 12.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.629 | 3.5 | 0.61 | 1.00 (1) | 5.6 | 23.2 | 0.0 |
| voltage_V | phase_blocks | {"settling_suppression": false, "transient_extra": "none", "transient_transition_window": 0} | 0.924 | 3.5 | 1.00 | 0.00 (1) | 0.0 | 0.0 | 19.4 |
| voltage_V | phase_blocks | {"settling_suppression": true, "transient_extra": "none", "transient_transition_window": 0} | 0.923 | 3.5 | 1.00 | 0.00 (1) | 0.0 | 0.0 | 19.4 |
| voltage_V | phase_blocks | {"settling_suppression": false, "transient_extra": "none", "transient_transition_window": 60} | 0.924 | 3.5 | 1.00 | 0.00 (1) | 0.0 | 0.0 | 19.4 |
| voltage_V | phase_blocks | {"settling_suppression": true, "transient_extra": "none", "transient_transition_window": 60} | 0.871 | 3.5 | 0.91 | 0.00 (1) | 0.0 | 0.0 | 0.0 |
| voltage_V | phase_blocks | {"settling_suppression": false, "transient_extra": "none", "transient_transition_window": 120} | 0.924 | 3.5 | 1.00 | 0.00 (1) | 0.0 | 0.0 | 19.4 |
| voltage_V | phase_blocks | {"settling_suppression": true, "transient_extra": "none", "transient_transition_window": 120} | 0.742 | 3.5 | 0.65 | 0.00 (1) | 0.0 | 0.0 | 0.0 |
| voltage_V | phase_blocks | {"settling_suppression": false, "transient_extra": "none", "transient_transition_window": 210} | 0.924 | 3.5 | 1.00 | 0.00 (1) | 0.0 | 0.0 | 19.4 |
| voltage_V | phase_blocks | {"settling_suppression": true, "transient_extra": "none", "transient_transition_window": 210} | 0.567 | 3.5 | 0.48 | 0.00 (1) | 0.0 | 0.0 | 0.0 |
| voltage_V | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.846 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 162.1 | 19.4 |
| voltage_V | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.846 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 162.1 | 19.4 |
| voltage_V | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.846 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 162.1 | 19.4 |
| voltage_V | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.798 | 3.5 | 0.91 | 1.00 (1) | 5.6 | 162.1 | 0.0 |
| voltage_V | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.846 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 162.1 | 19.4 |
| voltage_V | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.693 | 3.5 | 0.65 | 1.00 (1) | 5.6 | 162.1 | 0.0 |
| voltage_V | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.846 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 162.1 | 19.4 |
| voltage_V | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.677 | 3.5 | 0.61 | 1.00 (1) | 5.6 | 162.1 | 0.0 |
| voltage_V | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.864 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 127.3 | 19.4 |
| voltage_V | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.864 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 127.3 | 19.4 |
| voltage_V | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.864 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 127.3 | 19.4 |
| voltage_V | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.817 | 3.5 | 0.91 | 1.00 (1) | 5.6 | 127.3 | 0.0 |
| voltage_V | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.864 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 127.3 | 19.4 |
| voltage_V | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.710 | 3.5 | 0.65 | 1.00 (1) | 5.6 | 127.3 | 0.0 |
| voltage_V | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.864 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 127.3 | 19.4 |
| voltage_V | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.692 | 3.5 | 0.61 | 1.00 (1) | 5.6 | 127.3 | 0.0 |
| voltage_V | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.870 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 81.0 | 19.4 |
| voltage_V | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.870 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 81.0 | 19.4 |
| voltage_V | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.870 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 81.0 | 19.4 |
| voltage_V | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.818 | 3.5 | 0.91 | 1.00 (1) | 5.6 | 81.0 | 0.0 |
| voltage_V | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.870 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 81.0 | 19.4 |
| voltage_V | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.701 | 3.5 | 0.65 | 1.00 (1) | 5.6 | 81.0 | 0.0 |
| voltage_V | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.870 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 81.0 | 19.4 |
| voltage_V | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.599 | 3.5 | 0.61 | 1.00 (1) | 5.6 | 81.0 | 0.0 |
| voltage_V | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.765 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 162.1 | 19.4 |
| voltage_V | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.765 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 162.1 | 19.4 |
| voltage_V | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.765 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 162.1 | 19.4 |
| voltage_V | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.717 | 3.5 | 0.91 | 1.00 (1) | 5.6 | 162.1 | 0.0 |
| voltage_V | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.765 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 162.1 | 19.4 |
| voltage_V | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.622 | 3.5 | 0.65 | 1.00 (1) | 5.6 | 162.1 | 0.0 |
| voltage_V | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.765 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 162.1 | 19.4 |
| voltage_V | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.605 | 3.5 | 0.61 | 1.00 (1) | 5.6 | 162.1 | 0.0 |
| voltage_V | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.857 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 127.3 | 19.4 |
| voltage_V | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.857 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 127.3 | 19.4 |
| voltage_V | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.857 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 127.3 | 19.4 |
| voltage_V | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.810 | 3.5 | 0.91 | 1.00 (1) | 5.6 | 127.3 | 0.0 |
| voltage_V | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.857 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 127.3 | 19.4 |
| voltage_V | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.704 | 3.5 | 0.65 | 1.00 (1) | 5.6 | 127.3 | 0.0 |
| voltage_V | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.857 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 127.3 | 19.4 |
| voltage_V | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.685 | 3.5 | 0.61 | 1.00 (1) | 5.6 | 127.3 | 0.0 |
| voltage_V | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.863 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 81.0 | 19.4 |
| voltage_V | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.863 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 81.0 | 19.4 |
| voltage_V | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.863 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 81.0 | 19.4 |
| voltage_V | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.810 | 3.5 | 0.91 | 1.00 (1) | 5.6 | 81.0 | 0.0 |
| voltage_V | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.863 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 81.0 | 19.4 |
| voltage_V | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.695 | 3.5 | 0.65 | 1.00 (1) | 5.6 | 81.0 | 0.0 |
| voltage_V | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.863 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 81.0 | 19.4 |
| voltage_V | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.594 | 3.5 | 0.61 | 1.00 (1) | 5.6 | 81.0 | 0.0 |
| voltage_V | phase_blocks | {"curvature_threshold": 12.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.910 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 23.2 | 19.4 |
| voltage_V | phase_blocks | {"curvature_threshold": 12.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.910 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 23.2 | 19.4 |
| voltage_V | phase_blocks | {"curvature_threshold": 12.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.910 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 23.2 | 19.4 |
| voltage_V | phase_blocks | {"curvature_threshold": 12.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.858 | 3.5 | 0.91 | 1.00 (1) | 5.6 | 23.2 | 0.0 |
| voltage_V | phase_blocks | {"curvature_threshold": 12.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.910 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 23.2 | 19.4 |
| voltage_V | phase_blocks | {"curvature_threshold": 12.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.736 | 3.5 | 0.65 | 1.00 (1) | 5.6 | 23.2 | 0.0 |
| voltage_V | phase_blocks | {"curvature_threshold": 12.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.910 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 23.2 | 19.4 |
| voltage_V | phase_blocks | {"curvature_threshold": 12.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.629 | 3.5 | 0.61 | 1.00 (1) | 5.6 | 23.2 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"settling_suppression": false, "transient_extra": "none", "transient_transition_window": 0} | 0.923 | 3.5 | 1.00 | 0.00 (1) | 0.0 | 0.0 | 19.4 |
| voltage_V | phase_blocks_stationary_only | {"settling_suppression": true, "transient_extra": "none", "transient_transition_window": 0} | 0.923 | 3.5 | 1.00 | 0.00 (1) | 0.0 | 0.0 | 19.4 |
| voltage_V | phase_blocks_stationary_only | {"settling_suppression": false, "transient_extra": "none", "transient_transition_window": 60} | 0.871 | 3.5 | 0.91 | 0.00 (1) | 0.0 | 0.0 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"settling_suppression": true, "transient_extra": "none", "transient_transition_window": 60} | 0.871 | 3.5 | 0.91 | 0.00 (1) | 0.0 | 0.0 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"settling_suppression": false, "transient_extra": "none", "transient_transition_window": 120} | 0.742 | 3.5 | 0.65 | 0.00 (1) | 0.0 | 0.0 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"settling_suppression": true, "transient_extra": "none", "transient_transition_window": 120} | 0.742 | 3.5 | 0.65 | 0.00 (1) | 0.0 | 0.0 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"settling_suppression": false, "transient_extra": "none", "transient_transition_window": 210} | 0.567 | 3.5 | 0.48 | 0.00 (1) | 0.0 | 0.0 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"settling_suppression": true, "transient_extra": "none", "transient_transition_window": 210} | 0.567 | 3.5 | 0.48 | 0.00 (1) | 0.0 | 0.0 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.846 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 162.1 | 19.4 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.846 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 162.1 | 19.4 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.798 | 3.5 | 0.91 | 1.00 (1) | 5.6 | 162.1 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.798 | 3.5 | 0.91 | 1.00 (1) | 5.6 | 162.1 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.693 | 3.5 | 0.65 | 1.00 (1) | 5.6 | 162.1 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.693 | 3.5 | 0.65 | 1.00 (1) | 5.6 | 162.1 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.677 | 3.5 | 0.61 | 1.00 (1) | 5.6 | 162.1 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.677 | 3.5 | 0.61 | 1.00 (1) | 5.6 | 162.1 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.864 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 127.3 | 19.4 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.864 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 127.3 | 19.4 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.817 | 3.5 | 0.91 | 1.00 (1) | 5.6 | 127.3 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.817 | 3.5 | 0.91 | 1.00 (1) | 5.6 | 127.3 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.710 | 3.5 | 0.65 | 1.00 (1) | 5.6 | 127.3 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.710 | 3.5 | 0.65 | 1.00 (1) | 5.6 | 127.3 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.692 | 3.5 | 0.61 | 1.00 (1) | 5.6 | 127.3 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.692 | 3.5 | 0.61 | 1.00 (1) | 5.6 | 127.3 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.870 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 81.0 | 19.4 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.870 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 81.0 | 19.4 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.818 | 3.5 | 0.91 | 1.00 (1) | 5.6 | 81.0 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.818 | 3.5 | 0.91 | 1.00 (1) | 5.6 | 81.0 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.701 | 3.5 | 0.65 | 1.00 (1) | 5.6 | 81.0 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.701 | 3.5 | 0.65 | 1.00 (1) | 5.6 | 81.0 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.599 | 3.5 | 0.61 | 1.00 (1) | 5.6 | 81.0 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.599 | 3.5 | 0.61 | 1.00 (1) | 5.6 | 81.0 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.765 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 162.1 | 19.4 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.765 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 162.1 | 19.4 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.717 | 3.5 | 0.91 | 1.00 (1) | 5.6 | 162.1 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.717 | 3.5 | 0.91 | 1.00 (1) | 5.6 | 162.1 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.622 | 3.5 | 0.65 | 1.00 (1) | 5.6 | 162.1 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.622 | 3.5 | 0.65 | 1.00 (1) | 5.6 | 162.1 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.605 | 3.5 | 0.61 | 1.00 (1) | 5.6 | 162.1 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.605 | 3.5 | 0.61 | 1.00 (1) | 5.6 | 162.1 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.857 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 127.3 | 19.4 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.857 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 127.3 | 19.4 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.810 | 3.5 | 0.91 | 1.00 (1) | 5.6 | 127.3 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.810 | 3.5 | 0.91 | 1.00 (1) | 5.6 | 127.3 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.704 | 3.5 | 0.65 | 1.00 (1) | 5.6 | 127.3 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.704 | 3.5 | 0.65 | 1.00 (1) | 5.6 | 127.3 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.685 | 3.5 | 0.61 | 1.00 (1) | 5.6 | 127.3 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.685 | 3.5 | 0.61 | 1.00 (1) | 5.6 | 127.3 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.863 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 81.0 | 19.4 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.863 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 81.0 | 19.4 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.810 | 3.5 | 0.91 | 1.00 (1) | 5.6 | 81.0 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.810 | 3.5 | 0.91 | 1.00 (1) | 5.6 | 81.0 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.695 | 3.5 | 0.65 | 1.00 (1) | 5.6 | 81.0 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.695 | 3.5 | 0.65 | 1.00 (1) | 5.6 | 81.0 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.594 | 3.5 | 0.61 | 1.00 (1) | 5.6 | 81.0 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.594 | 3.5 | 0.61 | 1.00 (1) | 5.6 | 81.0 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 12.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.910 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 23.2 | 19.4 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 12.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.910 | 3.5 | 1.00 | 1.00 (1) | 5.6 | 23.2 | 19.4 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 12.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.858 | 3.5 | 0.91 | 1.00 (1) | 5.6 | 23.2 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 12.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.858 | 3.5 | 0.91 | 1.00 (1) | 5.6 | 23.2 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 12.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.736 | 3.5 | 0.65 | 1.00 (1) | 5.6 | 23.2 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 12.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.736 | 3.5 | 0.65 | 1.00 (1) | 5.6 | 23.2 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 12.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.629 | 3.5 | 0.61 | 1.00 (1) | 5.6 | 23.2 | 0.0 |
| voltage_V | phase_blocks_stationary_only | {"curvature_threshold": 12.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.629 | 3.5 | 0.61 | 1.00 (1) | 5.6 | 23.2 | 0.0 |
| current_mA | setpoint_blocks | {"settling_suppression": false, "transient_extra": "none", "transient_transition_window": 0} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"settling_suppression": true, "transient_extra": "none", "transient_transition_window": 0} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"settling_suppression": false, "transient_extra": "none", "transient_transition_window": 60} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"settling_suppression": true, "transient_extra": "none", "transient_transition_window": 60} | 0.871 | 6.0 | 0.54 | – (0) | – | – | 0.0 |
| current_mA | setpoint_blocks | {"settling_suppression": false, "transient_extra": "none", "transient_transition_window": 120} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"settling_suppression": true, "transient_extra": "none", "transient_transition_window": 120} | 0.595 | 6.0 | 0.29 | – (0) | – | – | 0.0 |
| current_mA | setpoint_blocks | {"settling_suppression": false, "transient_extra": "none", "transient_transition_window": 210} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"settling_suppression": true, "transient_extra": "none", "transient_transition_window": 210} | 0.400 | 6.0 | 0.17 | – (0) | – | – | 0.0 |
| current_mA | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.871 | 6.0 | 0.54 | – (0) | – | – | 0.0 |
| current_mA | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.595 | 6.0 | 0.29 | – (0) | – | – | 0.0 |
| current_mA | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.918 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.615 | 6.0 | 0.33 | – (0) | – | – | 0.0 |
| current_mA | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.871 | 6.0 | 0.54 | – (0) | – | – | 0.0 |
| current_mA | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.595 | 6.0 | 0.29 | – (0) | – | – | 0.0 |
| current_mA | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.917 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.615 | 6.0 | 0.33 | – (0) | – | – | 0.0 |
| current_mA | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.871 | 6.0 | 0.54 | – (0) | – | – | 0.0 |
| current_mA | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.595 | 6.0 | 0.29 | – (0) | – | – | 0.0 |
| current_mA | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.917 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.538 | 6.0 | 0.29 | – (0) | – | – | 0.0 |
| current_mA | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.715 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.715 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.715 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.661 | 5.0 | 0.62 | – (0) | – | – | 0.0 |
| current_mA | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.715 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.453 | 12.0 | 0.33 | – (0) | – | – | 0.0 |
| current_mA | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.715 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.446 | 6.0 | 0.33 | – (0) | – | – | 0.0 |
| current_mA | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.892 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.892 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.892 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.855 | 6.0 | 0.58 | – (0) | – | – | 0.0 |
| current_mA | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.892 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.594 | 12.0 | 0.33 | – (0) | – | – | 0.0 |
| current_mA | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.892 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.593 | 6.0 | 0.33 | – (0) | – | – | 0.0 |
| current_mA | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.917 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.917 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.917 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.884 | 6.0 | 0.58 | – (0) | – | – | 0.0 |
| current_mA | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.917 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.615 | 6.0 | 0.33 | – (0) | – | – | 0.0 |
| current_mA | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.917 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.538 | 6.0 | 0.29 | – (0) | – | – | 0.0 |
| current_mA | setpoint_blocks | {"curvature_threshold": 12.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.915 | 8.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"curvature_threshold": 12.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.915 | 8.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"curvature_threshold": 12.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.915 | 8.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"curvature_threshold": 12.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.884 | 6.0 | 0.58 | – (0) | – | – | 0.0 |
| current_mA | setpoint_blocks | {"curvature_threshold": 12.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.915 | 8.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"curvature_threshold": 12.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.615 | 6.0 | 0.33 | – (0) | – | – | 0.0 |
| current_mA | setpoint_blocks | {"curvature_threshold": 12.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.915 | 8.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | setpoint_blocks | {"curvature_threshold": 12.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.538 | 6.0 | 0.29 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks | {"settling_suppression": false, "transient_extra": "none", "transient_transition_window": 0} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"settling_suppression": true, "transient_extra": "none", "transient_transition_window": 0} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"settling_suppression": false, "transient_extra": "none", "transient_transition_window": 60} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"settling_suppression": true, "transient_extra": "none", "transient_transition_window": 60} | 0.871 | 6.0 | 0.54 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks | {"settling_suppression": false, "transient_extra": "none", "transient_transition_window": 120} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"settling_suppression": true, "transient_extra": "none", "transient_transition_window": 120} | 0.595 | 6.0 | 0.29 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks | {"settling_suppression": false, "transient_extra": "none", "transient_transition_window": 210} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"settling_suppression": true, "transient_extra": "none", "transient_transition_window": 210} | 0.400 | 6.0 | 0.17 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.871 | 6.0 | 0.54 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.595 | 6.0 | 0.29 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.918 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.615 | 6.0 | 0.33 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.871 | 6.0 | 0.54 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.595 | 6.0 | 0.29 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.917 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.615 | 6.0 | 0.33 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.871 | 6.0 | 0.54 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.595 | 6.0 | 0.29 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.917 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.538 | 6.0 | 0.29 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.715 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.715 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.715 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.661 | 5.0 | 0.62 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.715 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.453 | 12.0 | 0.33 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.715 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.446 | 6.0 | 0.33 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.892 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.892 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.892 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.855 | 6.0 | 0.58 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.892 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.594 | 12.0 | 0.33 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.892 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.593 | 6.0 | 0.33 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.917 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.917 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.917 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.884 | 6.0 | 0.58 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.917 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.615 | 6.0 | 0.33 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.917 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.538 | 6.0 | 0.29 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks | {"curvature_threshold": 12.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.915 | 8.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"curvature_threshold": 12.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.915 | 8.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"curvature_threshold": 12.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.915 | 8.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"curvature_threshold": 12.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.884 | 6.0 | 0.58 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks | {"curvature_threshold": 12.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.915 | 8.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"curvature_threshold": 12.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.615 | 6.0 | 0.33 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks | {"curvature_threshold": 12.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.915 | 8.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks | {"curvature_threshold": 12.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.538 | 6.0 | 0.29 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"settling_suppression": false, "transient_extra": "none", "transient_transition_window": 0} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks_stationary_only | {"settling_suppression": true, "transient_extra": "none", "transient_transition_window": 0} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks_stationary_only | {"settling_suppression": false, "transient_extra": "none", "transient_transition_window": 60} | 0.871 | 6.0 | 0.54 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"settling_suppression": true, "transient_extra": "none", "transient_transition_window": 60} | 0.871 | 6.0 | 0.54 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"settling_suppression": false, "transient_extra": "none", "transient_transition_window": 120} | 0.595 | 6.0 | 0.29 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"settling_suppression": true, "transient_extra": "none", "transient_transition_window": 120} | 0.595 | 6.0 | 0.29 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"settling_suppression": false, "transient_extra": "none", "transient_transition_window": 210} | 0.400 | 6.0 | 0.17 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"settling_suppression": true, "transient_extra": "none", "transient_transition_window": 210} | 0.400 | 6.0 | 0.17 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.871 | 6.0 | 0.54 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.871 | 6.0 | 0.54 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.595 | 6.0 | 0.29 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.595 | 6.0 | 0.29 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.615 | 6.0 | 0.33 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.615 | 6.0 | 0.33 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.871 | 6.0 | 0.54 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.871 | 6.0 | 0.54 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.595 | 6.0 | 0.29 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.595 | 6.0 | 0.29 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.615 | 6.0 | 0.33 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.615 | 6.0 | 0.33 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.904 | 8.0 | 0.79 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.871 | 6.0 | 0.54 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.871 | 6.0 | 0.54 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.595 | 6.0 | 0.29 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.595 | 6.0 | 0.29 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.538 | 6.0 | 0.29 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.538 | 6.0 | 0.29 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.715 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.715 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.661 | 5.0 | 0.62 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.661 | 5.0 | 0.62 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.453 | 12.0 | 0.33 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.453 | 12.0 | 0.33 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.446 | 6.0 | 0.33 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.446 | 6.0 | 0.33 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.892 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.892 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.855 | 6.0 | 0.58 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.855 | 6.0 | 0.58 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.594 | 12.0 | 0.33 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.594 | 12.0 | 0.33 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.593 | 6.0 | 0.33 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.593 | 6.0 | 0.33 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.917 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.917 | 12.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.884 | 6.0 | 0.58 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.884 | 6.0 | 0.58 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.615 | 6.0 | 0.33 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.615 | 6.0 | 0.33 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.538 | 6.0 | 0.29 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.538 | 6.0 | 0.29 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 12.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.915 | 8.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 12.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.915 | 8.0 | 0.83 | – (0) | – | – | 1.4 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 12.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.884 | 6.0 | 0.58 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 12.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.884 | 6.0 | 0.58 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 12.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.615 | 6.0 | 0.33 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 12.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.615 | 6.0 | 0.33 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 12.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.538 | 6.0 | 0.29 | – (0) | – | – | 0.0 |
| current_mA | phase_blocks_stationary_only | {"curvature_threshold": 12.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.538 | 6.0 | 0.29 | – (0) | – | – | 0.0 |
| temperature_C | setpoint_blocks | {"settling_suppression": false, "transient_extra": "none", "transient_transition_window": 0} | 0.620 | 3.5 | 0.93 | 0.56 (9) | 0.0 | 13.9 | 17.6 |
| temperature_C | setpoint_blocks | {"settling_suppression": true, "transient_extra": "none", "transient_transition_window": 0} | 0.599 | 3.5 | 0.93 | 0.00 (9) | 0.0 | 0.0 | 6.2 |
| temperature_C | setpoint_blocks | {"settling_suppression": false, "transient_extra": "none", "transient_transition_window": 60} | 0.620 | 3.5 | 0.93 | 0.56 (9) | 0.0 | 13.9 | 17.6 |
| temperature_C | setpoint_blocks | {"settling_suppression": true, "transient_extra": "none", "transient_transition_window": 60} | 0.642 | 3.5 | 0.80 | 0.00 (9) | 0.0 | 0.0 | 1.4 |
| temperature_C | setpoint_blocks | {"settling_suppression": false, "transient_extra": "none", "transient_transition_window": 120} | 0.620 | 3.5 | 0.93 | 0.56 (9) | 0.0 | 13.9 | 17.6 |
| temperature_C | setpoint_blocks | {"settling_suppression": true, "transient_extra": "none", "transient_transition_window": 120} | 0.660 | 3.5 | 0.73 | 0.00 (9) | 0.0 | 0.0 | 0.0 |
| temperature_C | setpoint_blocks | {"settling_suppression": false, "transient_extra": "none", "transient_transition_window": 210} | 0.620 | 3.5 | 0.93 | 0.56 (9) | 0.0 | 13.9 | 17.6 |
| temperature_C | setpoint_blocks | {"settling_suppression": true, "transient_extra": "none", "transient_transition_window": 210} | 0.602 | 3.5 | 0.53 | 0.00 (9) | 0.0 | 0.0 | 0.0 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.662 | 3.5 | 0.93 | 1.00 (9) | 0.7 | 16.1 | 17.6 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.789 | 3.5 | 0.93 | 1.00 (9) | 0.7 | 2.2 | 6.2 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.662 | 3.5 | 0.93 | 1.00 (9) | 0.7 | 16.1 | 17.6 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.861 | 5.0 | 0.80 | 1.00 (9) | 0.7 | 2.2 | 0.5 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.667 | 3.5 | 0.93 | 1.00 (9) | 0.7 | 16.1 | 17.6 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.886 | 3.5 | 0.93 | 1.00 (9) | 0.7 | 2.2 | 0.5 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.667 | 3.5 | 0.93 | 1.00 (9) | 0.7 | 16.1 | 17.6 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.886 | 3.5 | 0.93 | 1.00 (9) | 0.7 | 2.2 | 0.5 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.677 | 3.5 | 0.93 | 1.00 (9) | 0.7 | 13.9 | 17.6 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.788 | 3.5 | 0.93 | 1.00 (9) | 0.7 | 0.0 | 6.2 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.677 | 3.5 | 0.93 | 1.00 (9) | 0.7 | 13.9 | 17.6 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.881 | 5.0 | 0.80 | 1.00 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.677 | 3.5 | 0.93 | 1.00 (9) | 0.7 | 13.9 | 17.6 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.905 | 3.5 | 0.93 | 1.00 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.677 | 3.5 | 0.93 | 1.00 (9) | 0.7 | 13.9 | 17.6 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.893 | 3.5 | 0.87 | 1.00 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.647 | 3.5 | 0.93 | 0.89 (9) | 0.7 | 13.9 | 17.6 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.749 | 3.5 | 0.93 | 0.89 (9) | 0.7 | 0.0 | 6.2 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.647 | 3.5 | 0.93 | 0.89 (9) | 0.7 | 13.9 | 17.6 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.834 | 5.0 | 0.80 | 0.89 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.647 | 3.5 | 0.93 | 0.89 (9) | 0.7 | 13.9 | 17.6 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.861 | 3.5 | 0.93 | 0.89 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.647 | 3.5 | 0.93 | 0.89 (9) | 0.7 | 13.9 | 17.6 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.848 | 3.5 | 0.87 | 0.89 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.718 | 15.0 | 0.93 | 1.00 (9) | 0.7 | 8.3 | 10.9 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.781 | 15.0 | 0.93 | 1.00 (9) | 0.7 | 2.2 | 5.7 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.718 | 15.0 | 0.93 | 1.00 (9) | 0.7 | 8.3 | 10.9 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.855 | 15.0 | 0.93 | 1.00 (9) | 0.7 | 2.2 | 0.5 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.718 | 15.0 | 0.93 | 1.00 (9) | 0.7 | 8.3 | 10.9 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.855 | 15.0 | 0.93 | 1.00 (9) | 0.7 | 2.2 | 0.5 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.718 | 15.0 | 0.93 | 1.00 (9) | 0.7 | 8.3 | 10.9 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.855 | 15.0 | 0.93 | 1.00 (9) | 0.7 | 2.2 | 0.5 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.673 | 6.0 | 0.80 | 1.00 (9) | 0.7 | 13.3 | 16.1 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.786 | 6.0 | 0.80 | 1.00 (9) | 0.7 | 0.0 | 5.2 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.673 | 6.0 | 0.80 | 1.00 (9) | 0.7 | 13.3 | 16.1 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.892 | 6.0 | 0.80 | 1.00 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.673 | 6.0 | 0.80 | 1.00 (9) | 0.7 | 13.3 | 16.1 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.904 | 3.5 | 0.93 | 1.00 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.673 | 6.0 | 0.80 | 1.00 (9) | 0.7 | 13.3 | 16.1 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.892 | 6.0 | 0.80 | 1.00 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.641 | 6.0 | 0.80 | 0.89 (9) | 0.7 | 13.3 | 16.1 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.745 | 6.0 | 0.80 | 0.89 (9) | 0.7 | 0.0 | 5.2 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.641 | 6.0 | 0.80 | 0.89 (9) | 0.7 | 13.3 | 16.1 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.845 | 6.0 | 0.80 | 0.89 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.641 | 6.0 | 0.80 | 0.89 (9) | 0.7 | 13.3 | 16.1 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.859 | 3.5 | 0.93 | 0.89 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.641 | 6.0 | 0.80 | 0.89 (9) | 0.7 | 13.3 | 16.1 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.846 | 3.5 | 0.87 | 0.89 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 12.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.643 | 3.5 | 0.93 | 0.89 (9) | 0.7 | 13.9 | 17.6 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 12.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.740 | 3.5 | 0.93 | 0.89 (9) | 0.7 | 0.0 | 6.2 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 12.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.643 | 3.5 | 0.93 | 0.89 (9) | 0.7 | 13.9 | 17.6 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 12.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.819 | 5.0 | 0.73 | 0.89 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 12.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.643 | 3.5 | 0.93 | 0.89 (9) | 0.7 | 13.9 | 17.6 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 12.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.845 | 3.5 | 0.87 | 0.89 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 12.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.643 | 3.5 | 0.93 | 0.89 (9) | 0.7 | 13.9 | 17.6 |
| temperature_C | setpoint_blocks | {"curvature_threshold": 12.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.832 | 3.5 | 0.80 | 0.89 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks | {"settling_suppression": false, "transient_extra": "none", "transient_transition_window": 0} | 0.591 | 3.5 | 0.87 | 0.56 (9) | 0.0 | 13.3 | 17.1 |
| temperature_C | phase_blocks | {"settling_suppression": true, "transient_extra": "none", "transient_transition_window": 0} | 0.546 | 3.5 | 0.87 | 0.00 (9) | 0.0 | 0.0 | 6.2 |
| temperature_C | phase_blocks | {"settling_suppression": false, "transient_extra": "none", "transient_transition_window": 60} | 0.591 | 3.5 | 0.87 | 0.56 (9) | 0.0 | 13.3 | 17.1 |
| temperature_C | phase_blocks | {"settling_suppression": true, "transient_extra": "none", "transient_transition_window": 60} | 0.577 | 3.5 | 0.73 | 0.00 (9) | 0.0 | 0.0 | 1.4 |
| temperature_C | phase_blocks | {"settling_suppression": false, "transient_extra": "none", "transient_transition_window": 120} | 0.591 | 3.5 | 0.87 | 0.56 (9) | 0.0 | 13.3 | 17.1 |
| temperature_C | phase_blocks | {"settling_suppression": true, "transient_extra": "none", "transient_transition_window": 120} | 0.590 | 3.5 | 0.67 | 0.00 (9) | 0.0 | 0.0 | 0.0 |
| temperature_C | phase_blocks | {"settling_suppression": false, "transient_extra": "none", "transient_transition_window": 210} | 0.591 | 3.5 | 0.87 | 0.56 (9) | 0.0 | 13.3 | 17.1 |
| temperature_C | phase_blocks | {"settling_suppression": true, "transient_extra": "none", "transient_transition_window": 210} | 0.526 | 3.5 | 0.47 | 0.00 (9) | 0.0 | 0.0 | 0.0 |
| temperature_C | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.662 | 3.5 | 0.87 | 1.00 (9) | 0.7 | 15.6 | 17.1 |
| temperature_C | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.753 | 3.5 | 0.87 | 1.00 (9) | 0.7 | 2.2 | 6.2 |
| temperature_C | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.662 | 3.5 | 0.87 | 1.00 (9) | 0.7 | 15.6 | 17.1 |
| temperature_C | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.817 | 5.0 | 0.73 | 1.00 (9) | 0.7 | 2.2 | 0.5 |
| temperature_C | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.666 | 3.5 | 0.87 | 1.00 (9) | 0.7 | 15.6 | 17.1 |
| temperature_C | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.846 | 3.5 | 0.87 | 1.00 (9) | 0.7 | 2.2 | 0.5 |
| temperature_C | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.666 | 3.5 | 0.87 | 1.00 (9) | 0.7 | 15.6 | 17.1 |
| temperature_C | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.846 | 3.5 | 0.87 | 1.00 (9) | 0.7 | 2.2 | 0.5 |
| temperature_C | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.652 | 3.5 | 0.87 | 1.00 (9) | 0.7 | 13.3 | 17.1 |
| temperature_C | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.749 | 3.5 | 0.87 | 1.00 (9) | 0.7 | 0.0 | 6.2 |
| temperature_C | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.652 | 3.5 | 0.87 | 1.00 (9) | 0.7 | 13.3 | 17.1 |
| temperature_C | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.833 | 5.0 | 0.73 | 1.00 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.652 | 3.5 | 0.87 | 1.00 (9) | 0.7 | 13.3 | 17.1 |
| temperature_C | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.861 | 3.5 | 0.87 | 1.00 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.652 | 3.5 | 0.87 | 1.00 (9) | 0.7 | 13.3 | 17.1 |
| temperature_C | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.848 | 3.5 | 0.80 | 1.00 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.620 | 3.5 | 0.87 | 0.89 (9) | 0.7 | 13.3 | 17.1 |
| temperature_C | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.708 | 3.5 | 0.87 | 0.89 (9) | 0.7 | 0.0 | 6.2 |
| temperature_C | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.620 | 3.5 | 0.87 | 0.89 (9) | 0.7 | 13.3 | 17.1 |
| temperature_C | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.782 | 5.0 | 0.73 | 0.89 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.620 | 3.5 | 0.87 | 0.89 (9) | 0.7 | 13.3 | 17.1 |
| temperature_C | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.812 | 3.5 | 0.87 | 0.89 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.620 | 3.5 | 0.87 | 0.89 (9) | 0.7 | 13.3 | 17.1 |
| temperature_C | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.798 | 3.5 | 0.80 | 0.89 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.739 | 15.0 | 0.93 | 1.00 (9) | 0.7 | 3.9 | 7.1 |
| temperature_C | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.754 | 9.0 | 0.93 | 1.00 (9) | 0.7 | 2.2 | 5.7 |
| temperature_C | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.739 | 15.0 | 0.93 | 1.00 (9) | 0.7 | 3.9 | 7.1 |
| temperature_C | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.826 | 9.0 | 0.93 | 1.00 (9) | 0.7 | 2.2 | 0.5 |
| temperature_C | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.739 | 15.0 | 0.93 | 1.00 (9) | 0.7 | 3.9 | 7.1 |
| temperature_C | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.826 | 9.0 | 0.93 | 1.00 (9) | 0.7 | 2.2 | 0.5 |
| temperature_C | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.739 | 15.0 | 0.93 | 1.00 (9) | 0.7 | 3.9 | 7.1 |
| temperature_C | phase_blocks | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.826 | 9.0 | 0.93 | 1.00 (9) | 0.7 | 2.2 | 0.5 |
| temperature_C | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.690 | 15.0 | 0.80 | 1.00 (9) | 0.7 | 1.7 | 7.6 |
| temperature_C | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.758 | 6.0 | 0.80 | 1.00 (9) | 0.7 | 0.0 | 5.2 |
| temperature_C | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.690 | 15.0 | 0.80 | 1.00 (9) | 0.7 | 1.7 | 7.6 |
| temperature_C | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.859 | 6.0 | 0.80 | 1.00 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.690 | 15.0 | 0.80 | 1.00 (9) | 0.7 | 1.7 | 7.6 |
| temperature_C | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.860 | 3.5 | 0.87 | 1.00 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.690 | 15.0 | 0.80 | 1.00 (9) | 0.7 | 1.7 | 7.6 |
| temperature_C | phase_blocks | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.859 | 6.0 | 0.80 | 1.00 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.628 | 6.0 | 0.80 | 0.89 (9) | 0.7 | 12.2 | 15.7 |
| temperature_C | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.713 | 6.0 | 0.80 | 0.89 (9) | 0.7 | 0.0 | 5.2 |
| temperature_C | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.628 | 6.0 | 0.80 | 0.89 (9) | 0.7 | 12.2 | 15.7 |
| temperature_C | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.808 | 6.0 | 0.80 | 0.89 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.628 | 6.0 | 0.80 | 0.89 (9) | 0.7 | 12.2 | 15.7 |
| temperature_C | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.811 | 3.5 | 0.87 | 0.89 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.628 | 6.0 | 0.80 | 0.89 (9) | 0.7 | 12.2 | 15.7 |
| temperature_C | phase_blocks | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.808 | 6.0 | 0.80 | 0.89 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks | {"curvature_threshold": 12.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.620 | 3.5 | 0.87 | 0.89 (9) | 0.7 | 13.3 | 17.1 |
| temperature_C | phase_blocks | {"curvature_threshold": 12.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.701 | 3.5 | 0.87 | 0.89 (9) | 0.7 | 0.0 | 6.2 |
| temperature_C | phase_blocks | {"curvature_threshold": 12.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.620 | 3.5 | 0.87 | 0.89 (9) | 0.7 | 13.3 | 17.1 |
| temperature_C | phase_blocks | {"curvature_threshold": 12.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.781 | 5.0 | 0.73 | 0.89 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks | {"curvature_threshold": 12.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.620 | 3.5 | 0.87 | 0.89 (9) | 0.7 | 13.3 | 17.1 |
| temperature_C | phase_blocks | {"curvature_threshold": 12.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.796 | 3.5 | 0.80 | 0.89 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks | {"curvature_threshold": 12.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.620 | 3.5 | 0.87 | 0.89 (9) | 0.7 | 13.3 | 17.1 |
| temperature_C | phase_blocks | {"curvature_threshold": 12.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.782 | 3.5 | 0.73 | 0.89 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks_stationary_only | {"settling_suppression": false, "transient_extra": "none", "transient_transition_window": 0} | 0.546 | 3.5 | 0.87 | 0.00 (9) | 0.0 | 0.0 | 6.2 |
| temperature_C | phase_blocks_stationary_only | {"settling_suppression": true, "transient_extra": "none", "transient_transition_window": 0} | 0.546 | 3.5 | 0.87 | 0.00 (9) | 0.0 | 0.0 | 6.2 |
| temperature_C | phase_blocks_stationary_only | {"settling_suppression": false, "transient_extra": "none", "transient_transition_window": 60} | 0.577 | 3.5 | 0.73 | 0.00 (9) | 0.0 | 0.0 | 1.4 |
| temperature_C | phase_blocks_stationary_only | {"settling_suppression": true, "transient_extra": "none", "transient_transition_window": 60} | 0.577 | 3.5 | 0.73 | 0.00 (9) | 0.0 | 0.0 | 1.4 |
| temperature_C | phase_blocks_stationary_only | {"settling_suppression": false, "transient_extra": "none", "transient_transition_window": 120} | 0.590 | 3.5 | 0.67 | 0.00 (9) | 0.0 | 0.0 | 0.0 |
| temperature_C | phase_blocks_stationary_only | {"settling_suppression": true, "transient_extra": "none", "transient_transition_window": 120} | 0.590 | 3.5 | 0.67 | 0.00 (9) | 0.0 | 0.0 | 0.0 |
| temperature_C | phase_blocks_stationary_only | {"settling_suppression": false, "transient_extra": "none", "transient_transition_window": 210} | 0.526 | 3.5 | 0.47 | 0.00 (9) | 0.0 | 0.0 | 0.0 |
| temperature_C | phase_blocks_stationary_only | {"settling_suppression": true, "transient_extra": "none", "transient_transition_window": 210} | 0.526 | 3.5 | 0.47 | 0.00 (9) | 0.0 | 0.0 | 0.0 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.753 | 3.5 | 0.87 | 1.00 (9) | 0.7 | 2.2 | 6.2 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.753 | 3.5 | 0.87 | 1.00 (9) | 0.7 | 2.2 | 6.2 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.817 | 5.0 | 0.73 | 1.00 (9) | 0.7 | 2.2 | 0.5 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.817 | 5.0 | 0.73 | 1.00 (9) | 0.7 | 2.2 | 0.5 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.846 | 3.5 | 0.87 | 1.00 (9) | 0.7 | 2.2 | 0.5 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.846 | 3.5 | 0.87 | 1.00 (9) | 0.7 | 2.2 | 0.5 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.846 | 3.5 | 0.87 | 1.00 (9) | 0.7 | 2.2 | 0.5 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.846 | 3.5 | 0.87 | 1.00 (9) | 0.7 | 2.2 | 0.5 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.749 | 3.5 | 0.87 | 1.00 (9) | 0.7 | 0.0 | 6.2 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.749 | 3.5 | 0.87 | 1.00 (9) | 0.7 | 0.0 | 6.2 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.833 | 5.0 | 0.73 | 1.00 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.833 | 5.0 | 0.73 | 1.00 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.861 | 3.5 | 0.87 | 1.00 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.861 | 3.5 | 0.87 | 1.00 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.848 | 3.5 | 0.80 | 1.00 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.848 | 3.5 | 0.80 | 1.00 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.708 | 3.5 | 0.87 | 0.89 (9) | 0.7 | 0.0 | 6.2 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 0} | 0.708 | 3.5 | 0.87 | 0.89 (9) | 0.7 | 0.0 | 6.2 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.782 | 5.0 | 0.73 | 0.89 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 60} | 0.782 | 5.0 | 0.73 | 0.89 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.812 | 3.5 | 0.87 | 0.89 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 120} | 0.812 | 3.5 | 0.87 | 0.89 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.798 | 3.5 | 0.80 | 0.89 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_nonstationary", "transient_transition_window": 210} | 0.798 | 3.5 | 0.80 | 0.89 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.754 | 9.0 | 0.93 | 1.00 (9) | 0.7 | 2.2 | 5.7 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.754 | 9.0 | 0.93 | 1.00 (9) | 0.7 | 2.2 | 5.7 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.826 | 9.0 | 0.93 | 1.00 (9) | 0.7 | 2.2 | 0.5 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.826 | 9.0 | 0.93 | 1.00 (9) | 0.7 | 2.2 | 0.5 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.826 | 9.0 | 0.93 | 1.00 (9) | 0.7 | 2.2 | 0.5 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.826 | 9.0 | 0.93 | 1.00 (9) | 0.7 | 2.2 | 0.5 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.826 | 9.0 | 0.93 | 1.00 (9) | 0.7 | 2.2 | 0.5 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 6.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.826 | 9.0 | 0.93 | 1.00 (9) | 0.7 | 2.2 | 0.5 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.758 | 6.0 | 0.80 | 1.00 (9) | 0.7 | 0.0 | 5.2 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.758 | 6.0 | 0.80 | 1.00 (9) | 0.7 | 0.0 | 5.2 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.859 | 6.0 | 0.80 | 1.00 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.859 | 6.0 | 0.80 | 1.00 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.860 | 3.5 | 0.87 | 1.00 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.860 | 3.5 | 0.87 | 1.00 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.859 | 6.0 | 0.80 | 1.00 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 8.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.859 | 6.0 | 0.80 | 1.00 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.713 | 6.0 | 0.80 | 0.89 (9) | 0.7 | 0.0 | 5.2 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.713 | 6.0 | 0.80 | 0.89 (9) | 0.7 | 0.0 | 5.2 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.808 | 6.0 | 0.80 | 0.89 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.808 | 6.0 | 0.80 | 0.89 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.811 | 3.5 | 0.87 | 0.89 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.811 | 3.5 | 0.87 | 0.89 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.808 | 6.0 | 0.80 | 0.89 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 10.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.808 | 6.0 | 0.80 | 0.89 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 12.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.701 | 3.5 | 0.87 | 0.89 (9) | 0.7 | 0.0 | 6.2 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 12.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 0} | 0.701 | 3.5 | 0.87 | 0.89 (9) | 0.7 | 0.0 | 6.2 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 12.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.781 | 5.0 | 0.73 | 0.89 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 12.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 60} | 0.781 | 5.0 | 0.73 | 0.89 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 12.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.796 | 3.5 | 0.80 | 0.89 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 12.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 120} | 0.796 | 3.5 | 0.80 | 0.89 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 12.0, "settling_suppression": false, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.782 | 3.5 | 0.73 | 0.89 (9) | 0.7 | 0.0 | 0.0 |
| temperature_C | phase_blocks_stationary_only | {"curvature_threshold": 12.0, "settling_suppression": true, "transient_extra": "curvature_all", "transient_transition_window": 210} | 0.782 | 3.5 | 0.73 | 0.89 (9) | 0.7 | 0.0 | 0.0 |

### WS3 MAD threshold (best transient F1 per threshold)

| Measurand | MAD | Best transient F1 | FA/h |
|---|---|---|---|
| voltage_V | 3.5 | 0.924 | 0.8 |
| voltage_V | 5.0 | 0.881 | 0.6 |
| voltage_V | 6.0 | 0.854 | 0.6 |
| voltage_V | 7.0 | 0.869 | 0.4 |
| voltage_V | 8.0 | 0.820 | 0.4 |
| voltage_V | 9.0 | 0.790 | 0.4 |
| voltage_V | 12.0 | 0.750 | 0.4 |
| voltage_V | 15.0 | 0.691 | 0.4 |
| current_mA | 3.5 | 0.698 | 3.6 |
| current_mA | 5.0 | 0.869 | 0.4 |
| current_mA | 6.0 | 0.891 | 1.3 |
| current_mA | 7.0 | 0.916 | 0.8 |
| current_mA | 8.0 | 0.917 | 0.6 |
| current_mA | 9.0 | 0.917 | 0.6 |
| current_mA | 12.0 | 0.918 | 0.6 |
| current_mA | 15.0 | 0.855 | 0.4 |
| temperature_C | 3.5 | 0.905 | 0.3 |
| temperature_C | 5.0 | 0.881 | 0.3 |
| temperature_C | 6.0 | 0.892 | 0.1 |
| temperature_C | 7.0 | 0.892 | 0.1 |
| temperature_C | 8.0 | 0.892 | 0.1 |
| temperature_C | 9.0 | 0.853 | 1.5 |
| temperature_C | 12.0 | 0.851 | 1.5 |
| temperature_C | 15.0 | 0.855 | 1.5 |

### WS3 CUSUM (best configuration per mode and exclusion window)

| Measurand | Mode | Window | min_baseline | min_series | k | h | ARL0 ok | FA | pre-onset | detected | median delay |
|---|---|---|---|---|---|---|---|---|---|---|---|
| voltage_V | run | 0 | 120 | 30 | 0.5 | 12 | True | 0 | 0 | 6 | 56 |
| voltage_V | run | 5 | 120 | 30 | 0.5 | 12 | True | 0 | 0 | 6 | 56 |
| voltage_V | run | 20 | 120 | 30 | 0.5 | 12 | True | 0 | 0 | 6 | 56 |
| voltage_V | segment | 0 | 60 | 30 | 0.5 | 12 | True | 0 | 0 | 6 | 62 |
| voltage_V | segment | 5 | 60 | 30 | 0.5 | 12 | True | 0 | 0 | 6 | 62 |
| voltage_V | segment | 20 | 30 | 30 | 0.5 | 15 | True | 0 | 0 | 6 | 66 |
| current_mA | run | 0 | 180 | 30 | 2.0 | 5 | True | 6 | 2 | 4 | 33 |
| current_mA | run | 10 | 180 | 30 | 2.0 | 5 | True | 6 | 2 | 4 | 33 |
| current_mA | run | 20 | 60 | 30 | 3.0 | 30 | True | 5 | 2 | 4 | 64 |
| current_mA | run | 45 | 60 | 30 | 3.0 | 30 | True | 0 | 0 | 6 | 66 |
| current_mA | run | 90 | 90 | 30 | 2.0 | 12 | True | 0 | 0 | 6 | 40 |
| current_mA | run | 135 | 90 | 30 | 3.0 | 4 | True | 0 | 0 | 6 | 55 |
| current_mA | segment | 0 | 90 | 30 | 2.0 | 4 | True | 0 | 0 | 6 | 42 |
| current_mA | segment | 10 | 90 | 30 | 2.0 | 4 | True | 0 | 0 | 6 | 42 |
| current_mA | segment | 20 | 90 | 30 | 2.0 | 4 | True | 0 | 0 | 6 | 46 |
| current_mA | segment | 45 | 60 | 30 | 2.0 | 8 | True | 0 | 0 | 6 | 52 |
| current_mA | segment | 90 | 15 | 30 | 3.0 | 30 | True | 0 | 0 | 6 | 142 |
| current_mA | segment | 135 | 10 | 30 | 3.0 | 30 | True | 0 | 0 | 2 | 105 |
| temperature_C | run | 0 | 150 | 30 | 3.0 | 12 | True | 4 | 2 | 2 | 184 |
| temperature_C | run | 30 | 10 | 30 | 1.5 | 6 | True | 4 | 2 | 4 | 238 |
| temperature_C | run | 60 | 10 | 30 | 1.5 | 8 | True | 4 | 0 | 6 | 180 |
| temperature_C | run | 120 | 10 | 30 | 1.0 | 12 | True | 0 | 0 | 6 | 181 |
| temperature_C | run | 210 | 30 | 30 | 0.75 | 10 | True | 0 | 0 | 2 | 180 |
| temperature_C | segment | 0 | 90 | 30 | 0.75 | 25 | True | 0 | 0 | 4 | 214 |
| temperature_C | segment | 30 | 60 | 30 | 1.0 | 25 | True | 0 | 0 | 4 | 203 |
| temperature_C | segment | 60 | 60 | 30 | 1.0 | 25 | True | 0 | 0 | 4 | 200 |
| temperature_C | segment | 120 | 150 | 30 | 0.5 | 10 | True | 0 | 0 | 4 | 136 |
| temperature_C | segment | 210 | 150 | 30 | 0.5 | 10 | True | 0 | 0 | 2 | 189 |

### Strata (hybrid M6, validation): recall by noise group / variant / magnitude

- voltage_V: noise_group: noise_high 16/18, noise_low 17/18, noise_mid 18/18; variant: VA 17/18, VB 18/18, VC 16/18; magnitude_bin: 10-30 sigma 27/29, <10 sigma 7/7, >=30 sigma 3/3
- current_mA: noise_group: noise_high 13/18, noise_low 17/18, noise_mid 18/18; variant: IA 17/18, IB 18/18, IC 13/18; magnitude_bin: 10-30 sigma 20/22, <10 sigma 0/2, >=30 sigma 15/15
- temperature_C: noise_group: noise_high 15/18, noise_low 16/18, noise_mid 15/18; variant: TA 16/18, TB 15/18, TC 15/18; magnitude_bin: 10-30 sigma 13/16, <10 sigma 1/2, >=30 sigma 21/21