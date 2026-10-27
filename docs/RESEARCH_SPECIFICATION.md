# IMUCA — Research Specification

## 1. Problem Statement

Low-cost instrumentation platforms based on microcontroller hardware (such as ESP32/ARM Cortex and commodity IC sensors like the INA219 current/power monitor and DS18B20 digital temperature probe) are increasingly deployed in field measurement, environmental telemetry, and industrial energy auditing. However, these systems are typically treated as black-box data loggers. In conventional engineering practice:

1. Bare digital readings are recorded without rigorous, traceable quantification of measurement uncertainty.
2. Calibration corrections, when performed, are often evaluated on the same points used for regression fitting, causing severe data leakage and overoptimistic accuracy claims.
3. Sensor aging, temperature-induced drift, and sudden communication drops are either ignored or masked through silent data deletion and zero-substitution.
4. Anomaly detection is often approached using complex, non-interpretable machine learning (ML) models before establishing an auditable, metrological baseline.

This creates an acute reliability gap where decision-makers cannot assess whether an observed variation reflects physical process dynamics or unquantified instrument degradation.

---

## 2. Research Questions (RQ)

- **RQ1**: To what extent does first-order GUM (JCGM 100:2008) uncertainty propagation combined with Welch-Satterthwaite effective degrees of freedom improve the defensibility of decision rules (ILAC-G8) in low-cost measurement systems compared to simple tolerance thresholding?
- **RQ2**: Does strict out-of-sample (train/validation) calibration modeling with statistical order selection (F-test and AIC/BIC) prevent overfitting in low-cost multi-measurand instrumentation?
- **RQ3**: How effectively can non-destructive statistical screening (Median Absolute Deviation modified Z-scores, sequence checks, and CUSUM change detection) identify instrument faults, sensor dropouts, and gradual aging drift without altering raw measurement records?
- **RQ4**: What baseline accuracy, repeatability, and drift performance bounds can be established using conventional metrology methods before introducing machine learning models?

---

## 3. Scope and Measurands

The immediate scope of the IMUCA metrology foundation covers three fundamental measurands:

| Measurand | Nominal Range | Primary Physical Mechanism / Model | SI Base Unit |
| :--- | :--- | :--- | :--- |
| **DC Voltage** | $0.0\text{ V}$ to $26.0\text{ V}$ | Direct resistive divider / ADC sampling | $\text{V}$ |
| **DC Current** | $0.0\text{ mA}$ to $3200.0\text{ mA}$ | Indirect Ohm's law: $I = V_{shunt} / R_{shunt}$ | $\text{A}$ ($10^{-3}\text{ A}$) |
| **Temperature** | $-55.0\ ^\circ\text{C}$ to $+125.0\ ^\circ\text{C}$ | Bandgap digital converter (DS18B20) | $\text{K}$ ($T_K = T_C + 273.15$) |

### Explicit Exclusions for Phase 1
- **Machine Learning (ML)**: Neural networks, Random Forests, LightGBM, and reinforcement learning are explicitly deferred. A rigorous conventional metrology baseline must precede any ML evaluation.
- **Hardware-in-the-Loop Validation**: The current phase implements and verifies the complete software-only metrology engine using reproducible synthetic scenarios and offline CSV pipelines. Physical hardware characterization will be performed once firmware integration is executed.

---

## 4. Research Hypotheses

- **$H_1$ (Calibration Generalisation)**: Linear calibration fitted solely on training points will achieve $\ge 80\%$ MAE reduction on held-out validation data when systematic gain and offset dominate sensor errors.
- **$H_2$ (Conformity Conservatism)**: ILAC-G8 guard-banded conformity assessment will prevent false acceptances near specification boundaries by classifying observations within $[USL - U, USL]$ as `CONDITIONAL` rather than `PASS`.
- **$H_3$ (Non-Destructive Integrity)**: Non-destructive data quality assessment using MAD modified Z-scores ($|M_i| > 3.5$) and sequence audit checks will achieve $\ge 80\%$ recall against injected sensor anomalies while preserving $100\%$ of raw observations for metrological trace audit.

---

## 5. Baselines and Benchmark Methodology

All future algorithmic extensions (including ML drift forecasting and adaptive filtering) will be evaluated against the conventional metrological baselines established in this framework:
1. **Uncalibrated Instrument Baseline**: Raw DUT measurements evaluated directly against reference standards.
2. **Standard Least-Squares Linear Calibration**: Two-parameter $(a_0, a_1)$ linear regression with training/validation separation.
3. **First-Order JCGM GUM Uncertainty Budget**: Type A (repeatability) + Type B (resolution, manufacturer spec, reference standard, thermal effects).
4. **CUSUM and Linear Drift Forecast**: Statistical cumulative sum for step change detection and linear slope forecasting for remaining time to tolerance breach.
