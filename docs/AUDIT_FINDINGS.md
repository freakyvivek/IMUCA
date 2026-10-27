# IMUCA Audit Findings & Defect Catalog

**Project:** IMUCA (Intelligent Measurement, Uncertainty, Calibration and Analysis)  
**Audit Date:** 2026-10-25  
**Auditor:** Scientific Metrology & Research Software Audit Specialist  
**Audit Scope:** Source code (`src/imuca/`), tests (`tests/`), scripts (`scripts/`), baseline results (`results/`), and research claims.

---

## 1. Executive Summary of Audit Findings

The Milestone 1 implementation of IMUCA represents a solid foundational software architecture for metrological analysis, but rigorous code-level audit and independent numerical testing uncovered **8 demonstrable defects** across data quality, uncertainty propagation, boundary conditions, serialization, and calibration validation.

All 8 defects have been classified according to severity, reproduced with targeted unit tests, and remediated safely without introducing architectural disruptions or breaking backward compatibility.

### Summary Matrix

| Finding ID | Severity | Affected Module | Defect Description | Status |
|---|---|---|---|---|
| **FIND-DQ-01** | High | `src/imuca/data_quality.py` | Zero-MAD outlier masking in constant/quantized signals | **Remediated** |
| **FIND-UNC-01** | High | `src/imuca/uncertainty.py` | Symmetric covariance dictionary double-counting off-diagonal variance | **Remediated** |
| **FIND-EXP-01** | High | `scripts/run_baseline_experiment.py` | Type A repeatability coerced into Type B, erasing degrees of freedom | **Remediated** |
| **FIND-UNC-02** | Medium | `src/imuca/uncertainty.py` | Decade boundary rounding error in metrological uncertainty rounding | **Remediated** |
| **FIND-VAL-01** | Medium | `src/imuca/validation.py` | Tolerance breach forecast returned `None` when limit was already breached | **Remediated** |
| **FIND-SCH-01** | Medium | `src/imuca/schema.py` | `OverflowError` on non-finite sequence numbers and string timestamps | **Remediated** |
| **FIND-CAL-01** | Medium | `src/imuca/calibration.py` | Temporal and autocorrelation data leakage in time-series split | **Remediated** |
| **FIND-REP-01** | Low | `src/imuca/reporting.py` | NumPy boolean and numeric serialization failure in `json.dump` | **Remediated** |

---

## 2. Detailed Findings Catalog

---

### Finding FIND-DQ-01: Zero-MAD Outlier Masking in Constant / Quantized Signals

- **Severity:** High
- **Affected File & Function:** `src/imuca/data_quality.py` &rarr; `DataQualityAssessor.screen_dataframe`
- **Initial Code:**
  ```python
  if mad > 1e-12:
      mod_z = 0.6745 * abs_devs / mad
      for idx_pos, (row_idx, z_val) in enumerate(zip(valid_indices, mod_z)):
          ...
  ```
- **Evidence:**
  When $\ge 50\%$ of data points are identical to the sample median (common in repeated measurements, highly quantized ADC readings, or steady-state reference sweeps), the Median Absolute Deviation is identically zero ($\text{MAD} = 0.0$). The guard `if mad > 1e-12:` bypassed outlier screening entirely. A rogue measurement (e.g., 12.0 V injected into a 5.0 V nominal stream) passed through undetected with status `CLEAN`.
- **Scientific Impact:**
  Direct violation of robust data screening (NIST / Iglewicz & Hoaglin 1993). Severe sensor glitches or communication bit-flips in stable DC channels remained unflagged, corrupting downstream Type A uncertainty calculations and calibration regression.
- **Remediation:**
  Implemented NIST / Iglewicz & Hoaglin recommended fallback: When $\text{MAD} \le 10^{-12}$, compute the Mean Absolute Deviation from the median:
  $$\text{MeanAD} = \frac{1}{n} \sum_{i=1}^n |x_i - \text{median}|$$
  If $\text{MeanAD} > 10^{-12}$, compute the modified Z-score using:
  $$M_i = \frac{0.6745 \cdot |x_i - \text{median}|}{1.2533 \cdot \text{MeanAD}}$$
  where $1.2533 \approx \sqrt{\pi/2}$ is the scaling factor converting MeanAD to standard deviation for normal distributions. If all values are identical ($\text{MeanAD} \le 10^{-12}$), set $M_i = 0$.
- **Demonstrating Test:** `tests/test_audit_numerical_cases.py::test_case_18_zero_mad_outlier_detection`
- **Status:** **Remediated**.

---

### Finding FIND-UNC-01: Symmetric Covariance Matrix Double-Counting

- **Severity:** High
- **Affected File & Function:** `src/imuca/uncertainty.py` &rarr; `build_uncertainty_budget`
- **Initial Code:**
  ```python
  if covariances:
      for (i, j), cov_val in covariances.items():
          if 0 <= i < len(components) and 0 <= j < len(components):
              c_i = components[i].sensitivity_coefficient
              c_j = components[j].sensitivity_coefficient
              u_c_sq += 2.0 * c_i * c_j * cov_val
  ```
- **Evidence:**
  In JCGM 100:2008 (GUM) Eq. 13, the combined variance is:
  $$u_c^2(y) = \sum_{i=1}^N c_i^2 u^2(x_i) + 2 \sum_{i=1}^{N-1}\sum_{j=i+1}^N c_i c_j \operatorname{cov}(x_i, x_j)$$
  If a caller passed a standard symmetric covariance dictionary `{(0, 1): cov, (1, 0): cov}`, the loop iterated over both entries, multiplying each by `2.0`. The off-diagonal term was thus added with a factor of $4.0$, overestimating the correlated variance by $100\%$. Furthermore, if a diagonal element `(i, i)` was included, variance was improperly doubled.
- **Scientific Impact:**
  Artificially inflated or distorted combined standard uncertainty $u_c$ and expanded uncertainty $U$ when correlated inputs were supplied via standard scientific covariance matrices.
- **Remediation:**
  Added tracking of unique unordered pairs `pair = (min(i, j), max(i, j))` and skipped diagonal terms `i == j`. When both `(i, j)` and `(j, i)` are present, their average is multiplied by $2.0$ once. If only a single directed entry is passed, it is multiplied by $2.0$ once.
- **Demonstrating Test:** `tests/test_audit_numerical_cases.py::test_symmetric_covariance_no_double_count`
- **Status:** **Remediated**.

---

### Finding FIND-EXP-01: Type A Component Coerced to Type B in Current Baseline Experiment

- **Severity:** High
- **Affected File & Function:** `scripts/run_baseline_experiment.py` &rarr; `run_current_experiment`
- **Initial Code:**
  ```python
  u_type_a = evaluate_type_a(df["current_mA"].values[:10] / 1000.0, unit="A", name="Current Repeatability (Type A)")
  all_comps = [u_type_a] + shunt_comps
  budget = build_uncertainty_budget(
      measurand_name="DC Current",
      nominal_value=nom_i * 1000.0, # in mA
      measurand_unit="mA",
      components=[
          evaluate_type_b(c.name, c.input_value * (1000.0 if c.unit != "Ohm" else 1.0),
                          distribution=c.distribution, unit="mA" if c.unit != "Ohm" else "Ohm",
                          sensitivity_coefficient=c.sensitivity_coefficient * (1.0 if c.unit != "Ohm" else 1000.0))
          for c in all_comps
      ],
      ...
  )
  ```
- **Evidence:**
  `evaluate_type_b` was called in a list comprehension over `all_comps`, which included `u_type_a`. This transformed the Type A experimental repeatability component into a Type B component, overwrote its finite degrees of freedom ($\nu = 9 \to \infty$), and recomputed standard uncertainty using a uniform or normal assumption instead of the empirical sample standard deviation of the mean $s / \sqrt{n}$.
- **Scientific Impact:**
  Distorted the Welch-Satterthwaite effective degrees of freedom $\nu_{\mathrm{eff}}$, causing student-t coverage factor lookups to incorrectly default to Gaussian $k = 2.0$ rather than the appropriate Student's $t$ quantile.
- **Remediation:**
  Evaluated `u_type_a` directly in mA units and preserved it as an unaltered Type A component. Scaled the sensitivity coefficients of the shunt resistor Type B components to mA ($c_V \times 1000$ mA/V and $c_R \times 1000$ mA/$\Omega$), passing them cleanly into `build_uncertainty_budget`.
- **Demonstrating Test:** Tested in `tests/test_audit_numerical_cases.py::test_case_11_and_12_nonlinear_shunt_current_propagation` and verified during baseline execution.
- **Status:** **Remediated**.

---

### Finding FIND-UNC-02: Decade Boundary Error in Metrological Rounding

- **Severity:** Medium
- **Affected File & Function:** `src/imuca/uncertainty.py` &rarr; `round_uncertainty_metrology`
- **Initial Code:**
  ```python
  order = math.floor(math.log10(uncertainty))
  factor = 10 ** (1 - order)
  rounded_u = math.ceil(uncertainty * factor) / factor
  decimals = max(0, 1 - order)
  rounded_val = round(value, decimals)
  ```
- **Evidence:**
  When `math.ceil` pushed an uncertainty across a decade boundary (e.g., $U = 0.00995 \to 0.010$), `order` remained evaluated at $\lfloor \log_{10}(0.00995) \rfloor = -3$. Consequently, `decimals = 1 - (-3) = 4`. The value was rounded to 4 decimals ($5.0212$) and formatted as `(5.0212 +/- 0.0100)`. This displayed three significant digits for uncertainty rather than the standard two significant digits.
- **Scientific Impact:**
  Minor formatting non-conformance with metrological rounding standards (ISO/IEC Guide 98-3 Clause 7.2.6), which specifies that uncertainty shall be rounded to at most two significant digits, and the measurand rounded to match the least significant decimal digit.
- **Remediation:**
  Recomputed `order_u = math.floor(math.log10(rounded_u))` after `math.ceil` to determine the true decimal placement:
  ```python
  order_u = math.floor(math.log10(rounded_u))
  decimals = max(0, 1 - order_u)
  rounded_val = round(value, decimals)
  ```
- **Demonstrating Test:** `tests/test_audit_numerical_cases.py::test_metrological_rounding_power_of_10_boundary`
- **Status:** **Remediated**.

---

### Finding FIND-VAL-01: Tolerance Breach Forecast Returned `None` for Already-Breached States

- **Severity:** Medium
- **Affected File & Function:** `src/imuca/validation.py` &rarr; `analyze_temporal_drift`
- **Initial Code:**
  ```python
  if is_sig:
      if slope > 0 and upper_limit is not None and curr_y < upper_limit:
          t_breach = float((upper_limit - curr_y) / slope)
      elif slope < 0 and lower_limit is not None and curr_y > lower_limit:
          t_breach = float((curr_y - lower_limit) / abs(slope))
  ```
- **Evidence:**
  When the current sensor reading was already beyond the specification limits ($curr\_y \ge upper\_limit$ for positive drift, or $curr\_y \le lower\_limit$ for negative drift), the condition failed and `t_breach` remained `None`. Callers interpreting `None` as "no breach forecasted" were misled, completely masking an active out-of-tolerance condition.
- **Scientific Impact:**
  Automated monitoring systems consuming this output would fail to trigger out-of-tolerance alarms when an instrument had already drifted out of specification.
- **Remediation:**
  Added explicit checks: if $curr\_y \ge upper\_limit$ with positive slope, or $curr\_y \le lower\_limit$ with negative slope, set `t_breach = 0.0` and append `"Tolerance limit already breached."` to `summary_message`.
- **Demonstrating Test:** `tests/test_audit_numerical_cases.py::test_case_21_drift_breach_already_breached`
- **Status:** **Remediated**.

---

### Finding FIND-SCH-01: `OverflowError` on Infinite Sequence Numbers and Unparsed Strings

- **Severity:** Medium
- **Affected File & Function:** `src/imuca/schema.py` &rarr; `validate_measurement_dataframe`
- **Initial Code:**
  ```python
  seq_num = int(row.get("sequence_id", i))
  # and
  elapsed = float(el_raw)  # where el_raw could be unparsed text or corrupted string
  ```
- **Evidence:**
  If a corrupted or malicious record contained `float('inf')` or `float('nan')` in `sequence_id`, Python's `int(float('inf'))` threw an unhandled `OverflowError`, crashing the pipeline. Furthermore, non-numeric strings in `elapsed_ms` threw unhandled `ValueError`.
- **Scientific Impact:**
  Breached data ingestion robustness. Ingestion pipelines should return diagnostic quality issues and clean boolean masks rather than raising unhandled interpreter crashes on malformed data.
- **Remediation:**
  Safely checked `math.isfinite()` before converting sequence identifiers to integer, falling back to row index $i$ and appending `INVALID_SEQUENCE` diagnostic flag. Wrapped `elapsed_ms` parsing in `try-except (ValueError, TypeError)` setting `np.nan` and flagging `MALFORMED_TIMESTAMP`.
- **Demonstrating Test:** `tests/test_audit_numerical_cases.py::test_case_23_schema_infinity_sequence_and_string_elapsed`
- **Status:** **Remediated**.

---

### Finding FIND-CAL-01: Temporal and Autocorrelation Data Leakage in Calibration Splitting

- **Severity:** Medium
- **Affected File & Function:** `src/imuca/calibration.py` &rarr; `CalibrationEngine.evaluate_train_validation_split`
- **Initial Code:**
  ```python
  rng = np.random.default_rng(random_seed)
  shuffled_indices = rng.permutation(n)
  n_train = int(np.floor(n * train_ratio))
  train_idx = shuffled_indices[:n_train]
  val_idx = shuffled_indices[n_train:]
  ```
- **Evidence:**
  The calibration module only supported random pointwise shuffling across time series or repetitive calibration points. When repeated measurements or slowly drifting sensors are shuffled point-by-point, adjacent correlated readings are split across the training and validation sets. This causes data leakage, artificially lowering validation residuals.
- **Scientific Impact:**
  Validation error metrics (MAE, RMSE reduction) can appear optimistically high due to autocorrelation between adjacent time-series samples.
- **Remediation:**
  Introduced a configurable `split_strategy` parameter:
  - `'random'`: Permutation split (preserved for independent static sweeps).
  - `'chronological'`: Contiguous time split (first $100 \times \text{train\_ratio}\%$ for training, remainder for validation). Prevents time-series autocorrelation leakage.
  - `'blocked'`: Interleaved block partition to ensure even span coverage without pointwise adjacency leakage.
  Stored `split_strategy`, `train_indices`, and `validation_indices` in `CalibrationValidationComparison`.
- **Demonstrating Test:** Tested in `tests/test_calibration.py` and `tests/test_audit_numerical_cases.py`.
- **Status:** **Remediated**.

---

### Finding FIND-REP-01: NumPy Boolean / Float Serialization Failure in JSON Reporting

- **Severity:** Low
- **Affected File & Function:** `src/imuca/reporting.py` &rarr; `MetrologyReportGenerator.generate_json_report`
- **Initial Code:**
  ```python
  with open(json_path, "w") as f:
      json.dump(report, f, indent=2)
  ```
- **Evidence:**
  When quality issues or drift results contained `np.bool_`, `np.floating`, `np.integer`, or `np.ndarray` types, the standard library `json.dump` raised `TypeError: Object of type bool_ is not JSON serializable`.
- **Scientific Impact:**
  Execution failure at the final reporting stage after successful numerical calculations.
- **Remediation:**
  Implemented recursive serializer `_json_serialize(obj)` mapping NumPy types to native Python `bool`, `float`, `int`, and `list` prior to dumping.
- **Demonstrating Test:** Verified during baseline experiment execution.
- **Status:** **Remediated**.

---

## 3. Classification of Scope Boundaries and Future Hardware Unknowns

The following items are **not software defects**, but architectural scope boundaries and physical hardware unknowns documented for Milestone 2:

1. **Physical Sensor Calibration Traceability:**  
   Current calibration sweeps are derived from synthetic generators. True metrological traceability (ISO/IEC 17025) requires physical comparison against a calibrated 6.5-digit digital multimeter (e.g. Keysight 34461A or Keithley DMM6500) with known calibration certificates and calibration interval.
2. **INA219 Internal Registers & Shunt Calibration:**  
   The synthetic model assumes a nominal $0.100\ \Omega \pm 0.5\%$ shunt. Physical SMT shunt resistors exhibit thermal coefficients ($\approx 50-100\ \text{ppm/}^\circ\text{C}$) and thermoelectric Seebeck voltages that must be characterized under live hardware load.
3. **Firmware Framing Protocol:**  
   Serial acquisition is implemented as a modular abstraction. Live streaming awaits final microcontroller firmware specification (baud rate, framing delimiters, CRC checksum, hardware timestamp counter).
