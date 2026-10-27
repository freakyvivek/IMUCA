#!/usr/bin/env python3
"""
Post-hoc paired comparison of two detectors from a completed final evaluation (no re-scoring,
no re-tuning). Both detectors were scored on the same runs, so the run-level bootstrap of the
DIFFERENCE in event F1 / false alarms per hour is reported in addition to the pre-specified
marginal intervals.

Usage:
    python scripts/posthoc_paired_comparison.py RESULTS_DIR DATA_ROOT [detector_a] [detector_b]
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from src.imuca.ml_features import integrity_rule_flags, SIGNAL_FAULT_TYPES
from src.imuca.hybrid_evaluation import EvalSet
from src.imuca.detection_metrics import alarm_episodes, classify_episodes, detect_with_windows


def per_run_counts(alarm, E):
    det = detect_with_windows(alarm, E.windows, E.seq)
    eps = alarm_episodes(alarm, E.exp, E.gap)
    true = classify_episodes(eps, E.active)
    rows = {}
    for r in pd.unique(E.exp):
        rows[r] = {"hours": float(np.sum(E.exp == r)) / 3600.0, "tp_eps": 0, "fp_eps": 0}
    for e, t in zip(eps, true):
        rows[e["run"]]["tp_eps" if t else "fp_eps"] += 1
    for d in det:
        rows[d["run_id"]][f"{d['fault_type']}__n"] = rows[d["run_id"]].get(f"{d['fault_type']}__n", 0) + 1
        rows[d["run_id"]][f"{d['fault_type']}__d"] = rows[d["run_id"]].get(f"{d['fault_type']}__d", 0) + int(d["detected"])
    return pd.DataFrame.from_dict(rows, orient="index").fillna(0)


def f1(tab):
    classes = sorted({c.split("__")[0] for c in tab.columns if c.endswith("__n")})
    recs = [tab[f"{c}__d"].sum() / tab[f"{c}__n"].sum() for c in classes if tab[f"{c}__n"].sum() > 0]
    ne = tab["tp_eps"].sum() + tab["fp_eps"].sum()
    if not recs or ne == 0:
        return np.nan
    p, r = tab["tp_eps"].sum() / ne, float(np.mean(recs))
    return 2 * p * r / (p + r) if p + r else 0.0


def main():
    res_dir, data_root = Path(sys.argv[1]), Path(sys.argv[2])
    a, b = (sys.argv[3], sys.argv[4]) if len(sys.argv) > 4 else ("hybrid_m7", "hybrid_m6")
    cfg = json.loads((WORKSPACE_ROOT / "config" / "hybrid_iteration_config.json").read_text(encoding="utf-8"))
    man = json.loads((data_root / "metadata" / "suite_manifest.json").read_text(encoding="utf-8"))
    out = {}
    lines = [f"# Post-hoc paired comparison: {a} vs {b}", "",
             "> Post-hoc analysis of the saved alarms of a completed final evaluation (no detector was re-run or re-tuned). "
             "The pre-specified result is the marginal comparison in REPORT.md; this paired run-level bootstrap uses the fact that both "
             "detectors were scored on the same runs.", "",
             "| Measurand | F1 a | F1 b | Diff a-b | 95 % paired bootstrap CI | P(diff <= 0) | FA/h diff | 95 % CI |", "|---|---|---|---|---|---|---|---|"]
    rng = np.random.default_rng(20261026)
    for m in cfg["measurands"]:
        pred = pd.read_csv(res_dir / "predictions" / f"{m}_test_alarms.csv")
        comps, events = [], []
        for f in man["files"]:
            if f["measurand"] != m:
                continue
            df = pd.read_csv(data_root / f["csv_file"])
            meta = json.loads((data_root / f["metadata_file"]).read_text(encoding="utf-8"))
            events += [e for e in meta["fault_events"] if e["fault_type"] in SIGNAL_FAULT_TYPES]
            for _, run in df.groupby("experiment_id", sort=False):
                run = run.reset_index(drop=True)
                flags, _ = integrity_rule_flags(run, m)
                comps.append({"run": run, "clean_index": np.flatnonzero(~flags)})
        E = EvalSet(comps, events, cfg, m)
        key = E.df[["experiment_id", "sequence_number"]].merge(pred, on=["experiment_id", "sequence_number"], how="left", validate="one_to_one")
        if key[f"{a}_alarm"].isna().any():
            raise SystemExit("prediction rows do not align with the evaluation records")
        ta, tb = per_run_counts(key[f"{a}_alarm"].to_numpy(bool), E), per_run_counts(key[f"{b}_alarm"].to_numpy(bool), E)
        ta, tb = ta.align(tb, fill_value=0)
        runs = ta.index.to_numpy()
        d_f1, d_fa = [], []
        for _ in range(4000):
            idx = rng.choice(runs, len(runs), replace=True)
            sa, sb = ta.loc[idx], tb.loc[idx]
            d_f1.append(f1(sa) - f1(sb))
            d_fa.append(sa["fp_eps"].sum() / sa["hours"].sum() - sb["fp_eps"].sum() / sb["hours"].sum())
        d_f1, d_fa = np.array(d_f1), np.array(d_fa)
        fa_a = ta["fp_eps"].sum() / ta["hours"].sum(); fa_b = tb["fp_eps"].sum() / tb["hours"].sum()
        out[m] = {"f1_a": f1(ta), "f1_b": f1(tb), "diff": f1(ta) - f1(tb), "ci95": [float(np.nanpercentile(d_f1, 2.5)), float(np.nanpercentile(d_f1, 97.5))],
                  "p_diff_le_0": float(np.mean(d_f1 <= 0)), "fa_diff": fa_a - fa_b,
                  "fa_ci95": [float(np.percentile(d_fa, 2.5)), float(np.percentile(d_fa, 97.5))], "runs": int(len(runs))}
        o = out[m]
        lines.append(f"| {m} | {o['f1_a']:.3f} | {o['f1_b']:.3f} | {o['diff']:+.3f} | [{o['ci95'][0]:+.3f}, {o['ci95'][1]:+.3f}] | {o['p_diff_le_0']:.3f} | "
                     f"{o['fa_diff']:+.2f} | [{o['fa_ci95'][0]:+.2f}, {o['fa_ci95'][1]:+.2f}] |")
    lines += ["", f"Runs resampled per measurand: {', '.join(f'{m} {v['runs']}' for m, v in out.items())}; 4000 bootstrap resamples."]
    suffix = f"_{a}_vs_{b}" if len(sys.argv) > 4 else ""
    (res_dir / f"POSTHOC_PAIRED_COMPARISON{suffix}.md").write_text("\n".join(lines), encoding="utf-8")
    (res_dir / f"posthoc_paired_comparison{suffix}.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    if suffix:
        print(f"Saved: {res_dir / f'POSTHOC_PAIRED_COMPARISON{suffix}.md'}")
    else:
        print(f"Saved: {res_dir / 'POSTHOC_PAIRED_COMPARISON.md'}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
