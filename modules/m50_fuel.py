"""
M50 -- Fuel delivery.

The only thing upstream of this module is the fuel flow the cycle demands and
the pressure the combustor sits at. Everything else is plumbing: pick a line
velocity, size the bore, add up the losses, and see what the pump has to make.

This is a good first module for a new member. It is real work, the physics is
first-year fluids, and it produces a number somebody has to go and buy a pump
against.
"""

import math
from core.module import module


@module(
    tier=6,
    title="Fuel flow, line sizing, pump pressure",
    owner="CSYS-3", second="CSYS-2",
    status="draft",
    reads=[
        "mdot_fuel_kg_s", "P03_Pa", "rho_fuel_kg_m3", "mu_fuel_Pa_s",
        "v_fuel_line_m_s", "L_fuel_line_m", "n_vaporizers_count",
        "dP_injector_Pa", "P00_Pa", "fuel_minor_K_ratio", "dP_fuel_filter_Pa",
    ],
    writes=["Vdot_fuel_m3_s", "d_fuel_line_m", "P_pump_req_Pa", "dP_pump_req_Pa", "dP_fuel_line_Pa"],
)
def m50_fuel(s):
    Vdot = s["mdot_fuel_kg_s"] / s["rho_fuel_kg_m3"]

    # line bore for the target velocity
    A = Vdot / s["v_fuel_line_m_s"]
    d = math.sqrt(4.0 * A / math.pi)

    # Darcy-Weisbach with a Blasius friction factor
    Re = s["rho_fuel_kg_m3"] * s["v_fuel_line_m_s"] * d / s["mu_fuel_Pa_s"]
    f = 64.0 / Re if Re < 2300 else 0.3164 * Re ** -0.25
    dP_line = f * (s["L_fuel_line_m"] / d) * 0.5 * s["rho_fuel_kg_m3"] * s["v_fuel_line_m_s"] ** 2

    # the pump has to beat combustor pressure, the injector drop and the line
    P_pump = s["P03_Pa"] + s["dP_injector_Pa"] + dP_line + s["dP_fuel_filter_Pa"] + s["fuel_minor_K_ratio"]*0.5*s["rho_fuel_kg_m3"]*s["v_fuel_line_m_s"]**2

    return {
        "dP_pump_req_Pa": P_pump-s["P00_Pa"],
        "dP_fuel_line_Pa": dP_line,
        "Vdot_fuel_m3_s": Vdot,
        "d_fuel_line_m": d,
        "P_pump_req_Pa": P_pump,
    }
