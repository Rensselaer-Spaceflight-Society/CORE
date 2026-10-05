"""
M11 -- Radial vaned diffuser: vaneless space, throat, channel and exit state.

Replaces the earlier bare diameter/velocity scaling. The impeller exit state
from M10 is carried through a free-vortex vaneless space to the vane leading
edge; the throat is sized for a chosen Mach number and compared with the
opening the leading-edge pitch can provide; a mean-line channel estimate takes
the flow to the exit diameter. Vane curves remain unresolved. See core/diffuser.py.

Loss accounting: the compressor map/efficiency already covers the wheel plus a
diffuser up to the stage exit plane, so this module subtracts NO total pressure.
It publishes the exit velocity and an estimated 90-degree turn/deswirl loss for
comparison with the pressure-ledger allowance (duct loss in the matching model).

D3_m keeps its legacy meaning: diffuser OUTER (exit) diameter, read by M34.
"""

from core.module import module
from core import diffuser


@module(
    tier=2,
    title="Radial vaned diffuser: leading edge, throat, channel, exit",
    owner="TURBO-2", second="TURBO-1",
    status="draft",
    reads=[
        "D2_m", "b2_m", "alpha2_deg", "Cm2_m_s", "Ctheta2_m_s",
        "mdot_kg_s", "T03_K", "P03_Pa", "R_gas_J_kgK",
        "diff_radius_ratio",
        "diff_vaneless_ratio", "diff_vanes_design_count", "diff_width_ratio",
        "diff_throat_mach_ratio", "diff_exit_turning_deg", "diff_cp_assumed_ratio", "diff_turn_K_ratio",
        "diff_exit_width_growth_ratio",
    ],
    writes=["D3_m", "n_vanes_diff_count", "A_throat_diff_m2", "C3_m_s",
            "D_diff_le_m", "b_diff_m", "alpha_diff_le_deg", "diff_throat_width_m",
            "diff_throat_open_ratio", "diff_area_ratio", "diff_divergence_deg",
            "diff_exit_mach_ratio", "diff_turn_loss_frac"],
    notes="Preliminary channel-diffuser geometry; recovery coefficient and turn loss are assumptions "
          "pending team CFD/rig data. No separate diffuser loss is subtracted (map includes a diffuser).",
)
def m11_diffuser(s):
    d = diffuser.design(
        s["mdot_kg_s"], s["T03_K"], s["P03_Pa"], s["D2_m"], s["b2_m"], s["Cm2_m_s"], s["Ctheta2_m_s"],
        s["diff_vaneless_ratio"], s["D2_m"] * s["diff_radius_ratio"], s["diff_vanes_design_count"],
        s["diff_width_ratio"], s["diff_throat_mach_ratio"], s["diff_exit_turning_deg"],
        s["diff_cp_assumed_ratio"], s["diff_turn_K_ratio"], s["R_gas_J_kgK"], s["diff_exit_width_growth_ratio"])
    return {
        "D3_m": d["D_exit_m"],
        "n_vanes_diff_count": float(d["n_vanes"]),
        "A_throat_diff_m2": d["A_throat_m2"],
        "C3_m_s": d["C_exit_m_s"],
        "D_diff_le_m": d["D_le_m"],
        "b_diff_m": d["b_m"],
        "alpha_diff_le_deg": d["alpha_le_deg"],
        "diff_throat_width_m": d["throat_width_m"],
        "diff_throat_open_ratio": d["throat_open_ratio"],
        "diff_area_ratio": d["area_ratio"],
        "diff_divergence_deg": d["divergence_2theta_deg"],
        "diff_exit_mach_ratio": d["M_exit"],
        "diff_turn_loss_frac": d["turn_loss_frac"],
    }
