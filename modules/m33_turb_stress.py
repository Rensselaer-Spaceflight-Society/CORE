"""M33: centrifugal blade stress screening from M13's shared blade geometry.

This does not compute disc stress, creep/fatigue life or actual burst speed.
The legacy burst_margin_ratio name is retained as an explicitly deprecated alias.
"""

import math
from core.module import module
from core import gas


@module(
    tier=4,
    title="Blade centrifugal stress screening and AN^2",
    owner="STRUCT-2", second="TURBO-4",
    status="draft",
    reads=[
        "A_annulus_turb_m2", "N_rpm", "rho_turb_kg_m3",
        "D_turb_tip_m", "D_turb_hub_m", "h_blade_m", "n_blades_turb_count",
        "m_blade_kg", "r_blade_cg_m", "A_blade_root_m2", "sigma_allow_turb_Pa",
    ],
    writes=["AN2_m2_rpm2", "sigma_root_Pa", "burst_margin_ratio", "F_blade_root_N", "blade_stress_speed_margin_ratio"],
)
def m33_turb_stress(s):
    omega = gas.rpm_to_rad_s(s["N_rpm"])
    A = s["A_annulus_turb_m2"]

    # -- AN^2, in the conventional m^2 * rpm^2 units ------------------------
    AN2 = A * s["N_rpm"] ** 2

    F_root = s['m_blade_kg']*omega**2*s['r_blade_cg_m']
    sigma = F_root/s['A_blade_root_m2']

    # -- burst margin --------------------------------------------------------
    # stress scales with omega^2, so the speed at which stress reaches the
    # allowable is sqrt(sigma_allow/sigma_design) times design speed
    margin = math.sqrt(s["sigma_allow_turb_Pa"] / max(sigma, 1.0))

    return {
        "AN2_m2_rpm2": AN2,
        "sigma_root_Pa": sigma,
        "burst_margin_ratio": margin,
        "blade_stress_speed_margin_ratio": margin,
        "F_blade_root_N": F_root,
    }
