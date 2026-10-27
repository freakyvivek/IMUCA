"""
Action Mapping and Recommendation Synthesis for IMUCA Decision Engine.
"""

from typing import Dict, List, Optional


ACTION_DEFINITIONS: Dict[str, Dict[str, str]] = {
    "R1": {
        "status": "HIGH UNCERTAINTY",
        "headline": "ATTENTION REQUIRED",
        "action": "Result not fit for the stated purpose; reduce dominant contributor before use.",
        "detail": "Expanded uncertainty exceeds allowable limits. Inspect top contributor in uncertainty budget table."
    },
    "R2": {
        "status": "CALIBRATION REQUIRED",
        "headline": "CALIBRATION REQUIRED",
        "action": "Adjust, correct or withdraw the instrument.",
        "detail": "Guard-banded or simple error exceeds tolerance band. Instrument must be adjusted or compensated."
    },
    "R3": {
        "status": "POSSIBLE DRIFT",
        "headline": "ATTENTION REQUIRED",
        "action": "Shorten calibration interval; schedule recalibration before projected breach.",
        "detail": "Statistically significant between-session drift detected. Linear extrapolation projects future tolerance breach."
    },
    "R4": {
        "status": "REPEATABILITY CONCERN",
        "headline": "ATTENTION REQUIRED",
        "action": "Investigate connections, thermal settling, noise.",
        "detail": "Sample standard deviation exceeds allowable dispersion limits. Check test fixture contact resistance and ambient stability."
    },
    "R5": {
        "status": "MEASUREMENT ACCEPTABLE",
        "headline": "ACCEPTABLE",
        "action": "Release result; retain for drift history.",
        "detail": "Measurement satisfies all uncertainty, tolerance, repeatability, and drift criteria."
    }
}


def synthesize_recommendation(
    headline_status: str,
    triggered_rules: List[str],
    has_sweep_failure: bool = False,
    sweep_nonconforming_points: Optional[List[int]] = None,
    projected_breach_session: Optional[float] = None,
    dominant_source_name: Optional[str] = None
) -> str:
    """
    Construct a complete, clear, and actionable engineering recommendation.
    """
    if "R2" in triggered_rules:
        return (
            "CALIBRATION REQUIRED. Measurement error exceeds allowable guard-banded tolerance. "
            "Withdraw instrument from critical use or apply documented offset and gain corrections."
        )
    elif "R3" in triggered_rules:
        rec_session = int(projected_breach_session - 4) if projected_breach_session else "earlier"
        return (
            f"ATTENTION REQUIRED. Significant drift trend detected. Shorten calibration interval and "
            f"schedule recalibration before session {rec_session} to maintain safety margin against projected breach at session {projected_breach_session}."
        )
    elif "R1" in triggered_rules:
        return (
            f"ATTENTION REQUIRED. High uncertainty detected. Dominant contributor is '{dominant_source_name}'. "
            f"Refine measurement setup to reduce this component before certifying result."
        )
    elif "R4" in triggered_rules:
        return (
            "ATTENTION REQUIRED. Repeatability scatter is abnormally large. Investigate cable shielding, "
            "DUT thermal equilibration, or environmental electrical noise."
        )
    else:
        # Default R5 Acceptable
        if has_sweep_failure and sweep_nonconforming_points:
            pts_str = ", ".join(str(p) for p in sweep_nonconforming_points)
            return (
                f"MEASUREMENT ACCEPTABLE. Release result and retain for drift history. "
                f"Note that sweep point(s) {pts_str} (e.g. 0.5 V) exhibited non-conformity; "
                f"restrict use to the range above 1.5 V or apply documented offset and gain correction."
            )
        return "MEASUREMENT ACCEPTABLE. Release result and retain for drift history."
