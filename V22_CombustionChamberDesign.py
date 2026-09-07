"""
V22 -- standalone entry point for the patched combustor.

Drop-in replacement for V21_CombustionChamberDesign.py. Same class name, same
run() interface, same self.res keys, so RPM_Sweep_OffDesign.py works against it
unchanged -- just change its import line from V21 to V22.

The physics lives in core/combustor.py so that the repo pipeline and this
standalone script share one copy. There is no second implementation to drift.

    python V22_CombustionChamberDesign.py            # KJ66 preset
    python V22_CombustionChamberDesign.py 6inch      # 6-inch preset

Current corrections and limitations are documented in docs/model-review.md.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.combustor import MicroJetCombustor, CombustorError, PATCH_NOTES  # noqa: E402,F401

kj66_inputs = {
    'casing_od_inch':        4.33,
    'shaft_tunnel_od_inch':  1.18,
    'wall_thickness_mm':     0.50,
    'pressure_ratio':        2.20,
    'compressor_efficiency': 0.74,
    'mass_flow_air_kg_s':    0.23,
    'target_tit_k':         1123.0,
    'liner_material':       '304SS',
    # Fixed geometry is rated; historical velocity matching is not validation.
    'tau_min_s': 0.0014,
}

user_inputs_6in = {
    'casing_od_inch':        6.00,
    'shaft_tunnel_od_inch':  2.00,
    'wall_thickness_mm':     1.50,
    'pressure_ratio':        2.50,
    'compressor_efficiency': 0.90,
    'mass_flow_air_kg_s':    0.60,
    'target_tit_k':         1000.0,
    'liner_material':       '316SS',
}


def print_report(res, inputs):
    W = 72
    def hdr(t):
        print(f"\n{'-'*W}\n  {t}\n{'-'*W}")
    def row(label, value, unit="", note=""):
        line = f"  {label:<34}{value:>14}  {unit}"
        if note:
            line += f"   [{note}]"
        print(line)

    print("\n" + "=" * W)
    print("   REVERSE-FLOW ANNULAR MICRO-JET COMBUSTOR  --  V22 (patched)")
    print("   PRELIMINARY - NOT FOR MANUFACTURE; see docs/model-review.md")
    print("=" * W)

    hdr("INLET")
    row("pressure ratio", f"{inputs['pressure_ratio']:.2f}")
    row("P2", f"{res['P2_Pa']/1000:.2f}", "kPa")
    row("T2", f"{res['T2_K']:.1f}", "K")
    row("air mass flow", f"{res['mdot_air']*1000:.1f}", "g/s")

    hdr("FUEL  (PATCH P1: real enthalpy balance, fuel mass in products)")
    row("fuel flow", f"{res['mdot_fuel']*1000:.3f}", "g/s")
    row("fuel-air ratio", f"{res['FAR']:.5f}")
    row("overall phi", f"{res['overall_phi']:.4f}")
    row("combustion efficiency", f"{res['eta_comb_converged']:.4f}", "", "assumed input, not CLP prediction")
    row("TIT round-trip error", f"{res['TIT_roundtrip_err_K']:.2e}", "K", "must be ~0")

    hdr("SIZE  (PATCH P14: intrinsic, from Lefebvre Sec. 4.3 -- not fill-the-casing)")
    row("reference area A_ref", f"{res['A_ref_m2']*1e6:.0f}", "mm2")
    row("reference velocity", f"{res['V_ref_m_s']:.1f}", "m/s")
    row("casing OD REQUIRED", f"{res['casing_od_required_mm']:.1f}", "mm")
    row("casing OD given", f"{res['casing_od_mm']:.1f}", "mm")
    row("radial fit margin", f"{res['casing_fit_margin_mm']:.1f}", "mm/side")

    hdr("GEOMETRY")
    row("outer liner OD (hot)", f"{res['outer_liner_od_hot_mm']:.2f}", "mm")
    row("outer liner OD (COLD BUILD)", f"{res['outer_liner_od_cold_mm']:.2f}", "mm",
        "PATCH P2: diameter, not radius")
    row("outer liner ID (cold)", f"{res['outer_liner_id_cold_mm']:.2f}", "mm")
    row("inner liner OD (COLD BUILD)", f"{res['inner_liner_od_cold_mm']:.2f}", "mm")
    row("inner liner ID (cold)", f"{res['inner_liner_id_cold_mm']:.2f}", "mm")
    row("combustion annulus gap", f"{res['combustion_gap_mm']:.2f}", "mm")
    row("mean combustion diameter", f"{res['D_mean_comb_mm']:.2f}", "mm")
    row("chamber length (hot)", f"{res['chamber_length_mm']:.2f}", "mm",
        f"L/D {res['chamber_L_over_D']:.2f}, driven by {res['length_driver']}")
    row("assumed liner metal temperature", f"{res['liner_wall_temp_K']:.0f}", "K")

    hdr("ANNULI - RATED FROM FROZEN GEOMETRY")
    row("outer annulus velocity", f"{res['v_outer_annulus']:.1f}", "m/s")
    row("inner annulus velocity", f"{res['v_inner_converged_m_s']:.1f}", "m/s", "continuity on actual geometry")
    row("path dP outer / inner", f"{res['dP_outer_path_Pa']:.0f} / {res['dP_inner_path_Pa']:.0f}", "Pa")
    row("outer branch mass residual", f"{res['outer_air_balance_error_kg_s']:.2e}", "kg/s")
    row("inner branch mass residual", f"{res['inner_air_balance_error_kg_s']:.2e}", "kg/s")

    hdr("AIR BUDGET")
    for lbl, k in [("film cooling", 'm_film_cooling'), ("primary", 'split_primary'),
                   ("secondary", 'split_secondary'), ("dilution", 'split_dilution')]:
        row(lbl, f"{res[k]*1000:.1f}", "g/s", f"{res[k]/res['mdot_air']*100:.1f}%")
    row("primary zone phi", f"{res['phi_primary_actual']:.2f}", "",
        "PATCH P11: this is an INPUT echoed back")

    hdr("HOLES - HOT MODEL DIMENSIONS, LOCAL PRESSURE BUDGET")
    print(f"  {'zone':<12}{'outer qty':>10}{'outer dia':>12}{'inner qty':>10}{'inner dia':>12}")
    for z, q, d, qi, di in [("primary", 'pri_out_qty', 'pri_out_mm', 'pri_in_qty', 'pri_in_mm'),
                            ("secondary", 'sec_out_qty', 'sec_out_mm', 'sec_in_qty', 'sec_in_mm'),
                            ("dilution", 'dil_out_qty', 'dil_out_mm', 'dil_in_qty', 'dil_in_mm')]:
        print(f"  {z:<12}{res[q]:>10d}{res[d]:>11.2f}mm{res[qi]:>10d}{res[di]:>11.2f}mm")
    row("local hole head outer / inner", f"{res['dP_outer_holes_Pa']:.0f} / {res['dP_inner_holes_Pa']:.0f}", "Pa")
    row("hole coefficient K", f"{res['hole_K_coefficient']:.1f}", "",
        "Lefebvre: >=6" if res['hole_K_ok'] else "BELOW Lefebvre minimum of 6")

    hdr("VAPORIZERS")
    row("count", f"{res['vap_n']}", "", f"n_raw {res['vap_n_raw']:.2f}")
    row("tube OD / ID", f"{res['vap_od_mm']:.2f} / {res['vap_id_mm']:.2f}", "mm")
    row("crimp orifice", f"{res['vap_crimp_dia_mm']:.2f}", "mm")
    row("scoop inlet", f"{res['vap_scoop_dia_mm']:.2f}", "mm")
    row("fuel per tube", f"{res['vap_m_fuel_per_tube']:.3f}", "g/s")

    hdr("CHECKS")
    row("residence time", f"{res['tau_comb_ms']:.2f}", "ms",
        f"target {res['tau_target_ms']:.2f} -- PATCH P3")
    row("combustion loading CLP", f"{res['CLP']:.2f}")
    row("J primary", f"{res['stab_J_primary']:.1f}", "", "band 5-80")
    row("dilution penetration", f"{res['dil_pen_norm_outer']:.3f}", "x H",
        f"single-jet form gave {res['dil_pen_norm_outer_singlejet']:.3f} -- PATCH P6")
    row("liner hoop stress", f"{max(res['sigma_hoop_outer_MPa'], res['sigma_hoop_inner_MPa']):.1f}", "MPa")

    hdr("DOME HEAT FLUX  --  LOW CONFIDENCE, PATCH P7")
    row("Lefebvre Sec. 8.5 (reported)", f"{res['stab_q_conv_lefebvre_kW_m2']:.0f}", "kW/m2")
    row("Martin 1977 impingement", f"{res['stab_q_conv_martin_kW_m2']:.0f}", "kW/m2")
    row("V21 original (flat plate)", f"{res['stab_q_conv_v21_original_kW_m2']:.0f}", "kW/m2")
    row("radiation", f"{res['stab_q_rad_kW_m2']:.0f}", "kW/m2")
    row("TOTAL (Lefebvre + rad)", f"{res['stab_q_dome_kW_m2']:.0f}", "kW/m2")
    print(f"\n  Three published methods disagree by ~{res['stab_q_conv_martin_kW_m2']/res['stab_q_conv_lefebvre_kW_m2']:.0f}x")
    print("  on this geometry. Do not quote one without saying which. See docs/model-review.md.")

    print("\n  Single sizing pass. Pressure loss, stability, thermal and buckling evidence remain open.\n")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "kj66"
    inputs = user_inputs_6in if which.lower() in ("6in", "6inch") else kj66_inputs
    print(f"\n  preset: {'6-inch' if inputs is user_inputs_6in else 'KJ66'}")
    try:
        print_report(MicroJetCombustor(inputs).run(), inputs)
    except CombustorError as e:
        print(f"\n  COMBUSTOR INFEASIBLE\n  {e}\n")
        sys.exit(1)
