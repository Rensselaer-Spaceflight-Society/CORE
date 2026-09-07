"""M20: one combustor sizing pass from the shared cycle.

Diagnostics are published from this same geometry for M24 to convert/check.
Efficiency is an explicit cycle input; CLP does not determine it.
"""

from core.module import module
from core.combustor import MicroJetCombustor, CombustorError


@module(
    tier=3,
    title="Combustor: liner, zones, air splits, holes, vaporizers",
    owner="CSYS-1", second="CSYS-2",
    status="draft",
    reads=[
        # from the cycle -- the combustor no longer computes its own
        # thermodynamics or fuel flow, which is what removes the risk of it
        # disagreeing with the rest of the engine about the gas
        "mdot_kg_s", "T03_K", "P03_Pa", "T04_K", "FAR_ratio", "mdot_fuel_kg_s",
        "PR_c_ratio", "eta_c_isen", "LHV_fuel_J_kg", "eta_b_frac", "R_gas_J_kgK",
        # geometry envelope
        "D_casing_out_m", "D_shaft_tunnel_m", "casing_wall_m",
        # design choices
        "phi_pz_ratio", "phi_sz_ratio", "film_cool_frac", "vap_air_frac",
        "v_annulus_outer_m_s", "vap_pitch_m", "tau_min_s", "L_D_min_ratio",
        "L_D_max_ratio", "dP34_frac", "Cd_hole_ratio", "f_outer_feed_frac",
        "liner_wall_temp_frac", "alpha_liner_per_K", "liner_area_frac", "K_annular_ratio",
    ],
    writes=[
        "d_holes_pri_out_cold_m",
        "d_holes_pri_in_cold_m",
        "d_holes_sec_out_cold_m",
        "d_holes_sec_in_cold_m",
        "d_holes_dil_out_cold_m",
        "d_holes_dil_in_cold_m",
        "L_pz_cold_m",
        "L_sz_cold_m",
        "L_dz_cold_m",
        "d_film_outer_cold_m",
        "n_film_outer_per_row_count",
        "d_film_inner_cold_m",
        "n_film_inner_per_row_count",
        "n_film_rows_count",

        "comb_CLP_ratio",
        "comb_tau_s",
        "comb_q_dome_W_m2",
        "comb_q_spread_W_m2",
        "comb_J_primary_ratio",
        "comb_dil_pen_ratio",
        "comb_sigma_hoop_Pa",
        "comb_hole_K_ratio",
        "D_outer_liner_id_cold_m",
        "D_inner_liner_id_cold_m",
        "L_liner_cold_m",
        "liner_thermal_scale_ratio",
        "comb_outer_mass_error_kg_s",
        "comb_inner_mass_error_kg_s",
        "vap_path_loss_Pa",
        "vap_air_budget_Pa",

        "A_comb_m2", "D_liner_out_m", "D_liner_in_m", "D_mean_comb_m",
        "comb_gap_m", "L_liner_m", "L_pz_m", "L_sz_m", "L_dz_m",
        "air_split_pz_frac", "air_split_sz_frac", "air_split_dz_frac",
        "air_split_film_frac",
        "n_vaporizers_count", "d_vap_od_m", "d_vap_id_m", "d_vap_crimp_m",
        "d_vap_scoop_m",
        "n_holes_pri_count", "d_holes_pri_out_m", "d_holes_pri_in_m",
        "n_holes_sec_count", "d_holes_sec_out_m", "d_holes_sec_in_m",
        "n_holes_dil_count", "d_holes_dil_out_m", "d_holes_dil_in_m",
        "v_annulus_inner_m_s", "D_liner_out_cold_m", "D_liner_in_cold_m",
        "eta_comb_predicted_frac", "T_liner_wall_K", "D_casing_req_m",
        "A_ref_m2", "V_ref_m_s", "casing_fit_margin_m",
    ],
    notes="Preliminary sizing; pressure loss, thermal and stability correlations need validation.",
)
def m20_combustor(s):
    # The combustor library still takes casing dimensions in inches because
    # that is how its geometry checks were written and validated. Convert here
    # rather than in the physics, so the state stays strictly SI.
    inputs = {
        'casing_od_inch':        s["D_casing_out_m"] / 0.0254,
        'shaft_tunnel_od_inch':  s["D_shaft_tunnel_m"] / 0.0254,
        'wall_thickness_mm':     s["casing_wall_m"] * 1000.0,
        'pressure_ratio':        s["PR_c_ratio"],
        'compressor_efficiency': s["eta_c_isen"],
        'mass_flow_air_kg_s':    s["mdot_kg_s"],
        'target_tit_k':          s["T04_K"],
        'gas_constant_J_kgK': s['R_gas_J_kgK'],
        'inlet_total_pressure_Pa': s['P03_Pa'],
        'inlet_total_temperature_K': s['T03_K'],
        'fuel_air_ratio': s['FAR_ratio'],
        'mass_flow_fuel_kg_s': s['mdot_fuel_kg_s'],
        'fuel_LHV_J_kg': s['LHV_fuel_J_kg'],
        'combustion_efficiency': s['eta_b_frac'],
        'liner_material':        '316SS',
        'tau_min_s':             s["tau_min_s"],
        'L_D_min':               s["L_D_min_ratio"],
        'L_D_max':               s["L_D_max_ratio"],
    }

    m = MicroJetCombustor(inputs)
    m.DESIGN_PARAMS.update({
        'phi_primary_target':             s["phi_pz_ratio"],
        'phi_secondary_target':           s["phi_sz_ratio"],
        'film_cooling_fraction':          s["film_cool_frac"],
        'primary_air_vaporizer_fraction': s["vap_air_frac"],
        'target_annulus_vel':             s["v_annulus_outer_m_s"],
        'vap_pitch_mm':                   s["vap_pitch_m"] * 1000.0,
        'target_pressure_drop':           s["dP34_frac"],
        'discharge_coeff_hole':           s["Cd_hole_ratio"],
        'f_outer_feed':                   s["f_outer_feed_frac"],
        'liner_wall_temp_frac':           s["liner_wall_temp_frac"],
        'liner_area_frac':                s["liner_area_frac"],
        'K_annular_ratio':                s["K_annular_ratio"],
    })
    m.MATERIALS['316SS']['alpha'] = s["alpha_liner_per_K"]

    try:
        r = m.run()
    except CombustorError as e:
        raise CombustorError(
            f"combustor sizing failed at the current design point: {e}\n"
            f"  mdot = {s['mdot_kg_s']:.3f} kg/s, casing OD = {s['D_casing_out_m']*1000:.0f} mm, "
            f"T04 = {s['T04_K']:.0f} K.\n"
            f"  The combustor is usually the first thing to become infeasible when the "
            f"engine is scaled -- it needs annulus area that the casing may not have."
        ) from None

    return {
        "d_holes_pri_out_cold_m": r['pri_out_mm']/1000/r['thermal_scale_ratio'],
        "d_holes_pri_in_cold_m": r['pri_in_mm']/1000/r['thermal_scale_ratio'],
        "d_holes_sec_out_cold_m": r['sec_out_mm']/1000/r['thermal_scale_ratio'],
        "d_holes_sec_in_cold_m": r['sec_in_mm']/1000/r['thermal_scale_ratio'],
        "d_holes_dil_out_cold_m": r['dil_out_mm']/1000/r['thermal_scale_ratio'],
        "d_holes_dil_in_cold_m": r['dil_in_mm']/1000/r['thermal_scale_ratio'],
        "L_pz_cold_m": r['L_primary_mm']/1000/r['thermal_scale_ratio'],
        "L_sz_cold_m": r['L_secondary_mm']/1000/r['thermal_scale_ratio'],
        "L_dz_cold_m": r['L_dilution_mm']/1000/r['thermal_scale_ratio'],
        "d_film_outer_cold_m": r['film_hole_dia_outer_mm']/1000/r['thermal_scale_ratio'],
        "n_film_outer_per_row_count": r['film_holes_per_row_outer'],
        "d_film_inner_cold_m": r['film_hole_dia_inner_mm']/1000/r['thermal_scale_ratio'],
        "n_film_inner_per_row_count": r['film_holes_per_row_inner'],
        "n_film_rows_count": r['film_n_rows'],

        "comb_CLP_ratio": r['CLP'],
        "comb_tau_s": r['tau_comb_ms']/1000,
        "comb_q_dome_W_m2": r['stab_q_dome_kW_m2']*1000,
        "comb_q_spread_W_m2": r['stab_q_dome_spread_kW_m2']*1000,
        "comb_J_primary_ratio": r['stab_J_primary'],
        "comb_dil_pen_ratio": max(r['dil_pen_norm_outer'],r['dil_pen_norm_inner']),
        "comb_sigma_hoop_Pa": max(r['sigma_hoop_outer_MPa'],r['sigma_hoop_inner_MPa'])*1e6,
        "comb_hole_K_ratio": r['hole_K_coefficient'],
        "D_outer_liner_id_cold_m": r['outer_liner_id_cold_mm']/1000,
        "D_inner_liner_id_cold_m": r['inner_liner_id_cold_mm']/1000,
        "L_liner_cold_m": r['chamber_length_cold_mm']/1000,
        "liner_thermal_scale_ratio": r['thermal_scale_ratio'],
        "comb_outer_mass_error_kg_s": r['outer_air_balance_error_kg_s'],
        "comb_inner_mass_error_kg_s": r['inner_air_balance_error_kg_s'],
        "vap_path_loss_Pa": r['vap_path_loss_Pa'],
        "vap_air_budget_Pa": r['vap_air_pressure_budget_Pa'],

        "A_comb_m2":          r['combustion_annulus_A'],
        "D_liner_out_m":      r['outer_liner_od_mm'] / 1000.0,
        "D_liner_in_m":       r['inner_liner_id_mm'] / 1000.0,
        "D_mean_comb_m":      r['D_mean_comb_mm'] / 1000.0,
        "comb_gap_m":         r['combustion_gap_mm'] / 1000.0,
        "L_liner_m":          r['chamber_length_mm'] / 1000.0,
        "L_pz_m":             r['L_primary_mm'] / 1000.0,
        "L_sz_m":             r['L_secondary_mm'] / 1000.0,
        "L_dz_m":             r['L_dilution_mm'] / 1000.0,
        "air_split_pz_frac":  r['split_primary'] / r['mdot_air'],
        "air_split_sz_frac":  r['split_secondary'] / r['mdot_air'],
        "air_split_dz_frac":  r['split_dilution'] / r['mdot_air'],
        "air_split_film_frac": r['m_film_cooling'] / r['mdot_air'],
        "n_vaporizers_count": float(r['vap_n']),
        "d_vap_od_m":         r['vap_od_mm'] / 1000.0,
        "d_vap_id_m":         r['vap_id_mm'] / 1000.0,
        "d_vap_crimp_m":      r['vap_crimp_dia_mm'] / 1000.0,
        "d_vap_scoop_m":      r['vap_scoop_dia_mm'] / 1000.0,
        "n_holes_pri_count":  float(r['pri_out_qty']),
        "d_holes_pri_out_m":  r['pri_out_mm'] / 1000.0,
        "d_holes_pri_in_m":   r['pri_in_mm'] / 1000.0,
        "n_holes_sec_count":  float(r['sec_out_qty']),
        "d_holes_sec_out_m":  r['sec_out_mm'] / 1000.0,
        "d_holes_sec_in_m":   r['sec_in_mm'] / 1000.0,
        "n_holes_dil_count":  float(r['dil_out_qty']),
        "d_holes_dil_out_m":  r['dil_out_mm'] / 1000.0,
        "d_holes_dil_in_m":   r['dil_in_mm'] / 1000.0,
        "v_annulus_inner_m_s": r['v_inner_converged_m_s'],
        "D_liner_out_cold_m": r['outer_liner_od_cold_mm'] / 1000.0,
        "D_liner_in_cold_m":  r['inner_liner_od_cold_mm'] / 1000.0,
        "eta_comb_predicted_frac": r['eta_comb_converged'],
        "T_liner_wall_K":     r['liner_wall_temp_K'],
        # PATCH P14: the combustor now has an intrinsic size and publishes the
        # casing it needs, instead of expanding to fill whatever it is given.
        "D_casing_req_m":     r['casing_od_required_mm'] / 1000.0,
        "A_ref_m2":           r['A_ref_m2'],
        "V_ref_m_s":          r['V_ref_m_s'],
        "casing_fit_margin_m": r['casing_fit_margin_mm'] / 1000.0,
    }
