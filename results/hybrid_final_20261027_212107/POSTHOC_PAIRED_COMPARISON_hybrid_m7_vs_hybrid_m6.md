# Post-hoc paired comparison: hybrid_m7 vs hybrid_m6

> Post-hoc analysis of the saved alarms of a completed final evaluation (no detector was re-run or re-tuned). The pre-specified result is the marginal comparison in REPORT.md; this paired run-level bootstrap uses the fact that both detectors were scored on the same runs.

| Measurand | F1 a | F1 b | Diff a-b | 95 % paired bootstrap CI | P(diff <= 0) | FA/h diff | 95 % CI |
|---|---|---|---|---|---|---|---|
| voltage_V | 0.825 | 0.825 | +0.000 | [+0.000, +0.000] | 1.000 | +0.00 | [+0.00, +0.00] |
| current_mA | 0.911 | 0.913 | -0.002 | [-0.009, +0.001] | 0.765 | +0.07 | [+0.00, +0.21] |
| temperature_C | 0.750 | 0.752 | -0.002 | [-0.007, +0.001] | 0.936 | +0.06 | [+0.00, +0.20] |

Runs resampled per measurand: voltage_V 84, current_mA 84, temperature_C 87; 4000 bootstrap resamples.