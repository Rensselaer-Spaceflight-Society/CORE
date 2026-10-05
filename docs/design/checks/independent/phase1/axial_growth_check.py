"""R6 hand check: NGV-trailing-edge to rotor-leading-edge axial gap change and rear-bearing float.

Run from the repository root:  python docs/design/checks/independent/phase1/axial_growth_check.py [results_dir]
Default results_dir: docs/design/results/pd1-jm85. Reads assembly_stack.json and clearances.json only;
does not import core.assembly. Exit 1 if the repository numbers differ from the restated formula by > 1 %.

Load paths (cold stack, x aft from the compressor backface):
  rotor : located axially by the FRONT bearing (BR-01 at fb_c); the shaft carries the turbine aft.
  NGV   : located by the casing (CS-01 from casing_front) -> rear cover CS-02 -> NGV flange front face;
          the vane trailing edge sits one axial gap AHEAD of that flange face, inside the hot casting.
The repository formula takes the casing straight from casing_front to the NGV TE at the casing temperature
and the shaft from fb_c to the wheel centre. The stack-faithful path below adds the return through the hot
NGV casting and uses the rotor leading edge; the backplate (aluminium) path to the front bearing is added as
a bound. Temperatures and expansion coefficients are those stated in clearances.json / materials.yaml.
"""
import json
import sys
from pathlib import Path

folder = Path(sys.argv[1] if len(sys.argv) > 1 else 'docs/design/results/pd1-jm85')
stack = json.loads((folder / 'assembly_stack.json').read_text())
clr = json.loads((folder / 'clearances.json').read_text())
x = stack['stations_m']
T = clr['assumed_temperatures_K']
ax = clr['axial']
a_shaft, a_316, a_ngv, a_al = 12.3e-6, 18.0e-6, 16.0e-6, 23.6e-6   # 4140, 316 mean to 900 K, NGV record, 6061
dT_shaft, dT_cas = T['shaft_mean'] - 293.0, T['casing'] - 293.0
dT_ngv = T['ngv_shroud'] - 293.0                       # hot casting near the vanes (stated shroud temperature)

fails = []


def cmp(name, mine, repo, tol=0.01):
    d = abs(mine / repo - 1) if repo else abs(mine)
    ok = d <= tol
    print(f'{name:58s} independent {mine: .4e}  repository {repo: .4e}  diff {100 * d:6.3f} %  {"PASS" if ok else "DIFF"}')
    if not ok:
        fails.append(name)


# 1. restated repository formula
rotor = a_shaft * (x['tw_c'] - x['fb_c']) * dT_shaft
ngv = a_316 * (x['ngv_te'] - x['casing_front']) * dT_cas
cmp('rotor aft growth (shaft fb_c -> wheel centre)', rotor, ax['rotor_aft_growth_m'])
cmp('NGV aft growth (casing casing_front -> NGV TE)', ngv, ax['ngv_aft_growth_m'])
cmp('NGV-rotor gap change (positive = opens)', rotor - ngv, ax['ngv_rotor_gap_change_m'])
rb = a_shaft * (x['rb_c'] - x['fb_c']) * dT_shaft - ngv
cmp('rear bearing float demand', rb, ax['rear_bearing_float_m'])

# 2. stack-faithful path (information)
rotor_le = a_shaft * (x['rotor_le'] - x['fb_c']) * dT_shaft
casing = a_316 * (x['casing_rear_cover'] - x['casing_front']) * dT_cas
cover = a_316 * (x['ngv_flange_front'] - x['casing_rear_cover']) * dT_cas
ngv_return = -a_ngv * (x['ngv_flange_front'] - x['ngv_te']) * dT_ngv
backplate = a_al * (x['fb_c'] - x['casing_front']) * (T['casing'] - 293.0)
gap = rotor_le + backplate - (casing + cover + ngv_return)
print(f'\nstack-faithful gap change: rotor LE {rotor_le:.3e} + backplate {backplate:.3e} - (casing {casing:.3e} '
      f'+ cover {cover:.3e} + NGV return {ngv_return:.3e}) = {gap * 1e6:+.0f} um (repository {ax["ngv_rotor_gap_change_m"] * 1e6:+.0f} um)')
carrier = -a_316 * (x['ngv_te'] - x['rb_c']) * (0.5 * (T['ngv_shroud'] + T['tunnel_mean']) - 293.0)
print(f'rear-bearing float if BC-02 is held at the NGV and grows forward to the bearing: '
      f'{(a_shaft * (x["rb_c"] - x["fb_c"]) * dT_shaft - (casing + cover + ngv_return + carrier)) * 1e6:.0f} um '
      f'(repository {ax["rear_bearing_float_m"] * 1e6:.0f} um; spring travel 500 um). The carrier support path is open (R9).')
print('sign: shaft grows aft more than the cool casing locates the NGV -> the gap OPENS; '
      'a hotter casing than shaft would close it.')
print('FAILS:', fails or 'none')
sys.exit(1 if fails else 0)
