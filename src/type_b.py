"""
Type B Uncertainty Evaluation Module for IMUCA.
Implements Equation 9.5 and Table 9.1: Probability distributions, divisors,
and systematic standard uncertainty components.
"""

from typing import Dict, List, Optional, Union, Tuple
from dataclasses import dataclass, field
import numpy as np


# Standard metrology distributions and their divisors
DISTRIBUTION_DIVISORS: Dict[str, Tuple[float, str]] = {
    "rectangular": (np.sqrt(3.0), "Uniform / Rectangular (sqrt(3))"),
    "triangular": (np.sqrt(6.0), "Triangular (sqrt(6))"),
    "normal_k2": (2.0, "Normal at k = 2 (approx. 95% confidence)"),
    "normal_k3": (3.0, "Normal at k = 3 (approx. 99.7% confidence)"),
    "u_shaped": (np.sqrt(2.0), "U-shaped / Arcsine (sqrt(2))")
}


@dataclass
class TypeBSource:
    name: str
    input_value: float              # Raw input value (e.g. 0.01 V resolution or 0.1 %)
    unit: str                       # 'V', 'mV', '% of reading', 'degC', etc.
    distribution: str               # Key in DISTRIBUTION_DIVISORS
    is_percent_of_reading: bool = False
    is_resolution: bool = False      # If True, half-width is input_value / 2
    tempco_percent_per_deg: Optional[float] = None  # For temp effects: %/degC
    sensitivity_coefficient: float = 1.0            # c_i (default 1.0 for direct voltage)
    degrees_of_freedom: Union[float, int] = np.inf  # nu_i (default infinity for reliable Type B)
    description: str = ""
    
    # Computed quantities
    half_width_v: float = 0.0
    half_width_mv: float = 0.0
    divisor: float = 1.0
    standard_uncertainty_v: float = 0.0
    standard_uncertainty_mv: float = 0.0
    scaled_uncertainty_mv: float = 0.0  # c_i * u_i in mV
    
    def evaluate(self, reading_v: float) -> "TypeBSource":
        """
        Calculate half-width and standard uncertainty based on the current reading.
        """
        div, _ = DISTRIBUTION_DIVISORS.get(self.distribution, (np.sqrt(3.0), "Rectangular"))
        self.divisor = float(div)
        
        # Calculate half-width in Volts
        if self.tempco_percent_per_deg is not None:
            # Ambient temperature: tempco (%/degC) * reading * delta_T
            # input_value is delta_T in degC
            tempco_fraction = (self.tempco_percent_per_deg / 100.0)
            self.half_width_v = tempco_fraction * reading_v * self.input_value
        elif self.is_resolution:
            # Display resolution: half-width is resolution / 2
            self.half_width_v = self.input_value / 2.0
        elif self.is_percent_of_reading:
            # Percentage of reading: (percent / 100) * reading
            self.half_width_v = (self.input_value / 100.0) * reading_v
        else:
            # Fixed value in Volts
            self.half_width_v = self.input_value
            
        self.half_width_mv = self.half_width_v * 1000.0
        self.standard_uncertainty_v = self.half_width_v / self.divisor
        self.standard_uncertainty_mv = self.standard_uncertainty_v * 1000.0
        self.scaled_uncertainty_mv = self.sensitivity_coefficient * self.standard_uncertainty_mv
        return self


@dataclass
class TypeBResult:
    sources: List[TypeBSource]
    combined_type_b_v: float
    combined_type_b_mv: float
    reading_v: float


def get_default_type_b_sources(reading_v: float = 5.021) -> List[TypeBSource]:
    """
    Construct the four standard Type B sources documented in Section 10 & 11 of the project report.
    """
    sources = [
        TypeBSource(
            name="Display resolution",
            input_value=0.01,  # 0.01 V resolution -> half-width = 5.000 mV
            unit="V",
            distribution="rectangular",
            is_resolution=True,
            sensitivity_coefficient=1.0,
            degrees_of_freedom=np.inf,
            description="3½-digit DMM 20 V range quantisation (10 mV step, half-width 5 mV)"
        ),
        TypeBSource(
            name="DUT specification",
            input_value=0.1,   # +/- 0.1 % of reading
            unit="%",
            distribution="rectangular",
            is_percent_of_reading=True,
            sensitivity_coefficient=1.0,
            degrees_of_freedom=np.inf,
            description="Manufacturer accuracy tolerance (+/- 0.1 % of reading)"
        ),
        TypeBSource(
            name="Reference standard",
            input_value=0.002, # U = 0.002 V at k = 2
            unit="V",
            distribution="normal_k2",
            sensitivity_coefficient=1.0,
            degrees_of_freedom=np.inf,
            description="Traceable calibration standard certificate uncertainty (k = 2)"
        ),
        TypeBSource(
            name="Ambient temperature",
            input_value=3.0,   # +/- 3 degC variation
            unit="degC",
            distribution="rectangular",
            tempco_percent_per_deg=0.005,  # 0.005 %/degC
            sensitivity_coefficient=1.0,
            degrees_of_freedom=np.inf,
            description="Ambient temperature variation (+/- 3 °C at 0.005 %/°C tempco)"
        )
    ]
    for s in sources:
        s.evaluate(reading_v)
    return sources


def evaluate_type_b(
    sources: List[TypeBSource],
    reading_v: float
) -> TypeBResult:
    """
    Evaluate all Type B uncertainty sources for a given operating point reading.
    """
    evaluated_sources = []
    sum_sq_mv = 0.0
    
    for s in sources:
        s.evaluate(reading_v)
        evaluated_sources.append(s)
        sum_sq_mv += (s.scaled_uncertainty_mv) ** 2
        
    comb_b_mv = float(np.sqrt(sum_sq_mv))
    comb_b_v = comb_b_mv / 1000.0
    
    return TypeBResult(
        sources=evaluated_sources,
        combined_type_b_v=comb_b_v,
        combined_type_b_mv=comb_b_mv,
        reading_v=reading_v
    )
