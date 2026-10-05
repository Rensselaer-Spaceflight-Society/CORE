"""Fork-A independent cycle closure check (design point + every operating-line speed).

Usage (from the repository root):  python <this script> [results_dir]
Default results_dir: docs/design/results/pd1-jm85

Independence: core.gas for PROPERTIES only (via indep_props). Loss settings are read from the case
file and map/bearing records, not from the run, and compared with the run's echo. Every balance
(corrected flow, inlet loss, compressor work, duct/combustor loss, FAR, mixing, turbine power,
bearing friction, windage, jet pipe, nozzle, thrust) is recomputed here.
Exit status 1 if any comparison differs by more than its tolerance.
"""
import csv
import math
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from indep_props import R, h, cp, T_of_h, T_isentropic, load_results, Reporter  # noqa: E402
from scipy.optimize import brentq  # noqa: E402

folder = sys.argv[1] if len(sys.argv) > 1 else 'docs/design/results/pd1-jm85'
rep = Reporter(tol_pct=1.0)
j = load_results(folder)
dpj = j('design_point.json')
eng = dpj['engine']
with open('config/cases/pd1-jm85.yaml', encoding='utf-8') as fh:
    case = yaml.safe_load(fh)
with open('data/maps/gt3076r_compressor.yaml', encoding='utf-8') as fh:
    mapy = yaml.safe_load(fh)
with open('data/components/bearings_candidate.yaml', encoding='utf-8') as fh:
    brg_rec = yaml.safe_load(fh)


def find_key(d, key):
    """Depth-first search for a key in nested YAML (records differ in layout)."""
    if isinstance(d, dict):
        if key in d:
            return d[key]
        for v in d.values():
            r = find_key(v, key)
            if r is not None:
                return r
    elif isinstance(d, list):
        for v in d:
            r = find_key(v, key)
            if r is not None:
                return r
    return None


ce = case['engine']
amb = case['ambient']
T0, P0 = amb['T0_K'], amb['P0_Pa']
T_ref = find_key(mapy, 'reference_temperature')['value']
P_ref = find_key(mapy, 'reference_pressure')['value']

print(f'== Fork-A cycle closure on {folder}')
print('-- inputs: case file vs echo in design_point.json')
for k in ('comb_loss_design', 'duct_loss_design', 'inlet_loss_ref', 'inlet_Q_ref_kg_s', 'leak_frac', 'jetpipe_loss',
          'nozzle_Cd', 'nozzle_Cv', 'eta_b', 'LHV_J_kg', 'T04_screen_max_K'):
    rep.cmp(f'input {k}', float(ce[k]), float(eng[k]), tol_pct=1e-9)
rep.cmp('input windage_Cm', float(ce['windage_Cm']), float(eng['mechanical']['windage_Cm']), tol_pct=1e-9)
rep.info('map reference T [K] / P [Pa] (record)', f'{T_ref} / {P_ref}',
         '545 R = 302.78 K; 28.4 inHg = 96,174 Pa (secondary source, per record)')
rep.cmp('A8 = pi/4 * 0.054^2 [m2]', math.pi / 4 * 0.054 ** 2, eng['A8_m2'], tol_pct=1e-6)

mech = eng['mechanical']
bp = brg_rec['parameters']
for b in mech['bearings']:
    for rk, ek in (('bore', 'bore_mm'), ('outer_diameter', 'od_mm'), ('friction_f0', 'f0'),
                   ('lubricant_viscosity', 'nu_cSt'), ('preload_spring_force', 'preload_N')):
        rep.cmp(f'input bearing {b["name"]} {ek} (record vs echo)', float(bp[rk]['value']), float(b[ek]), tol_pct=1e-9)
    rep.info(f'input bearing {b["name"]} mu_load (code default, not in record)', b['mu_load'])


def bearing_power(N, b):
    """SKF/Palmgren: M0 = f0 (nu n)^(2/3) dm^3 1e-7 [N mm] (nu n >= 2000), M1 = 0.5 mu F d [N mm]."""
    dm = 0.5 * (b['bore_mm'] + b['od_mm'])
    M0 = b['f0'] * (b['nu_cSt'] * N) ** (2 / 3) * dm ** 3 * 1e-7
    M1 = 0.5 * b['mu_load'] * b['preload_N'] * b['bore_mm']
    return (M0 + M1) * 1e-3 * N * 2 * math.pi / 60


def check_point(p, label, verbose):
    """Recompute every cycle balance of one matched point; returns dict of (indep, repo) pairs."""
    c, t, s, fl, pw, ls = p['compressor'], p['turbine'], p['stations'], p['flows'], p['powers'], p['losses']
    out = {}
    m = c['mdot_kg_s']
    theta, delta = s['T2_K'] / T_ref, s['P2_Pa'] / P_ref
    out['Q_corr'] = (m * math.sqrt(theta) / delta, c['Q_corr_kg_s'])
    out['N_corr'] = (p['N_rpm'] / math.sqrt(theta), c['N_corr_rpm'])
    loss_in = ce['inlet_loss_ref'] * (c['Q_corr_kg_s'] / ce['inlet_Q_ref_kg_s']) ** 2
    out['P2 (inlet loss)'] = (P0 * (1 - loss_in), s['P2_Pa'])
    out['P03 = P2 PR'] = (s['P2_Pa'] * c['PR'], s['P3_Pa'])
    T03s = T_isentropic(s['T2_K'], c['PR'], 0.0)
    wc = (h(T03s) - h(s['T2_K'])) / c['eta']
    out['compressor w'] = (wc, c['w_J_kg'])
    out['T03'] = (T_of_h(h(s['T2_K']) + wc), s['T3_K'])
    out['P_compressor = m w'] = (m * wc, pw['P_compressor_W'])
    FF3 = m * math.sqrt(s['T3_K']) / s['P3_Pa']
    duct = ce['duct_loss_design'] * (FF3 / (eng['FF_duct_design'] or eng['FF_design'])) ** 2
    out['P031'] = (s['P3_Pa'] * (1 - duct), s['P31_Pa'])
    m_comb = m * (1 - ce['leak_frac'])
    m_leak = m * ce['leak_frac']
    FF31 = m_comb * math.sqrt(s['T3_K']) / s['P31_Pa']
    comb = ce['comb_loss_design'] * (FF31 / eng['FF_design']) ** 2
    out['P04'] = (s['P31_Pa'] * (1 - comb), s['P4_Pa'])
    out['P41 = P04 (no mixing loss)'] = (s['P4_Pa'], s['P41_Pa'])
    # combustor energy balance with fuel mass in the products (fuel sensible enthalpy at datum)
    T03, T04, eb, LHV = s['T3_K'], s['T4_K'], ce['eta_b'], ce['LHV_J_kg']

    def fb(f):
        return m_comb * h(T03) + m_comb * f * eb * LHV - m_comb * (1 + f) * h(T04, f)
    far = brentq(fb, 1e-6, 0.06, xtol=1e-15, rtol=1e-15)
    out['FAR combustor'] = (far, fl['FAR_combustor'])
    m_fuel = m_comb * far
    out['fuel flow [kg/s]'] = (m_fuel, fl['m_fuel_kg_s'])
    out['fuel flow [kg/h]'] = (m_fuel * 3600, fl['fuel_kg_h'])
    out['m_comb = m (1 - leak)'] = (m_comb, fl['m_comb_air_kg_s'])
    out['m_leak'] = (m_leak, fl['m_leak_kg_s'])
    m_t = m + m_fuel
    out['m_turbine = m_air + m_fuel'] = (m_t, fl['m_turbine_kg_s'])
    f_mix = m_fuel / (m_comb + m_leak)
    out['FAR mixed'] = (f_mix, fl['FAR_mixed'])
    hmix = ((m_comb + m_fuel) * h(T04, far) + m_leak * h(T03)) / m_t
    out['T41 adiabatic mixing'] = (T_of_h(hmix, f_mix), s['T41_K'])
    # turbine power from the reported delivered work (closure of work checked in r3_turbine_check)
    w_t = h(s['T41_K'], f_mix) - h(s['T5_K'], f_mix)
    out['P_turbine = m_t (h41 - h05)'] = (m_t * w_t, pw['P_turbine_W'])
    rho_cav = s['P4_Pa'] / (R * 0.5 * (s['T3_K'] + s['T41_K']))
    om = p['N_rpm'] * 2 * math.pi / 60
    P_brg = sum(bearing_power(p['N_rpm'], b) for b in mech['bearings']) * mech['scale']
    P_wind = (mech['windage_faces'] * mech['windage_Cm'] * 0.5 * rho_cav * om ** 3 * mech['windage_radius_m'] ** 5
              * mech['scale'])
    out['P_bearings (SKF)'] = (P_brg, pw['P_bearings_W'])
    out['P_windage (disc)'] = (P_wind, pw['P_windage_W'])
    net = m_t * w_t - m * wc - P_brg - P_wind
    out['shaft balance P_t - P_c - P_mech, / P_c'] = (net / (m * wc), 0.0)
    # jet pipe and nozzle
    mx = t['mixed_exit']
    q = 0.5 * mx['P_static_Pa'] / (R * mx['T_static_K']) * mx['Ct_m_s'] ** 2
    out['P07 = P05 (1 - jp) - q_swirl'] = (s['P5_Pa'] * (1 - ce['jetpipe_loss']) - q, s['P7_Pa'])
    T07, P07 = s['T7_K'], s['P7_Pa']
    npr = P07 / P0
    g07 = cp(T07, f_mix) / (cp(T07, f_mix) - R)
    npr_crit = ((g07 + 1) / 2) ** (g07 / (g07 - 1))
    choked = npr >= npr_crit
    out['nozzle choked flag'] = (float(choked), float(p['nozzle']['choked']))
    Pe = P0
    T8s = T_isentropic(T07, Pe / P07, f_mix)
    V8 = ce['nozzle_Cv'] * math.sqrt(2 * (h(T07, f_mix) - h(T8s, f_mix)))
    T8 = T_of_h(h(T07, f_mix) - 0.5 * V8 ** 2, f_mix)
    out['V8 [m/s] (unchoked, Cv on velocity)'] = (V8, s['V8_m_s'])
    out['T8 static'] = (T8, s['T8_static_K'])
    m_noz = ce['nozzle_Cd'] * eng['A8_m2'] * Pe / (R * T8) * V8
    out['nozzle mass flow Cd A rho8 V8'] = (m_noz, fl['m_nozzle_kg_s'])
    out['mass residual (m_noz - m_t)/m_t'] = ((m_noz - m_t) / m_t, 0.0)
    out['thrust = m V8 + A8 (P8 - P0)'] = (m_noz * V8 + eng['A8_m2'] * (Pe - P0), p['thrust_N'])
    out['_npr'] = (npr, p['nozzle']['NPR'])
    out['_npr_crit'] = (npr_crit, None)
    out['_losses'] = (dict(inlet=loss_in, duct=duct, comb=comb), ls)
    return out


# ------------------------------------------------------------------ design point, verbose
pt = dpj['point']
res = check_point(pt, 'DP', True)
print(f'\n-- design point {pt["N_rpm"]} rpm')
for k, (a, b) in res.items():
    if k.startswith('_'):
        continue
    if b == 0.0 and ('residual' in k or 'balance' in k):
        rep.cmp(k, a, b, abs_tol=1e-6, note='(absolute)')
    else:
        rep.cmp(k, a, b, tol_pct=0.05)
npr, nprc = res['_npr'][0], res['_npr_crit'][0]
rep.cmp('NPR = P07/P0', npr, res['_npr'][1], tol_pct=1e-6, note=f'critical {nprc:.4f} -> unchoked')
lo, ls = res['_losses']
rep.cmp('ledger inlet loss frac', lo['inlet'], ls['inlet_frac'], tol_pct=0.01)
rep.cmp('ledger duct (turn/deswirl) loss frac', lo['duct'], ls['duct_frac'], tol_pct=0.01)
rep.cmp('ledger combustor loss frac', lo['comb'], ls['combustor_frac'], tol_pct=0.01)

# pressure ledger file: each segment ratio reproduced, each mechanism once
print('\n-- pressure_ledger.csv vs station table (each loss exactly once)')
with open(os.path.join(folder, 'pressure_ledger.csv'), encoding='utf-8') as fh:
    led = list(csv.DictReader(fh))
st = {}
with open(os.path.join(folder, 'station_table.csv'), encoding='utf-8') as fh:
    for row in csv.DictReader(fh):
        st[row['station']] = row
P = {k: float(st[k]['P_total_Pa']) for k in ('0', '2', '3', '31', '4', '41', '5', '7')}
seg_ratio = {'0-2': 1 - P['2'] / P['0'], '3-31': 1 - P['31'] / P['3'], '31-4': 1 - P['4'] / P['31'],
             '4-41': 1 - P['41'] / P['4'], '41-5': 1 - P['5'] / P['41'], '5-7': 1 - P['7'] / P['5']}
for row in led:
    seg = row['segment']
    if row['loss_frac'] == '':
        rep.info(f'ledger {seg} {row["element"][:34]}', 'no entry', row['basis'][:70])
        continue
    rep.cmp(f'ledger {seg} {row["element"][:34]}', float(row['loss_frac']), seg_ratio[seg], tol_pct=1e-6)
chain = P['0'] * (1 - seg_ratio['0-2']) * float(pt['compressor']['PR']) * (1 - seg_ratio['3-31']) * \
    (1 - seg_ratio['31-4']) * (1 - seg_ratio['4-41']) * (1 - seg_ratio['41-5']) * (1 - seg_ratio['5-7'])
rep.cmp('pressure chain P0 -> P07 (product of segments)', chain, P['7'], tol_pct=1e-6)
q_sw = pt['losses']['swirl_head_Pa']
rep.cmp('jet-pipe segment = 0.010 + q_swirl/P05', ce['jetpipe_loss'] + q_sw / P['5'], seg_ratio['5-7'], tol_pct=1e-6)
mstat = {k: float(st[k]['mass_flow_kg_s']) for k in ('2', '3', '31', '4', '41', '5', '7', '8')}
fl = pt['flows']
rep.cmp('station 4 flow = m_comb + m_fuel', fl['m_comb_air_kg_s'] + fl['m_fuel_kg_s'], mstat['4'], tol_pct=1e-9)
rep.cmp('station 41 flow = station 4 + leak', mstat['4'] + fl['m_leak_kg_s'], mstat['41'], tol_pct=1e-9)
rep.cmp('station 31 flow = m_air - leak (combustor feed)', fl['m_air_kg_s'] - fl['m_leak_kg_s'], mstat['31'],
        tol_pct=1e-9)

# ------------------------------------------------------------------ every operating-line speed
print('\n-- operating line: worst relative difference per quantity over all matched speeds')
ol = j('operating_line.json')
worst = {}
for p in ol:
    if not p.get('converged'):
        continue
    r = check_point(p, str(p['N_rpm']), False)
    for k, (a, b) in r.items():
        if k.startswith('_') or b is None:
            continue
        if b == 0.0:
            d = abs(a)
        else:
            d = abs(a - b) / abs(b)
        if d > worst.get(k, (0, None))[0]:
            worst[k] = (d, p['N_rpm'])
        worst.setdefault(k, (d, p['N_rpm']))
for k, (d, n) in worst.items():
    unit = 'abs' if ('residual' in k or 'balance' in k) else 'rel'
    ok = d <= (1e-6 if unit == 'abs' else 5e-4)
    if not ok:
        rep.fail.append('OL ' + k)
    print(f'OL {k:<56} worst {unit} diff {d:.3e} at {n} rpm {"PASS" if ok else "DIFF"}')
print(f'OL speeds checked: {[p["N_rpm"] for p in ol if p.get("converged")]}')

sys.exit(rep.finish())
