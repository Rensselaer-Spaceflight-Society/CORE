"""Fixed-geometry candidate: engine definition, matched design point, pipeline seeds.

This module turns a case file plus its component records into
  1. an EngineDefinition for core/engine_match.py (fixed purchased/designed geometry),
  2. the matched design point (speed = case design speed, zero starter torque),
     with the combustor loss anchor made consistent with that point,
  3. the seed set for the module pipeline, every derived value tagged with its source,
  4. the solved module state.
Nothing here resizes purchased geometry or tunes a result toward a target.
"""
from __future__ import annotations

import math

from core import registry, solver
from core.compressor_map import CompressorMap, MapOffsets
from core.engine_match import (EngineDefinition, MechanicalLosses, Bearing, match_speed,
                               solve_from_guess, verify_point, operating_line)
from core.records import ROOT, MissingInput
from core.turbine_rating import stage_from_records

MATERIAL_CODE = {'316SS': 0, '304SS': 1, 'IN625': 2, 'IN718': 3}


class CandidateError(Exception):
    pass


def mechanical_from_records(recs, scale=1.0):
    b = recs['bearings']
    bore, od = b.si('bore') * 1e3, b.si('outer_diameter') * 1e3
    f0 = b.param('friction_f0')['value']
    nu = b.param('lubricant_viscosity')['value']
    pre = b.si('preload_spring_force')
    brgs = [Bearing('front', bore, od, f0, nu, pre), Bearing('rear', bore, od, f0, nu, pre)]
    return MechanicalLosses(bearings=brgs, windage_radius_m=recs['turbine'].si('hub_diameter') / 2,
                            scale=scale)


def engine_from_case(case, recs, stage_overrides=None, map_offsets=None, FF_design=None, **overrides):
    e = dict(case.get('engine') or {})
    cmap = CompressorMap(ROOT / case['components']['compressor_map'], map_offsets or MapOffsets())
    so = dict(case.get('turbine_overrides') or {})
    so.update(stage_overrides or {})
    stage = stage_from_records(recs['turbine'], recs['ngv'], so)
    D8 = recs['assembly'].si('nozzle_exit_d')
    kw = dict(
        case_id=case['case_id'], stage=stage, cmap=cmap, A8_m2=math.pi / 4 * D8 * D8,
        FF_design=FF_design if FF_design is not None else 2.7e-5,
        comb_loss_design=e.get('comb_loss_design', 0.04), duct_loss_design=e.get('duct_loss_design', 0.015),
        inlet_loss_ref=e.get('inlet_loss_ref', 0.01), inlet_Q_ref_kg_s=e.get('inlet_Q_ref_kg_s', 0.2),
        leak_frac=e.get('leak_frac', 0.02), jetpipe_loss=e.get('jetpipe_loss', 0.01),
        nozzle_Cd=e.get('nozzle_Cd', 0.97), nozzle_Cv=e.get('nozzle_Cv', 0.97), eta_b=e.get('eta_b', 0.96),
        LHV_J_kg=float(e.get('LHV_J_kg', 43e6)), T04_screen_max_K=e.get('T04_screen_max_K', 1150.0),
        mech=mechanical_from_records(recs))
    kw['mech'].windage_Cm = e.get('windage_Cm', 0.004)
    kw.update(overrides)
    return EngineDefinition(**kw)


def anchored_design_point(eng, N_design, T0, P0, tol=1e-7, max_iter=30):
    """Match at the design speed and make the combustor-loss anchor self-consistent.

    The prescribed combustor loss is defined AT the design point: the loss-scaling
    anchor FF_design must equal the combustor-inlet flow function of the matched
    design point. Iterate (match -> FF -> update) to a fixed point. A global scan
    starts the process and reports every branch it finds.
    """
    scan = match_speed(eng, N_design, T0, P0, n_scan=11)
    conv = [b for b in scan['branches'] if b.get('converged')]
    if not conv:
        raise CandidateError(f'no steady match at design speed {N_design:.0f} rpm: {scan.get("reason")} '
                             f'{scan.get("failure_reasons")}')
    pt = conv[0]
    history = []
    for _ in range(max_iter):
        ff = pt['losses']['FF31']
        ff3 = pt['losses']['FF3']
        history.append(dict(FF_design=eng.FF_design, FF31=ff, FF_duct_design=eng.FF_duct_design,
                            FF3=ff3, T04_K=pt['T04_K'], beta=pt['beta']))
        if (eng.FF_duct_design is not None and abs(ff / eng.FF_design - 1) < tol
                and abs(ff3 / eng.FF_duct_design - 1) < tol):
            break
        eng = eng.with_(FF_design=ff, FF_duct_design=ff3)
        nxt = solve_from_guess(eng, N_design, pt['beta'], pt['T04_K'], T0, P0)
        if nxt is None:
            r = match_speed(eng, N_design, T0, P0, n_scan=11)
            c = [b for b in r['branches'] if b.get('converged')]
            if not c:
                raise CandidateError('design point lost while anchoring the combustor loss')
            nxt = c[0]
        pt = nxt
    else:
        raise CandidateError('combustor loss anchor did not converge')
    checks = verify_point(eng, pt, T0, P0, starts=((0.3, 800.0), (0.8, 1200.0), (pt['beta'], pt['T04_K'] + 150)))
    return eng, pt, dict(global_scan_branches=len(conv), multiple_branches=len(conv) > 1,
                         anchor_history=history, multi_start=checks)


def rating_sweep(eng, speeds, design_point, T0, P0):
    """Operating line through the rating speeds by continuation from the design point."""
    N_d = design_point['N_rpm']
    lower = sorted([N for N in speeds if N < N_d], reverse=True)
    upper = sorted([N for N in speeds if N > N_d])
    down = operating_line(eng, lower, T0, P0, anchor=design_point)
    up = operating_line(eng, upper, T0, P0, anchor=design_point)
    pts = list(reversed(down)) + [dict(design_point, method='design point')] + up
    return pts


# ---------------------------------------------------------------------------- seeds
def _mm(rec, name):
    return rec.si(name)


def _lab(rec, name):
    """Provenance label carrying the record's own basis (supplied / design / assumption ...)."""
    return f'record {rec.id}.{name} ({rec.param(name)["basis"]})'


def candidate_seeds(case, recs, eng, dp):
    """Derived seeds with provenance for the candidate pipeline (value, source)."""
    c, t, n, b, a = recs['compressor'], recs['turbine'], recs['ngv'], recs['bearings'], recs['assembly']
    st, fl = dp['stations'], dp['flows']
    comb = case.get('combustor') or {}
    diff = case.get('diffuser') or {}
    rs = case.get('rotor_support') or {}
    amb = case.get('ambient') or {}
    A_ngv, alpha1 = eng.stage.ngv_throat()
    k_b = b.si('radial_stiffness_preloaded')
    seeds = {}

    def put(k, v, src):
        seeds[k] = (v, src)

    src_mp = f'engine_match design point {dp["N_rpm"]:.0f} rpm (core/engine_match.py)'
    put('cycle_imported_point_flag', 1.0, 'mode: fixed_geometry_rating')
    for f in ('compressor_fixed_wheel_flag', 'turbine_fixed_wheel_flag', 'ngv_fixed_flag',
              'nozzle_fixed_flag', 'assembly_mode_flag'):
        put(f, 1.0, 'mode: fixed_geometry_rating')
    put('T00_K', amb.get('T0_K', 288.15), 'case ambient'); put('P00_Pa', amb.get('P0_Pa', 101325.0), 'case ambient')
    put('N_rpm', dp['N_rpm'], 'case operating.design_speed_rpm')
    put('PR_c_ratio', dp['compressor']['PR'], src_mp)
    put('eta_c_isen', dp['compressor']['eta'], src_mp)
    put('eta_t_isen', dp['turbine']['eta_tt'], src_mp)
    put('T04_K', dp['T04_K'], src_mp)
    put('eta_b_frac', eng.eta_b, 'case engine.eta_b'); put('LHV_fuel_J_kg', eng.LHV_J_kg, 'case engine.LHV_J_kg')
    put('dP34_frac', dp['losses']['combustor_frac'], 'case engine.comb_loss_design at the anchored design point')
    put('Cv_nozzle_ratio', eng.nozzle_Cv, 'case engine.nozzle_Cv')
    put('R_gas_J_kgK', eng.R, 'engine_match gas constant (single value for match and modules)')
    put('op_mdot_air_kg_s', fl['m_air_kg_s'], src_mp); put('op_mdot_comb_kg_s', fl['m_comb_air_kg_s'], src_mp)
    put('op_mdot_fuel_kg_s', fl['m_fuel_kg_s'], src_mp); put('op_P02_Pa', st['P2_Pa'], src_mp)
    put('op_T03_K', st['T3_K'], src_mp); put('op_P03_Pa', st['P3_Pa'], src_mp); put('op_P031_Pa', st['P31_Pa'], src_mp)
    put('op_P04_Pa', st['P4_Pa'], src_mp); put('op_T05_K', st['T5_K'], src_mp); put('op_P05_Pa', st['P5_Pa'], src_mp)
    put('op_P07_Pa', st['P7_Pa'], src_mp)
    put('op_w_comp_J_kg', dp['compressor']['w_J_kg'], src_mp); put('op_w_turb_J_kg', dp['turbine']['w_J_kg'], src_mp)
    put('op_F_gross_N', dp['thrust_N'], src_mp)
    put('op_ngv_M_ratio', dp['turbine']['M1'], src_mp)
    put('op_ngv_T_K', dp['turbine']['T1_K'], src_mp)
    put('op_ngv_P_Pa', dp['turbine']['P1_Pa'], src_mp)
    put('op_shaft_comp_power_W', dp['powers']['P_compressor_W'] + 0.5 * dp['powers']['P_bearings_W'],
        'rated compressor + front bearing power; same torque basis as shaft stress postprocessing')
    # purchased compressor wheel
    put('D2_fixed_m', _mm(c, 'exducer_diameter'), 'record compressor_wheel.exducer_diameter (supplied)')
    put('D1s_fixed_m', _mm(c, 'inducer_diameter'), 'record compressor_wheel.inducer_diameter (supplied)')
    put('D1h_fixed_m', _mm(c, 'inducer_hub_diameter_assumed'), 'record compressor_wheel.inducer_hub_diameter_assumed (ASSUMPTION)')
    put('b2_fixed_m', _mm(c, 'exducer_tip_height'), 'record compressor_wheel.exducer_tip_height (supplied)')
    put('m_imp_fixed_kg', c.si('mass_estimate'), 'record compressor_wheel.mass_estimate (ASSUMPTION)')
    put('Z_imp_fixed_count', c.param('full_blade_count')['value'], 'record compressor_wheel.full_blade_count (supplied)')
    # purchased turbine and NGV
    put('D_turb_tip_fixed_m', _mm(t, 'tip_diameter'), 'record turbine_rotor.tip_diameter (supplied)')
    put('D_turb_hub_fixed_m', _mm(t, 'hub_diameter'), 'record turbine_rotor.hub_diameter (supplied)')
    put('n_blades_turb_fixed_count', t.param('blade_count_estimate')['value'], 'record turbine_rotor.blade_count_estimate (ASSUMPTION)')
    put('m_turb_fixed_kg', t.si('mass_estimate'), 'record turbine_rotor.mass_estimate (calculated envelope)')
    put('I_turb_fixed_kg_m2', t.si('polar_inertia_estimate'), 'record turbine_rotor.polar_inertia_estimate (calculated envelope)')
    put('m_blade_fixed_kg', t.si('blade_mass_assumed'), 'record turbine_rotor.blade_mass_assumed (ASSUMPTION)')
    put('A_blade_root_fixed_m2', t.si('blade_root_area_assumed'), 'record turbine_rotor.blade_root_area_assumed (ASSUMPTION)')
    put('r_blade_cg_fixed_m', t.si('blade_cg_radius_assumed'), 'record turbine_rotor.blade_cg_radius_assumed (ASSUMPTION)')
    put('t_tip_clear_fixed_m', t.si('tip_clearance_design'), _lab(t, 'tip_clearance_design'))
    put('A_throat_ngv_fixed_m2', A_ngv, 'NGV exit annulus x cos(exit angle) (ASSUMED angle and assumed vane tip '
                                        'diameter; throat unmeasured)' if not n.has_value('throat_area')
        else _lab(n, 'throat_area'))
    put('alpha_ngv_exit_fixed_deg', alpha1, 'record ngv_ring.exit_flow_angle (ASSUMPTION)')
    put('n_vanes_ngv_fixed_count', n.param('vane_count_estimate')['value'], 'record ngv_ring.vane_count_estimate (ASSUMPTION)')
    # nozzle
    put('A8_fixed_m2', eng.A8_m2, _lab(a, 'nozzle_exit_d'))
    put('nozzle_Cd_ratio', eng.nozzle_Cd, 'case engine.nozzle_Cd')
    # combustor and casing stock
    put('casing_od_m', a.si('casing_od'), _lab(a, 'casing_od'))
    put('casing_wall_m', a.si('casing_wall_stock'), _lab(a, 'casing_wall_stock') + ': 0.060 in sheet')
    put('liner_wall_m', a.si('liner_wall_stock'), _lab(a, 'liner_wall_stock') + ': cold stock')
    put('tunnel_wall_m', a.si('tunnel_wall_stock'), _lab(a, 'tunnel_wall_stock') + ': 0.065 in wall')
    put('D_shaft_tunnel_m', a.si('tunnel_od_stock'), _lab(a, 'tunnel_od_stock') + ': 2 in tube')
    put('liner_material_code_count', MATERIAL_CODE[comb.get('liner_material', '316SS')], 'case combustor.liner_material')
    put('alpha_liner_per_K', comb.get('liner_alpha_per_K', 16e-6), 'case combustor.liner_alpha_per_K')
    put('tau_min_s', comb.get('tau_min_s', 0.002), 'case combustor.tau_min_s')
    put('inner_hole_K_target_ratio', comb.get('target_inner_hole_K', 6.0), 'case combustor.target_inner_hole_K')
    put('dil_holes_per_vap_inner_count', comb.get('dil_holes_per_vap_inner', 3), 'case combustor')
    put('dil_holes_per_vap_outer_count', comb.get('dil_holes_per_vap_outer', 4), 'case combustor')
    put('sec_holes_per_vap_count', comb.get('sec_holes_per_vap', 2), 'case combustor')
    # diffuser
    D2 = _mm(c, 'exducer_diameter')
    put('diff_vaneless_ratio', diff.get('vaneless_ratio', 1.08), 'case diffuser.vaneless_ratio')
    put('diff_radius_ratio', diff.get('exit_diameter_m', 1.45 * D2) / D2, 'case diffuser.exit_diameter_m / D2')
    put('diff_vanes_design_count', diff.get('vane_count', 17), 'case diffuser.vane_count')
    put('diff_width_ratio', diff.get('channel_width_m', _mm(c, 'exducer_tip_height')) / _mm(c, 'exducer_tip_height'),
        'case diffuser.channel_width_m / b2')
    put('diff_throat_mach_ratio', diff.get('throat_mach_target', 0.7), 'case diffuser.throat_mach_target')
    put('diff_cp_assumed_ratio', diff.get('cp_vaned_assumed', 0.6), 'case diffuser.cp_vaned_assumed')
    put('diff_turn_K_ratio', diff.get('turn_K', 1.0), 'case diffuser.turn_K')
    put('diff_exit_width_growth_ratio', diff.get('exit_width_growth', 1.0), 'case diffuser.exit_width_growth')
    # bearings / supports
    put('d_bearing_bore_m', b.si('bore'), 'record bearings.bore (supplied)')
    put('brg_od_m', b.si('outer_diameter'), 'record bearings.outer_diameter (supplied)')
    put('brg_width_m', b.si('width'), 'record bearings.width (supplied)')
    k_sup = rs.get('k_support_N_m', 1.0 / (1.0 / k_b + 1.0 / b.si('housing_stiffness')))
    put('k_support_N_m', k_sup, f'case rotor_support ({rs.get("mount", "rigid")}) - ASSUMPTION')
    put('c_support_N_s_m', rs.get('c_support_N_s_m', b.si('support_damping')), 'case rotor_support - ASSUMPTION')
    put('bearing_stiffness_N_m', k_sup, 'same as k_support_N_m (M31 reporting)')
    # stack (compressor/turbine/NGV/assembly records)
    stack = {
        'cw_length_m': (c, 'backface_to_nose_length_envelope'), 'cw_super_back_m': (c, 'super_back_height'),
        'cw_cg_from_backface_m': (c, 'cg_from_backface_estimate'), 'cw_Ip_kg_m2': (c, 'polar_inertia_estimate'),
        'cw_Id_kg_m2': (c, 'diametral_inertia_estimate'), 'cw_D2_ext_m': (c, 'exducer_extended_tip_diameter'),
        'ngv_axial_chord_m': (n, 'vane_axial_chord'), 'ngv_hub_d_m': (n, 'vane_hub_diameter'),
        'ngv_tip_d_m': (n, 'vane_tip_diameter'), 'ngv_flange_od_m': (n, 'flange_od'),
        'ngv_overall_height_m': (n, 'overall_height_blank'), 'ngv_vane_ring_height_m': (n, 'vane_ring_height_blank'),
        'ngv_outer_ring_od_m': (n, 'outer_ring_od'),
        'tw_rim_width_m': (t, 'blade_axial_width_at_rim'), 'tw_boss_d_m': (t, 'hub_boss_diameter'),
        'tw_boss_total_m': (t, 'hub_boss_total_length'), 'tw_boss_side_a_m': (t, 'hub_boss_protrusion_side_a'),
        'tw_Id_kg_m2': (t, 'diametral_inertia_estimate'),
        'cw_bore_d_m': (c, 'bore_diameter'), 'tw_bore_d_m': (t, 'bore_diameter'),
        'ngv_hub_pocket_d_m': (n, 'hub_ring_bore'),
    }
    for k, (rec, pname) in stack.items():
        put(k, rec.si(pname), _lab(rec, pname))
    amap = {'front_thread_length_m': 'front_thread_length', 'compressor_nut_length_m': 'compressor_nut_length',
            'backface_clearance_m': 'backface_clearance', 'backplate_rear_face_x_m': 'backplate_rear_face_x',
            'backplate_od_m': 'backplate_od', 'front_sleeve_od_m': 'front_sleeve_od',
            'front_bearing_gap_m': 'front_bearing_gap_to_backplate', 'front_bearing_recess_m': 'front_bearing_recess',
            'shaft_journal_d_m': 'shaft_journal_d',
            'shaft_body_d_m': 'shaft_body_d', 'shaft_comp_seat_d_m': 'shaft_comp_seat_d',
            'shaft_rear_thread_d_m': 'shaft_rear_thread_d', 'rear_thread_length_m': 'rear_thread_length',
            'turbine_nut_length_m': 'turbine_nut_length', 'rear_spacer_length_m': 'rear_spacer_length',
            'rear_spacer_od_m': 'rear_spacer_od', 'ngv_rotor_axial_gap_m': 'ngv_rotor_axial_gap',
            'plenum_gap_m': 'plenum_gap', 'transition_length_m': 'transition_length',
            'nozzle_length_m': 'nozzle_length', 'ngv_bolt_pcd_m': 'ngv_flange_pcd', 'ngv_bolt_hole_d_m': 'ngv_flange_bolt_hole',
            'tailcone_length_m': 'tailcone_length', 'bellmouth_length_m': 'bellmouth_length'}
    for k, pname in amap.items():
        put(k, a.si(pname), _lab(a, pname))
    return seeds


def run_pipeline(seed, module_set='candidate', guess_overrides=None):
    import run as R
    specs = R.load_all_modules(module_set)
    limits = registry.load_limits()
    guesses = registry._coerce_numbers(registry.load_yaml('initial_guess.yaml'), 'config/initial_guess.yaml')
    guesses.update(guess_overrides or {})
    seeded = set(seed) | set(limits)
    plan = solver.build_plan(specs, seeded)
    state = dict(seed)
    state.update(limits)
    state, log = solver.run_plan(plan, state, guesses=guesses)
    return plan, state, limits, log


def unregistered(seed):
    reg = registry.load_registry()
    return sorted(k for k in seed if k not in reg)
