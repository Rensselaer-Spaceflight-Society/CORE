"""Fixed-geometry mean-line rating of a single-stage axial turbine.

The geometry is held fixed: annulus radii, throat areas (or exit flow angles via
the cosine rule cos(angle) = throat / exit annulus), chords and tip clearance.
Given the inlet total state, mass flow and shaft speed the model returns the
work the stage actually delivers. It does not size anything and it does not
impose the compressor's demand.

Method (one mean radius, constant axial position):

  NGV   continuity through the throat area on the subsonic branch; Soderberg
        enthalpy-loss coefficient with aspect-ratio and Reynolds corrections.
        If the requested flow exceeds the throat's maximum flux the NGV is
        choked for that inlet state and a TurbineLimit is raised.
  Rotor relative frame, rothalpy conserved at constant radius; relative exit
        flow angle from the rotor throat (cosine rule); Soderberg rotor loss;
        incidence loss 0.5 k (W1 sin i)^2 relative to a stated metal angle;
        rotor relative choke is a TurbineLimit.
  Work  Euler U (Ctheta1 - Ctheta2). Tip leakage reduces delivered work by
        (1 - K_tip c/H). This is an empirical work penalty, NOT a resolved
        leakage stream. The outlet closure holds passage static pressure,
        enforces Euler angular momentum, continuity and total enthalpy,
        and solves the mixed outlet temperature and axial velocity.

References: Soderberg's correlation as presented in Dixon & Hall, Fluid
Mechanics and Thermodynamics of Turbomachinery (axial turbine mean-line
losses). Its stated basis is Re = 1e5, aspect ratio ~3 and Zweifel-optimal
pitch; outside that the result is an extrapolation and is flagged. Incidence
and tip-leakage terms are provisional engineering models.

This is a preliminary rating for screening a purchased stage whose blade
angles are not yet measured. It is not a stage map and does not replace CFD
or rig data.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict, replace

from core import gas, thermo


class TurbineLimit(Exception):
    """Requested operating point is outside what the fixed geometry can pass."""


def mu_hot(T):
    """Hot-gas dynamic viscosity [Pa s]: Sutherland's law for air.

    mu = 1.458e-6 T^1.5 / (T + 110.4) (US Standard Atmosphere 1976 / ISO 2533 form;
    the same law as mu0 = 1.716e-5 Pa s at 273.15 K). Within ~2 % of tabulated air
    at 300-1000 K; lean products (FAR ~0.013) are close to air. The power law
    3.5e-5 (T/1000)^0.7 used before (and still in core/combustor.py) is ~18 % below
    tabulated air, which overstated the turbine Reynolds numbers by ~20 %.
    """
    return 1.458e-6 * T ** 1.5 / (T + 110.4)


@dataclass(frozen=True)
class StageGeometry:
    stage_id: str
    r_hub_m: float
    r_tip_m: float
    ngv_r_hub_m: float
    ngv_r_tip_m: float
    alpha1_deg: float            # NGV exit flow angle from axial (cosine rule)
    beta2_deg: float             # rotor exit relative flow angle from axial (negative)
    ngv_axial_chord_m: float
    rotor_axial_chord_m: float
    ngv_count: int
    rotor_count: int
    tip_clearance_m: float
    beta1_metal_deg: float | None = None   # None: incidence loss not evaluated
    A_ngv_throat_m2: float | None = None   # if given, overrides alpha1 via cosine rule
    A_rotor_throat_m2: float | None = None
    loss_scale: float = 1.0
    K_tip: float = 2.0
    k_incidence: float = 1.0
    source_note: str = ''

    def __post_init__(self):
        for k in ('r_hub_m', 'r_tip_m', 'ngv_r_hub_m', 'ngv_r_tip_m', 'ngv_axial_chord_m',
                  'rotor_axial_chord_m', 'loss_scale'):
            v = getattr(self, k)
            if not math.isfinite(v) or v <= 0:
                raise ValueError(f'{self.stage_id}: {k} must be positive')
        if self.r_tip_m <= self.r_hub_m or self.ngv_r_tip_m <= self.ngv_r_hub_m:
            raise ValueError(f'{self.stage_id}: tip radius must exceed hub radius')
        if not 0 <= self.tip_clearance_m < 0.2 * (self.r_tip_m - self.r_hub_m):
            raise ValueError(f'{self.stage_id}: tip clearance outside model range')
        if not 0 < self.alpha1_deg < 85 or not -85 < self.beta2_deg < 0:
            raise ValueError(f'{self.stage_id}: angles outside (0,85) / (-85,0) deg')
        if self.ngv_count < 3 or self.rotor_count < 3:
            raise ValueError(f'{self.stage_id}: blade counts must be at least 3')
        for k in ('A_ngv_throat_m2', 'A_rotor_throat_m2'):
            v = getattr(self, k)
            if v is not None and (not math.isfinite(v) or v <= 0):
                raise ValueError(f'{self.stage_id}: {k} must be positive when given')

    # derived ---------------------------------------------------------------
    @property
    def r_mean_m(self):
        return 0.5 * (self.r_hub_m + self.r_tip_m)

    @property
    def blade_height_m(self):
        return self.r_tip_m - self.r_hub_m

    @property
    def ngv_height_m(self):
        return self.ngv_r_tip_m - self.ngv_r_hub_m

    @property
    def A_ngv_exit_m2(self):
        return math.pi * (self.ngv_r_tip_m ** 2 - self.ngv_r_hub_m ** 2)

    @property
    def A_rotor_m2(self):
        return math.pi * (self.r_tip_m ** 2 - self.r_hub_m ** 2)

    def ngv_throat(self):
        if self.A_ngv_throat_m2 is not None:
            ratio = self.A_ngv_throat_m2 / self.A_ngv_exit_m2
            if not 0 < ratio < 1:
                raise ValueError(f'{self.stage_id}: NGV throat must be smaller than exit annulus')
            return self.A_ngv_throat_m2, math.degrees(math.acos(ratio))
        return self.A_ngv_exit_m2 * math.cos(math.radians(self.alpha1_deg)), self.alpha1_deg

    def rotor_throat(self):
        if self.A_rotor_throat_m2 is not None:
            ratio = self.A_rotor_throat_m2 / self.A_rotor_m2
            if not 0 < ratio < 1:
                raise ValueError(f'{self.stage_id}: rotor throat must be smaller than annulus')
            return self.A_rotor_throat_m2, -math.degrees(math.acos(ratio))
        return self.A_rotor_m2 * math.cos(math.radians(self.beta2_deg)), self.beta2_deg

    def with_(self, **kw):
        return replace(self, **kw)

    def as_dict(self):
        d = asdict(self)
        d['A_ngv_throat_eff_m2'], d['alpha1_eff_deg'] = self.ngv_throat()
        d['A_rotor_throat_eff_m2'], d['beta2_eff_deg'] = self.rotor_throat()
        return d


def soderberg(deflection_deg, chord_m, height_m, kind):
    """Soderberg enthalpy-loss coefficient before Reynolds correction."""
    z = 0.04 * (1.0 + 1.5 * (deflection_deg / 100.0) ** 2)
    ratio = chord_m / height_m
    if kind == 'nozzle':
        return (1.0 + z) * (0.993 + 0.021 * ratio) - 1.0
    return (1.0 + z) * (0.975 + 0.075 * ratio) - 1.0


def _reynolds_factor(rho, V, s, H, angle_deg, T):
    c = math.cos(math.radians(angle_deg))
    dh = 2.0 * s * H * c / (s * c + H)
    re = rho * V * dh / mu_hot(T)
    return (1e5 / re) ** 0.25, re


def _flux_branch(state_of_speed, A, mdot, vmax, what):
    """Find subsonic speed with rho*V*A = mdot; raise TurbineLimit beyond max flux."""
    def flux(v):
        T, P, rho = state_of_speed(v)
        return rho * v * A
    # maximum flux by golden-section on (0, vmax)
    a, b = 1e-3, vmax * 0.999
    g = (math.sqrt(5) - 1) / 2
    c, d = b - g * (b - a), a + g * (b - a)
    fc, fd = flux(c), flux(d)
    for _ in range(45):
        if fc < fd:
            a, c, fc = c, d, fd
            d = a + g * (b - a); fd = flux(d)
        else:
            b, d, fd = d, c, fc
            c = b - g * (b - a); fc = flux(c)
    v_star = 0.5 * (a + b)
    fmax = flux(v_star)
    if mdot > fmax:
        raise TurbineLimit(f'{what} choked: requested {mdot:.4f} kg/s exceeds maximum '
                           f'{fmax:.4f} kg/s for this inlet state')
    v = thermo.bisect(lambda v: flux(v) - mdot, 1e-6, v_star, tol=1e-9)
    return v, mdot / fmax


def rate(geom: StageGeometry, mdot, T01, P01, N_rpm, far, R=287.05):
    """Rate the fixed stage. Returns a dict of states, work, losses and margins."""
    thermo.positive(mdot=mdot, T01=T01, P01=P01, N=N_rpm)
    gas.cp_products(T01, far)
    U = gas.rpm_to_rad_s(N_rpm) * geom.r_mean_m
    H_N, H_R = geom.ngv_height_m, geom.blade_height_m
    s_N = 2 * math.pi * geom.r_mean_m / geom.ngv_count
    s_R = 2 * math.pi * geom.r_mean_m / geom.rotor_count
    h01 = gas.h_products(T01, far)
    A_N, alpha1 = geom.ngv_throat()
    A_R, beta2 = geom.rotor_throat()

    # ---- NGV ---------------------------------------------------------------
    zeta_N1 = soderberg(alpha1, geom.ngv_axial_chord_m, H_N, 'nozzle') * geom.loss_scale

    def ngv_state(C, zeta=None):
        h1 = h01 - 0.5 * C * C
        T1 = thermo.temperature_fast(h1, far)
        z = zeta_N1 if zeta is None else zeta
        T1s = thermo.temperature_fast(h1 - z * 0.5 * C * C, far)
        P1 = thermo.pressure(T1s, T01, P01, far, R)
        return T1, P1, P1 / (R * T1)

    vmax = math.sqrt(2 * (h01 - gas.h_products(max(gas._T_MIN + 1, 0.4 * T01), far)))
    C1, ngv_choke_ratio = _flux_branch(ngv_state, A_N, mdot, vmax, 'NGV throat')
    T1, P1, rho1 = ngv_state(C1)
    fRe_N, Re_N = _reynolds_factor(rho1, C1, s_N, H_N, alpha1, T1)
    zeta_N = zeta_N1 * fRe_N
    # re-solve with Reynolds-corrected loss (one update is sufficient: weak coupling)
    C1, ngv_choke_ratio = _flux_branch(lambda v: ngv_state(v, zeta_N), A_N, mdot, vmax, 'NGV throat')
    T1, P1, rho1 = ngv_state(C1, zeta_N)
    g1 = thermo.gamma(T1, far, R)
    M1 = C1 / math.sqrt(g1 * R * T1)
    a1 = math.radians(alpha1)
    Cx1, Ct1 = C1 * math.cos(a1), C1 * math.sin(a1)

    # ---- rotor inlet (relative) -----------------------------------------------
    Wt1 = Ct1 - U
    W1 = math.hypot(Cx1, Wt1)
    beta1 = math.degrees(math.atan2(Wt1, Cx1))
    M1rel = W1 / math.sqrt(g1 * R * T1)
    h1 = gas.h_products(T1, far)
    rothalpy = h1 + 0.5 * W1 * W1
    incidence = None if geom.beta1_metal_deg is None else beta1 - geom.beta1_metal_deg
    dh_inc = 0.0 if incidence is None else geom.k_incidence * 0.5 * (W1 * math.sin(math.radians(incidence))) ** 2

    deflection_R = abs(beta1 - beta2)
    zeta_R1 = soderberg(deflection_R, geom.rotor_axial_chord_m, H_R, 'rotor') * geom.loss_scale

    def rotor_state(W, zeta=None):
        h2 = rothalpy - 0.5 * W * W
        T2 = thermo.temperature_fast(h2, far)
        z = zeta_R1 if zeta is None else zeta
        T2s = thermo.temperature_fast(h2 - z * 0.5 * W * W - dh_inc, far)
        P2 = thermo.pressure(T2s, T1, P1, far, R)
        return T2, P2, P2 / (R * T2)

    wmax = math.sqrt(2 * (rothalpy - gas.h_products(max(gas._T_MIN + 1, 0.4 * T1), far)))
    W2, rotor_choke_ratio = _flux_branch(rotor_state, A_R, mdot, wmax, 'rotor relative throat')
    T2, P2, rho2 = rotor_state(W2)
    fRe_R, Re_R = _reynolds_factor(rho2, W2, s_R, H_R, beta2, T2)
    zeta_R = zeta_R1 * fRe_R
    W2, rotor_choke_ratio = _flux_branch(lambda w: rotor_state(w, zeta_R), A_R, mdot, wmax,
                                         'rotor relative throat')
    T2, P2, rho2 = rotor_state(W2, zeta_R)
    b2 = math.radians(beta2)
    Cx2, Wt2 = W2 * math.cos(b2), W2 * math.sin(b2)
    Ct2 = U + Wt2
    C2 = math.hypot(Cx2, Ct2)
    g2 = thermo.gamma(T2, far, R)
    M2rel = W2 / math.sqrt(g2 * R * T2)
    M2 = C2 / math.sqrt(g2 * R * T2)

    # ---- work, exit totals -----------------------------------------------------
    w_euler = U * (Ct1 - Ct2)
    h2 = gas.h_products(T2, far)
    h02_passage = h2 + 0.5 * C2 * C2
    energy_residual = (h01 - h02_passage) - w_euler
    tip_frac = geom.tip_clearance_m / H_R
    tip_factor = 1.0 - geom.K_tip * tip_frac
    if tip_factor <= 0:
        raise TurbineLimit('tip-clearance model invalid at this clearance/height ratio')
    w = w_euler * tip_factor
    h02 = h01 - w
    T02 = thermo.temperature_fast(h02, far)
    # A work debit cannot be combined with the original passage velocity and
    # temperature: those describe the unpenalised Euler work. Close a distinct
    # empirical mixed plane at the passage static pressure. Its tangential
    # velocity follows Euler work and its axial velocity follows continuity.
    # Axial momentum / leakage-stream mixing losses still require a better model.
    Ct2mix = Ct1 - w / U
    cx_per_K = mdot * R / (P2 * geom.A_rotor_m2)
    T2mix = thermo.bisect(
        lambda T: gas.h_products(T, far) + 0.5 * ((cx_per_K * T) ** 2 + Ct2mix ** 2) - h02,
        gas._T_MIN, T02, tol=1e-8)
    Cx2mix = cx_per_K * T2mix
    C2mix = math.hypot(Cx2mix, Ct2mix)
    alpha2mix = math.degrees(math.atan2(Ct2mix, Cx2mix))
    P02 = thermo.pressure(T02, T2mix, P2, far, R)
    T02_isen = thermo.isentropic_temperature_fast(T01, P02 / P01, far, R)
    T2_isen = thermo.isentropic_temperature_fast(T01, P2 / P01, far, R)
    dh_is_tt = h01 - gas.h_products(T02_isen, far)
    dh_is_ts = h01 - gas.h_products(T2_isen, far)
    eta_tt = w / dh_is_tt if dh_is_tt > 0 and w > 0 else float('nan')
    eta_ts = w / dh_is_ts if dh_is_ts > 0 and w > 0 else float('nan')

    psi = w / (U * U)
    phi = Cx2 / U
    reaction = (h1 - h2) / (h01 - h02_passage) if h01 > h02_passage else float('nan')
    alpha2 = math.degrees(math.atan2(Ct2, Cx2))
    flags = []
    if P2 >= P1:
        flags.append('negative rotor reaction (diffusing rotor passage); Soderberg loss invalid')
    if w <= 0:
        flags.append('stage absorbs work (windmilling)')
    if not all(2e4 <= re <= 1e6 for re in (Re_N, Re_R)):
        flags.append('Reynolds number outside Soderberg correction comfort range')
    if deflection_R > 130:
        flags.append('rotor deflection above ~130 deg; Soderberg extrapolated')
    if incidence is not None and abs(incidence) > 15:
        flags.append(f'incidence {incidence:.1f} deg beyond +/-15 deg; loss model unreliable')
    if M1 > 0.95 or M2rel > 0.95:
        flags.append('near-sonic NGV or rotor exit; subsonic-branch model at its limit')
    return dict(
        stage_id=geom.stage_id, mdot_kg_s=mdot, N_rpm=N_rpm, U_mean_m_s=U,
        T01_K=T01, P01_Pa=P01, T1_K=T1, P1_Pa=P1, C1_m_s=C1, M1=M1, alpha1_deg=alpha1,
        W1_m_s=W1, beta1_deg=beta1, M1_rel=M1rel, incidence_deg=incidence,
        T2_K=T2, P2_Pa=P2, W2_m_s=W2, beta2_deg=beta2, M2_rel=M2rel, C2_m_s=C2, M2=M2,
        alpha2_exit_swirl_deg=alpha2, Cx2_m_s=Cx2,
        mixed_exit=dict(T_static_K=T2mix, P_static_Pa=P2, Cx_m_s=Cx2mix, Ct_m_s=Ct2mix,
                        C_m_s=C2mix, alpha_deg=alpha2mix, annulus_area_m2=geom.A_rotor_m2,
                        closure='empirical work debit at fixed passage static pressure; mass, energy and Euler closure'),
        T02_passage_K=thermo.temperature_fast(h02_passage, far),
        w_euler_J_kg=w_euler, w_J_kg=w, power_W=mdot * w,
        T02_K=T02, P02_Pa=P02, PR_tt=P01 / P02, PR_ts=P01 / P2,
        eta_tt=eta_tt, eta_ts=eta_ts, psi=psi, phi=phi, reaction=reaction,
        zeta_ngv=zeta_N, zeta_rotor=zeta_R, dh_incidence_J_kg=dh_inc, tip_work_factor=tip_factor,
        Re_ngv=Re_N, Re_rotor=Re_R, ngv_flow_fraction_of_max=ngv_choke_ratio,
        rotor_flow_fraction_of_max=rotor_choke_ratio, A_ngv_throat_m2=A_N, A_rotor_throat_m2=A_R,
        energy_residual_J_kg=energy_residual, flags=flags)


def stage_from_records(turbine, ngv, overrides=None):
    """Build StageGeometry from validated component records (core.records.Record)."""
    o = overrides or {}
    kw = dict(
        stage_id=f'{turbine.id}+{ngv.id}',
        r_hub_m=turbine.si('hub_diameter') / 2, r_tip_m=turbine.si('tip_diameter') / 2,
        ngv_r_hub_m=ngv.si('vane_hub_diameter') / 2, ngv_r_tip_m=ngv.si('vane_tip_diameter') / 2,
        alpha1_deg=ngv.param('exit_flow_angle')['value'],
        beta2_deg=turbine.param('rotor_exit_relative_angle')['value'],
        ngv_axial_chord_m=ngv.si('vane_axial_chord'),
        rotor_axial_chord_m=turbine.si('blade_axial_width_at_rim'),
        ngv_count=int(ngv.param('vane_count_estimate')['value']),
        rotor_count=int(turbine.param('blade_count_estimate')['value']),
        tip_clearance_m=turbine.si('tip_clearance_design'),
        A_ngv_throat_m2=ngv.si('throat_area') if ngv.has_value('throat_area') else None,
        A_rotor_throat_m2=turbine.si('rotor_throat_area') if turbine.has_value('rotor_throat_area') else None,
        beta1_metal_deg=(math.degrees(turbine.si('rotor_inlet_metal_angle'))
                         if turbine.has_value('rotor_inlet_metal_angle') else None),
        source_note='dimensions from supplier drawings; angles are assumptions unless throat areas are supplied')
    kw.update(o)
    return StageGeometry(**kw)
