# IMUCA Faculty Demonstration Guide (5–10 Minutes)

> **Demonstration Script & Walkthrough for Measurements and Instrumentation Faculty Review**

This guide provides a structured, step-by-step walkthrough to demonstrate the **IMUCA** system in 5 to 10 minutes.

---

## 🕒 Demonstration Overview & Key Takeaway

| Duration | Phase | Action / Focus |
|---|---|---|
| **0:00 – 1:00** | Introduction & Problem Statement | Why bare readings fail; need for integrated metrology pipeline. |
| **1:00 – 2:30** | Data Ingestion & Validation | Raw data, MAD outlier flagging without silent deletion. |
| **2:30 – 4:30** | Uncertainty Budget & GUM Combination | Type A + Type B sources, variance shares, dominant contributor ranking. |
| **4:30 – 6:30** | Calibration Sweep & Residual Diagnostics | Offset/gain separation, 3-band conformity, quantisation residuals. |
| **6:30 – 8:00** | Drift Detection & Breach Forecast | Demo A vs Demo B: Demonstrating dynamic rule-based decision engine. |
| **8:00 – 9:30** | Automated Report Export & Viva Defense | Downloadable HTML report, transparent rules defense vs black-box ML. |

---

## 🚀 Step-by-Step Script

### STEP 1: Launch Application & Overview (Minute 0:00 – 1:00)
1. **Launch Command:**
   ```bash
   python -m streamlit run app.py
   ```
2. **Open:** `http://localhost:8501`
3. **Faculty Pitch:**
   > *"Good morning/afternoon, Professor. Today I am presenting IMUCA — the Intelligent Measurement Uncertainty and Calibration Analyzer. In conventional instrumentation practice, measurement readings are recorded in isolation, while uncertainty budgets, calibration curves, and drift tracking live in separate spreadsheets. IMUCA closes this research gap by providing a 12-stage unified metrology engine that takes raw readings, quantifies uncertainty according to ISO GUM, performs calibration and drift analysis, and feeds an auditable rule-based decision engine."*

---

### STEP 2: Raw Data & Robust Validation (Minute 1:00 – 2:30)
1. Navigate to **Tab 2: Raw Data & Validation**.
2. Explain the dataset:
   - 10-point calibration sweep from $0.5\text{ V}$ to $5.0\text{ V}$ in $0.5\text{ V}$ steps.
   - 10 repeated readings at the $5.000\text{ V}$ operating point.
3. Highlight **Algorithm 1a Validation**:
   - Show how the algorithm checks for non-numeric data, missing fields, and range limits.
   - Point out the **MAD Outlier Check ($|z| > 3.5$)**:
     > *"Crucially, IMUCA NEVER silently deletes outliers. Suspect data points are flagged for engineering inspection while retaining raw data integrity."*

---

### STEP 3: Statistical Reduction & Type A Evaluation (Minute 2:30 – 3:30)
1. Click **Tab 3: Statistics**.
2. Show the computed values:
   - Mean $\bar{x} = 5.021\text{ V}$
   - Sample Standard Deviation $s = 9.944\text{ mV}$ (with $n-1$ Bessel's correction).
   - Standard Error $s(\bar{x}) = 3.145\text{ mV}$.
3. Open the **Calculation Details** expander to show the step-by-step arithmetic trace.

---

### STEP 4: Uncertainty Budget & Dominant Source Ranking (Minute 3:30 – 4:30)
1. Click **Tab 5: Uncertainty Budget**.
2. Show the **Uncertainty Budget Table** containing all 5 sources:
   - **Repeatability (Type A):** $u = 3.145\text{ mV}$ ($35.6\%$ of variance) $\rightarrow$ **DOMINANT**.
   - **DUT Specification (Type B, Rectangular $d=\sqrt{3}$):** $u = 2.899\text{ mV}$ ($30.2\%$).
   - **Display Resolution (Type B, Rectangular $d=\sqrt{3}$):** $u = 2.887\text{ mV}$ ($30.0\%$).
   - **Reference Standard (Type B, Normal $d=2$):** $u = 1.000\text{ mV}$ ($3.6\%$).
   - **Ambient Tempco (Type B, Rectangular $d=\sqrt{3}$):** $u = 0.435\text{ mV}$ ($0.7\%$).
3. Point to the **Plotly Bar Chart**:
   - Highlight the red bar indicating the dominant contributor.
4. Deliver the Engineering Insight:
   > *"Professor, the budget ranking provides an actionable engineering conclusion: Buying a more expensive reference standard reduces combined uncertainty by less than 2%, while controlling room temperature changes almost nothing. To improve precision, we must replace the 3½-digit meter with a 4½-digit meter, which attacks both resolution and scatter simultaneously."*
5. Show **Welch-Satterthwaite Effective DOF ($\nu_{eff} = 71.2$)**, coverage factor $k=2$, expanded uncertainty $U = 10.55\text{ mV}$, and reported format:  
   $$\mathbf{(5.021 \pm 0.011)\text{ V, } k=2}$$

---

### STEP 5: Calibration Curve & Residual Diagnostics (Minute 4:30 – 6:00)
1. Click **Tab 6: Calibration**.
2. Point to the KPI cards:
   - **Zero Offset:** $+6.67\text{ mV}$
   - **Gain Error:** $+0.303\%$
   - **Linearity:** $R^2 = 0.999997$
3. Show the **Sweep Error Plot** and **Residual Plot**:
   - Explain why Point 1 ($0.500\text{ V}$) fails the $\pm 1.0\%$ tolerance:
     > *"At low voltages, the fixed 8 mV offset becomes a large percentage of reading (+2.0%), causing point 1 to fail even though higher points easily pass."*
   - Show the **Documented Correction Formula**:
     $$X_{corrected} = \frac{X_{DUT} - 0.006667}{1.003030}$$
     Applying this formula brings all points inside tolerance.

---

### STEP 6: The Core Demonstration: Demo A vs Demo B (Minute 6:00 – 8:00)
1. Point to the top **Measurement Quality Banner** currently showing:
   - **MEASUREMENT QUALITY:** `ACCEPTABLE`
   - **Triggered Rule:** `R5 Default (No violations)`
   - **Drift Status:** `NOT ASSESSED`
2. Now, click the **Demo B (+ History)** button in the left sidebar!
3. Observe the immediate dynamic transition:
   - **MEASUREMENT QUALITY:** switches from `ACCEPTABLE` to **`ATTENTION REQUIRED`**.
   - **Triggered Rule:** **`R3 Possible Drift`**
   - **Drift Status:** **`SIGNIFICANT UPWARD DRIFT DETECTED`**
4. Navigate to **Tab 7: Drift & Trend**:
   - Show the historical trend: Drift rate $b = +1.10\text{ mV/session}$ ($p = 1.3 \times 10^{-6}$).
   - Show the **Projected Tolerance Breach at Session 28** (18 sessions ahead).
   - Point out the recommendation: *Schedule recalibration before session 24 to retain safety margin.*
5. Faculty Summary:
   > *"This proves that IMUCA's decision engine does not return a canned or static response; it actively modifies its engineering recommendation as historical drift evidence becomes available."*

---

### STEP 7: Automated Report Generation (Minute 8:00 – 9:00)
1. Click **Tab 9: Automated Report**.
2. Show the comprehensive, publication-ready HTML preview:
   - Complete traceability of statistics, budget table, calibration fit, drift stats, and rule audit log.
   - Prominent disclaimer: *"Synthetic proof-of-concept data — not experimental laboratory data."*
3. Click **Download HTML Report** to demonstrate file export.

---

## 🛡️ Key Viva Q&A Cheat Sheet

**Q1: Why did you use rule-based logic instead of a machine learning model?**  
*Answer:* In accredited metrology (ISO/IEC 17025), every decision must be strictly traceable and auditable by hand with a calculator. Furthermore, supervised ML requires large datasets of instrument failure modes, which do not exist for a new instrument. A transparent rule engine establishes the baseline against which future unsupervised models can be evaluated.

**Q2: Why use sample standard deviation ($n-1$) instead of population SD ($n$)?**  
*Answer:* Because the true population mean $\mu$ is unknown and estimated from the sample mean $\bar{x}$, removing one degree of freedom. The $n-1$ denominator (Bessel's correction) provides an unbiased estimator of variance.

**Q3: How is Type B uncertainty converted from a datasheet specification?**  
*Answer:* By dividing the stated half-width by the divisor of the assumed probability distribution: $\sqrt{3}$ for rectangular (uniform), $\sqrt{6}$ for triangular, $2$ for normal at $95\%$ confidence ($k=2$).

**Q4: Has this system been tested on physical hardware?**  
*Answer:* No, this is currently a validated proof-of-concept using numerically injected error models. Hardware integration via SCPI/USB with DMMs and programmable power supplies is planned for Phase 2.
