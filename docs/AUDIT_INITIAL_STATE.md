# IMUCA — Audit Initial State Report

**Date & Time**: 2026-10-25 12:05:00 UTC  
**Auditor**: Metrology Software Systems Auditor & Scientific Validation Engineer  
**Host Environment**: Windows 11 / Python 3.14.7 (64-bit) / pytest 9.1.1  

---

## 1. Environment & Package Discovery

| Parameter | Observed State | Notes |
| :--- | :--- | :--- |
| **Python Version** | Python 3.14.7 (C:\Users\sunda\AppData\Local\Python\pythoncore-3.14-64\python.exe) | Confirmed via CLI |
| **NumPy Version** | 2.5.2 | Supports new 2.x scalar type hierarchies |
| **Pandas Version** | 3.0.5 | Confirmed |
| **SciPy Version** | 1.18.1 | Confirmed |
| **Matplotlib Version** | 3.11.1 | Agg headless backend active |
| **Pytest Version** | 9.1.1 | Confirmed |
| **Git Repository** | Not initialized (`.git` absent in folder) | Local filesystem project directory |

---

## 2. Repository Structure Analysis

```
d:/IMUCA MNI/
├── pyproject.toml                         # Project package configuration & pytest setup
├── config/
│   └── default_config.json               # Metrological parameter thresholds
├── docs/                                 # Research specifications & documentation
│   ├── RESEARCH_SPECIFICATION.md
│   ├── SYSTEM_ARCHITECTURE.md
│   ├── METROLOGY_METHODS.md
│   ├── UNCERTAINTY_BUDGETS.md
│   ├── DATA_SCHEMA.md
│   └── VALIDATION_PLAN.md
├── data/
│   ├── raw/                              # Empty directory for raw inputs
│   ├── processed/                        # Processed CSVs from baseline runs
│   ├── synthetic/                        # Synthetic benchmark datasets & JSON metadata
│   ├── demo_measurements.csv             # Legacy single-measurand demo CSV
│   ├── demo_single_point_10repeats.csv   # Legacy single-measurand repeat observations
│   ├── sample_invalid_data.csv           # Legacy validation stress dataset
│   └── calibration_history.csv           # Legacy 10-session drift log
├── src/
│   ├── imuca/                            # Target modular metrology package
│   │   ├── __init__.py
│   │   ├── schema.py
│   │   ├── data_ingestion.py
│   │   ├── data_quality.py
│   │   ├── synthetic_data.py
│   │   ├── measurement_metrics.py
│   │   ├── uncertainty.py
│   │   ├── calibration.py
│   │   ├── validation.py
│   │   └── reporting.py
│   └── [legacy flat files: statistics.py, type_a.py, budget.py, calibration.py, app.py, etc.]
├── tests/
│   ├── standalone_tests.py               # Pure-python assertions
│   ├── test_schema.py                    # Schema, immutability, conversions
│   ├── test_data_quality.py              # MAD outliers, sequence integrity, confusion matrix
│   ├── test_measurement_metrics.py       # Metrics, Bessel's correction, zero guard
│   ├── test_uncertainty.py               # GUM budget, Type A/B, shunt model, Monte Carlo
│   ├── test_calibration.py               # Calibration regression, train/test split, F-test
│   ├── test_validation.py                # Conformity, drift rate, breach forecast
│   ├── test_statistics.py                # Legacy statistics tests
│   ├── test_decision_engine.py           # Legacy decision engine tests
│   └── test_drift.py                     # Legacy drift tests
├── scripts/
│   └── run_baseline_experiment.py        # 4-stage baseline benchmark runner
└── results/
    ├── milestone1_baseline_backup/       # Secure backup of initial results
    └── [EXP_01, EXP_02, EXP_03 artifacts: reports, markdown summaries, PNG plots]
```

---

## 3. Initial Baseline Test Execution

Command executed:
```bash
python -m pytest -v
```

**Results**:
- **Collected**: 46 items across 10 test modules.
- **Passed**: 46 (100%).
- **Failed**: 0.
- **Skipped**: 0.
- **Execution Time**: 1.25 seconds.

---

## 4. Initial Baseline Experiment Execution

Command executed:
```bash
python scripts/run_baseline_experiment.py
```

**Results Recorded**:
1. **Experiment 1 (DC Voltage Calibration & GUM Budget)**:
   - Uncalibrated Bias: $+10.404\text{ mV}$, MAE: $10.404\text{ mV}$, RMSE: $10.827\text{ mV}$.
   - Linear Calibration ($R^2 = 0.999999$): Held-out MAE reduction: $91.3\%$, RMSE reduction: $89.9\%$.
   - Combined Uncertainty $u_c$: $3.023\text{ mV}$, Expanded $U (k=2.0)$: $6.046\text{ mV}$.
   - Reported Result: `(5.0000 +/- 0.0061) V (k=2.00, 95% confidence)`.
   - Dominant Contributor: DUT Specification Tolerance ($91.2\%$).
2. **Experiment 2 (DC Current Shunt Model & Calibration)**:
   - Uncalibrated Bias: $+30.68\text{ mA}$, MAE: $30.68\text{ mA}$, RMSE: $31.95\text{ mA}$.
   - Linear Calibration: Held-out MAE reduction: $98.9\%$.
   - Shunt Model Combined Uncertainty $u_c(I)$: $5.03\text{ mA}$, Expanded $U(k=2)$: $10.06\text{ mA}$.
   - Dominant Contributor: Shunt Resistor Tolerance ($98.8\%$).
3. **Experiment 3 (Temperature Drift & Breach Forecast)**:
   - Linear Drift Rate: $+14.747\text{ mK/s}$ ($53.09\ ^\circ\text{C/hour}$, $p = 2.615 \times 10^{-220}$).
   - Forecasted Time-to-Breach: $42.4\text{ seconds}$.
   - CUSUM Shift Detected: True.
   - Temperature Expanded Uncertainty $U(k=2)$: $\pm 0.520\ ^\circ\text{C}$.
4. **Experiment 4 (Fault Detection Benchmark)**:
   - Confusion Matrix: $\text{TP} = 10, \text{FP} = 3, \text{TN} = 137, \text{FN} = 0$.
   - Precision: $76.9\%$, Recall: $100.0\%$, False Alarm Rate: $2.14\%$, Missed Detection Rate: $0.00\%$, F1-Score: $0.870$.

---

## 5. Files Requiring Strict Preservation

1. `data/*.csv`: Historical demo datasets (`demo_measurements.csv`, `demo_single_point_10repeats.csv`, `sample_invalid_data.csv`, `calibration_history.csv`) used by existing demo dashboard and legacy unit tests.
2. `app.py`: Interactive Streamlit visualization application.
3. `src/*.py`: Legacy flat modules (`statistics.py`, `type_a.py`, `type_b.py`, `budget.py`, `calibration.py`, `residuals.py`, `limits.py`, `rules.py`, `loader.py`, `validator.py`, etc.) ensuring backwards compatibility with `app.py`.
4. `results/milestone1_baseline_backup/`: Exact snapshot of Milestone 1 generated reports, JSON records, and PNG plots.

---

## 6. Audit Focus Areas Identified for Phase B

1. **Schema & Record Immutability**:
   - Verify whether `MeasurementRecord` immutability is comprehensive (e.g. check dictionary mutation, field reassignment).
   - Verify timestamp parsing and ISO-8601 validation against edge cases (missing timezone, leap seconds, invalid months/days).
2. **Synthetic Data Realism**:
   - Inspect random noise generation, deterministic seeding, and whether drift or quantization creates artifacts.
   - Verify that ground truth (`true_*`) is completely isolated and cannot leak into reference or DUT paths.
3. **Data Quality & MAD Edge Cases**:
   - Zero-MAD behavior when $>50\%$ of observations are identical (e.g. heavily quantized signals).
   - Edge cases for single observation, all-NaN series, non-finite values, and negative time steps.
4. **Measurement Metrics**:
   - Bessel's correction $(n-1)$ behavior for $n=1$ or empty datasets.
   - Near-zero reference thresholding: verify numerical tolerance and check whether negative reference values near zero are handled symmetrically ($|y_{ref}| < \epsilon$).
5. **GUM Uncertainty Engine**:
   - Verify covariance propagation with negative and positive correlation coefficients.
   - Verify Welch-Satterthwaite formula when degrees of freedom are infinite vs finite vs zero.
   - Verify coverage factor $k$ and distinguish between confidence intervals and coverage intervals.
   - Audit metrological rounding rules (edge cases near boundary values like 0.0099 vs 0.010).
6. **Calibration Integrity & Data Leakage**:
   - Check if random split on time-series with temporal drift causes leakage between train and test sets.
   - Verify F-test degrees of freedom and whether higher order polynomials properly fall back to linear.
   - Extrapolation bounds: check upper and lower bound handling.
7. **Drift & Conformity**:
   - Non-uniform time steps in linear drift regression.
   - CUSUM threshold scaling and reset mechanics.
   - ILAC-G8 guard-banding rules near tolerance boundaries.
