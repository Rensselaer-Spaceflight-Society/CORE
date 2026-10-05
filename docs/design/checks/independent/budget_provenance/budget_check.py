"""Independent re-computation of the October 2 workbook and the PD-1 cash scenarios.

Run from the repository root:
    python <this file> [run_output_folder]      (default docs/design/results/pd1-jm85)

Independence: does NOT import core/ or modules/. The workbook is opened read-only with openpyxl
(formulas and cached values) and never saved; its sha256 is checked before and after. The tax/reserve
rates, rounding step and travel row are taken from the workbook's own cells and formula text, then
compared with data/budget/pd1_adjustments.yaml. The PD-1 changes are applied from the YAML by this
script's own reading of its fields (changes / adverse_only / additions / savings_options / routes).

Prints one line per comparison: name | independent | repository | diff | PASS/DIFF/FINDING.
Exit status 1 if any numeric comparison differs (DIFF). FINDING lines are documented wording or
scope observations that do not change a number.
"""
import csv
import hashlib
import json
import math
import re
import sys
import unicodedata
from pathlib import Path

import openpyxl
import yaml

WB = Path('C:/Users/andyc/OneDrive/Desktop/CORE/outputs/core-budget-20261002-fbef9859/CORE_Itemized_Budget.xlsx')
RUN = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('docs/design/results/pd1-jm85')
DIFFS = []


def line(name, ind, rep, tol=0.5, kind='num'):
    if kind == 'num':
        d = None if (ind is None or rep is None) else float(ind) - float(rep)
        ok = d is not None and abs(d) <= tol
        tag = 'PASS' if ok else 'DIFF'
        print(f'{name} | {ind} | {rep} | {d if d is not None else "n/a"} | {tag}')
    else:
        ok = ind == rep
        tag = 'PASS' if ok else 'DIFF'
        print(f'{name} | {ind!r} | {rep!r} | {"-" if ok else "mismatch"} | {tag}')
    if not ok:
        DIFFS.append(name)
    return ok


def finding(name, text):
    print(f'{name} | {text} | - | - | FINDING')


def norm(s):
    if s is None:
        return ''
    s = unicodedata.normalize('NFKC', str(s)).strip()
    return re.sub(r'\s+', ' ', s)


def ceil_step(x, step):
    # Excel CEILING(x, step) for positive x; guard against binary noise (432.16/25 etc.)
    q = x / step
    return math.ceil(q - 1e-9) * step


# ---------------------------------------------------------------- 1. workbook
h0 = hashlib.sha256(WB.read_bytes()).hexdigest()
wf = openpyxl.load_workbook(WB, read_only=True, data_only=False)
wv = openpyxl.load_workbook(WB, read_only=True, data_only=True)
F = [list(r) for r in wf['Parts budget'].iter_rows(min_row=1, max_row=160, max_col=11, values_only=True)]
V = [list(r) for r in wv['Parts budget'].iter_rows(min_row=1, max_row=160, max_col=11, values_only=True)]
wf.close(); wv.close()


def f(cell):
    col = ord(cell[0]) - 65; row = int(cell[1:]) - 1
    return F[row][col]


def v(cell):
    col = ord(cell[0]) - 65; row = int(cell[1:]) - 1
    return V[row][col]


# formulas the totals rely on (text check; any edit to the workbook logic would show here)
expected_formulas = {
    'G120': '=SUM(G9:G118)', 'G126': '=CEILING((G120-G118+SUM(G122:G124))*$K$2,$K$5)',
    'G127': '=CEILING(G120*$K$3,$K$5)', 'G129': '=SUM(G120,G122:G124,G126:G127)', 'G3': '=G129',
    'G147': '=SUM(G143:G146)', 'G148': '=G120-G147+SUM(G122:G124)+CEILING((G120-G147)*$K$3,$K$5)',
}
for c, txt in expected_formulas.items():
    line(f'workbook formula {c}', txt, f(c), kind='str')
for r in list(range(9, 119)) + [122, 123, 124]:
    if f(f'G{r}') != f'=D{r}*F{r}':
        line(f'workbook line formula G{r}', f'=D{r}*F{r}', f(f'G{r}'), kind='str')
tax_rate, reserve_rate, step, target_old = v('K2'), v('K3'), v('K5'), v('K4')
travel_row_sheet = 118  # G126 subtracts G118 (formula text checked above)

wb_rows = []
for r in range(9, 119):
    wb_rows.append(dict(row_id=v(f'A{r}'), sheet_row=r, part=v(f'B{r}'), specification=v(f'C{r}'), qty=v(f'D{r}'),
                        unit=v(f'E{r}'), unit_cost=v(f'F{r}'), cached_total=v(f'G{r}'), price_basis=v(f'I{r}'),
                        evidence=v(f'J{r}'), source=v(f'K{r}'), freight=False))
for r in (122, 123, 124):
    wb_rows.append(dict(row_id=v(f'A{r}'), sheet_row=r, part=v(f'B{r}'), specification=v(f'C{r}'), qty=v(f'D{r}'),
                        unit=v(f'E{r}'), unit_cost=v(f'F{r}'), cached_total=v(f'G{r}'), price_basis=v(f'I{r}'),
                        evidence=v(f'J{r}'), source=v(f'K{r}'), freight=True))
for w in wb_rows:
    if abs(w['qty'] * w['unit_cost'] - w['cached_total']) > 1e-9:
        line(f"workbook qty x unit {w['row_id']}", w['qty'] * w['unit_cost'], w['cached_total'])
travel_id = v(f'A{travel_row_sheet}')
direct = sum(w['qty'] * w['unit_cost'] for w in wb_rows if not w['freight'])
freight = sum(w['qty'] * w['unit_cost'] for w in wb_rows if w['freight'])
travel = v(f'F{travel_row_sheet}') * v(f'D{travel_row_sheet}')
tax = ceil_step((direct - travel + freight) * tax_rate, step)
reserve = ceil_step(direct * reserve_rate, step)
total = direct + freight + tax + reserve
line('workbook direct (G120, rows 9-118 qty x unit)', direct, v('G120'))
line('workbook freight (G122:G124)', freight, v('G122') + v('G123') + v('G124'))
line('workbook tax (G126)', tax, v('G126'))
line('workbook reserve (G127)', reserve, v('G127'))
line('workbook total (G129)', total, v('G129'))
line('workbook total (G3)', total, v('G3'))
borrow = sum(v(f'G{r}') for r in (97, 98, 107, 112))
line('workbook conditional reduction (G147 = H12+H13+T05+T10)', borrow, v('G147'))
cond = direct - borrow + freight + ceil_step((direct - borrow) * reserve_rate, step)
line('workbook conditional total (G148, tax-exempt, reserve recalculated)', cond, v('G148'))
line('workbook travel row (G126 subtracts G118)', 'V01', travel_id, kind='str')

# ---------------------------------------------------------------- 2. CSV extraction vs workbook
with open('data/budget/oct02_parts_budget.csv', encoding='utf-8') as fh:
    csv_rows = list(csv.DictReader(fh))
line('CSV row count = workbook rows 9-118 + 122-124', len(wb_rows), len(csv_rows))
by_csv = {r['row_id']: r for r in csv_rows}
mism = []
for w in wb_rows:
    c = by_csv.get(w['row_id'])
    if c is None:
        mism.append((w['row_id'], 'missing in CSV')); continue
    checks = [('sheet_row', w['sheet_row'], int(c['sheet_row'])), ('qty', float(w['qty']), float(c['qty'])),
              ('unit_cost', float(w['unit_cost']), float(c['unit_cost_usd'])),
              ('line_total', float(w['cached_total']), float(c['line_total_usd'])),
              ('part', norm(w['part']), norm(c['part'])), ('specification', norm(w['specification']), norm(c['specification'])),
              ('unit', norm(w['unit']), norm(c['unit'])), ('price_basis', norm(w['price_basis']), norm(c['price_basis'])),
              ('evidence', norm(w['evidence']), norm(c['evidence'])), ('source', norm(w['source']), norm(c['source']))]
    for k, a, b in checks:
        if a != b:
            mism.append((w['row_id'], k, a, b))
line('CSV fields equal workbook (IDs, sheet rows, qty, unit cost, totals, text)', 0, len(mism))
for m in mism[:10]:
    print('   mismatch:', m)

# ---------------------------------------------------------------- 3. PD-1 adjustments (independent application)
adj = yaml.safe_load(open('data/budget/pd1_adjustments.yaml', encoding='utf-8'))
line('YAML tax rate = workbook K2', tax_rate, adj['rates']['tax_rate'], tol=1e-12)
line('YAML reserve rate = workbook K3', reserve_rate, adj['rates']['reserve_rate'], tol=1e-12)
line('YAML rounding = workbook K5', step, adj['rates']['round_to_usd'], tol=1e-12)
line('YAML travel row = workbook G118 row', travel_id, adj['rates']['travel_row'], kind='str')
line('YAML source sha256 = workbook sha256', h0, adj['source_workbook']['sha256'], kind='str')

lines = {w['row_id']: dict(id=w['row_id'], qty=float(w['qty']), nom=float(w['unit_cost']), adv=float(w['unit_cost']),
                           freight=w['freight'], part=w['part'], spec=w['specification'], basis=w['price_basis'])
         for w in wb_rows}
for ch in adj['changes']:
    L = lines[ch['row_id']]
    if 'qty' in ch: L['qty'] = float(ch['qty'])
    if 'nominal_unit_usd' in ch: L['nom'] = float(ch['nominal_unit_usd'])
    if 'adverse_unit_usd' in ch: L['adv'] = float(ch['adverse_unit_usd'])
    if 'specification' in ch: L['spec'] = ch['specification']
for ch in adj['adverse_only']:
    lines[ch['row_id']]['adv'] = float(ch['adverse_unit_usd'])
for a in adj['additions']:
    assert a['row_id'] not in lines, a['row_id']
    lines[a['row_id']] = dict(id=a['row_id'], qty=float(a['qty']), nom=float(a['nominal_unit_usd']),
                              adv=float(a['adverse_unit_usd']), freight=False, part=a['part'], spec=a['specification'],
                              basis=a.get('price_basis'))


def tot(Ls, key, tax_on=True):
    d = sum(L['qty'] * L[key] for L in Ls.values() if not L['freight'])
    fr = sum(L['qty'] * L[key] for L in Ls.values() if L['freight'])
    tr = Ls[travel_id]['qty'] * Ls[travel_id][key]
    tx = ceil_step((d - tr + fr) * tax_rate, step) if tax_on else 0.0
    rs = ceil_step(d * reserve_rate, step)
    return dict(direct=d, freight=fr, tax=tx, reserve=rs, total=d + fr + tx + rs)


def apply(Ls, ids):
    import copy
    L2 = copy.deepcopy(Ls); tax_on = True
    opts = {o['id']: o for o in adj['savings_options']}
    for i in ids:
        o = opts[i]
        if o.get('amount_usd') == 'tax_line':
            tax_on = False
        elif 'replacement_unit_usd' in o:
            for k in o['rows']: L2[k]['nom'] = float(o['replacement_unit_usd'])
        else:
            for k in o['rows']: L2[k]['nom'] = 0.0
    return tot(L2, 'nom', tax_on)


ind = dict(nominal=tot(lines, 'nom'), adverse=tot(lines, 'adv'), tax_exempt_only=tot(lines, 'nom', tax_on=False),
           all_conditional_options=apply(lines, [o['id'] for o in adj['savings_options']]))
for r in adj['routes']:
    ind['route ' + '+'.join(r['options'])] = apply(lines, r['options'])

cs = json.loads((RUN / 'bom/cost_summary.json').read_text(encoding='utf-8'))
for comp in ('direct', 'freight', 'tax', 'reserve', 'total'):
    line(f'cost_summary workbook_reproduction.{comp}', dict(direct=direct, freight=freight, tax=tax, reserve=reserve,
                                                           total=total)[comp], cs['workbook_reproduction'][comp])
for sc, vals in ind.items():
    for comp in ('direct', 'freight', 'tax', 'reserve', 'total'):
        line(f'scenario {sc}: {comp}', vals[comp], cs['scenarios'][sc][comp])
    line(f'scenario {sc}: vs $5,500', vals['total'] - 5500, cs['gaps'][sc]['vs_target'])
    line(f'scenario {sc}: vs $6,000', vals['total'] - 6000, cs['gaps'][sc]['vs_ceiling'])

# option amounts and confirmation flags
opt_rep = {o['id']: o for o in cs['scenarios']['options']}
for o in adj['savings_options']:
    if o.get('amount_usd') == 'tax_line':
        amt = ind['nominal']['tax']
    elif 'replacement_unit_usd' in o:
        amt = sum(lines[k]['qty'] * (lines[k]['nom'] - o['replacement_unit_usd']) for k in o['rows'])
    else:
        amt = sum(lines[k]['qty'] * lines[k]['nom'] for k in o['rows'])
    line(f"saving {o['id']} amount", amt, opt_rep[o['id']]['direct_or_tax_saving_usd'])
    line(f"saving {o['id']} confirmed flag (must be False)", False, opt_rep[o['id']]['confirmed'], kind='str')
for r in adj['routes']:
    if 'Not confirmed' not in r.get('note', ''):
        finding(f"route {'+'.join(r['options'])}", 'route note does not say "Not confirmed"')

# per-line BOM agreement
with open(RUN / 'bom/candidate_bom.csv', encoding='utf-8') as fh:
    bom = {r['row_id']: r for r in csv.DictReader(fh)}
bad = [(k, L['qty'], L['nom'], L['adv'], bom.get(k)) for k, L in lines.items()
       if k not in bom or abs(float(bom[k]['qty']) - L['qty']) > 1e-9 or abs(float(bom[k]['nominal']) - L['nom']) > 1e-9
       or abs(float(bom[k]['adverse']) - L['adv']) > 1e-9]
line('candidate_bom.csv rows (qty, nominal, adverse) = independent lines', 0, len(bad))
line('candidate_bom.csv row count', len(lines), len(bom))

# integrity: no negative / zero prices (sponsor credit), unknowns stay visible, no second rotor/billet charge
neg = [k for k, L in lines.items() if L['nom'] <= 0 or L['adv'] <= 0]
line('lines with zero or negative nominal/adverse price (sponsor credit / unknown as zero)', 0, len(neg))
adv_lt_nom = [k for k, L in lines.items() if L['adv'] < L['nom']]
line('lines whose adverse price is below nominal', 0, len(adv_lt_nom))
quote_needed = sorted(k for k, L in lines.items() if norm(L['basis']) == 'Quote needed')
rep_exp = sorted(e['row_id'] for e in cs['open_exposures'] if e['basis'] == 'Quote needed')
line('open exposures list every "Quote needed" row', ','.join(quote_needed), ','.join(rep_exp), kind='str')
rotor_terms = re.compile(r'billet|inconel|heat[- ]treat|turbine wheel|turbine rotor', re.I)
rotor_lines = sorted(k for k, L in lines.items() if rotor_terms.search(norm(L['part']) + ' ' + norm(L['spec'])))
print(f'rotor/billet-related lines | {rotor_lines} | - | - | INFO (R01 is the compressor billet wheel; R02 the only turbine wheel)')
line('only one turbine-wheel purchase line', 1, sum(1 for k in rotor_lines if k.startswith('R02')))
# FX arithmetic stated in the YAML reasons
line('R02 nominal = CHF 370 x 1.25 x 1.08 (rounded)', round(370 * 1.25 * 1.08), lines['R02']['nom'], tol=0.6)
line('R03 list conversion CHF 295 x 1.25 x 1.08 (stated USD 398)', round(295 * 1.25 * 1.08), 398, tol=0.6)

# ---------------------------------------------------------------- 4. reports
txt_mr = Path('docs/design/MORNING_REPORT.md').read_text(encoding='utf-8')
txt_mb = Path('docs/design/manufacturing-and-budget.md').read_text(encoding='utf-8')
txt_sm = (RUN / 'SUMMARY.md').read_text(encoding='utf-8')


def fmt(x, signed=False):
    s = f'{abs(x):,.0f}'
    if not signed:
        return [s]
    return ['+' + s] if x > 0 else (['−' + s, '-' + s] if x < 0 else ['0', '±0'])


def check_row(doc, docname, label, total_v, gaps=True, anchored=False):
    rows = [l for l in doc.splitlines() if (l.startswith(label) if anchored else (l.startswith('|') and label in l))]
    if not rows:
        line(f'{docname}: row "{label}" present', 1, 0); return
    r = rows[0].replace('**', '')
    cells = [c.strip() for c in r.strip('|').split('|')]
    ok = any(x in cells for x in fmt(total_v))
    ok &= (not gaps) or (any(x in cells for x in fmt(total_v - 5500, True)) and any(x in cells for x in fmt(total_v - 6000, True)))
    line(f'{docname}: "{label}" total{" and gaps" if gaps else ""}', 1, int(ok))


wbtot = total
mr_rows = [('October 2 workbook', wbtot), ('PD-1 nominal', ind['nominal']['total']),
           ('PD-1 adverse', ind['adverse']['total']), ('Nominal, tax-exempt only', ind['tax_exempt_only']['total']),
           ('route SV1+SV5+SV4,', ind['route SV1+SV5+SV4']['total']),
           ('Route SV1+SV5+SV4+SV2+SV3', ind['route SV1+SV5+SV4+SV2+SV3']['total']),
           ('every conditional option', ind['all_conditional_options']['total'])]
for lab, t in mr_rows:
    check_row(txt_mr, 'MORNING_REPORT sec4', lab, t)
mb_rows = [('October 2 workbook baseline', wbtot), ('PD-1 nominal (changes', ind['nominal']['total']),
           ('PD-1 adverse', ind['adverse']['total']), ('tax-exempt only', ind['tax_exempt_only']['total']),
           ('Route SV1+SV5+SV4 (', ind['route SV1+SV5+SV4']['total']),
           ('Route SV1+SV5+SV4+SV2+SV3', ind['route SV1+SV5+SV4+SV2+SV3']['total']),
           ('every conditional option', ind['all_conditional_options']['total'])]
for lab, t in mb_rows:
    check_row(txt_mb, 'manufacturing-and-budget sec1', lab, t)
for lab, key in (('| nominal |', 'nominal'), ('| adverse |', 'adverse'), ('| tax_exempt_only |', 'tax_exempt_only'),
                 ('| all_conditional_options |', 'all_conditional_options'), ('| route SV1+SV5+SV4 |', 'route SV1+SV5+SV4'),
                 ('| route SV1+SV5+SV4+SV2+SV3 |', 'route SV1+SV5+SV4+SV2+SV3')):
    check_row(txt_sm, 'SUMMARY cash table', lab, ind[key]['total'], gaps=False, anchored=True)

# "Prices not yet in any total" (MORNING_REPORT §4): which of those exposures are already in the adverse total?
adv_delta = lambda ids: sum(lines[k]['qty'] * (lines[k]['adv'] - lines[k]['nom']) for k in ids)
in_adverse = {'assembled-core balancing (S03+S04)': adv_delta(['S03', 'S04']),
              'turbine/NGV landed cost (R02+R03)': adv_delta(['R02', 'R03']),
              'turbine freight (P03)': adv_delta(['P03']), 'fuel pump (F01)': adv_delta(['F01'])}
for k, d in in_adverse.items():
    print(f'adverse-total delta {k} | {d:.0f} | - | - | INFO')
if re.search(r'Prices not yet in\s+any total', txt_mr):
    finding('MORNING_REPORT sec4 "Prices not yet in any total"',
            'balancing (+175), turbine/NGV landed cost (+200), freight (+70) and pump (+70) ARE in the adverse '
            'total (8,027); only journal grinding, drawn outer-liner tube and a larger starter battery are in no total')
grind = [k for k, L in lines.items() if re.search(r'grind', norm(L['part']) + norm(L['spec']), re.I)]
line('journal grinding line present in any total (expected: none, stated as exposure)', 0, len(grind))
m = re.search(r'leaving a ~610 × (\d+) mm strip', txt_mb)
if m:
    rem = cs['sheet_nesting']['remainder_strip_mm'][1]
    line('manufacturing-and-budget sec3 remainder strip height (mm, doc says ~)', rem, float(m.group(1)), tol=5.0)

h1 = hashlib.sha256(WB.read_bytes()).hexdigest()
line('workbook sha256 unchanged by this script', h0, h1, kind='str')
print(f'workbook sha256 {h1}')
print(f'{len(DIFFS)} numeric difference(s)')
sys.exit(1 if DIFFS else 0)
