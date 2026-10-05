"""Independent reference model for the PD-1 audit (fork B: compressor map + matching).

Independence rule: the ONLY repository import is core.gas, used for the cp/h
property functions (allowed by the review handoff). Everything else is written
here from the stated equations (module docstrings, case file, component records
and textbook relations), NOT imported from the code under test:

  * entropy by numerical quadrature of cp/T (not core.thermo.entropy)
  * isentropic relations and temperature inversion (own Newton/brentq)
  * map reading, beta definition and interpolation (own parser)
  * turbine mean line (cosine-rule throats, Soderberg + aspect + Reynolds,
    rothalpy, tip-work debit, mixed-out exit) re-coded from the stated method
  * convergent nozzle with Cv on kinetic energy and Cd on mass flow
  * bearing (Palmgren viscous + load moment) and disc windage powers
  * the ledger 0-2-3-31-4-41-5-7-8 and a nested brentq matching solver

Run every script from the repository root.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import yaml
from scipy.integrate import cumulative_simpson
from scipy.interpolate import CubicSpline, PchipInterpolator
from scipy.optimize import brentq, minimize_scalar

ROOT = Path.cwd()
if not (ROOT / 'core' / 'gas.py').is_file():
    raise SystemExit('run from the repository root (core/gas.py not found)')
sys.path.insert(0, str(ROOT))
from core import gas  # noqa: E402  (properties only)

R = 287.05
LB_MIN_TO_KG_S = 0.45359237 / 60.0
T_REF_545R = 545.0 * 5.0 / 9.0           # 302.7778 K
P_REF_284INHG = 28.4 * 3386.389           # 96,173.4 Pa (inHg at 0 degC)


# ----------------------------------------------------------------------------- properties
_TG = np.linspace(200.0, 1900.0, 17001)   # 0.1 K grid
_CP = np.array([gas.cp_air(float(t)) for t in _TG])
_S = cumulative_simpson(_CP / _TG, x=_TG, initial=0.0)
_S_SPLINE = CubicSpline(_TG, _S)


def kfar(far):
    """cp_products/cp_air (checked to be T-independent at two temperatures)."""
    k1 = gas.cp_products(500.0, far) / gas.cp_air(500.0)
    k2 = gas.cp_products(1500.0, far) / gas.cp_air(1500.0)
    assert abs(k1 - k2) < 1e-12, 'products cp not proportional to air cp'
    return k1


def s(T, far=0.0):
    return kfar(far) * float(_S_SPLINE(T))


def h(T, far=0.0):
    return gas.h_products(T, far)


def cp(T, far=0.0):
    return gas.cp_products(T, far)


def T_from_h(hv, far=0.0):
    t = min(max(300.0 + hv / 1100.0, 201.0), 1899.0)
    for _ in range(40):
        d = (gas.h_products(t, far) - hv) / gas.cp_products(t, far)
        t -= d
        if not 200.0 < t < 1900.0:
            break
        if abs(d) < 1e-11:
            return t
    return brentq(lambda T: gas.h_products(T, far) - hv, 200.0, 1900.0, xtol=1e-12)


def T_isentropic(T1, pressure_ratio, far=0.0):
    """Temperature reached isentropically from T1 at pressure ratio P2/P1."""
    target = s(T1, far) + R * math.log(pressure_ratio)
    return brentq(lambda T: s(T, far) - target, 200.0, 1900.0, xtol=1e-11)


def P_isentropic(T2, T1, P1, far=0.0):
    return P1 * math.exp((s(T2, far) - s(T1, far)) / R)


def gamma(T, far=0.0):
    c = cp(T, far)
    return c / (c - R)


# ----------------------------------------------------------------------------- compressor map
class OffMap(ValueError):
    pass


class Map:
    """Digitized map, beta linear in corrected flow along each line (0 surge end,
    1 choke end), PCHIP (or linear) along the line, linear in corrected speed at
    constant beta between lines. No extrapolation."""

    def __init__(self, csv_path='data/maps/gt3076r_compressor_digitized.csv', T_ref=302.78, P_ref=96174.0,
                 along='pchip', across='linear'):
        L, E = {}, {}
        with open(ROOT / csv_path, newline='', encoding='utf-8') as f:
            for r in csv.DictReader(f):
                n = float(r['speed_line_rpm_corrected'])
                if r['record'] == 'line':
                    L.setdefault(n, []).append((float(r['Q_corr_lb_min']), float(r['PR'])))
                elif r['record'] == 'eta':
                    E.setdefault(n, []).append((float(r['Q_corr_lb_min']), float(r['eta_isen_tt'])))
        self.T_ref, self.P_ref, self.along, self.across = T_ref, P_ref, along, across
        self.speeds = sorted(L)
        self.lines = {}
        for n in self.speeds:
            q, pr = map(np.array, zip(*sorted(L[n])))
            qe, e = map(np.array, zip(*sorted(E[n])))
            q, qe = q * LB_MIN_TO_KG_S, qe * LB_MIN_TO_KG_S
            if along == 'pchip':
                fpr, fe = PchipInterpolator(q, pr), PchipInterpolator(qe, e)
            else:
                fpr = (lambda x, q=q, pr=pr: np.interp(x, q, pr))
                fe = (lambda x, qe=qe, e=e: np.interp(x, qe, e))
            self.lines[n] = dict(q=q, pr=pr, qe=qe, e=e, fpr=fpr, fe=fe)

    def line_point(self, n, beta):
        d = self.lines[n]
        q = d['q'][0] + beta * (d['q'][-1] - d['q'][0])
        qe = min(max(q, d['qe'][0]), d['qe'][-1])
        return q, float(d['fpr'](q)), float(d['fe'](qe))

    def bracket(self, nc):
        if not self.speeds[0] - 1e-9 <= nc <= self.speeds[-1] + 1e-9:
            raise OffMap(f'corrected speed {nc:.0f} outside {self.speeds[0]:.0f}-{self.speeds[-1]:.0f}')
        for lo, hi in zip(self.speeds, self.speeds[1:]):
            if lo <= nc <= hi:
                return lo, hi
        return self.speeds[-1], self.speeds[-1]

    def point(self, nc, beta):
        if not -1e-12 <= beta <= 1 + 1e-12:
            raise OffMap(f'beta {beta} outside [0,1]')
        lo, hi = self.bracket(nc)
        a, b = self.line_point(lo, beta), self.line_point(hi, beta)
        if hi == lo:
            return a
        if self.across == 'linear':
            w = (nc - lo) / (hi - lo)
            return tuple((1 - w) * x + w * y for x, y in zip(a, b))
        # alternative: interpolate (PR-1) and Q in N^2 (tip-speed-squared scaling), eta linear in N
        w2 = (nc ** 2 - lo ** 2) / (hi ** 2 - lo ** 2)
        w = (nc - lo) / (hi - lo)
        q = (1 - w) * a[0] + w * b[0]
        pr = 1 + (1 - w2) * (a[1] - 1) + w2 * (b[1] - 1)
        return q, pr, (1 - w) * a[2] + w * b[2]

    def corrected_speed(self, N, T_in):
        return N / math.sqrt(T_in / self.T_ref)

    def corrected_flow(self, mdot, T_in, P_in):
        return mdot * math.sqrt(T_in / self.T_ref) / (P_in / self.P_ref)

    def actual_flow(self, q, T_in, P_in):
        return q * (P_in / self.P_ref) / math.sqrt(T_in / self.T_ref)

    def beta_for_q(self, nc, q):
        f = lambda b: self.point(nc, b)[0] - q
        if f(0.0) > 0 or f(1.0) < 0:
            raise OffMap(f'Q {q:.4f} kg/s outside line at {nc:.0f}')
        return brentq(f, 0.0, 1.0, xtol=1e-13)


def compressor(mp, N, beta, T_in, P_in, flow_scale=1.0, eta_delta=0.0, pr_rise_scale=1.0):
    nc = mp.corrected_speed(N, T_in)
    q, pr, eta = mp.point(nc, beta)
    q *= flow_scale
    pr = 1 + (pr - 1) * pr_rise_scale
    eta += eta_delta
    mdot = mp.actual_flow(q, T_in, P_in)
    T3s = T_isentropic(T_in, pr, 0.0)
    w = (h(T3s) - h(T_in)) / eta
    T3 = T_from_h(h(T_in) + w)
    qs = mp.point(nc, 0.0)[0] * flow_scale
    return dict(N_corr=nc, Q=q, PR=pr, eta=eta, mdot=mdot, T3=T3, P3=P_in * pr, w=w, SM_flow=1 - qs / q)


# ----------------------------------------------------------------------------- turbine mean line
class Choke(Exception):
    pass


@dataclass
class Stage:
    r_hub: float = 0.0275
    r_tip: float = 0.0425
    ngv_r_hub: float = 0.0277
    ngv_r_tip: float = 0.0435
    alpha1_deg: float = 65.0
    beta2_deg: float = -58.0
    ngv_chord: float = 0.012
    rotor_chord: float = 0.0075
    ngv_count: int = 20
    rotor_count: int = 30
    tip_clearance: float = 0.00035
    A_ngv_throat: float | None = None
    A_rotor_throat: float | None = None
    loss_scale: float = 1.0
    K_tip: float = 2.0

    @property
    def r_mean(self):
        return 0.5 * (self.r_hub + self.r_tip)

    def ngv(self):
        A_exit = math.pi * (self.ngv_r_tip ** 2 - self.ngv_r_hub ** 2)
        if self.A_ngv_throat is not None:
            return self.A_ngv_throat, math.degrees(math.acos(self.A_ngv_throat / A_exit))
        return A_exit * math.cos(math.radians(self.alpha1_deg)), self.alpha1_deg

    def rotor(self):
        A = math.pi * (self.r_tip ** 2 - self.r_hub ** 2)
        if self.A_rotor_throat is not None:
            return self.A_rotor_throat, -math.degrees(math.acos(self.A_rotor_throat / A))
        return A * math.cos(math.radians(self.beta2_deg)), self.beta2_deg


def stage_from_records(turbine_yaml='data/components/turbine_jetmax_tw85.yaml',
                       ngv_yaml='data/components/ngv_jetmax_ngv85.yaml', **over):
    t = yaml.safe_load(open(ROOT / turbine_yaml, encoding='utf-8'))['parameters']
    n = yaml.safe_load(open(ROOT / ngv_yaml, encoding='utf-8'))['parameters']
    mm = lambda p: p['value'] * 1e-3
    st = Stage(r_hub=mm(t['hub_diameter']) / 2, r_tip=mm(t['tip_diameter']) / 2,
               ngv_r_hub=mm(n['vane_hub_diameter']) / 2, ngv_r_tip=mm(n['vane_tip_diameter']) / 2,
               alpha1_deg=n['exit_flow_angle']['value'], beta2_deg=t['rotor_exit_relative_angle']['value'],
               ngv_chord=mm(n['vane_axial_chord']), rotor_chord=mm(t['blade_axial_width_at_rim']),
               ngv_count=int(n['vane_count_estimate']['value']), rotor_count=int(t['blade_count_estimate']['value']),
               tip_clearance=mm(t['tip_clearance_design']))
    return replace(st, **over)


def mu_hot(T):
    # Sutherland's law for air (US Standard Atmosphere 1976 form). The repository used
    # 3.5e-5 (T/1000)^0.7 before the verification fix; that law is ~18 % below tabulated air.
    return 1.458e-6 * T ** 1.5 / (T + 110.4)


def soderberg(eps_deg, chord, height, kind):
    z = 0.04 * (1.0 + 1.5 * (eps_deg / 100.0) ** 2)
    if kind == 'nozzle':
        return (1.0 + z) * (0.993 + 0.021 * chord / height) - 1.0
    return (1.0 + z) * (0.975 + 0.075 * chord / height) - 1.0


def hydraulic_diameter(pitch, height, angle_deg):
    c = math.cos(math.radians(angle_deg))
    return 2.0 * pitch * height * c / (pitch * c + height)


def _continuity(state, A, mdot, vmax):
    flux = lambda v: state(v)[2] * v * A
    r = minimize_scalar(lambda v: -flux(v), bounds=(1.0, 0.999 * vmax), method='bounded',
                        options=dict(xatol=1e-7, maxiter=500))
    vstar = float(r.x)
    fmax = flux(vstar)
    if mdot > fmax:
        raise Choke(f'requested {mdot:.5f} kg/s > max {fmax:.5f} kg/s')
    v = brentq(lambda v: flux(v) - mdot, 1e-6, vstar, xtol=1e-11)
    return v, mdot / fmax


def rate_turbine(st: Stage, mdot, T01, P01, N, far, reynolds='single_update'):
    """reynolds: 'single_update' (as the stated method: one update) or 'converged' (fixed point)."""
    U = N * 2 * math.pi / 60 * st.r_mean
    H_N, H_R = st.ngv_r_tip - st.ngv_r_hub, st.r_tip - st.r_hub
    s_N, s_R = 2 * math.pi * st.r_mean / st.ngv_count, 2 * math.pi * st.r_mean / st.rotor_count
    A_N, a1 = st.ngv()
    A_R, b2 = st.rotor()
    h01 = h(T01, far)
    zN1 = soderberg(a1, st.ngv_chord, H_N, 'nozzle') * st.loss_scale

    def ngv_state(C, z):
        h1 = h01 - 0.5 * C * C
        T1 = T_from_h(h1, far)
        T1s = T_from_h(h1 - z * 0.5 * C * C, far)
        P1 = P_isentropic(T1s, T01, P01, far)
        return T1, P1, P1 / (R * T1)

    vmax = math.sqrt(2 * (h01 - h(max(201.0, 0.4 * T01), far)))
    zN = zN1
    C1, fracN = _continuity(lambda v: ngv_state(v, zN), A_N, mdot, vmax)
    for it in range(30):
        T1, P1, rho1 = ngv_state(C1, zN)
        ReN = rho1 * C1 * hydraulic_diameter(s_N, H_N, a1) / mu_hot(T1)
        zN_new = zN1 * (1e5 / ReN) ** 0.25
        C1, fracN = _continuity(lambda v: ngv_state(v, zN_new), A_N, mdot, vmax)
        done = abs(zN_new - zN) < 1e-12
        zN = zN_new
        if reynolds == 'single_update' or done:
            break
    T1, P1, rho1 = ngv_state(C1, zN)
    ReN = rho1 * C1 * hydraulic_diameter(s_N, H_N, a1) / mu_hot(T1)   # Re at the final state
    Cx1, Ct1 = C1 * math.cos(math.radians(a1)), C1 * math.sin(math.radians(a1))
    Wt1 = Ct1 - U
    W1 = math.hypot(Cx1, Wt1)
    beta1 = math.degrees(math.atan2(Wt1, Cx1))
    I = h(T1, far) + 0.5 * W1 * W1
    zR1 = soderberg(abs(beta1 - b2), st.rotor_chord, H_R, 'rotor') * st.loss_scale

    def rotor_state(W, z):
        h2 = I - 0.5 * W * W
        T2 = T_from_h(h2, far)
        T2s = T_from_h(h2 - z * 0.5 * W * W, far)
        P2 = P_isentropic(T2s, T1, P1, far)
        return T2, P2, P2 / (R * T2)

    wmax = math.sqrt(2 * (I - h(max(201.0, 0.4 * T1), far)))
    zR = zR1
    W2, fracR = _continuity(lambda w: rotor_state(w, zR), A_R, mdot, wmax)
    for it in range(30):
        T2, P2, rho2 = rotor_state(W2, zR)
        ReR = rho2 * W2 * hydraulic_diameter(s_R, H_R, b2) / mu_hot(T2)
        zR_new = zR1 * (1e5 / ReR) ** 0.25
        W2, fracR = _continuity(lambda w: rotor_state(w, zR_new), A_R, mdot, wmax)
        done = abs(zR_new - zR) < 1e-12
        zR = zR_new
        if reynolds == 'single_update' or done:
            break
    T2, P2, rho2 = rotor_state(W2, zR)
    ReR = rho2 * W2 * hydraulic_diameter(s_R, H_R, b2) / mu_hot(T2)
    Cx2, Wt2 = W2 * math.cos(math.radians(b2)), W2 * math.sin(math.radians(b2))
    Ct2 = U + Wt2
    C2 = math.hypot(Cx2, Ct2)
    wE = U * (Ct1 - Ct2)
    h2 = h(T2, far)
    energy_res = (h01 - (h2 + 0.5 * C2 * C2)) - wE
    w = wE * (1.0 - st.K_tip * st.tip_clearance / H_R)
    h02 = h01 - w
    T02 = T_from_h(h02, far)
    Ct2m = Ct1 - w / U
    A_an = math.pi * (st.r_tip ** 2 - st.r_hub ** 2)
    k = mdot * R / (P2 * A_an)
    T2m = brentq(lambda T: h(T, far) + 0.5 * ((k * T) ** 2 + Ct2m ** 2) - h02, 250.0, T02, xtol=1e-10)
    P02 = P_isentropic(T02, T2m, P2, far)
    T02s = T_isentropic(T01, P02 / P01, far)
    eta_tt = w / (h01 - h(T02s, far))
    flags = []
    if not all(2e4 <= re <= 1e6 for re in (ReN, ReR)):
        flags.append('Re outside 2e4-1e6')
    if P2 >= P1:
        flags.append('negative reaction')
    return dict(U=U, C1=C1, T1=T1, P1=P1, alpha1=a1, beta1=beta1, W1=W1, W2=W2, T2=T2, P2=P2, Cx2=Cx2, Ct1=Ct1,
                Ct2=Ct2, C2=C2, w_euler=wE, w=w, T02=T02, P02=P02, T2m=T2m, Ct2m=Ct2m, rho2m=P2 / (R * T2m),
                eta_tt=eta_tt, psi=w / U ** 2, phi=Cx2 / U, reaction=(h(T1, far) - h2) / (h01 - (h2 + 0.5 * C2 * C2)),
                zeta_ngv=zN, zeta_rotor=zR, Re_ngv=ReN, Re_rotor=ReR, ngv_frac=fracN, rotor_frac=fracR,
                A_ngv=A_N, A_rotor=A_R, energy_residual=energy_res, power=mdot * w, flags=flags)


# ----------------------------------------------------------------------------- nozzle
def nozzle(T0, P0, Pamb, far, A, Cd, Cv):
    """Convergent nozzle: Cv scales the ideal kinetic energy by Cv^2 at the same static pressure,
    Cd multiplies the resulting mass flux. Choked when the actual exit velocity reaches the local
    sound speed at a static pressure >= Pamb (same definition as the stated model)."""
    h0 = h(T0, far)

    def actual(Ts_ideal):
        hh = h0 - Cv ** 2 * (h0 - h(Ts_ideal, far))
        T = T_from_h(hh, far)
        return math.sqrt(max(0.0, 2 * (h0 - hh))), T

    g = lambda Ti: actual(Ti)[0] ** 2 - gamma(actual(Ti)[1], far) * R * actual(Ti)[1]
    Ti_star = brentq(g, 0.5 * T0, T0 - 1e-6, xtol=1e-10)
    P_star = P_isentropic(Ti_star, T0, P0, far)
    choked = Pamb <= P_star
    Ti = Ti_star if choked else T_isentropic(T0, Pamb / P0, far)
    P8 = P_star if choked else Pamb
    V8, T8 = actual(Ti)
    m = Cd * A * (P8 / (R * T8)) * V8
    return m, V8, T8, P8, choked


# ----------------------------------------------------------------------------- engine
@dataclass
class Engine:
    stage: Stage
    mp: Map
    A8: float
    FF_design: float
    FF_duct: float
    comb_loss: float = 0.025
    duct_loss: float = 0.020
    inlet_loss_ref: float = 0.01
    Q_ref: float = 0.20
    leak: float = 0.02
    jetpipe: float = 0.01
    Cd: float = 0.97
    Cv: float = 0.97
    eta_b: float = 0.96
    LHV: float = 43.0e6
    # bearings (record values) and windage (case/assembly)
    f0: float = 1.7
    nu_cSt: float = 8.0
    preload_N: float = 40.0
    mu_load: float = 0.0015
    bore_mm: float = 10.0
    od_mm: float = 26.0
    n_bearings: int = 2
    windage_r: float = 0.0275
    windage_Cm: float = 0.004
    windage_faces: int = 2
    reynolds: str = 'single_update'


def far_balance(T3, T4, eta_b, LHV):
    """f from m_a h_a(T3) + m_f eta_b LHV = (m_a+m_f) h_p(T4, f); own fixed point."""
    f = 0.0
    for _ in range(200):
        f_new = (h(T4, f) - h(T3, 0.0)) / (LHV * eta_b - h(T4, f))
        if abs(f_new - f) < 1e-15:
            return f_new
        f = f_new
    raise RuntimeError('far did not converge')


def mech_power(e: Engine, N, rho_cav):
    om = N * 2 * math.pi / 60
    dm = 0.5 * (e.bore_mm + e.od_mm)
    M0 = e.f0 * (e.nu_cSt * N) ** (2 / 3) * dm ** 3 * 1e-7          # N mm (Palmgren, nu*n >= 2000)
    M1 = 0.5 * e.mu_load * e.preload_N * e.bore_mm                   # N mm
    brg = e.n_bearings * (M0 + M1) * 1e-3 * om
    wind = e.windage_faces * e.windage_Cm * 0.5 * rho_cav * om ** 3 * e.windage_r ** 5
    return brg + wind, brg, wind


def evaluate(e: Engine, N, beta, T04, T0=288.15, P0=101325.0, map_kw=None):
    map_kw = map_kw or {}
    nc = e.mp.corrected_speed(N, T0)
    q = e.mp.point(nc, beta)[0] * map_kw.get('flow_scale', 1.0)
    loss_in = e.inlet_loss_ref * (q / e.Q_ref) ** 2           # depends on Q_corr only: no iteration needed
    P2 = P0 * (1 - loss_in)
    c = compressor(e.mp, N, beta, T0, P2, **map_kw)
    m, T03, P03 = c['mdot'], c['T3'], c['P3']
    FF3 = m * math.sqrt(T03) / P03
    duct = e.duct_loss * (FF3 / e.FF_duct) ** 2
    P031 = P03 * (1 - duct)
    m_comb = m * (1 - e.leak)
    FF31 = m_comb * math.sqrt(T03) / P031
    comb = e.comb_loss * (FF31 / e.FF_design) ** 2
    P04 = P031 * (1 - comb)
    if T04 <= T03 + 1:
        raise ValueError('T04 <= T03')
    f = far_balance(T03, T04, e.eta_b, e.LHV)
    m_fuel = m_comb * f
    m_leak = m * e.leak
    m_t = m_comb + m_fuel + m_leak
    f_mix = m_fuel / (m_comb + m_leak)
    h41 = ((m_comb + m_fuel) * h(T04, f) + m_leak * h(T03, 0.0)) / m_t
    T41 = T_from_h(h41, f_mix)
    t = rate_turbine(e.stage, m_t, T41, P04, N, f_mix, e.reynolds)
    q_sw = 0.5 * t['rho2m'] * t['Ct2m'] ** 2
    P07 = t['P02'] * (1 - e.jetpipe) - q_sw
    T07 = t['T02']
    if P07 <= P0:
        m_noz, V8, T8, P8, ch = 0.0, 0.0, T07, P0, False
    else:
        m_noz, V8, T8, P8, ch = nozzle(T07, P07, P0, f_mix, e.A8, e.Cd, e.Cv)
    rho_cav = P04 / (R * 0.5 * (T03 + T41))
    Pm, Pb, Pw = mech_power(e, N, rho_cav)
    Pc, Pt = m * c['w'], t['power']
    return dict(c=c, t=t, P2=P2, T03=T03, P03=P03, P031=P031, P04=P04, T41=T41, T07=T07, P07=P07, V8=V8, T8=T8,
                P8=P8, choked=ch, m_air=m, m_t=m_t, m_noz=m_noz, m_fuel=m_fuel, far=f, far_mix=f_mix, FF3=FF3,
                FF31=FF31, loss_in=loss_in, duct=duct, comb=comb, q_swirl=q_sw, Pc=Pc, Pt=Pt, Pm=Pm, Pb=Pb, Pw=Pw,
                r_mass=(m_noz - m_t) / m_t, r_power=(Pt - Pc - Pm) / Pc,
                thrust=m_noz * V8 + e.A8 * (P8 - P0), NPR=P07 / P0)


def _safe(fn, *a, **k):
    try:
        return fn(*a, **k)
    except (OffMap, Choke, ValueError, RuntimeError, gas.GasError, ZeroDivisionError):
        return None


def solve_T04(e, N, beta, T0, P0, map_kw=None, n=40, T_hi=1500.0):
    """Power balance in T04 at fixed beta; returns list of ALL roots on an n-point grid."""
    c = compressor(e.mp, N, beta, T0, P0 * 0.99, **(map_kw or {}))
    lo = c['T3'] + 40.0
    grid = np.linspace(lo, T_hi, n)
    vals = []
    for T in grid:
        ev = _safe(evaluate, e, N, beta, float(T), T0, P0, map_kw)
        vals.append(None if ev is None else ev['r_power'])
    roots = []
    for (T1, v1), (T2, v2) in zip(zip(grid, vals), zip(grid[1:], vals[1:])):
        if v1 is not None and v2 is not None and v1 * v2 <= 0:
            roots.append(brentq(lambda T: evaluate(e, N, beta, T, T0, P0, map_kw)['r_power'], T1, T2,
                                xtol=1e-9, rtol=1e-13))
    return roots, list(zip(grid.tolist(), vals))


def match(e, N, T0=288.15, P0=101325.0, map_kw=None, n_beta=21, beta_bracket=None):
    """Nested solve: inner T04 (power), outer beta (mass). Returns every converged root found."""
    def rm(b):
        roots, _ = solve_T04(e, N, b, T0, P0, map_kw)
        if not roots:
            return None
        return evaluate(e, N, b, roots[0], T0, P0, map_kw)['r_mass'], roots
    betas = np.linspace(*(beta_bracket or (0.0, 1.0)), n_beta)
    scan = [(float(b), _safe(rm, float(b))) for b in betas]
    sols = []
    for (b1, v1), (b2, v2) in zip(scan, scan[1:]):
        if v1 is None or v2 is None or v1[0] * v2[0] > 0:
            continue
        try:
            bs = brentq(lambda b: rm(b)[0], b1, b2, xtol=1e-12, rtol=1e-14)
            r, roots = rm(bs)
            ev = evaluate(e, N, bs, roots[0], T0, P0, map_kw)
        except (TypeError, OffMap, Choke, ValueError, RuntimeError, gas.GasError) as err:
            sols.append(dict(beta=None, T04=None, failed=f'refinement failed in [{b1:.3f},{b2:.3f}]: {err}'))
            continue
        sols.append(dict(beta=bs, T04=roots[0], n_T04_roots=len(roots), ev=ev))
    return [x for x in sols if x.get('beta') is not None], scan


def anchored_engine(e: Engine, N, T0=288.15, P0=101325.0, tol=1e-9, beta_bracket=(0.5, 0.8)):
    hist = []
    for _ in range(40):
        sols, _ = match(e, N, T0, P0, n_beta=7, beta_bracket=beta_bracket)
        if len(sols) != 1:
            raise RuntimeError(f'anchoring: {len(sols)} roots in {beta_bracket}')
        ev = sols[0]['ev']
        hist.append((e.FF_design, ev['FF31'], e.FF_duct, ev['FF3'], sols[0]['T04'], sols[0]['beta']))
        if abs(ev['FF31'] / e.FF_design - 1) < tol and abs(ev['FF3'] / e.FF_duct - 1) < tol:
            return e, sols[0], hist
        e = replace(e, FF_design=ev['FF31'], FF_duct=ev['FF3'])
    raise RuntimeError('anchor did not converge')


def engine_from_inputs(case_yaml='config/cases/pd1-jm85.yaml', **over):
    case = yaml.safe_load(open(ROOT / case_yaml, encoding='utf-8'))
    en = case['engine']
    mrec = yaml.safe_load(open(ROOT / case['components']['compressor_map'], encoding='utf-8'))['parameters']
    asm = yaml.safe_load(open(ROOT / case['components']['assembly'], encoding='utf-8'))['parameters']
    brg = yaml.safe_load(open(ROOT / case['components']['bearings'], encoding='utf-8'))['parameters']
    trb = yaml.safe_load(open(ROOT / case['components']['turbine'], encoding='utf-8'))['parameters']
    mp = Map(T_ref=mrec['reference_temperature']['value'], P_ref=mrec['reference_pressure']['value'])
    D8 = asm['nozzle_exit_d']['value'] * 1e-3
    e = Engine(stage=stage_from_records(case['components']['turbine'], case['components']['ngv']), mp=mp,
               A8=math.pi / 4 * D8 ** 2, FF_design=2.7e-5, FF_duct=2.7e-5,
               comb_loss=en['comb_loss_design'], duct_loss=en['duct_loss_design'], inlet_loss_ref=en['inlet_loss_ref'],
               Q_ref=en['inlet_Q_ref_kg_s'], leak=en['leak_frac'], jetpipe=en['jetpipe_loss'], Cd=en['nozzle_Cd'],
               Cv=en['nozzle_Cv'], eta_b=en['eta_b'], LHV=float(en['LHV_J_kg']),
               f0=brg['friction_f0']['value'], nu_cSt=brg['lubricant_viscosity']['value'],
               preload_N=brg['preload_spring_force']['value'], bore_mm=brg['bore']['value'],
               od_mm=brg['outer_diameter']['value'], windage_r=trb['hub_diameter']['value'] * 1e-3 / 2,
               windage_Cm=en.get('windage_Cm', 0.004))
    return replace(e, **over), case


# ----------------------------------------------------------------------------- reporting
FAILS = []


def compare(name, indep, repo, tol_pct=1.0, note='', abs_tol=None):
    if indep is None or repo is None:
        print(f'{name:<64s} indep={indep!s:>14s} repo={repo!s:>14s}   n/a      OPEN  {note}')
        return
    d = (indep - repo) / repo * 100 if repo != 0 else float('inf')
    ok = (abs(indep - repo) <= abs_tol) if abs_tol is not None else abs(d) <= tol_pct
    if not ok:
        FAILS.append(name)
    print(f'{name:<64s} indep={indep:14.6g} repo={repo:14.6g} {d:+9.4f}%  {"PASS" if ok else "DIFF"}  {note}')


def results_dir(case, argv):
    return Path(argv[1]) if len(argv) > 1 else ROOT / 'docs/design/results' / case
