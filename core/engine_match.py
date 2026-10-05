"""Fixed-geometry single-spool turbojet operating-point matching.

At a prescribed shaft speed N and ambient state this finds the steady operating
point of a FIXED engine (compressor characteristic, turbine stage geometry,
nozzle area, duct and combustor loss characteristics) with ZERO starter torque.

Independent inputs : N, ambient T0/P0, fixed geometry, loss/efficiency models.
Unknowns           : compressor map position beta, combustor exit temperature T04.
Residuals          : r_mass  = (nozzle capacity - turbine flow) / turbine flow
                     r_power = (P_turbine - P_compressor - P_mechanical) / P_compressor
Derived            : fuel flow (energy balance), all station states, thrust.

The turbine work is computed by core/turbine_rating.rate from the stage geometry
and the gas state; it is not set equal to the compressor demand. The nozzle
passes whatever its fixed area allows at the turbine-exit state. A point is
reported only when both residuals are below tolerance; otherwise the reason
(map boundary, NGV/rotor choke, no sign change, T04 outside the search range)
is returned. No earlier solution is recycled.

Pressure ledger (one entry per physical loss, each counted once):
  0 -> 2   inlet bellmouth + screen         dP/P ~ (Q_corr/Q_ref)^2 anchored
  2 -> 3   compressor stage per map          map PR / efficiency (includes its diffuser)
  3 -> 31  diffuser exit -> combustor inlet  reverse turn / deswirl, ~ FF^2 anchored
  31 -> 4  combustor (annuli, holes, liner)  prescribed design loss ~ FF^2 (fixed geometry)
  4 -> 41  bearing-tunnel leakage re-entry   adiabatic mixing, no extra loss
  41 -> 5  turbine stage                     mean-line rating
  5 -> 7   jet pipe                          fixed fraction + dissipated exit swirl head
  7 -> 8   convergent nozzle                 Cv, Cd; choked or unchoked
FF = mdot sqrt(T)/P at combustor inlet. Mechanical losses are explicit bearing
friction and disc windage powers; no separate mechanical efficiency is applied.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict, replace

from scipy.optimize import brentq

from core import gas, thermo
from core.compressor_map import CompressorMap, MapDomainError
from core.turbine_rating import StageGeometry, rate, TurbineLimit

RESIDUAL_TOL = 1e-6   # relative; numerical closure, not an engineering margin


class MatchFailure(Exception):
    pass


@dataclass
class Bearing:
    name: str
    bore_mm: float
    od_mm: float
    f0: float = 1.7          # SKF/Palmgren viscous-moment factor (angular contact, oil mist ~1-2)
    nu_cSt: float = 8.0      # operating lubricant viscosity (fuel/oil mist assumption)
    preload_N: float = 40.0
    mu_load: float = 0.0015

    @property
    def dm_mm(self):
        return 0.5 * (self.bore_mm + self.od_mm)

    def power_W(self, N_rpm):
        omega = gas.rpm_to_rad_s(N_rpm)
        M0 = self.f0 * (self.nu_cSt * N_rpm) ** (2.0 / 3.0) * self.dm_mm ** 3 * 1e-7   # N mm
        M1 = 0.5 * self.mu_load * self.preload_N * self.bore_mm                    # N mm
        return (M0 + M1) * 1e-3 * omega


@dataclass
class MechanicalLosses:
    bearings: list = field(default_factory=list)
    windage_radius_m: float = 0.0275      # turbine disc rim radius exposed to cavity gas
    windage_Cm: float = 0.004             # moment coefficient per face (assumption)
    windage_faces: int = 2
    scale: float = 1.0                    # robustness multiplier

    def power_W(self, N_rpm, rho_cavity=0.5):
        omega = gas.rpm_to_rad_s(N_rpm)
        brg = sum(b.power_W(N_rpm) for b in self.bearings)
        wind = self.windage_faces * self.windage_Cm * 0.5 * rho_cavity * omega ** 3 * self.windage_radius_m ** 5
        return self.scale * (brg + wind), self.scale * brg, self.scale * wind


@dataclass
class EngineDefinition:
    case_id: str
    stage: StageGeometry
    cmap: CompressorMap
    A8_m2: float
    FF_design: float                      # combustor-inlet flow function at the loss anchor
    comb_loss_design: float = 0.04
    duct_loss_design: float = 0.015
    inlet_loss_ref: float = 0.01
    inlet_Q_ref_kg_s: float = 0.25
    leak_frac: float = 0.02
    jetpipe_loss: float = 0.01
    nozzle_Cd: float = 0.97
    nozzle_Cv: float = 0.97
    eta_b: float = 0.96
    LHV_J_kg: float = 43.0e6
    mech: MechanicalLosses = field(default_factory=MechanicalLosses)
    T04_screen_max_K: float = 1150.0
    T04_search_max_K: float = 1500.0
    R: float = 287.05
    FF_duct_design: float | None = None   # separate upstream anchor; no leakage deducted in the turn

    def with_(self, **kw):
        return replace(self, **kw)

    def describe(self):
        d = {k: v for k, v in asdict(self).items() if k not in ('stage', 'cmap', 'mech')}
        d['stage'] = self.stage.as_dict()
        d['map_offsets'] = self.cmap.offsets.as_dict()
        d['map_identity'] = self.cmap.identity()
        d['mechanical'] = asdict(self.mech)
        return d


def _nozzle_flow(T0, P0, Pamb, far, A, Cd, Cv, R):
    V, T, P, choked = thermo.nozzle(T0, P0, Pamb, far, R, Cv=Cv)
    rho = P / (R * T)
    return Cd * A * rho * V, V, T, P, choked


def _evaluate(eng: EngineDefinition, N, beta, T04, T0, P0):
    """Evaluate the cycle at (beta, T04). Raises MapDomainError/TurbineLimit/GasError."""
    R = eng.R
    # inlet loss: fixed point on corrected flow (converges in a few passes)
    P2 = P0 * (1 - eng.inlet_loss_ref)
    for _ in range(20):
        c = eng.cmap.operate(N, beta, T0, P2, R)
        loss = eng.inlet_loss_ref * (c['Q_corr_kg_s'] / eng.inlet_Q_ref_kg_s) ** 2
        P2_new = P0 * (1 - loss)
        if abs(P2_new - P2) < 1e-6 * P0:
            break
        P2 = P2_new
    c = eng.cmap.operate(N, beta, T0, P2, R)
    m_air, T03, P03 = c['mdot_kg_s'], c['T_out_K'], c['P_out_Pa']
    FF3 = m_air * math.sqrt(T03) / P03
    duct = eng.duct_loss_design * (FF3 / (eng.FF_duct_design or eng.FF_design)) ** 2
    P031 = P03 * (1 - duct)
    m_comb = m_air * (1 - eng.leak_frac)
    FF31 = m_comb * math.sqrt(T03) / P031
    comb = eng.comb_loss_design * (FF31 / eng.FF_design) ** 2
    if duct + comb >= 0.5:
        raise TurbineLimit('duct + combustor loss above 50 %: outside loss-scaling validity')
    P04 = P031 * (1 - comb)
    if T04 <= T03 + 1.0:
        raise thermo.gas.GasError('combustor exit temperature not above inlet')
    far = gas.far_for_T4(T03, T04, eng.eta_b, eng.LHV_J_kg)
    m_fuel = m_comb * far
    m_leak = m_air * eng.leak_frac
    m_t = m_comb + m_fuel + m_leak
    far_mix = m_fuel / (m_comb + m_leak)
    h41 = ((m_comb + m_fuel) * gas.h_products(T04, far) + m_leak * gas.h_air(T03)) / m_t
    T41 = thermo.temperature_fast(h41, far_mix)
    t = rate(eng.stage, m_t, T41, P04, N, far_mix, R)
    # jet pipe: fixed loss + dissipated swirl dynamic head (static density at rotor exit)
    mixed = t['mixed_exit']
    q_swirl = 0.5 * (mixed['P_static_Pa'] / (R * mixed['T_static_K'])) * mixed['Ct_m_s'] ** 2
    P05 = t['P02_Pa']
    P07 = P05 * (1 - eng.jetpipe_loss) - q_swirl
    T07 = t['T02_K']
    if P07 <= P0 * (1 + 1e-9):
        # no pressure head: the nozzle passes no flow; residual stays continuous (-1)
        m_noz, V8, T8, P8, choked = 0.0, 0.0, T07, P0, False
    else:
        m_noz, V8, T8, P8, choked = _nozzle_flow(T07, P07, P0, far_mix, eng.A8_m2, eng.nozzle_Cd,
                                                 eng.nozzle_Cv, R)
    rho_cav = P04 / (R * 0.5 * (T03 + T41))   # cavity gas between tunnel and disc (rough)
    P_mech, P_brg, P_wind = eng.mech.power_W(N, rho_cav)
    P_c = m_air * c['w_J_kg']
    P_t = t['power_W']
    F = m_noz * V8 + eng.A8_m2 * (P8 - P0)
    return dict(
        compressor=c, turbine=t,
        r_mass=(m_noz - m_t) / m_t, r_power=(P_t - P_c - P_mech) / P_c,
        stations=dict(
            T0_K=T0, P0_Pa=P0, T2_K=T0, P2_Pa=P2, T3_K=T03, P3_Pa=P03, P31_Pa=P031,
            T4_K=T04, P4_Pa=P04, T41_K=T41, P41_Pa=P04, T5_K=t['T02_K'], P5_Pa=P05,
            P5_static_Pa=mixed['P_static_Pa'], T5_static_K=mixed['T_static_K'], T7_K=T07, P7_Pa=P07,
            T8_static_K=T8, P8_static_Pa=P8, V8_m_s=V8),
        flows=dict(m_air_kg_s=m_air, m_leak_kg_s=m_leak, m_comb_air_kg_s=m_comb, m_fuel_kg_s=m_fuel,
                   m_turbine_kg_s=m_t, m_nozzle_kg_s=m_noz, FAR_combustor=far, FAR_mixed=far_mix,
                   fuel_kg_h=m_fuel * 3600),
        powers=dict(P_compressor_W=P_c, P_turbine_W=P_t, P_mechanical_W=P_mech, P_bearings_W=P_brg,
                    P_windage_W=P_wind, P_accessory_W=0.0, P_starter_W=0.0,
                    P_net_W=P_t - P_c - P_mech, torque_net_Nm=(P_t - P_c - P_mech) / gas.rpm_to_rad_s(N)),
        losses=dict(inlet_frac=1 - P2 / P0, duct_frac=duct, combustor_frac=comb,
                    jetpipe_frac=eng.jetpipe_loss, swirl_head_Pa=q_swirl,
                    FF3=FF3, FF31=FF31, FF_design=eng.FF_design, FF_duct_design=eng.FF_duct_design),
        nozzle=dict(A8_m2=eng.A8_m2, choked=choked, NPR=P07 / P0),
        thrust_N=F)


def _inner_T04(eng, N, beta, T0, P0, n_grid=14):
    """Solve the power balance in T04 at fixed beta.

    T04 is scanned between T03 + 40 K and the search ceiling; the first sign
    change of the power residual between two feasible grid points is refined.
    Low T04 can be infeasible (the fixed stage windmills: negative Euler work)
    and high T04 can be infeasible (NGV choke at fixed flow). Raises
    MatchFailure with the reason when no balance exists.
    """
    c = eng.cmap.operate(N, beta, T0, P0 * (1 - eng.inlet_loss_ref), eng.R)
    lo, hi = c['T_out_K'] + 40.0, eng.T04_search_max_K

    def f(T):
        try:
            return _evaluate(eng, N, beta, T, T0, P0)['r_power'], None
        except (TurbineLimit, thermo.gas.GasError) as e:
            return None, str(e)

    grid = [lo + (hi - lo) * i / (n_grid - 1) for i in range(n_grid)]
    vals = [f(T) for T in grid]
    for (T1, (v1, _)), (T2, (v2, _)) in zip(zip(grid, vals), zip(grid[1:], vals[1:])):
        if v1 is not None and v2 is not None and v1 * v2 <= 0:
            T = brentq(lambda T: f(T)[0], T1, T2, xtol=1e-6, rtol=1e-10, maxiter=100)
            return T, _evaluate(eng, N, beta, T, T0, P0)
    # A root can sit between the last feasible grid point and an infeasible neighbour
    # (NGV/rotor choke at high T04, windmilling at low T04). Walk each feasible/infeasible
    # edge to the boundary and look for the sign change there before reporting no balance.
    for (T1, (v1, _)), (T2, (v2, _)) in zip(zip(grid, vals), zip(grid[1:], vals[1:])):
        if (v1 is None) == (v2 is None):
            continue
        T_ok, v_ok, T_bad = (T1, v1, T2) if v1 is not None else (T2, v2, T1)
        T_e, v_e = T_ok, v_ok
        for _ in range(40):
            if abs(T_bad - T_e) < 1e-3:        # 1 mK: brentq refines the root inside [T_ok, T_e]
                break
            m = 0.5 * (T_e + T_bad)
            v_m, _ = f(m)
            if v_m is None:
                T_bad = m
            else:
                T_e, v_e = m, v_m
        if T_e != T_ok and v_ok * v_e <= 0:
            a, b = sorted((T_ok, T_e))
            try:
                T = brentq(lambda T: f(T)[0], a, b, xtol=1e-6, rtol=1e-10, maxiter=100)
            except (TypeError, ValueError):    # an infeasible pocket inside the edge interval
                continue
            return T, _evaluate(eng, N, beta, T, T0, P0)
    feas = [(T, v) for T, (v, e) in zip(grid, vals) if v is not None]
    errs = sorted({e.split(' at ')[0].split(':')[0] for _, (v, e) in zip(grid, vals) if e})
    if not feas:
        raise MatchFailure(f'beta {beta:.3f}: no feasible T04 in {lo:.0f}-{hi:.0f} K ({"; ".join(errs)})')
    if all(v < 0 for _, v in feas):
        raise MatchFailure(f'beta {beta:.3f}: turbine work insufficient for T04 {feas[0][0]:.0f}-{feas[-1][0]:.0f} K'
                           + (f' (other T04 infeasible: {"; ".join(errs)})' if errs else ''))
    if all(v > 0 for _, v in feas):
        raise MatchFailure(f'beta {beta:.3f}: power surplus at every feasible T04 '
                           f'{feas[0][0]:.0f}-{feas[-1][0]:.0f} K' + (f' ({"; ".join(errs)})' if errs else ''))
    raise MatchFailure(f'beta {beta:.3f}: power residual changes sign only across an infeasible gap ({"; ".join(errs)})')


def match_speed(eng: EngineDefinition, N_rpm, T0=288.15, P0=101325.0, n_scan=21):
    """Find steady branches on a finite beta scan (not proof of root completeness).

    The inner solve follows the first power-balanced temperature branch. Other
    branches or narrow feasible intervals can be missed; no-match is model/search
    evidence, not a proof that the physical engine has no equilibrium.
    """
    try:
        nc = eng.cmap.corrected_speed(N_rpm, T0)
        eng.cmap.point(nc, 0.5)
    except MapDomainError as e:
        return dict(status='outside_map', N_rpm=N_rpm, reason=str(e), branches=[])
    scan = []
    for i in range(n_scan):
        b = i / (n_scan - 1)
        try:
            T04, ev = _inner_T04(eng, N_rpm, b, T0, P0)
            scan.append((b, T04, ev['r_mass'], None))
        except (MatchFailure, MapDomainError, TurbineLimit, thermo.gas.GasError) as e:
            scan.append((b, None, None, str(e)))
    branches = []
    for (b1, T1, r1, _), (b2, T2, r2, _) in zip(scan, scan[1:]):
        if r1 is None or r2 is None or r1 * r2 > 0:
            continue
        g = lambda b: _inner_T04(eng, N_rpm, b, T0, P0)[1]['r_mass']
        try:
            bs = brentq(g, b1, b2, xtol=1e-10, rtol=1e-12, maxiter=100)
            T04, ev = _inner_T04(eng, N_rpm, bs, T0, P0)
        except (MatchFailure, TurbineLimit, MapDomainError, ValueError) as e:
            branches.append(dict(converged=False, reason=f'refinement failed: {e}'))
            continue
        conv = abs(ev['r_mass']) < RESIDUAL_TOL and abs(ev['r_power']) < RESIDUAL_TOL
        branches.append(_package(eng, N_rpm, bs, T04, ev, conv))
    reasons = sorted({s[3].split(':', 1)[1].strip() if s[3] and ':' in s[3] else s[3]
                      for s in scan if s[3]})
    if not branches:
        valid = [s for s in scan if s[2] is not None]
        return dict(status='no_match', N_rpm=N_rpm, N_corr_rpm=nc, branches=[],
                    reason=('mass residual has no sign change over the valid beta range'
                            if valid else 'no beta gives a power-balanced point'),
                    scan=[dict(beta=s[0], T04_K=s[1], r_mass=s[2], failure=s[3]) for s in scan],
                    failure_reasons=reasons)
    return dict(status='matched' if all(b.get('converged') for b in branches) else 'unconverged',
                N_rpm=N_rpm, N_corr_rpm=nc, branches=branches,
                multiple_branches=len(branches) > 1,
                scan=[dict(beta=s[0], T04_K=s[1], r_mass=s[2], failure=s[3]) for s in scan])


def _package(eng, N, beta, T04, ev, converged):
    c, t = ev['compressor'], ev['turbine']
    checks = dict(
        surge_margin_flow=c['SM_flow'], surge_margin_pr=c['SM_pr'], map_beta=beta,
        map_eta_confidence=c['eta_confidence'],
        T04_K=T04, T04_screen_max_K=eng.T04_screen_max_K, T04_within_screen=T04 <= eng.T04_screen_max_K,
        ngv_flow_fraction_of_max=t['ngv_flow_fraction_of_max'],
        rotor_flow_fraction_of_max=t['rotor_flow_fraction_of_max'],
        ngv_exit_mach=t['M1'], rotor_exit_rel_mach=t['M2_rel'], turbine_flags=t['flags'],
        nozzle_choked=ev['nozzle']['choked'])
    return dict(converged=converged, N_rpm=N, beta=beta, T04_K=T04,
                residuals=dict(r_mass=ev['r_mass'], r_power=ev['r_power'],
                               tol=RESIDUAL_TOL,
                               mass_scale='turbine mass flow', power_scale='compressor power'),
                compressor={k: v for k, v in c.items()}, turbine={k: v for k, v in t.items()},
                stations=ev['stations'], flows=ev['flows'], powers=ev['powers'],
                losses=ev['losses'], nozzle=ev['nozzle'], thrust_N=ev['thrust_N'], checks=checks)


def verify_point(eng, point, T0=288.15, P0=101325.0, starts=((0.2, 800.0), (0.8, 1300.0), (0.5, 1000.0))):
    """Numerical cross-check with the same physics, using a different root search."""
    from scipy.optimize import root

    def F(x):
        b, T = x
        if not 0.0 <= b <= 1.0 or not gas._T_MIN < T <= eng.T04_search_max_K:
            return [10.0, 10.0]
        try:
            ev = _evaluate(eng, point['N_rpm'], b, T, T0, P0)
            return [ev['r_mass'], ev['r_power']]
        except (MapDomainError, TurbineLimit, thermo.gas.GasError):
            return [1.0, 1.0]

    out = []
    for b0, T0g in starts:
        s = root(F, [b0, T0g], method='hybr', options=dict(xtol=1e-10))
        res = F(s.x)
        out.append(dict(start=(b0, T0g), success=bool(s.success) and max(abs(r) for r in res) < 1e-5,
                        beta=float(s.x[0]), T04_K=float(s.x[1]), residual=res))
    return out


def solve_from_guess(eng, N_rpm, beta0, T040, T0=288.15, P0=101325.0):
    """Local 2-D Newton-type solve (scipy hybr) from a nearby solution.

    Used for continuation along speed and for robustness cases. The returned
    point is accepted only if both residuals meet RESIDUAL_TOL inside the map
    domain; otherwise None is returned and the caller must fall back to the
    global scan (match_speed). It never returns a previous solution.
    """
    from scipy.optimize import root

    def F(x):
        b, T = x
        if not 0.0 <= b <= 1.0 or not gas._T_MIN < T <= eng.T04_search_max_K:
            return [10.0 * (abs(b - min(max(b, 0.0), 1.0)) + 1.0)] * 2
        try:
            ev = _evaluate(eng, N_rpm, b, T, T0, P0)
            return [ev['r_mass'], ev['r_power']]
        except (MapDomainError, TurbineLimit, thermo.gas.GasError):
            return [10.0, 10.0]

    s = root(F, [beta0, T040], method='hybr', options=dict(xtol=1e-12, maxfev=200))
    b, T = float(s.x[0]), float(s.x[1])
    if not 0.0 <= b <= 1.0 or not gas._T_MIN < T <= eng.T04_search_max_K:
        return None
    try:
        ev = _evaluate(eng, N_rpm, b, T, T0, P0)
    except (MapDomainError, TurbineLimit, thermo.gas.GasError):
        return None
    if abs(ev['r_mass']) < RESIDUAL_TOL and abs(ev['r_power']) < RESIDUAL_TOL:
        return _package(eng, N_rpm, b, T, ev, True)
    return None


def operating_line(eng, speeds, T0=288.15, P0=101325.0, anchor=None):
    """Steady operating points along increasing speed by continuation.

    Each point is first attempted from the previous solution; if that fails
    (or there is no previous solution) the global scan is used. Points that
    the global scan cannot match are reported as failures with reasons.
    """
    out, prev = [], anchor
    for N in speeds:
        pt = None
        if prev is not None:
            pt = solve_from_guess(eng, N, prev['beta'], prev['T04_K'], T0, P0)
            method = 'continuation'
        if pt is None:
            r = match_speed(eng, N, T0, P0, n_scan=11)
            method = 'global_scan'
            conv = [b for b in r['branches'] if b.get('converged')]
            if conv:
                pt = conv[0]
                if len(conv) > 1:
                    pt['note'] = f'{len(conv)} branches found; lowest-beta branch reported'
            else:
                out.append(dict(N_rpm=N, status=r['status'], reason=r.get('reason'),
                                failure_reasons=r.get('failure_reasons'), method=method))
                prev = None
                continue
        pt['method'] = method
        out.append(pt)
        prev = pt
    return out
