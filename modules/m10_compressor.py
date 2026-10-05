"""
M10 -- Centrifugal compressor: impeller sizing.

Given the work the cycle demands and the speed you chose, Euler plus a slip
factor gives you the tip speed, and tip speed plus rpm gives you the diameter.
That is the whole of preliminary radial compressor sizing in one sentence.

    dh = U2 * Ctheta2,   Ctheta2 = sigma * (U2 - Cm2*tan(beta2b))

For radial blades (beta2b = 0) this collapses to dh = sigma*U2^2 and U2 falls
straight out. With backsweep it is a quadratic in U2, solved below.

The inducer is sized separately, to keep the relative Mach number at the shroud
below about 0.9. That constraint plus mass flow is what fixes the inducer
diameter, and it is usually the thing that stops you spinning faster.

D2_m is the single most-read number this module produces. The diffuser, the
casing and the whole axial stack-up all wait on it.

CROSS-CHECK AGAINST KJ66: 66 mm exducer at 117,000 rpm gives U2 = 404 m/s.

FIXED PURCHASED WHEEL (compressor_fixed_wheel_flag = 1): the wheel dimensions
come from the component record (D2/D1s/D1h/b2/mass seeds) and are NOT changed.
The Euler/slip relations then run in reverse as DIAGNOSTICS: the tangential
exit velocity the cycle work implies, the implied work coefficient dh/U2^2 and
exit flow angle, and the inducer relative Mach from continuity on the actual
inducer. A work coefficient above the Stanitz slip value means the cycle asks
more of the wheel than its blade count supports at this speed.
"""

import math
from core.module import module
from core import gas, thermo


@module(
    tier=2,
    title="Impeller sizing: exducer, inducer, blade width",
    owner="TURBO-1", second="TURBO-2",
    status="draft",
    reads=[
        "mdot_kg_s", "T02_K", "P02_Pa", "T03_K", "P03_Pa",
        "N_rpm", "Z_imp_count", "beta2b_deg", "inducer_hub_tip_ratio",
        "Cm2_U2_ratio", "beta1s_deg", "blockage_frac",
        "cp_cold_J_kgK", "gamma_cold_ratio", "R_gas_J_kgK",
        "power_input_factor_ratio", "rho_imp_kg_m3",
    ],
    optional_reads=["compressor_fixed_wheel_flag", "D2_fixed_m", "D1s_fixed_m", "D1h_fixed_m",
                    "b2_fixed_m", "m_imp_fixed_kg", "Z_imp_fixed_count"],
    writes=[
        "U2_m_s", "D2_m", "D1s_m", "D1h_m", "b2_m", "sigma_slip_ratio",
        "Cm2_m_s", "Ctheta2_m_s", "alpha2_deg", "M2_abs_ratio",
        "M1s_rel_ratio", "rho03_kg_m3", "m_imp_kg", "work_coeff_c_ratio",
    ],
    notes="Stanitz slip. Inducer sized to a target shroud relative flow angle.",
)
def m10_compressor(s):
    if "compressor_fixed_wheel_flag" in s and s["compressor_fixed_wheel_flag"]:
        return _fixed_wheel(s)
    cp = s["cp_cold_J_kgK"]
    g = s["gamma_cold_ratio"]
    R = s["R_gas_J_kgK"]
    omega = gas.rpm_to_rad_s(s["N_rpm"])
    mdot = s["mdot_kg_s"]

    # -- exducer ------------------------------------------------------------
    sigma = gas.stanitz_slip(s["Z_imp_count"])
    # the power input factor covers disc friction and recirculation: the
    # impeller has to do slightly more work than the air ends up with
    dh = s["power_input_factor_ratio"] * (gas.h_air(s["T03_K"]) - gas.h_air(s["T02_K"]))

    k = s["Cm2_U2_ratio"]
    tb = math.tan(math.radians(s["beta2b_deg"]))
    # dh = sigma*U2*(U2 - k*U2*tb)  ->  U2 = sqrt(dh / (sigma*(1 - k*tb)))
    U2 = math.sqrt(dh / (sigma * (1.0 - k * tb)))
    D2 = 2.0 * U2 / omega

    Cm2 = k * U2
    Ctheta2 = sigma * (U2 - Cm2 * tb)
    C2 = math.hypot(Cm2, Ctheta2)
    alpha2 = math.degrees(math.atan2(Ctheta2, Cm2))   # from radial

    T2s, P2s = thermo.static(s["T03_K"], s["P03_Pa"], C2, R=R)
    rho2 = gas.density(P2s, T2s, R)
    M2 = gas.mach(C2, T2s, thermo.gamma(T2s,R=R), R)

    # exit blade width from continuity around the exducer circumference
    b2 = mdot / (rho2 * math.pi * D2 * Cm2 * (1.0 - s["blockage_frac"]))

    # -- inducer ------------------------------------------------------------
    # Hold the shroud relative flow angle at its optimum (55-65 deg from axial)
    # and solve for the shroud diameter that passes the mass flow. Static
    # density depends on the axial velocity, so iterate a couple of times.
    nu = s["inducer_hub_tip_ratio"]
    tan_b1s = math.tan(math.radians(s["beta1s_deg"]))
    rho1 = gas.density(s["P02_Pa"], s["T02_K"], R)     # first guess: total
    D1s = 0.6 * D2
    for _ in range(40):
        # D1s^3 = mdot * 4 * tan(b1s) / (rho1 * pi * (1-nu^2) * omega/2 * ... )
        D1s_new = (
            mdot * 8.0 * tan_b1s
            / (rho1 * math.pi * (1.0 - nu * nu) * omega * (1.0 - s["blockage_frac"]))
        ) ** (1.0 / 3.0)
        U1s = omega * D1s_new / 2.0
        Cx1 = U1s / tan_b1s
        T1s, P1s = thermo.static(s["T02_K"], s["P02_Pa"], Cx1, R=R)
        rho1_new = gas.density(P1s, T1s, R)
        if abs(rho1_new - rho1) < 1e-9 and abs(D1s_new - D1s) < 1e-9:
            rho1, D1s = rho1_new, D1s_new
            break
        rho1, D1s = rho1_new, D1s_new

    else:
        raise ValueError("inducer continuity did not converge in 40 passes")

    U1s = omega * D1s / 2.0
    Cx1 = U1s / tan_b1s
    T1_static, _ = thermo.static(s["T02_K"], s["P02_Pa"], Cx1, R=R)
    W1s = math.hypot(Cx1, U1s)
    M1s_rel = gas.mach(W1s, T1_static, thermo.gamma(T1_static,R=R), R)

    # -- mass ---------------------------------------------------------------
    # crude but honest: a back-disc plus blades, filled to about 35% of the
    # swept cylinder. Replace with the CAD mass properties once the model exists.
    vol = 0.35 * math.pi / 4.0 * D2 * D2 * (b2 + 0.35 * D2)
    m_imp = vol * s["rho_imp_kg_m3"]

    return {
        "U2_m_s": U2,
        "D2_m": D2,
        "D1s_m": D1s,
        "D1h_m": nu * D1s,
        "b2_m": b2,
        "sigma_slip_ratio": sigma,
        "Cm2_m_s": Cm2,
        "Ctheta2_m_s": Ctheta2,
        "alpha2_deg": alpha2,
        "M2_abs_ratio": M2,
        "M1s_rel_ratio": M1s_rel,
        "rho03_kg_m3": rho2,
        "m_imp_kg": m_imp,
        "work_coeff_c_ratio": dh / (U2 * U2),
    }


def _fixed_wheel(s):
    R = s["R_gas_J_kgK"]
    omega = gas.rpm_to_rad_s(s["N_rpm"])
    D2, D1s, D1h, b2 = s["D2_fixed_m"], s["D1s_fixed_m"], s["D1h_fixed_m"], s["b2_fixed_m"]
    thermo.positive(D2=D2, D1s=D1s, D1h=D1h, b2=b2)
    if not D1h < D1s < D2:
        raise ValueError("fixed wheel needs hub < inducer < exducer diameters")
    mdot = s["mdot_kg_s"]
    U2 = omega * D2 / 2.0
    Z = s["Z_imp_fixed_count"] if "Z_imp_fixed_count" in s else s["Z_imp_count"]
    sigma = gas.stanitz_slip(Z)
    # The air's total-enthalpy rise is the whole shaft work: blade (Euler) work times the
    # power input factor (disc friction/recirculation also end up in the gas), so the
    # blade work is dh0 / PIF. (The legacy sizing branch above multiplies instead; that
    # inflates its D2 by ~PIF and is left for the team because it moves the baseline.)
    dh = (gas.h_air(s["T03_K"]) - gas.h_air(s["T02_K"])) / s["power_input_factor_ratio"]
    Ctheta2 = dh / U2                       # Euler, no inlet swirl
    # exit meridional velocity from continuity at the actual exit width (iterate density)
    Cm2 = 0.3 * U2
    for _ in range(60):
        C2 = math.hypot(Cm2, Ctheta2)
        T2s, P2s = thermo.static(s["T03_K"], s["P03_Pa"], C2, R=R)
        rho2 = gas.density(P2s, T2s, R)
        Cm2_new = mdot / (rho2 * math.pi * D2 * b2 * (1.0 - s["blockage_frac"]))
        if abs(Cm2_new - Cm2) < 1e-9:
            break
        Cm2 = Cm2_new
    else:
        raise ValueError("fixed-wheel exit continuity did not converge")
    C2 = math.hypot(Cm2, Ctheta2)
    alpha2 = math.degrees(math.atan2(Ctheta2, Cm2))
    M2 = gas.mach(C2, T2s, thermo.gamma(T2s, R=R), R)
    # inducer: axial velocity from continuity on the actual annulus, relative Mach at shroud
    A1 = math.pi / 4 * (D1s ** 2 - D1h ** 2) * (1.0 - s["blockage_frac"])
    Cx = 50.0
    for _ in range(60):
        T1, P1 = thermo.static(s["T02_K"], s["P02_Pa"], Cx, R=R)
        Cx_new = mdot / (gas.density(P1, T1, R) * A1)
        if abs(Cx_new - Cx) < 1e-9:
            break
        Cx = Cx_new
    else:
        raise ValueError("fixed-wheel inducer continuity did not converge")
    U1s = omega * D1s / 2.0
    M1s_rel = gas.mach(math.hypot(Cx, U1s), T1, thermo.gamma(T1, R=R), R)
    return {
        "U2_m_s": U2, "D2_m": D2, "D1s_m": D1s, "D1h_m": D1h, "b2_m": b2,
        "sigma_slip_ratio": sigma, "Cm2_m_s": Cm2, "Ctheta2_m_s": Ctheta2, "alpha2_deg": alpha2,
        "M2_abs_ratio": M2, "M1s_rel_ratio": M1s_rel, "rho03_kg_m3": rho2,
        "m_imp_kg": s["m_imp_fixed_kg"], "work_coeff_c_ratio": dh / (U2 * U2),
    }
