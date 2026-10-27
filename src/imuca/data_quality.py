"""
IMUCA Data Quality and Integrity Assessment Module.

Section 7 Specification:
- Detects missing values, non-finite entries, and type errors.
- Detects duplicate records, sequence gaps, and out-of-order records.
- Handles sensor status codes and communication timeouts.
- Performs configurable physical range checks.
- Flags abrupt changes and step-discontinuities without silent deletion.
- Performs non-destructive outlier detection using Median Absolute Deviation (MAD).
- Computes sampling interval jitter and latency diagnostics.
- Computes classification metrics (Precision, Recall, FAR, MDR) against ground-truth fault labels.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple, Union
import numpy as np
import pandas as pd
import math


@dataclass
class QualityIssue:
    """Documented quality issue identified in a dataset."""
    record_index: int
    column: str
    issue_type: str  # MISSING, NON_FINITE, OUT_OF_RANGE, SEQUENCE_GAP, DUPLICATE_SEQ, OUT_OF_ORDER, STATUS_ERROR, ABRUPT_CHANGE, OUTLIER
    severity: str    # ERROR (invalid record), WARNING (suspicious, retained)
    value: Any
    threshold: Optional[Any] = None
    description: str = ""


@dataclass
class SamplingIntervalDiagnostics:
    """Statistical evaluation of timestamp and sampling-rate stability."""
    nominal_period_s: float
    mean_period_s: float
    std_jitter_s: float
    min_period_s: float
    max_period_s: float
    max_gap_s: float
    dropout_count: int
    is_periodic: bool


@dataclass
class FaultDetectionMetrics:
    """Metrics evaluating performance of quality checks against ground-truth labels."""
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    precision: float
    recall: float
    false_alarm_rate: float
    missed_detection_rate: float
    f1_score: float


@dataclass
class QualityAssessmentReport:
    """Comprehensive data quality audit report."""
    total_records: int
    clean_records_count: int
    flagged_records_count: int
    error_records_count: int
    warning_records_count: int
    issues: List[QualityIssue] = field(default_factory=list)
    sampling_diagnostics: Optional[SamplingIntervalDiagnostics] = None
    detection_metrics: Optional[FaultDetectionMetrics] = None
    annotated_dataframe: pd.DataFrame = field(default_factory=pd.DataFrame)
    summary_by_type: Dict[str, int] = field(default_factory=dict)


class DataQualityAssessor:
    """
    Evaluates dataset quality without mutating raw inputs.
    Flags suspicious data non-destructively for metrological review.
    """

    def __init__(
        self,
        mad_threshold: float = 3.5,
        max_acceptable_gap_factor: float = 2.5,
        nominal_sampling_period_s: float = 1.0
    ):
        self.mad_threshold = mad_threshold
        self.max_acceptable_gap_factor = max_acceptable_gap_factor
        self.nominal_sampling_period_s = nominal_sampling_period_s

    def assess(
        self,
        df: pd.DataFrame,
        measurand_col: str,
        range_limits: Tuple[float, float],
        max_rate_of_change: Optional[float] = None,
        ground_truth_fault_col: Optional[str] = "is_injected_fault"
    ) -> QualityAssessmentReport:
        """
        Run complete suite of quality assessments on the dataset.
        """
        annotated = df.copy()
        n = len(annotated)
        issues: List[QualityIssue] = []

        is_error = np.zeros(n, dtype=bool)
        is_warning = np.zeros(n, dtype=bool)
        record_flags: List[List[str]] = [[] for _ in range(n)]

        # 1. Sequence & Monotonicity Checks
        if "sequence_number" in annotated.columns:
            seqs = annotated["sequence_number"].values
            seen_seq = set()
            prev_s = None

            for i in range(n):
                s = seqs[i]
                if pd.isna(s) or not isinstance(s, (int, np.integer, float)):
                    is_error[i] = True
                    record_flags[i].append("INVALID_SEQ")
                    issues.append(QualityIssue(i, "sequence_number", "MISSING", "ERROR", s, description="Missing sequence number"))
                    continue

                s_int = int(s)
                if s_int in seen_seq:
                    is_error[i] = True
                    record_flags[i].append("DUPLICATE_SEQ")
                    issues.append(QualityIssue(i, "sequence_number", "DUPLICATE_SEQ", "ERROR", s_int, description=f"Duplicate sequence number {s_int}"))
                else:
                    seen_seq.add(s_int)

                if prev_s is not None:
                    if s_int <= prev_s:
                        is_error[i] = True
                        record_flags[i].append("OUT_OF_ORDER_SEQ")
                        issues.append(QualityIssue(i, "sequence_number", "OUT_OF_ORDER", "ERROR", s_int, prev_s, f"Sequence decreased from {prev_s} to {s_int}"))
                    elif s_int > prev_s + 1:
                        is_warning[i] = True
                        gap_sz = s_int - prev_s - 1
                        record_flags[i].append(f"SEQ_GAP_{gap_sz}")
                        issues.append(QualityIssue(i, "sequence_number", "SEQUENCE_GAP", "WARNING", s_int, gap_sz, f"Gap of {gap_sz} samples"))
                prev_s = s_int

        # 2. Timing and Sampling Interval Diagnostics
        sampling_diag = None
        if "elapsed_ms" in annotated.columns:
            times_ms = pd.to_numeric(annotated["elapsed_ms"], errors="coerce").values
            deltas_s = np.diff(times_ms) / 1000.0

            if len(deltas_s) > 0 and np.all(np.isfinite(deltas_s)):
                mean_p = float(np.mean(deltas_s))
                std_j = float(np.std(deltas_s, ddof=1)) if len(deltas_s) > 1 else 0.0
                min_p = float(np.min(deltas_s))
                max_p = float(np.max(deltas_s))
                max_gap = float(np.max(deltas_s))
                
                # Check dropouts
                thresh_gap = self.nominal_sampling_period_s * self.max_acceptable_gap_factor
                dropouts = int(np.sum(deltas_s > thresh_gap))

                # Flag interval anomalies
                for i, dt in enumerate(deltas_s):
                    if dt < 0:
                        is_error[i + 1] = True
                        record_flags[i + 1].append("BACKWARDS_TIME")
                        issues.append(QualityIssue(i + 1, "elapsed_ms", "OUT_OF_ORDER", "ERROR", dt, 0.0, "Negative time step"))
                    elif dt > thresh_gap:
                        is_warning[i + 1] = True
                        record_flags[i + 1].append(f"TIME_GAP_{dt:.2f}s")
                        issues.append(QualityIssue(i + 1, "elapsed_ms", "SEQUENCE_GAP", "WARNING", dt, thresh_gap, f"Time gap of {dt:.2f}s exceeded threshold {thresh_gap:.2f}s"))

                sampling_diag = SamplingIntervalDiagnostics(
                    nominal_period_s=self.nominal_sampling_period_s,
                    mean_period_s=mean_p,
                    std_jitter_s=std_j,
                    min_period_s=min_p,
                    max_period_s=max_p,
                    max_gap_s=max_gap,
                    dropout_count=dropouts,
                    is_periodic=(std_j < 0.1 * self.nominal_sampling_period_s)
                )

        # 3. Sensor Status Code Checks
        if "status" in annotated.columns:
            statuses = annotated["status"].astype(str).values
            for i, st in enumerate(statuses):
                st_norm = st.strip().upper()
                if st_norm not in ("OK", "NOMINAL", "VALID"):
                    is_error[i] = True
                    record_flags[i].append(f"STATUS_{st_norm}")
                    issues.append(QualityIssue(i, "status", "STATUS_ERROR", "ERROR", st, description=f"Sensor hardware reported status error: '{st}'"))

        # 4. Measurand Value Checks: Missing, Non-Finite, Range
        if measurand_col in annotated.columns:
            raw_vals = annotated[measurand_col].values
            r_min, r_max = range_limits
            numeric_vals = np.full(n, np.nan, dtype=float)

            for i, v in enumerate(raw_vals):
                if pd.isna(v):
                    is_error[i] = True
                    record_flags[i].append("MISSING_VALUE")
                    issues.append(QualityIssue(i, measurand_col, "MISSING", "ERROR", v, description=f"Missing measurement in '{measurand_col}'"))
                    continue

                try:
                    fv = float(v)
                except (ValueError, TypeError):
                    is_error[i] = True
                    record_flags[i].append("NON_NUMERIC")
                    issues.append(QualityIssue(i, measurand_col, "NON_FINITE", "ERROR", v, description=f"Non-numeric string in '{measurand_col}'"))
                    continue

                if not math.isfinite(fv):
                    is_error[i] = True
                    record_flags[i].append("NON_FINITE")
                    issues.append(QualityIssue(i, measurand_col, "NON_FINITE", "ERROR", fv, description=f"Non-finite value (NaN/Inf) in '{measurand_col}'"))
                elif fv < r_min or fv > r_max:
                    is_error[i] = True
                    record_flags[i].append("OUT_OF_RANGE")
                    issues.append(QualityIssue(i, measurand_col, "OUT_OF_RANGE", "ERROR", fv, (r_min, r_max), f"Value {fv} outside range [{r_min}, {r_max}]"))
                else:
                    numeric_vals[i] = fv

            # 5. Non-Destructive MAD Outlier Detection
            # Uses Modified Z-score: M_i = 0.6745 * |x_i - median| / MAD
            # Standard GUM / NIST recommendation for robust outlier screening
            valid_indices = np.where(np.isfinite(numeric_vals))[0]
            if len(valid_indices) >= 5:
                vals_subset = numeric_vals[valid_indices]
                med = float(np.median(vals_subset))
                abs_devs = np.abs(vals_subset - med)
                mad = float(np.median(abs_devs))

                if mad > 1e-12:
                    mod_z = 0.6745 * abs_devs / mad
                else:
                    # NIST / Iglewicz & Hoaglin (1993) recommendation when MAD is zero
                    # (occurs when >50% of observations are identical to the median).
                    # Use Mean Absolute Deviation (MeanAD) from the median:
                    mean_ad = float(np.mean(abs_devs))
                    if mean_ad > 1e-12:
                        mod_z = (0.6745 * abs_devs) / (1.2533 * mean_ad)
                    else:
                        mod_z = np.zeros_like(abs_devs)

                for idx_pos, (row_idx, z_val) in enumerate(zip(valid_indices, mod_z)):
                    if z_val > self.mad_threshold:
                        is_warning[row_idx] = True
                        record_flags[row_idx].append(f"OUTLIER_MAD_{z_val:.1f}")
                        issues.append(QualityIssue(
                            record_index=int(row_idx),
                            column=measurand_col,
                            issue_type="OUTLIER",
                            severity="WARNING",
                            value=float(numeric_vals[row_idx]),
                            threshold=float(self.mad_threshold),
                            description=f"MAD modified Z-score={z_val:.2f} exceeded threshold {self.mad_threshold}"
                        ))

            # 6. Abrupt Change / Step Discontinuity Check
            if max_rate_of_change is not None and max_rate_of_change > 0:
                for i in range(1, n):
                    if np.isfinite(numeric_vals[i]) and np.isfinite(numeric_vals[i - 1]):
                        dt = 1.0
                        if "elapsed_ms" in annotated.columns and np.isfinite(times_ms[i]) and np.isfinite(times_ms[i - 1]):
                            dt = max(1e-3, (times_ms[i] - times_ms[i - 1]) / 1000.0)
                        
                        rate = abs(numeric_vals[i] - numeric_vals[i - 1]) / dt
                        if rate > max_rate_of_change:
                            is_warning[i] = True
                            record_flags[i].append(f"ABRUPT_CHANGE_{rate:.1f}/s")
                            issues.append(QualityIssue(
                                record_index=i,
                                column=measurand_col,
                                issue_type="ABRUPT_CHANGE",
                                severity="WARNING",
                                value=float(numeric_vals[i]),
                                threshold=max_rate_of_change,
                                description=f"Rate of change {rate:.2f}/s exceeded allowable {max_rate_of_change:.2f}/s"
                            ))

        # Annotate DataFrame non-destructively
        annotated["quality_flags"] = [";".join(f) if f else "CLEAN" for f in record_flags]
        annotated["is_error"] = is_error
        annotated["is_warning"] = is_warning
        annotated["is_clean"] = ~(is_error | is_warning)

        # 7. Evaluate Fault Detection Performance (if ground truth labels are provided)
        detection_metrics = None
        if ground_truth_fault_col and ground_truth_fault_col in annotated.columns:
            gt = annotated[ground_truth_fault_col].astype(bool).values
            pred = (is_error | is_warning)

            tp = int(np.sum(pred & gt))
            fp = int(np.sum(pred & (~gt)))
            tn = int(np.sum((~pred) & (~gt)))
            fn = int(np.sum((~pred) & gt))

            prec = (tp / (tp + fp)) if (tp + fp) > 0 else 1.0
            rec = (tp / (tp + fn)) if (tp + fn) > 0 else 1.0
            far = (fp / (fp + tn)) if (fp + tn) > 0 else 0.0
            mdr = (fn / (tp + fn)) if (tp + fn) > 0 else 0.0
            f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0

            detection_metrics = FaultDetectionMetrics(
                true_positives=tp,
                false_positives=fp,
                true_negatives=tn,
                false_negatives=fn,
                precision=prec,
                recall=rec,
                false_alarm_rate=far,
                missed_detection_rate=mdr,
                f1_score=f1
            )

        # Issue summary by type
        summary_by_type: Dict[str, int] = {}
        for iss in issues:
            summary_by_type[iss.issue_type] = summary_by_type.get(iss.issue_type, 0) + 1

        clean_cnt = int(np.sum(annotated["is_clean"]))
        err_cnt = int(np.sum(annotated["is_error"]))
        warn_cnt = int(np.sum(annotated["is_warning"]))
        flagged_cnt = n - clean_cnt

        return QualityAssessmentReport(
            total_records=n,
            clean_records_count=clean_cnt,
            flagged_records_count=flagged_cnt,
            error_records_count=err_cnt,
            warning_records_count=warn_cnt,
            issues=issues,
            sampling_diagnostics=sampling_diag,
            detection_metrics=detection_metrics,
            annotated_dataframe=annotated,
            summary_by_type=summary_by_type
        )
