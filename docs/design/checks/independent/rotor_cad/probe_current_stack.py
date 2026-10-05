"""READ-ONLY PROBE (not an independent check): rebuild the stack with the CURRENT core/assembly.py
from the run's own state and compare it with the run's assembly_stack.json.

core/assembly.py was edited at 13:59, after run cf53eecfed2f (13:39-13:49). This shows which
stack outputs that edit changes.  Usage (repo root): python probe_current_stack.py [out/<case>/<fp12>]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, '.')
from core import assembly  # noqa: E402  (probe only)

RUN = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('out') / json.loads(Path('out/pd1-jm85/LATEST.json').read_text())['run_dir'].replace(chr(92), '/')
state = json.loads((RUN / 'state.json').read_text())
state = state.get('state', state)
old = json.loads((RUN / 'assembly_stack.json').read_text())
st = assembly.build_stack(assembly.params_from_state(state))
d_x = {k: (old['stations_m'].get(k), v) for k, v in st['x'].items() if abs(old['stations_m'].get(k, 1e9) - v) > 1e-12}
print('stations changed:', d_x or 'none')
op = {q['id']: q for q in old['parts']}
d_p = [q['id'] for q in st['parts'] if any(abs(q[k] - op[q['id']][k]) > 1e-12 for k in ('x0', 'x1', 'r_in', 'r_out'))]
print('part envelopes changed:', d_p or 'none')
d_s = [s.name for s, o in zip(st['sections'], old['shaft_sections']) if abs(s.od - o['od_m']) > 1e-12 or abs(s.z0 - o['z0_m']) > 1e-12
       or abs(s.length - o['length_m']) > 1e-12]
print('shaft sections changed:', d_s or 'none', '| counts', len(st['sections']), len(old['shaft_sections']))
d_m = [d.name for d, o in zip(st['discs'], old['rotating_masses']) if abs(d.mass - o['mass_kg']) > 1e-15 or abs(d.z - o['x_m']) > 1e-12]
print('rotating masses changed:', d_m or 'none')
oc = {c['name']: c for c in old['checks']}
nc = {c.name: c for c in st['checks']}
for n in sorted(set(oc) | set(nc)):
    a, b = oc.get(n), nc.get(n)
    if a is None:
        print(f'  NEW check     : {n!r} status={b.status} value={b.value}')
    elif b is None:
        print(f'  REMOVED check : {n!r} (was {a["status"]}, value {a["value"]})')
    elif a['status'] != b.status or (a['value'] != b.value and not (a['value'] is None or b.value is None)
                                     and abs(a['value'] - b.value) > 1e-12):
        print(f'  CHANGED check : {n!r} {a["status"]}/{a["value"]} -> {b.status}/{b.value}')
print(f'stack checks: run {len(oc)} -> current {len(nc)}; statuses run '
      f'{sorted((c["status"] for c in old["checks"]))} ')
print('current statuses', sorted(c.status for c in st['checks']))
