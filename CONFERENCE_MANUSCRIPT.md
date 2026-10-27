# Evaluating Multi-Track Hybrid Fault Detection and Uncertainty Lifecycle Management in Precision DC and Thermal Instrumentation: An Empirical Study on Synthetic Benchmark Suites

**Conference Submission Draft — Target: IEEE International Instrumentation and Measurement Technology Conference (I2MTC) / IEEE AUTOTESTCON**

*Author List Omitted for Blind Peer Review*

---

### Abstract
Precision instrumentation systems deployed in industrial testing, semiconductor characterization, and metrology calibration benches require simultaneous quantification of measurement uncertainty under international standards (JCGM 100:2008 / GUM) and rapid, automated detection of instrument degradation (drifts, offset shifts, gain changes, stuck readings, and intermittent spikes). However, existing statistical and machine-learning detectors face severe operational trade-offs: recursive sequential detectors like CUSUM suffer from persistent alarm overhang after faults resolve, classical segment detectors trigger excessive false alarms during legitimate physical settling transients, and single-model anomaly detectors fail to categorize fault modes. 

This paper presents an audited, reproducible evaluation framework and a multi-track hybrid fault detector designed for multichannel precision DC voltage, DC current (with resistive shunt self-heating), and delayed temperature measurements. The architecture integrates an $O(1)$ deterministic data-integrity track, a causal second-difference curvature filter, causal rolling-feature gradient-boosted decision trees, an empirical stuck-state rule, and an optimized tabular CUSUM engine equipped with an adaptive hysteresis clearance and level-shift attribution lifecycle. 

In a pre-frozen, single-execution independent evaluation across an 85-scenario synthetic test suite (Suite v5, comprising 166,278 observations and 486 injected signal-fault events), the hybrid detector demonstrates channel-dependent performance:
1. **DC Current:** Relative to the baseline hybrid (M5), the iterated hybrid (M7) achieves a statistically significant event $F_1$ gain of $+0.080$ ($95\%$ paired run-bootstrap CI $[+0.023, +0.142]$, empirical $P(\Delta \le 0) = 0.002$), while reducing false alarms by $7.65\,\text{h}^{-1}$ relative to conventional segment detectors and lifting fault classification accuracy from $0.804$ to $0.892$ (improving gain-change classification from $2/9$ to $7/9$ and offset-shift classification from $4/15$ to $10/15$).
2. **Temperature:** Relative to M5, M7 provides an event $F_1$ gain of $+0.152$ ($95\%$ CI $[+0.079, +0.231]$, $P(\Delta \le 0) < 0.00025$) and slashes post-fault alarm overhang from $38.5$ to $12.9\,\text{records/h}$ ($29\%$ reduction relative to M6 at $18.1\,\text{records/h}$).
3. **DC Voltage:** Statistical superiority over the M5 baseline is **not established** ($\Delta F_1 = +0.005$, $95\%$ CI $[-0.038, +0.047]$, $P(\Delta \le 0) = 0.417$). While standalone tuned CUSUM yields a nominally higher voltage event $F_1$ ($0.910$ vs $0.825$), it produces an unacceptable **$222.4\,\text{records/h}$ post-fault alarm overhang**, lacks fault classification, and requires an external calibrated reference standard.

We explicitly disclose that all findings are derived from mathematical sensor models without physical device testing. We present the complete open-source codebase, pre-frozen SHA-256 configuration bundles, and 165 automated regression tests ensuring bit-level reproducibility.

**Index Terms**—Fault detection and diagnosis (FDD), Guide to the Expression of Uncertainty in Measurement (GUM), Cumulative Sum (CUSUM), measurement lifecycle, sensor lag, false alarm rate, precision instrumentation, reproducible metrology.

---

## I. Introduction

Precision measurement systems are foundational to modern automated test equipment (ATE), laboratory calibration benches, and high-reliability aerospace monitoring. In such environments, instrumentation must satisfy two stringent operational requirements:
1. **Traceable Uncertainty Quantification:** Measurements must be accompanied by rigorously evaluated uncertainty budgets conforming to international standards, primarily JCGM 100:2008 (the GUM) [1] and ILAC-G8:09/2019 decision rules [2].
2. **Automated Anomaly and Degradation Awareness:** Instrumental degradation—ranging from rapid transient spikes and ADC stuck states to subtle calibration drifts, static offset shifts, and load-dependent gain errors—must be detected and diagnosed rapidly before corrupting downstream calibration decisions.

In current metrological practice, uncertainty calculation is predominantly performed using offline spreadsheets, manual software scripts, or commercial certificate generators that operate ex post facto. Such tools treat input observation vectors as static, assuming that the measurement channel was pristine throughout the acquisition. Conversely, modern statistical process control (SPC) and machine-learning (ML) anomaly detectors are typically decoupled from the metrological measurement model. When applied naively to precision physical channels, standalone detectors encounter three severe failure modes:

- **Thermal Settling and Setpoint Transient False Alarms:** Physical sensors exhibit non-instantaneous step responses. Resistive current shunts undergo thermal self-heating ($I^2 R$), while industrial temperature probes (RTDs, thermistors, thermocouples) exhibit first-order thermal diffusion lag with time constants $\tau$ ranging from seconds to tens of seconds. Standard moving-window statistics or threshold-based segment detectors flag these legitimate physical transitions as anomalies, creating crippling false alarm cascades [3].
- **Latched Alarm Overhang in Sequential Drift Detectors:** Sequential detectors such as Page's Cumulative Sum (CUSUM) [4] and Exponentially Weighted Moving Averages (EWMA) are optimal for detecting persistent, small mean shifts. However, once a fault resolves or an intermittent disturbance clears, standard CUSUM accumulators decay sluggishly. This causes "alarm overhang," where alarms remain active long after the sensor has returned to nominal operation, mischaracterizing the operational workload and invalidating downstream sample windows [5].
- **The Metric Blind Spot of Event $F_1$:** Many anomaly detection studies evaluate models purely via event-level precision, recall, and $F_1$ scores (treating any overlap between an alarm episode and a fault window as a true positive) [6]. This metric is blind to alarm duration: a detector that triggers once and remains latched forever can achieve near-perfect event recall and misleadingly high event $F_1$, despite being operationally unusable.

### Contributions of This Work
To address these challenges, this paper presents **IMUCA (Intelligent Measurement Uncertainty and Calibration Analyzer)**, an open-source, audited framework for simultaneous GUM-compliant metrology and multi-track hybrid fault detection. Rather than asserting universal superiority across all measurement domains, this work provides a rigorous, empirically grounded evaluation across synthetic DC voltage, DC current, and temperature acquisition channels. The specific contributions are:

1. **An Audited 12-Stage GUM/ILAC Metrology Pipeline:** A mathematically verified pipeline implementing Bessel-corrected Type A statistics, non-normal Type B distributions, unique-index covariance propagation (eliminating symmetric double-counting), Welch-Satterthwaite effective degrees of freedom, and ILAC-G8 guard-banded conformity.
2. **A 5-Track Hybrid Fault Detection Architecture:** A modular detection engine combining: (i) an $O(1)$ deterministic data-integrity guard; (ii) a causal discrete second-difference curvature filter for setpoint transitions; (iii) causal rolling-feature gradient-boosted decision trees (GBT); (iv) an empirical stuck-signal analyzer; and (v) an optimized recursive tabular CUSUM drift detector.
3. **An Adaptive Alarm Lifecycle and Attribution Engine:** An integrated clearance mechanism incorporating adaptive hysteresis de-latching ($W_{\text{clear}}, z_{\text{clear}}$) and level-shift confirmed attribution that reduces temperature post-fault alarm overhang by $29\%$ relative to prior hybrid revisions and rescues current-channel fault classification.
4. **Independent Confirmatory Evaluation on Pre-Frozen Configurations:** An experimental protocol adhering strictly to metrological integrity: code and hyperparameters were frozen and cryptographically hashed (`results/hybrid_frozen_20261027_210333/`) before generating a fresh 85-scenario synthetic test suite (Suite v5) with disjoint random seed roots. Confirmatory evaluation was scored strictly once (`results/hybrid_final_20261027_212107/`).
5. **Rigorous Paired Bootstrap Statistical Disclosures:** We report $4,000$ paired run-bootstrap resamples, disclosing where hybrid superiority is supported (current and temperature vs M5 baseline) and where it is **not established** (voltage vs baseline). We expose the limitations of relying purely on event $F_1$ and document the metrological trade-offs observed across measurands.

---

## II. Audited Metrological Pipeline & Theoretical Foundations

The IMUCA framework structures measurement analysis into a sequential 12-stage pipeline strictly aligned with JCGM 100:2008 (GUM) [1] and ILAC-G8:09/2019 [2].

```
                     RAW TIME-SERIES MEASUREMENT VECTOR
                                     │
      ┌──────────────────────────────┴──────────────────────────────┐
      │  Stage 1: Deterministic Data Integrity & Robust Screening   │
      └──────────────────────────────┬──────────────────────────────┘
                                     │
      ┌──────────────────────────────┴──────────────────────────────┐
      │  Stage 2–4: SI Normalization, Bessel Stats & Error Metrics   │
      └──────────────────────────────┬──────────────────────────────┘
                                     │
      ┌──────────────────────────────┴──────────────────────────────┐
      │  Stage 5–8: GUM Type A, Type B, Covariances & Welch-Satt.   │
      └──────────────────────────────┬──────────────────────────────┘
                                     │
      ┌──────────────────────────────┴──────────────────────────────┐
      │  Stage 9–10: Calibration Regression & Residual Diagnostics   │
      └──────────────────────────────┬──────────────────────────────┘
                                     │
      ┌──────────────────────────────┴──────────────────────────────┐
      │  Stage 11–12: Drift Forecasting & ILAC-G8 Guarded Rules      │
      └──────────────────────────────┬──────────────────────────────┘
                                     │
                 CALIBRATION CERTIFICATE & METROLOGY REPORT
```

### A. Stage 1: Robust Screening & NIST MeanAD Fallback
Standard screening relies on the Median Absolute Deviation (MAD) [7]:
$$\text{MAD} = \operatorname{median}_i \left( |x_i - \operatorname{median}(x)| \right)$$
In highly quantized or oversampled precision ADC data, more than $50\%$ of readings within a window can be identical, driving $\text{MAD} = 0.0$. Under naive implementations, an exception or threshold bypass occurs, permitting gross outliers to corrupt downstream estimators. IMUCA implements the NIST/Iglewicz-Hoaglin fallback [7]:
$$\text{MeanAD} = \frac{1}{n} \sum_{i=1}^n |x_i - \operatorname{median}(x)|, \quad M_i = \frac{0.6745 \cdot |x_i - \operatorname{median}(x)|}{1.2533 \cdot \text{MeanAD}}$$
where $1.2533 \approx \sqrt{\pi/2}$. Points with modified Z-score $M_i > 3.5$ are flagged non-destructively as outliers without deleting raw data.

### B. Stages 5–8: Traceable Uncertainty Propagation
- **Type A Evaluation:** For $n$ repeated observations, sample variance is Bessel-corrected ($n-1$ degrees of freedom $\nu_A$):
  $$s^2 = \frac{1}{n-1}\sum_{i=1}^n (x_i - \bar{x})^2, \quad u_A(\bar{x}) = \frac{s}{\sqrt{n}}$$
- **Type B Evaluations:** Specified limits $a$ are converted according to assumed distributions:
  - Normal ($k=2$, $95.45\%$): $u_B = a / 2$
  - Rectangular (quantization/resolution): $u_B = a / \sqrt{3}$
  - Triangular (sum of two uniforms): $u_B = a / \sqrt{6}$
  - U-shaped (cycling thermal bath): $u_B = a / \sqrt{2}$
- **Covariance Matrix Propagation:** For indirect measurement models $y = f(x_1, \dots, x_N)$, GUM Eq. 13 defines:
  $$u_c^2(y) = \sum_{i=1}^N c_i^2 u^2(x_i) + 2 \sum_{i=1}^{N-1} \sum_{j=i+1}^N c_i c_j \operatorname{cov}(x_i, x_j)$$
  where $c_i = \partial f / \partial x_i$. IMUCA enforces unique unordered pair indexing $(i < j)$, preventing symmetric covariance double-counting.
- **Effective Degrees of Freedom:** Evaluated via the Welch-Satterthwaite formula:
  $$\nu_{\text{eff}} = \frac{u_c^4(y)}{\sum_{i=1}^N \frac{c_i^4 u^4(x_i)}{\nu_i}}$$
  When $\nu_{\text{eff}} < 100$, the expanded uncertainty $U = k \cdot u_c(y)$ dynamically substitutes coverage factor $k = t_{0.9545}(\nu_{\text{eff}})$ from the Student's $t$-distribution in place of $k=2.000$.

---

## III. Multi-Track Hybrid Fault Detection Architecture

To detect both fast transients and slow systematic degradations without mutual interference, IMUCA structures anomaly detection into five specialized, precedence-ordered tracks.

```
 RAW STREAM (y_t) ──► [Track 1: Data Integrity Guard] ──(Passed)──► Calibration Correction (e_t)
                            │ (Failure: O(1) Alarm)                       │
                            ▼                                             ▼
                 [missing, duplicate, gap, etc.]          ┌───────────────┴───────────────┐
                                                          │                               │
                                                          ▼                               ▼
                                              [Track 2: Curvature Filter]    [Track 4: Stuck Rule]
                                              (Second-Difference Δ^2)        (Variance Freeze)
                                                          │                               │
                                                          └───────────────┬───────────────┘
                                                                          │
                                                                          ▼
                                                              [Track 3: Causal GBT]
                                                              (Rolling Stats & Magnitude)
                                                                          │
                                                                          ▼
                                                              [Track 5: Recursive CUSUM]
                                                              (Slack k, Threshold h)
                                                                          │
                                                                          ▼
                                                              [Alarm Lifecycle Engine]
                                                              - Adaptive Hysteresis Clear
                                                              - Confirmed Attribution Fallback
```

### A. Track 1: Deterministic Data Integrity Guard
Prior to numerical processing, input records pass through an $O(1)$ deterministic parser evaluating sequence continuity ($\Delta s_t = s_t - s_{t-1} = 1$), sampling period tolerances ($|t_k - t_{k-1} - \Delta t_{\text{nominal}}| \le \epsilon$), floating-point validity ($x_t \notin \{\text{NaN}, \pm\infty\}$), and hardware error status flags. Any failure immediately triggers a specific integrity alarm (`missing_samples`, `duplicate_sequence`, `communication_gap`, `invalid_status`, or `non_finite`) and halts subsequent statistical ingestion for that record.

### B. Track 2: Causal Second-Difference Curvature Filter
To detect impulsive spikes during non-stationary setpoint changes and thermal settling without firing false alarms on the transition itself, Track 2 applies a causal discrete second-difference operator:
$$\Delta^2 x_t = x_t - 2x_{t-1} + x_{t-2}$$
For a constant-velocity ramp ($x_t = a t + b$), $\Delta^2 x_t = 0$ identically. For an exponential settling curve ($x_t = A(1 - e^{-t/\tau})$), $\Delta^2 x_t \approx -A (1 - e^{-1/\tau})^2 e^{-t/\tau} \approx 0$ for sampling periods $\Delta t \ll \tau$. Normalizing by the causal rolling scale of second differences:
$$z_t^{(\text{curv})} = \frac{|\Delta^2 x_t - \operatorname{median}(\Delta^2 x_{\text{roll}})|}{1.4826 \cdot \operatorname{MAD}(\Delta^2 x_{\text{roll}})}$$
When $z_t^{(\text{curv})} > \theta_{\text{curv}}$, an impulsive transient flag is asserted.

### C. Track 3: Causal Rolling-Feature Gradient Boosted Decision Trees
Persistent level shifts (offset shifts, gain changes, abrupt steps) are monitored using a Histogram-based Gradient Boosted Classifier (LightGBM-style architecture [8]). The feature extraction pipeline is **strictly causal**: all features at time $t$ depend solely on observations $\{x_{t-k}, e_{t-k}\}_{k \ge 0}$ to prevent temporal data leakage. Features include:
- Exponential moving average (EMA) deviations across multiple half-lives ($H \in \{5, 20, 60\}$ samples).
- Rolling MAD-normalized residual error scales.
- Setpoint correlation coefficients $\hat{\rho}(x_t, y_t^{\text{nominal}})$ over sliding windows.
- Causal rolling identical-value run lengths ($f_{\text{run}}$) for stuck-state awareness.

### D. Track 4: Empirical Stuck-Signal Rule
When an ADC freezes, residual noise drops to zero. Track 4 computes the empirical variance over sliding windows of length $W_{\text{stuck}} = 20$. If $\hat{\sigma}_W^2 < \alpha_{\text{stuck}} \cdot \sigma_{\text{nominal}}^2$ with $\alpha_{\text{stuck}} = 10^{-4}$, a `stuck_signal` state is triggered independently of GBT tree predictions.

### E. Track 5: Recursive Two-Sided Tabular CUSUM
Slow, subtle sensor aging and calibration drifts are captured by a two-sided recursive CUSUM applied to calibration residuals $e_t = x_t - \hat{x}_{\text{cal}}(t)$:
$$S_t^+ = \max\left(0, S_{t-1}^+ + \frac{e_t - \mu_0}{\sigma_0} - k\right), \quad S_t^- = \max\left(0, S_{t-1}^- - \frac{e_t - \mu_0}{\sigma_0} - k\right)$$
where $k$ is the reference allowance (slack) and $h$ is the decision threshold. In IMUCA, $k$ and $h$ are optimized during development by satisfying Siegmund's analytical Average Run Length constraint [9]:
$$\text{ARL}_0(h, k) \ge 10 \times N_{\text{max\_series}}$$
ensuring that the in-control false alarm rate during stationary operation remains bounded.

### F. Alarm Lifecycle Engine & Level-Shift Attribution Fallback
Prior hybrid revisions suffered from two critical operational defects:
1. **Latching Alarm Overhang:** CUSUM drift alarms persisted indefinitely until run completion, creating hundreds of spurious alarm records after the fault resolved.
2. **Attribution Truncation at Run End:** The post-trigger confirmation window looked ahead $D + L$ samples to distinguish isolated spikes from persistent step/gain changes. If an offset shift occurred within $D + L$ samples of run termination, the look-ahead fell off the buffer, defaulting the categorization to `transient` and ruining classification accuracy.

Milestone 7 remediates both defects:
- **Hysteresis Clearance:** Alarms clear when residuals satisfy $|z_t| \le z_{\text{clear}}$ (with $z_{\text{clear}} = 2.0$) continuously across a clearance horizon $W_{\text{clear}} = 60$ samples.
- **In-Episode Level-Shift Fallback:** If an alarm episode persists through to run termination without clearance, the engine evaluates the in-episode mean shift $\bar{e}_{\text{episode}} - \bar{e}_{\text{baseline}}$. If $|\Delta \bar{e}| \ge k_{\text{confirm}} \cdot \hat{\sigma}_e$, the event is confirmed as a persistent `offset_shift` or `gain_change` rather than falling back to an unclassified transient.

---

## IV. Experimental Methodology & Synthetic Benchmark Suites

### A. Physical Sensor Simulation Models
To evaluate detectors across distinct metrological dynamics, IMUCA generates synthetic datasets using differential physics-based models:

1. **DC Voltage Channel:** Direct resistive divider feeding an analog-to-digital converter. Governed by thermal Johnson-Nyquist noise, input impedance loading, and reference voltage drift. Operating range: $0.1\,\text{V}$ to $10.0\,\text{V}$.
2. **DC Current Channel (Shunt with TCR and Self-Heating):** Models an indirect low-burden precision manganin shunt resistor ($R_{\text{shunt}} = 0.1\,\Omega$):
   $$V_{\text{shunt}}(t) = I(t) \cdot R_{\text{shunt}} \left[1 + \alpha_{\text{TCR}}(T_{\text{ambient}} - T_0) + \theta_{\text{self-heating}} \cdot I^2(t)\right] + \epsilon_{\text{thermal}}(t)$$
   Simulates non-linear Joule self-heating thermal transients, TCR resistance shifts, and low-burden voltage drops across steps up to $1000.0\,\text{mA}$.
3. **Temperature Channel (First-Order Thermal Diffusion Lag):** Models immersion probes governed by thermal lag dynamics:
   $$\frac{d T_{\text{measured}}}{dt} = \frac{1}{\tau} \left(T_{\text{medium}}(t) - T_{\text{measured}}(t)\right) + \epsilon_{\text{Johnson}}(t)$$
   Evaluated across three realistic sensor variants:
   - *Variant TA:* Fast-response, low-noise thin-film RTD ($\tau = 2.0\,\text{s}$, $\sigma = 0.05\,^\circ\text{C}$).
   - *Variant TB:* Medium industrial thermistor ($\tau = 8.0\,\text{s}$, $\sigma = 0.15\,^\circ\text{C}$).
   - *Variant TC:* Slow, high-noise sheathed industrial thermocouple ($\tau = 25.0\,\text{s}$, $\sigma = 0.45\,^\circ\text{C}$).

### B. 11-Class Fault Taxonomy and Operating Phases
The benchmark simulates 11 distinct fault modes:
- **Data Integrity Fault Modes (5 classes):** `missing_samples`, `duplicate_sequence`, `communication_gap`, `invalid_status`, `non_finite`.
- **Signal Fault Modes (6 classes):** `isolated_spike`, `abrupt_change`, `offset_shift`, `gain_change`, `stuck_signal`, `gradual_drift`.

Each run evaluates performance across four distinct operating phases:
1. *Steady-State Phase:* Constant nominal input; tests baseline stationary noise immunity.
2. *Ramp Phase:* Linear slew rates; tests derivative tracking.
3. *Settling Phase:* Window immediately following setpoint steps; tests lag-transient discrimination.
4. *Post-Event Transient Phase:* Interval immediately following fault clearance; measures alarm de-latching speed and overhang.

### C. Benchmark Suites and Seed Disjointness
Five generations of synthetic benchmark suites have been produced. To prevent methodological data snooping and hyperparameter overfitting, strict dataset segregation was maintained:
- **Suite v3 (Development Only):** 94 scenarios used exclusively for model training (calibration split) and hyperparameter selection (validation split).
- **Suite v4 (Historical Final):** 85 scenarios used for Milestone 6 evaluation; archived and permanently frozen.
- **Suite v5 (Confirmatory Test Suite):** 85 scenarios (166,278 records; 486 injected signal-fault events) generated with completely disjoint seed roots:
  - Calibration: `62015028`
  - Validation: `72025028`
  - Test: `84055028`

### D. Cryptographic Freezing & Confirmatory Evaluation Protocol
Prior to generating or inspecting Suite v5, all detector source code, calibration polynomials, trained GBT weights, and hyperparameter dictionaries were locked into a frozen bundle at `results/hybrid_frozen_20261027_210333/`. The SHA-256 hash of `frozen_settings.json` was cryptographically recorded as:
```
816270d89b31d9772c2d4006071a4c88c803ac5607551395e85be5af846aa2e9
```
The confirmatory evaluation harness (`scripts/run_hybrid_iteration.py final`) executed strictly once, verifying that active code hashes matched the frozen manifest before scoring the fresh v5 test split, outputting results to `results/hybrid_final_20261027_212107/`.

### E. Paired Run-Bootstrap Resampling Methodology
To compare detectors scored on identical runs, we implemented post-hoc paired run-bootstrap resampling ($B = 4,000$ resamples) [10]. 
- **Resampling Unit:** The whole acquisition run (`experiment_id`), preserving intra-run temporal autocorrelation, sensor variant parameters, and noise dynamics ($N=84$ runs for voltage, $N=84$ for current, $N=87$ for temperature).
- **Unstratified Resampling:** Sampling is uniform across runs within each measurand; it is not stratified by fault class or operating context.
- **Reported Statistics:** The paired difference $\Delta = M_A - M_B$, the $95\%$ bootstrap percentile interval $[\Delta_{0.025}, \Delta_{0.975}]$, and the empirical proportion of bootstrap resamples with non-positive difference:
  $$P(\Delta \le 0) = \frac{1}{B} \sum_{b=1}^B \mathbb{I}(\Delta_b \le 0)$$
  *Important Methodological Disclosure:* $P(\Delta \le 0)$ is an empirical bootstrap probability, **not a conventional frequentist null-hypothesis p-value**. When zero of $4,000$ resamples satisfy $\Delta \le 0$, we report $P(\Delta \le 0) < 0.00025$ ($< 2.5 \times 10^{-4}$) rather than an impossible exact zero.

---

## V. Empirical Results & Paired Statistical Comparisons

### A. Master Test Performance Evaluation (Suite v5)
Table I presents the overall performance on the fresh Suite v5 test split across all three measurands, comparing the iterated Hybrid M7 against frozen Hybrid M6, frozen Hybrid M5, and representative standalone detectors.

#### TABLE I: Master Performance Summary on Independent Test Suite v5 (Scored Strictly Once)
*Notes: All $F_1$ and FA/h intervals are $95\%$ run-bootstrap intervals. Classification accuracy evaluates detected events with exact ground-truth matching. Post-fault alarm overhang is in records per hour. Delays are median samples.*

| Measurand | Detector Architecture | Event $F_1$ [$95\%$ CI] | Macro Recall | Episode Precision | False Alarms / h [$95\%$ CI] | Missed Events | Class. Accuracy [$95\%$ CI] | Post-Fault Overhang (rec/h) | Median Delay (samples) |
|---|---|---|---|---|---|---|---|---|---|
| **DC Voltage** | **IMUCA Hybrid M7** | **0.825** [0.76, 0.88] | **0.870** | **0.785** | **2.6** [1.9, 3.6] | **17 / 162** | **0.828** [0.76, 0.88] | **0.0** | **0** |
| DC Voltage | IMUCA Hybrid M6 (frozen) | 0.825 [0.76, 0.88] | 0.870 | 0.785 | 2.6 [1.9, 3.6] | 17 / 162 | 0.800 [0.73, 0.86] | 0.0 | 0 |
| DC Voltage | IMUCA Hybrid M5 (frozen) | 0.820 [0.77, 0.87] | 0.787 | 0.856 | 1.6 [1.0, 2.4] | 27 / 162 | 0.852 [0.78, 0.90] | 0.0 | 0 |
| DC Voltage | Tuned CUSUM Alone | 0.910 [0.87, 0.95]* | 0.848 | 0.982 | 0.1 [0.0, 0.4] | 38 / 162 | – (No Class.) | 222.4 | 0 |
| DC Voltage | Conventional Segment Det. | 0.630 [0.55, 0.71] | 0.495 | 0.867 | 1.1 [0.7, 1.8] | 55 / 162 | – | 3.4 | 0 |
| DC Voltage | Standalone GBT Classifier | 0.546 [0.47, 0.62] | 0.422 | 0.771 | 1.6 [1.0, 2.4] | 93 / 162 | – | 0.7 | 2 |
| DC Voltage | Standalone Isolation Forest | 0.217 [0.15, 0.28] | 0.216 | 0.219 | 8.9 [7.4, 10.5]| 143 / 162 | – | 0.1 | 29 |
| **DC Current** | **IMUCA Hybrid M7** | **0.911** [0.87, 0.94] | **0.935** | **0.888** | **1.3** [0.8, 2.1] | **14 / 162** | **0.892** [0.83, 0.93] | **11.3** | **0** |
| DC Current | IMUCA Hybrid M6 (frozen) | 0.913 [0.87, 0.95] | 0.935 | 0.893 | 1.3 [0.8, 2.0] | 14 / 162 | 0.804 [0.73, 0.86] | 1.5 | 0 |
| DC Current | IMUCA Hybrid M5 (frozen) | 0.831 [0.77, 0.89] | 0.770 | 0.903 | 1.0 [0.6, 1.7] | 23 / 162 | 0.906 [0.85, 0.94] | 8.3 | 0 |
| DC Current | Standalone GBT Classifier | 0.831 [0.77, 0.89] | 0.796 | 0.869 | 1.9 [1.2, 2.7] | 39 / 162 | – | 0.8 | 0 |
| DC Current | Tuned CUSUM Alone | 0.738 [0.68, 0.79] | 0.620 | 0.911 | 0.3 [0.1, 0.8] | 80 / 162 | – (No Class.) | 116.6 | 0 |
| DC Current | Conventional Segment Det. | 0.508 [0.44, 0.57] | 0.524 | 0.492 | 9.0 [7.5, 10.6]| 49 / 162 | – | 1.5 | 0 |
| DC Current | Standalone Isolation Forest | 0.224 [0.16, 0.29] | 0.262 | 0.195 | 12.2 [10.5, 14.1]| 138 / 162 | – | 0.1 | 23 |
| **Temperature**| **IMUCA Hybrid M7** | **0.750** [0.68, 0.81] | **0.728** | **0.773** | **2.9** [2.1, 3.8] | **38 / 162** | **0.798** [0.72, 0.86] | **12.9** | **0** |
| Temperature| IMUCA Hybrid M6 (frozen) | 0.752 [0.68, 0.81] | 0.728 | 0.778 | 2.8 [2.1, 3.8] | 38 / 162 | 0.815 [0.74, 0.87] | 18.1 | 0 |
| Temperature| IMUCA Hybrid M5 (frozen) | 0.598 [0.51, 0.67] | 0.556 | 0.646 | 3.4 [2.6, 4.5] | 79 / 162 | 0.578 [0.47, 0.68] | 38.5 | 0 |
| Temperature| Standalone GBT Classifier | 0.649 [0.58, 0.71] | 0.609 | 0.696 | 4.2 [3.3, 5.4] | 72 / 162 | – | 0.7 | 0 |
| Temperature| Conventional Segment Det. | 0.612 [0.55, 0.67] | 0.644 | 0.584 | 4.9 [3.8, 6.1] | 61 / 162 | – | 15.6 | 0 |
| Temperature| Tuned CUSUM Alone | 0.586 [0.47, 0.68] | 0.414 | 1.000 | 0.0 [0.0, 0.2] | 100 / 162 | – (No Class.) | 96.9 | 0 |
| Temperature| Standalone Isolation Forest | 0.456 [0.38, 0.53] | 0.340 | 0.693 | 2.2 [1.5, 3.0] | 91 / 162 | – | 1.9 | 0 |

*\*Note on CUSUM Voltage F1: CUSUM scores 0.910 purely due to latching overlap; alarms persist across 222.4 records/h after faults end, and it provides zero fault classification.*

---

### B. Exploratory Paired Run-Bootstrap Comparisons
Table II summarizes the four post-hoc paired comparisons conducted across $4,000$ paired bootstrap resamples on the identical Suite v5 runs.

#### TABLE II: Summary of Paired Run-Bootstrap Resampling Analyses ($B = 4,000$ Resamples)
*Notes: Comparisons are exploratory post-hoc analyses on identical test runs. $P(\Delta \le 0)$ denotes the empirical proportion of resamples with $\Delta \le 0$; values of 0.000 are bounded as $<0.00025$.*

| Comparison | Measurand | $F_1$ Det A | $F_1$ Det B | Diff $\Delta F_1$ [$95\%$ Paired CI] | $P(\Delta \le 0)$ | FA/h Diff [$95\%$ CI] | Statistical Conclusion |
|---|---|---|---|---|---|---|---|
| **M7 vs M6** | Voltage | 0.825 | 0.825 | **+0.000** [+0.000, +0.000] | 1.000 | 0.00 [0.00, 0.00] | Identical alarm output; no event $F_1$ change |
| | Current | 0.911 | 0.913 | **−0.002** [−0.009, +0.001] | 0.765 | +0.07 [0.00, +0.21] | No event $F_1$ change; classification improved |
| | Temperature | 0.750 | 0.752 | **−0.002** [−0.007, +0.001] | 0.936 | +0.06 [0.00, +0.20] | No event $F_1$ change; overhang reduced $29\%$ |
| **M7 vs M5** | Voltage | 0.825 | 0.820 | **+0.005** [−0.038, +0.047] | 0.417 | +1.01 [+0.29, +1.78] | **Superiority is NOT established** |
| | Current | 0.911 | 0.831 | **+0.080** [+0.023, +0.142] | 0.002 | +0.34 [−0.27, +0.99] | Significant $F_1$ improvement ($P = 0.002$) |
| | Temperature | 0.750 | 0.598 | **+0.152** [+0.079, +0.231] | <0.00025 | −0.55 [−1.31, +0.24] | Significant $F_1$ gain; overhang reduced $66\%$ |
| **M7 vs CUSUM** | Voltage | 0.825 | 0.910 | **−0.085** [−0.147, −0.029] | 0.999 | +2.55 [+1.73, +3.47] | CUSUM has higher $F_1$ but $222.4\,\text{rec/h}$ overhang |
| | Current | 0.911 | 0.738 | **+0.173** [+0.114, +0.234] | <0.00025 | +1.01 [+0.41, +1.76] | Hybrid significantly superior in $F_1$ & diagnosis |
| | Temperature | 0.750 | 0.586 | **+0.164** [+0.062, +0.273] | 0.00025 | +2.89 [+1.88, +4.08] | Hybrid significantly superior in $F_1$ & diagnosis |
| **M7 vs Segment**| Voltage | 0.825 | 0.630 | **+0.195** [+0.128, +0.263] | <0.00025 | +1.48 [+0.79, +2.25] | Hybrid superior on event $F_1$ |
| | Current | 0.911 | 0.508 | **+0.403** [+0.341, +0.474] | <0.00025 | **−7.65** [−9.60, −5.83] | Massive $F_1$ gain and $7.65\,\text{FA/h}$ reduction |
| | Temperature | 0.750 | 0.612 | **+0.138** [+0.064, +0.214] | <0.00025 | **−1.97** [−3.15, −0.69] | Substantial $F_1$ gain and $1.97\,\text{FA/h}$ reduction |

---

### C. Deep-Dive: Verification of the Zero-Width Voltage Interval
In Table II, the paired comparison between Hybrid M7 and Hybrid M6 on voltage displays:
$$\Delta F_1 = +0.000, \quad 95\% \text{ CI } [+0.000, +0.000], \quad \Delta \text{FA/h} = 0.00$$
To determine whether this represents an estimation anomaly or metric truncation, we audited the prediction files (`voltage_V_test_alarms.csv`) and hyperparameter manifests. 

The audit reveals that on the validation split, the hyperparameter optimization grid selected **the exact same detector tuple for voltage in M7 as in M6**:
- `transient_extra`: `none`
- `segment_mad_threshold`: `3.5`
- `cusum_k`: `0.5`, `cusum_h`: `12`, `cusum_mode`: `run`
- `settling_suppression`: `false`

The only code modification active in M7 was the in-episode level-shift fallback in `confirm_categories_error()`. This function executes **after alarm generation** and alters only the categorical label assigned to an already confirmed alarm episode; it does not change the binary alarm series $a_t \in \{0, 1\}$. 

Consequently, the alarm series generated by Hybrid M7 and Hybrid M6 for all $84$ test runs are **bit-for-bit identical**. In every one of the $4,000$ bootstrap resamples, $F_1(s_a) - F_1(s_b) \equiv 0.0000000$ identically. The zero-width interval is therefore not a statistical artifact of large sample size, but an exact algebraic identity reflecting identical parameter selection on validation.

---

### D. Per-Fault Class Detection, Attribution & Latency Breakdown
Table III details the detection recall and median detection delays across the six signal fault classes.

#### TABLE III: Detection Recall (Detected / Injected Events [Wilson $95\%$ Score Interval]) and Median Delay (Samples)
| Measurand | Fault Class | Injected $n$ | IMUCA Hybrid M7 | IMUCA Hybrid M6 | IMUCA Hybrid M5 | Segment Detector | Tuned CUSUM |
|---|---|---|---|---|---|---|---|
| **Voltage** | `abrupt_change` | 27 | **26/27** [0.82, 0.99], 0 | 26/27 [0.82, 0.99], 0 | 26/27 [0.82, 0.99], 0 | 26/27 [0.82, 0.99], 0 | 27/27 [0.88, 1.00], 0 |
| | `gain_change` | 9 | **6/9** [0.35, 0.88], 0 | 6/9 [0.35, 0.88], 0 | 3/9 [0.12, 0.65], 0 | 3/9 [0.12, 0.65], 0 | 9/9 [0.70, 1.00], 0 |
| | `gradual_drift` | 9 | **9/9** [0.70, 1.00], 78 | 9/9 [0.70, 1.00], 78 | 9/9 [0.70, 1.00], 106 | 1/9 [0.02, 0.44], 72 | 9/9 [0.70, 1.00], 85 |
| | `isolated_spike` | 72 | **65/72** [0.81, 0.95], 0 | 65/72 [0.81, 0.95], 0 | 60/72 [0.73, 0.90], 0 | 63/72 [0.78, 0.93], 0 | 49/72 [0.57, 0.78], 0 |
| | `offset_shift` | 18 | **13/18** [0.49, 0.88], 0 | 13/18 [0.49, 0.88], 0 | 12/18 [0.44, 0.84], 0 | 9/18 [0.29, 0.71], 0 | 16/18 [0.67, 0.97], 0 |
| | `stuck_signal` | 27 | **26/27** [0.82, 0.99], 6 | 26/27 [0.82, 0.99], 6 | 25/27 [0.77, 0.98], 8 | 5/27 [0.08, 0.37], 4 | 14/27 [0.34, 0.69], 0 |
| **Current** | `abrupt_change` | 27 | **25/27** [0.77, 0.98], 0 | 25/27 [0.77, 0.98], 0 | 25/27 [0.77, 0.98], 0 | 26/27 [0.82, 0.99], 0 | 15/27 [0.37, 0.72], 0 |
| | `gain_change` | 9 | **9/9** [0.70, 1.00], 0 | 9/9 [0.70, 1.00], 0 | 6/9 [0.35, 0.88], 0 | 5/9 [0.27, 0.81], 0 | 9/9 [0.70, 1.00], 0 |
| | `gradual_drift` | 9 | **9/9** [0.70, 1.00], 72 | 9/9 [0.70, 1.00], 72 | 5/9 [0.27, 0.81], 167 | 0/9 [0.00, 0.30], – | 9/9 [0.70, 1.00], 72 |
| | `isolated_spike` | 72 | **64/72** [0.80, 0.94], 0 | 64/72 [0.80, 0.94], 0 | 66/72 [0.83, 0.96], 0 | 69/72 [0.88, 0.99], 0 | 36/72 [0.39, 0.61], 0 |
| | `offset_shift` | 18 | **15/18** [0.61, 0.94], 0 | 15/18 [0.61, 0.94], 0 | 10/18 [0.34, 0.75], 0 | 10/18 [0.34, 0.75], 0 | 10/18 [0.34, 0.75], 0 |
| | `stuck_signal` | 27 | **26/27** [0.82, 0.99], 4 | 26/27 [0.82, 0.99], 4 | 27/27 [0.88, 1.00], 4 | 3/27 [0.04, 0.28], 19 | 3/27 [0.04, 0.28], 0 |
| **Temperature**| `abrupt_change` | 27 | **22/27** [0.63, 0.92], 0 | 22/27 [0.63, 0.92], 0 | 14/27 [0.34, 0.69], 0 | 16/27 [0.41, 0.75], 0 | 16/27 [0.41, 0.75], 0 |
| | `gain_change` | 9 | **5/9** [0.27, 0.81], 0 | 5/9 [0.27, 0.81], 0 | 5/9 [0.27, 0.81], 0 | 5/9 [0.27, 0.81], 23 | 1/9 [0.02, 0.44], 41 |
| | `gradual_drift` | 9 | **8/9** [0.56, 0.98], 113 | 8/9 [0.56, 0.98], 113 | 6/9 [0.35, 0.88], 34 | 9/9 [0.70, 1.00], 5 | 7/9 [0.45, 0.94], 169 |
| | `isolated_spike` | 72 | **60/72** [0.73, 0.90], 0 | 60/72 [0.73, 0.90], 0 | 31/72 [0.32, 0.55], 0 | 50/72 [0.58, 0.79], 0 | 23/72 [0.22, 0.43], 0 |
| | `offset_shift` | 18 | **11/18** [0.39, 0.80], 0 | 11/18 [0.39, 0.80], 0 | 9/18 [0.29, 0.71], 0 | 13/18 [0.49, 0.88], 0 | 7/18 [0.20, 0.61], 0 |
| | `stuck_signal` | 27 | **18/27** [0.48, 0.81], 10 | 18/27 [0.48, 0.81], 10 | 18/27 [0.48, 0.81], 8 | 8/27 [0.16, 0.48], 24 | 8/27 [0.16, 0.48], 0 |

---

### E. Fault Categorization & Attribution Breakthrough
While alarm detection indicates an anomaly is present, root-cause diagnosis requires accurate categorization. Table IV demonstrates the major breakthrough achieved by the M7 in-episode attribution fallback.

#### TABLE IV: Fault Classification Accuracy & Attribution Breakdown (Detected Events Categorized Correctly)
| Measurand | Architecture | Overall Accuracy [$95\%$ CI] | `abrupt_change` | `gain_change` | `gradual_drift` | `isolated_spike` | `offset_shift` | `stuck_signal` |
|---|---|---|---|---|---|---|---|---|
| **Voltage** | **Hybrid M7** | **0.828** [0.76, 0.88] | **24/26** | **3/6** | **8/9** | **60/65** | **7/13** | **18/26** |
| Voltage | Hybrid M6 (frozen) | 0.800 [0.73, 0.86] | 23/26 | 3/6 | 8/9 | 59/65 | 5/13 | 18/26 |
| Voltage | Hybrid M5 (frozen) | 0.852 [0.78, 0.90] | 24/26 | 0/3 | 9/9 | 60/60 | 2/12 | 20/25 |
| **Current** | **Hybrid M7** | **0.892** [0.83, 0.93] | **21/25** | **7/9** | **9/9** | **60/64** | **10/15** | **25/26** |
| Current | Hybrid M6 (frozen) | 0.804 [0.73, 0.86] | 21/25 | 2/9 | 9/9 | 58/64 | 4/15 | 25/26 |
| Current | Hybrid M5 (frozen) | 0.906 [0.85, 0.94] | 24/25 | 2/6 | 5/5 | 65/66 | 3/10 | 27/27 |
| **Temperature**| **Hybrid M7** | **0.798** [0.72, 0.86] | **14/22** | **3/5** | **4/8** | **53/60** | **8/11** | **17/18** |
| Temperature| Hybrid M6 (frozen) | 0.815 [0.74, 0.87] | 16/22 | 2/5 | 4/8 | 57/60 | 5/11 | 17/18 |
| Temperature| Hybrid M5 (frozen) | 0.578 [0.47, 0.68] | 3/14 | 2/5 | 1/6 | 24/31 | 4/9 | 14/18 |

In the current channel, M7 lifted classification accuracy from $0.804$ to **$0.892$**:
- Correct `gain_change` categorizations jumped from $2/9$ to **$7/9$**.
- Correct `offset_shift` categorizations jumped from $4/15$ to **$10/15$**.
In M6, these events were mislabeled as transients because the alarms persisted through the end of the test run, which prevented the look-ahead window from filling.

---

### F. Context-Dependent False Alarms Across Operating Phases
Table V breaks down false alarm rates across the four operational contexts.

#### TABLE V: False Alarm Rates Across Operational Phases ($\text{Events / h}$ with Exposure Hours in Parentheses)
| Measurand | Detector | Steady-State Phase | Ramp Phase | Settling Phase | Post-Event Transient Phase |
|---|---|---|---|---|---|
| **Voltage** | **Hybrid M7** | **2.9** (9.98 h) | **0.0** (0.49 h) | **42.1** (0.24 h) | **38.8** (0.18 h) |
| Voltage | Hybrid M6 (frozen) | 2.9 (9.98 h) | 0.0 (0.49 h) | 42.1 (0.24 h) | 38.8 (0.18 h) |
| Voltage | Hybrid M5 (frozen) | 1.1 (9.98 h) | 6.1 (0.49 h) | 12.6 (0.24 h) | 44.4 (0.18 h) |
| Voltage | Segment Detector | 0.9 (9.98 h) | 0.0 (0.49 h) | 0.0 (0.24 h) | 38.8 (0.18 h) |
| Voltage | Tuned CUSUM Alone | 0.1 (9.98 h) | 0.0 (0.49 h) | 0.0 (0.24 h) | 0.0 (0.18 h) |
| **Current** | **Hybrid M7** | **0.7** (5.56 h) | – (0.00 h) | – (0.00 h) | **1.7** (5.44 h) |
| Current | Hybrid M6 (frozen) | 0.7 (5.56 h) | – (0.00 h) | – (0.00 h) | 1.5 (5.44 h) |
| Current | Hybrid M5 (frozen) | 0.2 (5.56 h) | – (0.00 h) | – (0.00 h) | 1.8 (5.44 h) |
| Current | Segment Detector | 6.8 (5.56 h) | – (0.00 h) | – (0.00 h) | 16.0 (5.44 h) |
| **Temperature**| **Hybrid M7** | **1.7** (5.20 h) | **3.2** (3.17 h) | **1.3** (3.79 h) | **5.7** (4.04 h) |
| Temperature| Hybrid M6 (frozen) | 1.5 (5.20 h) | 3.2 (3.17 h) | 1.3 (3.79 h) | 5.7 (4.04 h) |
| Temperature| Hybrid M5 (frozen) | 1.2 (5.20 h) | 1.6 (3.17 h) | 1.6 (3.79 h) | 9.2 (4.04 h) |
| Temperature| Segment Detector | 0.8 (5.20 h) | 0.0 (3.17 h) | 10.6 (3.79 h) | 17.3 (4.04 h) |
| Temperature| Tuned CUSUM Alone | 0.0 (5.20 h) | 0.0 (3.17 h) | 0.0 (3.79 h) | 0.0 (4.04 h) |

In the temperature channel, Hybrid M7 maintains low settling false alarms ($1.3\,\text{FA/h}$ vs $10.6\,\text{FA/h}$ for the conventional segment detector) and suppresses post-event false alarms to $5.7\,\text{FA/h}$ (vs $17.3\,\text{FA/h}$ for the segment detector).

---

## VI. Discussion & Critical Analysis

### A. Channel-Dependent Efficacy: No Universal Superiority
A central finding of this study is that **detector superiority is strictly channel-dependent**:
- In the **current channel**, the hybrid detector provides superior holistic utility. By combining setpoint-aware curvature filtering and causal GBT models, M7 achieves $0.911$ event $F_1$, recovers $64/72$ spikes while maintaining $100\%$ gradual drift recall ($9/9$), and suppresses false alarms by $7.65\,\text{FA/h}$ relative to segment detectors.
- In the **temperature channel**, the hybrid provides massive improvements over baseline M5 ($F_1$ rises from $0.598$ to $0.750$, $P < 0.00025$). The curvature track enables detection of spikes during dynamic thermal ramps ($31/37$ non-stationary spike recall vs $4/37$ in M5), while hysteresis clearance slashes overhang by $29\%$ relative to M6.
- In the **voltage channel**, however, **superiority of the hybrid over the M5 baseline is not established** ($\Delta F_1 = +0.005$, $95\%$ CI $[-0.038, +0.047]$, $P = 0.417$). The simple segment detector achieves $1.1\,\text{FA/h}$ compared to M7's $2.6\,\text{FA/h}$. In low-noise, linear channels without thermal lag, adding complex machine-learning and curvature tracks yields diminishing returns and slightly elevated false alarm rates during setpoint step transitions.

### B. The Alarm Overhang Paradox: Why Event $F_1$ Misleads
A critical methodological contribution of this evaluation is exposing the failure of event-level $F_1$ to capture operational alarm utility. 

On the voltage channel, tuned CUSUM alone appears superior if judged purely by event $F_1$ ($0.910$ vs $0.825$). However, inspection of the alarm records reveals that CUSUM exhibits an astronomical **$222.4\,\text{post-fault alarm records/hour}$**. Because CUSUM accumulators decay slowly after a fault ends, alarms remain active across hundreds of nominal data points. Furthermore, CUSUM provides zero fault categorization (cannot distinguish a $10\,\text{mV}$ drift from a frozen sensor) and relies on an externally calibrated reference standard. In an automated calibration laboratory, such latching behavior would halt production lines and require manual operator clearing. The hybrid detector completely eliminates voltage overhang ($0.0\,\text{records/h}$) while delivering automated fault diagnosis.

### C. Temperature Sensor Thermal Lag and Drift Latency
Gradual drift detection in the temperature channel exhibits an unavoidable physical delay. In Suite v5, the median detection delay for gradual temperature drifts was **113 seconds (samples)**. This latency is physically dictated by the sensor's thermal time constant: for Variant TC ($\tau = 25.0\,\text{s}$), a gradual temperature drift of $0.05\,^\circ\text{C/min}$ remains masked within the thermal diffusion lag and Johnson noise floor for over two minutes before the cumulative deviation crosses the statistical detection threshold.

---

## VII. Unresolved Issues, Threats to Validity & Metrological Limitations

To maintain the highest standards of scientific integrity, the following limitations must be explicitly emphasized:

1. **Voltage Channel Equivalence:** Hybrid M7 does not establish superiority over the simpler M5 baseline on the DC voltage channel. For clean, approximately linear voltage signals, conventional segment thresholding remains a viable, lower-complexity alternative.
2. **Imperfect Current Classification:** Although M7 improved current fault classification from $0.804$ to $0.892$, offset shift classification remains imperfect ($10/15$ correct), and isolated spike recall ($64/72$) does not achieve $100\%$. The interplay between self-heating thermal curves and static offsets requires further modeling.
3. **Thermal Diffusion Latency:** Temperature drift detection delay remains bounded by physical sensor dynamics (median 113 s). Fast detection of small temperature drifts without high false alarm rates is fundamentally constrained by sensor thermal inertia.
4. **Metric Limitations:** Event-level $F_1$ is insufficient for evaluating industrial anomaly detectors because it ignores alarm duration, persistence, and post-fault recovery. Operational metrics (FA/h, overhang records/h, categorization accuracy) must be co-reported.
5. **Synthetic Simulation Boundary:** **All experiments were conducted exclusively on synthetic datasets generated from mathematical sensor models.** The framework has not yet been validated on physical ADCs, real semiconductor testbenches, traceable laboratory standards (e.g., Fluke 5730A / Keysight 3458A), or environmental thermal chambers.
6. **Cross-Device Generalization Limits:** While Suite v5 evaluated previously unseen random realisations generated with disjoint seeds, this does not establish generalization across physically diverse sensor manufacturers, lead-wire parasitics, or unmodeled electromagnetic interference (EMI).
7. **Unstratified Bootstrap Resampling:** The $4,000$ paired bootstrap resamples were drawn at the whole-run level without stratification across fault classes or noise tiers. Rare fault modes within specific noise strata may exhibit wider true sampling variances than captured by aggregate run resampling.

---

## VIII. Conclusion & Physical Metrology Roadmap

This paper presented an audited, reproducible metrology and multi-track hybrid fault detection framework for precision instrumentation. By combining GUM-compliant uncertainty propagation with an $O(1)$ integrity guard, causal curvature filtering, rolling-feature GBTs, recursive CUSUM, and an adaptive hysteresis lifecycle, IMUCA resolves critical operational trade-offs in dynamic measurement channels. 

Evaluated on an independent, pre-frozen 85-scenario synthetic test suite, the hybrid detector establishes substantial, statistically supported improvements in current-channel reliability ($+0.080$ $F_1$, $P = 0.002$; classification accuracy $0.892$) and temperature alarm lifecycle ($+0.152$ $F_1$, $P < 0.00025$; $29\%$ overhang reduction). We honestly disclose that voltage superiority over baseline is not established, and explain why event $F_1$ must not be used in isolation from alarm overhang and fault attribution.

### Phase 2 Roadmap: Laboratory Hardware Validation
The immediate next phase of the IMUCA project transitions the software framework from synthetic benchmarks to physical experimental validation:
1. **Instrument Communication Layer:** Implementation of a hardware DAQ abstraction layer interfacing with physical precision multimeters (Keysight 34461A / 3458A) via SCPI-over-USB/GPIB and microcontrollers (INA219 / ADS1115 / DS18B20) via UART/I2C.
2. **Environmental Chamber Stress-Testing:** Deployment of calibrated PT100 RTDs and precision shunts inside an automated environmental test chamber, introducing controlled ambient thermal ramps, supply voltage fluctuations, and physical calibration drifts.
3. **Metrological Traceability Audits:** Cross-validation of the automated GUM uncertainty engine against primary calibration certificates issued by accredited ISO/IEC 17025 laboratories.

---

## References

1. Joint Committee for Guides in Metrology (JCGM), *Evaluation of measurement data — Guide to the expression of uncertainty in measurement*, JCGM 100:2008 (GUM 1995 with minor corrections), Sèvres, France: BIPM, 2008.
2. International Laboratory Accreditation Cooperation (ILAC), *Guidelines on Decision Rules and Statements of Conformity*, ILAC-G8:09/2019, 2019.
3. R. H. Dieck, *Measurement Uncertainty: Methods and Applications*, 4th ed., Research Triangle Park, NC: ISA, 2007.
4. E. S. Page, "Continuous inspection schemes," *Biometrika*, vol. 41, no. 1/2, pp. 100–115, 1954.
5. D. C. Montgomery, *Introduction to Statistical Quality Control*, 8th ed., New York, NY: John Wiley & Sons, 2019.
6. M. Tatbul, T. J. Lee, S. Zgraggen, C. Mavroforakis, M. Shen, and N. Tatbul, "Precision and recall for time series," in *Advances in Neural Information Processing Systems (NeurIPS)*, vol. 31, 2018, pp. 1920–1930.
7. B. Iglewicz and D. C. Hoaglin, *How to Detect and Handle Outliers*, ASQC Basic References in Quality Control, vol. 16, Milwaukee, WI: ASQC Quality Press, 1993.
8. G. Ke et al., "LightGBM: A highly efficient gradient boosting decision tree," in *Advances in Neural Information Processing Systems (NeurIPS)*, vol. 30, 2017, pp. 3146–3154.
9. D. Siegmund, "Error probabilities and average run lengths for sequential test with two sides," *The Annals of Statistics*, vol. 13, no. 1, pp. 286–298, 1985.
10. B. Efron and R. J. Tibshirani, *An Introduction to the Bootstrap*, New York, NY: Chapman & Hall, 1993.
