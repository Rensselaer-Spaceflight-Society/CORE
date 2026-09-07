"""
Gas model validation.

The gas model sits underneath every other module, so it gets validated against
published air property tables rather than against itself. If these fail,
nothing downstream means anything.

Table data: standard air properties (Keenan & Kaye; reproduced as Cengel &
Boles Table A-17). Values are enthalpy in kJ/kg and cp in J/kg K.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import gas   # noqa: E402

# (T [K], cp [J/kgK], h [kJ/kg])
AIR_TABLE = [
    (300, 1005, 300.19), (400, 1013, 400.98), (500, 1030, 503.02),
    (600, 1051, 607.02), (700, 1075, 713.27), (800, 1099, 821.95),
    (900, 1121, 932.93), (1000, 1141, 1046.04), (1100, 1159, 1161.07),
    (1200, 1175, 1277.79), (1300, 1189, 1395.97), (1400, 1202, 1515.42),
    (1500, 1214, 1635.97), (1600, 1225, 1757.57), (1800, 1244, 2003.30),
]
H_DATUM_KJ = 300.19     # table value at the 300 K datum


@pytest.mark.parametrize("T,cp_table,_h", AIR_TABLE)
def test_cp_air_matches_tables(T, cp_table, _h):
    """cp within 0.5% of published air tables from 300 to 1800 K."""
    err = abs(gas.cp_air(T) - cp_table) / cp_table
    assert err < 0.005, f"cp_air({T}) = {gas.cp_air(T):.1f} vs table {cp_table}"


@pytest.mark.parametrize("T,_cp,h_table", AIR_TABLE)
def test_enthalpy_matches_tables(T, _cp, h_table):
    """Enthalpy rise within 0.5% of tables. This is the one that matters --
    the fuel-air ratio is an enthalpy difference, not a cp."""
    dh_table = (h_table - H_DATUM_KJ) * 1000.0
    dh_model = gas.h_air(T)
    if dh_table == 0:
        assert abs(dh_model) < 1.0
        return
    err = abs(dh_model - dh_table) / dh_table
    assert err < 0.005, f"h_air({T}) = {dh_model/1000:.1f} kJ/kg vs table {dh_table/1000:.1f}"


@pytest.mark.parametrize("T3,T4", [(300, 900), (384, 1000), (437.6, 1150), (500, 1400)])
def test_far_round_trips(T3, T4):
    """far_for_T4 and T4_for_far must invert each other.

    This is the test that makes the energy balance trustworthy: it is checked
    by round trip, not by inspection. Any change to the gas model that breaks
    self-consistency fails here rather than showing up as a wrong fuel flow
    three modules downstream.
    """
    far = gas.far_for_T4(T3, T4, 0.98, 43.1e6)
    T4_back = gas.T4_for_far(T3, far, 0.98, 43.1e6)
    assert abs(T4_back - T4) < 1e-3, f"round trip gave {T4_back:.6f} K, expected {T4}"


def test_far_is_in_a_physical_range():
    """A kerosene turbojet runs f between roughly 0.010 and 0.030. Anything
    outside that is a modelling error, not a design choice."""
    far = gas.far_for_T4(437.6, 1150.0, 0.98, 43.1e6)
    assert 0.010 < far < 0.030, f"fuel-air ratio {far:.4f} is not physical"


def test_constant_cp_form_would_have_been_wrong():
    """Documents the bug this model replaced, so nobody reintroduces it.

    The old form was far = (cp_h*T4 - cp_c*T3)/(eta_b*LHV - cp_h*T4) with
    cp_c = 1005 and cp_h = 1150 as constants. It over-predicts by more than
    10%. If somebody 'simplifies' the gas model back to constant cp, this
    test tells them what it costs.
    """
    T3, T4, eta_b, LHV = 437.6, 1150.0, 0.98, 43.1e6
    far_correct = gas.far_for_T4(T3, T4, eta_b, LHV)
    far_const_cp = (1150 * T4 - 1005 * T3) / (eta_b * LHV - 1150 * T4)
    over = far_const_cp / far_correct - 1.0
    assert over > 0.10, (
        "the constant-cp form used to over-predict by >10%; if that has "
        "changed, the gas model changed and this note needs updating"
    )


def test_products_are_heavier_on_cp_than_air():
    """Products carry slightly more cp than air, and the correction grows
    with fuel-air ratio. Small, but it should have the right sign."""
    assert gas.cp_products(1200, 0.0) == pytest.approx(gas.cp_air(1200))
    assert gas.cp_products(1200, 0.02) > gas.cp_air(1200)
    assert gas.cp_products(1200, 0.02) / gas.cp_air(1200) < 1.03


def test_choked_area_and_exit_velocity_agree_at_the_choke_point():
    """Two independent paths to the same physics -- if the nozzle is exactly
    choked, the area from choked_area must pass the mass flow that
    exit_velocity implies."""
    mdot, T0, P0, g, R, cp = 0.5, 1000.0, 300000.0, 1.333, 287.0, 1150.0
    A = gas.choked_area(mdot, T0, P0, g, R)
    V, T_e, P_e, choked = gas.exit_velocity(T0, P0, P0 / gas.critical_pressure_ratio(g), cp, g, R)
    assert choked
    rho = gas.density(P_e, T_e, R)
    assert rho * V * A == pytest.approx(mdot, rel=1e-6)
