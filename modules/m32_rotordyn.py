"""
M32 -- Rotordynamics: first bending critical.

Two overhung masses on a shaft in two bearings. The shaft's own bending
stiffness sits in series with the bearing stiffness, and on a small machine
like this the bearings are usually the softer element -- which means the first
critical is set more by your bearing mounts than by your shaft diameter. That
is a genuinely counterintuitive result and it changes what you would go and fix.

This is a first-pass lumped model. It tells you whether you are in trouble, not
whether you are safe. The real answer needs an FEM with gyroscopic terms and a
proper Campbell diagram, which is STRUCT-2's Gate D deliverable.

Gyroscopic effects split each mode into forward and backward whirl and make the
criticals speed-dependent -- ignored here, which is why the margin requirement
in limits.yaml is 20% rather than something tighter.
"""

import math
from core.module import module


@module(
    tier=4,
    title="First bending critical and separation margin",
    owner="STRUCT-2", second="STRUCT-1",
    status="stub",
    reads=[
        "d_shaft_m", "L_bear_span_m", "m_turb_kg", "m_imp_kg", "m_shaft_kg",
        "k_bearing_N_m", "E_shaft_Pa", "N_rpm", "N_operating_min_rpm", "N_operating_max_rpm",
    ],
    writes=["N_crit1_rpm", "N_crit_margin_frac", "critical_crossed_flag"],
    notes="STUB: undamped lumped model, no gyroscopics. Replace with an NX or "
          "Ansys rotordynamics model before Gate D.",
)
def m32_rotordyn(s):
    d = s["d_shaft_m"]
    L = s["L_bear_span_m"]
    I = math.pi * d ** 4 / 64.0

    # simply-supported shaft, central load: k = 48EI/L^3
    k_shaft = 48.0 * s["E_shaft_Pa"] * I / L ** 3

    # two bearings in parallel, then in series with the shaft
    k_bear = 2.0 * s["k_bearing_N_m"]
    k_eff = 1.0 / (1.0 / k_shaft + 1.0 / k_bear)

    # effective mass: both wheels plus half the shaft
    m_eff = s["m_turb_kg"] + s["m_imp_kg"] + 0.5 * s["m_shaft_kg"]

    omega_n = math.sqrt(k_eff / m_eff)
    N_crit = omega_n * 60.0 / (2.0 * math.pi)

    low,high = s['N_operating_min_rpm'],s['N_operating_max_rpm']
    if not 0 < low <= s['N_rpm'] <= high:
        raise ValueError('operating speed interval must contain the design speed')
    margin = max(low-N_crit,N_crit-high,0)/high
    crossed = 0 < N_crit <= high

    return {"N_crit1_rpm": N_crit, "N_crit_margin_frac": margin, "critical_crossed_flag": crossed}
