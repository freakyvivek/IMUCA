# Post-hoc paired comparison: hybrid_m7 vs segment_setpoint

> Post-hoc analysis of the saved alarms of a completed final evaluation (no detector was re-run or re-tuned). The pre-specified result is the marginal comparison in REPORT.md; this paired run-level bootstrap uses the fact that both detectors were scored on the same runs.

| Measurand | F1 a | F1 b | Diff a-b | 95 % paired bootstrap CI | P(diff <= 0) | FA/h diff | 95 % CI |
|---|---|---|---|---|---|---|---|
| voltage_V | 0.825 | 0.630 | +0.195 | [+0.128, +0.263] | 0.000 | +1.48 | [+0.79, +2.25] |
| current_mA | 0.911 | 0.508 | +0.403 | [+0.341, +0.474] | 0.000 | -7.65 | [-9.60, -5.83] |
| temperature_C | 0.750 | 0.612 | +0.138 | [+0.064, +0.214] | 0.000 | -1.97 | [-3.15, -0.69] |

Runs resampled per measurand: voltage_V 84, current_mA 84, temperature_C 87; 4000 bootstrap resamples.