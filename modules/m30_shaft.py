"""
M30 -- Shaft sizing and the axial stack-up.

The shaft is the classic downstream component: it can do nothing until the
impeller and the turbine wheel have both frozen their geometry, because it
needs their diameters, their masses and the axial length of everything between
them. This is exactly why Gate B (rotating assembly envelope frozen) exists and
why it comes before Gate C.

L_shaft_m is the sum of the axial stack, and it is one of the two numbers that
set overall engine length.
"""

import math
from core.module import module
from core import gas


@module(
    tier=4,
    title="Shaft diameter, length, bearing span, torque",
    owner="STRUCT-1", second="STRUCT-2",
    status="draft",
    reads=[
        "mdot_kg_s", "w_comp_J_kg", "N_rpm", "eta_mech_frac",
        "d_bearing_bore_m", "D2_m", "b2_m", "L_liner_m", "h_blade_m",
        "tau_allow_shaft_Pa", "rho_shaft_kg_m3", "bear_span_frac",
        "D_shaft_tunnel_m",
    ],
    writes=["d_shaft_m", "L_shaft_m", "L_bear_span_m", "torque_Nm", "m_shaft_kg"],
)
def m30_shaft(s):
    omega = gas.rpm_to_rad_s(s["N_rpm"])

    # -- torque from shaft power --------------------------------------------
    power = s["mdot_kg_s"] * s["w_comp_J_kg"] / s["eta_mech_frac"]
    torque = power / omega

    # -- diameter from torsion, then floored by the bearing bore ------------
    # solid round shaft: tau = 16*T/(pi*d^3)
    d_torsion = (16.0 * torque / (math.pi * s["tau_allow_shaft_Pa"])) ** (1.0 / 3.0)
    d_shaft = max(d_torsion, s["d_bearing_bore_m"])

    # -- axial stack --------------------------------------------------------
    # impeller + diffuser + combustor + turbine + nuts and clearances
    L_imp = s["b2_m"] + 0.30 * s["D2_m"]
    L_diff = 0.10 * s["D2_m"]
    L_turb = 3.0 * s["h_blade_m"]
    L_slack = 0.06 * s["D2_m"]
    L_shaft = L_imp + L_diff + s["L_liner_m"] + L_turb + L_slack

    L_span = s["bear_span_frac"] * L_shaft

    vol = math.pi / 4.0 * d_shaft ** 2 * L_shaft
    m_shaft = vol * s["rho_shaft_kg_m3"]

    return {
        "d_shaft_m": d_shaft,
        "L_shaft_m": L_shaft,
        "L_bear_span_m": L_span,
        "torque_Nm": torque,
        "m_shaft_kg": m_shaft,
    }
