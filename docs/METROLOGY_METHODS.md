# IMUCA — Metrology Methods and Mathematical Formulations

## 1. Measurement Models

### 1.1 Direct DC Voltage Measurement
For direct voltage sensing:
$$Y_V = V_{DUT}$$
where $V_{DUT}$ is the sampled potential difference across the input terminals.

### 1.2 Indirect DC Current Measurement (Shunt Resistor Model)
For current sensing using an external or internal precision low-side/high-side shunt resistor:
$$I = f(V_{shunt}, R_{shunt}) = \frac{V_{shunt}}{R_{shunt}}$$

Sensitivity coefficients derived by partial differentiation (GUM Section 5.1):
$$c_V = \frac{\partial I}{\partial V_{shunt}} = \frac{1}{R_{shunt}}$$
$$c_R = \frac{\partial I}{\partial R_{shunt}} = -\frac{V_{shunt}}{R_{shunt}^2} = -\frac{I}{R_{shunt}}$$

Combined variance according to first-order Taylor series:
$$u_c^2(I) = c_V^2 u^2(V_{shunt}) + c_R^2 u^2(R_{shunt}) + 2 c_V c_R \operatorname{cov}(V_{shunt}, R_{shunt})$$

Assuming independent calibration of shunt resistance and differential voltage measurement, the covariance term is zero:
$$u_c(I) = \sqrt{\left(\frac{1}{R_{shunt}}\right)^2 u^2(V_{shunt}) + \left(\frac{I}{R_{shunt}}\right)^2 u^2(R_{shunt})}$$

### 1.3 Temperature Measurement
$$T_K = T_{C} + 273.15$$
where $T_C$ is the digitized Celsius temperature reading from the sensor register.

---

## 2. Statistical Metrics and Error Definitions

### 2.1 Sample Mean and Bessel's Correction
For a series of $n$ independent observations $\{y_1, y_2, \dots, y_n\}$:
$$\bar{y} = \frac{1}{n} \sum_{i=1}^n y_i$$
$$s^2 = \frac{1}{n - 1} \sum_{i=1}^n (y_i - \bar{y})^2$$
$$s = \sqrt{s^2}$$
where the $(n - 1)$ denominator provides an unbiased estimator of population variance.

### 2.2 Repeatability and Standard Error of the Mean
$$s_m = u_A = \frac{s}{\sqrt{n}}$$
Degrees of freedom: $\nu = n - 1$.

Pooled repeatability across $K$ measurement series (ISO 5725-2):
$$s_r = \sqrt{\frac{\sum_{k=1}^K (n_k - 1) s_k^2}{\sum_{k=1}^K (n_k - 1)}}$$
Repeatability limit:
$$r = 2.8 \cdot s_r$$

### 2.3 Error vs Uncertainty Distinction
> **Critical Metrology Note**: Error and uncertainty are fundamentally distinct concepts (JCGM 200:2012 / VIM 3).
> - **Error**: The difference between a measured value and a reference standard value ($e_i = y_i - y_{ref, i}$). It is a known quantity with a specific sign when a reference is present.
> - **Uncertainty**: A non-negative parameter characterizing the dispersion of values that could reasonably be attributed to the measurand.
> - **Root Mean Square Error (RMSE)** is an aggregate measure of model residuals or bias, **never** to be conflated with measurement uncertainty.

$$\text{Mean Bias} = \bar{e} = \frac{1}{n} \sum_{i=1}^n (y_i - y_{ref, i})$$
$$\text{MAE} = \frac{1}{n} \sum_{i=1}^n |y_i - y_{ref, i}|$$
$$\text{RMSE} = \sqrt{\frac{1}{n} \sum_{i=1}^n (y_i - y_{ref, i})^2}$$

Guarded relative error (rejection near zero reference):
$$e_{rel, i} = \begin{cases} \frac{y_i - y_{ref, i}}{y_{ref, i}} & \text{if } |y_{ref, i}| > 10^{-4} \\ \text{undefined (NaN)} & \text{otherwise} \end{cases}$$

---

## 3. Uncertainty Evaluation Methodology (JCGM 100:2008 / GUM)

### 3.1 Type A Evaluation
Evaluated from statistical distribution of observations:
$$u_A = \frac{s}{\sqrt{n}}, \quad \nu_A = n - 1$$

### 3.2 Type B Evaluation
Evaluated from specification bounds, calibration certificates, or physical limits with half-width $a$:
- **Rectangular (Uniform) Distribution**:
  $$u_B = \frac{a}{\sqrt{3}}$$
- **Triangular Distribution**:
  $$u_B = \frac{a}{\sqrt{6}}$$
- **Normal Distribution**:
  $$u_B = \frac{a}{k} \quad (k = 2.0 \text{ for } 95\% \text{ expanded uncertainty on certificate})$$
- **U-Shaped (Arcsine) Distribution** (e.g. thermal or sinusoidal variation):
  $$u_B = \frac{a}{\sqrt{2}}$$

### 3.3 Welch-Satterthwaite Effective Degrees of Freedom
When combining Type A and Type B components:
$$\nu_{eff} = \frac{u_c^4(y)}{\sum_{i=1}^N \frac{c_i^4 u^4(x_i)}{\nu_i}}$$
If $\nu_{eff} < 100$, coverage factor $k$ is obtained from the Student's $t$ quantile:
$$k = t_{1 - \alpha/2}(\nu_{eff})$$

### 3.4 Metrological Rounding Rule
1. Expanded uncertainty $U$ is rounded upward to 2 significant digits.
2. The reported measurement value is rounded to the same decimal place as the least significant figure of $U$.

---

## 4. Calibration Engine and F-Test Model Selection

Given calibration observations $\{(x_1, y_1), \dots, (x_n, y_n)\}$:
1. Fit linear model: $\hat{y} = a_0 + a_1 x$
2. Fit candidate polynomial of degree $d$: $\hat{y} = \sum_{j=0}^d a_j x^j$
3. Compute sequential F-test comparing reduced model $(d-1)$ to full model $(d)$:
   $$F = \frac{(SSE_{red} - SSE_{full}) / 1}{SSE_{full} / (n - d - 1)}$$
   The polynomial term is accepted if and only if $p = 1 - F_{cdf}(F) < 0.05$ and $\text{BIC}_{full} < \text{BIC}_{red}$.

---

## 5. References

1. **JCGM 100:2008**: *Evaluation of measurement data — Guide to the expression of uncertainty in measurement* (GUM 1995 with minor corrections). Joint Committee for Guides in Metrology.
2. **JCGM 101:2008**: *Evaluation of measurement data — Supplement 1 to the GUM: Propagation of distributions using a Monte Carlo method*.
3. **JCGM 200:2012**: *International vocabulary of metrology — Basic and general concepts and associated terms* (VIM 3rd edition).
4. **ISO 5725-2:2019**: *Accuracy (trueness and precision) of measurement methods and results — Part 2: Basic method for the determination of repeatability and reproducibility of a standard measurement method*.
5. **ILAC-G8:09/2019**: *Guidelines on Decision Rules and Statements of Conformity*. International Laboratory Accreditation Cooperation.
6. **ISO 14253-1:2017**: *Geometrical product specifications (GPS) — Inspection by measurement of workpieces and measuring equipment — Part 1: Decision rules for proving conformity or nonconformity with specifications*.
