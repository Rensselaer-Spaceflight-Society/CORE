"""Fork-B independent compressor-map checks (items 1, 2, 3, 5).

usage (from repo root):  python <this> [pd1_results_dir] [dp2_results_dir]
Defaults: docs/design/results/pd1-jm85 and docs/design/results/dp2-prescribed.
Does not import core.compressor_map / engine_match / thermo / modules.
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import indep_lib as L  # noqa: E402

pd1 = Path(sys.argv[1]) if len(sys.argv) > 1 else L.ROOT / 'docs/design/results/pd1-jm85'
dp2 = Path(sys.argv[2]) if len(sys.argv) > 2 else L.ROOT / 'docs/design/results/dp2-prescribed'
dp = json.loads((pd1 / 'design_point.json').read_text())['point']
line = json.loads((pd1 / 'operating_line.json').read_text())
mc = json.loads((dp2 / 'map_consistency.json').read_text())
mrec = L.yaml.safe_load(open(L.ROOT / 'data/maps/gt3076r_compressor.yaml', encoding='utf-8'))['parameters']

print('== 1. reference conditions and correction direction')
L.compare('T_ref record vs 545 R', mrec['reference_temperature']['value'], L.T_REF_545R, 0.01)
L.compare('P_ref record vs 28.4 inHg', mrec['reference_pressure']['value'], L.P_REF_284INHG, 0.01)
mp = L.Map(T_ref=mrec['reference_temperature']['value'], P_ref=mrec['reference_pressure']['value'])
st, c = dp['stations'], dp['compressor']
L.compare('N_corr = N/sqrt(T2/Tref) at 68 krpm (T2 = T0, adiabatic inlet)', mp.corrected_speed(68000, st['T2_K']),
          c['N_corr_rpm'], 1e-6)
L.compare('Q_corr = mdot sqrt(T2/Tref)/(P2/Pref) with P2 after inlet loss', mp.corrected_flow(c['mdot_kg_s'], st['T2_K'],
          st['P2_Pa']), c['Q_corr_kg_s'], 1e-6)
L.compare('  same with P0 (would be wrong station): Q_corr', mp.corrected_flow(c['mdot_kg_s'], 288.15, 101325.0),
          c['Q_corr_kg_s'], 100, note='informative: station choice moves Q by the inlet loss')
L.compare('inlet loss 0.01 (Q/0.20)^2 at design', 0.01 * (c['Q_corr_kg_s'] / 0.20) ** 2, dp['losses']['inlet_frac'], 1e-4)
L.compare('P03 = P2 * PR', st['P2_Pa'] * c['PR'], st['P3_Pa'], 1e-6)

print('== 2. beta-line interpolation reproduced from the CSV (own code)')


def check_point(tag, pt):
    cc, ss = pt['compressor'], pt['stations']
    N, beta = pt['N_rpm'], pt['beta']
    nc = mp.corrected_speed(N, ss['T2_K'])
    q, pr, eta = mp.point(nc, beta)
    L.compare(f'{tag} Q_corr at reported beta {beta:.6f}', q, cc['Q_corr_kg_s'], 1e-4)
    L.compare(f'{tag} PR', pr, cc['PR'], 1e-4)
    L.compare(f'{tag} eta_c', eta, cc['eta'], 1e-4)
    k = L.compressor(mp, N, beta, ss['T2_K'], ss['P2_Pa'])
    L.compare(f'{tag} mdot (actual)', k['mdot'], cc['mdot_kg_s'], 1e-4)
    L.compare(f'{tag} T03 (own isentrope, quadrature entropy)', k['T3'], cc['T_out_K'], 1e-3)
    L.compare(f'{tag} specific work w_c', k['w'], cc['w_J_kg'], 1e-3)
    L.compare(f'{tag} compressor power mdot*w', k['mdot'] * k['w'], cc['power_W'], 1e-3)
    L.compare(f'{tag} SM_flow = 1 - Q_surge/Q (const N_corr)', k['SM_flow'], cc['SM_flow'], 1e-3)
    qs, prs = mp.point(nc, 0.0)[:2]
    L.compare(f'{tag} SM_pr = (PRs/PR)(Q/Qs) - 1', (prs / pr) * (q / qs) - 1, cc['SM_pr'], 1e-3)
    lo, hi = mp.bracket(nc)
    print(f'    {tag}: N_corr {nc:,.0f} between digitized lines {lo:,.0f} and {hi:,.0f} '
          f'(weight on upper {(nc - lo) / (hi - lo):.3f}); beta {beta:.4f} inside [0,1]')
    # interpolation-scheme sensitivity (not a defect: quantifies digitization/interpolation uncertainty)
    for along, across in (('linear', 'linear'), ('pchip', 'n2')):
        m2 = L.Map(T_ref=mp.T_ref, P_ref=mp.P_ref, along=along, across=across)
        q2, pr2, e2 = m2.point(nc, beta)
        print(f'    {tag}: alt interpolation along={along:6s} across={across:6s}: Q {100 * (q2 / q - 1):+.3f} %, '
              f'PR {100 * (pr2 / pr - 1):+.3f} %, eta {e2 - eta:+.4f}')


check_point('68 krpm DP', dp)
p56 = [p for p in line if isinstance(p, dict) and p.get('N_rpm') == 56000 and 'compressor' in p]
if p56:
    check_point('56 krpm', p56[0])
else:
    L.compare('56 krpm point present in operating_line.json', None, None)

print('== 2b. domain limits (no extrapolation)')
n_lo, n_hi = mp.speeds[0], mp.speeds[-1]
for T in (288.15, 308.15, 268.15):
    print(f'    T0 {T:.2f} K: lowest digitized line {n_lo:,.0f} corrected = {n_lo * math.sqrt(T / mp.T_ref):,.0f} rpm physical; '
          f'highest {n_hi:,.0f} = {n_hi * math.sqrt(T / mp.T_ref):,.0f} rpm physical')
L.compare('lowest line, physical rpm at 288.15 K ("~54.5 krpm")', n_lo * math.sqrt(288.15 / mp.T_ref), 54500, 0.1)
hot56 = mp.corrected_speed(56000, 308.15)
print(f'    56 krpm on a 308.15 K day -> N_corr {hot56:,.0f} < {n_lo:,.0f}: off-map ({hot56 < n_lo}) '
      f'-> robustness "unresolved" rows at 56 krpm hot day / combined adverse are consistent')
for bad in ((n_lo - 1, 0.5), (n_hi + 1, 0.5), (60000, -0.01), (60000, 1.01)):
    try:
        mp.point(*bad)
        print(f'    point{bad}: ACCEPTED (unexpected)')
        L.FAILS.append('domain')
    except L.OffMap:
        print(f'    point{bad}: rejected (expected)')

print('== 3. DP-2 point (0.30 kg/s, PR 1.63, 66 krpm) against the map')
T2, P2 = 288.15, 101325.0 * 0.99
q_dp2 = mp.corrected_flow(0.30, T2, P2)
L.compare('DP-2 corrected flow', q_dp2, mc['corrected_flow_kg_s'], 1e-4)
nc66 = mp.corrected_speed(66000, T2)
qc, prc, ec = mp.point(nc66, 1.0)
print(f'    66 krpm (N_corr {nc66:,.0f}): choke end Q {qc:.4f} kg/s corr = {mp.actual_flow(qc, T2, P2):.4f} kg/s '
      f'physical at PR {prc:.3f}; DP-2 needs {q_dp2:.4f} kg/s corr -> beta {"> 1 (off map)" if q_dp2 > qc else "inside"}')
L.compare('66 krpm choke-end physical flow ("~0.25 kg/s")', mp.actual_flow(qc, T2, P2), 0.25, 1.5)
L.compare('66 krpm choke-end PR ("~1.29")', prc, 1.29, 1.0)
L.compare('code says off map at 66 krpm', 1.0 if isinstance(mc['map_at_prescribed_speed'], str) else 0.0, 1.0, 0)


def pr_at_flow(N):
    nc = mp.corrected_speed(N, T2)
    b = mp.beta_for_q(nc, q_dp2)
    return mp.point(nc, b)[1], b


lo, hi = 75000.0, 100000.0
while True:  # lowest speed where the DP-2 corrected flow lies on the line
    try:
        pr_at_flow(lo)
        break
    except L.OffMap:
        lo += 250
first_on_map = lo
for _ in range(60):  # back off to the exact first speed with Q on the line
    pass
a, b = first_on_map - 250, first_on_map
for _ in range(50):
    m = 0.5 * (a + b)
    try:
        pr_at_flow(m)
        b = m
    except L.OffMap:
        a = m
N_first = b
f = lambda N: pr_at_flow(N)[0] - 1.63
N_pr = L.brentq(f, N_first + 1e-6, 100000.0, xtol=1e-3)
print(f'    0.30 kg/s first on a speed line at {N_first:,.0f} rpm (PR there {pr_at_flow(N_first + 1e-3)[0]:.3f}); '
      f'PR 1.63 reached at 0.30 kg/s at {N_pr:,.0f} rpm (code grid answer: '
      f'{mc["lowest_speed_reaching_prescribed_PR_at_prescribed_flow"]["N_rpm"]:,} rpm)')
L.compare('speed for 0.30 kg/s @ PR 1.63 ("first near 85 krpm")', N_pr, 85000, 2.5, note='code uses a 2.5 krpm grid')
for row in mc['speeds_passing_prescribed_flow'][:4]:
    pr_i, b_i = pr_at_flow(row['N_rpm'])
    L.compare(f'  PR at 0.30 kg/s, {row["N_rpm"]} rpm', pr_i, row['PR'], 1e-3)

print('== 3b. work-coefficient argument (DP-2, 76.13 mm exducer, 66 krpm, eta_c 0.72 prescribed)')
U2 = math.pi * 0.07613 * 66000 / 60
T3s = L.T_isentropic(288.15, 1.63)
dh_is = L.h(T3s) - L.h(288.15)
dh0 = dh_is / 0.72
psi_actual = dh0 / U2 ** 2
L.compare('U2 at 66 krpm, D2 76.13 mm', U2, 263.08639358957004, 1e-6)
L.compare('code value = blade (Euler) coefficient dh0 / (PIF U2^2)', psi_actual / 1.04, mc['implied_work_coefficient'], 0.05)
sig11 = 1 - 0.63 * math.pi / 11
L.compare('Stanitz slip, Z = 11 (1 - 0.63 pi/Z)', sig11, mc['stanitz_slip_76mm_11_blades'], 1e-6)
print(f'    actual total-enthalpy coefficient dh0/U2^2 = {psi_actual:.4f}')
print(f'    Euler (blade) coefficient with the conventional power-input factor (dh0 = PIF * Euler):'
      f' {psi_actual / 1.04:.4f}   (the pre-fix code reported 1.04 x dh0/U2^2 = {1.04 * psi_actual:.4f}: PIF applied in the opposite direction)')
print(f'    Stanitz sigma: Z=11 -> {sig11:.4f}; Z=12 (stock 6+6 counted fully) -> {1 - 0.63 * math.pi / 12:.4f}; '
      f'Z=6 (full blades only) -> {1 - 0.63 * math.pi / 6:.4f}; any backsweep lowers the achievable value further')
eta_cross = L.brentq(lambda eta: (dh_is / eta) / 1.04 / U2 ** 2 - sig11, 0.6, 0.95)
print(f'    required Euler coefficient falls to sigma(11) = {sig11:.3f} at eta_c = {eta_cross:.3f} '
      f'(radial blades, no inlet swirl): the slip argument depends on the assumed 0.72')

print()
print('FAILS:', L.FAILS if L.FAILS else 'none')
sys.exit(1 if L.FAILS else 0)
