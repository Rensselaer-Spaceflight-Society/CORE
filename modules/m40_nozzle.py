"""
M40 -- Convergent exhaust nozzle.

Sizes the exit and reports the thrust that actually comes out. F_gross_N should
land back on F_target_N -- if it does not, the cycle and the nozzle disagree
about something and the closure test in run.py will say so.

Whether the nozzle chokes matters more than it sounds. Choked, the exit static
pressure sits above ambient and there is a pressure-thrust term, and the nozzle
decouples from the back pressure entirely. Unchoked, ambient pressure reaches
back up into the turbine and the whole engine becomes altitude-sensitive. At a
pressure ratio near 3 you will be choked; the KJ66, at 1.96 overall with a
lossy combustor, is not.
"""

import math
from core.module import module
from core import gas, thermo


@module(
    tier=5,
    title="Nozzle exit area, velocity, gross thrust",
    owner="TURBO-2", second="STRUCT-3",
    status="draft",
    reads=[
        "mdot_kg_s", "FAR_ratio", "T05_K", "P05_Pa", "P00_Pa",
        "cp_hot_J_kgK", "gamma_hot_ratio", "R_gas_J_kgK", "Cv_nozzle_ratio",
    ],
    writes=["A8_m2", "D8_m", "V8_m_s", "F_gross_N", "nozzle_choked_flag"],
)
def m40_nozzle(s):
    mdot_hot = s["mdot_kg_s"] * (1.0 + s["FAR_ratio"])

    V8, T8, P8, choked = thermo.nozzle(
        s["T05_K"],s["P05_Pa"],s["P00_Pa"],s["FAR_ratio"],s["R_gas_J_kgK"],s["Cv_nozzle_ratio"])

    rho8 = gas.density(P8, T8, s["R_gas_J_kgK"])
    A8 = mdot_hot / (rho8 * V8)
    D8 = math.sqrt(4.0 * A8 / math.pi)

    F = gas.gross_thrust(mdot_hot, V8, A8, P8, s["P00_Pa"])

    return {
        "A8_m2": A8,
        "D8_m": D8,
        "V8_m_s": V8,
        "F_gross_N": F,
        "nozzle_choked_flag": 1.0 if choked else 0.0,
    }
