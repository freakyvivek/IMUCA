"""
IMUCA ML fault-detection helpers (signal track).

Models receive only the causal features in `ml_features.FEATURE_NAMES`. Labels are used
only as training targets / sample weights (calibration partition) and for threshold and
model selection (validation partition). The test partition is scored once per frozen model.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, IsolationForest

from src.imuca.data_quality import DataQualityAssessor
from src.imuca.ml_features import FEATURE_NAMES


def class_balanced_weights(signal_fault_type: pd.Series) -> np.ndarray:
    """Each signal-fault class gets equal total weight; negatives together match the positives."""
    t = signal_fault_type.to_numpy()
    w = np.zeros(len(t))
    pos = t != "none"
    classes = sorted(set(t[pos]))
    n_pos = pos.sum()
    for c in classes:
        m = t == c
        w[m] = (n_pos / len(classes)) / m.sum()
    if (~pos).any():
        w[~pos] = n_pos / (~pos).sum() if n_pos else 1.0
    return w


@dataclass
class GBTDetector:
    params: Dict[str, Any]
    seed: int
    model: Optional[HistGradientBoostingClassifier] = None
    threshold: Optional[float] = None

    def fit(self, train: pd.DataFrame) -> "GBTDetector":
        _assert_partition(train, "calibration")
        self.model = HistGradientBoostingClassifier(random_state=self.seed, early_stopping=False, **self.params)
        self.model.fit(train[FEATURE_NAMES].to_numpy(), train["is_signal_fault"].to_numpy(),
                       sample_weight=class_balanced_weights(train["signal_fault_type"]))
        return self

    def score(self, df: pd.DataFrame) -> np.ndarray:
        return self.model.predict_proba(df[FEATURE_NAMES].to_numpy())[:, 1]


@dataclass
class IsolationForestDetector:
    params: Dict[str, Any]
    seed: int
    model: Optional[IsolationForest] = None
    fill_values: Dict[str, float] = field(default_factory=dict)
    threshold: Optional[float] = None
    training_records: int = 0

    def fit(self, train: pd.DataFrame) -> "IsolationForestDetector":
        """Fit on fault-free calibration records only (labels select the training population)."""
        _assert_partition(train, "calibration")
        normal = train[~train["is_signal_fault"]]
        self.fill_values = {c: float(normal[c].median()) for c in FEATURE_NAMES}
        x = normal[FEATURE_NAMES].fillna(self.fill_values).to_numpy()
        self.model = IsolationForest(random_state=self.seed, **self.params).fit(x)
        self.training_records = int(len(normal))
        return self

    def score(self, df: pd.DataFrame) -> np.ndarray:
        x = df[FEATURE_NAMES].fillna(self.fill_values).to_numpy()
        return -self.model.score_samples(x)


def _assert_partition(df: pd.DataFrame, partition: str) -> None:
    parts = set(df["partition"].unique())
    if parts != {partition}:
        raise ValueError(f"Model fitting must use the {partition} partition only, got {sorted(parts)}.")


def segment_baseline_flags(frames: Dict[str, pd.DataFrame], measurand: str, base_cfg: Dict[str, Any]) -> Dict[tuple, bool]:
    """
    Existing conventional detector applied per contiguous protocol segment
    (run x setpoint_index block). Returns {(experiment_id, sequence_number): flagged} for the
    first record carrying each key (duplicate copies are excluded from the signal track).
    """
    mc = base_cfg["measurands"][measurand]
    assessor = DataQualityAssessor(mad_threshold=base_cfg["quality"]["mad_threshold"],
                                   nominal_sampling_period_s=1.0 / base_cfg["quality"]["nominal_sampling_rate_hz"])
    out: Dict[tuple, bool] = {}
    for df in frames.values():
        key = df["experiment_id"].astype(str) + "|" + df["setpoint_index"].astype(str)
        seg = (key != key.shift()).cumsum()
        for _, idx in df.groupby(seg.to_numpy(), sort=False).indices.items():
            sub = df.iloc[idx].reset_index(drop=True)
            rep = assessor.assess(sub, measurand_col=measurand, range_limits=(mc["min_range"], mc["max_range"]),
                                  max_rate_of_change=mc["max_rate_of_change_per_sec"], ground_truth_fault_col=None)
            flag = (rep.annotated_dataframe["is_error"] | rep.annotated_dataframe["is_warning"]).to_numpy()
            for e, s, f in zip(sub["experiment_id"], sub["sequence_number"], flag):
                out.setdefault((e, int(s)), bool(f))
    return out


def targeted_weights(train: pd.DataFrame, target_types: tuple, excluded_types: tuple,
                     onset_window: int, persistent_types: tuple,
                     onset_seq: Dict[str, int]) -> tuple:
    """
    Target and sample weights for a detector responsible only for `target_types`.
    - Rows carrying an excluded type (handled by another component) get weight 0.
    - Persistent target faults are positive only within `onset_window` samples of onset
      (the only part a causal single-sensor detector can see); later rows get weight 0.
    - Each target class gets equal total weight; negatives together match the positives.
    `onset_seq` maps fault event id -> onset sequence number.
    """
    types = train["signal_fault_type"].to_numpy()
    ids = train["label_fault_event_id"].to_numpy()
    seq = train["sequence_number"].to_numpy()
    y = np.zeros(len(train), bool)
    use = np.ones(len(train), bool)
    cls = np.array(["none"] * len(train), dtype=object)
    for i, (t, eid) in enumerate(zip(types, ids)):
        if t == "none":
            continue
        tl = t.split(";")
        if any(x in excluded_types for x in tl):
            use[i] = False
            continue
        hit = None
        for x in tl:
            if x not in target_types:
                continue
            if x in persistent_types:
                onsets = [onset_seq[e] for e in eid.split(";") if e in onset_seq]
                if onsets and 0 <= seq[i] - max(onsets) < onset_window:
                    hit = x
            else:
                hit = x
        if hit is None:
            use[i] = False
        else:
            y[i] = True
            cls[i] = hit
    w = np.zeros(len(train))
    pos_classes = sorted(set(cls[y]))
    n_pos = int(y.sum())
    for c in pos_classes:
        m = y & (cls == c)
        w[m] = (n_pos / len(pos_classes)) / m.sum()
    neg = use & ~y
    if neg.any():
        w[neg] = n_pos / neg.sum() if n_pos else 1.0
    return y, w


@dataclass
class TargetedGBTDetector:
    """GBT responsible for a subset of signal faults (hybrid component); optional monotone constraints."""
    params: Dict[str, Any]
    seed: int
    target_types: tuple
    excluded_types: tuple
    onset_window: int
    persistent_types: tuple
    monotone_increasing: tuple = ()
    model: Optional[HistGradientBoostingClassifier] = None
    threshold: Optional[float] = None
    training_summary: Dict[str, Any] = field(default_factory=dict)

    def fit(self, train: pd.DataFrame, onset_seq: Dict[str, int]) -> "TargetedGBTDetector":
        _assert_partition(train, "calibration")
        y, w = targeted_weights(train, self.target_types, self.excluded_types, self.onset_window,
                                self.persistent_types, onset_seq)
        keep = w > 0
        cst = [1 if f in self.monotone_increasing else 0 for f in FEATURE_NAMES]
        self.model = HistGradientBoostingClassifier(random_state=self.seed, early_stopping=False,
                                                    monotonic_cst=cst, **self.params)
        self.model.fit(train.loc[keep, FEATURE_NAMES].to_numpy(), y[keep], sample_weight=w[keep])
        self.training_summary = {"records_used": int(keep.sum()), "positives": int(y[keep].sum()),
                                 "excluded_records": int((~keep).sum())}
        return self

    def score(self, df: pd.DataFrame) -> np.ndarray:
        return self.model.predict_proba(df[FEATURE_NAMES].to_numpy())[:, 1]
