#!/usr/bin/env python3
"""Run a named engine case and write a self-describing result folder.

    python run_case.py --list
    python run_case.py pd1-jm85                 # candidate: match, pipeline, components, CAD, BOM
    python run_case.py pd1-jm85 --robustness    # + fixed-geometry robustness cases
    python run_case.py dp2-prescribed           # prescribed-flow design screen (comparison)
    python run_case.py baseline-250N            # legacy thrust-sizing regression case

Results go to out/<case>/<design-fingerprint[:12]>/ through a staging folder.
out/<case>/LATEST.json points at the newest successful run; a failed run marks it
stale. PRELIMINARY - NOT FOR MANUFACTURE: screening results, not released design.
Exit status: 0 when the run completed (engineering screens may still fail and are
reported), 1 when the run itself failed.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import cases, candidate, postprocess, assembly          # noqa: E402
from core.records import ROOT, file_sha256, Check, MissingInput    # noqa: E402

RELEASE = 'PRELIMINARY - NOT FOR MANUFACTURE'


def _csv(rows, cols):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator='\n')
    w.writerow(cols)
    for r in rows:
        w.writerow([r.get(c) for c in cols])
    return buf.getvalue()


def _checks_table(checks):
    return [c.as_dict() if isinstance(c, Check) else c for c in checks]


def limit_rows(state, limits):
    import run as R
    return [dict(label=l, variable=k, value=v, operator=op, limit=lim, status='pass' if ok else 'fail')
            for l, k, v, op, lim, ok in R.check_limits(state, limits)]


def station_rows(dp):
    s, f = dp['stations'], dp['flows']
    m_air, m_t = f['m_air_kg_s'], f['m_turbine_kg_s']
    rows = [
        ('0', 'ambient (static = total)', s['T0_K'], s['P0_Pa'], None, None, 0.0, 'case ambient'),
        ('2', 'compressor face (after bellmouth/screen)', s['T2_K'], s['P2_Pa'], None, None, m_air, 'inlet loss model'),
        ('3', 'compressor stage exit (map plane, diffuser exit)', s['T3_K'], s['P3_Pa'], None, None, m_air, 'compressor map'),
        ('31', 'combustor inlet (after turn/deswirl)', s['T3_K'], s['P31_Pa'], None, None, f['m_comb_air_kg_s'], 'duct loss model'),
        ('4', 'combustor exit / liner discharge', s['T4_K'], s['P4_Pa'], None, None, f['m_comb_air_kg_s'] + f['m_fuel_kg_s'], 'prescribed-loss scaling'),
        ('41', 'NGV inlet (after tunnel-leak re-entry)', s['T41_K'], s['P41_Pa'], None, None, m_t, 'adiabatic mixing'),
        ('45', 'NGV exit / rotor inlet (static, mean line)', None, None, dp['turbine']['T1_K'], dp['turbine']['P1_Pa'], m_t, 'turbine rating'),
        ('5', 'turbine exit', s['T5_K'], s['P5_Pa'], s['T5_static_K'], s['P5_static_Pa'], m_t, 'turbine rating'),
        ('7', 'nozzle inlet (after jet pipe/swirl)', s['T7_K'], s['P7_Pa'], None, None, m_t, 'jet-pipe loss model'),
        ('8', 'nozzle exit', None, None, s['T8_static_K'], s['P8_static_Pa'], m_t, 'thermo.nozzle'),
    ]
    return [dict(station=a, description=b, T_total_K=c, P_total_Pa=d, T_static_K=e, P_static_Pa=g,
                 mass_flow_kg_s=h, source=i) for a, b, c, d, e, g, h, i in rows]


def pressure_ledger(dp, eng):
    s, l = dp['stations'], dp['losses']
    return [
        dict(segment='0-2', element='bellmouth + screen + starter struts', loss_frac=l['inlet_frac'],
             basis='assumption: 1 % at reference corrected flow, scaled with flow squared'),
        dict(segment='2-3', element='compressor stage incl. its diffuser', loss_frac=None,
             basis='map pressure ratio/efficiency (no separate diffuser loss: double count avoided)'),
        dict(segment='3-31', element='90 deg turn + deswirl into annuli', loss_frac=l['duct_frac'],
             basis=f'assumption {eng.duct_loss_design:.3f} at design FF, scaled with FF squared'),
        dict(segment='31-4', element='combustor (annuli, holes, liner)', loss_frac=l['combustor_frac'],
             basis=f'prescribed sizing basis {eng.comb_loss_design:.3f} at design FF, scaled with FF squared'),
        dict(segment='4-41', element='tunnel leakage re-entry ahead of NGV', loss_frac=0.0,
             basis=f'adiabatic mixing; {eng.leak_frac:.3f} of compressor air bypasses the combustor'),
        dict(segment='41-5', element='turbine stage (expansion, not a loss)', loss_frac=None,
             basis=f'rated expansion P5/P41 = {s["P5_Pa"] / s["P41_Pa"]:.4f}; its losses (Soderberg, tip leakage, '
                   'incidence) are inside the rating'),
        dict(segment='5-7', element='jet pipe + dissipated exit swirl', loss_frac=1 - s['P7_Pa'] / s['P5_Pa'],
             basis=f'{eng.jetpipe_loss:.3f} fixed + swirl dynamic head {l["swirl_head_Pa"]:.0f} Pa'),
        dict(segment='7-8', element='convergent nozzle', loss_frac=None,
             basis=f'Cv {eng.nozzle_Cv}, Cd {eng.nozzle_Cd}; choked={dp["nozzle"]["choked"]}'),
    ]


CASE_INPUT_BLOCKS = ('engine', 'combustor', 'diffuser', 'rotor_support', 'seed_overrides', 'turbine_overrides')


def assumptions_register(recs, case=None):
    rows = []
    for role, r in recs.items():
        for row in r.summary_rows():
            if row['basis'] in ('assumption', 'unresolved'):
                rows.append(dict(role=role, **row))
    # Case-file inputs (losses, Cd/Cv, efficiencies, supports, combustor seeds ...) carry the
    # result as much as record parameters do; list them so the register is complete.
    for block in CASE_INPUT_BLOCKS if case else ():
        for name, value in (case.get(block) or {}).items():
            rows.append(dict(role='case', component=f'{case["case_id"]}.{block}', parameter=name, value=value,
                             unit=None, basis='case input (assumption or design choice)',
                             source=f'config/cases/{case["case_id"]}.yaml', range=None,
                             note='Set in the case file; see the comment there for its basis.'))
    return rows


# ---------------------------------------------------------------------------- candidate
def run_candidate(case, recs, folder, args, log):
    T0, P0 = case['ambient']['T0_K'], case['ambient']['P0_Pa']
    op = case['operating']
    eng = candidate.engine_from_case(case, recs)
    t0 = time.time()
    eng, dp, dinfo = candidate.anchored_design_point(eng, op['design_speed_rpm'], T0, P0)
    log.append(f'design point matched in {time.time()-t0:.1f} s: beta {dp["beta"]:.4f}, T04 {dp["T04_K"]:.2f} K, '
               f'residuals {dp["residuals"]["r_mass"]:.2e} / {dp["residuals"]["r_power"]:.2e}')
    t0 = time.time()
    line = candidate.rating_sweep(eng, op['rating_speeds_rpm'], dp, T0, P0)
    log.append(f'operating line ({len(line)} speeds) in {time.time()-t0:.1f} s')
    seeds = candidate.candidate_seeds(case, recs, eng, dp)
    seed, prov = cases.compose_seed(case, seeds)
    unreg = candidate.unregistered(seed)
    if unreg:
        raise cases.CaseError(f'seed variables not in config/variables.yaml: {unreg}')
    t0 = time.time()
    plan, state, limits, plog = candidate.run_pipeline(
        seed, case.get('module_set', 'candidate'), guess_overrides={'D_casing_out_m': recs['assembly'].si('casing_od')})
    log.append(f'module pipeline in {time.time()-t0:.1f} s')
    # ---- detailed definitions from the same state
    from modules.m20_combustor import run_library
    comb = run_library(state).run()
    p_stack = assembly.params_from_state(state)
    stack = assembly.build_stack(p_stack)
    layout = postprocess.combustor_layout(comb)
    noz = postprocess.nozzle_contour(stack, p_stack)
    from core import diffuser as diffmod
    diff = diffmod.design(state['mdot_kg_s'], state['T03_K'], state['P03_Pa'], state['D2_m'], state['b2_m'],
                          state['Cm2_m_s'], state['Ctheta2_m_s'], state['diff_vaneless_ratio'],
                          state['D2_m'] * state['diff_radius_ratio'], state['diff_vanes_design_count'],
                          state['diff_width_ratio'], state['diff_throat_mach_ratio'], state['diff_exit_turning_deg'],
                          state['diff_cp_assumed_ratio'], state['diff_turn_K_ratio'], state['R_gas_J_kgK'],
                          state['diff_exit_width_growth_ratio'])
    t0 = time.time()
    rs = case.get('rotor_support') or {}
    k0 = state['k_support_N_m']
    rd = postprocess.rotor_dynamics(stack, state['N_operating_min_rpm'], state['N_operating_max_rpm'],
                                    rs.get('unbalance_grade_G_mm_s', 2.5), k_range=[0.5 * k0, k0, 2.5 * k0])
    log.append(f'rotor dynamics in {time.time()-t0:.1f} s')
    mats = recs['materials']
    clr = postprocess.clearances(stack, p_stack, dp, mats, state['N_rpm'])
    mech = postprocess.shaft_and_structure(stack, state, mats, dp, comb)
    # combustor basis comparison (same inlet state, loss and residence-time options)
    basis = combustor_basis_comparison(state)
    # ---- write results
    folder.write_json('design_point.json', cases.clean_floats(dict(release_status=RELEASE, point=dp, verification=dinfo,
                                                                   engine=eng.describe())))
    folder.write_json('operating_line.json', cases.clean_floats(line))
    folder.write_text('operating_line.csv', _csv([op_row(p) for p in line], OP_COLS))
    folder.write_text('station_table.csv', _csv(station_rows(dp), ['station', 'description', 'T_total_K', 'P_total_Pa',
                                                                   'T_static_K', 'P_static_Pa', 'mass_flow_kg_s', 'source']))
    folder.write_text('pressure_ledger.csv', _csv(pressure_ledger(dp, eng), ['segment', 'element', 'loss_frac', 'basis']))
    pw = dp['powers']
    folder.write_json('power_ledger.json', cases.clean_floats(dict(
        N_rpm=dp['N_rpm'], P_compressor_W=pw['P_compressor_W'], P_turbine_W=pw['P_turbine_W'],
        P_bearings_W=pw['P_bearings_W'], P_windage_W=pw['P_windage_W'], P_accessory_W=0.0, P_starter_W=0.0,
        P_net_W=pw['P_net_W'], residual_frac=dp['residuals']['r_power'],
        note='Mechanical losses explicit (bearing friction + disc windage); no mechanical efficiency applied.')))
    folder.write_json('state.json', {k: state[k] for k in sorted(state)})
    folder.write_json('seed_provenance.json', {k: prov[k] for k in sorted(prov) if prov[k] != 'seed_base'})
    folder.write_json('limits.json', limit_rows(state, limits))
    folder.write_json('combustor.json', cases.clean_floats(dict(
        library_result={k: v for k, v in comb.items() if k != 'cad_geometry'}, cad_geometry=comb['cad_geometry'],
        layout={k: v for k, v in layout.items() if k != 'checks'}, layout_checks=_checks_table(layout['checks']),
        basis_comparison=basis)))
    folder.write_json('diffuser.json', cases.clean_floats(diff))
    folder.write_json('nozzle.json', cases.clean_floats(dict(noz, checks=_checks_table(noz['checks']))))
    folder.write_json('assembly_stack.json', cases.clean_floats(dict(
        frame='x aft positive from compressor wheel backface (cold); r radial; theta 0 at top, clockwise viewed from front',
        stations_m=stack['x'], parts=stack['parts'],
        shaft_sections=[dict(name=s.name, z0_m=s.z0, length_m=s.length, od_m=s.od) for s in stack['sections']],
        rotating_masses=[dict(name=d.name, x_m=d.z, mass_kg=d.mass, Ip_kg_m2=d.Ip, Id_kg_m2=d.Id) for d in stack['discs']],
        bearings=[dict(name=s.name, x_m=s.z, k_N_m=s.k, c_N_s_m=s.c) for s in stack['supports']],
        summary={k: stack[k] for k in ('bearing_span_m', 'comp_overhang_m', 'turb_overhang_m', 'shaft_length_m',
                                       'engine_length_m', 'shaft_mass_kg', 'rotor_mass_kg', 'rotor_cg_x_m', 'rotor_Ip_kg_m2')},
        checks=_checks_table(stack['checks']))))
    folder.write_json('rotordynamics.json', cases.clean_floats(rd))
    folder.write_json('clearances.json', cases.clean_floats(dict(clr, checks=_checks_table(clr['checks']))))
    folder.write_json('structures.json', cases.clean_floats(dict(mech, checks=_checks_table(mech['checks']))))
    all_checks = (stack['checks'] + layout['checks'] + noz['checks'] + clr['checks'] + mech['checks'])
    extra = candidate_extra_checks(state, dp, line, diff, rd, case)
    all_checks += extra
    folder.write_json('candidate_checks.json', cases.clean_floats(_checks_table(all_checks)))
    folder.write_json('assumptions_register.json', cases.clean_floats(assumptions_register(recs, case)))
    folder.write_text('pipeline_plan.txt', plan.describe() + '\n')
    return dict(engine=eng, design_point=dp, line=line, state=state, limits=limits, stack=stack, p_stack=p_stack,
                comb=comb, layout=layout, nozzle=noz, diffuser=diff, rotor=rd, clearances=clr, mech=mech,
                checks=all_checks, limit_rows=limit_rows(state, limits), prov=prov, basis=basis)


OP_COLS = ['N_rpm', 'status', 'method', 'beta', 'mdot_air_kg_s', 'PR', 'eta_c', 'SM_flow', 'T03_K', 'P03_kPa',
           'T04_K', 'T41_K', 'EGT_T5_K', 'P5_kPa', 'eta_t_tt', 'psi', 'ngv_flow_frac', 'rotor_flow_frac',
           'fuel_kg_h', 'thrust_N', 'P_comp_kW', 'P_turb_kW', 'P_mech_W', 'r_mass', 'r_power', 'map_conf', 'nozzle_choked']


def op_row(p):
    if 'beta' not in p:
        return dict(N_rpm=p.get('N_rpm'), status=p.get('status'), method=p.get('method'))
    c, s, f, pw, t = p['compressor'], p['stations'], p['flows'], p['powers'], p['turbine']
    return dict(N_rpm=p['N_rpm'], status='matched' if p.get('converged') else 'unconverged', method=p.get('method'),
                beta=round(p['beta'], 5), mdot_air_kg_s=round(c['mdot_kg_s'], 5), PR=round(c['PR'], 4),
                eta_c=round(c['eta'], 4), SM_flow=round(c['SM_flow'], 4), T03_K=round(s['T3_K'], 2),
                P03_kPa=round(s['P3_Pa'] / 1e3, 3), T04_K=round(p['T04_K'], 2), T41_K=round(s['T41_K'], 2),
                EGT_T5_K=round(s['T5_K'], 2), P5_kPa=round(s['P5_Pa'] / 1e3, 3), eta_t_tt=round(t['eta_tt'], 4),
                psi=round(t['psi'], 4), ngv_flow_frac=round(t['ngv_flow_fraction_of_max'], 4),
                rotor_flow_frac=round(t['rotor_flow_fraction_of_max'], 4), fuel_kg_h=round(f['fuel_kg_h'], 3),
                thrust_N=round(p['thrust_N'], 3), P_comp_kW=round(pw['P_compressor_W'] / 1e3, 4),
                P_turb_kW=round(pw['P_turbine_W'] / 1e3, 4), P_mech_W=round(pw['P_mechanical_W'], 2),
                r_mass=p['residuals']['r_mass'], r_power=p['residuals']['r_power'],
                map_conf=c['eta_confidence'], nozzle_choked=p['nozzle']['choked'])


def combustor_basis_comparison(state):
    from modules.m20_combustor import combustor_inputs, MATERIAL_CODES
    from core.combustor import MicroJetCombustor, CombustorError
    out = []
    for loss in (0.025, 0.03, 0.04, 0.06):
        for tau in (0.0014, 0.002):
            s = dict(state)
            s['dP34_frac'], s['tau_min_s'] = loss, tau
            inputs, params, material = combustor_inputs(s)
            m = MicroJetCombustor(inputs)
            m.DESIGN_PARAMS.update(params)
            m.MATERIALS[material]['alpha'] = s['alpha_liner_per_K']
            try:
                r = m.run()
                out.append(dict(loss=loss, tau_ms=tau * 1e3, feasible=True, L_cold_mm=r['chamber_length_cold_mm'],
                                L_over_D=r['chamber_L_over_D'], casing_req_mm=r['casing_od_required_mm'],
                                n_vap=r['vap_n'], K_outer=r['hole_K_outer'], K_inner=r['hole_K_inner'],
                                dil_pen=max(r['dil_pen_norm_outer'], r['dil_pen_norm_inner']), J_primary=r['stab_J_primary'],
                                q_dome_kW_m2=r['stab_q_dome_kW_m2'], ligaments_ok=r['main_hole_ligaments_ok'],
                                passes_existing_screens=(max(r['dil_pen_norm_outer'], r['dil_pen_norm_inner']) <= 0.75
                                                         and min(r['hole_K_outer'], r['hole_K_inner']) >= 6
                                                         and r['tau_comb_ms'] >= 1.2 and r['main_hole_ligaments_ok'])))
            except CombustorError as e:
                out.append(dict(loss=loss, tau_ms=tau * 1e3, feasible=False, error=str(e).splitlines()[0]))
    return out


def candidate_extra_checks(state, dp, line, diff, rd, case):
    ch = []
    ch.append(Check.compare('design point mass residual', abs(dp['residuals']['r_mass']), '<=', 1e-6, '-', 'calculated'))
    ch.append(Check.compare('design point power residual (zero starter torque)', abs(dp['residuals']['r_power']), '<=',
                            1e-6, '-', 'calculated'))
    ch.append(Check.compare('module-path nozzle mass residual (import consistency)', abs(state['nozzle_mass_residual_ratio']),
                            '<=', 1e-5, '-', 'calculated'))
    lo, hi = case['operating']['steady_range_rpm']
    inrange = [p for p in line if lo <= p.get('N_rpm', 0) <= hi]
    matched = [p for p in inrange if p.get('converged')]
    # Model-validity rule (same as core/robustness.status_of): a model used outside its
    # validity range cannot establish a pass, and it is not evidence of failure either.
    flagged = [(p['N_rpm'], p['turbine']['flags']) for p in matched if p['turbine']['flags']]
    extrapolated = [n for n, _ in flagged]

    def over_range(check):
        if check.status != 'pass' or not extrapolated:
            return check
        note = (f'met at every matched speed, but at {extrapolated} rpm the turbine loss model is outside its '
                'validity range, so the pass is not established there')
        return Check(check.name, 'unknown', check.value, check.limit, check.unit, check.criterion, check.basis,
                     f'{check.reason}; {note}' if check.reason else note)
    ch.append(over_range(Check(
        'steady self-sustaining match at every rated speed in range', 'pass' if len(matched) == len(inrange) and inrange
        else 'fail', len(matched), len(inrange), 'count', '== all', 'calculated',
        'zero starter torque; conditional on assumed turbine angles and map proxy')))
    if matched:
        ch.append(Check('turbine correlation validity over steady range', 'unknown' if flagged else 'pass',
                        len(flagged), 0, 'count', '<= 0', 'calculated',
                        (f'model outside its validity range (unresolved, not an engine failure): {flagged}') if flagged
                        else 'No implemented validity flag; unmeasured blade incidence remains unknown.'))
        ch.append(over_range(Check.compare('max T04 over steady range', max(p['T04_K'] for p in matched), '<=',
                                           case['engine'].get('T04_screen_max_K', 1150.0), 'K', 'calculated')))
        ch.append(over_range(Check.compare('min surge margin (flow) over steady range',
                                           min(p['compressor']['SM_flow'] for p in matched), '>=', 0.15, '-', 'calculated',
                                           'definition SM_flow = 1 - Q_surge/Q at constant corrected speed')))
        ch.append(over_range(Check.compare('max NGV flow fraction of choke over steady range',
                                           max(p['turbine']['ngv_flow_fraction_of_max'] for p in matched), '<=', 0.95,
                                           '-', 'calculated')))
        ch.append(over_range(Check.compare('max rotor relative flow fraction of choke',
                                           max(p['turbine']['rotor_flow_fraction_of_max'] for p in matched), '<=', 0.95,
                                           '-', 'calculated')))
    below = [p for p in line if p.get('N_rpm', 1e9) < lo]
    ch.append(Check('self-sustain below lowest map speed line', 'unknown', None, None, '', '', 'unresolved',
                    'no compressor characteristic below ~54.5 krpm physical; starter cut-out and idle not established'))
    ch.append(Check.compare('diffuser throat opening required/available', diff['throat_open_ratio'], '<=', 1.0, '-', 'calculated'))
    ch.append(Check.compare('diffuser turn/deswirl loss estimate vs ledger allowance', diff['turn_loss_frac'], '<=',
                            case['engine'].get('duct_loss_design', 0.015), '-', 'calculated'))
    ch.append(Check.compare('critical-speed separation (FE, all modes, 1.5 x max search)', rd['separation_frac'], '>=', 0.20, '-',
                            'calculated', 'limits.yaml criterion; supports are assumptions'))
    tip = [r for r in rd['unbalance']['response'] if r['N_rpm'] <= case['operating']['steady_range_rpm'][1] * 1.05]
    if tip:
        mx = max(r['amp_turbine_m'] for r in tip)
        ch.append(Check.compare('turbine orbit at G2.5 unbalance vs 1/3 cold tip clearance', mx, '<=',
                                state['t_tip_clear_m'] / 3, 'm', 'calculated', 'linear response, assumed damping'))
    return ch


# ---------------------------------------------------------------------------- other modes
def run_legacy(case, folder, log, prescribed=False):
    from core import registry
    extra = {}
    if prescribed:
        pf = case['prescribed']
        extra = {'cycle_prescribed_flow_flag': (1.0, 'mode: prescribed_flow_screen'),
                 'mdot_prescribed_kg_s': (pf['mdot_kg_s'], 'case prescribed.mdot_kg_s'),
                 'compressor_fixed_wheel_flag': (1.0, 'mode: purchased wheel held fixed'),
                 'D2_fixed_m': (pf['D2_m'], 'case prescribed (DP-2 nominal wheel)'),
                 'D1s_fixed_m': (pf['D1s_m'], 'case prescribed'), 'D1h_fixed_m': (pf['D1h_m'], 'case prescribed (assumption)'),
                 'b2_fixed_m': (pf['b2_m'], 'case prescribed'), 'm_imp_fixed_kg': (pf['m_imp_kg'], 'case prescribed'),
                 'Z_imp_fixed_count': (pf['Z_imp'], 'case prescribed')}
    seed, prov = cases.compose_seed(case, extra)
    unreg = candidate.unregistered(seed)
    if unreg:
        raise cases.CaseError(f'seed variables not in config/variables.yaml: {unreg}')
    plan, state, limits, plog = candidate.run_pipeline(seed, case.get('module_set', 'baseline'))
    folder.write_json('state.json', {k: state[k] for k in sorted(state)})
    folder.write_json('seed_provenance.json', {k: prov[k] for k in sorted(prov) if prov[k] != 'seed_base'})
    folder.write_json('limits.json', limit_rows(state, limits))
    folder.write_text('pipeline_plan.txt', plan.describe() + '\n')
    out = dict(state=state, limits=limits, limit_rows=limit_rows(state, limits), prov=prov)
    if prescribed:
        from core.compressor_map import CompressorMap, MapDomainError
        cm = CompressorMap(ROOT / 'data/maps/gt3076r_compressor.yaml')
        T2, P2 = state['T02_K'], state['P02_Pa']
        q = cm.corrected_flow(state['mdot_kg_s'], T2, P2)
        res = dict(corrected_flow_kg_s=q, corrected_flow_lb_min=q * 60 / 0.45359237,
                   N_rpm=state['N_rpm'], N_corr_rpm=cm.corrected_speed(state['N_rpm'], T2), PR_prescribed=state['PR_c_ratio'])
        try:
            b = cm.beta_for_flow(res['N_corr_rpm'], q)
            res['map_at_prescribed_speed'] = dict(zip(('Q', 'PR', 'eta'), cm.point(res['N_corr_rpm'], b)))
        except MapDomainError as e:
            res['map_at_prescribed_speed'] = f'outside map: {e}'
        speeds = []
        for N in range(60000, 100001, 2500):
            nc = cm.corrected_speed(N, T2)
            try:
                b = cm.beta_for_flow(nc, q)
                Q, PR, eta = cm.point(nc, b)
                speeds.append(dict(N_rpm=N, N_corr_rpm=nc, beta=b, PR=PR, eta=eta))
            except MapDomainError:
                continue
        res['speeds_passing_prescribed_flow'] = speeds
        hits = [s for s in speeds if s['PR'] >= state['PR_c_ratio']]
        res['lowest_speed_reaching_prescribed_PR_at_prescribed_flow'] = hits[0] if hits else None
        res['implied_work_coefficient'] = state['work_coeff_c_ratio']
        res['stanitz_slip_76mm_11_blades'] = state['sigma_slip_ratio']
        folder.write_json('map_consistency.json', cases.clean_floats(res))
        out['map_consistency'] = res
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('case', nargs='?')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--robustness', action='store_true', help='run fixed-geometry robustness cases (slow)')
    ap.add_argument('--out', default=None, help='output root (default out/)')
    args = ap.parse_args(argv)
    if args.list or not args.case:
        for c in cases.list_cases():
            k = cases.load_case(c)
            print(f'{c:<18} {k["mode"]:<24} {k.get("title", "")}')
        return 0
    case = cases.load_case(args.case)
    recs = cases.case_records(case)
    extra_identity = dict(robustness=bool(args.robustness))
    fp = cases.case_fingerprint(case, recs, extra=extra_identity)
    folder = cases.RunFolder(case['case_id'], fp, args.out)
    log = [f'case {case["case_id"]} mode {case["mode"]} fingerprint {fp}']
    t_start = time.time()
    try:
        if case['mode'] == 'fixed_geometry_rating':
            res = run_candidate(case, recs, folder, args, log)
            from core import exports
            exports.write_all(case, recs, res, folder, log)
            if args.robustness:
                from core import robustness
                robustness.run(case, recs, res, folder, log)
            # Systems append checks after the component calculations. Publish the
            # final list only now, so the checks file and manifest agree.
            folder.write_json('candidate_checks.json', cases.clean_floats(_checks_table(res['checks'])))
            folder.write_json('design_readiness.json', design_readiness(recs, res))
        elif case['mode'] == 'prescribed_flow_screen':
            res = run_legacy(case, folder, log, prescribed=True)
        else:
            res = run_legacy(case, folder, log)
        files = design_identity(case, recs)
        manifest = dict(release_status=RELEASE, case_id=case['case_id'], mode=case['mode'], design_fingerprint=fp,
                        fingerprint_scope='case file, seed/limits/registry, every data/ record (components, maps, budget, '
                                          'systems, interfaces), core/*.py, '
                                          'modules/*.py, run.py, run_case.py, requirements.txt; plus run options',
                        run_options=extra_identity, design_files=files,
                        derived_seed_sources={k: v for k, v in res['prov'].items() if v != 'seed_base'},
                        limit_failures=[r for r in res['limit_rows'] if r['status'] == 'fail'],
                        generated_files={}, log=log)
        if 'checks' in res:
            manifest['check_scope'] = 'Numerical screens only; physical evidence and release blockers are in design_readiness.json.'
            manifest['check_summary'] = {s: sum(1 for c in res['checks'] if c.status == s)
                                         for s in ('pass', 'fail', 'unknown', 'not_applicable')}
            manifest['failed_checks'] = [c.name for c in res['checks'] if c.status == 'fail']
            manifest['unknown_checks'] = [c.name for c in res['checks'] if c.status == 'unknown']
        log.append(f'completed in {time.time()-t_start:.1f} s')
        folder.write_json('run_metadata.json', cases.run_metadata())
        folder.write_text('run.log', '\n'.join(log) + '\n')
        for root, _, names in os.walk(folder.stage):
            for n in sorted(names):
                pth = os.path.join(root, n)
                rel = os.path.relpath(pth, folder.stage).replace(os.sep, '/')
                manifest['generated_files'][rel] = file_sha256(pth)
        folder.write_json('manifest.json', manifest)
        final = folder.commit()
        print('\n'.join(log))
        print(f'\n{RELEASE}\nresults: {final}')
        return 0
    except Exception as e:
        log.append('FAILED: ' + ''.join(traceback.format_exception_only(type(e), e)).strip())
        folder.write_text('run.log', '\n'.join(log) + '\n' + traceback.format_exc())
        folder.fail(e)
        print('\n'.join(log), file=sys.stderr)
        traceback.print_exc()
        return 1


def design_identity(case, recs):
    out = {}
    for p in cases.design_files(case, recs):
        try:
            rel = p.resolve().relative_to(ROOT).as_posix()
        except ValueError:
            rel = str(p)
        out[rel] = file_sha256(p)
    return out


def design_readiness(recs, res):
    """Do not confuse equation closure or numerical screen counts with release evidence."""
    pending = [dict(role=role, parameter=name, note=rec.param(name).get('note', ''))
               for role, rec in recs.items() for name in rec.unresolved()]
    evidence = [
        'Actual compressor wheel/housing/diffuser map applicability and map reference conditions',
        'Measured turbine and NGV throats, blade metal angles, orientation and rotation hand',
        'Supplier rotor alloy, temperature/speed/life limits; disc/blade and fitted-hub stress assessment',
        'Approved shaft/bearing/wheel fits and assembly sequence; NGV blank centre-web machining',
        'Bearing speed/preload/lubrication data and measured support stiffness/damping versus temperature',
        'Combustor stability, combustion efficiency, pressure loss and exit temperature distribution',
        'Thermal analysis, transient clearances, seals/leakage and rear bearing/mount temperature',
        'Starter torque-speed/current, battery/ESC selection and low-speed light-off/self-sustain evidence',
        'CAD interference/assembly review, resolved liner seams, stock-size vaporizer rerating and diffuser vane curves',
        'Delivered quotes and confirmed savings/loans/site access within the $6,000 all-in ceiling',
        'Physical controls/interlocks, reviewed containment and a staged test plan',
        'Team acceptance of the front-dome layout versus the originally described reverse-flow architecture',
    ]
    rb = res.get('robustness')
    return dict(release_status=RELEASE, hardware_ready=False, physical_self_sustain='unverified',
                numerical_failures=[c.name for c in res['checks'] if c.status == 'fail'],
                numerical_unknowns=[c.name for c in res['checks'] if c.status == 'unknown'],
                unresolved_record_parameters=pending,
                evidence_not_established_in_repository=evidence,
                robustness_status_counts=({status: sum(r['status'] == status for r in rb['cases'])
                                          for status in ('feasible', 'fails', 'unresolved')} if rb else None),
                budget_nominal_usd=res['budget']['scenarios']['nominal']['total'],
                budget_ceiling_usd=res['budget']['ceiling_usd'],
                note='Evidence items require engineering review; numerical passes do not close them. '
                     'Feasible robustness points satisfy only the implemented model screens.')


if __name__ == '__main__':
    sys.exit(main())
