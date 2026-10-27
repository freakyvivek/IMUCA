# IMUCA — ML Benchmark Plan (Specification Only)

> **Update (Milestone 4, 2026-10-26):** tasks C1 and C2 have been run as research experiments (GBT, Isolation Forest, tuned CUSUM); see `docs/ML_FAULT_DETECTION.md`. Nothing is integrated into the application.
>
> **Status:** specification for a future milestone. **No ML model has been trained or deployed**, and the Streamlit application and decision engine are unchanged. Nothing in the application presents an ML prediction as operational.
>
> Machine-readable version: `config/ml_benchmark_spec.json`. `tests/test_synthetic_suite.py::test_ml_spec_features_respect_role_policy` enforces its feature/role policy against the dataset column dictionaries.

Data: the synthetic suite v2 (`docs/SYNTHETIC_DATA_SPECIFICATION.md`, `docs/DATASET_CATALOG.md`). The conventional baselines and their current numbers come from `scripts/run_synthetic_benchmark.py` (`results/synthetic_benchmark_<timestamp>/`).

---

## 1. Leakage policy

### 1.1 Column roles

Every dataset column has a role in its metadata. Features may use only:

| Role | Allowed as feature? | Notes |
|---|---|---|
| `observation` | Yes | DUT reading, shunt voltage, status, ambient sensor |
| `time` | Yes | `elapsed_ms`, `sequence_number`; causal use only |
| `quality_flag` | Yes | `dq_flags` is computed from observable fields only |
| `reference_observation` | **Only** in tasks that declare reference access, causally and on the documented schedule | e.g. one reference checkpoint every 300 s |
| `ground_truth`, `derived_error`, `label` | **No** | Targets and evaluation only |
| `protocol` | **No** | In simulation the planned set-point equals the true value, so `setpoint_index` / `operating_condition_id` leak truth. They are used only to group results |
| `identifier`, `partition`, `provenance` | **No** | `experiment_id` / `device_id` are grouping keys; per-device models are allowed |

No task uses the same column as both input and target. Labels never appear as inputs.

### 1.2 Splits

1. The unit of partitioning is the run (`experiment_id`). A run's records never appear in two partitions.
2. **Calibration** partition: fit models, scalers, encoders, thresholds and feature statistics.
3. **Validation** partition: hyper-parameters and model selection.
4. **Test** partition: evaluated once per frozen model. It comes from an independent seed root and holds the held-out operating conditions. Test results must not feed back into design choices; any later change requires new test runs (a new test seed root).
5. Random splitting within a run is forbidden: dwell, lag and thermal state make adjacent samples correlated.
6. Window features are causal (only samples with `elapsed_ms ≤ t`). No centred windows, whole-run normalisation or future-looking smoothing.
7. Results are reported separately for in-distribution (`grid_A`, same ramp rate) and held-out conditions (`grid_B_interleaved`, `extrapolation_above_cal_range`, `_ambient30C`, `_descending`, `ramp_0p08_heldout`).

### 1.3 Reference versus truth

Training targets for residual correction use the **reference** reading (`reference_* − observation`), because that is what a real laboratory provides. Ground truth is used only for evaluation, so that the floor set by the reference's own realised error is visible. Where a task's target exists only in simulation (`true_drift_component`), the plan says so.

---

## 2. Tasks

### Regression

| Task | Data | Target (training) | Evaluation | Inputs | Baselines |
|---|---|---|---|---|---|
| **R1** Voltage residual correction | `VOLT_SWEEP_LINEAR`, `VOLT_SWEEP_NONLINEAR` | `reference_voltage_V − voltage_V` | vs reference and vs `true_voltage_V`, per condition | `voltage_V`, `environmental_temperature_C` | identity; `CalibrationEngine.fit_linear`; `select_best_model` (F-test + BIC, degree ≤ 3) |
| **R2** Current residual correction | `CURR_SWEEP_AMBIENT`, `CURR_SWEEP_SELFHEAT`, `CURR_LOAD_STEPS` | `reference_current_mA − current_mA` | as R1; plus the first 3τ after each load step | `current_mA`, `shunt_voltage_mV`, ambient; causal EWM of I² (τ = 45 s, 180 s); time since last level change | identity; linear; F-test/BIC polynomial |
| **R3** Temperature drift prediction | `TEMP_DRIFT`, `FD_TEMP_GRADUAL_DRIFT`, `FD_TEMP_NONE` | `true_drift_component(t + h)`, h ∈ {0, 300, 600} s (**simulation-only target**) | MAE/RMSE per horizon, drift-rate error, interval calibration | `temperature_C`, ambient, time; most recent 300 s checkpoint error (obs − ref); slope of past checkpoint errors | `analyze_temporal_drift` slope extrapolation on checkpoint errors; last checkpoint carried forward |

### Classification / anomaly detection

| Task | Data | Target | Inputs | Baselines |
|---|---|---|---|---|
| **C1** Fault detection (record + event level) | `FD_*`, `*_INTEGRITY` | `is_injected_fault`; event ids for event-level metrics | Observations, status, sequence/time deltas, `dq_flags`, causal rolling median deviation, identical-reading run length. Track **C1a** signal-only; track **C1b** adds the same-record reference value (reported separately) | `DataQualityAssessor` whole-run and per protocol segment |
| **C2** Drift detection (online, run level) | `*_DRIFT`, `FD_*_GRADUAL_DRIFT` vs `FD_*_NONE` and control runs | onset time of the `gradual_drift` event; runs without one are negatives | Observations + 300 s reference checkpoints | `analyze_temporal_drift` (regression significance, CUSUM) |
| **C3** Abnormal-measurement identification (multi-class) | `FD_*`, `*_INTEGRITY` | `label_fault_type` | As C1a | Rule mapping of `DataQualityAssessor` flags to classes |

---

## 3. Metrics

- **Regression:** bias, MAE, RMSE and max |error|, all against the reference **and** against ground truth, per operating condition. Where a model gives prediction intervals, their empirical coverage against ground truth. Error metrics are not uncertainty: an ML correction must come with its own uncertainty evaluation (e.g. GP predictive variance or conformal intervals calibrated on the validation partition) before it could enter a GUM budget.
- **Detection:** precision, recall, F1, false-alarm rate, missed-detection rate, event-level recall, detection delay, false alarms per hour on fault-free runs, per-class recall, and false alarms within 3 samples of a genuine process event.
- **Drift:** run-level detection rate, false-alarm rate on controls, detection delay (s), drift-rate estimation error.

## 4. Candidate models (to be compared, not yet trained)

Kept deliberately small, given the data volume (hundreds to a few thousand records per task and partition):

- R1/R2: ridge regression on polynomial and load-history features; Gaussian-process regression (gives predictive uncertainty); shallow gradient-boosted trees with a monotone constraint on the reading. For R2, also a physics-informed first-order thermal grey-box model as a strong structured baseline.
- R3/C2: local-linear-trend Kalman filter / state-space model; Bayesian online change-point detection; Page–Hinkley or a CUSUM with properly tuned (k, h) on checkpoint errors.
- C1/C3: gradient-boosted trees on causal window features; isolation forest or a one-class model trained on fault-free calibration runs only; a hierarchical scheme (observable record faults by rule, signal faults by a learned model). A temporal CNN only if validation shows a clear gain over trees.

## 5. What the conventional baseline already shows (targets to beat)

These figures come from `results/synthetic_benchmark_20261026_100450/BENCHMARK_SUMMARY.md` (test partition unless stated):

- **Calibration.** Linear/polynomial calibration reduces validation RMSE vs reference by 86–98 %. F-test/BIC correctly adopts a quadratic model only for `VOLT_SWEEP_NONLINEAR` and `CURR_SWEEP_SELFHEAT`. Under held-out conditions, static calibration degrades and the incomplete GUM budget under-covers: `CURR_SWEEP_AMBIENT` at 30 °C ambient reaches 1.02 mA RMSE with 30 % coverage of U, and the descending self-heating sweep 1.41 mA with 70 % coverage. These are the main headroom for R2.
- **Dynamics.** For `TEMP_RAMPS`, static calibration leaves about ±1.5 °C lag bias on the 0.08 °C/s ramps (expected ≈ τ·rate = 1.6 °C). For `CURR_LOAD_STEPS`, the error is larger within 3τ after a load step. This is headroom for history-aware models.
- **Drift.** Regression significance separates drift runs from controls 6/6 vs 0/9. The existing CUSUM alarms on all 9 controls, because h = 4σ gives an in-control ARL of about 170 samples. This is the baseline for C2.
- **Faults.** Record-level faults (missing, non-finite, duplicate, gap, invalid status) are detected 100 % by the existing assessor. Applied to whole multi-level runs, it misses all isolated spikes and stuck signals, and nearly all offset, gain, drift and abrupt faults. Applying it per protocol segment recovers spikes and abrupt changes for voltage and current, but raises false alarms on temperature ramps and lag transients. This is the baseline for C1/C3. The ambiguous classes are expected to stay hard without reference access (track C1b).

## 6. Reproducibility requirements

1. Record the suite manifest SHA-256 and per-CSV checksums used (`data/synthetic/metadata/suite_manifest.json`).
2. Fix and record all model seeds; report mean ± spread over at least 5 seeds.
3. Record library versions (numpy, pandas, scipy, scikit-learn if introduced).
4. Feature definitions live in version-controlled code and are generated from raw CSVs only.
5. Report the conventional baseline of `scripts/run_synthetic_benchmark.py` next to every ML result, on the same partitions.
6. Results go to new timestamped directories under `results/`; earlier results are never overwritten.

## 7. Out of scope for this milestone

Training, hyper-parameter search, model deployment, any change to `app.py` or the rule engine (R1–R5), hardware/firmware/serial acquisition and cloud services. Any future ML output shown in the application must be labelled experimental and kept apart from the transparent rule-based decision.
