"""Fixed-geometry robustness study and feasibility thresholds for a candidate.

Every case keeps the purchased and designed geometry fixed and re-solves the
steady zero-starter-torque match at the same shaft speed. Ranges are either
taken from the component records (assumption ranges) or are stated
ILLUSTRATIVE bounds; no probability of success is computed. Categorical changes
(the alternative TW70/NGV70 stage) are separate candidates, not perturbations.

Screens applied to every result (first failure reported):
  match exists | T04 <= T04 screen | SM_flow >= 0.15 | NGV and rotor flow <= 0.95
  of choke | map point inside the medium-confidence efficiency domain | turbine
  loss model inside its validity flags

Status rule (one rule for every model domain): a missing steady match or a physical
screen exceedance 'fails'. A point whose only problem is that a model is used outside
its validity domain (below the lowest map speed line, outside the medium-confidence
map region, turbine loss correlation outside its range) is 'unresolved': the model
cannot tell, so it is neither feasible evidence nor evidence of failure.
"""
from __future__ import annotations

import math
import time

from core import candidate, cases
from core.compressor_map import MapOffsets, MapDomainError
from core.engine_match import solve_from_guess, match_speed


def _solve(eng, N, guess, T0, P0):
    pt = solve_from_guess(eng, N, guess['beta'], guess['T04_K'], T0, P0)
    method = 'continuation'
    if pt is None:
        r = match_speed(eng, N, T0, P0, n_scan=11)
        conv = [b for b in r['branches'] if b.get('converged')]
        method = 'global_scan'
        if not conv:
            return None, method, r.get('reason') or 'no match', r.get('failure_reasons')
        pt = conv[0]
    return pt, method, None, None


MODEL_DOMAIN = ('outside map domain', 'outside medium-confidence map domain', 'turbine model validity')


def physical_screen(pt, T04_max, reason=None):
    """First missing-match or physical screen failure, or None."""
    if pt is None:
        if reason and 'outside digitized lines' in reason:
            return 'outside map domain (corrected speed below lowest digitized line) - unresolved, not an engine failure'
        return 'no steady match'
    c, t = pt['compressor'], pt['turbine']
    if pt['T04_K'] > T04_max:
        return f'T04 {pt["T04_K"]:.0f} K > {T04_max:.0f} K screen'
    if c['SM_flow'] < 0.15:
        return f'surge margin {c["SM_flow"]:.3f} < 0.15'
    if t['ngv_flow_fraction_of_max'] > 0.95:
        return 'NGV within 5 % of choke'
    if t['rotor_flow_fraction_of_max'] > 0.95:
        return 'rotor relative throat within 5 % of choke'
    return None


def model_screen(pt):
    """Model used outside its validity domain at an existing point, or None."""
    if pt is None:
        return None
    if pt['compressor']['eta_confidence'] != 'medium':
        return 'outside medium-confidence map domain'
    if pt['turbine'].get('flags'):
        return 'turbine model validity: ' + '; '.join(pt['turbine']['flags'])
    return None


def screens(pt, T04_max, reason=None):
    return physical_screen(pt, T04_max, reason) or model_screen(pt)


def status_of(first_failure):
    if first_failure is None:
        return 'feasible'
    return 'unresolved' if first_failure.startswith(MODEL_DOMAIN) else 'fails'


def case_list(recs, eng):
    t, n = recs['turbine'], recs['ngv']
    a1lo, a1hi = n.param('exit_flow_angle')['range']
    b2lo, b2hi = t.param('rotor_exit_relative_angle')['range']
    tclo, tchi = t.si_range('tip_clearance_design')
    m = recs['compressor_map']
    flow_u = m.si('substitution_flow_uncertainty')
    eta_lo, eta_hi = m.param('substitution_efficiency_deficit')['range']
    A_ngv = eng.stage.ngv_throat()[0]
    L = []
    add = lambda name, group, basis, **kw: L.append(dict(name=name, group=group, basis=basis, **kw))
    add('nominal', 'reference', 'nominal assumptions')
    add(f'NGV exit angle {a1lo:.0f} deg (larger throat)', 'turbine geometry', 'record range', stage=dict(alpha1_deg=a1lo))
    add(f'NGV exit angle {a1hi:.0f} deg (smaller throat)', 'turbine geometry', 'record range', stage=dict(alpha1_deg=a1hi))
    add(f'rotor exit angle {b2hi:.0f} deg (less turning)', 'turbine geometry', 'record range', stage=dict(beta2_deg=b2hi))
    add(f'rotor exit angle {b2lo:.0f} deg (more turning)', 'turbine geometry', 'record range', stage=dict(beta2_deg=b2lo))
    add('NGV throat -5 % (casting/finish tolerance, illustrative)', 'tolerance', 'illustrative',
        stage=dict(A_ngv_throat_m2=0.95 * A_ngv))
    add('NGV throat +5 % (illustrative)', 'tolerance', 'illustrative', stage=dict(A_ngv_throat_m2=1.05 * A_ngv))
    add('turbine losses x1.5 (Soderberg extrapolated to low Re)', 'turbine losses', 'illustrative', stage=dict(loss_scale=1.5))
    add('turbine losses x2.0', 'turbine losses', 'illustrative', stage=dict(loss_scale=2.0))
    add(f'tip clearance {tchi*1e3:.2f} mm', 'turbine losses', 'record range', stage=dict(tip_clearance_m=tchi))
    add('tip-leakage factor K_tip 3.0', 'turbine losses', 'illustrative', stage=dict(K_tip=3.0))
    add('incidence loss active, metal angle 10 deg off design flow', 'turbine losses', 'illustrative', incidence_offset=10.0)
    add(f'compressor efficiency {-eta_hi:+.2f} (billet wheel / vaned diffuser)', 'compressor map', 'map record',
        offsets=dict(eta_delta=-eta_hi))
    add(f'compressor efficiency {-eta_lo:+.2f}', 'compressor map', 'map record', offsets=dict(eta_delta=-eta_lo))
    add(f'compressor flow {-flow_u*100:.0f} %', 'compressor map', 'map record', offsets=dict(flow_scale=1 - flow_u))
    add(f'compressor flow {+flow_u*100:.0f} %', 'compressor map', 'map record', offsets=dict(flow_scale=1 + flow_u))
    add('compressor pressure rise -5 %', 'compressor map', 'illustrative', offsets=dict(pr_rise_scale=0.95))
    add('map reference 288.15 K / 101.325 kPa', 'compressor map', 'convention alternative',
        offsets=dict(reference_override=(288.15, 101325.0)))
    add('combustor loss 4 % at design FF', 'pressure losses', 'V22 basis', eng=dict(comb_loss_design=0.04))
    add('combustor loss 6 % at design FF', 'pressure losses', 'DP-2 cycle screen basis', eng=dict(comb_loss_design=0.06))
    add('combustor loss 8 % at design FF', 'pressure losses', 'illustrative (KJ66 reports ~12 % at PR ~2)',
        eng=dict(comb_loss_design=0.08))
    add('turn/deswirl loss 3 %', 'pressure losses', 'illustrative', eng=dict(duct_loss_design=0.03))
    add('inlet loss 2 %', 'pressure losses', 'illustrative', eng=dict(inlet_loss_ref=0.02))
    add('tunnel leakage 5 %', 'leakage', 'illustrative', eng=dict(leak_frac=0.05))
    add('bearing/windage losses x3', 'mechanical', 'illustrative', mech_scale=3.0)
    add('nozzle area -3 % (forming tolerance, illustrative)', 'tolerance', 'illustrative', A8_scale=0.97)
    add('nozzle area +3 %', 'tolerance', 'illustrative', A8_scale=1.03)
    add('hot day 308 K', 'ambient', 'illustrative', ambient=(308.15, 101325.0))
    add('cold day 268 K', 'ambient', 'illustrative', ambient=(268.15, 101325.0))
    add('low ambient pressure 95 kPa', 'ambient', 'illustrative', ambient=(288.15, 95000.0))
    add('combined adverse (a1 low, b2 least turning, losses x1.5, eta -0.04, comb 6 %, leak 4 %, hot day)', 'combined',
        'illustrative bounding combination',
        stage=dict(alpha1_deg=a1lo, beta2_deg=b2hi, loss_scale=1.5), offsets=dict(eta_delta=-eta_hi),
        eng=dict(comb_loss_design=0.06, leak_frac=0.04), ambient=(308.15, 101325.0))
    return L


def build(case, recs, base_eng, spec, N):
    offsets = MapOffsets(**spec['offsets']) if spec.get('offsets') else None
    so = dict(spec.get('stage') or {})
    eng = candidate.engine_from_case(case, recs, stage_overrides=so, map_offsets=offsets,
                                     FF_design=base_eng.FF_design, FF_duct_design=base_eng.FF_duct_design,
                                     **(spec.get('eng') or {}))
    if spec.get('mech_scale'):
        eng.mech.scale = spec['mech_scale']
    if spec.get('A8_scale'):
        eng = eng.with_(A8_m2=base_eng.A8_m2 * spec['A8_scale'])
    return eng


def run(case, recs, res, folder, log):
    t0 = time.time()
    base_eng, dp = res['engine'], res['design_point']
    T0n, P0n = case['ambient']['T0_K'], case['ambient']['P0_Pa']
    T04_max = case['engine'].get('T04_screen_max_K', 1150.0)
    speeds = [case['operating']['nominal_speed_rpm'], case['operating']['design_speed_rpm'],
              case['operating']['steady_range_rpm'][0]]
    guesses = {p['N_rpm']: p for p in res['line'] if 'beta' in p}
    rows = []
    for spec in case_list(recs, base_eng):
        for N in speeds:
            T0, P0 = spec.get('ambient', (T0n, P0n))
            g = guesses.get(N, dp)
            if spec.get('incidence_offset') is not None:
                beta1_design = res['design_point']['turbine']['beta1_deg']
                spec = dict(spec, stage=dict(spec.get('stage') or {}, beta1_metal_deg=beta1_design + spec['incidence_offset']))
            try:
                eng = build(case, recs, base_eng, spec, N)
                pt, method, reason, fr = _solve(eng, N, g, T0, P0)
            except (MapDomainError, ValueError) as e:
                pt, method, reason, fr = None, 'error', str(e), None
            fail = screens(pt, T04_max, reason)
            row = dict(case=spec['name'], group=spec['group'], basis=spec['basis'], N_rpm=N, method=method,
                       status=status_of(fail), first_failure=fail, model_validity=model_screen(pt),
                       no_match_reason=reason)
            if pt is not None:
                row.update(T04_K=pt['T04_K'], dT04_K=pt['T04_K'] - g['T04_K'], beta=pt['beta'],
                           mdot_kg_s=pt['compressor']['mdot_kg_s'], PR=pt['compressor']['PR'], SM_flow=pt['compressor']['SM_flow'],
                           eta_c=pt['compressor']['eta'], eta_t=pt['turbine']['eta_tt'], thrust_N=pt['thrust_N'],
                           fuel_kg_h=pt['flows']['fuel_kg_h'], ngv_frac=pt['turbine']['ngv_flow_fraction_of_max'],
                           rotor_frac=pt['turbine']['rotor_flow_fraction_of_max'],
                           r_mass=pt['residuals']['r_mass'], r_power=pt['residuals']['r_power'])
            rows.append(row)
    thresholds = threshold_search(case, recs, base_eng, dp, T04_max)
    trim = nozzle_trim_table(case, recs, base_eng, dp, T04_max)
    rescue = adverse_rescue(case, recs, base_eng, dp, T04_max)
    alt = alternative_stage(case, recs, base_eng, T04_max)
    out = dict(speeds_rpm=speeds, T04_screen_K=T04_max, cases=rows, thresholds=thresholds, nozzle_trim_table=trim,
               combined_adverse_rescue=rescue, alternative_candidate=alt,
               note='Fixed geometry in every case. Ranges are record ranges or labelled illustrative bounds; '
                    'no statistical reliability is implied.')
    folder.write_json('robustness/robustness.json', cases.clean_floats(out))
    import csv, io
    cols = ['case', 'group', 'basis', 'N_rpm', 'status', 'first_failure', 'model_validity', 'T04_K', 'dT04_K', 'beta',
            'mdot_kg_s', 'PR', 'SM_flow', 'eta_c', 'eta_t', 'thrust_N', 'fuel_kg_h', 'ngv_frac', 'rotor_frac', 'method',
            'no_match_reason']
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator='\n')
    w.writerow(cols)
    for r in rows:
        w.writerow([r.get(c) for c in cols])
    folder.write_text('robustness/robustness.csv', buf.getvalue())
    res['robustness'] = out
    tornado(out, folder, dp['N_rpm'], T04_max)
    n_fail = sum(1 for r in rows if r['status'] == 'fails')
    n_unres = sum(1 for r in rows if r['status'] == 'unresolved')
    log.append(f'robustness: {len(rows)} case-speed points, {n_fail} fail a screen, {n_unres} unresolved '
               f'(model outside its validity domain); {time.time()-t0:.0f} s')


def threshold_search(case, recs, base_eng, dp, T04_max):
    """Bisection on single parameters for the value where the design-speed match hits a physical screen.

    The boundary is where the model's physical screens (match exists, T04, surge margin,
    choke) change; model-validity flags do not move it. Whether the model is inside its
    validity domain on the feasible side of the boundary is reported separately.
    """
    N = dp['N_rpm']
    T0, P0 = case['ambient']['T0_K'], case['ambient']['P0_Pa']
    out = []

    def feasible(spec):
        try:
            eng = build(case, recs, base_eng, spec, N)
            pt, method, reason, _ = _solve(eng, N, dp, T0, P0)
        except (MapDomainError, ValueError) as e:
            pt, reason = None, str(e)
        return physical_screen(pt, T04_max, reason), pt

    def search(name, make, lo, hi, unit, n=14):
        f_lo, p_lo = feasible(make(lo))
        f_hi, p_hi = feasible(make(hi))
        if (f_lo is None) == (f_hi is None):
            out.append(dict(parameter=name, unit=unit, bracket=[lo, hi], result='same endpoint status; interior not scanned',
                            feasible_at_low=f_lo is None, feasible_at_high=f_hi is None,
                            failure_at_low=f_lo, failure_at_high=f_hi))
            return
        a, b = lo, hi
        fa, pa = f_lo, p_lo
        fb, pb = f_hi, p_hi
        for _ in range(n):
            m = 0.5 * (a + b)
            fm, pm = feasible(make(m))
            if (fm is None) == (fa is None):
                a, fa, pa = m, fm, pm
            else:
                b, fb, pb = m, fm, pm
        # report the failure found just past the boundary, not the one at the far end of the bracket
        p_feasible, beyond = (pa, fb) if fa is None else (pb, fa)
        out.append(dict(parameter=name, unit=unit, boundary=0.5 * (a + b), feasible_side='low' if f_lo is None else 'high',
                        failure_beyond=beyond,
                        model_validity_at_boundary=model_screen(p_feasible) or 'inside implemented validity flags',
                        note='one transition located inside the bracket; not a proof that the feasible set is connected'))
    A_ngv = base_eng.stage.ngv_throat()[0]
    search('NGV effective throat area (smallest feasible)', lambda A: dict(stage=dict(A_ngv_throat_m2=A)),
           0.25 * A_ngv, A_ngv, 'm2')
    search('NGV effective throat area (largest feasible)', lambda A: dict(stage=dict(A_ngv_throat_m2=A)),
           A_ngv, 0.98 * base_eng.stage.A_ngv_exit_m2, 'm2')
    A_r = base_eng.stage.rotor_throat()[0]
    search('rotor relative throat area (smallest feasible)', lambda A: dict(stage=dict(A_rotor_throat_m2=A)),
           0.25 * A_r, A_r, 'm2')
    search('rotor relative throat area (largest feasible)', lambda A: dict(stage=dict(A_rotor_throat_m2=A)),
           A_r, 0.98 * base_eng.stage.A_rotor_m2, 'm2')
    search('turbine loss multiplier (largest feasible)', lambda s: dict(stage=dict(loss_scale=s)), 1.0, 10.0, '-')
    search('compressor efficiency offset (most negative feasible)', lambda d: dict(offsets=dict(eta_delta=d)), -0.30, 0.0, '-')
    search('combustor loss at design FF (largest feasible)', lambda x: dict(eng=dict(comb_loss_design=x)), 0.025, 0.40, '-')
    return out


def nozzle_trim_table(case, recs, base_eng, dp, T04_max, angles=(56, 60, 64, 68, 72), diameters=(0.046, 0.050, 0.054,
                                                                                                  0.058, 0.062)):
    """T04 at the design speed versus NGV exit angle (i.e. measured throat) and nozzle exit diameter."""
    N = dp['N_rpm']
    T0, P0 = case['ambient']['T0_K'], case['ambient']['P0_Pa']
    out = []
    for a in angles:
        for D in diameters:
            eng = candidate.engine_from_case(case, recs, stage_overrides=dict(alpha1_deg=a),
                                             FF_design=base_eng.FF_design, FF_duct_design=base_eng.FF_duct_design)
            eng = eng.with_(A8_m2=math.pi / 4 * D * D)
            try:
                pt, *_ = _solve(eng, N, dp, T0, P0)
            except (MapDomainError, ValueError):
                pt = None
            first = screens(pt, T04_max)
            out.append(dict(ngv_exit_angle_deg=a, ngv_throat_m2=eng.stage.ngv_throat()[0], nozzle_exit_d_m=D,
                            T04_K=pt['T04_K'] if pt else None, thrust_N=pt['thrust_N'] if pt else None,
                            SM_flow=pt['compressor']['SM_flow'] if pt else None, status=status_of(first), screen=first))
    return out


def adverse_rescue(case, recs, base_eng, dp, T04_max, target_K=1100.0):
    """Nozzle exit diameter that brings the combined adverse case back to target T04 at the design speed."""
    spec = [c for c in case_list(recs, base_eng) if c['group'] == 'combined'][0]
    N = dp['N_rpm']
    T0, P0 = spec['ambient']

    def T04_at(D):
        eng = build(case, recs, base_eng, spec, N).with_(A8_m2=math.pi / 4 * D * D)
        pt, *_ = _solve(eng, N, dp, T0, P0)
        return pt['T04_K'] if pt else None
    lo, hi = recs['assembly'].si('nozzle_exit_d'), 0.075
    t_lo, t_hi = T04_at(lo), T04_at(hi)
    if t_lo is None or t_hi is None or t_hi > target_K:
        return dict(target_K=target_K, result='not reachable with nozzle area alone in 54-75 mm', T04_at_54=t_lo, T04_at_75=t_hi)
    for _ in range(16):
        m = 0.5 * (lo + hi)
        t = T04_at(m)
        if t is not None and t <= target_K:
            hi = m
        else:
            lo = m
    trial = build(case, recs, base_eng, spec, N).with_(A8_m2=math.pi / 4 * hi * hi)
    pt, *_ = _solve(trial, N, dp, T0, P0)
    # The exit-area-only matching model assumes the throat is at the exit.
    # Opening the exit beyond the retained inlet annulus breaks that assumption.
    shroud_r = trial.stage.r_tip_m + trial.stage.tip_clearance_m
    inlet_annulus = math.pi * (shroud_r ** 2 - trial.stage.r_hub_m ** 2)
    geometry_ok = trial.A8_m2 <= inlet_annulus
    return dict(target_K=target_K, nozzle_exit_d_m=hi, T04_K=pt['T04_K'] if pt else None, case=spec['name'],
                model_screen=screens(pt, T04_max), exit_is_minimum_area_necessary_check=geometry_ok,
                retained_nozzle_inlet_annulus_m2=inlet_annulus,
                result=('candidate for full nozzle geometry rerating' if geometry_ok else
                        'INVALID as a simple exit resize: retained inlet annulus is smaller than exit; redesign/rerate nozzle'),
                note='This is a changed geometry study, not evidence that the original candidate is robust.')


def alternative_stage(case, recs, base_eng, T04_max):
    """TW70 + NGV70 finished pair on the same compressor/nozzle: categorical alternative."""
    from core.records import load_record
    from core.turbine_rating import stage_from_records
    try:
        t70 = load_record('data/components/turbine_jetmax_tw70.yaml')
        n70 = load_record('data/components/ngv_jetmax_ngv70.yaml')
    except Exception as e:  # missing record is reported, not hidden
        return dict(error=str(e))
    st = stage_from_records(t70, n70)
    T0, P0 = case['ambient']['T0_K'], case['ambient']['P0_Pa']
    out = []
    for D8 in (0.046, 0.050, 0.054):
        eng = base_eng.with_(stage=st, A8_m2=math.pi / 4 * D8 * D8)
        for N in (case['operating']['steady_range_rpm'][0], case['operating']['nominal_speed_rpm'],
                  case['operating']['design_speed_rpm']):
            r = match_speed(eng, N, T0, P0, n_scan=11)
            conv = [b for b in r['branches'] if b.get('converged')]
            pt = conv[0] if conv else None
            out.append(dict(nozzle_exit_d_m=D8, N_rpm=N, status='matched' if pt else r['status'],
                            first_failure=screens(pt, T04_max),
                            T04_K=pt['T04_K'] if pt else None, thrust_N=pt['thrust_N'] if pt else None,
                            SM_flow=pt['compressor']['SM_flow'] if pt else None,
                            rotor_frac=pt['turbine']['rotor_flow_fraction_of_max'] if pt else None,
                            mdot_kg_s=pt['compressor']['mdot_kg_s'] if pt else None))
    return dict(stage=st.as_dict(), points=out,
                note='Same compressor proxy map, same inlet/combustor loss models; 70 mm pair evidence is the UT160 '
                     'designer report at 123 krpm with a different compressor.')


def tornado(out, folder, N, T04_max):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    rows = [r for r in out['cases'] if r['N_rpm'] == N and r['case'] != 'nominal' and r.get('T04_K') is not None]
    rows.sort(key=lambda r: abs(r['dT04_K']))
    fig, ax = plt.subplots(figsize=(10, 0.32 * len(rows) + 1.5))
    base = [r for r in out['cases'] if r['N_rpm'] == N and r['case'] == 'nominal'][0]['T04_K']
    ax.barh([r['case'][:70] for r in rows], [r['dT04_K'] for r in rows],
            color=['firebrick' if r['status'] == 'fails' else ('gray' if r['status'] == 'unresolved' else 'steelblue')
                   for r in rows])
    ax.axvline(T04_max - base, color='k', ls='--', lw=1, label=f'T04 screen {T04_max:.0f} K')
    ax.set_xlabel(f'change in T04 at {N:.0f} rpm from nominal {base:.0f} K (fixed geometry, zero starter torque)')
    ax.legend(fontsize=7)
    ax.tick_params(axis='y', labelsize=7)
    ax.set_title('PD-1 robustness (record ranges and ILLUSTRATIVE bounds; not probabilities)\n'
                 'PRELIMINARY - NOT FOR MANUFACTURE', fontsize=9)
    for ext in ('png', 'svg'):
        fig.savefig(folder.path(f'figures/robustness_tornado.{ext}'), dpi=140, bbox_inches='tight')
    plt.close(fig)
