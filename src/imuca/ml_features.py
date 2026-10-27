"""
IMUCA Causal Feature Engineering for Signal-Level Fault Detection.

Rules enforced by construction:
- Only observable columns are read: the measurand reading, status, sequence_number and
  elapsed_ms (plus experiment_id for grouping). Ground truth, reference readings, labels,
  protocol columns and derived errors are never read by the feature code.
- Every feature at record k uses records 0..k of the same run only (causal). Window
  statistics that describe "recent history" exclude the current record so that a fault
  does not normalise itself.
- Records rejected by the deterministic integrity rules (missing, non-finite, duplicate,
  out-of-order, sequence/time gap, non-OK status) are removed from the signal stream
  before features are computed. These rules are themselves causal.
- The only fitted quantity, a per-measurand noise-scale floor, is estimated from the
  calibration partition only (`CausalFeatureBuilder.fit` refuses other partitions).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.imuca.data_quality import DataQualityAssessor


SIGNAL_FAULT_TYPES = ("isolated_spike", "stuck_signal", "offset_shift", "gain_change", "gradual_drift", "abrupt_change")
INTEGRITY_FAULT_TYPES = ("missing_samples", "duplicate_sequence", "communication_gap", "invalid_status", "non_finite")
PERSISTENT_SIGNAL_FAULTS = ("offset_shift", "gain_change", "gradual_drift")

# DataQualityAssessor issue types that are deterministic, causal record-integrity checks
INTEGRITY_ISSUE_TYPES = ("MISSING", "NON_FINITE", "DUPLICATE_SEQ", "OUT_OF_ORDER", "SEQUENCE_GAP", "STATUS_ERROR")

# The complete set of dataset columns the feature code is allowed to read
OBSERVABLE_INPUT_COLUMNS = ("experiment_id", "status", "sequence_number", "elapsed_ms")

FEATURE_NAMES = [
    "f_d1", "f_abs_d1", "f_d2",
    "f_dev_med5", "f_dev_med15", "f_dev_med60", "f_dev_mean60",
    "f_std15", "f_std60",
    "f_max_abs_d1_5", "f_max_abs_d1_30",
    "f_level_shift_15_60",
    "f_slope60", "f_slope300",
    "f_identical_run", "f_frac_zero_d1_30", "f_frac_zero_d1_300", "f_noise_ratio_15_300",
    "f_since_large_change", "f_position",
]

FEATURE_DEFINITIONS = {
    "f_d1": "(x[k] - x[k-1]) / s[k]",
    "f_abs_d1": "|x[k] - x[k-1]| / s[k]",
    "f_d2": "(x[k] - 2x[k-1] + x[k-2]) / s[k]",
    "f_dev_med5": "(x[k] - median(x[k-5..k-1])) / s[k]",
    "f_dev_med15": "(x[k] - median(x[k-15..k-1])) / s[k]",
    "f_dev_med60": "(x[k] - median(x[k-60..k-1])) / s[k]",
    "f_dev_mean60": "(x[k] - mean(x[k-60..k-1])) / s[k]",
    "f_std15": "std(x[k-14..k]) / s[k]",
    "f_std60": "std(x[k-59..k]) / s[k]",
    "f_max_abs_d1_5": "max |d1| over k-4..k, / s[k]",
    "f_max_abs_d1_30": "max |d1| over k-29..k, / s[k]",
    "f_level_shift_15_60": "(mean(x[k-14..k]) - mean(x[k-74..k-15])) / s[k]",
    "f_slope60": "least-squares slope of x over k-59..k, times 60 samples, / s[k]",
    "f_slope300": "least-squares slope of x over k-299..k, times 300 samples, / s[k]",
    "f_identical_run": "log(1 + number of consecutive identical readings ending at k)",
    "f_frac_zero_d1_30": "fraction of zero first differences over k-29..k",
    "f_frac_zero_d1_300": "fraction of zero first differences over k-329..k-30 (past baseline)",
    "f_noise_ratio_15_300": "mean |d1| over k-14..k / mean |d1| over k-314..k-15",
    "f_since_large_change": "log(1 + samples since |d1|/s last exceeded 6), capped at 600",
    "f_position": "log(1 + index of the record in the cleaned run stream)",
}
NOISE_SCALE_DEFINITION = (
    "s[k] = max( 1.4826*median(|d1| over k-60..k-1)/sqrt(2), 1.2533*mean(|d1| over k-60..k-1)/sqrt(2), floor ), "
    "floor = 0.25 * median(raw s) over fault-free calibration-partition records of the measurand"
)


# ==============================================================================
# Deterministic integrity rules (separate track)
# ==============================================================================

def integrity_rule_flags(run: pd.DataFrame, measurand: str) -> Tuple[np.ndarray, List[str]]:
    """
    Apply the existing DataQualityAssessor and keep only its causal record-integrity
    issue types. Returns (flag per record, ';'-joined reasons per record).
    """
    run = run.reset_index(drop=True)
    rep = DataQualityAssessor().assess(
        run[[measurand, *OBSERVABLE_INPUT_COLUMNS[1:]]],
        measurand_col=measurand, range_limits=(-np.inf, np.inf),
        max_rate_of_change=None, ground_truth_fault_col=None,
    )
    flags = np.zeros(len(run), bool)
    reasons: List[List[str]] = [[] for _ in range(len(run))]
    for iss in rep.issues:
        if iss.issue_type in INTEGRITY_ISSUE_TYPES:
            flags[iss.record_index] = True
            reasons[iss.record_index].append(iss.issue_type)
    return flags, [";".join(sorted(set(r))) if r else "" for r in reasons]


# ==============================================================================
# Causal features
# ==============================================================================

def _rolling_slope(x: pd.Series, w: int) -> pd.Series:
    """Causal least-squares slope over the last w samples (index spacing = 1)."""
    i = pd.Series(np.arange(len(x), dtype=float), index=x.index)
    valid = x.notna()
    xi = x.where(valid)
    ii = i.where(valid)
    n = valid.astype(float).rolling(w, min_periods=w // 2).sum()
    sx = xi.rolling(w, min_periods=w // 2).sum()
    si = ii.rolling(w, min_periods=w // 2).sum()
    sxi = (xi * ii).rolling(w, min_periods=w // 2).sum()
    sii = (ii * ii).rolling(w, min_periods=w // 2).sum()
    den = n * sii - si ** 2
    return (n * sxi - si * sx) / den.where(den > 0)


def raw_noise_scale(x: pd.Series) -> pd.Series:
    """Robust noise-scale estimate from PAST first differences (excludes record k)."""
    absd = x.diff().abs().shift(1)
    med = absd.rolling(60, min_periods=10).median() * 1.4826 / np.sqrt(2.0)
    mean = absd.rolling(60, min_periods=10).mean() * 1.2533 / np.sqrt(2.0)
    return np.maximum(med, mean)


def causal_features(x: np.ndarray, floor: float) -> pd.DataFrame:
    """Compute FEATURE_NAMES for one cleaned run stream x (1-D, chronological)."""
    s_x = pd.Series(np.asarray(x, dtype=float))
    d1 = s_x.diff()
    absd = d1.abs()
    scale = raw_noise_scale(s_x).fillna(floor).clip(lower=floor)
    past = s_x.shift(1)
    f = pd.DataFrame(index=s_x.index)
    f["f_d1"] = d1 / scale
    f["f_abs_d1"] = absd / scale
    f["f_d2"] = (s_x - 2 * s_x.shift(1) + s_x.shift(2)) / scale
    for w in (5, 15, 60):
        f[f"f_dev_med{w}"] = (s_x - past.rolling(w, min_periods=max(2, w // 3)).median()) / scale
    f["f_dev_mean60"] = (s_x - past.rolling(60, min_periods=20).mean()) / scale
    f["f_std15"] = s_x.rolling(15, min_periods=5).std() / scale
    f["f_std60"] = s_x.rolling(60, min_periods=20).std() / scale
    f["f_max_abs_d1_5"] = absd.rolling(5, min_periods=1).max() / scale
    f["f_max_abs_d1_30"] = absd.rolling(30, min_periods=1).max() / scale
    recent = s_x.rolling(15, min_periods=5).mean()
    older = s_x.shift(15).rolling(60, min_periods=20).mean()
    f["f_level_shift_15_60"] = (recent - older) / scale
    f["f_slope60"] = _rolling_slope(s_x, 60) * 60.0 / scale
    f["f_slope300"] = _rolling_slope(s_x, 300) * 300.0 / scale

    same = (d1 == 0).to_numpy()
    run_len = np.zeros(len(s_x))
    for k in range(1, len(s_x)):
        run_len[k] = run_len[k - 1] + 1 if same[k] else 0
    f["f_identical_run"] = np.log1p(run_len)
    zero = (d1 == 0).astype(float).where(d1.notna())
    f["f_frac_zero_d1_30"] = zero.rolling(30, min_periods=10).mean()
    f["f_frac_zero_d1_300"] = zero.shift(30).rolling(300, min_periods=30).mean()
    base = absd.shift(15).rolling(300, min_periods=30).mean()
    f["f_noise_ratio_15_300"] = absd.rolling(15, min_periods=5).mean() / base.where(base > 0)

    big = (f["f_abs_d1"] > 6.0).to_numpy()
    since = np.zeros(len(s_x))
    last = None
    for k in range(len(s_x)):
        if big[k]:
            last = k
        since[k] = 600.0 if last is None else min(600.0, k - last)
    f["f_since_large_change"] = np.log1p(since)
    f["f_position"] = np.log1p(np.arange(len(s_x), dtype=float))
    return f[FEATURE_NAMES].replace([np.inf, -np.inf], np.nan)


@dataclass
class CausalFeatureBuilder:
    """Per-measurand causal feature builder; the noise-scale floor is fitted on calibration data only."""
    measurand: str
    floor_fraction: float = 0.25
    floor: Optional[float] = None
    fit_info: Dict[str, float] = field(default_factory=dict)

    def fit(self, frame: pd.DataFrame) -> "CausalFeatureBuilder":
        parts = set(frame["partition"].unique())
        if parts != {"calibration"}:
            raise ValueError(f"CausalFeatureBuilder.fit accepts calibration-partition rows only, got {sorted(parts)}.")
        scales = []
        for _, run in frame.groupby("experiment_id", sort=False):
            flags, _ = integrity_rule_flags(run, self.measurand)
            clean = run.loc[~flags]
            # fault-free records only (labels are allowed for fitting on training data)
            sc = raw_noise_scale(clean[self.measurand].astype(float).reset_index(drop=True))
            ok = (clean["label_fault_type"].to_numpy() == "none")
            scales.append(sc.to_numpy()[ok])
        s = np.concatenate(scales)
        s = s[np.isfinite(s) & (s > 0)]
        med = float(np.median(s))
        self.floor = self.floor_fraction * med
        self.fit_info = {"median_raw_scale": med, "floor": self.floor, "records_used": int(len(s))}
        return self

    def transform_run(self, run: pd.DataFrame) -> Tuple[pd.DataFrame, np.ndarray, List[str]]:
        """
        Features for one run. Returns (features for integrity-clean records, integrity flag
        per input record, integrity reasons per input record). Feature rows are indexed by
        the input run's index so evaluation columns can be joined afterwards.
        """
        if self.floor is None:
            raise RuntimeError("CausalFeatureBuilder must be fitted before transform.")
        observable = run[[self.measurand, *OBSERVABLE_INPUT_COLUMNS]]
        flags, reasons = integrity_rule_flags(observable, self.measurand)
        clean = observable.loc[~flags]
        feats = causal_features(clean[self.measurand].to_numpy(dtype=float), self.floor)
        feats.index = clean.index
        return feats, flags, reasons


EVALUATION_COLUMNS = (
    "scenario_id", "experiment_id", "partition", "sequence_number", "elapsed_ms", "protocol_phase",
    "label_fault_type", "label_fault_event_id", "label_process_event",
)


def signal_fault_type(label: str) -> str:
    """Signal-track label of a record ('none' when no signal fault is active)."""
    if label == "none":
        return "none"
    types = [t for t in label.split(";") if t in SIGNAL_FAULT_TYPES]
    return ";".join(types) if types else "none"


def build_signal_dataset(frames: Dict[str, pd.DataFrame], measurand: str,
                         builder: CausalFeatureBuilder) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Build (signal_dataset, integrity_dataset) for one measurand from scenario frames.
    signal_dataset: integrity-clean records with FEATURE_NAMES + evaluation-only columns.
    integrity_dataset: every record with its rule flag and labels (separate track).
    """
    sig_parts, int_parts = [], []
    for sid, df in frames.items():
        for _, run in df.groupby("experiment_id", sort=False):
            run = run.reset_index(drop=True)
            feats, flags, reasons = builder.transform_run(run)
            ev = run.loc[feats.index, list(EVALUATION_COLUMNS)]
            sig = pd.concat([ev.reset_index(drop=True), feats.reset_index(drop=True)], axis=1)
            sig["signal_fault_type"] = [signal_fault_type(s) for s in sig["label_fault_type"]]
            sig["is_signal_fault"] = sig["signal_fault_type"] != "none"
            sig_parts.append(sig)
            it = run[list(EVALUATION_COLUMNS)].copy()
            it["integrity_rule_flag"] = flags
            it["integrity_rule_reasons"] = reasons
            it["integrity_label"] = [";".join(t for t in s.split(";") if t in INTEGRITY_FAULT_TYPES) or "none"
                                     for s in run["label_fault_type"]]
            int_parts.append(it)
    return pd.concat(sig_parts, ignore_index=True), pd.concat(int_parts, ignore_index=True)
