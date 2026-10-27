# Post-hoc paired comparison: hybrid_m6 vs hybrid_m5

> Post-hoc analysis of the saved alarms of a completed final evaluation (no detector was re-run or re-tuned). The pre-specified result is the marginal comparison in REPORT.md; this paired run-level bootstrap uses the fact that both detectors were scored on the same runs.

| Measurand | F1 a | F1 b | Diff a-b | 95 % paired bootstrap CI | P(diff <= 0) | FA/h diff | 95 % CI |
|---|---|---|---|---|---|---|---|
| voltage_V | 0.847 | 0.815 | +0.032 | [-0.010, +0.078] | 0.072 | +0.47 | [-0.33, +1.29] |
| current_mA | 0.867 | 0.858 | +0.009 | [-0.054, +0.074] | 0.395 | +0.81 | [+0.14, +1.61] |
| temperature_C | 0.767 | 0.655 | +0.112 | [+0.054, +0.172] | 0.000 | -0.80 | [-1.53, -0.06] |

Runs resampled per measurand: voltage_V 84, current_mA 84, temperature_C 87; 4000 bootstrap resamples.