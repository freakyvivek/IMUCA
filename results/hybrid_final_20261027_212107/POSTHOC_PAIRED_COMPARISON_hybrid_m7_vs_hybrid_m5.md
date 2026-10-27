# Post-hoc paired comparison: hybrid_m7 vs hybrid_m5

> Post-hoc analysis of the saved alarms of a completed final evaluation (no detector was re-run or re-tuned). The pre-specified result is the marginal comparison in REPORT.md; this paired run-level bootstrap uses the fact that both detectors were scored on the same runs.

| Measurand | F1 a | F1 b | Diff a-b | 95 % paired bootstrap CI | P(diff <= 0) | FA/h diff | 95 % CI |
|---|---|---|---|---|---|---|---|
| voltage_V | 0.825 | 0.820 | +0.005 | [-0.038, +0.047] | 0.417 | +1.01 | [+0.29, +1.78] |
| current_mA | 0.911 | 0.831 | +0.080 | [+0.023, +0.142] | 0.002 | +0.34 | [-0.27, +0.99] |
| temperature_C | 0.750 | 0.598 | +0.152 | [+0.079, +0.231] | 0.000 | -0.55 | [-1.31, +0.24] |

Runs resampled per measurand: voltage_V 84, current_mA 84, temperature_C 87; 4000 bootstrap resamples.