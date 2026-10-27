# IMUCA — ML Fault Detection & CUSUM Tuning (Milestone 4)

> **Update (Milestone 5):** the follow-up hybrid detector and a fresh independent evaluation are documented in `docs/HYBRID_FAULT_DETECTION.md`.
>
> **Synthetic data only.** Every result here comes from the simulated suite in `data/synthetic/` (see `SYNTHETIC_DATA_SPECIFICATION.md`). No real-sensor accuracy is claimed. The ML detectors are research artefacts: they are **not** integrated into `app.py`, the R1–R5 decision engine or any calibration step.

| Item | Location |
|---|---|
| Causal features + integrity rules | `src/imuca/ml_features.py` |
| Detectors (GBT, Isolation Forest, conventional baseline) | `src/imuca/ml_fault_detection.py` |
| Detection metrics | `src/imuca/detection_metrics.py` |
| CUSUM tuning helpers | `src/imuca/cusum_tuning.py`; optional parameters added to `validation.analyze_temporal_drift` (defaults unchanged) |
| Experiment configuration | `config/ml_fault_detection_config.json` |
| Experiment runner | `scripts/run_ml_fault_detection.py` |
| Tests | `tests/test_ml_fault_detection.py` (18 tests) |
| Results of record | `results/ml_fault_detection_20261026_104358/` (`REPORT.md`, `metrics.json`, `models/`, `predictions/`, `plots/`, `config/`) |

---

## 1. Two tracks

| Track | Faults | Method |
|---|---|---|
| **Integrity** | missing samples, duplicate sequence, communication gap, invalid status, non-finite | Deterministic, causal rules: the record-integrity issue types of the existing `DataQualityAssessor` (`MISSING`, `NON_FINITE`, `DUPLICATE_SEQ`, `OUT_OF_ORDER`, `SEQUENCE_GAP`, `STATUS_ERROR`) |
| **Signal** | isolated spike, stuck signal, offset shift, gain change, gradual drift, abrupt change | GBT, Isolation Forest, conventional per-segment detector, evaluated on records that pass the integrity rules |

Records flagged by the integrity rules are removed from the signal stream before features are computed, and they are not scored by the signal detectors.

## 2. Causal features (`FEATURE_NAMES`, 20 features)

**Inputs read:** the measurand reading, `status`, `sequence_number`, `elapsed_ms` (and `experiment_id` for grouping). **Never read:** ground truth, reference readings, labels, derived errors, protocol columns. A test poisons all of those columns and checks that the features do not change.

**Noise scale** `s[k] = max(1.4826·median(|Δx| over k−60..k−1)/√2, 1.2533·mean(|Δx| over k−60..k−1)/√2, floor)`. This uses only *past* differences, so a fault cannot normalise itself. `floor = 0.25 × median raw scale` over fault-free **calibration-partition** records. `CausalFeatureBuilder.fit` refuses other partitions.

| Feature | Definition |
|---|---|
| `f_d1`, `f_abs_d1`, `f_d2` | first difference, its magnitude, second difference, divided by s |
| `f_dev_med5/15/60` | x[k] − median of the previous 5/15/60 samples, divided by s |
| `f_dev_mean60` | x[k] − mean of the previous 60 samples, divided by s |
| `f_std15`, `f_std60` | std over the last 15/60 samples (incl. k), divided by s |
| `f_max_abs_d1_5/30` | max \|Δx\| over the last 5/30 samples, divided by s |
| `f_level_shift_15_60` | mean(last 15) − mean(the 60 before those), divided by s |
| `f_slope60`, `f_slope300` | least-squares slope over the last 60/300 samples × window, divided by s |
| `f_identical_run` | log(1 + consecutive identical readings) |
| `f_frac_zero_d1_30`, `f_frac_zero_d1_300` | share of zero differences recently / in the past baseline |
| `f_noise_ratio_15_300` | recent mean \|Δx\| / past mean \|Δx\| |
| `f_since_large_change` | log(1 + samples since \|Δx\|/s > 6), capped at 600 |
| `f_position` | log(1 + position in the cleaned run stream) |

No raw level is used, so the models cannot memorise set-points. A test checks that changing samples after k leaves every feature at or before k unchanged.

## 3. Data splits and selection

- Unit of partitioning: the run (`experiment_id`). **Train** = calibration runs, **model and threshold selection** = validation runs, **final evaluation** = test runs (independent seed root, held-out conditions). Disjointness is asserted in code and tested.
- Training data for each measurand: all scenarios of that measurand, including fault-free sweeps, ramps and load steps, so that genuine operating transitions appear as negatives.
- **GBT** (`HistGradientBoostingClassifier`): target `is_signal_fault`. Sample weights give each fault class equal total weight and the negatives the same total. Grid: depth {3, 6} × learning rate {0.05, 0.1}, 300 iterations, L2 = 1.0.
- **Isolation Forest:** fitted on fault-free calibration records only. Grid: max_samples {256, 2048} × max_features {0.5, 1.0}, 300 trees. Missing early-window features are filled with calibration medians.
- **Threshold:** the smallest score threshold whose **validation** false-alarm rate is ≤ 0.5 %. **Selection:** highest validation macro event recall, tie-broken by validation F1.
- **Conventional baseline:** `DataQualityAssessor` per contiguous protocol segment, with the thresholds from `default_config.json`. It has no tunable threshold. It uses operator protocol boundaries and whole-segment (non-causal) MAD statistics, which the ML detectors do not get.
- Seeds: `random_seed = 20261027`. Training is deterministic; a test checks this, and three runs produced bit-identical scores.

Selected settings:

| Measurand | GBT | GBT threshold | Isolation Forest | IF threshold |
|---|---|---|---|---|
| voltage_V | depth 6, lr 0.05 | 0.899 | max_samples 2048, max_features 1.0 | 0.593 |
| current_mA | depth 3, lr 0.05 | 0.904 | max_samples 2048, max_features 1.0 | 0.574 |
| temperature_C | depth 3, lr 0.1 | 0.928 | max_samples 256, max_features 1.0 | 0.623 |

## 4. Evaluation protocol

- Record level: precision, recall, F1, false-alarm rate (FAR), missed-detection rate, confusion matrix, plus alarms per true class.
- Event level: a transient fault is detected if any alarm falls on its labelled records. A persistent fault (offset, gain, drift) counts only if an alarm falls within **60 samples of onset**. Delay = samples from onset to first alarm. Each class is reported with its **chance level** 1 − (1 − FAR)^window, because a long window can be "detected" by random alarms.
- False alarms by context (evaluation only; uses labels and protocol):
  - `steady`
  - `ramp`
  - `post_event_transient`: after a set-point change, true step or load step, or after a ramp ends. Windows: 5 samples for voltage, 135 for current (3τ thermal), 100 for temperature (5τ lag).
  - `post_fault_aftermath`: within 30 samples after a labelled fault.

## 5. Results (test partition, `results/ml_fault_detection_20261026_104358/`)

**Integrity track:** precision = recall = 1.000, FAR = 0 for all three measurands and all five classes. No signal-fault record is flagged by the integrity rules.

**Signal track: macro event recall (mean over the six classes) and record FAR:**

| Measurand | GBT | Isolation Forest | Conventional per-segment |
|---|---|---|---|
| voltage_V | **0.71** (FAR 1.27 %) | 0.24 (0.58 %) | 0.38 (0.38 %) |
| current_mA | 0.47 (0.39 %) | 0.45 (0.54 %) | **0.58** (1.21 %) |
| temperature_C | 0.39 (0.88 %) | 0.51 (0.53 %) | **0.56** (5.11 %) |

What the per-class tables in `REPORT.md` show:

- **Isolated spikes:** the conventional detector catches 14/14 for voltage and current and 12/14 for temperature. GBT catches 5–8/14 and misses spikes as large as 50–120σ. At the spike sample a causal detector cannot tell a spike from the first sample of a genuine step; the per-segment baseline avoids this by knowing the set-point boundaries and looking at the whole segment.
- **Abrupt changes:** the conventional detector catches 5/5 (voltage, current) and 3/4 (temperature); GBT 4/5, 2/5, 3/4.
- **Offset and gain changes:** GBT detects 2/2 of each for voltage within 0–1 samples, where the conventional detector finds 0/2. The conventional "2/2" temperature offset detections occur at a chance level of 0.96, so they carry no information.
- **Gradual drift** is essentially undetectable by every pointwise detector: at most 1/3 events, close to the chance level (0.21–0.54). Drift is handled by CUSUM (§6).
- **Stuck signals:** GBT detects 3/4 for voltage and temperature; every detector finds 0/4 for current.
- **Temperature transients:** the conventional detector's FAR is 34.9 % in post-ramp / post-step lag transients. Its per-segment MAD treats a settling or ramping segment as stationary. GBT has 1.5 % and Isolation Forest 1.0 % there, and all three are near 0 on the ramps themselves. On the fault-free `TEMP_PLATEAUS` test runs that is 269 false alarms per hour for the conventional detector, 28 for GBT and 0 for IF.
- **Fault aftermath** produces a large share of GBT's false alarms (9 % FAR in the 30 samples after voltage faults): the window features still "see" the fault.
- **Isolation Forest** has a 16 % FAR right after voltage set-point changes, because those steps are rare in its fault-free training data.

**Verdict.** No detector dominates. GBT is better on voltage, mostly through offset, gain and stuck faults, at roughly 3× the conventional false-alarm rate. The conventional detector is better on spikes and abrupt changes everywhere. Both ML models give far fewer false alarms during temperature lag transients. With 2–14 events per class and measurand, every recall figure carries wide uncertainty; for example, a 95 % interval for 2/2 spans about 0.16–1.0. The data do **not** support claiming that ML is generally better.

## 6. CUSUM investigation and tuning

**Root cause.** The existing detector uses k = 0.5σ, h = 4σ. Its two-sided in-control ARL is ≈ 169 samples (Siegmund), so on 1,200–1,800-sample runs false alarms are expected without any drift. Tests confirm this on simulated white noise.

**Change to existing code:** `analyze_temporal_drift` gained optional `cusum_k_sigma`, `cusum_h_sigma` and `cusum_sigma` arguments. Their defaults reproduce the previous behaviour exactly, which is tested.

**Tuning set** (calibration + validation runs only): 42 drift-free controls and 9 drift runs. The error series is the static-calibrated reading minus the reference, on integrity-clean steady/plateau records. σ and target come from the first 10 % of each run (causal). Constraints: Siegmund ARL₀ ≥ 18,000 samples (10 × longest run), zero false alarms and zero pre-onset alarms. Then maximise detections and minimise median delay. **Selected: k = 0.5, h = 15** (nominal ARL₀ ≈ 1e7).

**Why h had to be so large.** On the tuning controls, the baseline window underestimates σ by a median 4 % (max 18 %), and its mean is off by a median 0.08σ (max 0.29σ). A 0.3σ target error alone cuts the ARL₀ of (k = 0.5, h = 10) from ~7e4 to ~1e3 samples. Estimation error from short baselines, not the recursion itself, drives the false alarms.

**Independent test runs (39 controls, 9 drift runs):**

| Configuration | False alarms on controls | Pre-onset alarms | Drift runs detected | Median delay |
|---|---|---|---|---|
| Existing (k = 0.5, h = 4, whole-run residual σ) | 39 / 39 | 4 | 5 / 9 | 45 s |
| Tuned (k = 0.5, h = 15, baseline σ) | **1 / 39** | 1 | **8 / 9** | 102.5 s |

The nine drift-free controls of the previous benchmark went from 9/9 to 0/9 false alarms; only 3 of the 9 are independent test runs. The remaining test errors are one false alarm on `FD_TEMP_INVALID_STATUS-TST01` and one pre-onset alarm on `FD_CURR_GRADUAL_DRIFT-TST02`. Temperature detection is slow (206–311 s).

## 7. Methodology note: test results were viewed once

The models, thresholds, grids and selection rules were fixed before the test partition was scored, and they were not changed afterwards. After viewing the test results I added only evaluation diagnostics, each of which leaves predictions unchanged:

- the fault-aftermath context
- counting the end of a ramp as the start of a lag transient
- the spike-latency analysis
- the CUSUM baseline-estimation analysis

`results/ml_fault_detection_20261026_103714/` is the original one-shot evaluation and is kept as its record. `…_104358` is the final report with the added diagnostics. Their test scores and alarms are bit-identical (checked). An intermediate run with the same predictions was superseded and removed. Any modelling change suggested by these diagnostics must be validated on a **new test seed root**.

## 8. Limitations

- The fault generator and the detectors share the same simulated noise model, which flatters learned detectors.
- Event counts are small: 2 per persistent class and 4–14 per transient class per measurand in the test partition.
- Offset, gain and drift faults are fundamentally ambiguous from a single DUT signal.
- Stuck temperature signals are partly unobservable under coarse quantisation.
- GBT was trained to flag the spike sample itself, so it cannot use the confirm-one-sample-later pattern.
- The single 0.5 % validation FAR operating point does not hold exactly on test: the GBT voltage FAR is 1.27 %.
- The CUSUM study needs a reference instrument and a static calibration, so it is a lab-verification setting. Its selected h is on the grid boundary, and its detection delays for slow temperature drift are long.

## 9. Recommended next steps

1. Generate a fresh test partition (new `seed_roots.test`) before evaluating any modelling change.
2. Train GBT with a "confirm at k+1" target for transient faults, plus aftermath-aware negatives. Compare at matched validation FAR against the conventional detector.
3. Run a hybrid: conventional/rule detection for spikes and abrupt changes, GBT for offset, gain and stuck faults, tuned CUSUM for drift.
4. Use longer CUSUM baselines, or self-starting CUSUM / robust σ estimates, to reduce the h needed for zero false alarms.
