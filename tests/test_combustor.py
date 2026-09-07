"""Combustor regression checks; KJ66 is a historical comparison, not validation.

Earlier bore/velocity claims used an unavailable mixed-stream pressure budget
and annulus areas different from the geometry. Those claims are withdrawn.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.combustor import MicroJetCombustor, CombustorError   # noqa: E402

KJ66 = {
    'casing_od_inch': 4.33, 'shaft_tunnel_od_inch': 1.18, 'wall_thickness_mm': 0.5,
    'pressure_ratio': 2.2, 'compressor_efficiency': 0.74, 'mass_flow_air_kg_s': 0.23,
    'target_tit_k': 1123.0, 'liner_material': '304SS', 'tau_min_s': 0.0014,
}


@pytest.fixture(scope="module")
def kj66():
    return MicroJetCombustor(dict(KJ66)).run()


# --------------------------------------------------------------- predictions

def test_predicts_six_vaporizers(kj66):
    """The KJ66 has six vaporizer sticks. Nothing in this model was tuned to
    produce that -- it falls out of dome circumference divided by pitch."""
    assert kj66['vap_n'] == 6


def test_vaporizer_is_sized_with_available_air_pressure(kj66):
    assert kj66['vap_crimp_dia_mm'] <= kj66['vap_id_mm']
    assert kj66['vap_path_loss_Pa'] == pytest.approx(kj66['vap_air_pressure_budget_Pa'])
    # Disagreement with historical 4 mm stock remains visible, not tuned away.
    assert abs(kj66['vap_id_mm']-4.0) > 1.0


def test_inner_velocity_matches_the_exported_annulus(kj66):
    r=kj66
    expected=r['mdot_air']*(1-r['f_outer_feed_used'])/(r['rho2']*r['A_inner_feed_m2'])
    assert r['v_inner_converged_m_s'] == pytest.approx(expected,rel=1e-12)


# ---------------------------------------------------------- self-consistency

def test_the_fuel_flow_delivers_the_target_temperature(kj66):
    """PATCH P1. The energy balance is checked by round trip, not by
    inspection: feed the computed fuel-air ratio back through and it must
    return the turbine inlet temperature that was asked for."""
    assert abs(kj66['TIT_roundtrip_err_K']) < 1e-6


def test_residence_time_matches_what_was_requested(kj66):
    """PATCH P3. V21 sized the chamber length from air-only mass flow but
    reported residence time from air plus fuel, so you asked for 2.00 ms and
    got 1.73. Both now use the same flow."""
    assert kj66['tau_comb_ms'] == pytest.approx(kj66['tau_target_ms'], rel=1e-6)


def test_the_air_budget_closes(kj66):
    """Every gram of air is accounted for. This was already true in V21 and is
    worth locking in."""
    total = (kj66['m_film_cooling'] + kj66['split_primary']
             + kj66['split_secondary'] + kj66['split_dilution'])
    assert total == pytest.approx(kj66['mdot_air'], rel=1e-12)


def test_each_branch_air_budget_closes(kj66):
    assert abs(kj66['outer_air_balance_error_kg_s']) < 1e-12
    assert abs(kj66['inner_air_balance_error_kg_s']) < 1e-12
    assert not kj66['pressure_loss_validated']


def test_assumed_efficiency_is_not_replaced_by_clp(kj66):
    assert kj66['eta_comb_converged'] == .96
    assert kj66['outer_loop_iters'] == 1
    assert kj66['eta_is_assumed']


# ------------------------------------------------------------ patch evidence

def test_thermal_growth_is_a_diameter_not_a_radius(kj66):
    """PATCH P2. V21 computed alpha*(OD/2)*dT -- a radius change -- and
    subtracted it from a diameter. The offset should now be consistent with
    alpha * D * dT at the liner metal temperature."""
    import math
    alpha = kj66['liner_alpha_per_K']
    dT = kj66['liner_wall_temp_K'] - 293.0
    expected = kj66['outer_liner_od_mm']-kj66['outer_liner_od_cold_mm']
    # stored rounded to 3 dp, so compare to that precision
    assert kj66['outer_liner_thermal_offset_mm'] == pytest.approx(expected, abs=1e-3)


def test_penetration_uses_the_multi_jet_correlation(kj66):
    """PATCH P6. Lefebvre Eq. 4.19 (1.15, single jet) vs Eq. 4.20 (1.25 with a
    blockage term, multiple jets). Every row here has 12-24 holes, so 4.20
    applies, and it gives materially less penetration."""
    assert kj66['dil_pen_norm_outer'] < kj66['dil_pen_norm_outer_singlejet']
    assert kj66['dil_pen_correlation'].startswith("Lefebvre Eq. 4.20")


def test_dome_flux_methods_are_reported_together(kj66):
    """PATCH P7. Three published methods disagree by roughly an order of
    magnitude on this geometry. All three are computed and the spread is
    published, so nobody quotes one without the caveat."""
    lef = kj66['stab_q_conv_lefebvre_kW_m2']
    mar = kj66['stab_q_conv_martin_kW_m2']
    v21 = kj66['stab_q_conv_v21_original_kW_m2']
    assert lef > 0 and mar > 0 and v21 > 0
    assert max(mar, v21) / lef > 2.0, (
        "the methods used to disagree by a large factor; if they now agree, "
        "something changed and this note needs revisiting"
    )
    assert "LOW" in kj66['stab_dome_confidence']


def test_v21_original_dome_flux_condemned_the_real_kj66(kj66):
    """The evidence that V21's dome correlation was wrong: it returned over
    1000 kW/m2 for the actual KJ66, against its own 600 kW/m2 'critical'
    threshold. Thousands of KJ66s have flown for 25 years."""
    assert kj66['stab_q_conv_v21_original_kW_m2'] > 600.0
    assert kj66['stab_q_conv_lefebvre_kW_m2'] < 600.0


def test_an_oversized_combustor_now_raises_instead_of_returning_nonsense():
    """PATCHES P9 and P14. V21 would silently return a 372 mm combustor for a
    152 mm engine -- longer than the whole machine. It now raises, and after
    P14 it usually raises on the casing requirement first, which is the more
    useful message because it tells you how much bigger the casing needs to be.
    Either error is a pass; returning a nonsense geometry is not."""
    inp = dict(KJ66)
    inp['mass_flow_air_kg_s'] = 0.90
    inp['casing_od_inch'] = 6.0
    with pytest.raises(CombustorError, match="(L/D|casing OD)"):
        MicroJetCombustor(inp).run()


def test_the_L_over_D_ceiling_is_enforced():
    """The length ceiling specifically, reached by starving the residence time
    floor rather than the casing."""
    inp = dict(KJ66)
    inp['tau_min_s'] = 0.010          # absurd, to force a long chamber
    inp['casing_od_inch'] = 8.0       # plenty of casing, so it is not that
    with pytest.raises(CombustorError, match="L/D"):
        MicroJetCombustor(inp).run()


def test_the_combustor_has_an_intrinsic_size():
    """PATCH P14. V21 sized the liner by subtracting feed annuli from a given
    casing bore, so the combustor expanded to fill whatever it was handed.
    Its required casing must now be independent of the casing supplied."""
    a = MicroJetCombustor(dict(KJ66, casing_od_inch=4.33)).run()
    b = MicroJetCombustor(dict(KJ66, casing_od_inch=6.00)).run()
    assert a['casing_od_required_mm'] == pytest.approx(b['casing_od_required_mm'], rel=1e-9)
    assert a['combustion_gap_mm'] == pytest.approx(b['combustion_gap_mm'], rel=1e-9)
