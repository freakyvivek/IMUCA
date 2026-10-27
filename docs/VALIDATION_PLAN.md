# IMUCA — Validation Plan and Acceptance Criteria

## 1. Overview and Evidence Categories

To maintain scientific defensibility, experimental evidence is partitioned into four distinct categories:

1. **Category 1: Simulated Algorithm Verification**: Unit and integration tests against synthetic datasets with known ground truth. Verifies mathematical correctness of formulas, GUM propagation, and non-destructive outlier detection.
2. **Category 2: Offline Reference-Instrument Comparison**: Testing against recorded laboratory CSV datasets where a calibrated reference standard (e.g. Keysight/Fluke DMM) provided coincident readings.
3. **Category 3: Calibration Generalisation Validation**: Out-of-sample testing where calibration models are evaluated solely on held-out validation data points to prove true error reduction without data leakage.
4. **Category 4: Physical Hardware Characterization (Future Stage)**: Real-time validation once microcontroller firmware and sensors (INA219, DS18B20) are integrated.

---

## 2. Predefined Experiments

### Experiment 1: DC Voltage Calibration Sweep & GUM Uncertainty Budget
- **Dataset**: `data/synthetic/nominal_voltage_baseline.csv` (10 steps from $0.5\text{ V}$ to $5.0\text{ V}$, 10 repeats each).
- **Objective**: Verify linear calibration regression, held-out MAE/RMSE reduction, and GUM budget combination at $5.000\text{ V}$.
- **Acceptance Criteria**:
  - Linear fit $R^2 \ge 0.9999$.
  - Post-calibration MAE reduction on held-out test data $\ge 80.0\%$.
  - Combined standard uncertainty $u_c \le 5.0\text{ mV}$.
  - Expanded uncertainty $U(k=2)$ correctly rounded to 2 significant digits.

### Experiment 2: DC Current Indirect Shunt Model & Calibration
- **Dataset**: `data/synthetic/current_calibration_sweep.csv` (12 steps from $100\text{ mA}$ to $2000\text{ mA}$, 10 repeats each).
- **Objective**: Verify Ohm's law indirect model $I = V_{shunt} / R_{shunt}$, analytical sensitivity coefficients ($c_V = 1/R, c_R = -I/R$), and out-of-sample calibration.
- **Acceptance Criteria**:
  - Analytical sensitivity coefficients match theoretical partial derivatives.
  - Post-calibration MAE reduction $\ge 90.0\%$.
  - Shunt resistor tolerance correctly identified as the dominant variance contributor ($\ge 50\%$ variance share).

### Experiment 3: Temperature Aging Drift & Breach Forecasting
- **Dataset**: `data/synthetic/temperature_drift_scenario.csv` (200 seconds at $45^\circ\text{C}$ with linear drift $+15\text{ mK/s}$).
- **Objective**: Verify linear drift slope estimation, statistical significance ($p < 0.05$), CUSUM step detection, and time-to-breach forecast.
- **Acceptance Criteria**:
  - Estimated drift rate within $\pm 10\%$ of true injected rate.
  - Linear drift p-value $< 10^{-5}$.
  - Forecasted seconds to upper specification breach calculated without numerical divergence.

### Experiment 4: Anomaly Screening & Fault Detection Benchmark
- **Dataset**: `data/synthetic/fault_stress_scenario.csv` (150 samples containing 10 injected anomalies: 3 outliers, 3 missing samples, 1 duplicate, 1 gap, 2 status faults).
- **Objective**: Verify non-destructive quality checks against ground-truth labels.
- **Acceptance Criteria**:
  - Detection Recall $\ge 80.0\%$.
  - Detection Precision $\ge 70.0\%$.
  - Missed Detection Rate $\le 20.0\%$.
  - Zero raw records deleted from dataset.

---

## 3. Hardware Validation Requirements (For Subsequent Phase)

When the hardware team delivers the physical instrument, the following experimental protocol must be executed before claiming physical accuracy:

1. **Equipment Requirements**:
   - Reference Multimeter: 6.5-digit calibrated DMM (e.g. Fluke 8846A or Keysight 34465A) with valid ISO/IEC 17025 calibration certificate.
   - Precision DC Source: Low-noise programmable power supply ($0-30\text{ V}, 0-3\text{ A}$).
   - Thermal Chamber or Stirred Liquid Calibration Bath: Stability $\pm 0.02\ ^\circ\text{C}$.
2. **Measurement Procedure**:
   - 10-point voltage sweep ($1.0\text{ V}$ to $24.0\text{ V}$) in ascending and descending directions to assess hysteresis.
   - 10-point current sweep ($100\text{ mA}$ to $3000\text{ mA}$) with 30-minute thermal dwell at full load to characterize shunt self-heating.
   - 5-point temperature calibration bath immersion ($-10^\circ\text{C}, 0^\circ\text{C}, 25^\circ\text{C}, 50^\circ\text{C}, 85^\circ\text{C}$).
3. **Traceability Declaration**:
   - Traceability can only be claimed when the reference instrument's calibration certificate number, date, and expanded uncertainty are logged in the IMUCA experiment metadata.

---

## 4. Data-Leakage Prevention & Partitioning Protocol

Following the Milestone 1 audit, calibration validation must adhere to strict partitioning rules:
1. **Model Fitting Isolation:**
   All calibration parameters (coefficients $a_0, a_1, \dots$, standard errors, residual variance) must be estimated solely on the training partition.
2. **Partition Strategies:**
   - **Chronological Split:** Mandatory for time-series datasets exhibiting temporal drift, thermal settling, or autocorrelation. First $100 \times \text{train\_ratio}\%$ for training; remaining points for held-out validation.
   - **Blocked Split:** Mandatory for multi-point sweeps with repeated setpoint dwells, preventing adjacent points from the same dwell cycle leaking into validation.
   - **Random Split:** Permitted only when observations are demonstrably independent, identically distributed, and uncorrelated.
3. **Hyperparameter & Model Selection:**
   F-test and BIC polynomial order selection must be computed strictly on the training partition.

---

## 5. Guard-Banded Conformity Assessment Protocol (ILAC-G8:09/2019)

Conformity decisions must explicitly incorporate expanded measurement uncertainty $U = k \cdot u_c$:
1. **Simple Acceptance (Informational Only):**
   $$\mathrm{PASS} \iff \mathrm{LSL} \le y_m \le \mathrm{USL}$$
2. **Binary Guard-Banded Acceptance (Consumer's Risk $< 2.5\%$):**
   $$\mathrm{PASS} \iff \mathrm{LSL} + U \le y_m \le \mathrm{USL} - U$$
   $$\mathrm{CONDITIONAL} \iff (\mathrm{LSL} \le y_m < \mathrm{LSL} + U) \lor (\mathrm{USL} - U < y_m \le \mathrm{USL})$$
   $$\mathrm{FAIL} \iff y_m < \mathrm{LSL} \lor y_m > \mathrm{USL}$$
3. **Audit Verification:**
   All 4 experiments and 63 automated tests are verified under these acceptance criteria.

