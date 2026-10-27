"""
IMUCA Detection Metrics for fault-detection benchmarking.

- Record-level confusion matrix, precision, recall, F1, false-alarm rate (FAR) and
  missed-detection rate (MDR).
- Event-level detection with explicit detection windows and the chance level implied
  by the detector's false-alarm rate (an alarm can fall inside a long window by chance).
- Detection delay in samples from fault onset to the first alarm in the window.
- False alarms stratified by operating context (steady, ramp, post-process-event transient).
"""

from __future__ import annotations
from typing import Any, Dict, Iterable, List, Optional

import numpy as np
import pandas as pd

RAMP_PHASES = ("ramp", "heating_ramp", "cooling_ramp")


def binary_metrics(pred: np.ndarray, truth: np.ndarray) -> Dict[str, Any]:
    pred = np.asarray(pred, bool)
    truth = np.asarray(truth, bool)
    tp = int(np.sum(pred & truth)); fp = int(np.sum(pred & ~truth))
    tn = int(np.sum(~pred & ~truth)); fn = int(np.sum(~pred & truth))
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = (2 * precision * recall / (precision + recall)) if precision and recall else (0.0 if (tp + fp) and (tp + fn) else None)
    return {
        "TP": tp, "FP": fp, "TN": tn, "FN": fn,
        "precision": precision, "recall": recall, "f1": f1,
        "false_alarm_rate": fp / (fp + tn) if fp + tn else None,
        "missed_detection_rate": fn / (tp + fn) if tp + fn else None,
    }


def event_detection(pred: np.ndarray, eval_df: pd.DataFrame, events: Iterable[Dict[str, Any]],
                    persistent_types: Iterable[str], persistent_window: int,
                    false_alarm_rate: Optional[float] = None, transient_tolerance: int = 0,
                    run_end_types: Iterable[str] = ()) -> List[Dict[str, Any]]:
    """
    One entry per event present in eval_df. The detection window is the event's labelled
    records for transient faults, and the first `persistent_window` samples after onset
    (by sequence number) for persistent faults. chance_detection_probability is
    1 - (1 - FAR)^window_length for the supplied FAR.
    transient_tolerance extends transient windows by that many samples after the event's last
    labelled record (detection latency allowance); run_end_types use onset -> end of run.
    """
    pred = np.asarray(pred, bool)
    persistent_types = set(persistent_types)
    run_end_types = set(run_end_types)
    ids = eval_df["label_fault_event_id"].to_numpy()
    exp = eval_df["experiment_id"].to_numpy()
    seq = eval_df["sequence_number"].to_numpy()
    out = []
    for ev in events:
        in_run = exp == ev["run_id"]
        if not in_run.any():
            continue
        if ev["fault_type"] in run_end_types:
            win = in_run & (seq >= ev["onset_sequence_number"])
        elif ev["fault_type"] in persistent_types:
            onset = ev["onset_sequence_number"]
            win = in_run & (seq >= onset) & (seq < onset + persistent_window)
        else:
            win = in_run & np.array([ev["event_id"] in s.split(";") for s in ids])
            if transient_tolerance > 0 and win.any():
                last = seq[win].max()
                win = win | (in_run & (seq > last) & (seq <= last + transient_tolerance))
        n_win = int(win.sum())
        if n_win == 0:
            continue
        hits = np.flatnonzero(pred & win)
        detected = len(hits) > 0
        delay = int(seq[hits[0]] - ev["onset_sequence_number"]) if detected else None
        chance = None if false_alarm_rate is None else float(1.0 - (1.0 - false_alarm_rate) ** n_win)
        out.append({"event_id": ev["event_id"], "fault_type": ev["fault_type"], "run_id": ev["run_id"],
                    "window_samples": n_win, "detected": detected, "delay_samples": delay,
                    "chance_detection_probability": chance, "magnitude": ev.get("magnitude")})
    return out


def summarize_events(events: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    by: Dict[str, Dict[str, Any]] = {}
    for e in events:
        b = by.setdefault(e["fault_type"], {"events": 0, "detected": 0, "delays": [], "chance": []})
        b["events"] += 1
        b["detected"] += int(e["detected"])
        if e["delay_samples"] is not None:
            b["delays"].append(e["delay_samples"])
        if e["chance_detection_probability"] is not None:
            b["chance"].append(e["chance_detection_probability"])
    return {t: {"events": b["events"], "detected": b["detected"],
                "event_recall": b["detected"] / b["events"],
                "median_delay_samples": float(np.median(b["delays"])) if b["delays"] else None,
                "max_delay_samples": int(np.max(b["delays"])) if b["delays"] else None,
                "mean_chance_detection_probability": float(np.mean(b["chance"])) if b["chance"] else None}
            for t, b in sorted(by.items())}


CONTEXTS = ("steady", "ramp", "post_event_transient", "post_fault_aftermath")


def operating_context(eval_df: pd.DataFrame, transient_samples: int, aftermath_samples: int = 0,
                      fault_column: str = "is_signal_fault") -> np.ndarray:
    """
    Context label per record for false-alarm analysis (evaluation only; uses labels):
    'post_fault_aftermath' (fault-free record within aftermath_samples after a labelled
    fault record of the same run), 'ramp' (protocol ramp phase), 'post_event_transient'
    (within transient_samples after a genuine process event such as a set-point change,
    true step or load step, or after the end of a ramp), else 'steady'. Precedence follows that order.
    """
    ctx = np.array(["steady"] * len(eval_df), dtype=object)
    phase = eval_df["protocol_phase"].to_numpy()
    seq = eval_df["sequence_number"].to_numpy()
    exp = eval_df["experiment_id"].to_numpy()
    ev = eval_df["label_process_event"].to_numpy() != "none"
    fault = eval_df[fault_column].to_numpy() if (aftermath_samples and fault_column in eval_df) else np.zeros(len(eval_df), bool)
    last_event, last_fault = {}, {}
    for i in range(len(eval_df)):
        # A genuine process event, or the end of a ramp (sensor-lag settling follows), starts a transient window
        ramp_ended = i > 0 and exp[i] == exp[i - 1] and phase[i - 1] in RAMP_PHASES and phase[i] not in RAMP_PHASES
        if ev[i] or ramp_ended:
            last_event[exp[i]] = seq[i]
        if fault[i]:
            last_fault[exp[i]] = seq[i]
        le = last_event.get(exp[i])
        lf = last_fault.get(exp[i])
        if not fault[i] and lf is not None and 0 < seq[i] - lf <= aftermath_samples:
            ctx[i] = "post_fault_aftermath"
        elif phase[i] in RAMP_PHASES:
            ctx[i] = "ramp"
        elif le is not None and 0 <= seq[i] - le < transient_samples:
            ctx[i] = "post_event_transient"
    return ctx


def false_alarms_by_context(pred: np.ndarray, truth: np.ndarray, context: np.ndarray) -> Dict[str, Dict[str, Any]]:
    pred = np.asarray(pred, bool); truth = np.asarray(truth, bool)
    out = {}
    for c in CONTEXTS:
        neg = (~truth) & (context == c)
        n = int(neg.sum())
        fa = int(np.sum(pred & neg))
        out[c] = {"negatives": n, "false_alarms": fa, "false_alarm_rate": fa / n if n else None}
    return out


def threshold_at_false_alarm_rate(scores: np.ndarray, truth: np.ndarray, target_far: float) -> float:
    """Smallest threshold whose false-alarm rate on negatives (score > threshold) is <= target."""
    neg = np.sort(np.asarray(scores, float)[~np.asarray(truth, bool)])
    if len(neg) == 0:
        return float(np.max(scores))
    allowed = int(np.floor(target_far * len(neg)))
    return float(neg[len(neg) - allowed - 1]) if allowed < len(neg) else float(neg[0])


# ==============================================================================
# Alarm episodes, episode matching and uncertainty intervals
# ==============================================================================

def alarm_episodes(alarm: np.ndarray, experiment_id: np.ndarray, gap: int = 2) -> List[Dict[str, Any]]:
    """
    Merge alarmed records into episodes: consecutive alarms in the same run separated by at
    most `gap` non-alarmed records form one episode (one operator-facing alarm).
    Indices refer to positions in the evaluated record stream.
    """
    alarm = np.asarray(alarm, bool)
    exp = np.asarray(experiment_id)
    eps: List[Dict[str, Any]] = []
    cur = None
    for i in np.flatnonzero(alarm):
        if cur is not None and exp[i] == cur["run"] and i - cur["end"] <= gap + 1:
            cur["end"] = i
        else:
            if cur is not None:
                eps.append(cur)
            cur = {"run": exp[i], "start": int(i), "end": int(i)}
    if cur is not None:
        eps.append(cur)
    return eps


def fault_active_mask(eval_df: pd.DataFrame, tolerance: int = 2, fault_column: str = "is_signal_fault") -> np.ndarray:
    """Fault-active records extended by `tolerance` records after each fault ends (same run)."""
    f = eval_df[fault_column].to_numpy().astype(bool)
    exp = eval_df["experiment_id"].to_numpy()
    out = f.copy()
    for s in range(1, tolerance + 1):
        shifted = np.zeros_like(f)
        shifted[s:] = f[:-s] & (exp[s:] == exp[:-s])
        out |= shifted
    return out


def classify_episodes(episodes: List[Dict[str, Any]], active: np.ndarray) -> List[bool]:
    """An episode is a true alarm if any of its records overlaps fault-active records."""
    return [bool(active[e["start"]:e["end"] + 1].any()) for e in episodes]


def wilson_interval(k: int, n: int, z: float = 1.96):
    """Wilson score interval for a binomial proportion k/n."""
    if n == 0:
        return (None, None)
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (float(max(0.0, centre - half)), float(min(1.0, centre + half)))


def poisson_rate_interval(count: int, exposure: float, alpha: float = 0.05):
    """Exact (Garwood) confidence interval for a Poisson rate count/exposure."""
    from scipy.stats import chi2
    if exposure <= 0:
        return (None, None)
    lo = 0.0 if count == 0 else chi2.ppf(alpha / 2, 2 * count) / 2
    hi = chi2.ppf(1 - alpha / 2, 2 * count + 2) / 2
    return (float(lo / exposure), float(hi / exposure))


def bootstrap_by_run(per_run: pd.DataFrame, stat, n_boot: int = 2000, seed: int = 0):
    """Percentile bootstrap (95 %) of stat(resampled per-run table), resampling whole runs."""
    rng = np.random.default_rng(seed)
    n = len(per_run)
    if n == 0:
        return (None, None)
    vals = []
    for _ in range(n_boot):
        v = stat(per_run.iloc[rng.integers(0, n, n)])
        if v is not None and np.isfinite(v):
            vals.append(v)
    if not vals:
        return (None, None)
    return (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5)))


def event_windows(eval_df: pd.DataFrame, events: Iterable[Dict[str, Any]], persistent_types: Iterable[str],
                  persistent_window: int, transient_tolerance: int = 0, run_end_types: Iterable[str] = ()) -> List[Dict[str, Any]]:
    """
    Precompute each event's detection window (record positions in eval_df) with the same rules
    as `event_detection`, so many alarm configurations can be scored quickly.
    """
    persistent_types = set(persistent_types)
    run_end_types = set(run_end_types)
    exp = eval_df["experiment_id"].to_numpy()
    seq = eval_df["sequence_number"].to_numpy()
    ids = eval_df["label_fault_event_id"].to_numpy()
    by_run: Dict[Any, np.ndarray] = {r: np.flatnonzero(exp == r) for r in pd.unique(exp)}
    out = []
    for ev in events:
        pos = by_run.get(ev["run_id"])
        if pos is None:
            continue
        s = seq[pos]
        onset = ev["onset_sequence_number"]
        if ev["fault_type"] in run_end_types:
            w = pos[s >= onset]
        elif ev["fault_type"] in persistent_types:
            w = pos[(s >= onset) & (s < onset + persistent_window)]
        else:
            w = pos[np.array([ev["event_id"] in x.split(";") for x in ids[pos]])]
            if transient_tolerance > 0 and len(w):
                last = seq[w].max()
                w = np.r_[w, pos[(s > last) & (s <= last + transient_tolerance)]]
        if len(w):
            out.append({"event": ev, "positions": np.sort(w), "onset": onset})
    return out


def detect_with_windows(pred: np.ndarray, windows: List[Dict[str, Any]], seq: np.ndarray,
                        false_alarm_rate: Optional[float] = None) -> List[Dict[str, Any]]:
    """Event detection on precomputed windows (identical result to `event_detection`)."""
    pred = np.asarray(pred, bool)
    out = []
    for w in windows:
        p = w["positions"]
        hits = p[pred[p]]
        ev = w["event"]
        out.append({"event_id": ev["event_id"], "fault_type": ev["fault_type"], "run_id": ev["run_id"],
                    "window_samples": int(len(p)), "detected": bool(len(hits)),
                    "delay_samples": int(seq[hits[0]] - w["onset"]) if len(hits) else None,
                    "first_alarm_position": int(hits[0]) if len(hits) else None,
                    "chance_detection_probability": None if false_alarm_rate is None else float(1.0 - (1.0 - false_alarm_rate) ** len(p)),
                    "magnitude": ev.get("magnitude")})
    return out
