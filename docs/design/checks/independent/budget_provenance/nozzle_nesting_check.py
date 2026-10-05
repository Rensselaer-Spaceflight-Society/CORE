"""Independent flat-pattern check behind savings option SV3 (nest the exhaust nozzle on the C01 remainder).

Run from the repository root:  python <this file> [run_output_folder]   (default docs/design/results/pd1-jm85)
Reads nozzle.json (contour) and bom/cost_summary.json (remainder strip from the run's C01 shelf packing).
Does not import core/ or modules/. Same 10 mm seam/kerf allowance as the run's nesting note.
"""
import json
import math
import sys
from pathlib import Path

RUN = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('docs/design/results/pd1-jm85')
noz = json.loads((RUN / 'nozzle.json').read_text(encoding='utf-8'))
cs = json.loads((RUN / 'bom/cost_summary.json').read_text(encoding='utf-8'))
W, H = cs['sheet_nesting']['remainder_strip_mm']
pts = noz['points']
r1, r2 = pts[0]['r_outer_m'] * 1e3, pts[-1]['r_outer_m'] * 1e3
L = (pts[-1]['x_m'] - pts[0]['x_m']) * 1e3
tail = [p for p in pts if p['r_tailcone_m'] > 0] + [next(p for p in pts if p['r_tailcone_m'] == 0)]
rt, Lt = tail[0]['r_tailcone_m'] * 1e3, (tail[-1]['x_m'] - tail[0]['x_m']) * 1e3


def frustum_box(ra, rb, length):
    a = math.atan((ra - rb) / length)
    Ro, Ri = ra / math.sin(a), rb / math.sin(a)
    th = 2 * math.pi * math.sin(a)
    if th <= math.pi:
        return 2 * Ro * math.sin(th / 2), Ro - Ri * math.cos(th / 2), math.degrees(a), math.degrees(th)
    return 2 * Ro, Ro * (1 - math.cos(th / 2)), math.degrees(a), math.degrees(th)


def cone_box(r, h):
    s = math.hypot(r, h)
    th = 2 * math.pi * r / s
    if th <= math.pi:
        return 2 * s * math.sin(th / 2), s, math.degrees(th)
    return 2 * s, s * (1 - math.cos(th / 2)), math.degrees(th)


wc, hc, half, th = frustum_box(r1, r2, L)
wt, ht, tht = cone_box(rt, Lt)
print(f'nozzle shell: r {r1:.2f} -> {r2:.2f} mm over {L:.1f} mm, half-angle {half:.2f} deg (nozzle.json {noz["half_angle_deg"]:.2f})')
print(f'  developed sector {th:.1f} deg, bounding box {wc:.1f} x {hc:.1f} mm (+10 mm allowance: {wc+10:.1f} x {hc+10:.1f})')
print(f'tailcone: r {rt:.1f} mm over {Lt:.1f} mm, developed sector {tht:.0f} deg, box {wt:.1f} x {ht:.1f} mm (+10: {wt+10:.1f} x {ht+10:.1f})')
print(f'C01 remainder strip from run: {W:.1f} x {H:.1f} mm')
fits = (wc + 10) + (wt + 10) <= W and max(hc, ht) + 10 <= H
print(f'main nozzle shell + tailcone side by side in the strip | {fits} | - | - | {"PASS" if fits else "FINDING"}')
# spare liner set (outer + inner wraps and both cones) from the run's own part list
parts = {p['part']: p for p in cs['sheet_nesting']['parts']}
liner_w = parts['outer liner wrap']['w_mm'] + parts['inner liner wrap']['w_mm']
liner_h = parts['outer liner wrap']['h_mm'] + parts['outer transition cone (developed)']['h_mm']
both = liner_h + max(hc, ht) + 10 <= H
print(f'spare liner set needs about {liner_w:.0f} x {liner_h:.0f} mm; liner set AND nozzle in the strip | {both} | - | - | INFO (doc: "not both")')
sys.exit(0)
