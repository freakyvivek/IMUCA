"""
IMUCA CUSUM investigation and tuning helpers.

The detector being tuned is the existing two-sided CUSUM inside
`src.imuca.validation.analyze_temporal_drift`; this module only chooses its parameters
(k, h in units of sigma, and a causal sigma estimate) and evaluates alarms.

Root cause of the Milestone-2 false alarms: with k = 0.5 sigma and h = 4 sigma the
two-sided in-control average run length (ARL0) is about 170 samples (Siegmund
approximation), so on 1200-1800-sample runs an alarm is practically certain even
without drift.
"""

from __future__ import annotations
from typing import Any, Dict, Optional

import numpy as np

from src.imuca.validation import analyze_temporal_drift


def siegmund_arl_one_sided(k: float, h: float, mu: float = 0.0) -> float:
    """
    Siegmund (1985) approximation of the ARL of a one-sided CUSUM on N(mu, 1) data with
    reference value k and decision interval h (both in sigma units):
        ARL = (exp(-2 D b) + 2 D b - 1) / (2 D^2),  D = mu - k,  b = h + 1.166
    (D = 0 limit: b^2).
    """
    d = mu - k
    b = h + 1.166
    if abs(d) < 1e-12:
        return b * b
    return (np.exp(-2 * d * b) + 2 * d * b - 1) / (2 * d * d)


def siegmund_arl_two_sided(k: float, h: float, mu: float = 0.0) -> float:
    """Two-sided ARL from the one-sided ARLs: 1/ARL = 1/ARL+ + 1/ARL-."""
    a_pos = siegmund_arl_one_sided(k, h, mu)
    a_neg = siegmund_arl_one_sided(k, h, -mu)
    return 1.0 / (1.0 / a_pos + 1.0 / a_neg)


def run_cusum(t_s: np.ndarray, e: np.ndarray, k: float, h: float,
              baseline_fraction: float = 0.1, sigma_mode: str = "baseline_window",
              onset_s: Optional[float] = None, min_baseline: int = 10) -> Dict[str, Any]:
    """
    Run the existing detector on one error series.
    sigma_mode='baseline_window': target = mean and sigma = std of the first
        `baseline_fraction` of the series (causal; uses no future data).
    sigma_mode='existing_default': target = median of the baseline window and sigma from
        the whole-run detrended residuals (the Milestone-2 benchmark configuration).
    min_baseline: minimum number of baseline samples (default 10, the Milestone-4 setting).
    """
    t_s = np.asarray(t_s, float)
    e = np.asarray(e, float)
    nb = max(min_baseline, int(len(e) * baseline_fraction))
    if sigma_mode == "baseline_window":
        target = float(np.mean(e[:nb]))
        sigma = float(np.std(e[:nb], ddof=1))
    elif sigma_mode == "existing_default":
        target = float(np.median(e[:nb]))
        sigma = None
    else:
        raise ValueError(sigma_mode)
    res = analyze_temporal_drift(t_s, e, nominal_target=target, cusum_k_sigma=k, cusum_h_sigma=h, cusum_sigma=sigma)
    alarm_t = float(t_s[res.shift_sample_index]) if res.shift_sample_index is not None else None
    out = {"alarm": bool(res.cusum_detected_shift), "alarm_time_s": alarm_t,
           "regression_alarm": bool(res.is_drift_significant), "sigma_used": sigma, "target": target,
           "baseline_samples": nb}
    if onset_s is not None:
        out["alarm_before_onset"] = alarm_t is not None and alarm_t < onset_s
        out["delay_s"] = (alarm_t - onset_s) if (alarm_t is not None and alarm_t >= onset_s) else None
    return out


def cusum_max_statistic(e: np.ndarray, target: float, sigma: float, k: float) -> np.ndarray:
    """
    Running max(S+, S-) of the two-sided CUSUM used in analyze_temporal_drift, in sigma units:
        S+[i] = max(0, S+[i-1] + (e[i]-target)/sigma - k),  S-[i] = max(0, S-[i-1] - (e[i]-target)/sigma - k).
    The existing detector alarms at the first i with max(S+, S-) > h.
    """
    z = (np.asarray(e, float) - target) / sigma
    sp = sn = 0.0
    out = np.empty(len(z))
    for i, v in enumerate(z):
        sp = max(0.0, sp + v - k)
        sn = max(0.0, sn - v - k)
        out[i] = sp if sp > sn else sn
    return out


def first_crossings(stat: np.ndarray, h_values) -> Dict[float, Optional[int]]:
    """First index where `stat` exceeds each h (None when never)."""
    out = {}
    for h in h_values:
        above = stat > h
        out[h] = int(np.argmax(above)) if above.any() else None
    return out
