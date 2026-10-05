"""Rotor FE benchmarks, assembly stack, combustor layout, CAD bundle, budget, controls, module modes."""
import json
import math
import os
import sys

import numpy as np
import pytest
from scipy.optimize import brentq

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import assembly, budget, cad_export, postprocess, controls_sim   # noqa: E402
from core.rotor_fe import RotorModel, ShaftSection, Disc, Support          # noqa: E402

E, RHO = 205e9, 7850.0


# ------------------------------------------------------------------- FE benchmarks (independent analytic)
def test_simply_supported_beam_matches_rayleigh_theory():
    d, L = 0.012, 0.4
    m = RotorModel([ShaftSection(0, L, d)], supports=[Support(0, 1e13), Support(L, 1e13)], max_element_length=0.02)
    f = [x['freq_rpm'] for x in m.modes(0, 6)][::2][:3]
    A, I = math.pi / 4 * d * d, math.pi / 64 * d ** 4
    for n, fe in zip((1, 2, 3), f):
        eb = (n * math.pi / L) ** 2 * math.sqrt(E * I / (RHO * A)) * 60 / (2 * math.pi)
        rayleigh = eb / math.sqrt(1 + (n * math.pi * d / 4 / L) ** 2)
        assert abs(fe / rayleigh - 1) < 2e-4


def test_jeffcott_rotor():
    d, L = 0.012, 0.4
    I = math.pi / 64 * d ** 4
    m = RotorModel([ShaftSection(0, L, d, rho=1e-3)], discs=[Disc(L / 2, 2.0, 0, 0)],
                   supports=[Support(0, 1e13), Support(L, 1e13)], max_element_length=0.02)
    exact = math.sqrt(48 * E * I / L ** 3 / 2.0) * 60 / (2 * math.pi)
    assert abs(m.modes(0, 2)[0]['freq_rpm'] / exact - 1) < 1e-5


def test_gyroscopic_overhung_disc_forward_and_backward_whirl():
    d, L, mm, Id, Ip = 0.012, 0.25, 1.0, 2e-3, 4e-3
    EI = E * math.pi / 64 * d ** 4
    K = np.linalg.inv(np.array([[L ** 3 / (3 * EI), L ** 2 / (2 * EI)], [L ** 2 / (2 * EI), L / EI]]))

    def analytic(Om, sign):
        f = lambda w: (K[0, 0] - mm * w * w) * (K[1, 1] - Id * w * w + sign * w * Om * Ip) - K[0, 1] ** 2
        ws = np.linspace(1, 40000, 200001)
        v = f(ws)
        return [brentq(f, ws[i], ws[i + 1]) * 60 / 2 / math.pi for i in np.where(np.sign(v[:-1]) != np.sign(v[1:]))[0]]
    rot = RotorModel([ShaftSection(-0.001, L + 0.001, d, rho=1e-4)], discs=[Disc(L, mm, Ip, Id)],
                     supports=[Support(-0.001, 1e14), Support(0.0, 1e14)], max_element_length=0.01)
    for N in (20000, 60000):
        Om = N * 2 * math.pi / 60
        fe = rot.modes(N, 8)
        fw = [x['freq_rpm'] for x in fe if x['whirl'] == 'forward'][:2]
        bw = [x['freq_rpm'] for x in fe if x['whirl'] == 'backward'][:2]
        for a, b in zip(fw, analytic(Om, +1)):
            assert abs(a / b - 1) < 5e-3
        for a, b in zip(bw, analytic(Om, -1)):
            assert abs(a / b - 1) < 5e-3


def test_rotor_model_rejects_bad_geometry():
    with pytest.raises(ValueError):
        RotorModel([ShaftSection(0, 0.1, 0.01), ShaftSection(0.12, 0.1, 0.01)])   # gap
    with pytest.raises(ValueError):
        RotorModel([ShaftSection(0, 0.1, 0.01)], discs=[Disc(0.2, 1, 0, 0)])     # off shaft


# ------------------------------------------------------------------- assembly stack
def stack_params():
    from core import cases, candidate
    case = cases.load_case('pd1-jm85')
    recs = cases.case_records(case)
    eng = candidate.engine_from_case(case, recs)
    # synthetic design point skeleton: only the fields candidate_seeds reads
    dp = dict(N_rpm=68000.0, T04_K=850.0, beta=0.6, thrust_N=40.0,
              stations=dict(P2_Pa=1e5, T3_K=334.0, P3_Pa=1.5e5, P31_Pa=1.47e5, P4_Pa=1.43e5, T5_K=810.0, P5_Pa=1.13e5,
                            P7_Pa=1.11e5),
              flows=dict(m_air_kg_s=0.2, m_comb_air_kg_s=0.196, m_fuel_kg_s=0.0027),
              losses=dict(combustor_frac=0.025), compressor=dict(w_J_kg=46000.0, PR=1.5, eta=0.76),
              turbine=dict(w_J_kg=45000.0, eta_tt=0.84, M1=0.4, T1_K=820, P1_Pa=130000),
              powers=dict(P_compressor_W=9200, P_bearings_W=100))
    seeds = candidate.candidate_seeds(case, recs, eng, dp)
    p = {k: v for k, (v, _) in seeds.items()}
    sp = {}
    for k in assembly.REQUIRED:
        src = assembly.STATE_MAP.get(k, k)
        if k in assembly.DERIVED:
            sp[k] = math.sqrt(4 * p['A8_fixed_m2'] / math.pi)
        elif src in p:
            sp[k] = p[src]
    sp.update(cw_D2_m=0.07613, cw_D1s_m=0.05704, cw_b2_m=0.00575, cw_mass_kg=0.075, tw_tip_d_m=0.085, tw_hub_d_m=0.055,
              tw_mass_kg=0.17, tw_Ip_kg_m2=8.4e-5, tw_tip_clearance_m=0.00035, liner_length_cold_m=0.087,
              outer_liner_od_cold_m=0.102, outer_liner_id_cold_m=0.099, inner_liner_od_cold_m=0.072,
              inner_liner_id_cold_m=0.069, diffuser_exit_d_m=0.126, diffuser_vane_height_m=0.006,
              tunnel_od_m=0.0508, brg_bore_m=0.010, rho_shaft_kg_m3=7850.0, E_shaft_Pa=205e9)
    return sp


def test_stack_is_ordered_and_checks_pass():
    st = assembly.build_stack(stack_params())
    x = st['x']
    order = ['shaft_front', 'cw_nose', 'cw_backface', 'fb_front', 'fb_rear', 'rb_front', 'rb_rear', 'boss_front',
             'rotor_le', 'rotor_te', 'boss_rear', 'shaft_rear']
    assert all(x[a] < x[b] for a, b in zip(order, order[1:]))
    assert x['dome'] < x['liner_end'] < x['ngv_le'] < x['ngv_te'] < x['rotor_le'] < x['nozzle_exit']
    assert [c.name for c in st['checks'] if c.status == 'fail'] == []


def test_stack_part_envelopes_are_well_formed():
    st = assembly.build_stack(stack_params())
    for q in st['parts']:
        assert q['x0'] <= q['x1'] and q['r_in'] <= q['r_out'], q['id']     # e.g. a cone stored as a box


def test_tunnel_carrier_joint_uses_the_stack_envelopes():
    st = assembly.build_stack(stack_params())
    c = next(c for c in st['checks'] if c.name == 'tunnel / rear carrier slip joint')
    bc2 = next(q for q in st['parts'] if q['id'] == 'BC-02')
    tu = next(q for q in st['parts'] if q['id'] == 'TU-01')
    if bc2['r_out'] > tu['r_in'] and min(bc2['x1'], tu['x1']) > max(bc2['x0'], tu['x0']):
        assert c.status == 'unknown' and c.value > 0           # envelopes interfere: not a pass


def test_rotating_shaft_end_inside_tailcone_envelope_is_not_passed():
    st = assembly.build_stack(stack_params())
    c = next(c for c in st['checks'] if c.name.startswith('shaft end and turbine nut vs tailcone'))
    protrusion = st['x']['shaft_rear'] - st['x']['nozzle_entry']
    assert c.value == pytest.approx(protrusion)
    assert c.status == ('unknown' if protrusion > 0 else 'pass')


def test_stack_parameter_change_propagates():
    p = stack_params()
    a = assembly.build_stack(p)
    b = assembly.build_stack(dict(p, liner_length_cold_m=p['liner_length_cold_m'] + 0.010))
    assert math.isclose(b['x']['rotor_le'] - a['x']['rotor_le'], 0.010, abs_tol=1e-12)
    assert math.isclose(b['bearing_span_m'] - a['bearing_span_m'], 0.010, abs_tol=1e-12)
    assert b['rotor_mass_kg'] > a['rotor_mass_kg']        # longer shaft body


def test_stack_rejects_missing_input_and_flags_incompatible_bore():
    p = stack_params()
    with pytest.raises(KeyError):
        assembly.build_stack({k: v for k, v in p.items() if k != 'tw_rim_width_m'})
    st = assembly.build_stack(dict(p, shaft_journal_d_m=0.008, shaft_body_d_m=0.011))
    failed = {c.name for c in st['checks'] if c.status == 'fail'}
    assert 'journal nominal matches selected bearing bore' in failed
    assert 'shaft body shoulder >= bearing abutment min' in failed


def test_nominal_wheel_interference_is_not_a_validated_fit():
    st = assembly.build_stack(stack_params())
    fits = [c for c in st['checks'] if 'bore /' in c.name]
    assert len(fits) == 2
    assert all(c.status == 'unknown' and c.value < 0 for c in fits)


def test_fit_checks_follow_the_purchased_wheel_bores():
    p = stack_params()
    assert p['tw_bore_d_m'] == pytest.approx(0.00999) and p['cw_bore_d_m'] == pytest.approx(0.00599)
    st = assembly.build_stack(dict(p, tw_bore_d_m=0.00799))        # e.g. a TW70-size bore on the 10 mm seat
    fit = next(c for c in st['checks'] if c.name == 'turbine bore / journal assembly fit')
    assert fit.status == 'unknown' and fit.value == pytest.approx(-0.00201)


def test_ngv_blind_hub_pocket_is_not_reported_as_finished_through_bore():
    st = assembly.build_stack(stack_params())
    check = next(c for c in st['checks'] if c.name == 'NGV hub through-bore for rear carrier')
    assert check.status == 'unknown'
    assert 'central web' in check.reason


def test_shaft_expansion_opens_axial_gap_when_stationary_ngv_does_not_expand():
    st = assembly.build_stack(stack_params())
    growth = assembly.axial_growth(st, 393, 293, 293, 12e-6, 16e-6, 16e-6)
    assert growth['ngv_rotor_gap_change_m'] > 0
    assert growth['ngv_rotor_gap_change_m'] == pytest.approx(growth['rotor_aft_growth_m'])
    opposite = assembly.axial_growth(st, 293, 293, 393, 12e-6, 16e-6, 16e-6)
    assert opposite['ngv_rotor_gap_change_m'] < 0


def test_self_sustain_failure_cuts_fuel_in_same_step():
    c = controls_sim.Controller()
    c.state, c.t_state, c.fuel = 'SELF_SUSTAIN_CHECK', 0, 0.35
    sensors = {'N': controls_sim.Sample(20000, 3), 'EGT': controls_sim.Sample(800, 3)}
    cmd = c.step(3, 0.02, sensors)
    assert c.fault == 'NO_SELF_SUSTAIN'
    assert not cmd['VALVE_OPEN'] and cmd['FUEL_CMD'] == 0


def test_controller_rejects_future_sensor_and_estop_blocks_start():
    c = controls_sim.Controller()
    cmd = c.step(0, 0.02, {}, start=True, estop=True)
    assert c.state == 'SAFE_OFF' and cmd['STARTER_CMD'] == 0
    c.state = 'RUN'
    sensors = {k: controls_sim.Sample(v, 11) for k, v in {'N': 50000, 'EGT': 800, 'P03': 30000, 'PF': 50000}.items()}
    cmd = c.step(10, 0.02, sensors)
    assert c.fault == 'N_FUTURE_TIMESTAMP' and not cmd['VALVE_OPEN']


def test_controller_releases_starter_in_transition_step():
    c = controls_sim.Controller()
    c.state = 'ASSIST'
    sensors = {'N': controls_sim.Sample(45000, 1), 'EGT': controls_sim.Sample(800, 1)}
    cmd = c.step(1, 0.02, sensors)
    assert c.state == 'SELF_SUSTAIN_CHECK' and cmd['STARTER_CMD'] == 0


def test_tip_clearance_and_buckling_formulas():
    p = stack_params()
    cold = assembly.tip_clearance_hot(p, 293.0, 293.0, 0.0, 14e-6, 16e-6, 165e9)
    assert math.isclose(cold['hot_m'], p['tw_tip_clearance_m'], rel_tol=1e-12)
    hot = assembly.tip_clearance_hot(p, 950.0, 293.0, 68000.0, 14e-6, 16e-6, 165e9)
    assert hot['hot_m'] < 0     # hot wheel in a cold shroud closes the gap: a visible negative, not hidden
    b = assembly.outer_liner_buckling(0.1, 0.0015, 0.09, 175e9)
    assert 1e6 < b['p_cr_elastic_Pa'] < 1e8


# ------------------------------------------------------------------- combustor layout
def _fake_comb(dil_out=32, d_dil=5.0):
    sc = 1.01
    return dict(thermal_scale_ratio=sc, L_primary_mm=26 * sc, L_secondary_mm=26 * sc, L_dilution_mm=35 * sc, vap_n=8,
                pri_out_mm=3.5 * sc, pri_in_mm=3.0 * sc, sec_out_mm=4.8 * sc, sec_in_mm=4.2 * sc,
                dil_out_mm=d_dil * sc, dil_in_mm=5.5 * sc, pri_out_qty=16, pri_in_qty=16, sec_out_qty=16, sec_in_qty=16,
                dil_out_qty=dil_out, dil_in_qty=24, film_holes_per_row_outer=40, film_holes_per_row_inner=30,
                film_hole_dia_outer_mm=1.2 * sc, film_hole_dia_inner_mm=1.2 * sc, film_n_rows=4,
                chamber_length_cold_mm=87.0, outer_liner_id_cold_mm=99.0, inner_liner_od_cold_mm=72.0,
                liner_wall_thickness_mm=1.524 * sc, vap_od_mm=6.2, vap_id_mm=5.0, vap_crimp_dia_mm=4.5,
                vap_scoop_dia_mm=3.0, D_mean_comb_mm=86.0 * sc, vap_bend_radius_mm=9.3, combustion_gap_mm=13.0 * sc,
                chamber_length_mm=87.0 * sc)


def test_layout_preserves_inner_outer_counts_and_film_area():
    lay = postprocess.combustor_layout(_fake_comb())
    rows = {(r['row'], r['side']): r for r in lay['rows']}
    assert rows[('dilution', 'outer')]['count'] == 32 and rows[('dilution', 'inner')]['count'] == 24
    assert len(rows[('dilution', 'outer')]['angles_deg']) == 32
    for side, fa in lay['film_adjustment'].items():          # omitted seam holes keep the film area
        a0 = fa['holes_per_row_model'] * fa['dia_model_m'] ** 2
        a1 = fa['holes_per_row_layout'] * fa['dia_layout_m'] ** 2
        assert math.isclose(a0, a1, rel_tol=1e-9)


def test_seam_check_passes_for_sparse_pattern_and_fails_for_dense():
    sparse = _fake_comb(dil_out=24, d_dil=4.5)
    sparse.update(dil_in_qty=16, dil_in_mm=4.5)
    seam = [c for c in postprocess.combustor_layout(sparse)['checks'] if 'seam' in c.name]
    assert seam and all(c.status == 'pass' for c in seam)
    dense = [c for c in postprocess.combustor_layout(_fake_comb())['checks'] if 'seam' in c.name]
    assert any(c.status == 'fail' for c in dense)       # 32 x 5 mm holes leave no 6 mm seam band


def test_impossible_hole_pattern_fails_visibly():
    lay = postprocess.combustor_layout(_fake_comb(dil_out=64, d_dil=6.0))
    lig = [c for c in lay['checks'] if c.name.startswith('outer liner minimum ligament')][0]
    assert lig.status == 'fail'


# ------------------------------------------------------------------- CAD bundle
def test_cad_bundle_units_and_read_back(tmp_path):
    B = cad_export.Bundle('f' * 64, 'demo')
    B.add('L1', 'P', 'length', 0.0125, 'design', 's')
    B.add('A1', 'P', 'angle', 37.5, 'design', 's')
    B.add('N1', 'P', 'count', 19, 'design', 's')
    B.add('M1', 'P', 'mass', 0.17, 'calculated', 's')
    B.add('U1', 'P', 'length', None, 'unresolved', 'n/a')
    with pytest.raises(cad_export.BundleError):
        B.add('L1', 'P', 'length', 0.001, 'design', 's')          # duplicate
    with pytest.raises(cad_export.BundleError):
        B.add('C2', 'P', 'count', 2.5, 'design', 's')             # non-integer count
    with pytest.raises(cad_export.BundleError):
        B.add('Z', 'P', 'length', None, 'design', 's')            # missing value not marked unresolved
    path = tmp_path / 'b.json'
    path.write_text(json.dumps(B.to_json({}, [])))
    b = cad_export.read_bundle(path, expected_fingerprint='f' * 64)
    vals = {p['name']: p for p in b['parameters']}
    assert vals['L1']['value'] == 12.5 and vals['L1']['unit'] == 'mm'
    assert vals['A1']['value'] == 37.5 and vals['A1']['unit'] == 'deg'      # angles are not scaled
    assert vals['N1']['value'] == 19 and vals['M1']['unit'] == 'kg'
    with pytest.raises(cad_export.BundleError):
        cad_export.read_bundle(path, expected_fingerprint='e' * 64)          # stale
    K = cad_export.Bundle('f' * 64, 'demo')
    K.add('K1', 'P', 'stiffness', 2.0e6, 'assumption', 's')                  # N/m in, N/um out - not a ratio
    assert K.params[0]['value'] == 2.0 and K.params[0]['unit'] == 'N/um'
    bad = json.loads(path.read_text())
    bad['parameters'][1]['unit'] = 'mm'
    path.write_text(json.dumps(bad))
    with pytest.raises(cad_export.BundleError):
        cad_export.read_bundle(path)


# ------------------------------------------------------------------- budget
def test_budget_extraction_reproduces_workbook_total():
    wb = budget.reproduce_workbook()
    assert wb['direct'] == 5402 and wb['freight'] == 200 and wb['tax'] == 450 and wb['reserve'] == 550
    assert wb['total'] == 6602


def test_candidate_budget_lines_are_traceable_and_complete():
    rows, adj = budget.candidate_lines()
    ids = [r['row_id'] for r in rows]
    assert len(ids) == len(set(ids))
    for r in rows:
        assert r['nominal'] is not None and r['adverse'] >= r['nominal'] - 1e-9 or r['row_id'] in ('R02', 'R03')
    sc = budget.scenarios(rows, adj)
    assert sc['adverse']['total'] >= sc['nominal']['total'] >= sc['tax_exempt_only']['total']
    assert sc['all_conditional_options']['total'] < sc['nominal']['total']
    assert all(not o['confirmed'] for o in sc['options'])     # savings stay conditional
    # a named route is recomputed with the workbook formulas, not by subtracting option amounts
    route = sc['route SV1+SV5+SV4']
    assert sc['all_conditional_options']['total'] <= route['total'] < sc['nominal']['total']
    assert route['tax'] == 0 and route['reserve'] == budget.ceil_to(route['direct'] * adj['rates']['reserve_rate'],
                                                                     adj['rates']['round_to_usd'])
    with pytest.raises(ValueError, match='unknown savings options'):
        budget.apply_options(rows, adj, ['SV9'])


# ------------------------------------------------------------------- controls (synthetic)
def _states(trace):
    seen = []
    for t, s, *_ in trace:
        if not seen or seen[-1] != s:
            seen.append(s)
    return seen


def test_synthetic_normal_start_reaches_run_with_starter_released():
    tr = controls_sim.simulate(controls_sim.SyntheticPlant(), controls_sim.Controller(), t_end=20)
    s = _states(tr)
    assert s[-1] == 'RUN' and 'SELF_SUSTAIN_CHECK' in s
    assert tr[-1][4]['STARTER_CMD'] == 0.0 and tr[-1][4]['VALVE_OPEN']


def test_failure_to_light_shuts_fuel_off():
    c = controls_sim.Controller()
    tr = controls_sim.simulate(controls_sim.SyntheticPlant(lights=False), c, t_end=20)
    assert c.fault == 'FAILURE_TO_LIGHT'
    assert tr[-1][4]['FUEL_CMD'] == 0.0 and not tr[-1][4]['VALVE_OPEN'] and not tr[-1][4]['IGNITER_ON']


def test_stale_and_invalid_sensors_trigger_shutdown():
    def stale_egt(t, s):
        if t > 8:
            s['EGT'] = controls_sim.Sample(s['EGT'].value, 8.0)
        return s
    c = controls_sim.Controller()
    controls_sim.simulate(controls_sim.SyntheticPlant(), c, t_end=15, faults={'stale': stale_egt})
    assert c.fault == 'EGT_STALE'

    def bad_n(t, s):
        if t > 8:
            s['N'] = controls_sim.Sample(float('nan'), t)
        return s
    c = controls_sim.Controller()
    controls_sim.simulate(controls_sim.SyntheticPlant(), c, t_end=12, faults={'nan': bad_n})
    assert c.fault == 'N_INVALID'


def test_overspeed_and_operator_stop():
    def overspeed(t, s):
        if t > 10:
            s['N'] = controls_sim.Sample(80000.0, t)
        return s
    c = controls_sim.Controller()
    controls_sim.simulate(controls_sim.SyntheticPlant(), c, t_end=12, faults={'os': overspeed})
    assert c.fault == 'OVERSPEED'
    c = controls_sim.Controller()
    tr = controls_sim.simulate(controls_sim.SyntheticPlant(), c, t_end=14, stop_at=10.0)
    assert 'SHUTDOWN' in _states(tr) and tr[-1][4]['FUEL_CMD'] == 0.0 and c.fault is None


def test_commands_saturate_and_hardware_is_disabled():
    c = controls_sim.Controller()
    cmds = c._cmd(0.0, 5.0, True, False, 3.0, 100.0)
    assert 0.0 <= cmds['FUEL_CMD'] <= 1.0 and cmds['STARTER_CMD'] == 1.0
    with pytest.raises(controls_sim.HardwareDisabled):
        c.out.enable()
    assert c.out.enabled is False


# ------------------------------------------------------------------- module modes
def _baseline_state():
    import run as R
    _, s, _, _ = R.solve()
    return s


def test_m01_imported_point_rejects_stale_values():
    from modules.m01_cycle import m01_cycle
    from core.module import ModuleError
    from core import gas
    s = _baseline_state()
    s = dict(s)
    s.update(cycle_imported_point_flag=1.0, op_mdot_air_kg_s=0.2, op_mdot_comb_kg_s=0.196, op_P02_Pa=1.0e5,
             op_T03_K=334.0, op_P03_Pa=1.5e5, op_P031_Pa=1.47e5, op_P04_Pa=1.43e5, op_T05_K=810.0, op_P05_Pa=1.13e5,
             op_F_gross_N=40.0)
    s['op_w_comp_J_kg'] = gas.h_air(334.0) - gas.h_air(s['T00_K'])
    s['op_w_turb_J_kg'] = 45000.0
    far = gas.far_for_T4(334.0, s['T04_K'], s['eta_b_frac'], s['LHV_fuel_J_kg'])
    s['op_mdot_fuel_kg_s'] = 0.196 * far
    out = m01_cycle.spec.run(s)
    assert out['mdot_comb_kg_s'] == 0.196 and out['P031_Pa'] == 1.47e5 and out['w_turb_J_kg'] == 45000.0
    s['op_w_comp_J_kg'] *= 1.01                       # stale/inconsistent compressor work
    with pytest.raises(gas.GasError):
        m01_cycle.spec.run(s)
    s2 = dict(s, cycle_prescribed_flow_flag=1.0)
    with pytest.raises(gas.GasError):
        m01_cycle.spec.run(s2)                         # two modes at once
    del s['op_T05_K']
    s['op_w_comp_J_kg'] /= 1.01
    with pytest.raises(ModuleError):
        m01_cycle.spec.run(s)                          # missing imported value fails loudly


def test_m12_fixed_ngv_reports_the_rated_point_when_imported():
    # With an imported fixed-geometry point the rating already includes NGV loss and leak mixing;
    # M12 must report that station, not re-solve an isentropic throat at combustor T04.
    from modules.m12_ngv import m12_ngv
    s = dict(_baseline_state())
    s.update(ngv_fixed_flag=1.0, cycle_imported_point_flag=1.0, A_throat_ngv_fixed_m2=1.49e-3,
             alpha_ngv_exit_fixed_deg=65.0, n_vanes_ngv_fixed_count=20.0, mdot_fuel_kg_s=0.0026,
             op_ngv_M_ratio=0.46, op_ngv_T_K=806.0, op_ngv_P_Pa=121800.0)
    out = m12_ngv.spec.run(s)
    assert (out['M_ngv_exit_ratio'], out['T_ngv_exit_K'], out['P_ngv_exit_Pa']) == (0.46, 806.0, 121800.0)
    assert out['ngv_choked_flag'] == 0.0 and out['A_throat_ngv_m2'] == 1.49e-3


def test_m10_fixed_wheel_keeps_purchased_geometry():
    from modules.m10_compressor import m10_compressor
    s = dict(_baseline_state())
    # baseline PR 3.2 work at 66 krpm is impossible for a 76 mm wheel (raises, correctly); use a PD-1-like point
    s.update(mdot_kg_s=0.2, N_rpm=68000.0, T03_K=334.0, P03_Pa=150000.0, P02_Pa=100400.0)
    s.update(compressor_fixed_wheel_flag=1.0, D2_fixed_m=0.07613, D1s_fixed_m=0.05704, D1h_fixed_m=0.019,
             b2_fixed_m=0.00575, m_imp_fixed_kg=0.075, Z_imp_fixed_count=11.0)
    out = m10_compressor.spec.run(s)
    assert out['D2_m'] == 0.07613 and out['D1s_m'] == 0.05704 and out['b2_m'] == 0.00575
    assert out['work_coeff_c_ratio'] > 0
    # blade (Euler) work is the air's enthalpy rise divided by the power input factor
    from core import gas
    U2 = gas.rpm_to_rad_s(68000.0) * 0.07613 / 2
    blade = (gas.h_air(334.0) - gas.h_air(s['T02_K'])) / s['power_input_factor_ratio']
    assert out['Ctheta2_m_s'] == pytest.approx(blade / U2, rel=1e-9)
    assert out['work_coeff_c_ratio'] == pytest.approx(blade / U2 ** 2, rel=1e-9)
