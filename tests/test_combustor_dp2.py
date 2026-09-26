"""DP-2 regressions: inlet state, local path budgets, geometry and reporting."""
import math

import pytest

from core import gas, thermo
from core.combustor import CombustorError, MicroJetCombustor
from V22_CombustionChamberDesign import dp2_inputs, kj66_inputs, print_report


def solve(**overrides):
    return MicroJetCombustor(dict(dp2_inputs, **overrides)).run()


@pytest.fixture(scope='module')
def dp2():
    return solve()


def test_dp2_matches_archived_cycle_screen(dp2):
    assert dp2['P2_Pa'] == pytest.approx(101325*.99*1.63)
    assert dp2['T2_K'] == pytest.approx(348.10, abs=.01)
    assert dp2['mdot_fuel']*3600 == pytest.approx(23.72, abs=.01)
    assert abs(dp2['TIT_roundtrip_err_K']) < 1e-6
    assert dp2['tau_comb_ms'] == pytest.approx(2.0)


def test_recovery_changes_pressure_without_changing_compressor_work(dp2):
    ideal = solve(inlet_pressure_recovery=1)
    assert dp2['P2_Pa'] == pytest.approx(ideal['P2_Pa']*.99)
    assert dp2['T2_K'] == ideal['T2_K']
    assert dp2['FAR'] == ideal['FAR']


def test_supplied_inlet_state_is_not_corrected_twice(dp2):
    supplied = solve(inlet_total_pressure_Pa=dp2['P2_Pa'],
                     inlet_total_temperature_K=dp2['T2_K'])
    assert supplied['P2_Pa'] == dp2['P2_Pa']
    assert supplied['T2_K'] == dp2['T2_K']
    assert supplied['mdot_fuel'] == dp2['mdot_fuel']


@pytest.mark.parametrize('key', ['inlet_total_pressure_Pa', 'inlet_total_temperature_K'])
def test_incomplete_inlet_state_is_rejected(key):
    with pytest.raises(CombustorError, match='both inlet'):
        solve(**{key: 350})


@pytest.mark.parametrize('value', [0, -1, 1.01, float('nan')])
def test_invalid_recovery_is_rejected(value):
    with pytest.raises(gas.GasError):
        solve(inlet_pressure_recovery=value)


@pytest.mark.parametrize('split,tunnel,loss', [(.6, 2, .04), (.8, 2, .04),
                                           (.6, 1.5, .04), (.6, 2, .025)])
def test_inner_K_uses_real_geometry_and_path_head(split, tunnel, loss):
    r = solve(f_outer_feed=split, shaft_tunnel_od_inch=tunnel, target_pressure_drop=loss)
    do, di = r['inner_liner_id_mm']/1000, tunnel*.0254
    area = math.pi*(do*do-di*di)/4
    v = .30*(1-split)/(r['rho2']*area)
    dh = do-di
    reynolds = r['rho2']*v*dh/1.85e-5
    friction = 64/reynolds if reynolds < 2300 else .316/reynolds**.25
    path_loss = (.5+friction*r['chamber_length_mm']/1000/dh)*r['rho2']*v*v/2
    _, static_pressure = thermo.static(r['T2_K'], r['P2_Pa']-path_loss, v)
    measured_K = (static_pressure-r['exit_P4_Pa'])/(.5*r['rho2']*v*v)
    assert measured_K == pytest.approx(6, rel=1e-7)
    assert r['hole_K_inner'] == pytest.approx(measured_K, rel=1e-10)
    assert r['A_inner_feed_m2'] == pytest.approx(area)
    assert r['v_inner_annulus'] == pytest.approx(v)
    assert r['casing_od_required_mm'] < r['casing_od_mm']
    for side in ('inner', 'outer'):
        assert abs(r[side+'_air_balance_error_kg_s']) < 1e-12
    assert r['vap_path_loss_Pa'] == pytest.approx(r['vap_air_pressure_budget_Pa'])


def test_K_target_changes_geometry_without_stealing_flame_volume(dp2):
    stronger = solve(target_inner_hole_K=8)
    legacy = solve(target_inner_hole_K=None)
    assert stronger['A_inner_feed_m2'] > dp2['A_inner_feed_m2'] > legacy['A_inner_feed_m2']
    assert stronger['v_inner_annulus'] < dp2['v_inner_annulus'] < legacy['v_inner_annulus']
    assert stronger['hole_K_inner'] == pytest.approx(8, rel=1e-7)
    assert stronger['combustion_annulus_A'] == pytest.approx(legacy['combustion_annulus_A'])
    assert stronger['chamber_length_mm'] == pytest.approx(legacy['chamber_length_mm'])
    assert stronger['casing_od_required_mm'] > legacy['casing_od_required_mm']


def test_legacy_kj66_can_opt_into_K_sizing():
    old = MicroJetCombustor(dict(kj66_inputs)).run()
    new = MicroJetCombustor(dict(kj66_inputs, target_inner_hole_K=6)).run()
    assert old['hole_K_inner'] < 2
    assert new['hole_K_inner'] == pytest.approx(6, rel=1e-7)


def test_explicit_inner_velocity_now_controls_the_area():
    r = solve(target_inner_hole_K=None, target_inner_annulus_vel=30)
    assert r['v_inner_annulus'] == pytest.approx(30)
    with pytest.raises(CombustorError, match='choose'):
        solve(target_inner_annulus_vel=30)


def test_K_sizing_still_rejects_insufficient_casing():
    with pytest.raises(CombustorError, match='casing OD'):
        solve(casing_od_inch=5)


def test_separate_liner_thickness_reaches_geometry_stress_and_cad(dp2):
    thin = solve(liner_wall_thickness_mm=.6)
    assert thin['casing_id_mm'] == dp2['casing_id_mm']
    assert thin['shaft_tunnel_id_mm'] == dp2['shaft_tunnel_id_mm']
    assert thin['casing_od_required_mm'] < dp2['casing_od_required_mm']
    scale = thin['thermal_scale_ratio']
    for side in ('outer', 'inner'):
        cad = thin['cad_geometry'][side+'_liner']
        assert (cad['od']-cad['id'])/2 == pytest.approx(.6/scale)
        assert cad['wall_thickness'] == pytest.approx(.6/scale)
        radius = (thin[side+'_liner_od_mm']+thin[side+'_liner_id_mm'])/4000
        stress = thin['P2_Pa']*.04*radius/.0006/1e6
        assert thin['sigma_hoop_'+side+'_MPa'] == pytest.approx(stress)
    assert thin['cad_geometry']['casing']['wall_thickness'] == 1.5
    assert thin['main_hole_ligaments']['dil_in']['minimum_cold_mm'] == 1.5


def test_explicit_walls_work_without_legacy_input():
    inputs = dict(dp2_inputs)
    inputs.pop('wall_thickness_mm')
    assert MicroJetCombustor(inputs).run()['casing_id_mm'] == pytest.approx(149.4)


@pytest.mark.parametrize('key', ['casing_wall_thickness_mm', 'liner_wall_thickness_mm',
                               'shaft_tunnel_wall_thickness_mm'])
def test_invalid_wall_is_rejected(key):
    with pytest.raises(CombustorError, match='wall thickness'):
        solve(**{key: 0})


def test_independent_dilution_counts_preserve_air_demand(dp2):
    crowded = solve(dil_holes_per_vap_inner=4)
    assert not crowded['main_hole_ligaments']['dil_in']['ok']
    assert dp2['main_hole_ligaments_ok']
    assert dp2['dil_in_qty'] == 24 and dp2['dil_out_qty'] == 32
    assert dp2['dil_out_mm'] == crowded['dil_out_mm']
    assert dp2['dil_in_qty']*dp2['dil_in_mm']**2 == pytest.approx(
        crowded['dil_in_qty']*crowded['dil_in_mm']**2)
    assert dp2['cad_geometry']['main_holes']['dilution']['inner_qty'] == 24


@pytest.mark.parametrize('value', [0, -1, 2.5, float('nan')])
def test_invalid_dilution_count_is_rejected(value):
    with pytest.raises(CombustorError, match='positive integer'):
        solve(dil_holes_per_vap_inner=value)


def test_scoop_reports_approach_separately_from_pressure_driven_face_speed(dp2):
    assert dp2['vap_scoop_approach_m_s'] == dp2['v_outer_annulus']
    assert dp2['vap_scoop_vel_actual'] > dp2['vap_scoop_approach_m_s']
    assert dp2['vap_scoop_approach_below_target']
    assert dp2['vap_scoop_capture_area_ratio'] == pytest.approx(
        dp2['vap_scoop_vel_actual']/dp2['vap_scoop_approach_m_s'])
    changed = solve(vap_scoop_approach_target_m_s=10, vap_scoop_target_vel_m_s=40)
    assert not changed['vap_scoop_approach_below_target']
    assert changed['vap_scoop_face_vs_target'] < 1
    assert changed['vap_path_loss_Pa'] == dp2['vap_path_loss_Pa']


def test_report_exposes_spacing_and_model_limitations(dp2, capsys):
    print_report(dp2, dp2_inputs)
    report = capsys.readouterr().out
    assert 'Main-hole ligaments' in report
    assert 'scoop approach / face speed' in report
    assert 'primary estimate raw / capped' in report
    assert 'not acceptance criteria' in report


def test_off_design_reproduces_dp2_with_inlet_recovery(dp2):
    from RPM_Sweep_OffDesign import build_design_card, evaluate_off_design_point
    card = build_design_card(dict(dp2_inputs))
    rated = evaluate_off_design_point(card['off_design_anchors'], 1.63, .30, .72, 1150)
    assert rated['P2_Pa'] == pytest.approx(dp2['P2_Pa'], abs=.1)
    assert rated['mdot_fuel_kg_s'] == pytest.approx(dp2['mdot_fuel'], abs=1e-6)


def test_unused_legacy_settings_are_not_silently_accepted():
    with pytest.raises(CombustorError, match='Unused legacy'):
        solve(outer_loop_max_iter=10)
