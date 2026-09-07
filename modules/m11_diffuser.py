"""
M11 -- Radial vaned diffuser.

Turns the impeller's high-velocity, highly-swirled exit flow into pressure
before it reaches the combustor. The KJ66 uses an aluminium wedge-vane radial
diffuser; the same geometry family scales.

D3_m matters to more people than you would expect: it puts a hard floor under
the casing outer diameter, which is why the casing module reads it.
"""

import math
from core.module import module
from core import gas, thermo


@module(
    tier=2,
    title="Radial diffuser: exit diameter, vane count, throat",
    owner="TURBO-2", second="TURBO-1",
    status="stub",
    reads=[
        "D2_m", "b2_m", "alpha2_deg", "Cm2_m_s", "Ctheta2_m_s",
        "mdot_kg_s", "T03_K", "P03_Pa", "R_gas_J_kgK",
        "diff_radius_ratio", "diff_diffusion_ratio",
    ],
    writes=["D3_m", "n_vanes_diff_count", "A_throat_diff_m2", "C3_m_s"],
    notes="STUB: geometric scaling only, no loss model. Owner to replace with a "
          "proper channel-diffuser calculation before Gate D.",
)
def m11_diffuser(s):
    D3 = s["D2_m"] * s["diff_radius_ratio"]

    C2 = math.hypot(s["Cm2_m_s"], s["Ctheta2_m_s"])
    C3 = C2 / s["diff_diffusion_ratio"]

    Ts,Ps = thermo.static(s["T03_K"],s["P03_Pa"],C3,R=s["R_gas_J_kgK"])
    rho3 = gas.density(Ps,Ts,s["R_gas_J_kgK"])
    A_throat = s["mdot_kg_s"] / (rho3 * C3)

    # Fixed provisional vane count; blade/vane harmonic review remains required.
    n_vanes = 17.0

    return {
        "D3_m": D3,
        "n_vanes_diff_count": n_vanes,
        "A_throat_diff_m2": A_throat,
        "C3_m_s": C3,
    }
