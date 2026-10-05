"""Fork-A independent check of R3 (turbine outlet closure) and the turbine mean line.

Usage (from the repository root):
    python <this script> [results_dir] [pre_review_run_dir]
Defaults: docs/design/results/pd1-jm85  and  out/pd1-jm85/af33609c34b6

Independence: imports core.gas for PROPERTIES only (via indep_props). Does not import
core.turbine_rating / core.engine_match / core.thermo / modules. Geometry is read from the
component records (data/components/*.yaml), not from the run output, and then compared with the
geometry echoed in design_point.json.

Part A  R3 residuals of the REPORTED design-point turbine state (energy, Euler, continuity, eta_tt, T05).
Part B  Independent re-rating from the reported inlet state with the documented method
        (Soderberg + aspect + Reynolds corrections, cosine-rule throats, tip-leakage work debit,
        mixed-out exit at passage static pressure) and comparison of every reported output.
Part C  Sensitivities (INFO only): Reynolds-correction iteration, tip-leakage effect on eta_tt,
        loss multipliers, viscosity model.
Part D  Pre-review run: energy mismatch of its reported exit state (the R3 defect).
Exit status 1 if any comparison in A or B differs by more than its tolerance.
"""
import math
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from indep_props import (R, h, T_of_h, T_isentropic, P_isentropic, gamma, soderberg,  # noqa: E402
                         throat_hydraulic_diameter, mu_repo_power_law, mu_sutherland_air,
                         load_results, Reporter, T_LO)
from scipy.optimize import brentq, minimize_scalar  # noqa: E402

folder = sys.argv[1] if len(sys.argv) > 1 else 'docs/design/results/pd1-jm85'
pre_folder = sys.argv[2] if len(sys.argv) > 2 else 'out/pd1-jm85/af33609c34b6'
rep = Reporter(tol_pct=1.0)


def rec_params(path):
    with open(path, encoding='utf-8') as fh:
        return yaml.safe_load(fh)['parameters']


tw = rec_params('data/components/turbine_jetmax_tw85.yaml')
ng = rec_params('data/components/ngv_jetmax_ngv85.yaml')
mm = 1e-3
geom = dict(r_hub=tw['hub_diameter']['value'] * mm / 2, r_tip=tw['tip_diameter']['value'] * mm / 2,
            ngv_r_hub=ng['vane_hub_diameter']['value'] * mm / 2, ngv_r_tip=ng['vane_tip_diameter']['value'] * mm / 2,
            alpha1=ng['exit_flow_angle']['value'], beta2=tw['rotor_exit_relative_angle']['value'],
            bN=ng['vane_axial_chord']['value'] * mm, bR=tw['blade_axial_width_at_rim']['value'] * mm,
            n_ngv=int(ng['vane_count_estimate']['value']), n_rotor=int(tw['blade_count_estimate']['value']),
            clr=tw['tip_clearance_design']['value'] * mm, K_tip=2.0)

j = load_results(folder)
dp = j('design_point.json')
pt = dp['point']
t = pt['turbine']
st = dp['engine']['stage']
fl = pt['flows']
f_mix = fl['FAR_mixed']
mdot = t['mdot_kg_s']
N = t['N_rpm']

print(f'== Fork-A turbine check on {folder}  (N = {N} rpm, FAR_mix = {f_mix:.6f})')
print('-- geometry: component records vs geometry echoed in design_point.json')
for k_rec, k_dp in (('r_hub', 'r_hub_m'), ('r_tip', 'r_tip_m'), ('ngv_r_hub', 'ngv_r_hub_m'),
                    ('ngv_r_tip', 'ngv_r_tip_m'), ('alpha1', 'alpha1_deg'), ('beta2', 'beta2_deg'),
                    ('bN', 'ngv_axial_chord_m'), ('bR', 'rotor_axial_chord_m'), ('n_ngv', 'ngv_count'),
                    ('n_rotor', 'rotor_count'), ('clr', 'tip_clearance_m'), ('K_tip', 'K_tip')):
    rep.cmp(f'geometry {k_rec}', float(geom[k_rec]), float(st[k_dp]), tol_pct=1e-9)

rm = 0.5 * (geom['r_hub'] + geom['r_tip'])
HR = geom['r_tip'] - geom['r_hub']
HN = geom['ngv_r_tip'] - geom['ngv_r_hub']
AR = math.pi * (geom['r_tip'] ** 2 - geom['r_hub'] ** 2)
AN_exit = math.pi * (geom['ngv_r_tip'] ** 2 - geom['ngv_r_hub'] ** 2)
U = N * 2 * math.pi / 60 * rm

# --------------------------------------------------------------------------------------- Part A
print('\n-- Part A: R3 residuals of the reported design-point turbine state')
T01, P01, T02, P02, w, wE = t['T01_K'], t['P01_Pa'], t['T02_K'], t['P02_Pa'], t['w_J_kg'], t['w_euler_J_kg']
h01, h02 = h(T01, f_mix), h(T02, f_mix)
rep.cmp('A1 h01 - h02 (T41 -> T5 total) vs reported w [J/kg]', h01 - h02, w, abs_tol=1.0,
        note=f'residual {h01 - h02 - w:+.4f} J/kg')
a1 = math.radians(t['alpha1_deg'])
Ct1, Cx1 = t['C1_m_s'] * math.sin(a1), t['C1_m_s'] * math.cos(a1)
b2 = math.radians(t['beta2_deg'])
Cx2, Ct2 = t['W2_m_s'] * math.cos(b2), U + t['W2_m_s'] * math.sin(b2)
rep.cmp('A2 Euler U(Ct1-Ct2) passage triangle [J/kg]', U * (Ct1 - Ct2), wE, tol_pct=1e-6)
rep.cmp('A3 delivered w = w_Euler (1 - K_tip c/H) [J/kg]', wE * (1 - geom['K_tip'] * geom['clr'] / HR), w, tol_pct=1e-6)
mx = t['mixed_exit']
rep.cmp('A4 Euler at mixed plane U(Ct1-Ct_mix) [J/kg]', U * (Ct1 - mx['Ct_m_s']), w, tol_pct=1e-6)
lhs = h(mx['T_static_K'], f_mix) + 0.5 * (mx['Cx_m_s'] ** 2 + mx['Ct_m_s'] ** 2)
rep.cmp('A5 mixed-plane energy h5 + C5^2/2 vs h05 [J/kg]', lhs, h02, abs_tol=1.0, note=f'residual {lhs - h02:+.4f} J/kg')
rho5 = mx['P_static_Pa'] / (R * mx['T_static_K'])
rep.cmp('A6 exit continuity rho5 Cx5 A_annulus vs mdot [kg/s]', rho5 * mx['Cx_m_s'] * AR, mdot, tol_pct=1e-4)
rho2 = t['P2_Pa'] / (R * t['T2_K'])
rep.cmp('A7 passage continuity rho2 W2 cos(b2) A_annulus [kg/s]', rho2 * Cx2 * AR, mdot, tol_pct=1e-4)
rho1 = t['P1_Pa'] / (R * t['T1_K'])
rep.cmp('A8 NGV continuity rho1 C1 cos(a1) A_ngv_exit [kg/s]', rho1 * Cx1 * AN_exit, mdot, tol_pct=1e-4)
h2p = h(t['T2_K'], f_mix) + 0.5 * t['C2_m_s'] ** 2
rep.cmp('A9 passage energy h2 + C2^2/2 vs h01 - w_Euler [J/kg]', h2p, h01 - wE, abs_tol=1.0,
        note=f'residual {h2p - (h01 - wE):+.4f} J/kg')
P02_check = P_isentropic(T02, mx['T_static_K'], mx['P_static_Pa'], f_mix)
rep.cmp('A10 P05 = isentropic stagnation of mixed static state [Pa]', P02_check, P02, tol_pct=1e-4)
T02s = T_isentropic(T01, P02 / P01, f_mix)
rep.cmp('A11 eta_tt = w / (h01 - h(T05s)) own isentropic', w / (h01 - h(T02s, f_mix)), t['eta_tt'], tol_pct=1e-4)
rep.cmp('A12 T05 from energy balance h(T05) = h01 - w [K]', T_of_h(h01 - w, f_mix), T02, tol_pct=1e-6)
rep.cmp('A13 turbine power mdot w [W]', mdot * w, pt['powers']['P_turbine_W'], tol_pct=1e-9)
rep.cmp('A14 psi = w/U^2', w / U ** 2, t['psi'], tol_pct=1e-6)
rep.cmp('A15 phi = Cx2/U (passage Cx)', Cx2 / U, t['phi'], tol_pct=1e-6)
rep.cmp('A16 U at mean radius [m/s]', U, t['U_mean_m_s'], tol_pct=1e-9)
h1 = h(t['T1_K'], f_mix)
rep.cmp('A17 reaction (h1-h2)/(h01-h02,passage)', (h1 - h(t['T2_K'], f_mix)) / (h01 - h2p), t['reaction'], tol_pct=1e-4)


# --------------------------------------------------------------------------------------- Part B
def rate(mdot, T01, P01, N, f, mu=mu_sutherland_air, loss_mult=1.0, K_tip=2.0, re_mode='one_update'):
    """Independent implementation of the documented mean-line method."""
    U = N * 2 * math.pi / 60 * rm
    sN = 2 * math.pi * rm / geom['n_ngv']      # NOTE: repository uses the ROTOR mean radius for the NGV pitch
    sR = 2 * math.pi * rm / geom['n_rotor']
    a1d, b2d = geom['alpha1'], geom['beta2']
    AN_t = AN_exit * math.cos(math.radians(a1d))
    AR_t = AR * math.cos(math.radians(b2d))
    h01 = h(T01, f)

    def subsonic(state, A, vmax):
        r = minimize_scalar(lambda v: -state(v)[2] * v * A, bounds=(1.0, vmax), method='bounded',
                            options={'xatol': 1e-8})
        vstar, fmax = r.x, -r.fun
        if mdot > fmax:
            raise RuntimeError('choked')
        v = brentq(lambda v: state(v)[2] * v * A - mdot, 1e-3, vstar, xtol=1e-12, rtol=1e-15)
        return v, mdot / fmax

    zN0 = soderberg(a1d, geom['bN'], HN, 'nozzle') * loss_mult

    def ngv(C, z):
        h1 = h01 - 0.5 * C * C
        T1 = T_of_h(h1, f)
        P1 = P_isentropic(T_of_h(h1 - z * 0.5 * C * C, f), T01, P01, f)
        return T1, P1, P1 / (R * T1)

    vN = math.sqrt(2 * (h01 - h(0.5 * T01, f)))
    dhN = throat_hydraulic_diameter(sN, HN, a1d)
    C1, _ = subsonic(lambda v: ngv(v, zN0), AN_t, vN)
    T1, P1, r1 = ngv(C1, zN0)
    ReN1 = r1 * C1 * dhN / mu(T1)
    zN = zN0 * (1e5 / ReN1) ** 0.25
    C1, fracN = subsonic(lambda v: ngv(v, zN), AN_t, vN)
    T1, P1, r1 = ngv(C1, zN)
    if re_mode == 'converged':
        for _ in range(60):
            zn = zN0 * (1e5 / (r1 * C1 * dhN / mu(T1))) ** 0.25
            if abs(zn - zN) < 1e-13:
                break
            zN = zn
            C1, fracN = subsonic(lambda v: ngv(v, zN), AN_t, vN)
            T1, P1, r1 = ngv(C1, zN)
    ReN_final = r1 * C1 * dhN / mu(T1)
    a1r = math.radians(a1d)
    Cx1, Ct1 = C1 * math.cos(a1r), C1 * math.sin(a1r)
    Wt1 = Ct1 - U
    W1 = math.hypot(Cx1, Wt1)
    beta1 = math.degrees(math.atan2(Wt1, Cx1))
    h1 = h(T1, f)
    I = h1 + 0.5 * W1 * W1          # rothalpy at constant radius
    epsR = abs(beta1 - b2d)
    zR0 = soderberg(epsR, geom['bR'], HR, 'rotor') * loss_mult

    def rot(W, z):
        h2 = I - 0.5 * W * W
        T2 = T_of_h(h2, f)
        P2 = P_isentropic(T_of_h(h2 - z * 0.5 * W * W, f), T1, P1, f)
        return T2, P2, P2 / (R * T2)

    vR = math.sqrt(2 * (I - h(0.5 * T1, f)))
    dhR = throat_hydraulic_diameter(sR, HR, b2d)
    W2, _ = subsonic(lambda v: rot(v, zR0), AR_t, vR)
    T2, P2, r2 = rot(W2, zR0)
    ReR1 = r2 * W2 * dhR / mu(T2)
    zR = zR0 * (1e5 / ReR1) ** 0.25
    W2, fracR = subsonic(lambda v: rot(v, zR), AR_t, vR)
    T2, P2, r2 = rot(W2, zR)
    if re_mode == 'converged':
        for _ in range(60):
            zr = zR0 * (1e5 / (r2 * W2 * dhR / mu(T2))) ** 0.25
            if abs(zr - zR) < 1e-13:
                break
            zR = zr
            W2, fracR = subsonic(lambda v: rot(v, zR), AR_t, vR)
            T2, P2, r2 = rot(W2, zR)
    ReR_final = r2 * W2 * dhR / mu(T2)
    b2r = math.radians(b2d)
    Cx2, Ct2 = W2 * math.cos(b2r), U + W2 * math.sin(b2r)
    C2 = math.hypot(Cx2, Ct2)
    wE = U * (Ct1 - Ct2)
    h2 = h(T2, f)
    h02p = h2 + 0.5 * C2 * C2
    w = wE * (1 - K_tip * geom['clr'] / HR)
    h02 = h01 - w
    T02 = T_of_h(h02, f)
    Ctm = Ct1 - w / U
    k = mdot * R / (P2 * AR)
    T2m = brentq(lambda T: h(T, f) + 0.5 * ((k * T) ** 2 + Ctm ** 2) - h02, T_LO, T02, xtol=1e-12)
    P02 = P_isentropic(T02, T2m, P2, f)
    T02s = T_isentropic(T01, P02 / P01, f)
    T2is = T_isentropic(T01, P2 / P01, f)
    g1, g2 = gamma(T1, f), gamma(T2, f)
    return dict(U_mean_m_s=U, C1_m_s=C1, T1_K=T1, P1_Pa=P1, M1=C1 / math.sqrt(g1 * R * T1), W1_m_s=W1,
                beta1_deg=beta1, M1_rel=W1 / math.sqrt(g1 * R * T1), T2_K=T2, P2_Pa=P2, W2_m_s=W2,
                M2_rel=W2 / math.sqrt(g2 * R * T2), C2_m_s=C2, M2=C2 / math.sqrt(g2 * R * T2),
                alpha2_exit_swirl_deg=math.degrees(math.atan2(Ct2, Cx2)), Cx2_m_s=Cx2,
                T02_passage_K=T_of_h(h02p, f), w_euler_J_kg=wE, w_J_kg=w, power_W=mdot * w, T02_K=T02,
                P02_Pa=P02, PR_tt=P01 / P02, PR_ts=P01 / P2, eta_tt=w / (h01 - h(T02s, f)),
                eta_ts=w / (h01 - h(T2is, f)), psi=w / U ** 2, phi=Cx2 / U, reaction=(h1 - h2) / (h01 - h02p),
                zeta_ngv=zN, zeta_rotor=zR, Re_ngv=ReN1, Re_rotor=ReR1, Re_ngv_final=ReN_final,
                Re_rotor_final=ReR_final, ngv_flow_fraction_of_max=fracN, rotor_flow_fraction_of_max=fracR,
                A_ngv_throat_m2=AN_t, A_rotor_throat_m2=AR_t, tip_work_factor=1 - K_tip * geom['clr'] / HR,
                energy_residual_J_kg=(h01 - h02p) - wE,
                mixed_T_static_K=T2m, mixed_Cx_m_s=k * T2m, mixed_Ct_m_s=Ctm,
                mixed_C_m_s=math.hypot(k * T2m, Ctm), zetaN_base=zN0, zetaR_base=zR0, deflection_R=epsR,
                fRe_N=(1e5 / ReN1) ** 0.25, fRe_R=(1e5 / ReR1) ** 0.25)


print('\n-- Part B: independent re-rating from the reported inlet state (T41, P41, mdot, N, FAR_mix)')
mine = rate(mdot, T01, P01, N, f_mix)
for key in ('U_mean_m_s', 'C1_m_s', 'T1_K', 'P1_Pa', 'M1', 'W1_m_s', 'beta1_deg', 'M1_rel', 'T2_K', 'P2_Pa',
            'W2_m_s', 'M2_rel', 'C2_m_s', 'M2', 'alpha2_exit_swirl_deg', 'Cx2_m_s', 'T02_passage_K', 'w_euler_J_kg',
            'w_J_kg', 'power_W', 'T02_K', 'P02_Pa', 'PR_tt', 'PR_ts', 'eta_tt', 'eta_ts', 'psi', 'phi', 'reaction',
            'zeta_ngv', 'zeta_rotor', 'Re_ngv', 'Re_rotor', 'ngv_flow_fraction_of_max',
            'rotor_flow_fraction_of_max', 'A_ngv_throat_m2', 'A_rotor_throat_m2', 'tip_work_factor'):
    rep.cmp(f'B {key}', mine[key], t[key], tol_pct=1.0)
for key, rk in (('mixed_T_static_K', 'T_static_K'), ('mixed_Cx_m_s', 'Cx_m_s'), ('mixed_Ct_m_s', 'Ct_m_s'),
                ('mixed_C_m_s', 'C_m_s')):
    rep.cmp(f'B mixed_exit.{rk}', mine[key], mx[rk], tol_pct=1.0)
rep.info('B Soderberg NGV: zeta* + aspect (no Re)', mine['zetaN_base'], f'x fRe {mine["fRe_N"]:.4f}')
rep.info('B Soderberg rotor: zeta* + aspect (no Re)', mine['zetaR_base'],
         f'x fRe {mine["fRe_R"]:.4f}; deflection {mine["deflection_R"]:.2f} deg')
rep.info('B energy residual passage plane [J/kg]', mine['energy_residual_J_kg'])

# --------------------------------------------------------------------------------------- Part C
print('\n-- Part C: sensitivities (INFO; same inlet state and mass flow, no re-match)')
conv = rate(mdot, T01, P01, N, f_mix, re_mode='converged')
rep.info('C Re-correction iterated to convergence: eta_tt', conv['eta_tt'],
         f'one-update {mine["eta_tt"]:.6f}; Re_N final {mine["Re_ngv_final"]:.0f} vs first {mine["Re_ngv"]:.0f}; '
         f'Re_R final {mine["Re_rotor_final"]:.0f} vs first {mine["Re_rotor"]:.0f}')
no_tip = rate(mdot, T01, P01, N, f_mix, K_tip=0.0)
rep.info('C eta_tt with K_tip = 0 (no tip-leakage debit)', no_tip['eta_tt'],
         f'K_tip 2 -> {mine["eta_tt"]:.4f}: eta drop {no_tip["eta_tt"] - mine["eta_tt"]:.4f} '
         f'({100 * (1 - mine["eta_tt"] / no_tip["eta_tt"]):.2f} % rel) vs work debit '
         f'{100 * (1 - mine["tip_work_factor"]):.2f} %')
for lm in (1.5, 2.0, 3.0):
    try:
        r_ = rate(mdot, T01, P01, N, f_mix, loss_mult=lm)
        rep.info(f'C eta_tt with Soderberg losses x{lm}', r_['eta_tt'], f'w {r_["w_J_kg"]:.0f} J/kg')
    except RuntimeError as e:
        rep.info(f'C eta_tt with Soderberg losses x{lm}', str(e))
old = rate(mdot, T01, P01, N, f_mix, mu=mu_repo_power_law)
rep.info('C pre-fix power-law viscosity: Re_ngv', old['Re_ngv'], f'Sutherland (current) {mine["Re_ngv"]:.0f}')
rep.info('C pre-fix power-law viscosity: Re_rotor', old['Re_rotor'], f'Sutherland (current) {mine["Re_rotor"]:.0f}')
rep.info('C pre-fix power-law viscosity: eta_tt', old['eta_tt'], f'Sutherland (current) {mine["eta_tt"]:.4f}')
rep.info('C mu ratio Sutherland/pre-fix law at T1, T2',
         f'{mu_sutherland_air(t["T1_K"]) / mu_repo_power_law(t["T1_K"]):.3f}, '
         f'{mu_sutherland_air(t["T2_K"]) / mu_repo_power_law(t["T2_K"]):.3f}')

# --------------------------------------------------------------------------------------- Part D
print(f'\n-- Part D: pre-review run {pre_folder} (pre-R3 logic)')
try:
    pj = load_results(pre_folder)('design_point.json')
    pp = pj['point']
    pt_ = pp['turbine']
    fpre = pp['flows']['FAR_mixed']
    h01p, h02p_ = h(pt_['T01_K'], fpre), h(pt_['T02_K'], fpre)
    rep.info('D pre-review: has mixed_exit block', 'mixed_exit' in pt_)
    rep.info('D pre-review: station 5 static T equals passage T2',
             abs(pp['stations']['T5_static_K'] - pt_['T2_K']) < 1e-9)
    e_exit = h(pt_['T2_K'], fpre) + 0.5 * pt_['C2_m_s'] ** 2 - h02p_
    rep.info('D pre-review: h(T5s) + C2^2/2 - h(T05) [J/kg]', e_exit,
             f'= -(w_Euler - w) = {-(pt_["w_euler_J_kg"] - pt_["w_J_kg"]):.1f} J/kg expected if T05 debited but '
             'exit velocity/static state undebited')
    P05_from_passage_total = P_isentropic(T_of_h(h(pt_['T2_K'], fpre) + 0.5 * pt_['C2_m_s'] ** 2, fpre),
                                          pt_['T2_K'], pt_['P2_Pa'], fpre)
    rep.info('D pre-review: reported P05 vs isentropic stagnation of passage state',
             f'{pt_["P02_Pa"]:.2f} vs {P05_from_passage_total:.2f} Pa',
             '(equal => P05 came from the undebited passage state while T05 used the debited work)')
    rep.info('D pre-review: h01 - h05 - w [J/kg]', h01p - h02p_ - pt_['w_J_kg'])
    T5_alt = T_of_h(h02p_ - 0.5 * pt_['C2_m_s'] ** 2, fpre)
    P05_alt = P_isentropic(pt_['T02_K'], T5_alt, pt_['P2_Pa'], fpre)
    rep.info('D pre-review: P05 from static T(h05 - C2^2/2) at P2 vs reported [Pa]',
             f'{P05_alt:.3f} vs {pt_["P02_Pa"]:.3f}',
             f'implied static {T5_alt:.3f} K vs reported station-5 static {pp["stations"]["T5_static_K"]:.3f} K')
except FileNotFoundError as e:
    rep.info('D pre-review run not found', str(e))

sys.exit(rep.finish())
