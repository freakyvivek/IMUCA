# IMUCA Metrology Analysis Report: `EXP_01_VOLTAGE`
> **Generated at**: 2026-10-25T06:45:14.711408+00:00 | **IMUCA Framework**: v1.0.0
> **Disclaimer**: SYNTHETIC EXPERIMENT: For algorithm validation only.

## 1. Data Quality Screening
- **Total Records Analyzed**: 100
- **Clean Records**: 100 (100.0%)
- **Integrity Error Flags**: 0
- **Warning Flags (Retained for audit)**: 0

## 2. Measurement Accuracy & Calibration Performance
| Metric | Uncalibrated Baseline | Post-Calibration (Held-out Test) | Improvement |
| :--- | :--- | :--- | :--- |
| **Mean Bias** | `0.0104` | `-8.471e-05` | - |
| **MAE** | `0.0104` | `0.0008667` | **91.3% reduction** |
| **RMSE** | `0.01083` | `0.001057` | **89.9% reduction** |
| **Max Absolute Error** | `0.01614` | `0.002262` | - |

**Model Adopted**: `linear` (Degree 1) | **Formula**: `y_cal = -0.00476924 + 0.997928 * x` | **$R^2$**: `0.999999`

## 3. GUM Uncertainty Budget (JCGM 100:2008)
- **Nominal Value**: `5.0 V`
- **Combined Standard Uncertainty ($u_c$)**: `0.003023 V`
- **Expanded Uncertainty ($U, k=2.00$)**: `0.006046 V`
- **Dominant Contributor**: `DUT Specification Tolerance` (91.2% variance share)
- **Metrologically Rounded Result**: **(5.0000 +/- 0.0061) V (k=2.00, 95% confidence)**

| Uncertainty Source | Type | Distribution | Standard Uncertainty $u_i$ | Sens. Coeff. $c_i$ | Contribution | Share % |
| :--- | :---: | :--- | :--- | :--- | :--- | :--- |
| Repeatability (Type A) | Type A | NORMAL | `0.0003712 V` | `1` | `0.0003712` | `1.5%` |
| Display Resolution | Type B | RECTANGULAR | `0.0005774 V` | `1` | `0.0005774` | `3.6%` |
| DUT Specification Tolerance | Type B | RECTANGULAR | `0.002887 V` | `1` | `0.002887` | `91.2%` |
| Reference Standard (Calibrated) | Type B | NORMAL | `0.0005 V` | `1` | `0.0005` | `2.7%` |
| Ambient Temperature Effect | Type B | RECTANGULAR | `0.0002887 V` | `1` | `0.0002887` | `0.9%` |

## 5. Generated Visualisations
- ![EXP_01_VOLTAGE_calibration_transfer.png](D:\IMUCA MNI\results\EXP_01_VOLTAGE_calibration_transfer.png)
- ![EXP_01_VOLTAGE_residuals.png](D:\IMUCA MNI\results\EXP_01_VOLTAGE_residuals.png)
- ![EXP_01_VOLTAGE_timeseries_uncertainty.png](D:\IMUCA MNI\results\EXP_01_VOLTAGE_timeseries_uncertainty.png)
