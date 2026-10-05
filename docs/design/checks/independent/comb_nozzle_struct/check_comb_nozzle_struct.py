"""Independent re-computation: nozzle (incl. R7 thrust), combustor screens, structures.

Run from the repository root:
    python <this file> [results_dir]          default: docs/design/results/pd1-jm85

Independence: does NOT import the code under test (core.thermo, core.combustor,
core.postprocess, core.engine_match, core.assembly, modules.*). Uses core.gas only
for gas properties (cp/h of air and products) and re-implements isentropic
expansion, orifice flux, energy balance and all mechanics from the stated formulas.
Inputs are the run outputs plus data/components/materials.yaml.

Each comparison prints: name | independent | repository | diff % | verdict.
PASS  = agrees within the stated tolerance (default 1 %).
DIFF  = unexplained disagreement > tolerance -> exit status 1.
INFO  = alternative definition / sensitivity; reported, never fails the script.
"""
import json
import math
import re
import sys
from pathlib import Path

import yaml
from scipy.integrate import quad
from scipy.optimize import brentq

sys.path.insert(0, '.')
from core import gas  # noqa: E402  (properties only)

RES = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('docs/design/results/pd1-jm85')
R_GAS = 287.05
FAILS = []


def load(name):
    return json.loads((RES / name).read_text())


def state_json():
    p = RES / 'state.json'
    if p.is_file():
        return json.loads(p.read_text())
    m = load('manifest.json')
    run = Path('out') / m['case_id'] / m['design_fingerprint'][:12] / 'state.json'
    return json.loads(run.read_text())


def row(name, indep, repo, tol=0.01, kind='cmp', note=''):
    if kind == 'info':
        verdict = 'INFO'
    elif repo is None:
        verdict = 'PASS' if indep else 'DIFF'
    else:
        denom = max(abs(repo), 1e-300)
        diff = abs(indep - repo) / denom if repo != 0 else abs(indep - repo)
        verdict = 'PASS' if diff <= tol else 'DIFF'
    if verdict == 'DIFF':
        FAILS.append(name)
    if isinstance(indep, (int, float)) and isinstance(repo, (int, float)) and repo != 0:
        d = f'{100 * (indep - repo) / abs(repo):+.3f}%'
    else:
        d = '-'
    fi = f'{indep:.6g}' if isinstance(indep, (int, float)) else str(indep)
    fr = f'{repo:.6g}' if isinstance(repo, (int, float)) else str(repo)
    print(f'{name:<70s} | {fi:>13s} | {fr:>13s} | {d:>9s} | {verdict}' + (f'  ({note})' if note else ''))


def section(title):
    print('\n== ' + title + ' ' + '=' * max(3, 100 - len(title)))


# ----------------------------------------------------------------------------- property helpers (independent)
def s_rel(T, far, Tref=300.0):
    """Entropy function int_Tref^T cp/T dT [J/kg K] by adaptive quadrature (gas.cp_products only)."""
    return quad(lambda t: gas.cp_products(t, far) / t, Tref, T, epsabs=1e-10, epsrel=1e-12)[0]


def T_isentropic(T0, P0, P, far):
    """Static temperature after isentropic expansion T0,P0 -> P (s(T) - s(T0) = R ln(P/P0))."""
    target = R_GAS * math.log(P / P0)
    return brentq(lambda t: quad(lambda x: gas.cp_products(x, far) / x, T0, t, epsabs=1e-10, epsrel=1e-12)[0] - target,
                  200.0, T0 * (1 + 1e-12) if P <= P0 else 1899.0, xtol=1e-10)


def T_from_h(h, far):
    return brentq(lambda t: gas.h_products(t, far) - h, 200.0, 1899.0, xtol=1e-10)


def gamma_of(T, far):
    cp = gas.cp_products(T, far)
    return cp / (cp - R_GAS)


def nozzle_state(T0, P0, Pamb, far, Cv):
    """Convergent nozzle with velocity coefficient: returns V, T, P, choked (own implementation)."""
    h0 = gas.h_products(T0, far)

    def actual(P):
        Tis = T_isentropic(T0, P0, P, far)
        dh = Cv ** 2 * (h0 - gas.h_products(Tis, far))
        T = T_from_h(h0 - dh, far)
        return math.sqrt(2 * dh), T

    def mach(P):
        V, T = actual(P)
        return V / math.sqrt(gamma_of(T, far) * R_GAS * T)

    if mach(Pamb) < 1.0:
        V, T = actual(Pamb)
        return V, T, Pamb, False
    P = brentq(lambda p: mach(p) - 1.0, Pamb, P0 * 0.999999, xtol=1e-6)   # static pressure where M = 1
    V, T = actual(P)
    return V, T, P, True


# ----------------------------------------------------------------------------- 1. nozzle + R7
def check_nozzle():
    section('1. Nozzle and R7 thrust (design point)')
    dp = load('design_point.json')
    pt, eng = dp['point'], dp['engine']
    st, fl = pt['stations'], pt['flows']
    T7, P7, P0 = st['T7_K'], st['P7_Pa'], st['P0_Pa']
    far = fl['FAR_mixed']
    A8, Cd, Cv = eng['A8_m2'], eng['nozzle_Cd'], eng['nozzle_Cv']
    V8, T8, P8, choked = nozzle_state(T7, P7, P0, far, Cv)
    rho8 = P8 / (R_GAS * T8)
    m_cap = Cd * A8 * rho8 * V8
    F = m_cap * V8 + A8 * (P8 - P0)
    row('NPR = P07/P0', P7 / P0, pt['nozzle']['NPR'], 1e-9)
    row('nozzle choked (own sonic search)', 0.0 if not choked else 1.0, 0.0 if not pt['nozzle']['choked'] else 1.0, 1e-9)
    row('V8 [m/s] (Cv applied to velocity)', V8, st['V8_m_s'], 0.002)
    row('T8 static [K]', T8, st['T8_static_K'], 0.001)
    row('nozzle capacity Cd*A8*rho8*V8 [kg/s] vs turbine flow', m_cap, fl['m_turbine_kg_s'], 0.003)
    row('gross thrust m*V8 + A8,geom*(P8-P0) [N]', F, pt['thrust_N'], 0.003)
    row('pressure-thrust term A8*(P8-P0) [N] (unchoked -> 0)', A8 * (P8 - P0), 0.0, kind='info',
        note='exactly zero because P8 = P0 when unchoked')
    # critical NPR for reference (own search): pressure ratio at which the exit Mach reaches 1
    def exit_mach(npr):        # Mach number of the Cv-degraded expansion to static P7/npr
        Tis = T_isentropic(T7, P7, P7 / npr, far)
        dh = Cv ** 2 * (gas.h_products(T7, far) - gas.h_products(Tis, far))
        Tx, Vx = T_from_h(gas.h_products(T7, far) - dh, far), math.sqrt(2 * dh)
        return Vx / math.sqrt(gamma_of(Tx, far) * R_GAS * Tx)
    npr_crit = brentq(lambda npr: exit_mach(npr) - 1.0, 1.5, 3.0, xtol=1e-6)
    row('critical NPR with Cv=0.97 (reference)', npr_crit, npr_crit, kind='info',
        note=f'design NPR {P7 / P0:.4f} is far below it')
    nprs = []

    def walk(o):
        if isinstance(o, dict):
            if isinstance(o.get('NPR'), (int, float)):
                nprs.append((o['NPR'], bool(o.get('choked'))))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(load('operating_line.json'))
    if nprs:
        row('operating line 55-80 krpm: max NPR (all unchoked -> R7 changes no PD-1 number)', max(nprs)[0], npr_crit,
            kind='info', note=f'any choked: {any(c for _, c in nprs)}')
    # geometry: half angle and exit area from the published contour
    nz = load('nozzle.json')
    pts = nz['points']
    L = pts[-1]['x_m'] - pts[0]['x_m']
    half = math.degrees(math.atan((pts[0]['r_outer_m'] - pts[-1]['r_outer_m']) / L))
    row('nozzle outer-wall half angle [deg]', half, nz['half_angle_deg'], 1e-6)
    row('nozzle exit area pi*r_ex^2 vs A8 used in the match [m2]', math.pi * pts[-1]['r_outer_m'] ** 2, A8, 1e-9)
    row('nozzle exit diameter [m] (54 mm claimed)', 2 * pts[-1]['r_outer_m'], 0.054, 1e-9)
    areas = [math.pi * (q['r_outer_m'] ** 2 - q['r_tailcone_m'] ** 2) for q in pts]
    row('minimum annular area located at the exit plane', areas.index(min(areas)) == len(areas) - 1, None)
    row('inlet annulus area [m2]', areas[0], nz['inlet_annulus_area_m2'], 1e-9)
    row('max/inlet annulus area (diffusing tailcone section, info)', max(areas) / areas[0], max(areas) / areas[0],
        kind='info', note='annulus area rises 23 % before converging; no internal minimum')
    # combined-adverse "rescue" by opening the nozzle exit: is it still a convergent nozzle?
    rb = load('robustness/robustness.json').get('combined_adverse_rescue')
    if rb and rb.get('nozzle_exit_d_m'):
        A_ex = math.pi / 4 * rb['nozzle_exit_d_m'] ** 2
        row('rescue nozzle: exit area / retained inlet annulus (>1 = not convergent)', A_ex / areas[0],
            A_ex / rb['retained_nozzle_inlet_annulus_m2'], 1e-9,
            note=f"code verdict: {rb.get('result')}; model screen: {rb.get('model_screen')}")
        rep = Path('docs/design/MORNING_REPORT.md').read_text(encoding='utf-8')
        i = rep.find('Ø69')
        ctx = rep[max(0, i - 200): i + 300] if i >= 0 else ''
        row('MORNING_REPORT states the Ø69 mm rescue is invalid as a simple resize', 'invalid' in ctx.lower() or 'INVALID' in ctx,
            None if False else 'INVALID', kind='info',
            note='False = report presents the rescue without the INVALID / model-validity qualification')
    # module path (M40 fixed-nozzle mode) vs match
    s = state_json()
    row('M40 F_gross_N vs match thrust [N]', s['F_gross_N'], pt['thrust_N'], 1e-9)
    row('M40 nozzle mass residual (|value| < 1e-9 expected)', abs(s['nozzle_mass_residual_ratio']) < 1e-9, None)
    row('M40 inputs: T05 = T07, op_P07 = P07', abs(s['T05_K'] - T7) < 1e-9 and abs(s['op_P07_Pa'] - P7) < 1e-6, None)
    # static source check of the thrust formula in both producers (R7)
    em = Path('core/engine_match.py').read_text()
    m40 = Path('modules/m40_nozzle.py').read_text()
    ok_em = bool(re.search(r'F\s*=\s*m_noz\s*\*\s*V8\s*\+\s*eng\.A8_m2\s*\*\s*\(P8\s*-\s*P0\)', em)) and \
        bool(re.search(r'return\s+Cd\s*\*\s*A\s*\*\s*rho\s*\*\s*V', em))
    ok_m40 = bool(re.search(r'm_cap\s*=\s*Cd\s*\*\s*A8\s*\*', m40)) and \
        bool(re.search(r'F\s*=\s*mdot_hot\s*\*\s*V8\s*\+\s*A8\s*\*\s*\(P8\s*-\s*s\["P00_Pa"\]\)', m40))
    row('source: engine_match uses Cd*A8 for flow, geometric A8 for pressure thrust', ok_em, None)
    row('source: M40 fixed mode uses Cd*A8 for flow, geometric A8 for pressure thrust', ok_m40, None)


# ----------------------------------------------------------------------------- 2. combustor
def orifice_flux_air(Pup, Tup, Pdown, Cd):
    """Compressible isentropic orifice mass flux for air (far = 0), own implementation."""
    Tj = T_isentropic(Tup, Pup, Pdown, 0.0)
    V = math.sqrt(2 * (gas.h_air(Tup) - gas.h_air(Tj)))
    return Cd * Pdown / (R_GAS * Tj) * V


def check_combustor():
    section('2. Combustor (design point)')
    c = load('combustor.json')
    r, lay = c['library_result'], c['layout']
    dp = load('design_point.json')['point']
    sc = r['thermal_scale_ratio']
    # --- residence time
    A = r['combustion_annulus_A']
    L = r['chamber_length_mm'] / 1e3
    V_tot = A * L
    m_thr = r['mdot_air'] + r['mdot_fuel']
    T_bulk = 0.5 * (r['T2_K'] + r['exit_T4_total_K'])
    tau = V_tot / (m_thr / (r['P2_Pa'] / (R_GAS * T_bulk)))
    row('liner volume A*L [m3]', V_tot, r['CLP_V_total_m3'], 1e-9)
    row('bulk residence time, mean-T density [ms] (1.4 ms claimed)', tau * 1e3, r['tau_comb_ms'], 0.002)
    tau_exit = V_tot / (m_thr / (r['P2_Pa'] / (R_GAS * r['exit_T4_total_K'])))
    row('residence time at exit-temperature density [ms] (definition sensitivity)', tau_exit * 1e3, r['tau_comb_ms'],
        kind='info', note='1.4 ms is a sizing input (length driver = residence time), not a prediction')
    bc = c['basis_comparison']
    passing = sorted({(b['loss'], b['tau_ms']) for b in bc if b.get('passes_existing_screens')})
    row('basis comparison: combinations passing all existing screens', str(passing), "[(0.025, 1.4)] claimed 'only'",
        kind='info', note='2.5 % is the only passing LOSS; 1.4 vs 2.0 ms both pass (1.4 ms chosen for a shorter span)')
    # --- hole areas vs the effective area implied by each branch pressure drop
    fo, fi = r['hole_split_f_outer'], r['hole_split_f_inner']
    Cd = 0.6
    flux = {b: orifice_flux_air(r[f'P_{b}_static_Pa'], r[f'T_{b}_static_K'], r['exit_P4_Pa'], Cd)
            for b in ('outer', 'inner')}
    demand = {'pri': r['split_primary_liner'], 'sec': r['split_secondary'], 'dil': r['split_dilution']}
    cap = {'outer': 0.0, 'inner': 0.0}
    for b, short, frac in (('outer', 'out', fo), ('inner', 'in', fi)):
        for z in ('pri', 'sec', 'dil'):
            n = r[f'{z}_{short}_qty']
            d = r[f'{z}_{short}_mm'] / 1e3
            A_geo = n * math.pi * d * d / 4
            A_req = demand[z] * frac / flux[b]
            row(f'{b} {z} hole area: geometric (hot) vs required from flux [mm2]', A_geo * 1e6, A_req * 1e6, 1e-3)
            cap[b] += A_geo * flux[b]
        nf, df = r[f'film_holes_per_row_{b}'], r[f'film_hole_dia_{b}_mm'] / 1e3
        cap[b] += r['film_n_rows'] * nf * math.pi * df * df / 4 * flux[b]
        film_area = getattr(check_combustor, 'film_area', 0.0) + r['film_n_rows'] * nf * math.pi * df * df / 4
        check_combustor.film_area = film_area
    row('film hole total area, both liners (hot) [mm2]', check_combustor.film_area * 1e6, r['film_total_area_mm2'], 1e-6)
    row('film hole total area vs film flow / branch flux [mm2]',
        sum(r['m_film_cooling'] * f / flux[b] for b, f in (('outer', fo), ('inner', fi))) * 1e6, r['film_total_area_mm2'], 1e-6)
    cap['outer'] += r['split_primary_vap']
    row('outer branch capacity incl. film + vaporizers [kg/s]', cap['outer'], r['mdot_air'] * r['f_outer_feed_used'], 1e-3)
    row('inner branch capacity incl. film [kg/s]', cap['inner'], r['mdot_air'] * (1 - r['f_outer_feed_used']), 1e-3)
    # incompressible effective-area comparison (information: compressibility effect)
    rho_o = r['P_outer_static_Pa'] / (R_GAS * r['T_outer_static_K'])
    inc = Cd * math.sqrt(2 * rho_o * r['dP_outer_holes_Pa'])
    row('outer hole flux: compressible / incompressible Cd*sqrt(2 rho dP)', flux['outer'] / inc, 1.0, kind='info',
        note='holes sized with the compressible flux (about 2 % below the incompressible value)')
    # counts preserved into the layout
    rows = lay['rows']
    for side, short in (('outer', 'out'), ('inner', 'in')):
        for z, zz in (('primary', 'pri'), ('secondary', 'sec'), ('dilution', 'dil')):
            n_lay = sum(q['count'] for q in rows if q['side'] == side and q['row'] == z)
            row(f'{side} {z} count in layout vs library', n_lay, r[f'{zz}_{short}_qty'], 0.0)
    # --- 1-D axial momentum check of the uniform-liner-static assumption
    rho4, u4 = r['exit_rho4'], r['exit_V4_m_s']
    q4 = r['exit_P4_total_Pa'] - r['exit_P4_Pa']
    dP_dome = rho4 * u4 * u4               # P_dome,s - P_exit,s with radial jets (no axial jet momentum), no friction
    row('liner exit Mach (own: V4 / a4)', u4 / math.sqrt(gamma_of(r['exit_T4_K'], r['FAR']) * R_GAS * r['exit_T4_K']),
        r['exit_Ma4'], 0.002)
    row('momentum: P_dome,s - P_exit,s = rho4*u4^2 [Pa] vs outer hole dP', dP_dome, r['dP_outer_holes_Pa'], kind='info',
        note='code assumes uniform liner static = exit static (documented approximation)')
    loss_mom = (r['P2_Pa'] - r['P_outer_static_Pa'] + r['dP_outer_holes_Pa'] + dP_dome - q4) / r['P2_Pa']
    row('momentum-consistent P031->P04 loss for the as-sized holes (dome bound)', loss_mom, r['dP_target_frac'],
        kind='info', note='upper estimate; prescribed basis 2.5 %')
    # first-order 1-D liner model: static above exit static at each row = (exit momentum flux) - (local flux),
    # radial jets carry no axial momentum; T after primary = code primary-zone estimate, after secondary = lean
    # energy balance of all air so far with all fuel, after dilution/film = the same balance (-> T4).
    Lh = [r['L_primary_mm'] / 1e3, r['L_secondary_mm'] / 1e3, r['L_dilution_mm'] / 1e3]
    m_film_row = r['m_film_cooling'] / r['film_n_rows']
    inj = [(0.0, 'vap', r['split_primary_vap'] + r['mdot_fuel']), (0.004, 'film', m_film_row),
           (0.55 * Lh[0], 'pri', r['split_primary_liner']), (Lh[0], 'film', m_film_row),
           (Lh[0] + 0.5 * Lh[1], 'sec', r['split_secondary']), (Lh[0] + Lh[1], 'film', m_film_row),
           (Lh[0] + Lh[1] + 0.4 * Lh[2], 'dil', r['split_dilution']), (Lh[0] + Lh[1] + 0.85 * Lh[2], 'film', m_film_row)]
    P4s = r['exit_P4_Pa']

    def T_mix(m_air):
        f = r['mdot_fuel'] / m_air
        return T_from_h((gas.h_air(r['T2_K']) + f * 43e6 * 0.96) / (1 + f), min(f, 0.06))
    m_cum, m_air_cum, flux_up = 0.0, 0.0, {}
    for x, kind, m in inj:
        if m_cum > 0:
            # upstream of (and at) the secondary row the gas is the rich primary-zone product (phi_pz 1.6)
            Tloc = r['T_primary_zone_est'] if x <= Lh[0] + 0.5 * Lh[1] + 1e-9 else T_mix(m_air_cum)
            flux_up[(x, kind)] = m_cum ** 2 * R_GAS * Tloc / (P4s * A * A)
        else:
            flux_up[(x, kind)] = 0.0
        m_cum += m
        m_air_cum += m - (r['mdot_fuel'] if kind == 'vap' else 0.0)
    F_exit = rho4 * u4 * u4
    hole_rows = [(x, k, m) for x, k, m in inj if k in ('pri', 'sec', 'dil', 'film')]
    for x, k, m in hole_rows:
        if k != 'film':
            row(f'1-D liner: static above exit static at the {k} row [Pa]', F_exit - flux_up[(x, k)],
                0.0, kind='info', note=f'code assumes 0; outer hole dP {r["dP_outer_holes_Pa"]:.0f} Pa')
    dPo, dPi = r['dP_outer_holes_Pa'], r['dP_inner_holes_Pa']

    def passed(X):            # total hole flow with every annulus static raised by X (fixed hole areas)
        tot = 0.0
        for x, k, m in hole_rows:
            d = F_exit - flux_up[(x, k)]
            for frac, dP in ((fo, dPo), (fi, dPi)):
                tot += m * frac * math.sqrt(max(dP + X - d, 0.0) / dP)
        return tot
    need = sum(m for _, _, m in hole_rows)
    X = brentq(lambda X: passed(X) - need, 0.0, 2e4)
    row('1-D liner: extra annulus-to-liner dP to pass the design hole flow [Pa]', X, 0.0, kind='info')
    row('1-D liner: momentum-consistent combustor loss with the as-sized holes', r['dP_target_frac'] + X / r['P2_Pa'],
        r['dP_target_frac'], kind='info', note='first-order; friction and reverse vaporizer momentum would add')
    # --- dilution penetration (Norster/Lefebvre multi-jet, Eq. 4.20 form)
    H = r['combustion_gap_mm'] / 1e3
    rho2 = r['rho2']

    def penetration(side, T_gas, lefebvre_defs):
        short, frac = ('out', fo) if side == 'outer' else ('in', fi)
        n, d = r[f'dil_{short}_qty'], r[f'dil_{short}_mm'] / 1e3
        m_dil = r['split_dilution'] * frac
        m_g = r['split_primary'] + r['split_secondary'] + r['mdot_fuel']
        rho_g = r['P2_Pa'] / (R_GAS * T_gas)
        U_g = m_g / (rho_g * A)
        if lefebvre_defs:            # vena-contracta jet: d_j = d sqrt(Cd), U_j from the hole pressure drop
            dP = r[f'dP_{side}_holes_Pa']
            U_j = math.sqrt(2 * dP / rho2)
            d_j = d * math.sqrt(Cd)
        else:                        # code definitions: geometric hole diameter, mean velocity in the hole
            U_j = (m_dil / n) / (rho2 * math.pi * d * d / 4)
            d_j = d
        J = rho2 * U_j ** 2 / (rho_g * U_g ** 2)
        return 1.25 * d_j * math.sqrt(J) * m_g / (m_g + m_dil) / H, J

    po, Jo = penetration('outer', 1200.0, False)
    pi_, Ji = penetration('inner', 1200.0, False)
    row('dilution J outer (code definitions, T_gas 1200 K)', Jo, r['dil_J_outer'], 1e-6)
    row('dilution J inner (code definitions, T_gas 1200 K)', Ji, r['dil_J_inner'], 1e-6)
    row('dilution penetration Y/H outer (code definitions)', po, r['dil_pen_norm_outer'], 1e-6)
    row('dilution penetration Y/H inner (code definitions) - screened value', pi_, r['dil_pen_norm_inner'], 1e-6)
    # mainstream temperature at the dilution plane from an energy balance (eta_b 0.96, LHV 43 MJ/kg)
    m_air_ps = r['split_primary'] + r['split_secondary']
    far_ps = r['mdot_fuel'] / m_air_ps
    target = (gas.h_air(r['T2_K']) + far_ps * 43e6 * 0.96) / (1 + far_ps)
    T_ps = T_from_h(target, far_ps)
    row('mainstream T ahead of dilution (energy balance) vs code constant [K]', T_ps, 1200.0, kind='info')
    for T_g in (1200.0, T_ps):
        for defs, label in ((False, 'code defs'), (True, 'Lefebvre d_j=d*sqrt(Cd), U_j=sqrt(2dP/rho3)')):
            p_in = penetration('inner', T_g, defs)[0]
            p_out = penetration('outer', T_g, defs)[0]
            row(f'Y/H max(outer,inner) at T_gas {T_g:.0f} K, {label}', max(p_in, p_out), 0.75, kind='info',
                note='screen limit 0.75')
    # --- weld seam and ligaments, cold layout
    t_cold = r['liner_wall_thickness_mm'] / sc / 1e3
    lig_min = max(2 * t_cold, 0.0015)
    row('ligament minimum max(2 t_cold, 1.5 mm) [m]', lig_min, lay['ligament_min_m'], 1e-9)
    radius = {'outer': r['outer_liner_id_cold_mm'] / 2e3, 'inner': r['inner_liner_od_cold_mm'] / 2e3}
    checks = {q['name']: q for q in c['layout_checks']}
    for side in ('outer', 'inner'):
        R = radius[side]
        holes = [(q['row'], q['x_from_dome_m'], a, q['dia_m']) for q in rows if q['side'] == side for a in q['angles_deg']]
        best = 1e9
        for i in range(len(holes)):
            for j in range(i + 1, len(holes)):
                dth = math.radians(min(abs(holes[i][2] - holes[j][2]), 360 - abs(holes[i][2] - holes[j][2])))
                best = min(best, math.hypot(holes[i][1] - holes[j][1], R * dth) - 0.5 * (holes[i][3] + holes[j][3]))
        row(f'{side} liner minimum ligament, all pairs [m]', best, lay['closest_pairs'][side]['distance_m'], 1e-9)

        def hits(seam):
            return [h for h in holes if R * math.radians(min(abs(h[2] - seam) % 360, 360 - abs(h[2] - seam) % 360))
                    < 0.003 + h[3] / 2]
        seam = lay['seam_angle_deg'][side]
        h0 = hits(seam)
        row(f'{side} liner seam hits at {seam:.2f} deg [count]', len(h0),
            checks[f'{side} liner holes clear of weld seam at {seam:.2f} deg']['value'], 0.0,
            note=', '.join(f'{h[0]}@{h[2]}deg d={h[3] * 1e3:.2f}mm' for h in h0))
        best_seam = min((len(hits(0.05 * k)), 0.05 * k) for k in range(7200))
        row(f'{side} liner: no seam angle clears the 3 mm band (min hits over 0.05 deg scan >= 1)', best_seam[0] >= 1, None,
            note=f'min {best_seam[0]} hit at {best_seam[1]:.2f} deg (seam through one dilution hole); '
                 f'the reported angle maximises edge clearance and gives {len(h0)} hits; failure is intrinsic to the pitch')
        # seam angle that maximises the minimum edge clearance to MAIN holes (the code's documented rule)
        main = [h for h in holes if h[0] in ('primary', 'secondary', 'dilution')]

        def clearance(th):
            return min(R * math.radians(min(abs(h[2] - th), 360 - abs(h[2] - th))) - h[3] / 2 for h in main)
        best_clear = max(clearance(0.25 * k) for k in range(1440))
        row(f'{side} liner: max achievable seam-to-main-hole edge clearance [m] vs 3 mm band', best_clear,
            clearance(seam), 1e-9, note='reported seam angle is (one of) the max-clearance positions')
        dil = [q for q in rows if q['side'] == side and q['row'] == 'dilution'][0]
        pitch_arc = R * 2 * math.pi / dil['count']
        row(f'{side} dilution arc pitch vs 2*(3 mm + r) needed for a clear band [m]', pitch_arc,
            2 * (0.003 + dil['dia_m'] / 2), kind='info')


# ----------------------------------------------------------------------------- 3. structures
def check_structures():
    section('3. Structures')
    st = load('structures.json')
    stack = load('assembly_stack.json')
    dp = load('design_point.json')['point']
    mats = yaml.safe_load(Path('data/components/materials.yaml').read_text())['parameters']
    N = dp['N_rpm']
    w = N * 2 * math.pi / 60
    P_c, P_b, P_t = dp['powers']['P_compressor_W'], dp['powers']['P_bearings_W'], dp['powers']['P_turbine_W']
    T = (P_c + 0.5 * P_b) / w
    row('torque at compressor seat (P_c + 0.5 P_brg)/omega [N m]', T, st['torque_Nm'], 1e-6)
    row('torque leaving the turbine P_t/omega [N m] (rear sections)', P_t / w, P_t / w, kind='info')
    secs = {s['name']: s for s in stack['shaft_sections']}
    d = min(s['od_m'] for s in stack['shaft_sections'] if 'seat' in s['name'] or 'journal' in s['name'] or s['name'] == 'body')
    tau = 16 * T / (math.pi * d ** 3)
    row('tau_nom = 16T/(pi d^3) on the 6 mm seat [Pa] (30.5 MPa claimed)', tau, st['shaft']['tau_nom_Pa'], 1e-6)
    m_c = [q for q in stack['rotating_masses'] if q['name'] == 'compressor wheel'][0]['mass_kg']
    e = 2.5e-3 / w                                   # G2.5 at the 68 krpm maximum continuous speed
    M = m_c * (e * w * w + 3 * 9.81) * stack['summary']['comp_overhang_m']
    row('bending moment m_c(e w^2 + 3g) * overhang [N m]', M, st['bending_moment_Nm'], 1e-6)
    sig = 32 * M / (math.pi * d ** 3)
    row('sigma_b nominal [Pa]', sig, st['shaft']['sigma_b_nom_Pa'], 1e-6)
    vm = math.sqrt((2.0 * sig) ** 2 + 3 * (1.6 * tau) ** 2)
    row('von Mises peak, Kt 2.0 bending / 1.6 torsion [Pa] (84.6 MPa)', vm, st['shaft']['von_mises_peak_Pa'], 1e-6)
    row('limit 0.5 x 4140 yield (materials.yaml) [Pa]', 0.5 * mats['s4140_yield_RT']['value'] * 1e6,
        [q for q in st['checks'] if q['name'].startswith('shaft peak')][0]['limit'], 1e-9)
    row('alternating bending sigma_b,peak [Pa] (6.0 MPa)', 2.0 * sig, st['shaft']['sigma_b_peak_Pa'], 1e-6)
    row('endurance limit 0.6 x 400 MPa [Pa]', 0.6 * mats['s4140_endurance_RT']['value'] * 1e6,
        [q for q in st['checks'] if q['name'].startswith('shaft alternating')][0]['limit'], 1e-9)
    # coverage: threaded ends are excluded from d_min
    for nm in ('front thread M6 (minor dia)', 'rear thread M8 (minor dia)'):
        dd = secs[nm]['od_m']
        Tq = T if 'front' in nm else P_t / w
        row(f'tau if full torque passed the {nm} [Pa]', 16 * Tq / (math.pi * dd ** 3), tau, kind='info',
            note='threads excluded from the check; nut clamp preload not modelled')
    # liner buckling (Windenburg-Trilling)
    b = st['liner_buckling']
    D, t, Lb, E, nu = b['D_m'], b['t_m'], b['L_m'], b['E_Pa'], 0.3
    c = load('combustor.json')['library_result']
    row('buckling D = outer liner OD cold [m]', D, c['outer_liner_od_cold_mm'] / 1e3, 1e-9)
    row('buckling t = cold wall [m]', t, c['liner_wall_thickness_mm'] / c['thermal_scale_ratio'] / 1e3, 1e-9)
    p_el = 2.42 * E / (1 - nu * nu) ** 0.75 * (t / D) ** 2.5 / (Lb / D - 0.45 * math.sqrt(t / D))
    row('p_cr elastic [Pa]', p_el, b['p_cr_elastic_Pa'], 1e-6)
    ratio = 0.5 * p_el / c['dP_outer_holes_Pa']
    row('buckling margin p_cr*0.5 / external dP (1298 claimed)', ratio,
        [q for q in st['checks'] if 'buckling' in q['name']][0]['value'], 1e-6)
    row('E used (hard-coded 175 GPa) vs materials 316 E at 900 K / RT [Pa]', E, mats['ss316_E_900K']['value'] * 1e9,
        kind='info', note=f"materials.yaml: RT {mats['ss316_E_RT']['value']} GPa, 900 K {mats['ss316_E_900K']['value']} GPa")
    # casing hoop
    stn = dp['stations']
    hoop = (stn['P3_Pa'] - stn['P0_Pa']) * 0.1524 / 2 / 0.001524
    row('casing hoop (P3-P0) r_o / t [Pa]', hoop, st['casing_hoop_Pa'], 1e-6)
    row('limit 0.3 x 316 yield [Pa]', 0.3 * mats['ss316_yield_RT']['value'] * 1e6,
        [q for q in st['checks'] if 'hoop' in q['name']][0]['limit'], 1e-9)
    # tip clearance
    cl = load('clearances.json')
    tr = dp['turbine']
    far = dp['flows']['FAR_mixed']
    T_rel = tr['T1_K'] + tr['W1_m_s'] ** 2 / (2 * gas.cp_products(tr['T1_K'], far))
    T_tip = T_rel - 30.0
    T_sh = 0.85 * stn['T41_K'] + 0.15 * stn['T3_K']
    at = cl['assumed_temperatures_K']
    row('rotor relative total T [K]', T_rel, at['rotor_relative_total'], 1e-6)
    row('NGV shroud T = 0.85 T41 + 0.15 T3 [K]', T_sh, at['ngv_shroud'], 1e-9)
    r_tip, b_hub, c0 = 0.0425, 0.0275, 0.00035
    a_w = mats['ni_cast_alpha_mean_to_1000K']['value']
    a_s = mats['ngv_alpha_mean']['value']
    lo_s, hi_s = mats['ngv_alpha_mean']['range']
    E_w = mats['ni_cast_E_1000K']['value'] * 1e9
    rho_w = 8000.0

    def tip(Tw, Ts, Nrpm, aw, as_):
        om = Nrpm * 2 * math.pi / 60
        th_w = aw * r_tip * (Tw - 293.0)
        disc = (1 - nu) * rho_w * om ** 2 * b_hub ** 3 / (4 * E_w)
        h = r_tip - b_hub      # constant-section blade stretch, exact integral
        blade = rho_w * om ** 2 / (2 * E_w) * (r_tip ** 2 * h - (r_tip ** 3 - b_hub ** 3) / 3)
        th_s = as_ * (r_tip + c0) * (Ts - 293.0)
        return c0 + th_s - th_w - disc - blade, disc + blade
    for key, args in (('nominal', (T_tip, T_sh, N, a_w, a_s)), ('low_shroud_alpha', (T_tip, T_sh, N, a_w, lo_s)),
                      ('high_shroud_alpha', (T_tip, T_sh, N, a_w, hi_s)),
                      ('shutdown_bound', (T_tip, stn['T3_K'] + 50.0, 0.3 * N, a_w, a_s))):
        hot, cf = tip(*args)
        row(f'tip clearance hot, {key} [m]', hot, cl['tip'][key]['hot_m'], 0.01)
        row(f'  centrifugal growth (disc + exact blade stretch), {key} [m]', cf, cl['tip'][key]['wheel_centrifugal_m'],
            0.10, note='code blade term is an approximation of the same integral')
    worst = tip(T_rel, stn['T3_K'] + 50.0, 0.3 * N, mats['ni_cast_alpha_mean_to_1000K']['range'][1], lo_s)[0]
    row('shutdown bound, worst corners (tip at T_rel, wheel alpha high, shroud alpha low) [m]', worst, 0.0, kind='info',
        note='stays positive')


if __name__ == '__main__':
    print(f'results folder: {RES}')
    check_nozzle()
    check_combustor()
    check_structures()
    print('\nunexplained differences:', FAILS or 'none')
    sys.exit(1 if FAILS else 0)
