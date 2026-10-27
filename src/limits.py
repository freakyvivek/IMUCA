"""
Engineering Limits and Configuration for IMUCA Decision Engine.
"""

from dataclasses import dataclass


@dataclass
class EngineeringLimits:
    u_allowable_mv: float = 25.0       # Maximum acceptable expanded uncertainty U (mV)
    tolerance_mv: float = 50.0         # Acceptance tolerance T at reference point (+/- 50 mV)
    drift_threshold_mv: float = 0.50   # Maximum acceptable drift rate b (mV / session)
    s_allowable_mv: float = 15.0       # Maximum acceptable sample standard deviation s (mV)
    confidence_level: float = 0.95     # Default 95% confidence level
    coverage_factor_k: float = 2.0     # Default k = 2
