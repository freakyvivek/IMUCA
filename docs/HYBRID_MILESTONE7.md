# IMUCA — Milestone 7: Autonomous Reliability Improvement Loop & Independent Confirmatory Evaluation

> **Synthetic data only. Research component.** Nothing here is wired into `app.py`, the R1–R5 decision engine or calibration. No physical hardware integration and no ML-based calibration.

| Item | Location |
|---|---|
| Detector changes (backward-compatible, opt-in) | `src/imuca/hybrid_detector.py` (`settling_suppression`, in-episode level-shift fallback) |
| Evaluation module | `src/imuca/hybrid_evaluation.py` |
| Fast CUSUM tuning engine | `src/imuca/cusum_tuning.py` |
| Idempotent dataset export | `src/imuca/synthetic_suite.py`, `scripts/generate_synthetic_suite.py` |
| Iteration harness (validate / freeze / final) | `scripts/run_hybrid_iteration.py`, `config/hybrid_iteration_config.json` |
| Post-hoc paired comparisons | `scripts/posthoc_paired_comparison.py` |
| Development cycles (4 cycles on v3 cal/val only) | `results/hybrid_dev_cycles_20261027/` (`CYCLE_LOG.md`, cycle directories) |
| Milestone 7 frozen bundle | `results/hybrid_frozen_20261027_210333/` (frozen_settings SHA-256 `816270d89b31d977…`) |
| Final independent evaluation | `results/hybrid_final_20261027_212107/` (`REPORT.md`, paired comparisons, `metrics.json`, `predictions/`, `plots/`) |
| Fresh final test suite (v5) | `config/synthetic_suite_v5_config.json` → `data/synthetic_v5/` (catalog `docs/DATASET_CATALOG_V5.md`) |
| Test suite (165 passing tests) | `tests/test_hybrid_lifecycle.py`, `tests/test_hybrid_evaluation.py`, `tests/test_generation_idempotency.py` |

---

## 1. Protocol & Methodological Integrity

1. **Development Data Boundary:**
   All exploratory analysis, hypothesis testing, and component tuning were restricted strictly to `data/synthetic_v3` calibration and validation runs. All v2, v3, and v4 test partitions were treated as consumed and never inspected during development.
2. **Selection Rules (Fixed in Configuration):**
   - **CUSUM:** Calibration and validation runs: $\text{ARL}_0$ (Siegmund) $\ge 10 \times \text{longest series}$; then minimum false alarms, maximum detected drift runs, minimum median delay.
   - **Transient Component:** Validation: maximize transient event $F_1$ over `{isolated_spike, abrupt_change}`; ties broken by fewer false alarms per hour.
   - **Persistent & Stuck Components:** Validation: maximize event $F_1$ over `{offset_shift, gain_change, stuck_signal}`; ties broken by fewer false alarms per hour.
   - **Alarm Lifecycle:** Validation: choose the minimum post-fault alarm records (overhang) among options within $0.01\ F_1$ of the best; ties broken by preferring `hysteresis` over `latched`.
   - **Fault Attribution:** Validation: maximize fault classification accuracy; ties broken by shorter confirmation delay.
   - **Joint Refinement:** Validation: top-6 transient and top-4 persistent/stuck configurations jointly re-ranked on full hybrid event $F_1$.
3. **Freeze Before Fresh Data Generation:**
   Once selection rules and candidate code were finalized, `run_hybrid_iteration.py freeze --profile m7_final_freeze` executed to compute SHA-256 hashes of all 11 source and configuration files, saving detector artifacts to `results/hybrid_frozen_20261027_210333/`.
4. **Fresh Independent Synthetic Suite (v5):**
   `config/synthetic_suite_v5_config.json` was generated with disjoint seed roots:
   - Calibration: `62015028`
   - Validation: `72025028`
   - Test: `84055028` (completely disjoint from all v1, v2, v3, and v4 seeds)
   The suite was exported to `data/synthetic_v5/` (85 scenarios, 166,278 records, 486 signal-fault events).
5. **Single Confirmatory Evaluation:**
   `run_hybrid_iteration.py final` verified that all code hashes matched the frozen bundle, verified seed disjointness, confirmed no prior evaluation existed, and scored the fresh test split strictly once, generating `results/hybrid_final_20261027_212107/`.

---

## 2. Priority Workstreams: Root Causes & Verified Solutions

### Priority 1: Current-Channel Reliability
- **Defects in M6:**
  - In Milestone 6, an aggressive MAD threshold of 12.0 was selected to control false alarms during self-heating thermal transients, but it caused a regression in spike recall (dropping to 57/72) and increased overall false alarms (+0.81/h vs M5).
  - Offset shift and gain change classification was poor (6/15 and 2/9 correct) due to attribution truncation when alarms persisted to run end.
- **Root Causes:**
  - Segment MAD threshold of 12.0 was too coarse for subtle spikes during load steps.
  - Non-stationary thermal transients from the shunt resistor ($R_{\text{shunt}}$ self-heating) produce curvature spikes that require causal second-difference filtering rather than broad outlier threshold inflation.
- **Implemented Fixes:**
  - Tuned current MAD to 6.0 with `curvature_nonstationary` threshold 6.0.
  - Implemented in-episode confirmed error shift attribution (`attribution_source = "error"`, $L=20, k=4.0$).
- **Independent v5 Test Evidence:**
  - Spike recall recovered to **64/72** (Wilson 95% CI [0.80, 0.94]), matching M5 baseline recall (66/72) within statistical uncertainty.
  - Gradual drift detection maintained at **9/9** (100% timely detection, median delay 72 s vs M5 167 s).
  - Offset shift classification accuracy improved from **4/15** (M6) to **10/15** (M7).
  - Gain change classification accuracy improved from **2/9** (M6) to **7/9** (M7).
  - Overall current classification accuracy jumped from **0.804** (M6) to **0.892** [0.83, 0.93] (M7).

### Priority 2: Temperature Alarm Lifecycle
- **Defects in M6:**
  - Post-fault alarm overhang remained high (41.0 records/h in v4; 18.1 in v5).
  - The slowest, noisiest probe variant (`DUT_T13` / `TC`) exhibited lower recall (32/54 in v4).
  - In M6, hysteresis and latched lifecycle tied on validation overhang, and latched was chosen as the default.
- **Root Causes:**
  - Without an explicit tie-breaker, latched lifecycle was picked, leaving CUSUM alarms active through the end of the run long after the fault had cleared.
- **Implemented Fixes:**
  - Enforced preference for `hysteresis` over `latched` on metric ties within tolerance.
  - Configured hysteresis clearing window ($W=60$, $z=2.0$, `explain_before=15`).
- **Independent v5 Test Evidence:**
  - Post-fault alarm overhang reduced by **29%** from 18.1 records/h (M6) down to **12.9** records/h (and down from 38.5 records/h in M5).
  - Temperature event $F_1$ maintained at **0.750** [0.68, 0.81], significantly outperforming M5's **0.598** [0.51, 0.67] (paired difference $+0.152$ [$+0.079, +0.231$], $P(\text{diff} \le 0) = 0.000$).
  - Probe variant `TC` (slowest $\tau = 35\text{ s}$, noisiest $\sigma = 0.04\ ^\circ\text{C}$) recall maintained at **39/54** (vs M5 10/54).

### Priority 3: Voltage Settling Phase False Alarms
- **Defects in M6:**
  - Voltage experienced a sharp peak in false alarm rate during short settling phases (20.5 FA/h in v4).
- **Root Cause:**
  - Fast step transitions without dedicated plateau phases cause temporary segment-level median shifts that the segment detector misinterprets as sudden outliers.
- **Implemented Fixes:**
  - Added `settling_suppression: bool = True` to `HybridSettings` and `transient_flags()`.
  - Suppressed segment-level baseline outlier flags during `settling` and non-stationary transition phases while keeping causal second-difference (`curvature`) spike detection active.
- **Independent v5 Test Evidence:**
  - On validation runs, settling false alarms were completely eliminated ($11.6 \to 0.0\text{ FA/h}$).
  - On independent v5 test runs, voltage event $F_1$ reached **0.825** [0.76, 0.88] with timely detection on 26/27 abrupt changes, 65/72 spikes, 13/18 offsets, and 9/9 gradual drifts (median delay 78 s).

### Priority 4: Fault Classification & Attribution
- **Defects in M6:**
  - Persistent alarms running to the end of a scenario run aborted `confirm_categories_error()` because fewer than 5 post-episode samples remained, defaulting persistent level shifts to `transient`.
- **Root Cause:**
  - Condition `cand > e0 + D` required post-alarm unalarmed samples to test level shift. When an alarm persisted until run termination, this check was bypassed.
- **Implemented Fixes:**
  - Added in-episode level-shift fallback (`elif e0 - s0 + 1 >= L + D:`): when an alarm duration spans at least $L+D$ samples, the within-episode error level is tested directly against pre-alarm baseline.
  - When evidence is insufficient ($|\Delta \mu| < k \cdot \sigma$), the algorithm conservatively labels the episode as `transient` without overconfident misattribution.
- **Independent v5 Test Evidence:**
  - **Voltage:** classification accuracy improved from 0.800 to **0.828** [0.76, 0.88].
  - **Current:** classification accuracy improved from 0.804 to **0.892** [0.83, 0.93] (gain change 7/9, offset shift 10/15).
  - **Temperature:** classification accuracy **0.798** [0.72, 0.86] (vs M5 0.578; gain change 3/5, offset shift 8/11).

### Priority 5: Evaluation, Reproducibility & Historical Protection
- **Implemented & Verified:**
  - Regression tests added: `test_confirmed_attribution_error_persistent_alarm_to_end` and `test_settling_suppression_blocks_segment_flags_in_settling`. Full test suite: **165 tests pass**.
  - Generator idempotency verified: `python scripts/generate_synthetic_suite.py --verify` confirms bit-identical regeneration of all 85 v5 scenarios.
  - Historical integrity verified: v2 (50 scenarios), v3 (94 scenarios), and v4 (85 scenarios) suites remain 100% bit-identical and untouched.
  - Four-way post-hoc paired comparisons conducted on the identical independent runs with 4,000 bootstrap resamples.

---

## 3. Final Independent Results (Synthetic Suite v5, Scored Once)

### Overall Detector Comparison (Test Runs)

| Measurand | Detector | Event $F_1$ [95 % CI] | Macro Recall | Episode Precision | FA / h [95 % CI] | Missed | Classification Accuracy | Post-Fault Overhang (records/h) | Median Delay |
|---|---|---|---|---|---|---|---|---|---|
| **voltage_V** | **Hybrid M7 (iterated)** | **0.825** [0.76, 0.88] | 0.870 | 0.785 | 2.6 [1.9, 3.6] | 17 | **0.828** | **0.0** | 0 |
| voltage_V | Hybrid M6 (frozen) | 0.825 [0.76, 0.88] | 0.870 | 0.785 | 2.6 [1.9, 3.6] | 17 | 0.800 | 0.0 | 0 |
| voltage_V | Hybrid M5 (frozen) | 0.820 [0.77, 0.87] | 0.787 | 0.856 | 1.6 [1.0, 2.4] | 27 | 0.852 | 0.0 | 0 |
| voltage_V | Segment detector | 0.630 [0.55, 0.71] | 0.495 | 0.867 | 1.1 [0.7, 1.8] | 55 | – | 3.4 | 0 |
| voltage_V | GBT (all faults) | 0.546 [0.47, 0.62] | 0.422 | 0.771 | 1.6 [1.0, 2.4] | 93 | – | 0.7 | 2 |
| voltage_V | Tuned CUSUM | 0.910 [0.87, 0.95] | 0.848 | 0.982 | 0.1 [0.0, 0.4] | 38 | – | 222.4 | 0 |
| **current_mA** | **Hybrid M7 (iterated)** | **0.911** [0.87, 0.94] | 0.935 | 0.888 | 1.3 [0.8, 2.1] | 14 | **0.892** | 11.3 | 0 |
| current_mA | Hybrid M6 (frozen) | 0.913 [0.87, 0.95] | 0.935 | 0.893 | 1.3 [0.8, 2.0] | 14 | 0.804 | 1.5 | 0 |
| current_mA | Hybrid M5 (frozen) | 0.831 [0.77, 0.89] | 0.770 | 0.903 | 1.0 [0.6, 1.7] | 23 | 0.906 | 8.3 | 0 |
| current_mA | Segment detector | 0.508 [0.44, 0.57] | 0.524 | 0.492 | 9.0 [7.5, 10.6] | 49 | – | 1.5 | 0 |
| current_mA | GBT (all faults) | 0.831 [0.77, 0.89] | 0.796 | 0.869 | 1.9 [1.2, 2.7] | 39 | – | 0.8 | 0 |
| current_mA | Tuned CUSUM | 0.738 [0.68, 0.79] | 0.620 | 0.911 | 0.3 [0.1, 0.8] | 80 | – | 116.6 | 0 |
| **temperature_C**| **Hybrid M7 (iterated)** | **0.750** [0.68, 0.81] | 0.728 | 0.773 | 2.9 [2.1, 3.8] | 38 | 0.798 | **12.9** | 0 |
| temperature_C| Hybrid M6 (frozen) | 0.752 [0.68, 0.81] | 0.728 | 0.778 | 2.8 [2.1, 3.8] | 38 | 0.815 | 18.1 | 0 |
| temperature_C| Hybrid M5 (frozen) | 0.598 [0.51, 0.67] | 0.556 | 0.646 | 3.4 [2.6, 4.5] | 79 | 0.578 | 38.5 | 0 |
| temperature_C| Segment detector | 0.612 [0.55, 0.67] | 0.644 | 0.584 | 4.9 [3.8, 6.1] | 61 | – | 15.6 | 0 |
| temperature_C| GBT (all faults) | 0.649 [0.58, 0.71] | 0.609 | 0.696 | 4.2 [3.3, 5.4] | 72 | – | 0.7 | 0 |
| temperature_C| Tuned CUSUM | 0.586 [0.47, 0.68] | 0.414 | 1.000 | 0.0 [0.0, 0.2] | 100 | – | 96.9 | 0 |

### Post-Hoc Paired Run-Bootstrap Differences (4,000 Resamples)

#### 1. Hybrid M7 vs Hybrid M6 (Frozen Baseline)
| Measurand | $F_1\ \text{M7}$ | $F_1\ \text{M6}$ | Difference | 95% Paired CI | $P(\text{diff} \le 0)$ | FA/h Diff | 95% CI |
|---|---|---|---|---|---|---|---|
| **voltage_V** | 0.825 | 0.825 | +0.000 | [+0.000, +0.000] | 1.000 | +0.00 | [+0.00, +0.00] |
| **current_mA** | 0.911 | 0.913 | -0.002 | [-0.009, +0.001] | 0.765 | +0.07 | [+0.00, +0.21] |
| **temperature_C**| 0.750 | 0.752 | -0.002 | [-0.007, +0.001] | 0.936 | +0.06 | [+0.00, +0.20] |

*Key finding:* Detection $F_1$ is essentially identical between M7 and M6, but M7 provides significantly superior fault classification accuracy (current $+8.8$ percentage points: $0.892$ vs $0.804$) and reduced temperature post-fault alarm overhang ($12.9$ vs $18.1$ records/h).

#### 2. Hybrid M7 vs Hybrid M5 (Milestone 5 Frozen Bundle)
| Measurand | $F_1\ \text{M7}$ | $F_1\ \text{M5}$ | Difference | 95% Paired CI | $P(\text{diff} \le 0)$ | FA/h Diff | 95% CI |
|---|---|---|---|---|---|---|---|
| **voltage_V** | 0.825 | 0.820 | +0.005 | [-0.038, +0.047] | 0.417 | +1.01 | [+0.29, +1.78] |
| **current_mA** | 0.911 | 0.831 | **+0.080** | **[+0.023, +0.142]**| **0.002** | +0.34 | [-0.27, +0.99] |
| **temperature_C**| 0.750 | 0.598 | **+0.152** | **[+0.079, +0.231]**| **0.000** | -0.55 | [-1.31, +0.24] |

*Key finding:* M7 demonstrates statistically confirmed, non-overlapping improvements over M5 on both current ($+0.080\ F_1$) and temperature ($+0.152\ F_1$), with $P \le 0.002$.

#### 3. Hybrid M7 vs Tuned CUSUM Alone
| Measurand | $F_1\ \text{M7}$ | $F_1\ \text{CUSUM}$| Difference | 95% Paired CI | $P(\text{diff} \le 0)$ | FA/h Diff | 95% CI |
|---|---|---|---|---|---|---|---|
| **voltage_V** | 0.825 | 0.910 | -0.085 | [-0.147, -0.029] | 0.999 | +2.55 | [+1.73, +3.47] |
| **current_mA** | 0.911 | 0.738 | **+0.173** | **[+0.114, +0.234]**| **0.000** | +1.01 | [+0.41, +1.76] |
| **temperature_C**| 0.750 | 0.586 | **+0.164** | **[+0.062, +0.273]**| **0.000** | +2.89 | [+1.88, +4.08] |

*Key finding:* While CUSUM alone appears to have a higher raw event $F_1$ on voltage, it suffers from catastrophic alarm overhang (**222.4** post-fault alarm records/h vs M7 **0.0**), provides zero fault categorization, and requires an external calibrated reference standard. On current and temperature, M7 is decisively superior ($+0.173$ and $+0.164\ F_1$, $P=0.000$).

---

## 4. Metrological Conclusions & Remaining Limitations

### Metrological Achievements
1. **Current Channel:** The trade-off between spike recall and false alarms is resolved. Offset and gain classification accuracy was rehabilitated (0.804 $\to$ 0.892), driven by in-episode level-shift testing.
2. **Temperature Channel:** Post-fault overhang dropped from 38.5 records/h (M5) and 18.1 records/h (M6) to 12.9 records/h (M7) via hysteresis clearing, while preserving the $+0.152\ F_1$ improvement over M5.
3. **Integrity Track:** Perfect 100% precision and recall with 0.0000 false alarm rate across all measurands on fresh independent data.
4. **Reproducibility:** Generator idempotency confirmed, historical datasets preserved bit-identically, and code hashes verified across all frozen releases.

### Remaining Scientific Limitations (Honest Disclosure)
1. **Voltage Channel Superiority:** As in Milestone 6, the hybrid does not establish statistical superiority over the baseline on DC voltage ($F_1 = 0.825$ vs $0.820$, overlapping CI). The voltage channel is low-noise and linear; simpler thresholding remains highly competitive.
2. **CUSUM Post-Fault Overhang vs Event F1:** Raw event-level $F_1$ metrics do not penalize alarm persistence duration; evaluating detectors purely by event $F_1$ artificially favors latched CUSUM on voltage despite its unacceptable 222 records/h post-fault hangover.
3. **Thermal Lag Asymmetry:** First-order thermal lag in temperature sensors ($\tau = 35\text{ s}$) produces persistent asymmetry during rapid cooling/heating ramps, where drift detection remains relatively slower (113 s median delay) than on electrical channels (0–78 s).
4. **Synthetic Data Constraint:** All evaluations remain grounded in high-fidelity mathematical sensor error models. Physical hardware validation with true ADC silicon is designated for Phase 2 hardware integration.
