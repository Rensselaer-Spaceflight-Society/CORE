"""
M13 -- Single-stage axial turbine: mean-line sizing.

Stage loading psi = dh0/U^2 is the design choice that fixes blade speed, and
blade speed plus rpm fixes the mean diameter. Flow coefficient phi = Cx/U then
fixes the axial velocity, and continuity gives the annulus area and blade height.

Watch the direction of information here, because it catches people out: gas
flows NGV -> rotor, but INFORMATION flows rotor -> NGV. The rotor's velocity
triangles decide what swirl angle the NGV has to deliver, so the rotor is sized
first and the NGV is sized to feed it. Physical order and dependency order are
not the same thing, and the solver cares only about the second.

CROSS-CHECK AGAINST KJ66: 66 mm tip, 44 mm hub, 11 mm blade, 23 blades,
117,000 rpm -> mean diameter 55 mm, U_mean = 337 m/s.
"""

import math
from core.module import module
from core import gas, thermo


@module(
    tier=2,
    title="Turbine mean-line: diameters, blade height, count, mass",
    owner="TURBO-3", second="TURBO-4",
    status="draft",
    reads=[
        "w_turb_J_kg", "psi_turb_ratio", "phi_turb_ratio", "N_rpm",
        "mdot_kg_s", "FAR_ratio", "T05_K", "P05_Pa",
        "R_gas_J_kgK", "cp_hot_J_kgK", "gamma_hot_ratio",
        "rho_turb_kg_m3", "aspect_ratio_turb_ratio", "solidity_turb_ratio",
        "tip_clear_frac", "reaction_turb_ratio", "blade_taper_factor_ratio",
    ],
    writes=[
        "D_turb_tip_m", "D_turb_hub_m", "D_turb_mean_m", "h_blade_m",
        "n_blades_turb_count", "U_turb_mean_m_s", "A_annulus_turb_m2",
        "t_tip_clear_m", "m_turb_kg", "I_turb_kg_m2",
        "m_blade_kg", "r_blade_cg_m", "A_blade_root_m2", "U_turb_tip_m_s",
    ],
)
def m13_turbine(s):
    omega = gas.rpm_to_rad_s(s["N_rpm"])
    mdot_hot = s["mdot_kg_s"] * (1.0 + s["FAR_ratio"])

    # -- blade speed from stage loading -------------------------------------
    U_mean = math.sqrt(s["w_turb_J_kg"] / s["psi_turb_ratio"])
    D_mean = 2.0 * U_mean / omega

    # -- annulus from continuity at turbine exit ----------------------------
    Cx = s["phi_turb_ratio"] * U_mean
    Ctheta3 = U_mean*(1-s['reaction_turb_ratio']-s['psi_turb_ratio']/2)
    T5_static, P5_static = thermo.static(s['T05_K'],s['P05_Pa'],
        math.hypot(Cx,Ctheta3),s['FAR_ratio'],s['R_gas_J_kgK'])
    rho5 = gas.density(P5_static, T5_static, s["R_gas_J_kgK"])
    A_ann = mdot_hot / (rho5 * Cx)

    h = A_ann / (math.pi * D_mean)
    D_tip = D_mean + h
    D_hub = D_mean - h
    thermo.positive(turbine_hub_diameter=D_hub)

    # -- blade count from solidity ------------------------------------------
    chord = h / s["aspect_ratio_turb_ratio"]
    pitch = chord / s["solidity_turb_ratio"]
    n_blades = max(3, int(round(math.pi * D_mean / pitch)))

    # -- mass and inertia ---------------------------------------------------
    # disc: annulus from bore to hub, at a thickness scaled off the hub radius
    r_hub, r_tip = D_hub / 2.0, D_tip / 2.0
    t_disc = 0.18 * r_hub
    r_bore = 0.28 * r_hub
    vol_disc = math.pi * (r_hub ** 2 - r_bore ** 2) * t_disc
    # blades: constant section, 8% of pitch thick, tapering to 60% at the tip
    # Seed is now explicitly the tip/root SECTION AREA ratio (linear taper).
    taper = s['blade_taper_factor_ratio']
    if not 0 < taper <= 1:
        raise ValueError('blade taper must be a tip/root section ratio in (0,1]')
    A_root = 0.08*pitch*chord
    A_blade = A_root*(1+taper)/2
    vol_blades = n_blades * A_blade * h
    m = (vol_disc + vol_blades) * s["rho_turb_kg_m3"]

    # polar inertia: disc as an annulus, blades as a ring at their centroid
    m_disc = vol_disc * s["rho_turb_kg_m3"]
    m_blades = vol_blades * s["rho_turb_kg_m3"]
    r_cg_blade = r_hub+h*(1+2*taper)/(3*(1+taper))
    mean_r2 = r_hub**2+2*r_hub*h*(1+2*taper)/(3*(1+taper))+h*h*(1+3*taper)/(6*(1+taper))
    I = 0.5 * m_disc * (r_hub ** 2 + r_bore ** 2) + m_blades * mean_r2

    return {
        "m_blade_kg": vol_blades/n_blades*s['rho_turb_kg_m3'],
        "r_blade_cg_m": r_cg_blade,
        "A_blade_root_m2": A_root,
        "U_turb_tip_m_s": omega*D_tip/2,
        "D_turb_tip_m": D_tip,
        "D_turb_hub_m": D_hub,
        "D_turb_mean_m": D_mean,
        "h_blade_m": h,
        "n_blades_turb_count": float(n_blades),
        "U_turb_mean_m_s": U_mean,
        "A_annulus_turb_m2": A_ann,
        "t_tip_clear_m": s["tip_clear_frac"] * h,
        "m_turb_kg": m,
        "I_turb_kg_m2": I,
    }
