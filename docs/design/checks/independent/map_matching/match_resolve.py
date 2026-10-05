"""Fork-B independent whole-engine re-solve (item 4) from case/record inputs.

usage (from repo root):  python <this> [pd1_results_dir]
Builds the engine from config/cases/pd1-jm85.yaml + data/components records with the
own model in indep_lib.py (no import of the code under test), solves the fixed-geometry
match (unknowns beta, T04; residuals r_mass, r_power) by a nested global scan + brentq,
anchors the loss-scaling flow functions itself, and compares with the run outputs.
"""
import json
import math
import sys
import time
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import indep_lib as L  # noqa: E402

t_start = time.time()
res = L.results_dir('pd1-jm85', sys.argv)
dpj = json.loads((res / 'design_point.json').read_text())
dp = dpj['point']
line = {p['N_rpm']: p for p in json.loads((res / 'operating_line.json').read_text()) if 'beta' in p}
rob = json.loads((res / 'robustness' / 'robustness.json').read_text())

e0, case = L.engine_from_inputs()
N_d = case['operating']['design_speed_rpm']

print('== A. global scan at the design speed (un-anchored FF guess 2.7e-5), all beta 0..1')
sols, scan = L.match(e0, N_d, n_beta=21)
print(f'    roots found: {len(sols)} ; scan points with a power-balanced T04: '
      f'{sum(1 for _, v in scan if v is not None)}/21 ; T04 roots per beta (max) '
      f'{max((len(v[1]) for _, v in scan if v is not None), default=0)}')
b_g = sols[0]['beta']
print('== B. own anchoring of the loss flow functions (FF_design = FF31, FF_duct = FF3 at the design point)')
e, sol, hist = L.anchored_engine(e0, N_d, beta_bracket=(max(0.0, b_g - 0.1), min(1.0, b_g + 0.1)))
print(f'    anchoring iterations: {len(hist)}')
ev = sol['ev']
t = ev['t']
c = ev['c']
pt, tt, cc, st = dp, dp['turbine'], dp['compressor'], dp['stations']
fl, pw, lo = dp['flows'], dp['powers'], dp['losses']
cmp = L.compare
cmp('FF_design (combustor-loss anchor)', e.FF_design, dpj['engine']['FF_design'], 1e-4)
cmp('FF_duct_design (turn-loss anchor)', e.FF_duct, dpj['engine']['FF_duct_design'], 1e-4)
cmp('DP beta', sol['beta'], pt['beta'], 1e-3)
cmp('DP T04 [K]', sol['T04'], pt['T04_K'], 1e-3)
cmp('DP inner T04 roots at solution beta (count)', sol['n_T04_roots'], 1, 0)
cmp('DP air mass flow [kg/s]', ev['m_air'], cc['mdot_kg_s'], 1e-3)
cmp('DP compressor PR', c['PR'], cc['PR'], 1e-3)
cmp('DP compressor eta', c['eta'], cc['eta'], 1e-3)
cmp('DP T03 [K]', ev['T03'], st['T3_K'], 1e-3)
cmp('DP P04 [Pa]', ev['P04'], st['P4_Pa'], 1e-3)
cmp('DP T41 after leak re-entry [K]', ev['T41'], st['T41_K'], 1e-3)
cmp('DP combustor loss fraction', ev['comb'], lo['combustor_frac'], 1e-3)
cmp('DP duct loss fraction', ev['duct'], lo['duct_frac'], 1e-3)
cmp('DP fuel flow [kg/h]', ev['m_fuel'] * 3600, fl['fuel_kg_h'], 1e-3)
cmp('DP turbine mass flow [kg/s]', ev['m_t'], fl['m_turbine_kg_s'], 1e-3)
cmp('DP U mean [m/s]', t['U'], tt['U_mean_m_s'], 1e-6)
cmp('DP NGV exit C1 [m/s]', t['C1'], tt['C1_m_s'], 1e-3)
cmp('DP rotor inlet rel. angle beta1 [deg]', t['beta1'], tt['beta1_deg'], 1e-2)
cmp('DP rotor exit W2 [m/s]', t['W2'], tt['W2_m_s'], 1e-3)
cmp('DP Euler work [J/kg]', t['w_euler'], tt['w_euler_J_kg'], 1e-3)
cmp('DP delivered work after tip debit [J/kg]', t['w'], tt['w_J_kg'], 1e-3)
cmp('DP eta_tt', t['eta_tt'], tt['eta_tt'], 1e-3)
cmp('DP psi = w/U^2', t['psi'], tt['psi'], 1e-3)
cmp('DP phi = Cx2/U', t['phi'], tt['phi'], 1e-3)
cmp('DP reaction', t['reaction'], tt['reaction'], 1e-3)
cmp('DP Re NGV (own: final state)', t['Re_ngv'], tt['Re_ngv'], 0.1, note='repo reports first-pass Re')
cmp('DP Re rotor (own: final state)', t['Re_rotor'], tt['Re_rotor'], 0.1, note='repo reports first-pass Re')
cmp('DP NGV flow fraction of max', t['ngv_frac'], tt['ngv_flow_fraction_of_max'], 1e-3)
cmp('DP rotor flow fraction of max', t['rotor_frac'], tt['rotor_flow_fraction_of_max'], 1e-3)
cmp('DP T05 total [K]', t['T02'], st['T5_K'], 1e-3)
cmp('DP P05 total [Pa]', t['P02'], st['P5_Pa'], 1e-3)
cmp('DP P07 [Pa]', ev['P07'], st['P7_Pa'], 1e-3)
cmp('DP nozzle NPR', ev['NPR'], dp['nozzle']['NPR'], 1e-3)
cmp('DP V8 [m/s]', ev['V8'], st['V8_m_s'], 1e-3)
cmp('DP thrust [N]', ev['thrust'], pt['thrust_N'], 1e-3)
cmp('DP compressor power [W]', ev['Pc'], pw['P_compressor_W'], 1e-3)
cmp('DP turbine power [W]', ev['Pt'], pw['P_turbine_W'], 1e-3)
cmp('DP bearing power [W]', ev['Pb'], pw['P_bearings_W'], 1e-3)
cmp('DP windage power [W]', ev['Pw'], pw['P_windage_W'], 1e-3)
cmp('DP SM_flow', c['SM_flow'], cc['SM_flow'], 1e-3)
print(f'    own residuals at own root: r_mass {ev["r_mass"]:.2e}, r_power {ev["r_power"]:.2e}; nozzle choked: {ev["choked"]}')

print('== C. repository design point inserted into the own residual equations')
evr = L.evaluate(replace(e0, FF_design=dpj['engine']['FF_design'], FF_duct=dpj['engine']['FF_duct_design']),
                 N_d, pt['beta'], pt['T04_K'])
cmp('own r_mass at repo (beta, T04)', evr['r_mass'], 0.0, abs_tol=1e-6)
cmp('own r_power at repo (beta, T04)', evr['r_power'], 0.0, abs_tol=1e-6)

print('== D. Reynolds-correction iteration (one update as coded vs converged fixed point)')
ec = replace(e, reynolds='converged')
sc, _ = L.match(ec, N_d, n_beta=5, beta_bracket=(sol['beta'] - 0.05, sol['beta'] + 0.05))
if sc:
    cmp('DP T04 with converged Re correction', sc[0]['T04'], pt['T04_K'], 0.5,
        note='size of the single-update simplification')

print('== E. 56 krpm (lowest steady-range speed), anchored engine, global beta scan')
s56, scan56 = L.match(e, 56000, n_beta=11)
print(f'    roots at 56 krpm: {len(s56)}')
if s56 and 56000 in line:
    p = line[56000]
    ev56 = s56[0]['ev']
    cmp('56k beta', s56[0]['beta'], p['beta'], 1e-3)
    cmp('56k T04 [K]', s56[0]['T04'], p['T04_K'], 1e-3)
    cmp('56k air flow [kg/s]', ev56['m_air'], p['compressor']['mdot_kg_s'], 1e-3)
    cmp('56k thrust [N]', ev56['thrust'], p['thrust_N'], 1e-3)
    cmp('56k fuel [kg/h]', ev56['m_fuel'] * 3600, p['flows']['fuel_kg_h'], 1e-3)
    cmp('56k Re rotor (own, final state)', ev56['t']['Re_rotor'], p['turbine']['Re_rotor'], 0.2)
    print(f'    56k flags (own): {ev56["t"]["flags"]}; repo flags: {p["turbine"]["flags"]}')

print('== F. nozzle trim table points (fixed angle + nozzle diameter), own global scan')
trim = {(r['ngv_exit_angle_deg'], round(r['nozzle_exit_d_m'], 3)): r for r in rob['nozzle_trim_table']}
for a1, D in ((60, 0.050), (72, 0.058), (56, 0.054)):
    et = replace(e, stage=replace(e.stage, alpha1_deg=float(a1)), A8=math.pi / 4 * D * D)
    ss, _ = L.match(et, N_d, n_beta=11)
    r = trim[(a1, D)]
    if not ss:
        cmp(f'trim a1={a1} D={D*1e3:.0f} mm: match exists', None, r['T04_K'])
        continue
    if len(ss) > 1:
        print(f'    trim a1={a1} D={D}: {len(ss)} roots (reporting the lowest beta)')
    cmp(f'trim a1={a1} D={D*1e3:.0f} mm T04 [K]', ss[0]['T04'], r['T04_K'], 1e-2)
    cmp(f'trim a1={a1} D={D*1e3:.0f} mm thrust [N]', ss[0]['ev']['thrust'], r['thrust_N'], 1e-2)
    cmp(f'trim a1={a1} D={D*1e3:.0f} mm SM_flow', ss[0]['ev']['c']['SM_flow'], r['SM_flow'], 1e-2)

print('== G. feasibility-window edges (NGV throat), own model + own screens vs the threshold table')


def own_screen(sol, physical=False):
    """Own statement of the documented screens, in the repository's order.

    physical=True stops after the physical screens (match, T04, surge, choke): the threshold table
    locates boundaries of those screens and reports model validity separately."""
    if sol is None:
        return 'no steady match'
    ev = sol['ev']
    if sol['T04'] > 1150.0:
        return 'T04 screen'
    if ev['c']['SM_flow'] < 0.15:
        return 'surge margin'
    if ev['t']['ngv_frac'] > 0.95:
        return 'NGV within 5 % of choke'
    if ev['t']['rotor_frac'] > 0.95:
        return 'rotor near choke'
    if physical:
        return None
    if ev['c']['N_corr'] > 100452.0:
        return 'low-confidence map'
    if ev['t']['flags']:
        return 'turbine model validity'
    return None


def category(text):
    if text is None:
        return None
    for key in ('no steady match', 'T04', 'surge', 'NGV within', 'rotor', 'confidence', 'validity'):
        if key.lower() in text.lower():
            return key
    return text


thr = {r['parameter']: r for r in rob['thresholds']}
for pname, step_out in (('NGV effective throat area (smallest feasible)', -1),
                        ('NGV effective throat area (largest feasible)', +1)):
    A_b = thr[pname]['boundary']
    table_says = thr[pname]['failure_beyond']
    got = {}
    for side, fac in (('inside', 1 - 0.03 * step_out), ('outside', 1 + 0.03 * step_out)):
        eg = replace(e, stage=replace(e.stage, A_ngv_throat=A_b * fac))
        sg, _ = L.match(eg, N_d, n_beta=21)
        sol = sg[0] if sg else None
        got[side] = own_screen(sol, physical=True)
        print(f'    {pname}: {side} {fac:.2f} x {A_b*1e6:.1f} mm2 -> '
              + (f'T04 {sol["T04"]:.0f} K, NGV frac {sol["ev"]["t"]["ngv_frac"]:.3f}, '
                 f'Re rotor {sol["ev"]["t"]["Re_rotor"]:.0f}; ' if sol else 'no root; ')
              + f'own screen: {got[side] or "feasible"}')
    same = category(got['outside']) == category(table_says)
    print(f'      table "failure_beyond": "{table_says}"  vs own just-outside: "{got["outside"]}"  -> '
          f'{"PASS" if same else "DIFF"}; inside feasible: {got["inside"] is None}')
    if not same or got['inside'] is not None:
        L.FAILS.append(f'{pname} edge')

print(f'\nelapsed {time.time() - t_start:.0f} s')
print('FAILS:', L.FAILS if L.FAILS else 'none')
sys.exit(1 if L.FAILS else 0)
