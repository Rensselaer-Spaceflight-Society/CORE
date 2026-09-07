"""
M31 -- Bearings: DN, loads, stiffness.

DN -- bore in millimetres times rpm -- is the number that decides whether a
bearing survives. Grease-packed steel tops out around 0.5e6. Oil-misted hybrid
ceramic angular contact will do 1.5-2e6 with proper preload. The KJ66 runs 8 mm
bore at 117,000 rpm, so DN = 0.94e6, on plain steel ISO 608 bearings fed with
oil premixed into the fuel.

Net axial thrust is the difference between the impeller's forward pull and the
turbine's aft push. It is small, it changes sign across the operating range, and
that sign change is exactly what wrecks unloaded angular contact bearings --
which is why the preload spring exists.
"""

import math
from core.module import module


@module(
    tier=4,
    title="Bearing DN, axial load, stiffness",
    owner="STRUCT-1", second="STRUCT-3",
    status="draft",
    reads=[
        "d_bearing_bore_m", "N_rpm", "P03_Pa", "P02_Pa", "P04_Pa", "P05_Pa",
        "D1s_m", "D1h_m", "D_turb_hub_m", "m_turb_kg", "m_imp_kg",
        "bearing_stiffness_N_m",
    ],
    writes=["DN_mm_rpm", "F_axial_N", "k_bearing_N_m"],
)
def m31_bearings(s):
    DN = (s["d_bearing_bore_m"] * 1000.0) * s["N_rpm"]

    # -- axial thrust --------------------------------------------------------
    # impeller: pressure rise acting over the eye annulus, pulling forward
    A_eye = math.pi / 4.0 * (s["D1s_m"] ** 2 - s["D1h_m"] ** 2)
    F_imp = (s["P03_Pa"] - s["P02_Pa"]) * A_eye

    # turbine: pressure drop across the disc, pushing aft
    A_disc = math.pi / 4.0 * s["D_turb_hub_m"] ** 2
    F_turb = (s["P04_Pa"] - s["P05_Pa"]) * A_disc

    F_axial = F_imp - F_turb

    return {
        "DN_mm_rpm": DN,
        "F_axial_N": F_axial,
        "k_bearing_N_m": s["bearing_stiffness_N_m"],
    }
