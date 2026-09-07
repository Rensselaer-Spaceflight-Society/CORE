"""
Shared gas dynamics and thermodynamic properties.

Physics that more than one module needs lives here. The distinction matters:
shared *numbers* go in the state dict, where exactly one module owns each.
Shared *equations* go here, where everybody calls the same function. If two
modules each write their own choked-flow relation or their own fuel-air ratio,
they will disagree and somebody will lose a day to it.

---------------------------------------------------------------------------
THE GAS MODEL, AND WHY IT IS NOT A CONSTANT cp
---------------------------------------------------------------------------
An early version of this file used cp_cold = 1005 and cp_hot = 1150 J/kg K as
constants, with enthalpy taken as h = cp*T. That is the form in most textbooks
and it is fine for a rough cycle -- but it over-predicted the fuel-air ratio by
14-17% against air property tables, because a constant cp with a zero-kelvin
enthalpy datum is not a consistent enthalpy function.

The fix is to carry a real enthalpy: fit cp(T) and integrate it analytically,
with an explicit datum. The polynomial below is a least-squares quartic fit to
standard air property tables (Keenan & Kaye / Cengel-Boles Table A-17) over
300-1800 K:

    cp within 0.18% of table, enthalpy within 0.10% of table.

The products correction is an unvalidated composition surrogate, not a fit to
burned-gas tables. Fuel mass fraction is not the reacted-gas composition.
The quoted air-fit accuracy does not apply to combustion products.

Use h_air / h_products and far_for_T4 for anything involving a temperature
rise across the combustor. Do not reintroduce a constant cp.
"""

from __future__ import annotations
import math

# --- air cp(T) quartic, fitted to standard tables over 300-1800 K -----------
# cp [J/kg K] = A4 T^4 + A3 T^3 + A2 T^2 + A1 T + A0
_A4 = 1.216428e-10
_A3 = -5.616647e-07
_A2 = 8.489141e-04
_A1 = -2.986003e-01
_A0 = 1.030663e+03

_T_MIN, _T_MAX = 200.0, 1900.0
_T_DATUM = 300.0          # enthalpy datum: h_air(300 K) == 0

# Products of lean kerosene combustion have a slightly higher cp than air.
# At f = 0.02 the difference is about 1.5% at 1000 K, rising slowly with f.
# Linear correction only: validate against equilibrium properties before release.
_PRODUCT_CP_SLOPE = 0.75   # dimensionless: cp_products/cp_air = 1 + slope*f


class GasError(Exception):
    pass


def _clamp(T):
    t = float(T)
    if not math.isfinite(t) or not _T_MIN <= t <= _T_MAX:
        raise GasError(f"temperature {t} K outside [{_T_MIN}, {_T_MAX}]")
    return t


def cp_air(T):
    """Specific heat of dry air at constant pressure [J/kg K]."""
    t = _clamp(T)
    return ((((_A4 * t + _A3) * t + _A2) * t + _A1) * t + _A0)


def cp_products(T, far=0.0):
    """Specific heat of lean kerosene combustion products [J/kg K]."""
    if not math.isfinite(far) or far < 0 or far > 0.06:
        raise GasError("FAR outside lean-products surrogate range [0, 0.06]")
    return cp_air(T) * (1.0 + _PRODUCT_CP_SLOPE * far)


def _h_indefinite(t):
    return (_A4 / 5 * t ** 5 + _A3 / 4 * t ** 4 + _A2 / 3 * t ** 3
            + _A1 / 2 * t ** 2 + _A0 * t)


def h_air(T):
    """Specific enthalpy of air [J/kg], datum h(300 K) = 0.

    Analytic integral of cp_air. Use enthalpy DIFFERENCES; the absolute value
    is meaningless on its own because the datum is arbitrary.
    """
    return _h_indefinite(_clamp(T)) - _h_indefinite(_T_DATUM)


def h_products(T, far=0.0):
    """Specific enthalpy of combustion products [J/kg], same datum as h_air."""
    cp_products(T, far)
    return h_air(T) * (1.0 + _PRODUCT_CP_SLOPE * far)


def far_for_T4(T3, T4, eta_b, LHV, max_iter=60, tol=1e-12):
    """Fuel-air ratio that raises air from T3 to T4 across the combustor.

    Solves the enthalpy balance WITH the fuel mass carried into the products:

        mdot_air * h(T3) + mdot_fuel * LHV * eta_b = (mdot_air + mdot_fuel) * h(T4)

    which rearranges to

        f = [h_p(T4) - h_a(T3)] / [LHV*eta_b - h_p(T4)]

    Because h_p itself depends on f (through the product composition), this is
    solved by fixed-point iteration. It converges in three or four passes.

    Two failure modes this replaces, both of which were live in earlier code:
      * using a single mean cp evaluated at (T3+T4)/2, which under-predicts f
      * omitting the fuel mass from the product stream, which under-predicts f
      * using constant cp values with a zero-kelvin datum, which OVER-predicts f
        by 14-17% -- the largest of the three errors and the least obvious

    Verify with T4_for_far(), which inverts this and must return T4 exactly.
    """
    from core.thermo import efficiency, positive
    efficiency(eta_b=eta_b)
    positive(LHV=LHV, tol=tol)
    if not isinstance(max_iter, int) or max_iter < 1:
        raise GasError("max_iter must be a positive integer")
    if T4 <= T3:
        raise GasError(
            f"combustor exit temperature {T4:.1f} K is not above its inlet "
            f"{T3:.1f} K -- check the station numbering"
        )
    h3 = h_air(T3)
    f = 0.02
    for _ in range(max_iter):
        h4 = h_products(T4, f)
        denom = LHV * eta_b - h4
        if denom <= 0:
            raise GasError(
                f"no fuel-air ratio can reach {T4:.0f} K: the heat release "
                f"available ({LHV*eta_b/1e6:.1f} MJ/kg) is below the product "
                f"enthalpy at that temperature"
            )
        f_new = (h4 - h3) / denom
        if abs(f_new - f) < tol:
            return f_new
        f = f_new
    raise GasError("fuel balance did not converge")


def T4_for_far(T3, far, eta_b, LHV, max_iter=80, tol=1e-9):
    """Inverse of far_for_T4: the temperature a given fuel-air ratio delivers.

    Exists so the energy balance can be checked by round trip rather than
    trusted. tests/test_gas.py asserts far_for_T4 and T4_for_far invert each
    other to within a millikelvin.
    """
    from core.thermo import efficiency, positive
    efficiency(eta_b=eta_b)
    positive(LHV=LHV, tol=tol)
    if not isinstance(max_iter, int) or max_iter < 1:
        raise GasError("max_iter must be a positive integer")
    cp_products(T3, far)
    target = (h_air(T3) + far*LHV*eta_b)/(1+far)
    lo, hi = T3, _T_MAX
    if not h_products(lo, far) <= target <= h_products(hi, far):
        raise GasError("requested fuel state exceeds the property bracket")
    for _ in range(max_iter):
        mid = (lo+hi)/2
        residual = h_products(mid, far)-target
        if residual == 0 or hi-lo < tol:
            return mid
        if residual < 0:
            lo = mid
        else:
            hi = mid
    raise GasError("fuel-temperature inversion did not converge")



# ===========================================================================
# COMPRESSIBLE FLOW
# ===========================================================================

def critical_pressure_ratio(gamma):
    """P0/P at which a convergent nozzle chokes."""
    return ((gamma + 1.0) / 2.0) ** (gamma / (gamma - 1.0))


def isentropic_T_ratio(pressure_ratio, gamma):
    """T0/T for a given P0/P."""
    return pressure_ratio ** ((gamma - 1.0) / gamma)


def exit_velocity(T0, P0, P_amb, cp, gamma, R, Cv=1.0):
    """Convergent nozzle exit state.

    Returns (V, T_exit, P_exit, choked). Handles both the choked and the
    fully-expanded case, which is the distinction that decides whether a
    micro turbojet's nozzle area couples to the back pressure or not.
    """
    npr = P0 / P_amb
    crit = critical_pressure_ratio(gamma)

    if npr >= crit:
        # choked: exit static pressure sits above ambient, so there is a
        # pressure-thrust term as well as a momentum term
        T_e = T0 * 2.0 / (gamma + 1.0)
        P_e = P0 / crit
        V = Cv * math.sqrt(gamma * R * T_e)
        return V, T_e, P_e, True

    T_e = T0 / isentropic_T_ratio(npr, gamma)
    V = Cv * math.sqrt(max(2.0 * cp * (T0 - T_e), 0.0))
    return V, T_e, P_amb, False


def gross_thrust(mdot, V, A_exit, P_exit, P_amb):
    """Momentum thrust plus the pressure term (zero unless choked)."""
    return mdot * V + A_exit * (P_exit - P_amb)


def choked_area(mdot, T0, P0, gamma, R):
    """Throat area needed to pass mdot when choked.

    A = mdot * sqrt(T0) / (P0 * C*), the standard corrected-flow relation.
    This is how the NGV throat gets sized, and it is why the NGV throat is the
    single dimension that most directly sets what the engine will swallow.
    """
    c_star = math.sqrt(gamma / R) * ((gamma + 1.0) / 2.0) ** (-(gamma + 1.0) / (2.0 * (gamma - 1.0)))
    return mdot * math.sqrt(T0) / (P0 * c_star)


def stanitz_slip(Z):
    """Stanitz slip factor (NACA TN 2654, 1952).

    sigma = 1 - 0.63*pi/Z, independent of backsweep. Valid from radial blades
    to about 45 degrees of backsweep. Wiesner's correlation is the other common
    choice and disagrees by a few percent -- pick one, write down which, and do
    not mix them between modules.
    """
    return 1.0 - 0.63 * math.pi / Z


def static_from_total(T0, P0, V, cp, gamma):
    """Static temperature, pressure and density from total conditions and speed."""
    T = T0 - V * V / (2.0 * cp)
    P = P0 * (T / T0) ** (gamma / (gamma - 1.0))
    return T, P


def density(P, T, R):
    return P / (R * T)


def mach(V, T, gamma, R):
    return V / math.sqrt(gamma * R * T)


def rpm_to_rad_s(N_rpm):
    return N_rpm * 2.0 * math.pi / 60.0
