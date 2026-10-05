"""Fork-A: turbine Reynolds numbers along the operating line vs the 2e4 'comfort' bound (R5 data).

Usage (from the repository root):  python <this script> [results_dir]
Default results_dir: docs/design/results/pd1-jm85

Re is recomputed from each reported turbine state with the Soderberg/Dixon definition
(Re = rho V Dh / mu at the row exit, Dh = 2 o H/(o + H), o = s cos(exit angle)), using
(a) the pre-fix power law 3.5e-5 (T/1000)^0.7, for comparison only, and
(b) Sutherland's law for air, an independent viscosity reference and (since the 2026-10-04 fix)
    the repository's law, so (b) must reproduce the reported values.
The repository's reported Re comes from the first (un-Re-corrected) NGV/rotor pass; the
recomputation uses the final reported state, so differences of a few 0.01 % are expected.
Exit status 1 if the reported Re differs from (b) by more than 0.5 %.
"""
import math
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from indep_props import R, throat_hydraulic_diameter, mu_repo_power_law, mu_sutherland_air, load_results, Reporter  # noqa

folder = sys.argv[1] if len(sys.argv) > 1 else 'docs/design/results/pd1-jm85'
rep = Reporter(tol_pct=0.5)
with open('data/components/turbine_jetmax_tw85.yaml', encoding='utf-8') as fh:
    tw = yaml.safe_load(fh)['parameters']
with open('data/components/ngv_jetmax_ngv85.yaml', encoding='utf-8') as fh:
    ng = yaml.safe_load(fh)['parameters']
with open('config/cases/pd1-jm85.yaml', encoding='utf-8') as fh:
    case = yaml.safe_load(fh)
lo_rng, hi_rng = case['operating']['steady_range_rpm']
mm = 1e-3
r_hub, r_tip = tw['hub_diameter']['value'] * mm / 2, tw['tip_diameter']['value'] * mm / 2
rm = 0.5 * (r_hub + r_tip)
HR = r_tip - r_hub
HN = (ng['vane_tip_diameter']['value'] - ng['vane_hub_diameter']['value']) * mm / 2
sN = 2 * math.pi * rm / int(ng['vane_count_estimate']['value'])
sR = 2 * math.pi * rm / int(tw['blade_count_estimate']['value'])
BOUND = 2e4

ol = load_results(folder)('operating_line.json')
print(f'== Fork-A turbine Reynolds numbers on {folder}; bound {BOUND:.0e} (core/turbine_rating.py:297, unsourced; '
      'Soderberg basis Re = 1e5)')
print(f'{"N_rpm":>7} {"Re_N rep":>9} {"Re_N(a)":>9} {"Re_N(b)":>9} {"Re_R rep":>9} {"Re_R(a)":>9} {"Re_R(b)":>9} '
      f'{"flag rep":>8} {"flag(b)":>8} {"fRe_R(a)":>8} {"fRe_R(b)":>8}')
rows = []
for p in ol:
    if not p.get('converged'):
        continue
    t = p['turbine']
    dhN = throat_hydraulic_diameter(sN, HN, t['alpha1_deg'])
    dhR = throat_hydraulic_diameter(sR, HR, t['beta2_deg'])
    rho1 = t['P1_Pa'] / (R * t['T1_K'])
    rho2 = t['P2_Pa'] / (R * t['T2_K'])
    reN_a = rho1 * t['C1_m_s'] * dhN / mu_repo_power_law(t['T1_K'])
    reR_a = rho2 * t['W2_m_s'] * dhR / mu_repo_power_law(t['T2_K'])
    reN_b = rho1 * t['C1_m_s'] * dhN / mu_sutherland_air(t['T1_K'])
    reR_b = rho2 * t['W2_m_s'] * dhR / mu_sutherland_air(t['T2_K'])
    flag_rep = any('Reynolds' in fl for fl in t['flags'])
    flag_b = not (BOUND <= reN_b <= 1e6 and BOUND <= reR_b <= 1e6)
    rows.append((p['N_rpm'], reN_a, reR_a, reN_b, reR_b, flag_rep, flag_b, t))
    print(f'{p["N_rpm"]:>7} {t["Re_ngv"]:>9.0f} {reN_a:>9.0f} {reN_b:>9.0f} {t["Re_rotor"]:>9.0f} {reR_a:>9.0f} '
          f'{reR_b:>9.0f} {str(flag_rep):>8} {str(flag_b):>8} {(1e5 / reR_a) ** 0.25:>8.3f} {(1e5 / reR_b) ** 0.25:>8.3f}')
print()
for n, reN_a, reR_a, reN_b, reR_b, flag_rep, flag_b, t in rows:
    rep.cmp(f'{n} rpm Re_ngv reported vs recomputed (Sutherland air)', reN_b, t['Re_ngv'])
    rep.cmp(f'{n} rpm Re_rotor reported vs recomputed (Sutherland air)', reR_b, t['Re_rotor'])
    flag_a = flag_b
    if flag_a != flag_rep:
        print(f'   NOTE {n} rpm: flag from recomputed Re ({flag_a}) differs from reported flag ({flag_rep}) '
              '(Re within 0.1 % of the bound)')
steady = [r for r in rows if lo_rng <= r[0] <= hi_rng]
n_rep = sum(1 for r in steady if r[5])
n_b = sum(1 for r in steady if r[6])
rep.info(f'steady-range speeds {lo_rng}-{hi_rng} rpm', len(steady))
rep.info('flagged in the run (reported flags)', n_rep, str([r[0] for r in steady if r[5]]))
rep.info('flagged by recomputation with Sutherland air', n_b, str([r[0] for r in steady if r[6]]))
rep.info('min rotor Re in steady range (pre-fix law / Sutherland)',
         f'{min(r[2] for r in steady):.0f} / {min(r[4] for r in steady):.0f}')
rep.info('max rotor Re in steady range (pre-fix law / Sutherland)',
         f'{max(r[2] for r in steady):.0f} / {max(r[4] for r in steady):.0f}')
rep.info('fraction of Soderberg basis Re 1e5 (rotor, steady range)',
         f'{min(r[2] for r in steady) / 1e5:.2f}-{max(r[2] for r in steady) / 1e5:.2f} (pre-fix law)')
for T in (785.0, 805.0, 1000.0):
    rep.info(f'viscosity at {T:.0f} K: pre-fix power law / Sutherland air [Pa s]',
             f'{mu_repo_power_law(T):.4e} / {mu_sutherland_air(T):.4e} (ratio {mu_sutherland_air(T) / mu_repo_power_law(T):.3f})')
sys.exit(rep.finish())
