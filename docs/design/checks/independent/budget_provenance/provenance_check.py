"""Independent provenance spot-check of the PD-1 run outputs.

Run from the repository root:
    python <this file> [run_output_folder]      (default docs/design/results/pd1-jm85)

Independence: reads data/components/*.yaml, data/maps/*.yaml, config/cases/pd1-jm85.yaml, the run's
seed_provenance.json / assumptions_register.json and docs/design/*.md as text/YAML/JSON. Does NOT import
core/ or modules/. The seed-variable -> record-parameter mapping for the stack block is transcribed from
core/candidate.py:214-225 (read, not imported) so that each label can be checked against the record basis.

Prints one line per comparison: name | independent | repository | diff | PASS/DIFF/FINDING.
Exit status 1 on any DIFF (a 'supplied' value without a source, a label that contradicts the record basis,
or a register that omits a record-level assumption).
"""
import glob
import json
import re
import sys
from pathlib import Path

import yaml

RUN = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('docs/design/results/pd1-jm85')
DIFFS = []


def out(name, ind, rep, ok, note='-'):
    print(f'{name} | {ind} | {rep} | {note} | {"PASS" if ok else "DIFF"}')
    if not ok:
        DIFFS.append(name)


def finding(name, text):
    print(f'{name} | {text} | - | - | FINDING')


case = yaml.safe_load(open('config/cases/pd1-jm85.yaml', encoding='utf-8'))
files = dict(case['components'])
recs = {}
for role, fn in files.items():
    recs[role] = yaml.safe_load(open(fn, encoding='utf-8'))

# ---------------------------------------------------------------- 1. every 'supplied' value has a source document
all_files = sorted(glob.glob('data/components/*.yaml')) + sorted(glob.glob('data/maps/*.yaml'))
n_sup = 0
for fn in all_files:
    d = yaml.safe_load(open(fn, encoding='utf-8'))
    docs = {s.get('id'): s for s in (d.get('source_documents') or [])}
    bad = []
    for k, p in (d.get('parameters') or {}).items():
        if isinstance(p, dict) and p.get('basis') == 'supplied':
            n_sup += 1
            s = docs.get(p.get('source'))
            if not s or not (s.get('url') or s.get('path')) or not s.get('accessed'):
                bad.append(k)
    out(f'supplied values with a resolvable source (url/path + access date): {Path(fn).name}', 0, len(bad), not bad,
        ','.join(bad) or '-')
print(f'total supplied parameters checked | {n_sup} | - | - | INFO')
for role in ('compressor', 'turbine', 'ngv', 'bearings'):
    for s in recs[role].get('source_documents') or []:
        print(f"source document {role}:{s.get('id')} | {s.get('url') or s.get('path')} | accessed {s.get('accessed')} | "
              f"sha256 {'yes' if s.get('sha256') else 'no'} | INFO")

# ---------------------------------------------------------------- 2. seed_provenance labels vs record basis
prov = json.loads((RUN / 'seed_provenance.json').read_text(encoding='utf-8'))
role_of = {'compressor_wheel': 'compressor', 'turbine_rotor': 'turbine', 'ngv_ring': 'ngv', 'bearings': 'bearings',
           'assembly_pd1': 'assembly'}
mislabel = []
for var, label in prov.items():
    m = re.match(r'record (\w+)\.(\w+) \((supplied|ASSUMPTION|calculated envelope|design)', label)
    if not m:
        continue
    comp, par, tag = m.groups()
    p = (recs[role_of[comp]].get('parameters') or {}).get(par)
    basis = p.get('basis') if p else None
    want = {'supplied': 'supplied', 'ASSUMPTION': 'assumption', 'calculated envelope': 'calculated',
            'design': 'design'}[tag]
    if basis != want:
        mislabel.append((var, label, basis))
out('seed_provenance "record X.Y (tag)" labels agree with the record basis', 0, len(mislabel), not mislabel,
    str(mislabel) if mislabel else '-')
# stack block (core/candidate.py:214-225) is labelled 'component record (purchased part)' wholesale
stack = {'cw_length_m': ('compressor', 'backface_to_nose_length_envelope'), 'cw_super_back_m': ('compressor', 'super_back_height'),
         'cw_cg_from_backface_m': ('compressor', 'cg_from_backface_estimate'), 'cw_Ip_kg_m2': ('compressor', 'polar_inertia_estimate'),
         'cw_Id_kg_m2': ('compressor', 'diametral_inertia_estimate'), 'cw_D2_ext_m': ('compressor', 'exducer_extended_tip_diameter'),
         'ngv_axial_chord_m': ('ngv', 'vane_axial_chord'), 'ngv_hub_d_m': ('ngv', 'vane_hub_diameter'),
         'ngv_tip_d_m': ('ngv', 'vane_tip_diameter'), 'ngv_flange_od_m': ('ngv', 'flange_od'),
         'ngv_overall_height_m': ('ngv', 'overall_height_blank'), 'ngv_vane_ring_height_m': ('ngv', 'vane_ring_height_blank'),
         'ngv_outer_ring_od_m': ('ngv', 'outer_ring_od'), 'tw_rim_width_m': ('turbine', 'blade_axial_width_at_rim'),
         'tw_boss_d_m': ('turbine', 'hub_boss_diameter'), 'tw_boss_total_m': ('turbine', 'hub_boss_total_length'),
         'tw_boss_side_a_m': ('turbine', 'hub_boss_protrusion_side_a'), 'tw_Id_kg_m2': ('turbine', 'diametral_inertia_estimate')}
not_supplied = []
for var, (role, par) in stack.items():
    lab = prov.get(var)
    basis = (recs[role]['parameters'].get(par) or {}).get('basis')
    if lab == 'component record (purchased part)' and basis != 'supplied':
        not_supplied.append(f'{var}<-{par}[{basis}]')
out('values labelled "component record (purchased part)" whose record basis is not supplied', 0, len(not_supplied),
    not not_supplied, '; '.join(not_supplied) or '-')

# ---------------------------------------------------------------- 3. assumptions register completeness
reg = json.loads((RUN / 'assumptions_register.json').read_text(encoding='utf-8'))
reg_keys = {(r['component'], r['parameter']) for r in reg}
expected = set()
for role, d in recs.items():
    cid = d.get('component_id') or role
    for k, p in (d.get('parameters') or {}).items():
        if isinstance(p, dict) and p.get('basis') in ('assumption', 'unresolved'):
            expected.add((cid, k))
missing = sorted(expected - reg_keys)
extra = sorted(reg_keys - expected)
out('record-level assumption/unresolved parameters present in assumptions_register.json', len(expected),
    len(expected & reg_keys), not missing, f'missing={missing} extra={extra}')
# case-level assumptions (config/cases/pd1-jm85.yaml) are outside the register by construction
case_level = {f'engine.{k}': v for k, v in case['engine'].items()}
case_level.update({f'rotor_support.{k}': v for k, v in case['rotor_support'].items()})
case_level.update({f'diffuser.{k}': v for k, v in case['diffuser'].items() if k in ('cp_vaned_assumed', 'turn_K')})
case_level.update({f'combustor.{k}': v for k, v in case['combustor'].items() if k in ('tau_min_s',)})
in_reg = [k for k in case_level if any(k.split('.')[1] in r['parameter'] for r in reg)]
finding('case-level assumptions absent from assumptions_register.json',
        f'{len(case_level) - len(in_reg)} of {len(case_level)} (e.g. engine.comb_loss_design 0.025, leak_frac 0.02, '
        f'duct_loss_design 0.02, inlet_loss_ref 0.01, jetpipe_loss 0.01, nozzle_Cd/Cv 0.97, eta_b 0.96, LHV 43 MJ/kg, '
        f'windage_Cm 0.004, rotor_support k 2e6 N/m, c 1000 N s/m) plus 22 combustor/fuel seed_overrides')

# ---------------------------------------------------------------- 4. consequential assumptions visible in the reports
docs = {Path(p).name: Path(p).read_text(encoding='utf-8') for p in sorted(glob.glob('docs/design/*.md'))
        if not p.endswith('REVIEW-HANDOFF.md')}
spot = [
    ('NGV exit flow angle 65 deg (assumption)', r'65\s*°|65 deg|exit angle 65'),
    ('rotor exit relative angle -58 deg (assumption)', r'[−-]58\s*°|[−-]58 deg'),
    ('NGV throat area unmeasured (unresolved)', r'throat'),
    ('rotor throat area unresolved', r'rotor (relative )?throat'),
    ('combustor loss 2.5 % (case)', r'2\.5\s*%'),
    ('turn/deswirl loss 2 % (case)', r'turn[^|\n]{0,25}2\s*%'),
    ('tunnel leakage 2 % (case)', r'leak[^|\n]{0,15}2\s*%'),
    ('inlet loss 1 % (case)', r'inlet[^|\n]{0,12}1\s*%'),
    ('jet-pipe loss 1 % (case)', r'jet[- ]?pipe[^|\n]{0,25}1\s*%'),
    ('nozzle Cd/Cv 0.97 (case)', r'C[dv][^|\n]{0,12}0\.97|0\.97'),
    ('combustion efficiency 0.96 (case)', r'(η_?b|eta_b|combustion efficiency)[^|\n]{0,15}0\.96|0\.96'),
    ('fuel LHV 43 MJ/kg (case)', r'43(\.0)?\s*MJ'),
    ('windage coefficient Cm 0.004 (case)', r'windage[^|\n]{0,40}(0\.004|C_?m)'),
    ('support stiffness 2 N/um and damping 1000 N s/m (case)', r'2 N/[µu]m'),
    ('map reference 545 R / 28.4 inHg (302.78 K / 96.17 kPa)', r'545|28\.4 ?inHg|302\.78|96\.17'),
    ('related-wheel map proxy and efficiency deficit 0.04', r'proxy'),
    ('turbine blade count 30 (assumption)', r'blade count|30 blades|blades \(assumed'),
    ('NGV vane count 20 (assumption)', r'vane count|20 vanes'),
    ('turbine tip clearance 0.35 mm (design assumption)', r'0\.35 ?mm'),
    ('turbine alloy / rated speed unknown', r'alloy'),
    ('compressor wheel mass/inertia/CG estimates', r'inerti'),
    ('compressor inducer hub 19 mm (assumption)', r'inducer hub|19 mm'),
    ('bearing friction / lubricant viscosity (assumption)', r'viscosity|friction'),
    ('compressor seat 6 mm envelope (assumption)', r'6 mm seat|Ø6 seat|6 mm.{0,20}seat|seat.{0,20}6 mm'),
    ('material properties handbook-level', r'handbook'),
    ('FX 1.25 USD/CHF + 8 % fees (budget)', r'1\.25'),
    ('T04 screen 1150 K is a candidate TIT, not an allowable', r'1150|1,150'),
]
for name, pat in spot:
    where = [n for n, t in docs.items() if re.search(pat, t, re.I)]
    if where:
        print(f'report visibility: {name} | found | {", ".join(where[:4])}{" ..." if len(where) > 4 else ""} | - | PASS')
    else:
        finding(f'report visibility: {name}', 'not found in docs/design/*.md')

print(f'{len(DIFFS)} difference(s)')
sys.exit(1 if DIFFS else 0)
