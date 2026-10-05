"""PROBE (code under test): mechanism of the missed root below the reported smallest-NGV-throat boundary."""
import json, sys
from pathlib import Path
ROOT = Path.cwd(); sys.path.insert(0, str(ROOT))
from core import cases, candidate
from core import engine_match as EM
from core.robustness import build
res = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'docs/design/results/pd1-jm85'
dpj = json.loads((res / 'design_point.json').read_text())
rob = json.loads((res / 'robustness' / 'robustness.json').read_text())
case = cases.load_case('pd1-jm85'); recs = cases.case_records(case)
eng = candidate.engine_from_case(case, recs, FF_design=dpj['engine']['FF_design'], FF_duct_design=dpj['engine']['FF_duct_design'])
A_min = next(t['boundary'] for t in rob['thresholds'] if t['parameter'].startswith('NGV effective throat area (smallest'))
e2 = build(case, recs, eng, dict(name='probe', stage=dict(A_ngv_throat_m2=0.90 * A_min)), 68000)
for n in (14, 30, 60):
    try:
        T, ev = EM._inner_T04(e2, 68000, 0.2876, 288.15, 101325.0, n_grid=n)
        print(f'inner T04 solve at beta 0.2876, n_grid {n}: T04 {T:.2f} K, r_mass {ev["r_mass"]:+.3e}')
    except Exception as ex:
        print(f'inner T04 solve at beta 0.2876, n_grid {n}: {type(ex).__name__}: {ex}')
r = EM.match_speed(e2, 68000, n_scan=11)
print('match_speed status:', r['status'], '| reason:', r.get('reason'), '| branches:',
      [(b.get('converged'), b.get('reason', '')[:90]) for b in r['branches']])
c = eng.cmap.operate(68000, 0.2876, 288.15, 101325.0 * 0.99)
lo = c['T_out_K'] + 40
for T in [lo + (1500 - lo) * i / 13 for i in range(14)]:
    try:
        print(f'  T04 {T:7.1f} K: r_power {EM._evaluate(e2, 68000, 0.2876, T, 288.15, 101325.0)["r_power"]:+.4f}')
    except Exception as ex:
        print(f'  T04 {T:7.1f} K: {type(ex).__name__}')
