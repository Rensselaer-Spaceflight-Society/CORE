"""
M34 -- Casing: the engine envelope.

Everything the casing produces is what the outside world sees -- outer
diameter, length, dry mass, centre of gravity. The stand, the mounts, the
nacelle and the shipping crate all wait on this module.

THE LOOP: this module reads the combustor's liner outer diameter, and the
combustor reads this module's casing outer diameter to know how much room it
has. That is a real circular dependency, not a modelling mistake -- in a
reverse-flow engine the liner and the casing genuinely size each other. The
solver detects the cycle and iterates the pair to a fixed point. You will see
it reported as a coupled block when you run.

Breaking a loop like this by hand -- "just assume the casing is 150 mm" -- is
also legitimate, and faster. But then somebody has to remember to check the
assumption, and on a twenty-person team nobody does.
"""

import math
from core.module import module


@module(
    tier=4,
    title="Engine envelope: OD, length, dry mass",
    owner="STRUCT-3", second="STRUCT-2",
    status="draft",
    reads=[
        "D3_m", "D_casing_req_m", "D_turb_tip_m", "L_shaft_m", "L_liner_m",
        "D8_m", "casing_wall_m", "annulus_gap_frac", "rho_casing_kg_m3",
        "m_turb_kg", "m_imp_kg", "m_shaft_kg", "accessory_mass_frac",
    ],
    writes=["D_casing_out_m", "L_engine_m", "m_engine_kg"],
)
def m34_casing(s):
    # the casing has to clear whichever is biggest: the diffuser, the liner
    # plus its cooling annulus, or the turbine tip
    # PATCH P14: read the casing the COMBUSTOR REQUIRES, not the diameter of
    # the liner it happened to produce. The old form fed back on itself -- the
    # combustor filled whatever casing it was given and the casing grew to
    # contain it, and the pair diverged without bound. The solver caught it.
    D_needed = max(
        s["D3_m"] + 2.0 * s["casing_wall_m"],
        s["D_casing_req_m"],
        s["D_turb_tip_m"] * 1.10 + 2.0 * s["casing_wall_m"],
    )
    D_out = D_needed

    # length: shaft stack plus an inlet bellmouth and an exhaust cone
    L_engine = s["L_shaft_m"] + 0.35 * D_out + 1.2 * s["D8_m"]

    # mass: a thin cylinder plus two end closures, plus the rotating parts,
    # plus a fraction for brackets, fittings and hardware
    A_shell = math.pi * D_out * L_engine
    A_ends = 2.0 * math.pi / 4.0 * D_out ** 2
    m_shell = (A_shell + A_ends) * s["casing_wall_m"] * s["rho_casing_kg_m3"]
    m_rot = s["m_turb_kg"] + s["m_imp_kg"] + s["m_shaft_kg"]
    m_total = (m_shell + m_rot) * (1.0 + s["accessory_mass_frac"])

    return {
        "D_casing_out_m": D_out,
        "L_engine_m": L_engine,
        "m_engine_kg": m_total,
    }
