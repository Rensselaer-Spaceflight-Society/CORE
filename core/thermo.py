"""Thermally perfect, fixed-composition screening model using gas.cp(T).

Products remain a heuristic; numerical conservation is not chemical validation.
No extrapolation outside the shared property interval is permitted.
"""
import math
from core import gas


def positive(**values):
    for name, value in values.items():
        if not math.isfinite(value) or value <= 0:
            raise gas.GasError(f"{name} must be finite and positive")


def efficiency(**values):
    positive(**values)
    if any(v > 1 for v in values.values()):
        raise gas.GasError("efficiencies must be in (0, 1]")


def bisect(fn, lo, hi, tol=1e-9):
    flo, fhi = fn(lo), fn(hi)
    if not all(math.isfinite(v) for v in (flo, fhi)) or flo * fhi > 0:
        raise gas.GasError("requested state is outside the property/flow bracket")
    for _ in range(120):
        mid = (lo + hi) / 2
        fm = fn(mid)
        if not math.isfinite(fm):
            raise gas.GasError("nonfinite inversion residual")
        if hi - lo < tol or fm == 0:
            return mid
        if flo * fm <= 0:
            hi = mid
        else:
            lo, flo = mid, fm
    raise gas.GasError("inversion did not converge")


def temperature(h, far=0):
    return bisect(lambda t: gas.h_products(t, far) - h, gas._T_MIN, gas._T_MAX)


def entropy(T, far=0):
    """Integral cp(T)/T; pressure term is -R ln(P). Datum cancels."""
    t = gas._clamp(T)
    gas.cp_products(t, far)  # composition validation
    return (gas._A4*t**4/4 + gas._A3*t**3/3 + gas._A2*t*t/2
            + gas._A1*t + gas._A0*math.log(t)) * (1 + gas._PRODUCT_CP_SLOPE*far)


def isentropic_temperature(T0, pressure_ratio, far=0, R=287.05):
    positive(pressure_ratio=pressure_ratio, R=R)
    target = entropy(T0, far) + R*math.log(pressure_ratio)
    return bisect(lambda t: entropy(t, far)-target, gas._T_MIN, gas._T_MAX)


def pressure(T, T0, P0, far=0, R=287.05):
    positive(P0=P0, R=R)
    return P0*math.exp((entropy(T, far)-entropy(T0, far))/R)


def gamma(T, far=0, R=287.05):
    cp = gas.cp_products(T, far)
    positive(R=R, cv=cp-R)
    return cp/(cp-R)


def static(T0, P0, V, far=0, R=287.05):
    if not math.isfinite(V) or V < 0:
        raise gas.GasError("speed must be finite and nonnegative")
    T = temperature(gas.h_products(T0, far)-V*V/2, far)
    return T, pressure(T, T0, P0, far, R)


def sonic(T0, far=0, R=287.05):
    h0 = gas.h_products(T0, far)
    T = bisect(lambda t: 2*(h0-gas.h_products(t, far))-gamma(t,far,R)*R*t,
               gas._T_MIN, T0)
    return math.sqrt(gamma(T,far,R)*R*T), T


def area_state(mdot, A, T0, P0, far=0, R=287.05):
    positive(mdot=mdot, A=A, P0=P0)
    vmax, _ = sonic(T0, far, R)
    def residual(v):
        t, p = static(T0,P0,v,far,R)
        return p/(R*t)*v*A-mdot
    V = bisect(residual, 0, vmax)
    T, P = static(T0,P0,V,far,R)
    return V, T, P


def nozzle(T0, P0, Pamb, far=0, R=287.05, Cv=1):
    """Convergent screening nozzle; Cv scales ideal kinetic energy by Cv².

    Critical state solves actual M=1 with consistent actual static enthalpy.
    This loss treatment is approximate and needs measured discharge data.
    """
    positive(P0=P0, Pamb=Pamb)
    efficiency(Cv=Cv)
    if P0 <= Pamb:
        raise gas.GasError("no positive nozzle pressure head")
    h0 = gas.h_products(T0,far)
    def actual(ti):
        h = h0-Cv**2*(h0-gas.h_products(ti,far))
        t = temperature(h,far)
        v = math.sqrt(max(0,2*(h0-h)))
        return v,t
    ti_star = bisect(lambda ti: actual(ti)[0]**2-gamma(actual(ti)[1],far,R)*R*actual(ti)[1], gas._T_MIN,T0)
    pstar = pressure(ti_star,T0,P0,far,R)
    choked = Pamb <= pstar
    ti = ti_star if choked else isentropic_temperature(T0,Pamb/P0,far,R)
    v,t = actual(ti)
    return v,t,pstar if choked else Pamb,choked


def orifice_flux(Pup, T, Pdown, Cd, R=287.05):
    """Local reservoir-to-static orifice approximation, with sonic cap."""
    efficiency(Cd=Cd)
    V, Ts, Ps, _ = nozzle(T,Pup,Pdown,R=R)
    return Cd*Ps/(R*Ts)*V
