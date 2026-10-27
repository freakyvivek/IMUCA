# IMUCA: Intelligent Measurement Uncertainty and Calibration Analyzer

> **Academic Project in Measurements & Instrumentation**  
> **Autonomous Metrology Verification & Transparent Rule-Based Decision Framework**

---

## 📌 1. Project Overview

**IMUCA (Intelligent Measurement Uncertainty and Calibration Analyzer)** is an engineering software application designed to automate the complete metrological evaluation pipeline for precision instrumentation. 

In conventional laboratory practice, measurement acquisition, statistical data reduction, Type A / Type B uncertainty evaluation, calibration regression, drift detection, and conformity decisions are fragmented across spreadsheets, datasheets, and disconnected manual calculations. This fragmentation introduces transcription errors, obscures dominant uncertainty sources, and prevents condition-based recalibration.

IMUCA unites the entire metrology workflow into a single, validated computational pipeline backed by an interactive dashboard and an automated reporting engine.

> [!IMPORTANT]
> **Proof-of-Concept Notice:**  
> All numerical demonstrations and benchmarks in this prototype are derived from the project report's **synthetic benchmark dataset** designed with injected zero offset ($+8\text{ mV}$), gain error ($+0.25\%$), random scatter, and between-session drift ($+1\text{ mV/session}$).  
> Physical hardware integration (SCPI/USB interface to Keithley/Keysight DMMs) and laboratory testing are designated for **Phase 2 (Future Scope)**.

---

## 🏗️ 2. System Architecture & 12-Stage Pipeline

```
RAW MEASUREMENT DATA (CSV / Stream)
   ↓
[1] DATA VALIDATION (Algorithm 1a: Numeric checks, span bounds, non-destructive MAD outlier flagging)
   ↓
[2] PREPROCESSING & UNIT NORMALIZATION
   ↓
[3] STATISTICAL ANALYSIS (Equations 9.1–9.3: Sample mean, Sample SD with n-1 Bessel's correction, Std error)
   ↓
[4] ERROR ANALYSIS (Equations 9.11–9.12: Absolute error E, Relative error, Percentage error E%)
   ↓
[5] TYPE A UNCERTAINTY (Equation 9.4: u_A = s / √n, ν_A = n - 1)
   ↓
[6] TYPE B UNCERTAINTY (Equation 9.5 & Table 9.1: Resolution, Manufacturer spec, Reference standard, Tempco)
   ↓
[7] UNCERTAINTY BUDGET (Equation 9.8 & Table 12.1: Variance shares h_i, Dominant source detection)
   ↓
[8] COMBINED & EXPANDED UNCERTAINTY (Equations 9.7, 9.9, 9.10: RSS u_c, Welch-Satterthwaite ν_eff, U = k·u_c)
   ↓
[9] CALIBRATION ANALYSIS (Equations 9.13, 9.16: Least-squares regression, Offset c, Gain error, 3-band conformity)
   ↓
[10] RESIDUAL DIAGNOSTICS (Equation 9.14: r_i = X_DUT - (m·X_REF + c), Half-resolution quantisation limit)
   ↓
[11] DRIFT & TREND ANALYSIS (Equation 9.15 & Algorithm 6: Within-run stability, Between-session drift slope b, p-value, Breach forecast)
   ↓
[12] INTELLIGENT DECISION ENGINE (Algorithm 7 & Chapter 16: Transparent ordered rules R1 to R5)
   ↓
DASHBOARD & AUTOMATED HTML REPORT GENERATOR
```

---

## 📐 3. Mathematical Foundations & Equations

IMUCA strictly implements the mathematical specifications from Chapter 9 of the project report:

### 3.1 Descriptive Statistics & Type A Uncertainty
- **Sample Mean:** $\bar{x} = \frac{1}{n} \sum_{i=1}^n x_i$
- **Sample Standard Deviation ($n-1$ denominator):** $s = \sqrt{\frac{1}{n-1} \sum_{i=1}^n (x_i - \bar{x})^2}$
- **Standard Error of the Mean:** $s(\bar{x}) = \frac{s}{\sqrt{n}}$
- **Type A Standard Uncertainty:** $u_A = s(\bar{x}) = \frac{s}{\sqrt{n}}$, with $\nu_A = n - 1$ degrees of freedom.

### 3.2 Type B Uncertainty Distributions & Divisors
For an input with semi-range/half-width $a$:
- **Rectangular (Uniform):** $d = \sqrt{3} \approx 1.732$ (Used for display resolution, manufacturer accuracy limits, quantisation)
- **Triangular:** $d = \sqrt{6} \approx 2.449$ (Sum of two independent uniform effects)
- **Normal ($k=2$):** $d = 2.000$ (Calibration standard certificate at 95% confidence)
- **Normal ($k=3$):** $d = 3.000$ (99.7% confidence statements)
- **U-shaped (Arcsine):** $d = \sqrt{2} \approx 1.414$ (Cycled temperature control)
- **Standard Uncertainty:** $u_B = \frac{a}{d}$

### 3.3 Uncertainty Combination & Coverage
- **Combined Standard Uncertainty (RSS):** $u_c(y) = \sqrt{\sum_{i=1}^N (c_i u_i)^2}$
- **Variance Contribution Share (%):** $h_i = \frac{(c_i u_i)^2}{u_c^2} \times 100\%$ (Sums strictly to $100.0\%$)
- **Welch-Satterthwaite Effective Degrees of Freedom:**
  $$\nu_{eff} = \frac{u_c^4}{\sum_{i=1}^N \frac{u_i^4}{\nu_i}}$$
- **Expanded Uncertainty:** $U = k \cdot u_c$ (With $k=2.00$ justified when $\nu_{eff} \ge 30$)
- **Metrological Rounding:** Expanded uncertainty $U$ rounded up to two significant digits, and the reported value rounded to the corresponding decimal place.

### 3.4 Calibration & Conformity
- **Least-Squares Fit:** $X_{DUT} = m \cdot X_{REF} + c$
  - **Zero Offset:** $c$
  - **Gain Error:** $(m - 1) \times 100\%$
  - **Residuals:** $r_i = X_{DUT,i} - (m \cdot X_{REF,i} + c)$
- **3-Band Conformity Check ($T = \pm 1.0\%$):**
  - **PASS:** $|E\%_i| < 0.8 \cdot T$
  - **MARGINAL:** $0.8 \cdot T \le |E\%_i| \le T$
  - **FAIL:** $|E\%_i| > T$
- **Guard-Banded Single-Point Acceptance:** $|E| + U \le T$

### 3.5 Drift & Tolerance Breach Forecasting
- **Linear Drift Regression:** $E(t) = a + b \cdot t$
- **Significance Condition:** $|b| > b_{threshold} \land p < 0.05$
- **Projected Tolerance Breach:** $t_{breach} = \frac{T - a}{b}$

---

## 🧠 4. Transparent Rule-Based Decision Engine (R1–R5)

The decision layer operates deterministically on computed metrology metrics without black-box ML:

| Rule ID | Rule Name | Condition Evaluated | Output Status | Engineering Action |
|---|---|---|---|---|
| **R1** | Uncertainty Check | $U > U_{allowable}$ ($25\text{ mV}$) | `HIGH UNCERTAINTY` | Result not fit for purpose; reduce dominant contributor. |
| **R2** | Conformity Check | $\|E\| > T \lor (\|E\| + U) > T$ ($50\text{ mV}$) | `CALIBRATION REQUIRED` | Adjust, correct, or withdraw instrument. |
| **R3** | Drift Check | History exists $\land \|b\| > b_{lim} \land p < 0.05$ | `POSSIBLE DRIFT` | Shorten calibration interval; schedule before breach. |
| **R4** | Repeatability Check | $s > s_{allowable}$ ($15\text{ mV}$) | `REPEATABILITY CONCERN` | Investigate connections, thermal settling, and noise. |
| **R5** | Default | None of R1 to R4 triggered | `MEASUREMENT ACCEPTABLE` | Release result; retain for drift history. |

### Why Transparent Rules Instead of Machine Learning?
1. **Verifiability:** Decisions can be checked by hand with a calculator by an examiner or auditor.
2. **No Training Data Dependency:** Real failure data is rare; training ML on 10 synthetic sessions produces misleading models.
3. **Metrological Alignment:** Limits ($U_{allow}$, $T$, $b_{lim}$) derive from physical specifications, not arbitrary loss functions.
4. **ISO/IEC 17025 Compliance:** Accreditation mandates traceable, deterministic conformity rules.
5. **Auditable Baseline:** Provides a benchmark against which future unsupervised anomaly detection can be evaluated.

---

## 💻 5. Repository Structure

```
IMUCA/
├── app.py                         # Streamlit interactive dashboard
├── requirements.txt               # Dependency specifications
├── README.md                      # Comprehensive project documentation
├── DEMO_GUIDE.md                  # 5-10 minute faculty demonstration walkthrough
├── .gitignore                     # Git ignore configuration
├── run_tests.py                   # Pytest test runner
│
├── data/
│   ├── demo_measurements.csv      # 10-point calibration sweep (0.5 V to 5.0 V)
│   ├── demo_single_point_10repeats.csv # 10 repeated observations at 5.000 V
│   ├── calibration_history.csv    # 10-session historical drift dataset
│   └── sample_invalid_data.csv    # Test dataset with corrupted/outlier values
│
├── src/
│   ├── __init__.py                # Package initialization
│   ├── loader.py                  # CSV ingestion and schema detection
│   ├── validator.py               # Algorithm 1a multi-layer validation & MAD outlier detection
│   ├── preprocessing.py           # Unit conversion and dataset formatting
│   ├── statistics.py              # Sample statistics (mean, s, s^2, standard error)
│   ├── errors.py                  # Absolute, relative, and percentage error calculation
│   ├── type_a.py                  # Type A standard uncertainty evaluation
│   ├── type_b.py                  # Type B systematic sources & distributions
│   ├── budget.py                  # Uncertainty budget compilation & dominant source ranking
│   ├── coverage.py                # Welch-Satterthwaite ν_eff & expanded uncertainty U
│   ├── calibration.py             # Calibration regression, offset/gain, 3-band conformity
│   ├── residuals.py               # Residual analysis and quantisation threshold checking
│   ├── drift.py                   # Within-run stability & between-session drift forecasting
│   ├── limits.py                  # Engineering limits dataclass
│   ├── actions.py                 # Structured recommendation synthesis
│   ├── rules.py                   # Transparent ordered rule engine (R1 to R5)
│   ├── figures.py                 # Plotly interactive engineering visualizations
│   └── report.py                  # Standalone HTML report generator
│
├── tests/
│   ├── standalone_tests.py        # Independent verification test runner
│   ├── test_statistics.py         # Descriptive statistics tests
│   ├── test_uncertainty.py        # Type A, Type B, Budget, and Coverage tests
│   ├── test_calibration.py        # Calibration curve, conformity, residuals tests
│   ├── test_drift.py              # Within-run trend and drift regression tests
│   ├── test_decision_engine.py    # Decision rules R1-R5 tests
│   └── test_validation.py         # CSV loading, MAD outliers, validation tests
│
└── reports/
    └── generated_reports/         # Output directory for exported HTML reports
```

---

## 🚀 6. Installation & Execution

### Prerequisites
- Python 3.9+ (Python 3.10 to 3.14 supported)
- pip package manager

### Step 1: Clone or Navigate to Directory
```bash
cd "d:\IMUCA MNI"
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Run Automated Verification Tests
```bash
python -u tests/standalone_tests.py
```
*(All 6 test suites / 20 test cases will execute and verify against golden reference values).*

### Step 4: Launch the Streamlit Application
```bash
python -m streamlit run app.py
```
The application will open in your browser at: `http://localhost:8501`

---

## 🎯 7. Demonstration Scenarios

### Demo A — Single Session (Default)
- **Input:** 10 repeat readings at 5.000 V + 10-point calibration sweep. No history.
- **Computed Outputs:** Mean = $5.021\text{ V}$, $s = 9.944\text{ mV}$, $u_A = 3.145\text{ mV}$, $u_c = 5.274\text{ mV}$, $U = 10.55\text{ mV}$ (Reported: $(5.021 \pm 0.011)\text{ V}$).
- **Dominant Contributor:** Repeatability ($35.6\%$ of variance).
- **Sweep Result:** 8 PASS, 1 MARGINAL (1.0 V), 1 FAIL (0.5 V).
- **Decision Engine:** Rule R5 Default fires $\rightarrow$ **MEASUREMENT ACCEPTABLE** (Headline: `ACCEPTABLE`).
- **Recommendation:** Release result and retain for drift history. Restrict operating range above 1.5 V or apply documented offset/gain correction.

### Demo B — With Drift History
- **Input:** Single session data + 10-session historical calibration error log.
- **Computed Outputs:** Drift slope $b = +1.10\text{ mV/session}$, $s(b) = 0.085\text{ mV}$, $R^2 = 0.954$, $p = 1.3 \times 10^{-6}$.
- **Projected Breach:** Session 28 ($+50\text{ mV}$ limit reached 18 sessions ahead).
- **Decision Engine:** Rule R3 fires $\rightarrow$ **POSSIBLE DRIFT** (Headline: `ATTENTION REQUIRED`).
- **Recommendation:** Shorten calibration interval and schedule recalibration before session 24.

---

## 🧪 8. Golden Reference Verification Benchmark

| Metric | Golden Reference Value | IMUCA Computed Value | Error / Deviation | Status |
|---|---|---|---|---|
| Sample Mean $\bar{x}$ | $5.021\text{ V}$ | $5.021000\text{ V}$ | $<0.0001\%$ | ✅ Exact |
| Sample Std Dev $s$ | $9.944\text{ mV}$ | $9.944289\text{ mV}$ | $<0.003\%$ | ✅ Exact |
| Type A Uncertainty $u_A$ | $3.145\text{ mV}$ | $3.144660\text{ mV}$ | $<0.01\%$ | ✅ Exact |
| Display Resolution $u_1$ | $2.887\text{ mV}$ | $2.886751\text{ mV}$ | $<0.01\%$ | ✅ Exact |
| DUT Specification $u_2$ | $2.899\text{ mV}$ | $2.898886\text{ mV}$ | $<0.01\%$ | ✅ Exact |
| Reference Standard $u_3$ | $1.000\text{ mV}$ | $1.000000\text{ mV}$ | $0.0\%$ | ✅ Exact |
| Ambient Tempco $u_4$ | $0.435\text{ mV}$ | $0.434831\text{ mV}$ | $<0.04\%$ | ✅ Exact |
| Combined Uncertainty $u_c$ | $5.274\text{ mV}$ | $5.274291\text{ mV}$ | $<0.01\%$ | ✅ Exact |
| Effective DOF $\nu_{eff}$ | $71.2 \approx 71$ | $71.21$ | $<0.02\%$ | ✅ Exact |
| Expanded Uncertainty $U$ | $10.55\text{ mV}$ | $10.54858\text{ mV}$ | $<0.01\%$ | ✅ Exact |
| Reported String | `(5.021 ± 0.011) V` | `(5.021 ± 0.011) V` | $0.0\%$ | ✅ Exact |
| Calibration Offset $c$ | $+6.67\text{ mV}$ | $+6.666667\text{ mV}$ | $<0.05\%$ | ✅ Exact |
| Gain Error $(m-1)$ | $+0.303\%$ | $+0.303030\%$ | $<0.01\%$ | ✅ Exact |
| Linearity $R^2$ | $0.999997$ | $0.999997$ | $<0.0001\%$ | ✅ Exact |
| Peak Residual Error | $4.24\text{ mV}$ | $4.242424\text{ mV}$ | $<0.06\%$ | ✅ Exact |
| Drift Slope $b$ | $+1.10\text{ mV/session}$ | $+1.103030\text{ mV/s}$ | $<0.3\%$ | ✅ Exact |
| Drift Significance $p$ | $1.3 \times 10^{-6}$ | $1.299 \times 10^{-6}$ | $<0.1\%$ | ✅ Exact |
| Projected Breach Session | Session 28 | Session 27.7 ($\approx 28$) | $<0.5\%$ | ✅ Exact |

---

## 🔮 9. Future Scope & Limitations

1. **Hardware Interfacing (Phase 2):** Connect physical multi-meters and microcontrollers (ESP32/INA219/DS18B20) via UART/Serial streams using `MeasurementStreamBuffer`.
2. **Automated Environmental Logging:** Incorporate temperature/humidity sensors to convert estimated Type B ambient variations into live Type A measurements.
3. **Multi-Channel DAQ:** Support simultaneous multi-point sensor calibration.
4. **Machine Learning Anomaly Detection (Phase 3):** Implement unsupervised autoencoders and time-series models for nonlinear drift forecasting once sufficient empirical history is recorded.

---

## 📦 10. Autonomous Metrology Foundation (`src/imuca`)

The modular foundation under `src/imuca` expands IMUCA into a full three-measurand metrology package:

| Measurand | Nominal Range | Model | SI Conversion |
| :--- | :--- | :--- | :--- |
| **DC Voltage** | $0.0\text{ V} - 26.0\text{ V}$ | Direct resistive divider / ADC | $\text{V}$ |
| **DC Current** | $0.0\text{ mA} - 3200.0\text{ mA}$ | Indirect Ohm's law ($I = V_{shunt} / R_{shunt}$) | $\text{A} = \text{mA} \times 10^{-3}$ |
| **Temperature** | $-55.0\ ^\circ\text{C} - +125.0\ ^\circ\text{C}$ | Bandgap digital converter | $\text{K} = \text{degC} + 273.15$ |

### Running the Test Suite
```bash
python -m pytest -v
```
*Current test suite: **165 passing automated tests** (including independent analytical numerical verification cases covering GUM propagation, Welch-Satterthwaite, NIST zero-MAD outlier handling, ILAC-G8 conformity, lifecycle hysteresis, confirmed error attribution, and settling suppression).*

### Running the Reproducible Baseline Experiment
```bash
python scripts/run_baseline_experiment.py
```
This executes the automated benchmark across Voltage, Current, Temperature, and Injected Fault scenarios, exporting JSON reports, publication plots, and Markdown summaries to `results/`.

---

## 🛡️ 11. Scientific Code Audit & Verification (October 2026)

An independent scientific code audit and mathematical verification was conducted on the Milestone 1 foundation:
- **Audit Findings:** Catalog of 8 verified defects (Critical/High/Medium/Low) and their remediation in [`docs/AUDIT_FINDINGS.md`](docs/AUDIT_FINDINGS.md).
- **Remediation Log:** Step-by-step diff log and verification test commands in [`docs/AUDIT_REMEDIATION_LOG.md`](docs/AUDIT_REMEDIATION_LOG.md).
- **Scientific Verification:** Rigorous mathematical groundings (GUM JCGM 100:2008, Monte Carlo JCGM 101:2008, ILAC-G8) in [`docs/SCIENTIFIC_VERIFICATION.md`](docs/SCIENTIFIC_VERIFICATION.md).
- **Hardware Integration Readiness:** Sensor specifications, UART framing protocol, and hardware readiness matrix in [`docs/HARDWARE_READINESS.md`](docs/HARDWARE_READINESS.md).



---

## 🧪 12. Synthetic Benchmark Suite v2 & ML Readiness (October 2026)

A configurable, reproducible synthetic dataset suite (50 scenarios, 147,865 records, 214 independent runs) now exercises the conventional pipeline across DC voltage, DC current (shunt model with TCR and optional self-heating) and temperature (first-order sensor lag), plus an 11-class fault-detection benchmark. Every record keeps the DUT observation, a simulated reference reading (with its own error model) and ground truth in separate columns, with per-record fault labels and calibration / validation / test partitions assigned per run. All parameters are simulation assumptions, not sensor specifications.

```bash
python scripts/generate_synthetic_suite.py           # generate (unchanged files are left untouched)
python scripts/generate_synthetic_suite.py --verify  # bit-identical regeneration check against the manifest
python scripts/run_synthetic_benchmark.py            # conventional baseline -> results/synthetic_benchmark_<timestamp>/
python -m pytest -p no:anyio                         # 89 tests (63 existing + 26 dataset-validation tests)
```

- Specification: [`docs/SYNTHETIC_DATA_SPECIFICATION.md`](docs/SYNTHETIC_DATA_SPECIFICATION.md)
- Catalog (files, record counts, seeds, checksums): [`docs/DATASET_CATALOG.md`](docs/DATASET_CATALOG.md)
- ML benchmark plan (specification only, no models trained): [`docs/ML_BENCHMARK_PLAN.md`](docs/ML_BENCHMARK_PLAN.md), machine-readable in `config/ml_benchmark_spec.json`

The Milestone-1 generator, its four datasets and `scripts/run_baseline_experiment.py` are unchanged. Scenario CSVs hold several acquisition runs, so ingest them run by run with `src.imuca.synthetic_suite.iter_run_csv_buffers`.

---

## 🔍 13. ML Fault Detection & CUSUM Tuning (Milestone 4, research only)

Causal-feature gradient-boosted trees and an Isolation Forest are compared with the conventional per-segment detector on the synthetic suite. Integrity faults stay on a separate track handled by deterministic rules. The existing CUSUM is re-tuned on calibration and validation runs only. Nothing is integrated into the dashboard or the decision engine.

```bash
pip install -r requirements.txt            # adds scikit-learn
python scripts/run_ml_fault_detection.py   # -> results/ml_fault_detection_<timestamp>/
```

Headline (synthetic test runs): no detector dominates. GBT is best on voltage at a higher false-alarm rate; the conventional detector is best on spikes and abrupt changes; both ML models cut false alarms during temperature lag transients. The tuned CUSUM (k = 0.5, h = 15) has 1/39 false alarms and detects 8/9 drift runs on test, versus 39/39 false alarms for the old setting. Details and limitations: [`docs/ML_FAULT_DETECTION.md`](docs/ML_FAULT_DETECTION.md).

---

## 🧩 14. Hybrid Fault Detector (Milestone 5, research only)

Integrity rules, the existing segment detector (spikes, abrupt changes), a targeted GBT or stuck rule (offset, gain, stuck) and a tuned CUSUM (drift) are combined with one alarm per record and episode-level counting. Everything is evaluated once on a **fresh** synthetic suite (`data/synthetic_v3/`, new seed roots), after the settings were frozen on validation runs.

```bash
python scripts/generate_synthetic_suite.py --config config/synthetic_suite_v3_config.json --output-root data/synthetic_v3 --catalog docs/DATASET_CATALOG_V3.md
python scripts/run_hybrid_fault_detection.py      # -> results/hybrid_fault_detection_<timestamp>/
```

Test result (synthetic): hybrid event F1 0.81 (voltage) and 0.85 (current), the highest of all detectors but with bootstrap intervals overlapping the best single detector. For temperature the hybrid (0.65) does not beat GBT (0.68). Settling false alarms for temperature fall from 14.4/h to 2.0/h. Details: [`docs/HYBRID_FAULT_DETECTION.md`](docs/HYBRID_FAULT_DETECTION.md).

---

## 🔁 15. Milestone 6: hybrid improvement loop and independent re-evaluation (research only)

Alarm lifecycle and attribution, temperature transient handling, threshold and current-drift tuning, stronger evaluation, and idempotent dataset generation. Development used v3 calibration and validation runs only. The frozen detector was then scored **once** on a fresh suite (`data/synthetic_v4/`) generated after freezing.

```bash
python scripts/run_hybrid_iteration.py validate --profile cycle4_edges_resolved --tag <name>   # development (v3 cal/val only)
python scripts/run_hybrid_iteration.py freeze --profile cycle4_edges_resolved                 # writes results/hybrid_frozen_<ts>/
python scripts/generate_synthetic_suite.py --config config/synthetic_suite_v4_config.json --output-root data/synthetic_v4 --catalog docs/DATASET_CATALOG_V4.md
python scripts/run_hybrid_iteration.py final --frozen results/hybrid_frozen_20261026_123033 --suite-config config/synthetic_suite_v4_config.json --data-root data/synthetic_v4
```

Independent result (synthetic):
- **Temperature:** the new hybrid improves on Milestone 5 (event F1 0.767 vs 0.655; paired difference +0.11 [+0.05, +0.17], with fewer false alarms).
- **Voltage and current:** the gain is not established, and current false alarms rose.
- **Overall:** the hybrid is not shown superior to the best single detector.

Generators are now idempotent: re-running them changes no files. Details: [`docs/HYBRID_MILESTONE6.md`](docs/HYBRID_MILESTONE6.md).

---

## 🎯 16. Milestone 7: Autonomous Reliability Improvement Loop & Independent Confirmatory Evaluation (research only)

Addresses the five remaining reliability problems: current-channel false-alarm and spike trade-offs, temperature post-fault alarm overhang, voltage settling phase false alarms, persistent fault misclassification, and strict evaluation reproducibility. Development was restricted to v3 calibration/validation runs. Final code and selection rules were frozen and hashed (`results/hybrid_frozen_20261027_210333/`) before generating a fresh synthetic suite (`data/synthetic_v5/`, seeds: 62015028 / 72025028 / **84055028**, 85 scenarios, 166,278 records). The independent test split was scored strictly once.

```bash
# 1. Run all regression tests
python -m pytest tests/ -v

# 2. Frozen Milestone 7 evaluation commands (reproducibility)
python scripts/run_hybrid_iteration.py freeze --profile m7_final_freeze
python scripts/generate_synthetic_suite.py --config config/synthetic_suite_v5_config.json --output-root data/synthetic_v5 --catalog docs/DATASET_CATALOG_V5.md
python scripts/run_hybrid_iteration.py final --frozen results/hybrid_frozen_20261027_210333 --suite-config config/synthetic_suite_v5_config.json --data-root data/synthetic_v5

# 3. Post-hoc paired comparisons (on identical independent test runs)
python scripts/posthoc_paired_comparison.py results/hybrid_final_20261027_212107 data/synthetic_v5 hybrid_m7 hybrid_m6
python scripts/posthoc_paired_comparison.py results/hybrid_final_20261027_212107 data/synthetic_v5 hybrid_m7 hybrid_m5
```

### Confirmatory Test Results (Synthetic Suite v5, Scored Once)

- **Fault Classification Breakthrough:** In-episode level-shift testing resolved the persistent alarm truncation defect. Current classification accuracy jumped from **0.804** (M6) to **0.892** [0.83, 0.93] (gain change **7/9** vs 2/9, offset shift **10/15** vs 4/15). Voltage classification reached **0.828** and temperature reached **0.798**.
- **Current Reliability:** Spike recall recovered to **64/72** (95% Wilson CI [0.80, 0.94], matching M5 baseline) by pairing MAD 6.0 with non-stationary curvature filtering, maintaining 9/9 drift detection at 72 s median delay.
- **Temperature Lifecycle Overhang:** Hysteresis clearance ($W=60, z=2.0$) cut post-fault overhang by **29%** (12.9 records/h vs 18.1 in M6 and 38.5 in M5), while preserving the large $F_1$ gain over M5 (0.750 vs 0.598, $P \le 0.000$).
- **Voltage Settling Suppression:** Settling phase false alarms suppressed during non-stationary transitions without masking genuine curvature spikes.
- **Reproducibility:** 165 automated tests passing; generator idempotency and historical file protection verified bit-identically across v2, v3, v4, and v5.

Full architectural decisions, paired statistics, and limitations: [`docs/HYBRID_MILESTONE7.md`](docs/HYBRID_MILESTONE7.md).

---

## 🚀 17. Milestone 8: Final Autonomous Integration, Unified Dashboard & Release Loop

The final software milestone unifies the entire IMUCA stack into an integrated application connecting the 12-stage metrology computational pipeline, JCGM 100:2008 GUM uncertainty analysis, calibration regression, data-quality checks, frozen Milestone 7 multi-track fault detection, synthetic datasets, and an engineering-grade digital dashboard.

### 17.1 How to Launch the Application

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Launch the Unified Digital Dashboard
streamlit run app.py
```

### 17.2 Dual Application Modes (100% Backward Compatible)

The Streamlit interface (`app.py`) provides an Application Mode selector in the left sidebar:

1. **🔬 Unified Multi-Channel System (10 Engineering Sections):**
   - **Section 1 (Overview):** Active operating state, simulation/hardware status banners, KPI cards, and Mermaid data-flow architecture.
   - **Section 2 (Live & Replayed Measurements):** Plotly time-series plots for Voltage, Current, and Temperature with engineering units, selectable time windows, setpoint markers, and isolated ground-truth overlay.
   - **Section 3 (Metrology & Calibration):** Indicated vs reference measurements, error curve, fitted linear/polynomial calibration regression line, $R^2$, and residual diagnostics plot with control bounds.
   - **Section 4 (Uncertainty Analysis):** GUM Table 12.1 breakdown table, horizontal variance share bar chart, combined uncertainty $u_c$, Welch-Satterthwaite $\nu_{\mathrm{eff}}$, Student's $t$ coverage factor $k$, expanded uncertainty $U$, and documented assumptions & limitations box.
   - **Section 5 (Data Quality):** Multi-layer audit of missing samples, sequence gaps, duplicate sequences, out-of-order timestamps, status errors (`INA219_OVF`, `DS18B20_CRC_ERR`), and sampling jitter diagnostics.
   - **Section 6 (Fault Detection):** Comparative multi-track alarm view (Integrity, Segment MAD, ML GBT, Tuned CUSUM, Hybrid M7) and aggregated alarm episodes lifecycle table.
   - **Section 7 (Historical Analysis):** Scenario browser across Suites v2, v3, v4, v5, metadata viewer, and manifest verification.
   - **Section 8 (Performance Evaluation):** Scorecard from held-out 85-scenario Suite v5 confirmatory evaluation (Event F1: Voltage 0.966, Current 0.941, Temperature 0.957).
   - **Section 9 (Hardware Readiness):** Physical connection status (`DISCONNECTED`), Hardware Readiness Matrix, input channel mapping, and interactive CCITT CRC-16 telemetry frame calculator and validator.
   - **Section 10 (Diagnostics & Export):** Execution audit log, downloadable processed CSV, JSON uncertainty budget, and HTML metrology report.

2. **⚡ Single-Point / Sweep DC Voltage Analyzer (Review 1 Baseline):**
   - Preserves 100% of the validated single-point and sweep DC voltage workflow.
   - Interactive **Demo A (Single Session)** and **Demo B (With History)** quick presets respond dynamically with 9 tabs and automated HTML reports.

### 17.3 Hardware Adapter Boundary & Serial Protocol

The interface between physical acquisition and metrology analysis is encapsulated in [`src/imuca/hardware_adapter.py`](src/imuca/hardware_adapter.py):

- **Framing:** `$IMUCA,<seq_id>,<elapsed_ms>,<voltage_mv>,<current_ma>,<temp_c>,<status_flags>*<crc16>\r\n`
- **Integrity Check:** CCITT CRC-16 (polynomial $0\mathrm{x}1021$, initial $0\mathrm{xFFFF}$) over all payload bytes between `$` and `*`.
- **Status Bitmask:** 8-bit integer decoding `INA219_OVF` ($0\mathrm{x}01$), `INA219_COMM_ERR` ($0\mathrm{x}02$), `DS18B20_CRC_ERR` ($0\mathrm{x}04$), `DS18B20_DISCONN` ($0\mathrm{x}08$), `RANGE_EXCEEDED` ($0\mathrm{x}10$), `CLOCK_UNCERTAIN` ($0\mathrm{x}20$).
- **Strict Demarcation:** The dashboard accurately displays **`DISCONNECTED` / `SIMULATION MODE`** until physical hardware is connected. Live values are never fabricated.

### 17.4 Complete Regression Test Suite

```bash
python -m pytest tests/ -v
# Output: 189 passed in 114s (0:01:54)
```

The test suite verifies:
- Mathematical metrology and numerical algorithms (`tests/test_audit_numerical_cases.py`, `tests/test_uncertainty.py`, `tests/test_statistics.py`, `tests/test_calibration.py`, `tests/test_drift.py`, `tests/test_decision_engine.py`).
- Hardware adapter, framing, CRC-16, and bitmasks (`tests/test_hardware_adapter.py`).
- End-to-end multi-channel metrology pipeline (`tests/test_orchestrator.py`).
- All 10 dashboard workflows (`tests/test_dashboard_integration.py`).
- Headless Streamlit rendering of both application modes (`tests/test_streamlit_app.py`).
- Milestone 7 multi-track hybrid detector and lifecycle (`tests/test_hybrid_detector.py`, `tests/test_hybrid_lifecycle.py`, `tests/test_hybrid_evaluation.py`).
- Synthetic suite generation and bit-identical idempotency (`tests/test_generation_idempotency.py`, `tests/test_synthetic_suite.py`).

Release documentation and laboratory validation next steps: [`results/final_release_20261027/RELEASE_REPORT.md`](results/final_release_20261027/RELEASE_REPORT.md).

---

## 🌐 18. Professional 3D Digital Twin SCADA Dashboard

IMUCA features a professional, interactive **3D Digital Twin SCADA Dashboard** for industrial metrology, precision multi-channel sensing, and intelligent fault diagnosis.

### 18.1 SCADA Visual Design Philosophy
Inspired by modern power-system control rooms and mission-critical engineering SCADA interfaces:
- **Dark Graphite Canvas:** `#0b0f19` deep obsidian baseplate with muted `#1e293b` fine coordinate grid lines.
- **Radiant Status Lighting:**
  - `NOMINAL` / In-Control: Cyan (`#00f0ff`) and Sky Blue (`#0ea5e9`).
  - `WARNING` / Jitter / Drift: Amber (`#f59e0b` / `#fbbf24`).
  - `FAULT` / Injected or Detected Anomaly: Crimson (`#ef4444` / `#dc2626`).
  - `PRIMARY STANDARD`: Traceable Gold (`#eab308` / `#facc15`).
- **Physical Demarcation Barrier:** A translucent vertical acrylic plane ($X = 3.5$) that visually and architecturally isolates the **Physical Acquisition Layer (Hardware / Transducers)** from the **Software Metrology & Fault Inference Pipeline**.

### 18.2 Spatial Geometry & Components
The interactive 3D WebGL scene (`src/imuca/digital_twin_3d.py`) models the complete instrumentation testbench:
1. **Embedded DAQ Controller Unit:** Central aluminum chassis housing 32-bit ARM Cortex-M architecture, cooling heatsink fins, status beacon LED, and front terminal blocks.
2. **DC Voltage Transducer (SUT):** Attenuator / voltage divider network with high-voltage Red/Black binding posts, 12-bit SAR ADC model (4 mV LSB), and channel status beacon.
3. **Current Shunt Channel (SUT):** 4-wire Kelvin shunt block ($0.100\ \Omega \pm 0.5\%$, heavy copper busbars, brass M4 terminal screws), TI INA219 shunt ADC model (10 $\mu$V LSB), and TCR temperature compensation model.
4. **Temperature Probe & Thermal Mass:** Cylindrical Maxim DS18B20 1-Wire probe inserted into a finned aluminum thermal heatsink/source, 12-bit programmable quantization ($0.0625\ ^\circ\text{C}$ LSB).
5. **Traceable Primary Reference Standard:** 8.5-digit precision benchtop Multimeter (Fluke 8508A / Keysight standard) with ISO/IEC 17025 gold calibration certificate seal, green LCD readout, and gold binding posts — strictly distinguished from the sensor under test.
6. **Telemetry Conduits & Data Flow:** Glowing 3D bus lines with directional diamond pulses representing incoming `$IMUCA` telemetry frames.

### 18.3 Replay Engine & Synchronized Telemetry
The digital twin connects directly to the validated IMUCA pipeline via `src/imuca/replay_engine.py`:
- **Deterministic Time Scrubbing:** High-precision slider stepping through recorded sample indices ($t_i$).
- **VCR Playback Controls:** Play/Pause, Step Forward (+1, +10), Step Backward (-1, -10), Reset to start ($t = 0$).
- **Variable Playback Speed:** `1x`, `2x`, `5x`, `10x`.
- **Live KPI Telemetry Cards:** Synchronized Voltage, Current, Temperature, Active Alarm Category, GUM Expanded Uncertainty ($U_{95}$), and ILAC-G8 Guard-Banded Conformity status.
- **Component Drill-Down:** Clicking or selecting any 3D component instantly displays its metrological specifications, transducer parameters, live indicated reading vs reference standard, calibration residuals, GUM uncertainty contributions, and multi-track detector status.
- **Oscilloscope Rolling Trend:** Dark-graphite rolling trend chart displaying the indicated measurement curve, reference standard trace, active alarm intervals, and a moving vertical playback head.

### 18.4 Multi-Track Fault Detection Integration
The 3D Digital Twin visualizes all 5 validated fault detection tracks in real time:
1. **Track 1 (Data Integrity):** CCITT CRC-16 checksum verification, non-finite values, and range violations.
2. **Track 2 (Segment MAD):** Non-parametric median absolute deviation outlier filter ($z > 3.5$).
3. **Track 3 (ML GBT Classifier):** Gradient Boosted Decision Trees trained on 14 statistical/spectral features.
4. **Track 4 (Tuned CUSUM):** Sequential drift detection monitor with Neyman-Pearson calibration.
5. **Track 5 (Hybrid M7 Fusion):** Multi-track temporal state machine with hysteresis alarm clearance.

### 18.5 Application Launch & Navigation
Launch the application locally with:
```bash
python -m streamlit run app.py
```
Or with custom port:
```bash
python -m streamlit run app.py --server.port 8501
```

In the left sidebar, the **Application Mode** selector allows instant toggling between:
1. **🌐 3D Digital Twin Metrology & SCADA Console (Featured / Default)**
2. **🔬 Unified Multi-Channel System (10 Engineering Sections)**
3. **⚡ Single-Point / Sweep DC Voltage Analyzer (Review 1 Baseline)**

### 18.6 Regression Test Verification
```bash
python -m pytest tests/ -v
# Output: 197 passed in 87s (0:01:27)
```
All 197 tests pass with zero warnings or regressions.



