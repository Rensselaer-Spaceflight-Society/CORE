"""Independent audit of the PD-1 assembly stack, cross-section figure and CAD bundle (fork D).

Does NOT import core.* or modules.*.  Re-derives every axial station by hand from the
versioned records (data/components/*.yaml, config/cases/pd1-jm85.yaml) plus the one
combustor output the stack consumes (cold liner length), then:
  1. compares the stations with assembly_stack.json and the CAD bundle sections;
  2. screens every pair of part envelopes for overlaps, static/rotating clashes and
     invalid envelopes, and checks the rotating clamp stack is contiguous;
  3. reads figures/cross_section.svg back into millimetres (axis ticks) and compares
     the drawn rectangles/shaft with the stack, listing what the figure hides;
  4. audits the CAD bundle: totals and status counts, unit policy, unresolved values,
     purchased values traced to records and to the supplier drawings, naming, interfaces.
Usage (repo root): python stack_cad_audit.py [run_or_snapshot_folder]
Exit 1 on any unexplained numeric difference (> 1e-6 mm for stations).
"""
import collections
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

RUN = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('docs/design/results/pd1-jm85')
fails, flags = [], []


def rec(name):
    return yaml.safe_load(Path(f'data/components/{name}.yaml').read_text())


def val(r, key):
    return r['parameters'][key]['value']


asm, cmp_, brg = rec('assembly_pd1'), rec('compressor_gt3076r_56trim'), rec('bearings_candidate')
tw, ngv = rec('turbine_jetmax_tw85'), rec('ngv_jetmax_ngv85')
case = yaml.safe_load(Path('config/cases/pd1-jm85.yaml').read_text())
stack = json.loads((RUN / 'assembly_stack.json').read_text())
bundle = json.loads((RUN / 'cad' / 'cad_bundle.json').read_text())
P = {p['name']: p for p in bundle['parameters']}
X = stack['stations_m']

# ------------------------------------------------------------------ 1. stations by hand (mm)
liner_len = P['CB_LINER_LENGTH']['value']          # combustor (M20) output consumed by the stack
h = {}
h['cw_backface'] = 0.0
h['cw_nose'] = -val(cmp_, 'backface_to_nose_length_envelope')
h['shaft_front'] = h['cw_nose'] - val(asm, 'front_thread_length')
h['comp_nut_front'] = h['cw_nose'] - val(asm, 'compressor_nut_length')
h['diffuser_floor'] = -val(cmp_, 'super_back_height')
h['diffuser_cover'] = h['diffuser_floor'] - case['diffuser']['channel_width_m'] * 1e3
h['backplate_rear'] = val(asm, 'backplate_rear_face_x')
h['fb_front'] = h['backplate_rear'] + val(asm, 'front_bearing_gap_to_backplate') - val(asm, 'front_bearing_recess')
h['fb_rear'] = h['fb_front'] + val(brg, 'width')
h['fb_c'] = 0.5 * (h['fb_front'] + h['fb_rear'])
h['dome'] = h['backplate_rear'] + val(asm, 'plenum_gap')
h['liner_end'] = h['dome'] + liner_len
h['ngv_front'] = h['liner_end'] + val(asm, 'transition_length')
h['rotor_le'] = h['ngv_front'] + val(ngv, 'vane_ring_height_blank')
h['ngv_te'] = h['rotor_le'] - val(asm, 'ngv_rotor_axial_gap')
h['ngv_le'] = h['ngv_te'] - val(ngv, 'vane_axial_chord')
h['rotor_te'] = h['rotor_le'] + val(tw, 'blade_axial_width_at_rim')
h['tw_c'] = 0.5 * (h['rotor_le'] + h['rotor_te'])
h['boss_front'] = h['rotor_le'] - val(tw, 'hub_boss_protrusion_side_a')
h['boss_rear'] = h['boss_front'] + val(tw, 'hub_boss_total_length')
h['rs_front'] = h['boss_front'] - val(asm, 'rear_spacer_length')
h['rb_rear'] = h['rs_front']
h['rb_front'] = h['rb_rear'] - val(brg, 'width')
h['rb_c'] = 0.5 * (h['rb_front'] + h['rb_rear'])
h['shaft_rear'] = h['boss_rear'] + val(asm, 'rear_thread_length')
h['ngv_ring_rear'] = h['ngv_front'] + val(ngv, 'overall_height_blank')
h['casing_front'] = h['diffuser_floor']
h['ngv_flange_front'] = h['ngv_front'] + val(ngv, 'vane_ring_height_blank')
h['casing_rear_cover'] = h['ngv_flange_front'] - val(asm, 'casing_wall_stock')
h['nozzle_entry'] = max(h['rotor_te'] + 2.0, h['ngv_ring_rear'])
h['nozzle_exit'] = h['nozzle_entry'] + val(asm, 'nozzle_length')
h['inlet_lip'] = h['cw_nose'] - 8.0 - val(asm, 'bellmouth_length')
h['cw_cg'] = -val(cmp_, 'cg_from_backface_estimate')
print(f'run folder {RUN}; cold liner length taken from the run (M20): {liner_len:.6f} mm')
print('\n[1] axial stations re-derived from the records (mm)')
for k, v in h.items():
    rv = X[k] * 1e3
    bv = bundle['sections']['stations_mm'].get(k)
    ok = abs(v - rv) < 1e-6 and (bv is None or abs(bv - rv) < 1e-6)
    if not ok:
        fails.append(f'station {k}')
    print(f'  {k:<18} hand={v:11.5f} stack={rv:11.5f} bundle={bv if bv is None else round(bv, 5)!s:>11} {"PASS" if ok else "DIFF"}')
missing = set(X) - set(h)
if missing:
    print('  stations not re-derived:', sorted(missing))
order = ['inlet_lip', 'shaft_front', 'comp_nut_front', 'cw_nose', 'diffuser_cover', 'diffuser_floor', 'cw_backface',
         'fb_front', 'fb_c', 'backplate_rear', 'fb_rear', 'dome', 'liner_end', 'ngv_front', 'rb_c', 'ngv_le', 'rb_rear',
         'boss_front', 'ngv_te', 'casing_rear_cover', 'rotor_le', 'tw_c', 'rotor_te', 'boss_rear', 'ngv_ring_rear',
         'shaft_rear', 'nozzle_exit']
mono = all(X[a] <= X[b] + 1e-12 for a, b in zip(order, order[1:]))
print(f'  gas-path ordering monotonic: {mono}')
if not mono:
    fails.append('station ordering')
summ = stack['summary']
for k, v in (('bearing_span_m', h['rb_c'] - h['fb_c']), ('comp_overhang_m', h['fb_c'] - h['cw_cg']),
             ('turb_overhang_m', h['tw_c'] - h['rb_c']), ('shaft_length_m', h['shaft_rear'] - h['shaft_front']),
             ('engine_length_m', h['nozzle_exit'] - h['inlet_lip'])):
    ok = abs(v - summ[k] * 1e3) < 1e-6
    print(f'  {k:<18} hand={v:9.4f} stack={summ[k] * 1e3:9.4f} {"PASS" if ok else "DIFF"}')
    if not ok:
        fails.append(k)

# ------------------------------------------------------------------ 2. envelopes, clamp stack, clashes
print('\n[2] part envelopes (stack boxes x0..x1, r_in..r_out, mm)')
parts = {q['id']: q for q in stack['parts']}
mm = lambda v: v * 1e3
for q in stack['parts']:
    if q['r_in'] > q['r_out'] + 1e-12 or q['x0'] > q['x1'] + 1e-12:
        flags.append(f"{q['id']} envelope inverted: r_in {mm(q['r_in']):.2f} > r_out {mm(q['r_out']):.2f} mm")
        print(f"  INVALID ENVELOPE {q['id']} ({q['name']}): r_in {mm(q['r_in']):.3f} > r_out {mm(q['r_out']):.3f} mm")
ids = list(parts)
ov = []
for i, a in enumerate(ids):
    for b in ids[i + 1:]:
        A, B = parts[a], parts[b]
        dx = min(A['x1'], B['x1']) - max(A['x0'], B['x0'])
        lo_a, hi_a = sorted((A['r_in'], A['r_out']))
        lo_b, hi_b = sorted((B['r_in'], B['r_out']))
        dr = min(hi_a, hi_b) - max(lo_a, lo_b)
        if dx > 1e-6 and dr > 1e-6:
            ov.append((a, b, mm(dx), mm(dr), A['rotating'] != B['rotating']))
known = {  # (pair) -> explanation; anything else is listed as unexplained
    ('CH-01', 'CW-01'): 'box artefact: shroud follows the blade tip contour (contour unresolved)',
    ('IN-01', 'CH-01'): 'n/a',
    ('DF-01', 'BC-01'): 'sleeve sits in the backplate pocket (pocket diameter not defined in bundle; see [3])',
    ('DF-01', 'BR-01'): 'bearing inside backplate pocket',
    ('BC-01', 'BR-01'): 'bearing in sleeve',
    ('BC-02', 'BR-02'): 'bearing in carrier',
    ('NG-01', 'TR-01'): 'box artefact: rotor runs inside the 85.7 mm shroud bore of the casting',
    ('BC-02', 'TR-01'): 'box artefact: 14 mm boss inside the 26 mm carrier bore; disc starts 2 mm aft of carrier',
    ('NG-01', 'CS-02'): 'box artefact: cover sits on the 92 mm outer ring ahead of the 104 mm flange',
    ('CB-01', 'CB-02'): 'dome joins liner', ('CB-01', 'CB-03'): 'dome joins liner',
    ('SH-01', 'CW-01'): 'wheel on shaft', ('SH-01', 'TR-01'): 'wheel on shaft', ('SH-01', 'BR-01'): 'journal',
    ('SH-01', 'BR-02'): 'journal', ('SH-01', 'DF-01'): 'shaft through backplate seal bore',
    ('SH-01', 'BC-01'): 'shaft inside sleeve bore', ('SH-01', 'BC-02'): 'shaft inside carrier bore',
    ('SH-01', 'NG-01'): 'shaft inside casting hub (web removal unresolved, R9)',
    ('SH-01', 'CH-01'): 'shaft nose inside housing inlet', ('SH-01', 'IN-01'): 'n/a',
    ('CW-01', 'DF-01'): 'box artefact: DF-01 box starts at the diffuser-cover plane; under the wheel the backplate face '
                        'is at x = +0.4 mm (figure polygon / IF-CW-DF)',
    ('EX-01', 'EX-02'): 'box artefact: EX-01 box r_in is the exit radius; the wall is at r 42.85 at the tailcone base',
}
for a, b, dx, dr, mixed in ov:
    key = (a, b) if (a, b) in known else (b, a)
    why = known.get(key)
    kind = 'STATIC/ROTATING' if mixed else 'static/static'
    tag = 'explained' if why else 'UNEXPLAINED'
    if not why:
        flags.append(f'envelope overlap {a}/{b}: {dx:.3f} mm axial x {dr:.3f} mm radial ({kind})')
    print(f'  overlap {a:<6}/{b:<6} axial {dx:7.3f} radial {dr:7.3f} mm  {kind:<15} {tag}: {why or ""}')
# rotating parts not in the parts list (nut/spacer/sleeve) against static envelopes
rot_extra = {
    'compressor nut': (h['comp_nut_front'], h['cw_nose'], 0.0, 5.0),
    'turbine nut': (h['boss_rear'], h['boss_rear'] + val(asm, 'turbine_nut_length'), 0.0, 6.5),
    'shaft rear thread end': (h['boss_rear'], h['shaft_rear'], 0.0, val(asm, 'shaft_rear_thread_d') / 2),
    'rear spacer': (h['rs_front'], h['boss_front'], 5.0, val(asm, 'rear_spacer_od') / 2),
    'front seal sleeve': (0.0, h['fb_front'], 3.0, val(asm, 'front_sleeve_od') / 2),
}
for name, (x0, x1, ri, ro) in rot_extra.items():
    for q in stack['parts']:
        if q['rotating'] or q['id'] in ('BR-01', 'BR-02'):
            continue
        dx = min(x1, mm(q['x1'])) - max(x0, mm(q['x0']))
        lo, hi = sorted((mm(q['r_in']), mm(q['r_out'])))
        dr = min(ro, hi) - max(ri, lo)
        if dx > 1e-6 and dr > 1e-6:
            flags.append(f'rotating {name} overlaps static {q["id"]} envelope ({dx:.2f} mm axial x {dr:.2f} mm radial)')
            print(f'  ROTATING {name:<22} vs static {q["id"]:<6} overlap axial {dx:6.3f} radial {dr:6.3f} mm  (no check covers this)')
# clamp stack contiguity (rotating, axial)
seq = [('compressor nut', h['comp_nut_front'], h['cw_nose']), ('compressor wheel', h['cw_nose'], 0.0),
       ('seal sleeve', 0.0, h['fb_front']), ('front bearing', h['fb_front'], h['fb_rear'])]
seq2 = [('rear bearing', h['rb_front'], h['rb_rear']), ('rear spacer', h['rs_front'], h['boss_front']),
        ('turbine boss', h['boss_front'], h['boss_rear']), ('turbine nut', h['boss_rear'], h['boss_rear'] + val(asm, 'turbine_nut_length'))]
for s in (seq, seq2):
    gaps = [round(b[1] - a[2], 9) for a, b in zip(s, s[1:])]
    print(f'  clamp stack {s[0][0]} -> {s[-1][0]}: interface gaps {gaps} mm  {"PASS" if all(abs(g) < 1e-9 for g in gaps) else "DIFF"}')
body = [q for q in stack['shaft_sections'] if q['name'] == 'body'][0]
print(f'  shoulders: body {mm(body["z0_m"]):.4f}..{mm(body["z0_m"] + body["length_m"]):.4f} mm vs front bearing rear face '
      f'{h["fb_rear"]:.4f} and rear bearing front face {h["rb_front"]:.4f}')
sh = mm(parts['EX-02']['x0'])
print(f'  aft rotating-to-static axial gaps: boss rear face {h["boss_rear"]:.3f} -> tailcone/nozzle plane {sh:.3f} = '
      f'{sh - h["boss_rear"]:.3f} mm; disc rear face {h["rotor_te"]:.3f} -> {sh:.3f} = {sh - h["rotor_te"]:.3f} mm; '
      f'nut ends {h["boss_rear"] + val(asm, "turbine_nut_length"):.3f}, shaft ends {h["shaft_rear"]:.3f}')
# tunnel / rear carrier slip joint geometry
tu, bc2 = parts['TU-01'], parts['BC-02']
print(f'  TU-01 ID {2 * mm(tu["r_in"]):.3f} mm, x {mm(tu["x0"]):.3f}..{mm(tu["x1"]):.3f}; BC-02 envelope OD {2 * mm(bc2["r_out"]):.3f} mm, '
      f'x {mm(bc2["x0"]):.3f}..{mm(bc2["x1"]):.3f}; overlap {mm(tu["x1"] - bc2["x0"]):.3f} mm long, '
      f'{mm(bc2["r_out"] - tu["r_in"]):.3f} mm radial interference')
chk = {c['name']: c for c in stack['checks']}
c_tun = chk.get('tunnel ID clears bearing carrier wall')
if c_tun:
    print(f'  check "tunnel ID clears bearing carrier wall" uses carrier OD {c_tun["value"] * 1e3:.1f} mm, not the {2 * mm(bc2["r_out"]):.1f} mm envelope')

# ------------------------------------------------------------------ 3. the figure, read back in mm
print('\n[3] cross_section.svg read back (axis ticks -> mm)')
svg_path = RUN / 'figures' / 'cross_section.svg'
txt = svg_path.read_text(encoding='utf-8')


def ticks(kind):
    out = []
    for m in re.finditer(rf'<g id="{kind}_\d+">(.*?)</g>\s*</g>\s*<g id="text_\d+">\s*<!-- (.*?) -->', txt, re.S):
        u = re.search(r'<use [^>]*x="([-\d.]+)" y="([-\d.]+)"', m.group(1))
        out.append((float(m.group(2).replace('−', '-')), float(u.group(1)), float(u.group(2))))
    return out


xt, yt = ticks('xtick'), ticks('ytick')
(xa, pxa, _), (xb, pxb, _) = xt[0], xt[-1]
(ra, _, pya), (rb, _, pyb) = yt[0], yt[-1]
sx = (pxb - pxa) / (xb - xa)
sy = (pyb - pya) / (rb - ra)
to_mm = lambda px, py: ((px - pxa) / sx + xa, (py - pya) / sy + ra)
print(f'  scale x {sx:.6f} px/mm, r {sy:.6f} px/mm (aspect equal: {abs(abs(sx) - abs(sy)) < 1e-6})')
ns = {'s': 'http://www.w3.org/2000/svg', 'x': 'http://www.w3.org/1999/xlink'}
root = ET.fromstring(txt)
drawn = []
for g in root.iter('{http://www.w3.org/2000/svg}g'):
    gid = g.get('id', '')
    if not gid.startswith('patch_'):
        continue
    pth = g.find('s:path', ns)
    if pth is None:
        continue
    nums = [float(v) for v in re.findall(r'[-\d.]+', pth.get('d'))]
    pts = [to_mm(nums[i], nums[i + 1]) for i in range(0, len(nums) - 1, 2)]
    xs_, rs_ = [p[0] for p in pts], [p[1] for p in pts]
    drawn.append((int(gid.split('_')[1]), min(xs_), max(xs_), min(rs_), max(rs_), len(pts), pth.get('style', '')))
rect_parts = [q for q in stack['parts'] if q['id'] not in ('CB-04', 'CB-05', 'EX-01', 'EX-02', 'SH-01', 'CW-01', 'TR-01', 'CH-01', 'DF-01')]
for q in rect_parts:
    tgt = (mm(q['x0']), mm(q['x1']), mm(q['r_in']), mm(q['r_out']))
    hit = [d for d in drawn if all(abs(a - b) < 0.02 for a, b in zip(d[1:5], tgt))]
    print(f'  {q["id"]:<6} drawn as stack box: {"yes (patch_%d)" % hit[0][0] if hit else "NO"}')
    if not hit:
        fails.append(f'figure missing {q["id"]}')
ngp = [d for d in drawn if abs(d[1] - mm(parts['NG-01']['x0'])) < 0.02 and abs(d[3] - mm(parts['NG-01']['r_in'])) < 0.02]
trp = [d for d in drawn if abs(d[1] - h['rotor_le']) < 0.02 or abs(d[1] - h['boss_front']) < 0.02]
if ngp and trp:
    print(f'  NG-01 is drawn as one solid annulus r {ngp[0][3]:.2f}..{ngp[0][4]:.2f} mm over x {ngp[0][1]:.2f}..{ngp[0][2]:.2f}: '
          f'no 48 mm blind pocket/web, no 92/104 mm step, no 85.7 mm shroud bore; turbine patches '
          f'{[d[0] for d in trp]} are drawn later on top of it (patch {ngp[0][0]})')
    flags.append('figure: NG-01 drawn as an open 48 mm-bore solid annulus; the blind pocket/web (R9) and the rotor-in-shroud '
                 'relation are not shown; turbine rectangles are painted over the NGV box')
dfp = [d for d in drawn if d[5] > 5 and abs(d[1] - h['diffuser_floor']) < 0.02]
bc1 = parts['BC-01']
if dfp:
    # DF-01 polygon: find the pocket radius = smallest r among vertices with x == backplate_rear
    pth = [g for g in root.iter('{http://www.w3.org/2000/svg}g') if g.get('id') == f'patch_{dfp[0][0]}'][0].find('s:path', ns)
    nums = [float(v) for v in re.findall(r'[-\d.]+', pth.get('d'))]
    pts = [to_mm(nums[i], nums[i + 1]) for i in range(0, len(nums) - 1, 2)]
    pocket = min(r for x, r in pts if abs(x - h['backplate_rear']) < 0.02)
    print(f'  DF-01 drawn bearing-pocket radius {pocket:.3f} mm (dia {2 * pocket:.2f}); BC-01 stack envelope OD '
          f'{2 * mm(bc1["r_out"]):.3f} mm over x {mm(bc1["x0"]):.2f}..{mm(bc1["x1"]):.2f}; BC-01 is painted over DF-01')
    flags.append(f'BC-01 sleeve OD / backplate pocket diameter undefined in bundle: figure pocket {2 * pocket:.1f} mm vs stack '
                 f'envelope {2 * mm(bc1["r_out"]):.2f} mm (IF-BC1-DF diameter null)')
# shaft fill
m = re.search(r'<g id="FillBetweenPolyCollection_1">.*?<path id="(\w+)" d="(.*?)".*?<use xlink:href="#\1" x="([-\d.]+)" y="([-\d.]+)"',
              txt, re.S)
if m:
    nums = [float(v) for v in re.findall(r'[-\d.]+', m.group(2))]
    ox, oy = float(m.group(3)), float(m.group(4))
    pts = [to_mm(nums[i] + ox, nums[i + 1] + oy) for i in range(0, len(nums) - 1, 2)]
    worst, miss = 0.0, []
    for s in stack['shaft_sections']:
        d_nom = s['od_m'] / 0.85 if 'thread' in s['name'] else s['od_m']
        for xe in (mm(s['z0_m']), mm(s['z0_m'] + s['length_m'])):
            cand = [abs(r - mm(d_nom) / 2) for x, r in pts if abs(x - xe) < 0.02 and r > 0.01]
            if not cand:
                miss.append((s['name'], round(xe, 3)))
            else:
                worst = max(worst, min(cand))
    print(f'  shaft profile drawn vs stack sections (threads at nominal dia): worst corner error {worst:.4f} mm, '
          f'missing corners {miss} {"PASS" if worst < 0.02 and not miss else "DIFF"}')
    if worst >= 0.02 or miss:
        fails.append('figure shaft profile')
markers = [float(v) for v in re.findall(r'<use xlink:href="#m\w+" x="([-\d.]+)" y="[-\d.]+" style="fill: #ff0000', txt)]
print(f'  bearing markers drawn at x = {[round(to_mm(v, 0)[0], 3) for v in markers]} mm (stack {h["fb_c"]:.3f}, {h["rb_c"]:.3f})')
print('  not drawn as envelopes: EX-02 tailcone (line only; the nut/shaft end inside it is not shown), CB-05 (invalid box), '
      'CB-04, EX-01 (lines)')

# ------------------------------------------------------------------ 4. CAD bundle
print('\n[4] CAD bundle')
st_counts = collections.Counter(p['status'] for p in bundle['parameters'])
print(f'  parameters: {len(bundle["parameters"])} (unique names {len(P)}); status counts {dict(st_counts)}; '
      f'sum {sum(st_counts.values())}')
mr = Path('docs/design/MORNING_REPORT.md').read_text(encoding='utf-8')
claim = re.search(r'(\d+) typed parameters', mr)
if claim and int(claim.group(1)) != len(bundle['parameters']):
    flags.append(f'MORNING_REPORT claims {claim.group(1)} parameters; bundle has {len(bundle["parameters"])} '
                 f'(148+19+13+5 = {sum(st_counts.values())})')
    print(f'  DIFF: MORNING_REPORT claims {claim.group(1)} typed parameters; bundle has {len(bundle["parameters"])}')
pol = bundle['unit_policy']
for p in bundle['parameters']:
    if pol.get(p['quantity_type']) != p['unit']:
        flags.append(f'unit policy: {p["name"]} {p["quantity_type"]} {p["unit"]}')
        print(f'  UNIT {p["name"]}: type {p["quantity_type"]} unit {p["unit"]} vs policy {pol.get(p["quantity_type"])}')
    if p['status'].startswith('unresolved') and p['value'] is not None:
        flags.append(f'unresolved parameter carries a value: {p["name"]}')
        print(f'  VALUE ON UNRESOLVED {p["name"]} = {p["value"]}')
    if p['value'] is None and not p['status'].startswith('unresolved'):
        flags.append(f'null value with status {p["status"]}: {p["name"]}')
    if p['quantity_type'] == 'ratio' and 'N/um' in (p['source'] or ''):
        flags.append(f'{p["name"]} is a stiffness in N/um exported as dimensionless ratio "-"')
        print(f'  TYPE {p["name"]} = {p["value"]} exported as ratio "-" but source says N/um (stiffness)')
print(f'  unresolved parameters (no value): {[p["name"] for p in bundle["parameters"] if p["status"].startswith("unresolved")]}')
for p in bundle['parameters']:
    if 'MINOR_DIA' in p['name'] and p['name'].endswith('_DIA'):
        sec = [s for s in stack['shaft_sections'] if 'thread' in s['name'] and str(int(round(p['value']))) in s['name']]
        if sec:
            flags.append(f'{p["name"]} = {p["value"]} mm is the nominal major diameter; the minor diameter used by the '
                         f'rotor model is {mm(sec[0]["od_m"]):.2f} mm')
            print(f'  NAME {p["name"]} = {p["value"]} mm (nominal thread size); stack/rotor model uses {mm(sec[0]["od_m"]):.2f} mm')
# purchased values: traced to records and to the supplier drawings read from tmp/pdfs/pd1-audit (by eye)
drawing = {'TR01_TIP_DIA': 85.0, 'TR01_HUB_DIA': 55.0, 'TR01_BORE_DIA': 9.99, 'TR01_BOSS_DIA': 14.0,
           'TR01_RIM_WIDTH': 7.5, 'TR01_BOSS_LENGTH': 19.0, 'TR01_BOSS_SIDE_A': 8.0,
           'NG01_HUB_DIA': 55.4, 'NG01_FLANGE_OD': 104.0}
rec_map = {'CW-01': cmp_, 'BR-01/02': brg, 'TR-01': tw, 'NG-01': ngv}
for p in bundle['parameters']:
    if p['basis'] != 'supplied' and not p['status'].startswith('fixed'):
        continue
    r = rec_map.get(p['part_id'])
    hits = []
    if r is None:      # CORE-made part labelled 'supplied': look for the purchased value it copies
        for rr_name, rr in rec_map.items():
            for k, v in rr['parameters'].items():
                if isinstance(v, dict) and v.get('basis') == 'supplied' and isinstance(v.get('value'), (int, float)) \
                        and abs(v['value'] - p['value']) < 1e-9:
                    src = next((d for d in rr['source_documents'] if d['id'] == v.get('source')), None)
                    hits.append((f'{rr["component_id"]}.{k} (copied into a CORE-made part; basis label "supplied")',
                                 v.get('source'), bool(src and src.get('url') and src.get('accessed'))))
    if r:
        for k, v in r['parameters'].items():
            if isinstance(v, dict) and v.get('basis') == 'supplied' and isinstance(v.get('value'), (int, float)) \
                    and abs(v['value'] - p['value']) < 1e-9:
                src = next((d for d in r['source_documents'] if d['id'] == v.get('source')), None)
                hits.append((k, v.get('source'), bool(src and src.get('url') and src.get('accessed'))))
    dv = drawing.get(p['name'])
    dtxt = '' if dv is None else (' drawing=%s %s' % (dv, 'MATCH' if abs(dv - p['value']) < 1e-9 else 'MISMATCH'))
    ok = bool(hits) and all(hh[2] for hh in hits)
    print(f'  {p["name"]:<26} {p["value"]!s:>8} {p["status"][:16]:<16} record: '
          f'{hits[0][0] + " <- " + str(hits[0][1]) if hits else "NOT TRACED"}{dtxt}')
    if not ok:
        flags.append(f'{p["name"]} ({p["basis"]}, {p["status"]}) not traced to a supplied record value with a dated source')
    if dv is not None and abs(dv - p['value']) > 1e-9:
        fails.append(f'{p["name"]} vs drawing')
print('  interfaces:')
for i in bundle['interfaces']:
    note = ''
    if i['interface_id'] == 'IF-CW-SH' and 'unresolved' not in (i['relation'] + i['note']).lower():
        note = '<- relation reads as settled although SH01_COMPRESSOR_FINISHED_SEAT_DIA is unresolved (R2)'
        flags.append('IF-CW-SH relation "slip/transition" presented as settled; seat fit unresolved')
    if i['interface_id'] == 'IF-TU-BC2':
        note = (f'<- {i["diameter_mm"]} mm sliding joint at x {i["x_mm"]}: tunnel ends at {mm(tu["x1"]):.4f}; carrier envelope '
                f'OD {2 * mm(bc2["r_out"]):.1f} mm < tunnel OD; geometry of the slip joint not defined')
        flags.append('IF-TU-BC2 slip joint not realisable from the exported envelopes (tunnel ID 47.50 < carrier OD 48.0; '
                     'interface quotes 50.8 mm at x 118.61, 1 mm aft of the tunnel end)')
    if i['interface_id'] == 'IF-NG-CS2' and abs(i['x_mm'] - h['ngv_flange_front']) > 1e-3:
        note = f'<- x is the cover front face; mating face is the flange front face at {h["ngv_flange_front"]:.4f}'
    if i['interface_id'] == 'IF-BC1-DF' and i['diameter_mm'] is None:
        note = '<- mating diameter missing'
    print(f'    {i["interface_id"]:<12} {str(i["x_mm"]):>9} {str(i["diameter_mm"]):>6} {i["relation"][:48]:<48} {note}')
txt_b = brg.get('summary', '')
if '12 mm shaft body' in txt_b and abs(val(asm, 'shaft_body_d') - 12.0) > 1e-9:
    flags.append(f'bearings record summary says a 12 mm shaft body; assembly record/stack use {val(asm, "shaft_body_d")} mm')

print('\nFLAGS (not numeric failures):')
for f in flags:
    print('  -', f)
print('\nSUMMARY:', 'no numeric differences' if not fails else f'{len(fails)} numeric difference(s): {fails}')
sys.exit(1 if fails else 0)
