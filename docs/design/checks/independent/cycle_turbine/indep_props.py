"""Independent property helpers for the fork-A audit scripts.

Only PROPERTY functions are taken from the repository (core.gas: cp/h of air and of the
lean-products surrogate). Entropy, inversions, isentropic relations, continuity, Euler work,
losses and balances are re-implemented here with scipy quadrature/root finding; nothing from
core.thermo, core.turbine_rating, core.engine_match, core.compressor_map or modules/ is imported.

Run the audit scripts from the repository root so that `core` is importable.
"""
import json
import math
import os
import sys

from scipy.integrate import quad
from scipy.optimize import brentq, minimize_scalar

sys.path.insert(0, os.getcwd())
from core import gas  # noqa: E402  (properties only)

R = 287.05          # J/kg K, the single gas constant the case uses for air and products
T_LO, T_HI = 200.0, 1900.0


def h(T, f=0.0):
    return gas.h_products(T, f)


def cp(T, f=0.0):
    return gas.cp_products(T, f)


def s0(T, f=0.0, Tref=300.0):
    """Temperature part of entropy, integral cp/T dT by adaptive quadrature."""
    return quad(lambda t: cp(t, f) / t, Tref, T, epsabs=1e-11, epsrel=1e-13, limit=200)[0]


def T_of_h(hv, f=0.0):
    return brentq(lambda T: h(T, f) - hv, T_LO, T_HI, xtol=1e-12, rtol=1e-15, maxiter=200)


def T_isentropic(T1, p_ratio, f=0.0):
    """Temperature reached isentropically from T1 at pressure ratio p_ratio = P2/P1."""
    target = s0(T1, f) + R * math.log(p_ratio)
    return brentq(lambda T: s0(T, f) - target, T_LO, T_HI, xtol=1e-11, rtol=1e-15, maxiter=200)


def P_isentropic(T2, T1, P1, f=0.0):
    """Pressure at T2 on the isentropic through (T1, P1)."""
    return P1 * math.exp((s0(T2, f) - s0(T1, f)) / R)


def gamma(T, f=0.0):
    c = cp(T, f)
    return c / (c - R)


def mu_repo_power_law(T):
    """The repository's hot-gas viscosity model, restated (core/turbine_rating.py:47-49)."""
    return 3.5e-5 * (T / 1000.0) ** 0.7


def mu_sutherland_air(T):
    """Sutherland's law for air, mu_ref 1.716e-5 Pa s at 273.15 K, S = 110.4 K (standard constants).

    Lean kerosene products (FAR ~0.013, ~97 % N2+O2 by mole) are within a few percent of air.
    Tabulated air (Incropera Table A.4): 3.698e-5 Pa s at 800 K, 4.244e-5 at 1000 K.
    """
    return 1.716e-5 * (T / 273.15) ** 1.5 * (273.15 + 110.4) / (T + 110.4)


def soderberg(deflection_deg, axial_chord, height, kind):
    """Soderberg nominal loss with the aspect-ratio correction (Dixon & Hall presentation).

    zeta* = 0.04 (1 + 1.5 (eps/100)^2); 1 + zeta1 = (1 + zeta*)(0.993 + 0.021 b/H) for nozzles and
    (1 + zeta*)(0.975 + 0.075 b/H) for rotors. Re correction applied separately.
    """
    zs = 0.04 * (1.0 + 1.5 * (deflection_deg / 100.0) ** 2)
    r = axial_chord / height
    if kind == 'nozzle':
        return (1.0 + zs) * (0.993 + 0.021 * r) - 1.0
    return (1.0 + zs) * (0.975 + 0.075 * r) - 1.0


def throat_hydraulic_diameter(pitch, height, angle_deg):
    """Dh = 2 o H / (o + H) with throat opening o = s cos(angle) (Dixon & Hall, Soderberg Re basis)."""
    o = pitch * math.cos(math.radians(angle_deg))
    return 2.0 * o * height / (o + height)


def load_results(folder):
    def j(name):
        with open(os.path.join(folder, name), encoding='utf-8') as fh:
            return json.load(fh)
    return j


class Reporter:
    """Prints one line per comparison and tracks unexplained differences above a tolerance."""

    def __init__(self, tol_pct=1.0):
        self.tol_pct = tol_pct
        self.fail = []

    def cmp(self, name, indep, repo, tol_pct=None, abs_tol=None, note=''):
        tol = self.tol_pct if tol_pct is None else tol_pct
        if repo is None or indep is None:
            print(f'{name:<58} indep={indep!s:<16} repo={repo!s:<16} diff=   n/a   OPEN {note}')
            return
        diff = indep - repo
        pct = 100.0 * diff / repo if repo != 0 else (0.0 if diff == 0 else float('inf'))
        ok = (abs(diff) <= abs_tol) if abs_tol is not None else (abs(pct) <= tol)
        flag = 'PASS' if ok else 'DIFF'
        if not ok:
            self.fail.append(name)
        print(f'{name:<58} indep={indep:<16.8g} repo={repo:<16.8g} diff={pct:+9.4f} % {flag} {note}')

    def info(self, name, value, note=''):
        v = f'{value:.8g}' if isinstance(value, (int, float)) else str(value)
        print(f'{name:<58} value={v:<16} INFO {note}')

    def finish(self):
        if self.fail:
            print(f'\nUNEXPLAINED DIFFERENCES (> tolerance): {self.fail}')
            return 1
        print('\nAll comparisons within tolerance.')
        return 0
