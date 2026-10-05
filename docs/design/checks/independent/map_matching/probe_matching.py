"""BEHAVIOUR PROBES of the code under test (core.engine_match / core.robustness screens).

These call the repository solver on purpose. They are NOT the independent reference
(that is match_resolve.py); they test uniqueness, start sensitivity, trend direction
and what actually fails just beyond each reported feasibility boundary.

usage (from repo root):  python <this> [pd1_results_dir]
"""
import json
import math
import sys
import time
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
from core import cases, candidate  # noqa: E402
from core import engine_match as EM  # noqa: E402
from core.robustness import screens, build  # noqa: E402

t0 = time.time()
res = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'docs/design/results/pd1-jm85'
dpj = json.loads((res / 'design_point.json').read_text())
dp = dpj['point']
rob = json.loads((res / 'robustness' / 'robustness.json').read_text())
case = cases.load_case('pd1-jm85')
recs = cases.case_records(case)
eng = candidate.engine_from_case(case, recs, FF_design=dpj['engine']['FF_design'],
                                 FF_duct_design=dpj['engine']['FF_duct_design'])
FAILS = []

print('== P1. distant starts, local Newton-type solve (solve_from_guess), 68 krpm')
for b0, T0g in ((0.02, 700.0), (0.98, 1450.0), (0.05, 1450.0), (0.95, 650.0), (0.5, 1100.0), (0.3, 500.0),
                (0.8, 900.0), (0.8, 1200.0)):
    p = EM.solve_from_guess(eng, 68000, b0, T0g)
    print(f'    start ({b0:.2f}, {T0g:6.0f} K): ' + ('no convergence' if p is None else
          f'beta {p["beta"]:.6f}, T04 {p["T04_K"]:.4f} K'))
    if p is not None and (abs(p['beta'] - dp['beta']) > 1e-6 or abs(p['T04_K'] - dp['T04_K']) > 1e-3):
        FAILS.append(f'different root from {b0},{T0g}')
try:
    EM._evaluate(eng, 68000, 0.8, 1200.0, 288.15, 101325.0)
    print('    reported failed verify_point start (0.8, 1200 K) evaluates normally')
except Exception as ex:  # what made the repository multi-start #2 fail
    print(f'    reported failed verify_point start (0.8, 1200 K) raises {type(ex).__name__}: {ex}')

for N in (68000, 56000):
    print(f'== P2. global scan, n_scan = 41 (repository uses 11/21), {N} rpm')
    r = EM.match_speed(eng, N, n_scan=41)
    br = [b for b in r['branches'] if b.get('converged')]
    sc = [s for s in r['scan'] if s['r_mass'] is not None]
    sign = sum(1 for a, b in zip(sc, sc[1:]) if a['r_mass'] * b['r_mass'] <= 0)
    print(f'    status {r["status"]}; converged branches {len(br)}; r_mass sign changes on the scan {sign}; '
          f'beta with a power balance {len(sc)}/41')
    for b in br:
        print(f'      branch beta {b["beta"]:.6f} T04 {b["T04_K"]:.4f} K')
    fails = sorted({s['failure'].split(':')[-1].strip()[:70] for s in r['scan'] if s['failure']})
    if fails:
        print(f'    scan failures: {fails}')
    if len(br) != 1:
        FAILS.append(f'{N}: {len(br)} branches')

print('== P3. power residual vs T04 at the design beta (fine grid): number of roots')
b = dp['beta']
c = eng.cmap.operate(68000, b, 288.15, 101325.0 * 0.99)
grid = [c['T_out_K'] + 40 + i * (1500 - c['T_out_K'] - 40) / 119 for i in range(120)]
vals = []
for T in grid:
    try:
        vals.append(EM._evaluate(eng, 68000, b, T, 288.15, 101325.0)['r_power'])
    except Exception as ex:
        vals.append(type(ex).__name__)
num = [(T, v) for T, v in zip(grid, vals) if not isinstance(v, str)]
roots = sum(1 for (T1, a), (T2, bb) in zip(num, num[1:]) if a * bb <= 0)
mono = all(bb >= a for (_, a), (_, bb) in zip(num, num[1:]))
bad = sorted({v for v in vals if isinstance(v, str)})
print(f'    {len(num)}/120 feasible T04 points; power-residual roots {roots}; monotone increasing {mono}; '
      f'infeasible types {bad}; feasible T04 range {num[0][0]:.0f}-{num[-1][0]:.0f} K')

print('== P4. trend: nozzle area at 68 krpm (continuation from the design point)')
rows = []
for f in (0.90, 0.95, 1.00, 1.05, 1.10):
    e2 = eng.with_(A8_m2=eng.A8_m2 * f)
    p = EM.solve_from_guess(e2, 68000, dp['beta'], dp['T04_K']) or \
        next((x for x in EM.match_speed(e2, 68000, n_scan=11)['branches'] if x.get('converged')), None)
    rows.append((f, p))
    print(f'    A8 x {f:.2f}: ' + ('no match' if p is None else
          f'T04 {p["T04_K"]:.2f} K, beta {p["beta"]:.4f}, thrust {p["thrust_N"]:.2f} N, '
          f'mdot {p["compressor"]["mdot_kg_s"]:.4f}'))
ok = [(f, p) for f, p in rows if p]
t_dec = all(a[1]['T04_K'] > b[1]['T04_K'] for a, b in zip(ok, ok[1:]))
b_inc = all(a[1]['beta'] < b[1]['beta'] for a, b in zip(ok, ok[1:]))
print(f'    smaller nozzle -> higher T04: {t_dec}; smaller nozzle -> lower beta: {b_inc}')
if not (t_dec and b_inc):
    FAILS.append('nozzle trend')

print('== P5. what actually fails just beyond each reported single-parameter boundary (68 krpm)')
N = 68000
T0n, P0n = 288.15, 101325.0
mk = {
    'NGV effective throat area (smallest feasible)': lambda x: dict(stage=dict(A_ngv_throat_m2=x)),
    'NGV effective throat area (largest feasible)': lambda x: dict(stage=dict(A_ngv_throat_m2=x)),
    'rotor relative throat area (smallest feasible)': lambda x: dict(stage=dict(A_rotor_throat_m2=x)),
    'rotor relative throat area (largest feasible)': lambda x: dict(stage=dict(A_rotor_throat_m2=x)),
    'turbine loss multiplier (largest feasible)': lambda x: dict(stage=dict(loss_scale=x)),
    'compressor efficiency offset (most negative feasible)': lambda x: dict(offsets=dict(eta_delta=x)),
    'combustor loss at design FF (largest feasible)': lambda x: dict(eng=dict(comb_loss_design=x)),
}
for th in rob['thresholds']:
    if 'boundary' not in th:
        print(f'    {th["parameter"]}: {th.get("result")}')
        continue
    x = th['boundary']
    sgn = -1 if th['feasible_side'] == 'high' else 1        # step OUT of the feasible side
    step = 0.03 * abs(x) if abs(x) > 1e-12 else 0.01
    out = []
    for xx in (x - sgn * step, x + sgn * step):
        spec = dict(name='probe', **mk[th['parameter']](xx))
        e2 = build(case, recs, eng, spec, N)
        p = EM.solve_from_guess(e2, N, dp['beta'], dp['T04_K'])
        if p is None:
            r = EM.match_speed(e2, N, n_scan=11)
            p = next((q for q in r['branches'] if q.get('converged')), None)
        out.append((xx, screens(p, 1150.0), None if p is None else p['T04_K']))
    (xi, si, Ti), (xo, so, To) = out
    print(f'    {th["parameter"]}: boundary {x:.6g}; inside {xi:.6g}: {si or "feasible"}'
          + (f' (T04 {Ti:.0f} K)' if Ti else '') + f'; outside {xo:.6g}: {so or "feasible"}'
          + (f' (T04 {To:.0f} K)' if To else '') + f'; table says beyond: "{th["failure_beyond"]}"')

print('== P6. smallest-NGV-throat edge: does the repository model have a root below the reported boundary?')
A_min = next(t['boundary'] for t in rob['thresholds'] if t['parameter'].startswith('NGV effective throat area (smallest'))
for fac in (0.97, 0.94, 0.90):
    e2 = build(case, recs, eng, dict(name='probe', stage=dict(A_ngv_throat_m2=A_min * fac)), N)
    std = EM.match_speed(e2, N, n_scan=11)
    std_ok = [q for q in std['branches'] if q.get('converged')]
    found = []
    for i in range(41):                      # finer outer scan + finer inner T04 grid (n_grid 60 vs 14)
        bb = i / 40
        try:
            T, ev = EM._inner_T04(e2, N, bb, T0n, P0n, n_grid=60)
            found.append((bb, T, ev['r_mass']))
        except Exception:
            pass
    roots = []
    for (b1, T1, r1), (b2, T2, r2) in zip(found, found[1:]):
        if r1 * r2 <= 0:
            g = lambda x: EM._inner_T04(e2, N, x, T0n, P0n, n_grid=60)[1]['r_mass']
            try:
                bs = EM.brentq(g, b1, b2, xtol=1e-10)
                T, ev = EM._inner_T04(e2, N, bs, T0n, P0n, n_grid=60)
                pk = EM._package(e2, N, bs, T, ev, abs(ev['r_mass']) < 1e-6 and abs(ev['r_power']) < 1e-6)
                roots.append((bs, T, pk['turbine']['ngv_flow_fraction_of_max'], screens(pk, 1150.0)))
            except Exception as ex:
                roots.append(('refine failed', str(ex)[:60]))
    print(f'    A_ngv = {fac:.2f} x boundary: standard scan (n_scan 11, inner grid 14) -> '
          f'{"no match: " + str(std.get("reason")) if not std_ok else "match"}; fine scan (41 x 60) roots: {roots}')

print(f'\nelapsed {time.time() - t0:.0f} s; FAILS: {FAILS or "none"}')
sys.exit(1 if FAILS else 0)
