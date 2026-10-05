"""Itemized cash estimate for the candidate, traceable to the October 2 workbook rows.

The October 2 rows are read from data/budget/oct02_parts_budget.csv (extracted
read-only). reproduce_workbook() recomputes the workbook total from those rows
with the workbook's own formulas and must return USD 6,602 - a self-check that the
extraction and the formulas agree before any candidate change is applied.

Candidate changes come from data/budget/pd1_adjustments.yaml; every changed or
added line keeps its row ID, linked part IDs, a nominal and an adverse unit cost
and the reason. Unknown prices are never zero: an item without a price is
reported as an open exposure. All lines are FORECAST (no spend-to-date supplied).
"""
from __future__ import annotations

import csv
import math

import yaml

from core import cases
from core.records import ROOT

TARGET, CEILING = 5500.0, 6000.0


def ceil_to(x, step):
    return math.ceil(round(x / step, 9)) * step


def load_rows():
    with open(ROOT / 'data/budget/oct02_parts_budget.csv', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r['qty'] = float(r['qty'])
        r['unit_cost_usd'] = float(r['unit_cost_usd'])
        r['line_total_usd'] = float(r['line_total_usd'])
        if abs(r['qty'] * r['unit_cost_usd'] - r['line_total_usd']) > 1e-9:
            raise ValueError(f'{r["row_id"]}: quantity x unit cost does not match the workbook line total')
    ids = [r['row_id'] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate budget row IDs')
    return rows


def totals(lines, rates, key):
    direct = sum(l['qty'] * l[key] for l in lines if not l['row_id'].startswith('P'))
    freight = sum(l['qty'] * l[key] for l in lines if l['row_id'].startswith('P'))
    travel = sum(l['qty'] * l[key] for l in lines if l['row_id'] == rates['travel_row'])
    tax = ceil_to((direct - travel + freight) * rates['tax_rate'], rates['round_to_usd'])
    reserve = ceil_to(direct * rates['reserve_rate'], rates['round_to_usd'])
    return dict(direct=direct, freight=freight, tax=tax, reserve=reserve, total=direct + freight + tax + reserve)


def reproduce_workbook():
    rows = load_rows()
    adj = yaml.safe_load(open(ROOT / 'data/budget/pd1_adjustments.yaml', encoding='utf-8'))
    for r in rows:
        r['nominal'] = r['unit_cost_usd']
    return totals(rows, adj['rates'], 'nominal')


def candidate_lines():
    rows = load_rows()
    adj = yaml.safe_load(open(ROOT / 'data/budget/pd1_adjustments.yaml', encoding='utf-8'))
    by = {r['row_id']: r for r in rows}
    for r in rows:
        r.update(nominal=r['unit_cost_usd'], adverse=r['unit_cost_usd'], status='forecast', change='unchanged',
                 part_ids=[], reason='')
    for ch in adj['changes']:
        r = by[ch['row_id']]
        r['change'] = 'changed'
        for k_src, k_dst in (('nominal_unit_usd', 'nominal'), ('adverse_unit_usd', 'adverse'), ('qty', 'qty'),
                             ('specification', 'specification')):
            if k_src in ch:
                r[k_dst] = ch[k_src]
        r['part_ids'] = ch.get('part_ids', [])
        r['reason'] = ch['reason']
    for ch in adj.get('adverse_only', []):
        r = by[ch['row_id']]
        r['adverse'] = ch['adverse_unit_usd']
        r['reason'] = (r['reason'] + ' ' if r['reason'] else '') + 'Adverse: ' + ch['reason']
    for a in adj.get('additions', []):
        if a['row_id'] in by:
            raise ValueError(f'added row {a["row_id"]} duplicates an existing row')
        line = dict(row_id=a['row_id'], sheet_row=None, part=a['part'], specification=a['specification'],
                    qty=float(a['qty']), unit=a['unit'], unit_cost_usd=None, line_total_usd=None,
                    price_basis=a.get('price_basis', 'Estimate'), evidence='', source='PD-1 design need',
                    nominal=a['nominal_unit_usd'], adverse=a['adverse_unit_usd'], status='forecast', change='added',
                    part_ids=a.get('part_ids', []), reason=a['reason'])
        rows.append(line)
        by[a['row_id']] = line
    for r in rows:
        for k in ('nominal', 'adverse'):
            if r[k] is None or not math.isfinite(float(r[k])):
                raise ValueError(f'{r["row_id"]}: unknown price must be an explicit open exposure, not missing')
    return rows, adj


def scenarios(rows, adj):
    rates = adj['rates']
    nom, adv = totals(rows, rates, 'nominal'), totals(rows, rates, 'adverse')
    by = {r['row_id']: r for r in rows}
    out = []
    for so in adj['savings_options']:
        if so.get('amount_usd') == 'tax_line':
            amt = nom['tax']
            rows_aff = []
        elif 'replacement_unit_usd' in so:
            rows_aff = so['rows']
            amt = sum(by[k]['qty'] * (by[k]['nominal'] - so['replacement_unit_usd']) for k in rows_aff)
        else:
            rows_aff = so['rows']
            amt = sum(by[k]['qty'] * by[k]['nominal'] for k in rows_aff)
        out.append(dict(id=so['id'], description=so['description'], rows=rows_aff, direct_or_tax_saving_usd=amt,
                        confirmed=so['confirmed'], consequence=so['consequence'], dependency=so['dependency']))
    # combined conditional scenarios: apply the options, recompute tax/reserve consistently
    all_cond = apply_options(rows, adj, [so['id'] for so in adj['savings_options']])
    # tax-exempt + list-price only (smallest dependency set)
    rates_te = dict(rates, tax_rate=0.0)
    te_only = totals(rows, rates_te, 'nominal')
    res = dict(nominal=nom, adverse=adv, tax_exempt_only=te_only, all_conditional_options=all_cond, options=out)
    for route in adj.get('routes', []):
        res['route ' + '+'.join(route['options'])] = apply_options(rows, adj, route['options'])
    return res


def apply_options(rows, adj, ids):
    """Totals with the named savings options applied (none of them is confirmed)."""
    import copy
    known = {so['id']: so for so in adj['savings_options']}
    unknown = [i for i in ids if i not in known]
    if unknown:
        raise ValueError(f'unknown savings options {unknown}')
    rows2 = copy.deepcopy(rows)
    by2 = {r['row_id']: r for r in rows2}
    tax_exempt = False
    for i in ids:
        so = known[i]
        if so.get('amount_usd') == 'tax_line':
            tax_exempt = True
        elif 'replacement_unit_usd' in so:
            for k in so['rows']:
                by2[k]['nominal'] = so['replacement_unit_usd']
        else:
            for k in so['rows']:
                by2[k]['nominal'] = 0.0
    rates = adj['rates']
    return totals(rows2, dict(rates, tax_rate=0.0 if tax_exempt else rates['tax_rate']), 'nominal')


def sheet_nesting(comb, stack, case_recs):
    """Shelf-pack the C01 sheet parts (610 x 610 mm) from the actual geometry (+ allowances)."""
    a = case_recs['assembly']
    casing_od = a.si('casing_od') * 1e3
    L_case = (stack['x']['casing_rear_cover'] - stack['x']['casing_front']) * 1e3
    parts = [
        ('casing wrap', math.pi * (casing_od - 1.524) + 10, L_case + 10),
        ('outer liner wrap', math.pi * comb['outer_liner_od_cold_mm'] + 10, comb['chamber_length_cold_mm'] + 10),
        ('inner liner wrap', math.pi * comb['inner_liner_od_cold_mm'] + 10, comb['chamber_length_cold_mm'] + 10),
        ('dome annulus blank', comb['outer_liner_od_cold_mm'] + 12, comb['outer_liner_od_cold_mm'] + 12),
        ('casing rear cover blank', casing_od + 6, casing_od + 6),
        ('outer transition cone (developed)', math.pi * comb['outer_liner_od_cold_mm'] + 10, 35),
        ('inner transition cone (developed)', math.pi * comb['inner_liner_od_cold_mm'] + 10, 35),
    ]
    W = H = 609.6
    parts_sorted = sorted(parts, key=lambda p: -p[2])
    shelves, placed, ok = [], [], True
    for name, w, h in parts_sorted:
        if w > W:
            ok = False
            placed.append(dict(part=name, w_mm=w, h_mm=h, shelf=None))
            continue
        for s in shelves:
            if s['used'] + w <= W and h <= s['h']:
                s['used'] += w
                placed.append(dict(part=name, w_mm=w, h_mm=h, shelf=s['i']))
                break
        else:
            y = sum(s['h'] for s in shelves)
            if y + h > H:
                ok = False
                placed.append(dict(part=name, w_mm=w, h_mm=h, shelf=None))
                continue
            shelves.append(dict(i=len(shelves), h=h, used=w))
            placed.append(dict(part=name, w_mm=w, h_mm=h, shelf=len(shelves) - 1))
    used_h = sum(s['h'] for s in shelves)
    return dict(sheet_mm=[W, H], fits=ok, parts=placed, height_used_mm=used_h, remainder_strip_mm=[W, H - used_h],
                note='Simple shelf packing with 10 mm seam/kerf allowance; shop nesting may do better. Nozzle (I03) '
                     'and a spare liner set would need the remainder strip.')


def write_all(case, recs, res, folder, log):
    wb = reproduce_workbook()
    if abs(wb['total'] - 6602) > 0.5 or abs(wb['direct'] - 5402) > 0.5:
        raise ValueError(f'budget extraction does not reproduce the workbook total: {wb}')
    rows, adj = candidate_lines()
    sc = scenarios(rows, adj)
    nest = sheet_nesting(res['comb'], res['stack'], recs)
    cols = ['row_id', 'sheet_row', 'part', 'specification', 'qty', 'unit', 'unit_cost_usd', 'nominal', 'adverse',
            'change', 'status', 'price_basis', 'part_ids', 'reason', 'source']
    import io
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator='\n')
    w.writerow(cols)
    for r in rows:
        w.writerow([';'.join(r[c]) if c == 'part_ids' else r.get(c) for c in cols])
    folder.write_text('bom/candidate_bom.csv', buf.getvalue())
    summary = dict(workbook_reproduction=wb, target_usd=TARGET, ceiling_usd=CEILING, scenarios=sc, sheet_nesting=nest,
                   spend_status=adj['spend_status'], fx_assumption=adj['fx_assumption'],
                   optional_not_in_totals=adj.get('optional_not_in_totals', []),
                   gaps={k: dict(vs_target=v['total'] - TARGET, vs_ceiling=v['total'] - CEILING)
                         for k, v in sc.items() if isinstance(v, dict) and 'total' in v},
                   open_exposures=[dict(row_id=r['row_id'], part=r['part'], nominal=r['nominal'], adverse=r['adverse'],
                                        basis=r['price_basis']) for r in rows
                                   if r['price_basis'] in ('Quote needed',) or r['change'] == 'added'],
                   note='All lines forecast. Free campus machining/welding and a reviewed shared test site are assumed '
                        'in kind (workbook basis) and are not confirmed.')
    folder.write_json('bom/cost_summary.json', cases.clean_floats(summary))
    res['budget'] = summary
    log.append(f"budget: workbook reproduced {wb['total']:.0f}; PD-1 nominal {sc['nominal']['total']:.0f}, adverse "
               f"{sc['adverse']['total']:.0f}, tax-exempt only {sc['tax_exempt_only']['total']:.0f}, "
               f"all conditional {sc['all_conditional_options']['total']:.0f} USD; C01 nesting fits={nest['fits']}")
