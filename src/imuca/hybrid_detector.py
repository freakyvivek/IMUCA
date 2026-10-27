"""
IMUCA Hybrid Fault Detector (research component; not used by the application).

Pipeline per acquisition run:
  0. Integrity rules (deterministic, causal): missing, non-finite, duplicate/out-of-order
     sequence, sequence/time gap, non-OK status. Flagged records leave the signal stream.
  1. Transient component (spikes, abrupt changes): the existing DataQualityAssessor applied
     per protocol segment (segment-aware; uses the whole segment, so decisions for a record
     are final when its segment ends).
  2. Persistent component (offset, gain): targeted gradient-boosted trees on causal features.
  3. Stuck component: targeted GBT, a statistical identical-run rule, or both (selected on
     validation data).
  4. Drift component: the existing analyze_temporal_drift CUSUM (tuned k, h) on the static-
     calibrated error vs the reference, using only records not explained by components 1-2,
     excluding protocol transitions, and re-baselined after each persistent alarm episode.

Alarm combination (no double counting):
  - Each record carries at most one alarm. When several components fire on the same record
    the category follows the precedence transient > stuck > persistent > drift.
  - A drift alarm whose onset falls inside, or within `explain_window` records after, a
    transient / stuck / persistent episode is attributed to that episode and suppressed.
  - Consecutive alarmed records (gap <= episode_gap) form one alarm episode.

Milestone 7 additions:
  - settling_suppression: suppress segment-detector alarms (but not curvature spikes) during
    settling/transition phases, reducing settling false alarms.
  - low_confidence_category: when enabled, episodes shorter than a threshold with ambiguous
    evidence are labelled 'uncertain' rather than confidently classified.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from src.imuca.data_quality import DataQualityAssessor
from src.imuca.cusum_tuning import run_cusum
from src.imuca.detection_metrics import alarm_episodes

NONSTATIONARY_PHASES = ("ramp", "heating_ramp", "cooling_ramp", "plateau_settling")
SIGNAL_ISSUE_TYPES = ("OUTLIER", "ABRUPT_CHANGE", "OUT_OF_RANGE")
CATEGORY_PRECEDENCE = ("transient", "stuck", "persistent", "drift")
FAULT_CATEGORY = {"isolated_spike": "transient", "abrupt_change": "transient", "stuck_signal": "stuck",
                  "offset_shift": "persistent", "gain_change": "persistent", "gradual_drift": "drift"}
SEGMENT_MODES = ("setpoint_blocks", "phase_blocks", "phase_blocks_stationary_only")
STUCK_MODES = ("gbt", "rule", "gbt_or_rule")
STUCK_EVIDENCE_RUN = 3  # identical readings needed before a GBT alarm is read as 'stuck'


@dataclass
class HybridSettings:
    segment_mode: str
    stuck_mode: str
    gbt_threshold: float
    stuck_alpha: float
    cusum_k: float
    cusum_h: float
    cusum_baseline_fraction: float = 0.1
    cusum_min_baseline: int = 30
    cusum_min_series: int = 60
    transition_exclusion: int = 0
    cusum_mode: str = "run"          # "run": one baseline per run; "segment": re-baseline at every set-point change
    segment_mad_threshold: float = 3.5  # modified-z threshold of the segment component (existing default 3.5)
    explain_window: int = 10
    rebaseline_gap: int = 5
    episode_gap: int = 2
    # --- Milestone 6 options (defaults reproduce Milestone-5 behaviour exactly) ---
    drift_lifecycle: str = "latched"         # "latched" | "hysteresis"
    clear_window: int = 60                   # hysteresis: samples in the clearance mean
    clear_z: float = 2.0                     # hysteresis: clear when |mean - target| < clear_z * sigma / sqrt(clear_window)
    clear_sigma: float = 0.0                 # hysteresis: if > 0, clear when |mean - target| < clear_sigma * sigma instead
    attribution: str = "first_alarm"         # "first_alarm" | "confirmed"
    confirm_window: int = 30                 # confirmed: samples compared before / after an episode
    confirm_k: float = 4.0                   # confirmed: level shift (in sigma) that marks a persistent fault
    confirm_delay: int = 0                   # confirmed: the shift must still be present this many samples after the episode
    transient_extra: str = "none"            # "none" | "curvature_nonstationary" | "curvature_all"
    transient_transition_window: int = 0     # samples after a set-point change (segments without explicit settling) treated as non-stationary
    explain_before: int = 0                  # drift alarms starting up to this many records BEFORE another episode are explained by it
    attribution_source: str = "signal"       # confirmed attribution on the raw "signal" or the reference-based "error"
    suppress_persistent_nonstationary: bool = False  # ignore offset/gain GBT alarms during protocol ramps / settling
    curvature_threshold: float = 8.0         # robust z of the second difference
    # --- Milestone 7 options (defaults reproduce Milestone-6 behaviour exactly) ---
    settling_suppression: bool = False       # suppress SEGMENT-detector alarms during settling phases (curvature kept)
    low_confidence_min_duration: int = 0     # if > 0, episodes shorter than this with ambiguous evidence get 'uncertain' category
    low_confidence_min_zscore: float = 0.0   # confirmed: minimum z-score of the level shift to classify confidently

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ==============================================================================
# Components
# ==============================================================================

def segment_labels(run: pd.DataFrame, mode: str) -> np.ndarray:
    """Contiguous protocol segments: set-point blocks, or set-point x protocol-phase blocks."""
    key = run["setpoint_index"].astype(str)
    if mode != "setpoint_blocks":
        key = key + "|" + run["protocol_phase"].astype(str)
    return (key != key.shift()).cumsum().to_numpy()


def segment_transient_flags(clean: pd.DataFrame, measurand: str, base_cfg: Dict[str, Any], mode: str,
                            mad_threshold: Optional[float] = None) -> np.ndarray:
    """Existing DataQualityAssessor per protocol segment; signal issue types only."""
    if mode not in SEGMENT_MODES:
        raise ValueError(mode)
    mc = base_cfg["measurands"][measurand]
    assessor = DataQualityAssessor(mad_threshold=base_cfg["quality"]["mad_threshold"] if mad_threshold is None else mad_threshold,
                                   nominal_sampling_period_s=1.0 / base_cfg["quality"]["nominal_sampling_rate_hz"])
    flags = np.zeros(len(clean), bool)
    seg = segment_labels(clean.reset_index(drop=True), mode)
    for _, idx in pd.Series(np.arange(len(clean))).groupby(seg).indices.items():
        sub = clean.iloc[idx].reset_index(drop=True)
        rep = assessor.assess(sub[[measurand, "sequence_number", "elapsed_ms", "status"]], measurand_col=measurand,
                              range_limits=(mc["min_range"], mc["max_range"]),
                              max_rate_of_change=mc["max_rate_of_change_per_sec"], ground_truth_fault_col=None)
        for iss in rep.issues:
            if iss.issue_type in SIGNAL_ISSUE_TYPES:
                flags[idx[iss.record_index]] = True
    if mode == "phase_blocks_stationary_only":
        flags &= ~clean["protocol_phase"].isin(NONSTATIONARY_PHASES).to_numpy()
    return flags


def segment_scores(clean: pd.DataFrame, measurand: str, base_cfg: Dict[str, Any], mode: str,
                   base_threshold: float = 3.5) -> Dict[str, np.ndarray]:
    """
    Run the existing DataQualityAssessor once per segment at `base_threshold` and keep, per
    record, the modified-z score of MAD outliers (0 if not an outlier at the base threshold)
    and the threshold-independent flags (rate of change, out of range). Flags for any MAD
    threshold >= base_threshold follow from `segment_flags_from_scores`.
    """
    if mode not in SEGMENT_MODES:
        raise ValueError(mode)
    mc = base_cfg["measurands"][measurand]
    assessor = DataQualityAssessor(mad_threshold=base_threshold,
                                   nominal_sampling_period_s=1.0 / base_cfg["quality"]["nominal_sampling_rate_hz"])
    z = np.zeros(len(clean))
    other = np.zeros(len(clean), bool)
    seg = segment_labels(clean.reset_index(drop=True), mode)
    for _, idx in pd.Series(np.arange(len(clean))).groupby(seg).indices.items():
        sub = clean.iloc[idx].reset_index(drop=True)
        rep = assessor.assess(sub[[measurand, "sequence_number", "elapsed_ms", "status"]], measurand_col=measurand,
                              range_limits=(mc["min_range"], mc["max_range"]),
                              max_rate_of_change=mc["max_rate_of_change_per_sec"], ground_truth_fault_col=None)
        for iss in rep.issues:
            if iss.issue_type == "OUTLIER":
                zval = float(iss.description.split("=")[1].split(" ")[0])
                z[idx[iss.record_index]] = max(z[idx[iss.record_index]], zval)
            elif iss.issue_type in ("ABRUPT_CHANGE", "OUT_OF_RANGE"):
                other[idx[iss.record_index]] = True
    nonstat = clean["protocol_phase"].isin(NONSTATIONARY_PHASES).to_numpy()
    return {"z": z, "other": other, "nonstationary": nonstat, "base_threshold": base_threshold, "mode": mode}


def segment_flags_from_scores(scores: Dict[str, np.ndarray], threshold: float) -> np.ndarray:
    if threshold < scores["base_threshold"]:
        raise ValueError("threshold below the base threshold used to compute the scores")
    flags = (scores["z"] > threshold) | scores["other"]
    if scores["mode"] == "phase_blocks_stationary_only":
        flags &= ~scores["nonstationary"]
    return flags


def curvature_scores(x: np.ndarray, setpoint_index: np.ndarray, floor: float, window: int = 120, guard: int = 3) -> np.ndarray:
    """
    Causal robust z-score of the second difference d2[k] = x[k] - 2x[k-1] + x[k-2]. Smooth ramps
    and exponential settling have small curvature, while a spike produces |d2| ~ its magnitude.
    The scale uses PAST |d2| only (median and mean based, floored); scores are zeroed for
    `guard` records after a protocol set-point change (genuine steps).
    """
    x = pd.Series(np.asarray(x, dtype=float))
    d2 = (x - 2 * x.shift(1) + x.shift(2)).abs()
    past = d2.shift(1)
    med = past.rolling(window, min_periods=20).median() * 1.4826
    mean = past.rolling(window, min_periods=20).mean() * 1.2533
    floor2 = floor * np.sqrt(6.0)
    scale = np.maximum(np.maximum(med.fillna(floor2), mean.fillna(floor2)), floor2)
    z = (d2 / scale).fillna(0.0).to_numpy(copy=True)
    sp = np.asarray(setpoint_index)
    change = np.flatnonzero(np.r_[False, sp[1:] != sp[:-1]])
    for c in change:
        z[c:c + guard] = 0.0
    z[:2] = 0.0
    return z


def confirm_categories(category: np.ndarray, alarm: np.ndarray, x: np.ndarray, setpoint_index: np.ndarray,
                       protocol_phase: np.ndarray, floor: float, settings: "HybridSettings",
                       experiment_id: np.ndarray) -> np.ndarray:
    """
    Confirmed attribution: an episode provisionally labelled 'transient' or 'persistent' becomes
    'persistent' when the signal level after the episode (or, if the episode reaches the end of
    its protocol segment and is at least confirm_window long, inside it) differs from the level
    before the episode by more than confirm_k robust sigmas; otherwise 'transient'. Episodes in
    non-stationary phases, or without enough same-segment context, keep their provisional label.
    The category becomes final confirm_window samples after the episode ends.
    """
    out = category.copy()
    L = settings.confirm_window
    sp = np.asarray(setpoint_index)
    for ep in alarm_episodes(alarm, experiment_id, settings.episode_gap):
        s0, e0 = ep["start"], ep["end"]
        cat0 = category[s0]
        if cat0 not in ("transient", "persistent") or protocol_phase[s0] in NONSTATIONARY_PHASES:
            continue
        seg = sp[s0]
        pre = np.arange(max(0, s0 - L), s0)
        pre = pre[(sp[pre] == seg) & ~alarm[pre]]
        if len(pre) < 5:
            continue
        d = np.diff(x[pre])
        sigma = max(1.4826 * float(np.median(np.abs(d))) / np.sqrt(2.0), floor) if len(d) else floor
        level = float(np.median(x[pre]))
        D = int(getattr(settings, "confirm_delay", 0))
        post = np.arange(e0 + 1 + D, min(len(x), e0 + 1 + D + L))
        post = post[(sp[post] == seg) & ~alarm[post]]
        if len(post) >= 5:
            shifted = abs(float(np.median(x[post])) - level) > settings.confirm_k * sigma
        elif e0 - s0 + 1 >= L + D:
            shifted = abs(float(np.median(x[s0 + D:e0 + 1])) - level) > settings.confirm_k * sigma
        else:
            continue
        new = "persistent" if shifted else "transient"
        span = np.arange(s0, e0 + 1)
        span = span[np.isin(category[span], ("transient", "persistent"))]
        out[span] = new
    return out


def confirm_categories_error(category: np.ndarray, alarm: np.ndarray, err: np.ndarray, usable: np.ndarray,
                             protocol_phase: np.ndarray, floor: float, settings: "HybridSettings",
                             experiment_id: np.ndarray) -> np.ndarray:
    """
    Confirmed attribution on the static-calibrated error against the reference. The fault-free
    error is level-independent, so before/after windows may span set-point changes; only usable
    records (finite, outside protocol transitions, not alarmed) are compared.
    """
    out = category.copy()
    L = settings.confirm_window
    D = int(getattr(settings, "confirm_delay", 0))
    ok = usable & np.isfinite(err)
    for ep in alarm_episodes(alarm, experiment_id, settings.episode_gap):
        s0, e0 = ep["start"], ep["end"]
        if category[s0] not in ("transient", "persistent"):
            continue
        pre = np.flatnonzero(ok[:s0] & ~alarm[:s0])[-L:]
        if len(pre) < 5:
            continue
        d = np.diff(err[pre])
        sigma = max(1.4826 * float(np.median(np.abs(d))) / np.sqrt(2.0), floor) if len(d) else floor
        level = float(np.median(err[pre]))
        cand = np.flatnonzero(ok & ~alarm)
        post = cand[cand > e0 + D][:L]
        if len(post) >= 5:
            shifted = abs(float(np.median(err[post])) - level) > settings.confirm_k * sigma
        elif e0 - s0 + 1 >= L + D:
            in_ep = np.flatnonzero(ok[s0 + D:e0 + 1]) + (s0 + D)
            if len(in_ep) >= 5:
                shifted = abs(float(np.median(err[in_ep])) - level) > settings.confirm_k * sigma
            else:
                continue
        else:
            continue
        span = np.arange(s0, e0 + 1)
        span = span[np.isin(category[span], ("transient", "persistent"))]
        out[span] = "persistent" if shifted else "transient"
    return out


def stuck_rule_flags(features: pd.DataFrame, alpha: float) -> np.ndarray:
    """
    Causal identical-run rule: with p0 the past share of zero first differences (records
    k-329..k-30, clipped to [0.02, 0.95]), alarm once the current run of identical readings L
    satisfies p0**L <= alpha, i.e. L >= ceil(log(alpha) / log(p0)).
    """
    run_len = np.expm1(features["f_identical_run"].to_numpy())
    p0 = features["f_frac_zero_d1_300"].fillna(features["f_frac_zero_d1_30"]).fillna(0.5).clip(0.02, 0.95).to_numpy()
    need = np.ceil(np.log(alpha) / np.log(p0))
    return run_len >= need


def transition_mask(clean: pd.DataFrame, window: int) -> np.ndarray:
    """
    Records in non-stationary protocol phases, plus records within `window` samples after a
    set-point change into a segment that has no explicit settling phase (plateau protocols
    already mark their settling records as 'plateau_settling').
    """
    phase_arr = clean["protocol_phase"].to_numpy()
    out = np.isin(phase_arr, NONSTATIONARY_PHASES)
    sp = clean["setpoint_index"].to_numpy()
    seq = clean["sequence_number"].to_numpy()
    last = None
    for i in range(len(clean)):
        if i > 0 and sp[i] != sp[i - 1]:
            last = seq[i]
        if last is not None and seq[i] - last < window and not str(phase_arr[i]).startswith("plateau_"):
            out[i] = True
    return out


def setpoint_change_positions(clean: pd.DataFrame) -> np.ndarray:
    sp = clean["setpoint_index"].to_numpy()
    return np.flatnonzero(np.r_[False, sp[1:] != sp[:-1]])


def drift_component(t_s: np.ndarray, err: np.ndarray, usable: np.ndarray, episodes: List[Dict[str, int]],
                    settings: HybridSettings, segment_starts: Optional[np.ndarray] = None) -> np.ndarray:
    """
    CUSUM drift alarms (latched until the next re-baseline point or the end of the run).
    The usable error series is split at the start of each persistent episode; the next
    sub-series begins `rebaseline_gap` records after that episode ends. With
    settings.cusum_mode == 'segment' it is also split at every set-point change.
    """
    n = len(err)
    alarm = np.zeros(n, bool)
    bounds = [(0, n)]
    if settings.cusum_mode == "segment" and segment_starts is not None and len(segment_starts):
        cuts = [0, *[int(x) for x in segment_starts], n]
        bounds = [(a, b) for a, b in zip(cuts[:-1], cuts[1:]) if b > a]
    elif settings.cusum_mode not in ("run", "segment"):
        raise ValueError(settings.cusum_mode)
    for ep in sorted(episodes, key=lambda e: e["start"]):
        for j, (s0, e0) in enumerate(bounds):
            if s0 <= ep["start"] < e0:
                bounds[j:j + 1] = [(s0, ep["start"]), (min(e0, ep["end"] + 1 + settings.rebaseline_gap), e0)]
                break
    lifecycle = getattr(settings, "drift_lifecycle", "latched")
    for s0, e0 in bounds:
        start = s0
        while True:
            idx = np.flatnonzero(usable[start:e0]) + start
            if len(idx) < settings.cusum_min_series:
                break
            o = run_cusum(t_s[idx], err[idx], settings.cusum_k, settings.cusum_h,
                          settings.cusum_baseline_fraction, "baseline_window", None, settings.cusum_min_baseline)
            if not o["alarm"]:
                break
            first = idx[np.flatnonzero(t_s[idx] >= o["alarm_time_s"])[0]]
            if lifecycle == "latched":
                alarm[first:e0] = True
                break
            if lifecycle != "hysteresis":
                raise ValueError(lifecycle)
            clear = _clearance_position(err, idx, first, o["target"], o["sigma_used"], settings)
            if clear is None:
                alarm[first:e0] = True
                break
            alarm[first:clear] = True
            start = clear                      # re-baseline after clearance
    return alarm


def _clearance_position(err: np.ndarray, idx: np.ndarray, first: int, target: float, sigma: float,
                        settings: HybridSettings) -> Optional[int]:
    """
    First usable position, at least clear_window usable samples after activation, at which the
    mean of the last clear_window usable errors is within clear_z * sigma / sqrt(clear_window) of
    the baseline target (alarm clears). None if the deviation persists to the end of the series.
    """
    w = settings.clear_window
    after = idx[idx >= first]
    if len(after) <= w or not sigma or not np.isfinite(sigma):
        return None
    vals = err[after]
    csum = np.cumsum(np.r_[0.0, vals])
    means = (csum[w:] - csum[:-w]) / w                 # mean of vals[j-w+1 .. j] for j = w-1 ..
    if getattr(settings, "clear_sigma", 0.0) > 0:
        ok = np.flatnonzero(np.abs(means[1:] - target) < settings.clear_sigma * sigma)
    else:
        z = np.abs(means - target) / (sigma / np.sqrt(w))
        ok = np.flatnonzero(z[1:] < settings.clear_z)  # require the window to start after activation
    if len(ok) == 0:
        return None
    return int(after[ok[0] + w]) if ok[0] + w < len(after) else None


def drift_usable(drift_inputs: Dict[str, Any], window: int) -> np.ndarray:
    """Finite error records outside protocol transitions for the given exclusion window (cached)."""
    cache = drift_inputs.setdefault("_usable_cache", {})
    if window not in cache:
        cache[window] = drift_inputs["finite"] & ~transition_mask(drift_inputs["protocol"], window)
    return cache[window]


def combine(transient: np.ndarray, stuck_rule: np.ndarray, gbt_alarm: np.ndarray, identical_run: np.ndarray,
            drift_inputs: Optional[Dict[str, Any]], settings: HybridSettings, experiment_id: np.ndarray,
            signal: Optional[Dict[str, Any]] = None) -> Dict[str, np.ndarray]:
    """Combine component outputs for ONE run (arrays aligned to the integrity-clean records)."""
    stuck_evidence = identical_run >= STUCK_EVIDENCE_RUN
    persistent = gbt_alarm & ~stuck_evidence
    if getattr(settings, "suppress_persistent_nonstationary", False) and signal is not None:
        persistent &= ~np.isin(signal["protocol_phase"], NONSTATIONARY_PHASES)
    if settings.stuck_mode == "gbt":
        stuck = gbt_alarm & stuck_evidence
    elif settings.stuck_mode == "rule":
        stuck = stuck_rule.copy()
    elif settings.stuck_mode == "gbt_or_rule":
        stuck = stuck_rule | (gbt_alarm & stuck_evidence)
    else:
        raise ValueError(settings.stuck_mode)

    drift = np.zeros(len(transient), bool)
    if drift_inputs is not None:
        pers_eps = alarm_episodes(persistent, experiment_id, settings.episode_gap)
        usable = drift_usable(drift_inputs, settings.transition_exclusion) & ~transient & ~stuck & ~persistent
        drift = drift_component(drift_inputs["t_s"], drift_inputs["err"], usable, pers_eps, settings,
                                drift_inputs.get("segment_starts"))
        # Explained-away: a drift alarm starting within / just after another component's episode
        explained = alarm_episodes(transient | stuck | persistent, experiment_id, settings.episode_gap)
        starts = np.flatnonzero(drift & ~np.r_[False, drift[:-1]])
        for s0 in starts:
            before = getattr(settings, "explain_before", 0)
            if any(ep["start"] - before <= s0 <= ep["end"] + settings.explain_window for ep in explained):
                stop = s0
                while stop < len(drift) and drift[stop]:
                    stop += 1
                drift[s0:stop] = False

    category = np.array(["none"] * len(transient), dtype=object)
    for cat, arr in reversed(list(zip(CATEGORY_PRECEDENCE, (transient, stuck, persistent, drift)))):
        category[arr] = cat
    alarm = category != "none"
    provisional = category.copy()
    if getattr(settings, "attribution", "first_alarm") == "confirmed":
        if signal is None:
            raise ValueError("confirmed attribution needs the signal inputs")
        if getattr(settings, "attribution_source", "signal") == "error" and drift_inputs is not None:
            usable = drift_usable(drift_inputs, settings.transition_exclusion)
            category = confirm_categories_error(category, alarm, drift_inputs["err"], usable, signal["protocol_phase"],
                                                signal["floor"], settings, experiment_id)
        else:
            category = confirm_categories(category, alarm, signal["x"], signal["setpoint_index"], signal["protocol_phase"],
                                          signal["floor"], settings, experiment_id)
    return {"transient": transient, "stuck": stuck, "persistent": persistent, "drift": drift,
            "alarm": alarm, "category": category, "provisional_category": provisional}


def transient_flags(comp: Dict[str, Any], st: HybridSettings) -> np.ndarray:
    """Transient-component flags: segment detector (cached flags or scores) plus optional curvature detector."""
    key = (st.segment_mode, st.segment_mad_threshold)
    if "segment" in comp and key in comp["segment"]:
        flags = comp["segment"][key].copy()
    else:
        flags = segment_flags_from_scores(comp["segment_scores"][st.segment_mode], st.segment_mad_threshold)
    w = int(getattr(st, "transient_transition_window", 0))
    if w > 0:
        nonstat = transition_mask(comp["signal_protocol"], w)
        if st.segment_mode == "phase_blocks_stationary_only":
            flags &= ~nonstat
    else:
        nonstat = np.isin(comp["signal"]["protocol_phase"], NONSTATIONARY_PHASES)
    # Milestone 7: settling_suppression — suppress segment-detector alarms (not curvature) during
    # settling/transition phases. This addresses false alarms from normal operating transitions
    # without losing genuine spike detection via the curvature detector.
    if getattr(st, "settling_suppression", False):
        settling = np.isin(comp["signal"]["protocol_phase"], NONSTATIONARY_PHASES)
        if w > 0:
            settling = settling | nonstat
        flags = flags & ~settling
    extra = getattr(st, "transient_extra", "none")
    if extra != "none":
        curv = comp["curvature_z"] > st.curvature_threshold
        if extra == "curvature_nonstationary":
            curv &= nonstat
        elif extra != "curvature_all":
            raise ValueError(extra)
        flags = flags | curv
    return flags


# ==============================================================================
# Detector object (applies the frozen configuration to raw runs)
# ==============================================================================

class HybridDetector:
    """Applies a frozen hybrid configuration to one raw acquisition run (non-destructive)."""

    def __init__(self, measurand: str, feature_builder, persistent_gbt, calibration_model,
                 base_cfg: Dict[str, Any], settings: HybridSettings, mad_thresholds: Optional[tuple] = None,
                 score_cache: bool = False, score_base_threshold: float = 3.5):
        self.measurand = measurand
        self.builder = feature_builder
        self.gbt = persistent_gbt
        self.cal = calibration_model
        self.base_cfg = base_cfg
        self.settings = settings
        self.mad_thresholds = tuple(mad_thresholds) if mad_thresholds else (settings.segment_mad_threshold,)
        self.score_cache = score_cache   # compute segment scores once (any MAD threshold >= base) instead of flags
        self.score_base_threshold = score_base_threshold

    def components(self, run: pd.DataFrame) -> Dict[str, Any]:
        """Settings-independent component inputs for one run (reused during validation search)."""
        m = self.measurand
        run = run.reset_index(drop=True)
        feats, integrity, reasons = self.builder.transform_run(run)
        clean = run.loc[feats.index]
        out = {"run": run, "clean_index": feats.index.to_numpy(), "features": feats,
               "integrity": integrity, "integrity_reasons": reasons,
               "identical_run": np.expm1(feats["f_identical_run"].to_numpy()),
               "experiment_id": clean["experiment_id"].to_numpy()}
        if self.score_cache:
            out["segment_scores"] = {mode: segment_scores(clean, m, self.base_cfg, mode, self.score_base_threshold) for mode in SEGMENT_MODES}
        else:
            out["segment"] = {(mode, thr): segment_transient_flags(clean, m, self.base_cfg, mode, thr)
                              for mode in SEGMENT_MODES for thr in self.mad_thresholds}
        x = clean[m].to_numpy(dtype=float)
        sp = clean["setpoint_index"].to_numpy()
        out["signal"] = {"x": x, "setpoint_index": sp, "protocol_phase": clean["protocol_phase"].to_numpy(),
                         "floor": float(self.builder.floor)}
        out["curvature_z"] = curvature_scores(x, sp, float(self.builder.floor))
        out["signal_protocol"] = clean[["setpoint_index", "protocol_phase", "sequence_number"]].reset_index(drop=True)
        if self.gbt is not None:
            out["gbt_score"] = self.gbt.score(feats)
        ref_col = f"reference_{m}"
        if self.cal is not None and ref_col in clean:
            err = self.cal.predict(clean[m].to_numpy(dtype=float)) - clean[ref_col].to_numpy(dtype=float)
            out["drift_inputs"] = {"t_s": clean["elapsed_ms"].to_numpy(dtype=float) / 1000.0, "err": err,
                                   "finite": np.isfinite(err), "segment_starts": setpoint_change_positions(clean),
                                   "protocol": clean[["setpoint_index", "protocol_phase", "sequence_number"]].reset_index(drop=True)}
        return out

    def apply(self, comp: Dict[str, Any], settings: Optional[HybridSettings] = None) -> Dict[str, np.ndarray]:
        st = settings or self.settings
        gbt_alarm = comp["gbt_score"] > st.gbt_threshold if "gbt_score" in comp else np.zeros(len(comp["clean_index"]), bool)
        return combine(transient_flags(comp, st), stuck_rule_flags(comp["features"], st.stuck_alpha),
                       gbt_alarm, comp["identical_run"], comp.get("drift_inputs"), st, comp["experiment_id"], comp.get("signal"))

    def annotate(self, run: pd.DataFrame) -> pd.DataFrame:
        """Return a copy of `run` with hybrid annotation columns; the input is not modified."""
        comp = self.components(run)
        res = self.apply(comp)
        out = run.reset_index(drop=True).copy()
        out["hybrid_integrity_alarm"] = comp["integrity"]
        out["hybrid_integrity_reasons"] = comp["integrity_reasons"]
        out["hybrid_signal_alarm"] = False
        out["hybrid_category"] = np.where(comp["integrity"], "integrity", "none").astype(object)
        idx = comp["clean_index"]
        out.loc[idx, "hybrid_signal_alarm"] = res["alarm"]
        out.loc[idx, "hybrid_category"] = res["category"]
        return out

    def alarm_log(self, run: pd.DataFrame) -> pd.DataFrame:
        """
        Alarm lifecycle log: one row per alarm episode (activation sequence number, clearance
        sequence number = last alarmed record, duration, provisional and confirmed category,
        components that fired). Integrity alarms are listed per record group as well.
        """
        comp = self.components(run)
        res = self.apply(comp)
        clean = comp["run"].loc[comp["clean_index"]].reset_index(drop=True)
        seq = clean["sequence_number"].to_numpy()
        rows = []
        for ep in alarm_episodes(res["alarm"], comp["experiment_id"], self.settings.episode_gap):
            sl = slice(ep["start"], ep["end"] + 1)
            fired = [c for c in CATEGORY_PRECEDENCE if res[c][sl].any()]
            rows.append({"experiment_id": ep["run"], "activated_seq": int(seq[ep["start"]]), "cleared_seq": int(seq[ep["end"]]),
                         "duration_samples": int(seq[ep["end"]] - seq[ep["start"]] + 1),
                         "provisional_category": res["provisional_category"][ep["start"]],
                         "category": res["category"][ep["start"]], "components": ";".join(fired)})
        return pd.DataFrame(rows)
