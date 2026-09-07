"""
M12 -- Nozzle guide vanes.

The NGV throat area is the most consequential single dimension in the hot
section. When it chokes -- and on a design like this it almost always does at
full power -- it fixes the corrected mass flow the engine can swallow,
regardless of what the compressor would like to deliver. Get it wrong and the
engine either will not make power or will overspeed the compressor into surge.

Sized from the rotor's velocity triangles: the rotor needs a certain absolute
swirl at its inlet, and the NGV exists to produce exactly that.
"""

import math
from core.module import module
from core import gas, thermo


@module(
    tier=2,
    title="NGV throat area, vane count, exit swirl",
    owner="TURBO-3", second="TURBO-4",
    status="draft",
    reads=[
        "mdot_kg_s", "FAR_ratio", "T04_K", "P04_Pa",
        "gamma_hot_ratio", "R_gas_J_kgK",
        "U_turb_mean_m_s", "psi_turb_ratio", "phi_turb_ratio",
        "D_turb_mean_m", "reaction_turb_ratio", "zweifel_ratio",
        "aspect_ratio_ngv_ratio", "n_blades_turb_count",
    ],
    writes=[
        "A_throat_ngv_m2", "n_vanes_ngv_count", "alpha_ngv_exit_deg",
        "ngv_choked_flag", "M_ngv_exit_ratio", "P_ngv_exit_Pa", "T_ngv_exit_K",
    ],
)
def m12_ngv(s):
    mdot_hot = s["mdot_kg_s"] * (1.0 + s["FAR_ratio"])
    g = s["gamma_hot_ratio"]

    # -- swirl the rotor needs ----------------------------------------------
    # For an axial stage: psi = 2*(1 - R - phi*tan(alpha_exit_from_axial))
    # is one common form; here use the direct triangle. With degree of reaction
    # R and loading psi, the NGV exit tangential velocity is:
    #     Ctheta2 = U * (1 - R + psi/2) / 1.0
    U = s["U_turb_mean_m_s"]
    Ctheta2 = U * (1.0 - s["reaction_turb_ratio"] + s["psi_turb_ratio"] / 2.0)
    Cx = s["phi_turb_ratio"] * U
    alpha2 = math.degrees(math.atan2(Ctheta2, Cx))   # from axial

    # -- throat area --------------------------------------------------------
    # Effective area NORMAL to the mean exit flow; not automatically sonic.
    speed = math.hypot(Cx,Ctheta2)
    Ts,Ps = thermo.static(s['T04_K'],s['P04_Pa'],speed,s['FAR_ratio'],s['R_gas_J_kgK'])
    M = speed/math.sqrt(thermo.gamma(Ts,s['FAR_ratio'],s['R_gas_J_kgK'])*s['R_gas_J_kgK']*Ts)
    choked = M >= 1
    if choked:
        vs,ts = thermo.sonic(s['T04_K'],s['FAR_ratio'],s['R_gas_J_kgK'])
        ps = thermo.pressure(ts,s['T04_K'],s['P04_Pa'],s['FAR_ratio'],s['R_gas_J_kgK'])
        A_throat = mdot_hot/(ps/(s['R_gas_J_kgK']*ts)*vs)
    else:
        A_throat = mdot_hot/(Ps/(s['R_gas_J_kgK']*Ts)*speed)

    # -- vane count from Zweifel --------------------------------------------
    # Zweifel Z ~ 2*(s/c)*cos^2(a2)*(tan(a1)+tan(a2)); with axial inlet a1 = 0:
    #     s/c = Z / (2*cos^2(a2)*tan(a2))
    a2 = math.radians(alpha2)
    s_over_c = s["zweifel_ratio"] / (2.0 * math.cos(a2) ** 2 * math.tan(a2))
    # annulus height at the NGV, taken as the rotor mean-line annulus
    h_ngv = A_throat / (math.pi * s["D_turb_mean_m"] * math.cos(a2))
    chord = h_ngv / s["aspect_ratio_ngv_ratio"]
    pitch = s_over_c * chord
    n_vanes = max(5, int(round(math.pi * s["D_turb_mean_m"] / pitch)))

    # keep vane and blade counts from sharing a common factor, which would put
    # every rotor blade in phase with a vane wake at once
    while math.gcd(n_vanes, int(s['n_blades_turb_count'])) != 1:
        n_vanes += 1

    return {
        "M_ngv_exit_ratio": M, "P_ngv_exit_Pa": Ps, "T_ngv_exit_K": Ts,
        "A_throat_ngv_m2": A_throat,
        "n_vanes_ngv_count": float(n_vanes),
        "alpha_ngv_exit_deg": alpha2,
        "ngv_choked_flag": 1.0 if choked else 0.0,
    }
