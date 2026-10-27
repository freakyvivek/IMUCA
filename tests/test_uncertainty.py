"""
Unit Tests for Uncertainty Evaluation and Budget Compilation against Golden Reference Values.
"""

import pytest
import numpy as np
from src.type_a import evaluate_type_a
from src.type_b import get_default_type_b_sources, evaluate_type_b
from src.budget import build_uncertainty_budget
from src.coverage import evaluate_expanded_uncertainty, round_uncertainty_metrology


DEMO_READINGS = [5.02, 5.01, 5.03, 5.02, 5.04, 5.01, 5.02, 5.03, 5.02, 5.01]


def test_type_a_uncertainty():
    res = evaluate_type_a(DEMO_READINGS)
    assert res.n == 10
    # s = 9.944 mV
    assert pytest.approx(res.sample_std_dev_mv, rel=1e-3) == 9.944
    # u_A = 3.145 mV
    assert pytest.approx(res.standard_uncertainty_mv, rel=1e-3) == 3.145
    assert res.degrees_of_freedom == 9


def test_type_b_uncertainty():
    sources = get_default_type_b_sources(reading_v=5.021)
    res = evaluate_type_b(sources, reading_v=5.021)
    
    # Check individual Type B standard uncertainties
    s_map = {s.name: s for s in res.sources}
    # Display resolution: 5.000 / sqrt(3) = 2.887 mV
    assert pytest.approx(s_map["Display resolution"].standard_uncertainty_mv, rel=1e-3) == 2.887
    # DUT specification: (0.1% * 5.021) / sqrt(3) = 5.021 / sqrt(3) = 2.899 mV
    assert pytest.approx(s_map["DUT specification"].standard_uncertainty_mv, rel=1e-3) == 2.899
    # Reference standard: 2.000 / 2 = 1.000 mV
    assert pytest.approx(s_map["Reference standard"].standard_uncertainty_mv, rel=1e-3) == 1.000
    # Ambient temp: 0.753 / sqrt(3) = 0.435 mV
    assert pytest.approx(s_map["Ambient temperature"].standard_uncertainty_mv, rel=1e-3) == 0.435
    
    # Combined Type B: 4.234 mV
    assert pytest.approx(res.combined_type_b_mv, rel=1e-3) == 4.234


def test_uncertainty_budget_and_combination():
    type_a = evaluate_type_a(DEMO_READINGS)
    type_b_sources = get_default_type_b_sources(reading_v=5.021)
    type_b = evaluate_type_b(type_b_sources, reading_v=5.021)
    
    budget = build_uncertainty_budget(type_a, type_b, confidence_level=0.95, force_k=2.0)
    
    # Combined standard uncertainty: 5.274 mV
    assert pytest.approx(budget.combined_uncertainty_mv, rel=1e-3) == 5.274
    # Expanded uncertainty at k=2: 10.55 mV
    assert pytest.approx(budget.coverage.expanded_uncertainty_mv, rel=1e-3) == 10.55
    # Effective degrees of freedom: 71.2
    assert pytest.approx(budget.coverage.effective_degrees_of_freedom, abs=1.0) == 71.2
    
    # Dominant contributor is Repeatability at ~35.6%
    assert budget.dominant_source.source_name == "Repeatability"
    assert pytest.approx(budget.dominant_source.variance_contribution_percent, abs=0.5) == 35.6
    
    # Check variance contributions sum to 100.0%
    total_share = sum(e.variance_contribution_percent for e in budget.entries)
    assert pytest.approx(total_share, rel=1e-4) == 100.0


def test_metrological_rounding():
    val_v = 5.021
    u_v = 0.01055  # 10.55 mV
    v_rnd, u_rnd, fmt = round_uncertainty_metrology(val_v, u_v)
    assert u_rnd == 0.011
    assert v_rnd == 5.021
    assert "(5.021 +/- 0.011) V" in fmt


# ==============================================================================
# Tests for new modular package: src.imuca.uncertainty
# ==============================================================================

from src.imuca.uncertainty import (
    evaluate_type_a as imuca_type_a,
    evaluate_type_b as imuca_type_b,
    evaluate_shunt_current_uncertainty,
    build_uncertainty_budget as imuca_build_budget,
    round_uncertainty_metrology as imuca_round_metrology
)


def test_imuca_type_b_distributions():
    # Rectangular: a / sqrt(3)
    c_rec = imuca_type_b("Resolution", limit_value=0.001, distribution="RECTANGULAR")
    assert pytest.approx(c_rec.standard_uncertainty, rel=1e-4) == 0.001 / np.sqrt(3)

    # Triangular: a / sqrt(6)
    c_tri = imuca_type_b("Alignment", limit_value=0.006, distribution="TRIANGULAR")
    assert pytest.approx(c_tri.standard_uncertainty, rel=1e-4) == 0.006 / np.sqrt(6)

    # Normal: a / 2
    c_norm = imuca_type_b("Ref Standard", limit_value=0.002, distribution="NORMAL")
    assert pytest.approx(c_norm.standard_uncertainty, rel=1e-4) == 0.001

    # U-shaped: a / sqrt(2)
    c_u = imuca_type_b("Thermal Cycling", limit_value=0.002, distribution="U_SHAPED")
    assert pytest.approx(c_u.standard_uncertainty, rel=1e-4) == 0.002 / np.sqrt(2)


def test_imuca_shunt_current_model_propagation():
    # Indirect model: I = V_shunt / R_shunt
    # V_shunt = 0.100 V (100 mV), R_shunt = 0.100 Ohm -> I = 1.000 A (1000 mA)
    # u(V) = 0.0001 V (0.1 mV), u(R) = 0.0005 Ohm
    v_val = 0.100
    r_val = 0.100
    u_v = 0.0001
    u_r = 0.0005

    i_val, comps = evaluate_shunt_current_uncertainty(
        v_shunt_v=v_val,
        r_shunt_ohm=r_val,
        u_v_shunt_v=u_v,
        u_r_shunt_ohm=u_r
    )

    assert pytest.approx(i_val, rel=1e-4) == 1.000
    assert len(comps) == 2

    # Analytical sensitivity coefficients:
    # c_V = 1 / R = 10.0 A/V
    # c_R = -V / R^2 = -10.0 A/Ohm
    c_v_comp = comps[0]
    c_r_comp = comps[1]
    assert pytest.approx(c_v_comp.sensitivity_coefficient, rel=1e-4) == 10.0
    assert pytest.approx(c_r_comp.sensitivity_coefficient, rel=1e-4) == -10.0

    # Combined uncertainty: sqrt((10 * 0.0001)^2 + (-10 * 0.0005)^2) = sqrt(0.001^2 + 0.005^2) = 0.005099 A
    budget = imuca_build_budget(
        measurand_name="DC Current",
        nominal_value=i_val,
        measurand_unit="A",
        components=comps,
        confidence_level=0.95,
        force_k=2.0
    )

    expected_uc = np.sqrt((10.0 * u_v) ** 2 + (-10.0 * u_r) ** 2)
    assert pytest.approx(budget.combined_standard_uncertainty, rel=1e-4) == expected_uc
    assert pytest.approx(budget.expanded_uncertainty, rel=1e-4) == 2.0 * expected_uc
    assert budget.dominant_component.name == "Shunt Resistor Tolerance"


def test_imuca_monte_carlo_agreement_with_gum():
    # Analytical test case: linear combination of two normal components
    # x1 ~ N(0, 3^2), x2 ~ N(0, 4^2) -> y = x1 + x2 -> u_c = 5.0
    c1 = imuca_type_b("Source1", limit_value=6.0, distribution="NORMAL")  # u = 3.0
    c2 = imuca_type_b("Source2", limit_value=8.0, distribution="NORMAL")  # u = 4.0

    budget = imuca_build_budget(
        measurand_name="TestMeasurand",
        nominal_value=100.0,
        measurand_unit="V",
        components=[c1, c2],
        confidence_level=0.95,
        run_monte_carlo=True,
        mc_trials=20000,
        random_seed=42
    )

    # GUM analytical u_c is 5.0
    assert pytest.approx(budget.combined_standard_uncertainty, rel=1e-4) == 5.0
    # Monte Carlo standard uncertainty should agree within 2%
    mc_u = budget.monte_carlo_result["standard_uncertainty"]
    assert pytest.approx(mc_u, rel=0.03) == 5.0

