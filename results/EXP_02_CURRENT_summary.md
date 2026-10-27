# IMUCA Metrology Analysis Report: `EXP_02_CURRENT`
> **Generated at**: 2026-10-25T06:49:02.567832+00:00 | **IMUCA Framework**: v1.0.0
> **Disclaimer**: SYNTHETIC EXPERIMENT: For algorithm validation only.

## 1. Data Quality Screening
- **Total Records Analyzed**: 120
- **Clean Records**: 120 (100.0%)
- **Integrity Error Flags**: 0
- **Warning Flags (Retained for audit)**: 0

## 2. Measurement Accuracy & Calibration Performance
| Metric | Uncalibrated Baseline | Post-Calibration (Held-out Test) | Improvement |
| :--- | :--- | :--- | :--- |
| **Mean Bias** | `30.68` | `0.0136` | - |
| **MAE** | `30.68` | `0.3996` | **98.9% reduction** |
| **RMSE** | `31.95` | `0.506` | **98.6% reduction** |
| **Max Absolute Error** | `45.47` | `1.418` | - |

**Model Adopted**: `linear` (Degree 1) | **Formula**: `y_cal = -14.8085 + 0.985325 * x` | **$R^2$**: `0.999999`

## 3. GUM Uncertainty Budget (JCGM 100:2008)
- **Nominal Value**: `1000.0 mA`
- **Combined Standard Uncertainty ($u_c$)**: `5.027 mA`
- **Expanded Uncertainty ($U, k=2.00$)**: `10.05 mA`
- **Dominant Contributor**: `Shunt Resistor Tolerance` (98.9% variance share)
- **Metrologically Rounded Result**: **(1000 +/- 11) mA (k=2.00, 95% confidence)**

| Uncertainty Source | Type | Distribution | Standard Uncertainty $u_i$ | Sens. Coeff. $c_i$ | Contribution | Share % |
| :--- | :---: | :--- | :--- | :--- | :--- | :--- |
| Current Repeatability (Type A) | Type A | NORMAL | `0.1345 mA` | `1` | `0.1345` | `0.1%` |
| Shunt Voltage Drop | Type B | NORMAL | `5e-05 V` | `1e+04` | `0.5` | `1.0%` |
| Shunt Resistor Tolerance | Type B | RECTANGULAR | `0.0005 Ohm` | `-1e+04` | `5` | `98.9%` |

## 5. Generated Visualisations
- ![EXP_02_CURRENT_calibration_transfer.png](D:\IMUCA MNI\results\EXP_02_CURRENT_calibration_transfer.png)
- ![EXP_02_CURRENT_residuals.png](D:\IMUCA MNI\results\EXP_02_CURRENT_residuals.png)
- ![EXP_02_CURRENT_timeseries_uncertainty.png](D:\IMUCA MNI\results\EXP_02_CURRENT_timeseries_uncertainty.png)
