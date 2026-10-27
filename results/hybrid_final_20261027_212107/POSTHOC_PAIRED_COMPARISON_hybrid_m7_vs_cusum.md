# Post-hoc paired comparison: hybrid_m7 vs cusum

> Post-hoc analysis of the saved alarms of a completed final evaluation (no detector was re-run or re-tuned). The pre-specified result is the marginal comparison in REPORT.md; this paired run-level bootstrap uses the fact that both detectors were scored on the same runs.

| Measurand | F1 a | F1 b | Diff a-b | 95 % paired bootstrap CI | P(diff <= 0) | FA/h diff | 95 % CI |
|---|---|---|---|---|---|---|---|
| voltage_V | 0.825 | 0.910 | -0.085 | [-0.147, -0.029] | 0.999 | +2.55 | [+1.73, +3.47] |
| current_mA | 0.911 | 0.738 | +0.173 | [+0.114, +0.234] | 0.000 | +1.01 | [+0.41, +1.76] |
| temperature_C | 0.750 | 0.586 | +0.164 | [+0.062, +0.273] | 0.000 | +2.89 | [+1.88, +4.08] |

Runs resampled per measurand: voltage_V 84, current_mA 84, temperature_C 87; 4000 bootstrap resamples.