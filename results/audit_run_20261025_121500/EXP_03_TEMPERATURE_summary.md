# IMUCA Metrology Analysis Report: `EXP_03_TEMPERATURE`
> **Generated at**: 2026-10-25T06:45:15.413770+00:00 | **IMUCA Framework**: v1.0.0
> **Disclaimer**: SYNTHETIC EXPERIMENT: For algorithm validation only.

## 1. Data Quality Screening
- **Total Records Analyzed**: 200
- **Clean Records**: 200 (100.0%)
- **Integrity Error Flags**: 0
- **Warning Flags (Retained for audit)**: 0

## 2. Measurement Accuracy & Calibration Performance
| Metric | Uncalibrated Baseline | Post-Calibration (Held-out Test) | Improvement |
| :--- | :--- | :--- | :--- |
| **Mean Bias** | `1.493` | N/A | - |
| **MAE** | `1.494` | N/A | - |
| **RMSE** | `1.72` | N/A | - |

## 3. GUM Uncertainty Budget (JCGM 100:2008)
- **Nominal Value**: `45.0 degC`
- **Combined Standard Uncertainty ($u_c$)**: `0.26 degC`
- **Expanded Uncertainty ($U, k=2.00$)**: `0.52 degC`
- **Dominant Contributor**: `Sensor Calibration Tolerance` (92.5% variance share)
- **Metrologically Rounded Result**: **(45.00 +/- 0.53) degC (k=2.00, 95% confidence)**

| Uncertainty Source | Type | Distribution | Standard Uncertainty $u_i$ | Sens. Coeff. $c_i$ | Contribution | Share % |
| :--- | :---: | :--- | :--- | :--- | :--- | :--- |
| Digital Quantization (12-bit) | Type B | RECTANGULAR | `0.03608 degC` | `1` | `0.03608` | `1.9%` |
| Sensor Calibration Tolerance | Type B | NORMAL | `0.25 degC` | `1` | `0.25` | `92.5%` |
| Self-Heating Dissipation | Type B | RECTANGULAR | `0.04619 degC` | `1` | `0.04619` | `3.2%` |
| Thermal Gradient | Type B | TRIANGULAR | `0.04082 degC` | `1` | `0.04082` | `2.5%` |

## 4. Drift Analysis & Breach Forecast
- **Drift Rate**: `1.4747e-02 /s` (p-value: `2.6155e-220`)
- **Statistically Significant**: `YES`
- **Forecasted Time to Tolerance Breach**: **`42.4 seconds`**
- **Summary**: Drift rate: 53.0899/hour (p=2.615e-220). Statistically significant drift detected. Forecasted time to breach: 42.4 s.

## 5. Generated Visualisations
- ![EXP_03_TEMPERATURE_calibration_transfer.png](D:\IMUCA MNI\results\EXP_03_TEMPERATURE_calibration_transfer.png)
- ![EXP_03_TEMPERATURE_residuals.png](D:\IMUCA MNI\results\EXP_03_TEMPERATURE_residuals.png)
- ![EXP_03_TEMPERATURE_timeseries_uncertainty.png](D:\IMUCA MNI\results\EXP_03_TEMPERATURE_timeseries_uncertainty.png)
