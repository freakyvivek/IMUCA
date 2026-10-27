# IMUCA — Hybrid Fault Detector (Milestone 5)

> **Update (Milestone 6):** the improvement loop and a fresh independent re-evaluation are documented in `docs/HYBRID_MILESTONE6.md`.
>
> **Synthetic data only. Research component.** The hybrid detector is not wired into `app.py`, the R1–R5 decision engine or any calibration step. No hardware integration and no ML-based calibration are part of this milestone. No real-sensor accuracy is claimed.

| Item | Location |
|---|---|
| Hybrid detector | `src/imuca/hybrid_detector.py` |
| Targeted GBT + training weights | `src/imuca/ml_fault_detection.py` (`TargetedGBTDetector`, `targeted_weights`) |
| Episode / event metrics, confidence intervals | `src/imuca/detection_metrics.py` |
| CUSUM helper (`min_baseline` option) | `src/imuca/cusum_tuning.py` |
| Fresh data suite (v3) | `config/synthetic_suite_v3_config.json` → `data/synthetic_v3/` (catalog: `docs/DATASET_CATALOG_V3.md`) |
| Experiment configuration | `config/hybrid_fault_detection_config.json` |
| Experiment runner | `scripts/run_hybrid_fault_detection.py` (`--selection-only` stops before any test record is processed) |
| Tests | `tests/test_hybrid_detector.py` (20 tests) |
| Results of record | `results/hybrid_fault_detection_20261026_113043/` (`REPORT.md`, `metrics.json`, `frozen_settings.json`, `models/`, `predictions/`, `plots/`, `config/`) |

---

## 1. Architecture

```
raw run ──► [0] integrity rules ──(flagged records leave the signal stream)──► integrity alarms
              │ clean records
              ├─► [1] transient: existing DataQualityAssessor per protocol segment ──► spikes, abrupt changes
              ├─► [2] persistent: targeted GBT on causal features ─────────────────► offset, gain
              ├─► [3] stuck: targeted GBT and/or identical-run rule ───────────────► stuck signal
              └─► [4] drift: existing CUSUM on (static-calibrated reading − reference),
                      excluding [1]–[3] alarms and protocol transitions, re-baselined after [2] ──► gradual drift
                                         │
                         combination: one alarm per record, precedence transient > stuck > persistent > drift;
                         drift alarms starting inside/≤10 records after another episode are "explained away";
                         consecutive alarms (gap ≤ 2) = one alarm episode
```

| Component | Method | Causality |
|---|---|---|
| Integrity | `DataQualityAssessor` record checks: missing, non-finite, duplicate/out-of-order, sequence/time gap, status | causal |
| Transient | Existing `DataQualityAssessor` (MAD outlier + rate of change) on each protocol segment. Validation chooses the segmentation (`setpoint_blocks`, `phase_blocks`, `phase_blocks_stationary_only`) and the modified-z threshold (3.5 default, 5, 7) | final at **segment end** (whole-segment MAD) |
| Persistent | `HistGradientBoostingClassifier` trained only for offset/gain onset windows (first 30 samples) and stuck records. Spike, abrupt and drift records are excluded from training (weight 0). Monotone constraint on `f_identical_run`. Threshold set at a validation false-alarm rate of 0.1 / 0.2 / 0.5 % | causal |
| Stuck | GBT alarm with ≥ 3 identical readings, **or** the identical-run rule: alarm when p0^L ≤ 10⁻⁴, where p0 is the past share of zero first differences (records k−329…k−30). Mode (`gbt` / `rule` / `gbt_or_rule`) chosen on validation | causal |
| Drift | Existing `analyze_temporal_drift` CUSUM with target and σ from a ≥ 30-sample baseline window. Validation chooses k, h, whole-run vs per-set-point re-baselining, and the post-transition exclusion window. Static calibration: `CalibrationEngine.select_best_model` on each device's calibration sweep | causal given [1]–[3]; requires a reference instrument |

`HybridDetector.annotate(run)` returns a copy of the run with `hybrid_integrity_alarm`, `hybrid_integrity_reasons`, `hybrid_signal_alarm` and `hybrid_category`. The input is not modified, which is tested.

**Use of protocol information.** Set-point index and protocol phase are used for segmentation and to mask transitions, as an operator schedule would provide them. They are never model features.

## 2. Investigations

**Stuck current faults (Milestone 4: 0/4 detected).** The signal was observable: stuck runs held 18–34 identical readings, while fault-free current records show `f_identical_run > 2.5` in 1 of 5,631 cases. The M4 GBT saw only 2 stuck events (47 records) in training and scored stuck records at a median of 0.16 against a 0.904 threshold. Fixes evaluated:

- more stuck training events (v3 has 3 device variants)
- a monotone constraint on `f_identical_run`
- a statistical identical-run rule

On the v3 test runs, stuck-current recall is 18/18 for the hybrid (rule mode), the rule alone and GBT(all). It is 16/18 for the targeted GBT and 6/18 for the existing segment detector.

**False alarms during temperature settling.** The existing detector computes one MAD per set-point block. That block contains the exponential lag transient, so the start of every plateau looks like an outlier. Splitting segments by protocol phase and suppressing the transient component in non-stationary phases (`phase_blocks_stationary_only`) removes these alarms. Test settling false alarms: existing detector **14.4 / h** [10.4, 19.3], hybrid **2.0 / h** [0.7, 4.3] over 3.07 h of fault-free settling. The cost: spikes during ramps and settling are no longer covered by the transient component, and the hybrid detects only 24/48 temperature spikes.

**Quantised MAD (found on validation).** For low-noise current channels (σ 0.15–0.2 mA, 0.1 mA quantisation) the MAD collapses to the quantisation step. The default modified-z threshold of 3.5 then corresponds to ≈ 2.6σ, giving about 1 % per-sample false alarms. Validation selected a threshold of 7.0 for current and temperature and 5.0 for voltage.

**CUSUM on multi-level runs (found on validation).** A linear static calibration leaves level-dependent error steps from INL or self-heating, which the CUSUM reads as drift. Polynomial calibration selection plus optional per-set-point re-baselining fixed voltage (0 false alarms, 6/6 tuning drift runs). Current remains weak: the best configuration has 1 false alarm and detects only 3/6 tuning drift runs.

## 3. Independent test protocol

1. **Fresh data.** `config/synthetic_suite_v3_config.json` uses new seed roots for every partition: calibration 31012027, validation 41022027, test 59033027. They are disjoint from v2's, which is tested. The suite has 94 scenarios, 245,665 records and 1,008 events, with these variations:
   - noise: 1.0–2.5 mV voltage, 0.15–0.3 mA current, 0.025–0.04 °C temperature
   - sensor lag τ = 10 / 20 / 35 s
   - transitions: level steps, ramps, bath transfers, random load steps with self-heating
   - fault magnitudes reaching down to about 5σ
   - mixed-fault and integrity-mix runs
   - long fault-free transition runs
   - complete runs stay within one partition
2. **Training** uses v3 calibration runs. **Selection** uses v3 validation runs only (CUSUM: calibration + validation). This covers GBT/IF configurations and thresholds, targeted-GBT configuration and FAR target, segment mode, MAD threshold, stuck mode, CUSUM k/h/mode/window, and transition windows.
3. **Freezing.** `frozen_settings.json` is written and hashed (SHA-256 `bcfb2b3bea0b1773…`) before any test record is passed to a detector. During development, `--selection-only` runs were used; they never process test runs. The design changes in §2 (quantised MAD, CUSUM calibration/re-baselining, transition mask) were all made from validation evidence before the single test evaluation.
4. **Single test evaluation.** The first full run (`results/hybrid_fault_detection_20261026_112521/`) scored the test runs and then crashed while plotting. It was re-run unchanged as `…_113043`. Its frozen settings and every test alarm are bit-identical (checked). No setting was changed after test results were seen. Afterwards I only changed report formatting and limitations text.

**Metrics.**
- **Sample level:** precision, recall, F1 and FAR over integrity-clean records.
- **Event level:**
  - Episode: consecutive alarms with gap ≤ 2. A true episode overlaps a fault-active record (+2 samples).
  - Timely detection windows: transient/stuck = event records + 2 samples; offset/gain = first 60 samples; drift = onset → end of run.
  - Event F1 = harmonic mean of the macro timely recall over fault classes and the episode precision.
  - False alarms per hour = false episodes / hours of evaluated operation.
- **Intervals:** Wilson (proportions), exact Poisson (rates), run-level bootstrap (event F1).

## 4. Results (v3 test runs; 108 signal events per measurand, 10.1–12.6 h of records)

| Measurand | Detector | Event F1 [95 % CI] | Macro timely recall | Episode precision | False alarms / h [95 % CI] | Missed events |
|---|---|---|---|---|---|---|
| voltage | **Hybrid** | **0.814** [0.74, 0.88] | 0.767 | 0.866 | 1.5 [0.8, 2.4] | 16 |
| voltage | Existing segment detector | 0.562 [0.46, 0.66] | 0.439 | 0.780 | 2.0 [1.2, 3.0] | 39 |
| voltage | GBT (all faults) | 0.650 [0.53, 0.75] | 0.481 | 1.000 | 0.0 [0.0, 0.4] | 56 |
| voltage | Tuned CUSUM | 0.750 [0.67, 0.82] | 0.645 | 0.897 | 0.6 [0.2, 1.3] | 45 |
| current | **Hybrid** | **0.852** [0.77, 0.93] | 0.803 | 0.908 | 1.1 [0.5, 1.9] | 12 |
| current | Existing segment detector | 0.543 [0.44, 0.64] | 0.578 | 0.511 | 8.3 [6.6, 10.3] | 29 |
| current | GBT (all faults) | 0.767 [0.68, 0.84] | 0.737 | 0.800 | 3.1 [2.1, 4.4] | 27 |
| current | Tuned CUSUM | 0.401 [0.26, 0.51] | 0.251 | 1.000 | 0.0 [0.0, 0.4] | 80 |
| temperature | Hybrid | 0.651 [0.54, 0.74] | 0.639 | 0.664 | 3.1 [2.2, 4.2] | 44 |
| temperature | Existing segment detector | 0.542 [0.44, 0.64] | 0.565 | 0.521 | 5.3 [4.1, 6.8] | 46 |
| temperature | **GBT (all faults)** | **0.675** [0.58, 0.76] | 0.655 | 0.697 | 3.7 [2.7, 5.0] | 38 |
| temperature | Isolation Forest | 0.641 [0.53, 0.74] | 0.520 | 0.835 | 1.1 [0.6, 1.9] | 45 |
| temperature | Tuned CUSUM | 0.632 [0.48, 0.76] | 0.471 | 0.960 | 0.1 [0.0, 0.4] | 58 |

The targeted GBT, stuck rule and Isolation Forest rows for every measurand, the per-fault-type tables, the context tables and the sample-level metrics are in `REPORT.md`.

**Integrity track:** 100 % precision and recall, 0 false alarms, for all classes and measurands. This uses the same deterministic rules for every detector.

**Verdict.**
- **Voltage and current:** the hybrid has the highest event F1 and fewer missed events. For current it also has fewer false alarms than any detector with comparable recall. Its bootstrap interval still overlaps the best single detector's (voltage: tuned CUSUM; current: GBT(all)), so **superiority is not established**.
- **Temperature:** the hybrid is not better than GBT(all) (0.651 vs 0.675, overlapping intervals). It does cut settling false alarms relative to the existing detector, but it misses half of the temperature spikes.

## 5. Settings selected on validation

| Measurand | Segment mode / MAD | Stuck mode | Targeted-GBT FAR target | CUSUM (mode, window, k, h) |
|---|---|---|---|---|
| voltage | `phase_blocks` / 5.0 | gbt | 0.2 % | segment, 5, 0.5, 15 |
| current | `setpoint_blocks` / 7.0 | rule | 0.1 % | segment, 135, 1.0, 10 |
| temperature | `phase_blocks_stationary_only` / 7.0 | gbt | 0.1 % | run, 120, 0.75, 10 |

## 6. Remaining limitations

- The data are synthetic, and the generator and detectors share noise models.
- **Event counts:** 6–48 per class and measurand, so per-class intervals are wide. Offset/gain detections in mixed runs can be triggered by co-occurring transients.
- **Transient component latency:** it uses whole segments, so its decisions are final only at segment end.
- **Drift component:** it needs a reference instrument and a static calibration. Current drift detection is weak (validation 3/6, test 4/6).
- **Latched drift alarms** inflate sample-level FAR, e.g. 11 % for temperature. Episode metrics are the intended operating measure.
- **Category attribution** is good for spikes, stuck and drift, but poor for offset and gain. The segment detector usually fires first and labels the step "transient".
- **Temperature spikes** during ramps and settling are mostly missed under the selected stationary-only mode.
- **Grid boundaries:** the selected MAD threshold of 7.0 lies on the grid's upper edge.

**Next steps:**
- A causal transient detector for non-stationary phases (e.g. second-difference MAD).
- Causal re-implementation of the segment component.
- A thermal grey-box term for self-heating channels.
- A new test seed root before evaluating any of these.
