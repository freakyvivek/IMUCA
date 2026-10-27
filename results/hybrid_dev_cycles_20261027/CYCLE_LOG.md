# Milestone 7 — development cycle log (2026-10-27)

All development and selection used **v3 calibration + validation runs only**. The v3, v4, and v5 test partitions were never loaded into any detector during this development process. Validation metrics are developmental and optimistic; independent confirmatory evidence is established exclusively by the final single-evaluation run on the fresh test suite (`v5`).

Baseline: Milestone 6 final bundle (`results/hybrid_frozen_20261026_123033`) evaluated on v4 test (`results/hybrid_final_20261026_123148`). Key identified deficiencies were:
1. **Current channel:** Spike recall dropped to 57/72 (MAD 12 trade-off), false alarms rose to 1.7/h, and classification accuracy regressed to 0.813 with poor offset shift attribution (6/15).
2. **Temperature channel:** Post-fault alarm overhang was 41.0 records/h (latched drift lifecycle selected over hysteresis), slow drift detection (142 s delay), and low recall on noisy/slow thermocouple variant TC (32/54).
3. **Voltage channel:** Severe false alarm rate during settling phases (20.5 FA/h over 0.24 h exposure).
4. **Fault attribution:** Abrupt changes and offset shifts misclassified due to missing persistent-episode confirmation fallback in `confirm_categories_error`.

---

### Development Cycles Summary Matrix

| Cycle | Workstream(s) | Profile / Change | Validation Evidence (v3 Validation) | Tests / Verification |
|---|---|---|---|---|
| **Cycle 1** | WS1, WS2, WS3 | `m7_cycle1_current_curvature`: Introduced `transient_extra="curvature_all"` option; added `settling_suppression` parameter to transient flags; expanded MAD grid (3.5–15.0). | Voltage settling FA/h dropped from 11.6 to **0.0/h** under `settling_suppression=True` (transient F1 0.915 → 0.923). Current curvature_all at z=10 gave F1 0.917 at MAD 12. Fixed long-episode fallback in `confirm_categories_error`, instantly recovering offset shift attribution to 5/6 (current) and 3/5 (temperature). | 20 lifecycle tests passed; 165 total tests passed. |
| **Cycle 2** | WS1, WS2 | `m7_cycle2_temperature_lifecycle`: Refined lifecycle tie-breaking to prefer `hysteresis` over `latched` on equal overhang/FA; expanded clearance options (W=60, 90, 120; clear_sigma=0.5, 0.75; clear_z=2.0; explain_before=15). | Full hybrid F1: Voltage 0.927, Current 0.838, Temperature 0.846. **Hysteresis successfully selected for current and temperature** (W=60, z=2.0), resolving the permanent overhang lock without sacrificing drift recall. | All regression tests passed. |
| **Cycle 3** | WS3, WS4 | `m7_cycle3_settling_attribution`: Evaluated confirmed attribution with error-based vs signal-based source across confirm_delays (30, 45). | Voltage attribution selected `confirmed` with error source (accuracy 0.843, 3/6 offsets, 2/2 gains, 23/23 spikes). Temperature selected `confirmed` with error source (accuracy 0.891, 3/5 offsets, 1/1 gain). | Regression tests for persistent episode confirmation verified. |
| **Cycle 4** | All (WS1–5) | `m7_final_freeze`: Freeze candidate uniting the optimal selections across all 5 workstreams. Restored confirm_delay 0 and 15 options for error-based attribution. | Full joint selection confirmed: Voltage F1 0.927, Current F1 0.838, Temperature F1 0.846. Classification: Voltage 0.843, Current 0.896 (with 5/6 offsets, 1/1 gains), Temperature 0.891. Both Current and Temperature adopt `hysteresis` lifecycle and `confirmed` error attribution. Ready for freezing. | Full repository test suite passed (165/165). |

---

### Key Architectural Fixes & Verifications

1. **Long-Episode Persistent Confirmation Fallback in `confirm_categories_error`:**
   Previously, when a persistent offset shift occurred and the hybrid alarm persisted through the end of the run, `cand = np.flatnonzero(ok & ~alarm)` after `e0 + D` had fewer than 5 samples (`len(post) < 5`). This caused `confirm_categories_error` to execute `continue`, abandoning the episode in its provisional `transient` category. Adding the `elif e0 - s0 + 1 >= L + D:` block checks the error shift within the active persistent episode `err[s0 + D:e0 + 1]`. If shifted by $> \text{confirm\_k} \cdot \sigma$, it confirms `out[span] = "persistent"`.

2. **Settling Suppression in Transient Processing:**
   When `settling_suppression = True`, the segment detector flags in non-stationary and settling phases are suppressed (`flags = flags & ~settling`), while discrete second-difference curvature flags (`curvature_z > threshold`) are preserved. This prevents false positive trips during capacitive/thermal decay while retaining impulse spike sensitivity.

3. **Lifecycle Selection Tie-Breaking:**
   When `hysteresis` and `latched` achieve identical overhang counts and false alarm rates on validation, the selection key now prefers `hysteresis` (`is_latched = 1 if latched else 0`), ensuring alarms clear when signals return to baseline.
