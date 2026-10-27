# IMUCA Synthetic Benchmark — Conventional Baseline Summary

> SYNTHETIC BENCHMARK: conventional-algorithm verification on simulated data only. No physical sensor performance is claimed.

- Run: `python scripts/run_synthetic_benchmark.py` at 2026-10-26T04:34:50.951748+00:00
- Suite manifest SHA-256: `dd99c42e05d886c0…`, generator v2.0.0, 50 scenarios / 147,865 records
- All CSVs verified against manifest checksums: **True**

**Error vs uncertainty.** Bias/MAE/RMSE below are *measurement error* metrics, computed against the simulated reference and, separately, against simulation ground truth. *U* is a GUM expanded uncertainty (k = 2) from an explicitly INCOMPLETE budget; its empirical coverage against ground truth is reported, not assumed.

## 1. Ingestion through the existing pipeline (run by run)

| Scenario group | Runs | Valid runs | Records | Error records | Warning records |
|---|---|---|---|---|---|
| voltage | 27 | 27 | 13,200 | 0 | 31 |
| current | 27 | 27 | 20,469 | 0 | 38 |
| temperature | 16 | 16 | 28,132 | 0 | 41 |
| fault_detection | 144 | 120 | 86,064 | 84 | 220 |

Error/warning records occur only in scenarios with injected record faults (non-finite, duplicates, gaps, invalid status, out-of-range spikes). All fault-free runs validate with zero errors. Malformed fixtures: `MAL_zero_byte.csv` → rejected, `MAL_header_only.csv` → rejected, `MAL_non_numeric_value.csv` → rejected, `MAL_non_finite.csv` → rejected, `MAL_backwards_time.csv` → rejected, `MAL_duplicate_sequence.csv` → rejected, `MAL_bad_timestamp.csv` → rejected, `MAL_out_of_range.csv` → rejected, `MAL_sequence_gap.csv` → flagged, `MAL_invalid_status.csv` → flagged, `MAL_missing_sequence_column.csv` → flagged

## 2. Calibration (fit on calibration runs → select on validation runs → test once)

| Scenario | Model | Val RMSE uncal → cal (vs ref) | Val RMSE reduction | Test RMSE uncal → cal (vs true) | Test bias cal (vs true) | s_r (expected) | U(k=2) at x0 | Coverage of U vs true (test) |
|---|---|---|---|---|---|---|---|---|
| `VOLT_SWEEP_LINEAR` | linear | 0.03664 → 0.001462 V | 96.0 % | 0.04067 → 0.001499 V | -5.073e-05 V | 0.001457 (0.001528) | 0.003168 V | 97.4 % |
| `VOLT_SWEEP_NONLINEAR` | polynomial_deg2 | 0.04676 → 0.001594 V | 96.6 % | 0.05458 → 0.001525 V | -0.0002021 V | 0.001519 (0.001528) | 0.003286 V | 97.4 % |
| `CURR_SWEEP_AMBIENT` | linear | 9.066 → 0.2049 mA | 97.7 % | 9.548 → 0.6414 mA | 0.1506 mA | 0.1983 (0.2021) | 0.4773 mA | 69.2 % |
| `CURR_SWEEP_SELFHEAT` | polynomial_deg2 | 2.651 → 0.3632 mA | 86.3 % | 2.786 → 0.8834 mA | -0.1143 mA | 0.3142 (0.2021) | 0.6825 mA | 83.6 % |
| `TEMP_PLATEAUS` | linear | 0.3529 → 0.0349 degC | 90.1 % | 0.3874 → 0.04004 degC | 0.01873 degC | 0.03437 (0.03501) | 0.08082 degC | 94.7 % |

Test breakdown by operating condition (calibrated RMSE vs true; coverage of U vs true):

- `VOLT_SWEEP_LINEAR` — extrapolation_above_cal_range: 0.001569 V (99 %); grid_A: 0.001403 V (98 %); grid_B_interleaved: 0.001535 V (97 %)
- `VOLT_SWEEP_NONLINEAR` — extrapolation_above_cal_range: 0.001491 V (99 %); grid_A: 0.001586 V (98 %); grid_B_interleaved: 0.001497 V (97 %)
- `CURR_SWEEP_AMBIENT` — extrapolation_above_cal_range: 0.4399 mA (70 %); grid_A: 0.2918 mA (92 %); grid_A_ambient30C: 1.023 mA (30 %); grid_B_interleaved: 0.3024 mA (88 %)
- `CURR_SWEEP_SELFHEAT` — extrapolation_above_cal_range: 0.8004 mA (57 %); grid_A: 0.4074 mA (92 %); grid_A_descending: 1.405 mA (70 %); grid_B_interleaved: 0.389 mA (92 %)
- `TEMP_PLATEAUS` — extrapolation_above_cal_range: 0.03928 degC (92 %); grid_A: 0.0396 degC (96 %); grid_B_interleaved: 0.04078 degC (93 %)

Uncalibrated shunt-model budget at 1 A (existing `evaluate_shunt_current_uncertainty`): u_c = 2.89 mA, U = 5.79 mA, dominant: Shunt Resistor Tolerance. INCOMPLETE: ADC gain/offset, TCR and self-heating not included.

## 3. Repeatability (VOLT_REPEATABILITY)

| Run | n | s | 95 % CI of σ | expected σ in CI | u_A of mean |
|---|---|---|---|---|---|
| CAL01 | 300 | 0.001553 V | [0.001438, 0.001688] V | True | 8.967e-05 V |
| VAL01 | 300 | 0.001517 V | [0.001404, 0.001649] V | True | 8.757e-05 V |
| TST01 | 300 | 0.00159 V | [0.001472, 0.001729] V | True | 9.18e-05 V |

Expected σ from generator: 0.001528 V (√(σ² + q²/12)).

## 4. Drift (error series = observed − reference)

| Scenario | Run | Drift injected | True rate | Est. rate (full run) | Est. rate (post-onset, oracle segment) | Rate error post-onset | Regression alarm | CUSUM alarm | CUSUM delay |
|---|---|---|---|---|---|---|---|---|---|
| `VOLT_DRIFT` | CAL01 | False | 0 | 1.627e-07 | – | – | False | True | – |
| `VOLT_DRIFT` | VAL01 | True | 5e-06 | 3.837e-06 | 4.789e-06 | -4.23 % | True | True | pre-onset alarm |
| `VOLT_DRIFT` | VAL02 | False | 0 | 9.505e-08 | – | – | False | True | – |
| `VOLT_DRIFT` | TST01 | True | -8e-06 | -4.967e-06 | -8.025e-06 | -0.319 % | True | True | pre-onset alarm |
| `VOLT_DRIFT` | TST02 | False | 0 | 6.755e-08 | – | – | False | True | – |
| `CURR_DRIFT` | CAL01 | False | 0 | 2.689e-05 | – | – | False | True | – |
| `CURR_DRIFT` | VAL01 | True | 0.003 | 0.002278 | 0.003029 | 0.959 % | True | True | 43 s |
| `CURR_DRIFT` | VAL02 | False | 0 | 1.842e-05 | – | – | False | True | – |
| `CURR_DRIFT` | TST01 | True | -0.004 | -0.00247 | -0.004022 | -0.54 % | True | True | 79 s |
| `CURR_DRIFT` | TST02 | False | 0 | -9.644e-06 | – | – | False | True | – |
| `TEMP_DRIFT` | CAL01 | False | 0 | 1.643e-06 | – | – | False | True | – |
| `TEMP_DRIFT` | VAL01 | True | 0.0001389 | 0.0001022 | 0.0001417 | 2.02 % | True | True | pre-onset alarm |
| `TEMP_DRIFT` | VAL02 | False | 0 | -1.901e-06 | – | – | False | True | – |
| `TEMP_DRIFT` | TST01 | True | -0.0002222 | -0.0001607 | -0.0002178 | 1.99 % | True | True | pre-onset alarm |
| `TEMP_DRIFT` | TST02 | False | 0 | 4.339e-07 | – | – | False | True | – |

Rates are in measurand units per second. Run-level detection (all partitions):

- `VOLT_DRIFT`: regression {'TP': 2, 'FN': 0, 'FP': 0, 'TN': 3}, CUSUM {'TP': 2, 'FN': 0, 'FP': 3, 'TN': 0}
- `CURR_DRIFT`: regression {'TP': 2, 'FN': 0, 'FP': 0, 'TN': 3}, CUSUM {'TP': 2, 'FN': 0, 'FP': 3, 'TN': 0}
- `TEMP_DRIFT`: regression {'TP': 2, 'FN': 0, 'FP': 0, 'TN': 3}, CUSUM {'TP': 2, 'FN': 0, 'FP': 3, 'TN': 0}

## 5. Fault detection — existing `DataQualityAssessor` (test partition)

| Scenario | Mode | Precision | Recall | False-alarm rate | Missed-detection rate | Event recall | FA near process events |
|---|---|---|---|---|---|---|---|
| `VOLT_INTEGRITY` | whole_run | 1 | 0.192 | 0 | 0.808 | 0.444 (4/9) | 0 |
| `VOLT_INTEGRITY` | per_protocol_segment | 1 | 1 | 0 | 0 | 1 (9/9) | 0 |
| `CURR_INTEGRITY` | whole_run | 0.875 | 0.25 | 0.00239 | 0.75 | 0.545 (6/11) | 2 |
| `CURR_INTEGRITY` | per_protocol_segment | 0.875 | 1 | 0.00955 | 0 | 1 (11/11) | 0 |
| `TEMP_INTEGRITY` | whole_run | 1 | 0.733 | 0 | 0.267 | 0.6 (6/10) | 0 |
| `TEMP_INTEGRITY` | per_protocol_segment | 0.0882 | 1 | 0.133 | 0 | 1 (10/10) | 8 |
| `FD_VOLT_NONE` | whole_run | – | – | 0 | – | – (0/0) | 0 |
| `FD_VOLT_NONE` | per_protocol_segment | – | – | 0 | – | – (0/0) | 0 |
| `FD_VOLT_ISOLATED_SPIKE` | whole_run | – | 0 | 0 | 1 | 0 (0/10) | 0 |
| `FD_VOLT_ISOLATED_SPIKE` | per_protocol_segment | 1 | 1 | 0 | 0 | 1 (10/10) | 0 |
| `FD_VOLT_OFFSET_SHIFT` | whole_run | – | 0 | 0 | 1 | 0 (0/2) | 0 |
| `FD_VOLT_OFFSET_SHIFT` | per_protocol_segment | 0.0256 | 0.00178 | 0.0596 | 0.998 | 0.5 (1/2) | 7 |
| `FD_VOLT_GAIN_CHANGE` | whole_run | – | 0 | 0 | 1 | 0 (0/2) | 0 |
| `FD_VOLT_GAIN_CHANGE` | per_protocol_segment | 0 | 0 | 0.0196 | 1 | 0 (0/2) | 4 |
| `FD_VOLT_GRADUAL_DRIFT` | whole_run | – | 0 | 0 | 1 | 0 (0/2) | 0 |
| `FD_VOLT_GRADUAL_DRIFT` | per_protocol_segment | – | 0 | 0 | 1 | 0 (0/2) | 0 |
| `FD_VOLT_ABRUPT_CHANGE` | whole_run | – | 0 | 0 | 1 | 0 (0/4) | 0 |
| `FD_VOLT_ABRUPT_CHANGE` | per_protocol_segment | 0.989 | 1 | 0.000902 | 0 | 1 (4/4) | 0 |
| `FD_VOLT_STUCK_SIGNAL` | whole_run | – | 0 | 0 | 1 | 0 (0/4) | 0 |
| `FD_VOLT_STUCK_SIGNAL` | per_protocol_segment | 1 | 0.171 | 0 | 0.829 | 0.25 (1/4) | 0 |
| `FD_VOLT_MISSING_SAMPLES` | whole_run | 1 | 1 | 0 | 0 | 1 (6/6) | 0 |
| `FD_VOLT_MISSING_SAMPLES` | per_protocol_segment | 1 | 1 | 0 | 0 | 1 (6/6) | 0 |
| `FD_VOLT_DUPLICATE_SEQUENCE` | whole_run | 1 | 1 | 0 | 0 | 1 (8/8) | 0 |
| `FD_VOLT_DUPLICATE_SEQUENCE` | per_protocol_segment | 0.889 | 1 | 0.000833 | 0 | 1 (8/8) | 0 |
| `FD_VOLT_COMMUNICATION_GAP` | whole_run | 1 | 1 | 0 | 0 | 1 (6/6) | 0 |
| `FD_VOLT_COMMUNICATION_GAP` | per_protocol_segment | 1 | 0.833 | 0 | 0.167 | 0.833 (5/6) | 0 |
| `FD_VOLT_INVALID_STATUS` | whole_run | 1 | 1 | 0 | 0 | 1 (6/6) | 0 |
| `FD_VOLT_INVALID_STATUS` | per_protocol_segment | 1 | 1 | 0 | 0 | 1 (6/6) | 0 |
| `FD_VOLT_NON_FINITE` | whole_run | 1 | 1 | 0 | 0 | 1 (6/6) | 0 |
| `FD_VOLT_NON_FINITE` | per_protocol_segment | 1 | 1 | 0 | 0 | 1 (6/6) | 0 |
| `FD_CURR_NONE` | whole_run | 0 | – | 0.00333 | – | – (0/0) | 4 |
| `FD_CURR_NONE` | per_protocol_segment | 0 | – | 0.005 | – | – (0/0) | 0 |
| `FD_CURR_ISOLATED_SPIKE` | whole_run | 0 | 0 | 0.00336 | 1 | 0 (0/10) | 4 |
| `FD_CURR_ISOLATED_SPIKE` | per_protocol_segment | 0.769 | 1 | 0.00252 | 0 | 1 (10/10) | 0 |
| `FD_CURR_OFFSET_SHIFT` | whole_run | 0.75 | 0.00369 | 0.00258 | 0.996 | 1 (2/2) | 1 |
| `FD_CURR_OFFSET_SHIFT` | per_protocol_segment | 0.769 | 0.0246 | 0.0155 | 0.975 | 1 (2/2) | 4 |
| `FD_CURR_GAIN_CHANGE` | whole_run | 0.75 | 0.00399 | 0.00223 | 0.996 | 1 (2/2) | 1 |
| `FD_CURR_GAIN_CHANGE` | per_protocol_segment | 0.331 | 0.0612 | 0.208 | 0.939 | 0.5 (1/2) | 4 |
| `FD_CURR_GRADUAL_DRIFT` | whole_run | 0.25 | 0.00259 | 0.00369 | 0.997 | 0.5 (1/2) | 3 |
| `FD_CURR_GRADUAL_DRIFT` | per_protocol_segment | 0 | 0 | 0.00246 | 1 | 0 (0/2) | 0 |
| `FD_CURR_ABRUPT_CHANGE` | whole_run | 0.5 | 0.0121 | 0.00193 | 0.988 | 0.5 (2/4) | 2 |
| `FD_CURR_ABRUPT_CHANGE` | per_protocol_segment | 0.994 | 1 | 0.000966 | 0 | 1 (4/4) | 0 |
| `FD_CURR_STUCK_SIGNAL` | whole_run | 0 | 0 | 0.00359 | 1 | 0 (0/4) | 4 |
| `FD_CURR_STUCK_SIGNAL` | per_protocol_segment | 0 | 0 | 0.00628 | 1 | 0 (0/4) | 0 |
| `FD_CURR_MISSING_SAMPLES` | whole_run | 0.826 | 1 | 0.00339 | 0 | 1 (6/6) | 4 |
| `FD_CURR_MISSING_SAMPLES` | per_protocol_segment | 0.826 | 1 | 0.00339 | 0 | 1 (6/6) | 0 |
| `FD_CURR_DUPLICATE_SEQUENCE` | whole_run | 0.667 | 1 | 0.00333 | 0 | 1 (8/8) | 4 |
| `FD_CURR_DUPLICATE_SEQUENCE` | per_protocol_segment | 0.444 | 1 | 0.00833 | 0 | 1 (8/8) | 0 |
| `FD_CURR_COMMUNICATION_GAP` | whole_run | 0.6 | 1 | 0.0036 | 0 | 1 (6/6) | 4 |
| `FD_CURR_COMMUNICATION_GAP` | per_protocol_segment | 0.5 | 1 | 0.00541 | 0 | 1 (6/6) | 0 |
| `FD_CURR_INVALID_STATUS` | whole_run | 0.75 | 1 | 0.00337 | 0 | 1 (6/6) | 4 |
| `FD_CURR_INVALID_STATUS` | per_protocol_segment | 0.75 | 1 | 0.00337 | 0 | 1 (6/6) | 0 |
| `FD_CURR_NON_FINITE` | whole_run | 0.6 | 1 | 0.00335 | 0 | 1 (6/6) | 4 |
| `FD_CURR_NON_FINITE` | per_protocol_segment | 0.429 | 1 | 0.0067 | 0 | 1 (6/6) | 0 |
| `FD_TEMP_NONE` | whole_run | – | – | 0 | – | – (0/0) | 0 |
| `FD_TEMP_NONE` | per_protocol_segment | 0 | – | 0.0583 | – | – (0/0) | 0 |
| `FD_TEMP_ISOLATED_SPIKE` | whole_run | – | 0 | 0 | 1 | 0 (0/10) | 0 |
| `FD_TEMP_ISOLATED_SPIKE` | per_protocol_segment | 0.105 | 0.8 | 0.0571 | 0.2 | 0.8 (8/10) | 0 |
| `FD_TEMP_OFFSET_SHIFT` | whole_run | – | 0 | 0 | 1 | 0 (0/2) | 0 |
| `FD_TEMP_OFFSET_SHIFT` | per_protocol_segment | 1 | 0.164 | 0 | 0.836 | 1 (2/2) | 0 |
| `FD_TEMP_GAIN_CHANGE` | whole_run | – | 0 | 0 | 1 | 0 (0/2) | 0 |
| `FD_TEMP_GAIN_CHANGE` | per_protocol_segment | 0.954 | 0.117 | 0.00447 | 0.883 | 1 (2/2) | 0 |
| `FD_TEMP_GRADUAL_DRIFT` | whole_run | – | 0 | 0 | 1 | 0 (0/2) | 0 |
| `FD_TEMP_GRADUAL_DRIFT` | per_protocol_segment | 1 | 0.0816 | 0 | 0.918 | 1 (2/2) | 0 |
| `FD_TEMP_ABRUPT_CHANGE` | whole_run | – | 0 | 0 | 1 | 0 (0/4) | 0 |
| `FD_TEMP_ABRUPT_CHANGE` | per_protocol_segment | 0.534 | 0.823 | 0.0625 | 0.177 | 0.75 (3/4) | 0 |
| `FD_TEMP_STUCK_SIGNAL` | whole_run | 0 | 0 | 0.00192 | 1 | 0 (0/4) | 0 |
| `FD_TEMP_STUCK_SIGNAL` | per_protocol_segment | 0.178 | 0.0833 | 0.0575 | 0.917 | 0.25 (1/4) | 0 |
| `FD_TEMP_MISSING_SAMPLES` | whole_run | 1 | 1 | 0 | 0 | 1 (6/6) | 0 |
| `FD_TEMP_MISSING_SAMPLES` | per_protocol_segment | 0.25 | 1 | 0.038 | 0 | 1 (6/6) | 0 |
| `FD_TEMP_DUPLICATE_SEQUENCE` | whole_run | 1 | 1 | 0 | 0 | 1 (8/8) | 0 |
| `FD_TEMP_DUPLICATE_SEQUENCE` | per_protocol_segment | 0.103 | 1 | 0.0583 | 0 | 1 (8/8) | 0 |
| `FD_TEMP_COMMUNICATION_GAP` | whole_run | 1 | 1 | 0 | 0 | 1 (6/6) | 0 |
| `FD_TEMP_COMMUNICATION_GAP` | per_protocol_segment | 0.0822 | 1 | 0.0591 | 0 | 1 (6/6) | 0 |
| `FD_TEMP_INVALID_STATUS` | whole_run | 1 | 1 | 0 | 0 | 1 (6/6) | 0 |
| `FD_TEMP_INVALID_STATUS` | per_protocol_segment | 0.152 | 1 | 0.0564 | 0 | 1 (6/6) | 0 |
| `FD_TEMP_NON_FINITE` | whole_run | 1 | 1 | 0 | 0 | 1 (6/6) | 0 |
| `FD_TEMP_NON_FINITE` | per_protocol_segment | 0.0789 | 1 | 0.0586 | 0 | 1 (6/6) | 0 |

Per-class event recall on the fault-detection benchmark (test partition, whole-run mode, pooled over measurands):

| Fault class | Events detected / total | Row recall |
|---|---|---|
| `abrupt_change` | 2 / 12 | 0.006 |
| `communication_gap` | 18 / 18 | 1.000 |
| `duplicate_sequence` | 24 / 24 | 1.000 |
| `gain_change` | 2 / 6 | 0.002 |
| `gradual_drift` | 1 / 6 | 0.001 |
| `invalid_status` | 18 / 18 | 1.000 |
| `isolated_spike` | 0 / 30 | 0.000 |
| `missing_samples` | 18 / 18 | 1.000 |
| `non_finite` | 18 / 18 | 1.000 |
| `offset_shift` | 2 / 6 | 0.001 |
| `stuck_signal` | 0 / 12 | 0.000 |

## 6. Dynamic scenarios with a static calibration

- `CURR_LOAD_STEPS` (calibration from `CURR_SWEEP_SELFHEAT`): test RMSE vs true uncal 2.834 → static-cal 1.199
  - steady: static-cal bias vs true -0.177, RMSE 1.199
  - within 3τ after load step: RMSE vs true 1.033; steady: 0.7914 (all partitions)
- `TEMP_RAMPS` (calibration from `TEMP_PLATEAUS`): test RMSE vs true uncal 1.323 → static-cal 1.272
  - cooling_ramp: static-cal bias vs true 1.527, RMSE 1.54
  - heating_ramp: static-cal bias vs true -1.493, RMSE 1.505
  - hold_end: static-cal bias vs true 0.2743, RMSE 0.45
  - hold_peak: static-cal bias vs true -0.08078, RMSE 0.2732
  - hold_start: static-cal bias vs true 0.02257, RMSE 0.04625

## 7. Limitations

- All data are synthetic; results verify algorithms against their own simulated assumptions, not physical instruments.
- Calibration is fitted against the simulated reference, whose realised systematic error is non-zero; the error floor vs ground truth includes it.
- Uncertainty budgets are INCOMPLETE (stability, ambient sensitivity, model inadequacy, lag and self-heating are not quantified); coverage below 95 % in held-out conditions is the expected symptom.
- DataQualityAssessor is a pointwise screen: persistent faults (offset, gain, drift) are mostly invisible to it, and global MAD on multi-level runs is insensitive to small spikes.
- Drift p-values assume independent residuals; quantisation and the slow ambient sinusoid make them approximate.
- The existing CUSUM in analyze_temporal_drift uses k = 0.5 s and h = 4 s (in-control ARL about 170 samples), so it alarms on drift-free runs of 1200-1800 samples; its alarms are not used as evidence of drift.
- Full-run drift slopes are biased low because the run includes the drift-free pre-onset segment; post-onset slopes use the known onset (oracle segmentation) and measure estimator accuracy only.
- Repeatability in CURR_SWEEP_SELFHEAT is inflated by the thermal transient inside each dwell; it is not pure noise.
- Per-protocol-segment QA treats ramps and post-step lag transients as segments, so MAD flags legitimate dynamics there (high false-alarm rate for temperature).
- Within-run ingestion only: scenario CSVs hold several runs and must be split by experiment_id before calling the existing pipeline.
- Event detection counts any flag inside the event window; it does not require a correct fault class.
