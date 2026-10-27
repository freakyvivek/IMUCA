# IMUCA — Milestone 6: Hybrid Detector Improvement Loop

> **Synthetic data only. Research component.** Nothing here is wired into `app.py`, the R1–R5 decision engine or calibration. No hardware integration and no ML-based calibration.

| Item | Location |
|---|---|
| Detector changes (opt-in; defaults reproduce Milestone 5) | `src/imuca/hybrid_detector.py` |
| Evaluation module | `src/imuca/hybrid_evaluation.py` |
| Fast CUSUM tuning (equivalent to the existing detector, tested) | `src/imuca/cusum_tuning.py` (`cusum_max_statistic`, `first_crossings`) |
| Idempotent dataset export | `src/imuca/synthetic_suite.py`, `scripts/generate_synthetic_suite.py` |
| Iteration harness (validate / freeze / final) | `scripts/run_hybrid_iteration.py`, `config/hybrid_iteration_config.json` |
| Post-hoc paired comparison | `scripts/posthoc_paired_comparison.py` |
| Development cycles | `results/hybrid_dev_cycles_20261026/` (`CYCLE_LOG.md`, one folder per cycle) |
| Frozen bundle | `results/hybrid_frozen_20261026_123033/` (frozen_settings SHA-256 `b0b38a79…`) |
| Final independent evaluation | `results/hybrid_final_20261026_123148/` (`REPORT.md`, `POSTHOC_PAIRED_COMPARISON.md`, `metrics.json`, `predictions/`, `plots/`) |
| Fresh final test suite | `config/synthetic_suite_v4_config.json` → `data/synthetic_v4/` (catalog `docs/DATASET_CATALOG_V4.md`) |
| Tests | `tests/test_generation_idempotency.py`, `tests/test_hybrid_lifecycle.py`, `tests/test_hybrid_evaluation.py` |

## 1. Protocol

1. **Development:** v3 calibration runs train the models, and v3 validation runs select every setting (CUSUM: calibration + validation). The harness drops the v3 test partition before any processing.
2. **Selection rules** (fixed in config):
   - CUSUM by false alarms → detections → delay → ARL₀.
   - Transient and persistent components by their own event F1, then a **joint refinement** of the top-6 × top-4 on full-hybrid event F1.
   - Lifecycle: least post-fault overhang among options within 0.01 F1 of the best.
   - Attribution: highest classification accuracy.
3. **Freeze:** `run_hybrid_iteration.py freeze` writes the settings, models, selection records and SHA-256 hashes of every relevant source file.
4. **Fresh suite:** v4 was generated *after* freezing. Its seed roots (61014027 / 71024027 / **83054027**) are disjoint from v2 and v3. It contains test runs only (85 scenarios, 166,248 records, 486 signal-fault events), uses new scenario and experiment IDs, and has the same device and fault distributions as v3.
5. **Single evaluation:** `final` aborts if any frozen source file changed, if the seeds overlap, if the data does not match its config, or if this (bundle, suite) pair was already evaluated (`evaluation_complete.json`). It was run once.

## 2. Workstreams: fixes and evidence

### WS1 — Alarm lifecycle and fault attribution

**Defects found:**
- Drift alarms were latched until the end of the run, including when spikes, stuck readings or abrupt changes triggered them.
- Drift alarms that started a few samples *before* the stuck or transient detector confirmed the fault were not explained away.
- Offset and gain steps were reported as "transient" because the segment detector fires first.

**Implemented:**
- `drift_lifecycle = hysteresis`: activation at CUSUM > h; persistence while the windowed mean error stays shifted; clearance by a z·σ/√W test or an absolute band `clear_sigma`; re-baseline after clearance.
- `explain_before`: drift alarms that start shortly before another episode are attributed to it.
- `attribution = confirmed`: provisional category at activation, final category after a level-shift test with a confirmation delay. It works on the raw signal or on the level-independent reference error (`attribution_source = error`).
- `HybridDetector.alarm_log()` gives one row per episode: activation and clearance sequence numbers, provisional and final category, contributing components.

**Effect (independent v4 test, M6 vs M5):**

| | Voltage | Current | Temperature |
|---|---|---|---|
| Post-fault alarm records / h | 0.6 vs 11.9 | 0 vs 0 | 41 vs 98 |
| Classification accuracy | **0.905** vs 0.847 | **0.813 vs 0.894 (regression)** | **0.728** vs 0.476 |
| Offsets correctly classified | 8/13 vs 0/11 | 6/15 vs 6/14 | 1/14 vs 2/14 |

The tolerance rule selected "latched" for the final drift lifecycle; the overhang reduction comes from explaining-away and re-baselining. Offset attribution remains weak for current and temperature.

### WS2 — Temperature transients

**Root cause:**
- The existing segment detector treats lag settling (after ramps and true steps) as outliers.
- The M5 temperature configuration avoided this by disabling transient detection in non-stationary phases, which lost spikes there.

**Implemented:**
- A causal second-difference ("curvature") detector for non-stationary phases. It uses a robust past-only scale and a guard after set-point changes.
- A transition window that marks set-point changes without an explicit settling phase as non-stationary.

**Effect (v4 test, temperature):**
- Spikes in non-stationary phases: **18/31** detected (M5 2/31; existing detector 12/31).
- Total spikes: 56/72 (M5 37/72).
- False alarms per hour in post-event transients: 5.4 (M5 9.9, existing detector 17.5); during settling: 3.1 (M5 3.1, existing 10.5).
- Ramps: 2.1 (M5 1.2) — slightly worse.
- **Voltage regression:** 20.5 false alarms/h during its short settling phases (5 alarms in 0.24 h; M5 0).

### WS3 — Thresholds and current drift

**MAD threshold:**
- The grid was extended to 2.5–20.
- Interior optima: 3.5 for voltage and temperature (2.5 and 3.0 are clearly worse), 12 for current (a 7–12 plateau, worse at 15–20).
- The earlier edge selection at 7.0 was an artefact of the limited grid.

**Current drift root causes:**
- The 135-sample exclusion left only 15–65 usable samples per segment, below `min_series`.
- The self-heating channel's error σ (1.18 mA) is four times the noise budget (0.30 mA).
- Reference uncertainty is a minor contributor (about 10 % of the variance).

**CUSUM tuning:**
- Expanded grid: windows, `min_baseline` (to 180), `min_series`, k (to 3) and h (to 30).
- The voltage `min_baseline` = 120 sits inside a 90–180 plateau. Temperature 10 ties with 5 and 15 because the baseline fraction dominates.
- Validation current drift detection: 3/6 → 6/6, with 0 false alarms.

**Effect (v4 test):**
- Drift detected: current **9/9** (M5 6/9, median delay 69 vs 140 s); temperature **8/9** (M5 6/9, but slower: 142 vs 60 s); voltage 9/9 (both; 55 vs 73 s).
- **Cost:** current spike recall fell to 57/72 (M5 65/72), and current false alarms rose (paired difference +0.81/h [+0.14, +1.61]).

### WS4 — Evaluation

New measures:
- event-level detection with tolerance windows
- fault-classification accuracy (Wilson CI)
- post-fault alarm overhang
- detection delay (median and p90)
- false alarms per hour (exact Poisson and run-bootstrap CIs)
- event F1 with run-bootstrap CI
- recall stratified by noise group, operating variant and fault magnitude
- false alarms by context (steady, ramp, settling, post-event)
- integrity track

Tests cover these, the lifecycle, attribution, curvature, cached-score equivalence, M5 reproduction, fast-CUSUM equivalence and the final-stage guards.

### WS5 — Reproducibility and preservation

**Defect:** a default v2 run rewrote the manifest timestamp, `fault_events.csv`, the malformed fixtures and the catalog even when nothing had changed. Windows CRLF line endings made byte comparison unreliable.

**Fix:**
- Every export file is written only when its content changes. JSON is compared semantically; text is compared newline-insensitively.
- The manifest keeps `manifest_written_utc` unless the substantive content changes, and per-scenario generation timestamps are preserved.
- Per-run `file_status` is returned, not stored.

**Verified:**
- Running the v2, v3 and v4 generators changes 0 files.
- A subprocess regression test confirms that `data/`, `docs/` and `results/` are untouched.
- v2 (50), v3 (94) and v4 (85) scenarios regenerate bit-identically.

The v2 `manifest_written_utc` had already been overwritten in Milestone 5 (now `2026-10-26T05:33:07Z`). The original value cannot be recovered, but the per-scenario generation timestamps were always preserved.

## 3. Final independent results (v4 test, scored once)

| Measurand | Detector | Event F1 [run-bootstrap 95 % CI] | FA / h [exact 95 % CI] | Missed / events | Median / p90 delay (samples, non-drift) | Drift delay (s) | Classification accuracy [95 % CI] |
|---|---|---|---|---|---|---|---|
| voltage | **Hybrid M6** | **0.847** [0.79, 0.90] | 2.3 [1.6, 3.2] | 15 / 162 | 0 / 7 | 55 | 0.905 [0.85, 0.94] |
| voltage | Hybrid M5 (frozen) | 0.815 [0.75, 0.87] | 1.8 [1.2, 2.6] | 25 / 162 | 0 / 7 | 73 | 0.847 [0.78, 0.90] |
| voltage | Tuned CUSUM alone | 0.922 [0.88, 0.95] | 0.1 [0.0, 0.4] | 38 / 162 | 0 | 55 | – (no categories; 293 post-fault alarm records / h) |
| current | **Hybrid M6** | **0.867** [0.82, 0.91] | 1.7 [1.1, 2.5] | 23 / 162 | 0 / 6 | 69 | 0.813 [0.74, 0.87] |
| current | Hybrid M5 (frozen) | 0.858 [0.80, 0.91] | 0.9 [0.5, 1.5] | 20 / 162 | 0 / 5.5 | 140.5 | 0.894 [0.83, 0.93] |
| temperature | **Hybrid M6** | **0.767** [0.71, 0.82] | 3.0 [2.2, 4.0] | 37 / 162 | 0 / 13 | 142.5 | 0.728 [0.64, 0.80] |
| temperature | Hybrid M5 (frozen) | 0.655 [0.58, 0.72] | 3.8 [2.9, 4.9] | 59 / 162 | 0 / 12.4 | 60 | 0.476 [0.38, 0.57] |
| temperature | GBT (all faults) | 0.706 [0.64, 0.77] | 3.7 [2.8, 4.7] | 53 / 162 | – | – | – |

The integrity track had 100 % precision and recall, with 0 false alarms, for all classes and measurands.

**Paired run-bootstrap difference M6 − M5 (post-hoc, same runs):**

| Measurand | F1 difference [95 % CI] | False alarms/h difference [95 % CI] |
|---|---|---|
| Voltage | +0.032 [−0.010, +0.078] | +0.47 [−0.33, +1.29] |
| Current | +0.009 [−0.054, +0.074] | **+0.81** [+0.14, +1.61] |
| Temperature | **+0.112** [+0.054, +0.172] | **−0.80** [−1.53, −0.06] |

**Conclusions:**
- **Temperature:** M6 is better than M5 on both event F1 and false alarms, and the paired interval excludes zero.
- **Voltage:** the gain is not established.
- **Current:** M6 is not better; it trades more false alarms for faster drift detection.
- **Overall:** the hybrid is **not** shown superior to the best single detector. The tuned CUSUM alone scores higher event F1 on voltage, but only because event F1 doesn't penalise its latched alarms, it gives no fault category and it needs a reference.

## 4. Remaining limitations and unmet goals

- **Attribution:** offset attribution remains poor for current (6/15) and temperature (1/14), and current classification regressed (0.813 vs 0.894).
- **Current:** false alarms increased and spike recall dropped (MAD 12 trade-off). Self-heating thermal transients still dominate the current-drift error budget.
- **Voltage settling:** false alarms during short voltage settling phases (20.5 /h over 0.24 h).
- **Temperature:**
  - Post-fault alarm records are still 41 /h on v4.
  - Drift detection is slower than M5 (142 vs 60 s).
  - The high-noise / slow-probe variant (TC) has the lowest recall (32/54).
- **Segment component latency:** it uses whole segments, so its decisions are final only at segment end.
- **Reference dependence:** the drift component and error-based attribution need a reference instrument (laboratory verification).
- **Data:** all data are synthetic; v4 shares v3's device and fault distributions, so this tests generalisation to new realisations, not to new devices.
- **Next modelling change:** v4 has now been seen, so any further modelling change needs a new suite (v5) with new seed roots.
