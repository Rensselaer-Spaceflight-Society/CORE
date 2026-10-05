"""Fuel, lubrication, starter and electrical requirement budgets for a candidate run.

Liquid-fuel pressures and vaporizer air pressures are kept separate: the pump must
overcome combustor pressure plus the liquid-side losses below; the vaporizer air
budget is part of the combustor model and is never paid by the pump.
Starter requirements below the lowest map speed are similarity EXTRAPOLATIONS
(power ~ N^3 from the lowest matched point) and are labelled as bounds.
"""
from __future__ import annotations

import math

import yaml

from core import cases
from core.records import ROOT, Check


FUEL = dict(rho=800.0, mu=0.0016)


def needle_restrictor(q_m3_s, dP, d_id, mu=FUEL['mu']):
    """Laminar capillary length giving dP at flow q (Hagen-Poiseuille)."""
    L = dP * math.pi * d_id ** 4 / (128 * mu * q_m3_s)
    v = q_m3_s / (math.pi / 4 * d_id ** 2)
    Re = FUEL['rho'] * v * d_id / mu
    return dict(length_m=L, velocity_m_s=v, Re=Re, laminar=Re < 2000)


def fuel_budget(res, margin=1.3, lube_frac=0.05, n_needles=None, needle_dP=60000.0, needle_id=0.5e-3):
    pts = [p for p in res['line'] if 'beta' in p]
    lo, hi = res['state']['N_operating_min_rpm'], res['state']['N_operating_max_rpm']
    rng = [p for p in pts if lo <= p['N_rpm'] <= hi] or pts
    mf = max(p['flows']['m_fuel_kg_s'] for p in rng)
    P_comb = max(p['stations']['P31_Pa'] for p in rng)
    q_comb = mf / FUEL['rho']
    q_lube = lube_frac * q_comb
    q_pump = margin * (q_comb + q_lube)
    n = n_needles or int(res['comb']['vap_n'])
    needle = needle_restrictor(q_comb / n, needle_dP, needle_id)
    st = res['state']
    items = [
        ('combustor (vaporizer stick) pressure, max in range', P_comb - st['P00_Pa']),
        ('needle laminar restrictors (distribution)', needle_dP),
        ('line friction (M50)', st['dP_fuel_line_Pa']),
        ('filter (allowance)', st['dP_fuel_filter_Pa']),
        ('fittings minor losses (M50 K)', st['fuel_minor_K_ratio'] * 0.5 * FUEL['rho'] * st['v_fuel_line_m_s'] ** 2),
        ('check valve cracking (allowance)', 7000.0),
        ('shutoff solenoid valve (allowance)', 15000.0),
    ]
    dP_total = sum(v for _, v in items)
    return dict(max_fuel_kg_h=mf * 3600, pump_flow_required_L_h=q_pump * 3.6e6, lube_flow_L_h=q_lube * 3.6e6,
                design_margin=margin, lube_fraction_of_fuel=lube_frac,
                pressure_items_Pa=[dict(item=a, dP_Pa=b) for a, b in items], pump_differential_required_Pa=dP_total,
                pump_outlet_required_abs_Pa=st['P00_Pa'] + dP_total, needle=dict(n=n, id_m=needle_id, **needle),
                note='Liquid budget only. Vaporizer air budget is inside the combustor model and is not paid by the pump. '
                     'Lube flow (fuel + 5 % oil mixture to bearings) bypasses the combustor and its heat release is not credited.')


def starter_budget(res, t_accel_s=3.0, speeds=(5000, 10000, 15000, 20000, 25000, 30000)):
    pts = [p for p in res['line'] if 'beta' in p]
    low = min(pts, key=lambda p: p['N_rpm'])
    Pc0, N0 = low['powers']['P_compressor_W'], low['N_rpm']
    I = res['stack']['rotor_Ip_kg_m2']
    mech = res['engine'].mech
    rows = []
    for N in speeds:
        w = N * 2 * math.pi / 60
        P_c = Pc0 * (N / N0) ** 3
        P_m = mech.power_W(N)[0]
        T_acc = I * w / t_accel_s
        T = (P_c + P_m) / w + T_acc
        rows.append(dict(N_rpm=N, compressor_motoring_W_bound=P_c, mechanical_W=P_m, accel_torque_Nm=T_acc,
                         torque_required_Nm=T, power_required_W=T * w))
    return dict(basis=f'compressor power scaled as N^3 from the lowest matched point ({N0:.0f} rpm, {Pc0:.0f} W) - '
                      'EXTRAPOLATION below the map, bounding estimate only; turbine windmilling and combustion assistance '
                      'neglected; acceleration from rest in the stated time with the rotor polar inertia.',
                rotor_Ip_kg_m2=I, accel_time_s=t_accel_s, rows=rows,
                attachment='rubber cone on the compressor nut through a one-way clutch; starter on a 3-strut bracket in '
                           'the inlet (struts inside the inlet-loss allowance); disengages by overrun.',
                unresolved=['light-off speed', 'starter cut-out speed', 'self-sustain speed below 54.5 krpm',
                            'motoring power below the map', 'starter motor torque-speed curve'])


def electrical_budget(st_rows):
    peak_starter = max(r['power_required_W'] for r in st_rows)
    loads = [
        dict(load='fuel pump (JetCat-class, assumed)', bus='12 V', current_A=3.0, duty='continuous', basis='assumption'),
        dict(load='fuel shutoff solenoid (NC)', bus='12 V', current_A=0.6, duty='continuous', basis='assumption'),
        dict(load='ignition module + plug', bus='12 V', current_A=2.0, duty='start only', basis='assumption'),
        dict(load='starter motor via ESC (peak at 30 krpm bound)', bus='3S LiPo 11.1 V', current_A=peak_starter / 11.1 / 0.75,
             duty='start only (<10 s)', basis='calculated bound / 75 % motor efficiency'),
        dict(load='microcontroller + logger + ADC + TC interfaces', bus='5 V', current_A=0.35, duty='continuous', basis='assumption'),
        dict(load='pressure transmitters (2 x 4-20 mA class)', bus='24 V', current_A=0.05, duty='continuous', basis='assumption'),
        dict(load='interlock relay coils (2)', bus='24 V', current_A=0.08, duty='continuous', basis='assumption'),
    ]
    by_bus = {}
    for l in loads:
        if l['duty'] == 'continuous':
            by_bus[l['bus']] = by_bus.get(l['bus'], 0.0) + l['current_A']
    return dict(loads=loads, continuous_current_by_bus_A=by_bus,
                checks=[Check.compare('12 V continuous load vs 5 A buck converter (E16)', by_bus.get('12 V', 0.0), '<=', 4.0,
                                      'A', 'assumption', '80 % derating of a 5 A converter'),
                        Check.compare('starter peak current vs 2200 mAh 3S LiPo at 30C (66 A)',
                                      loads[3]['current_A'], '<=', 66.0, 'A', 'assumption', 'battery C-rating not verified')])


def write_all(case, recs, res, folder, log):
    fb = fuel_budget(res)
    sb = starter_budget(res)
    eb = electrical_budget(sb['rows'])
    sig = yaml.safe_load(open(ROOT / 'data/systems/signals.yaml', encoding='utf-8'))
    ids = [c['id'] for c in sig['channels']]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate signal ids')
    folder.write_json('systems/fuel_budget.json', cases.clean_floats(fb))
    folder.write_json('systems/starter_budget.json', cases.clean_floats(sb))
    folder.write_json('systems/electrical_budget.json', cases.clean_floats(dict(eb, checks=[c.as_dict() for c in eb['checks']])))
    folder.write_json('systems/signals.json', sig)
    res['systems'] = dict(fuel=fb, starter=sb, electrical=eb)
    res['checks'].extend(eb['checks'])
    log.append(f"systems: pump {fb['pump_flow_required_L_h']:.1f} L/h at {fb['pump_differential_required_Pa']/1e5:.2f} bar(d); "
               f"starter bound {max(r['power_required_W'] for r in sb['rows']):.0f} W at 30 krpm")
