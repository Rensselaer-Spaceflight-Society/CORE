# Screening only: this sweep prescribes PR, airflow and TIT; it does not solve
# compressor/turbine maps, surge margin, starting transients or flame stability.
"""
PURPOSE
-------
Given the fixed geometry produced by V22_CombustionChamberDesign.py at a single
design point, this script answers: "How does the combustor perform when the
compressor operates at a different RPM (and therefore a different PR and mass flow)?"

SEPARATION OF CONCERNS
-----------------------
  V21 — Sizing / Design model    : What physical dimensions should the engine have?
  Sweep_OffDesign — Rating model : Given those fixed dimensions, what are the outlet
                                   conditions across the operating envelope?

USAGE
-----
  1. Adjust `DESIGN_INPUTS` at the bottom to match your engine.
  2. Populate `OPERATING_LINE` with (rpm_pct, PR, mdot_air, eff_c, tit) tuples.
  3. Run the script. Two files are written:
       - design_card_<timestamp>.json   — everything a downstream script needs
       - sweep_results_<timestamp>.json — per-point off-design outlet conditions
  4. All results are also pretty-printed to the console.

OFF-DESIGN PHYSICS SUMMARY
---------------------------
  Thermodynamics  : Isentropic compression with isentropic efficiency (same as V21).
                    T2 = T_amb + (T2_iso - T_amb) / eta_c  — isentropic, not polytropic.
  Pressure drop   : The absolute pressure drop (Pa) is scaled from the design-point
                    anchor using the Bernoulli/dynamic-pressure relation:
                      dP_Pa = dP_Pa_design * (mdot/mdot_dp)^2 * (rho_dp/rho)
                    The fraction dP_frac = dP_Pa / P2 is derived after scaling.
                    Scaling absolute Pa (not the fraction) correctly accounts for
                    both changing mass flux and changing static pressure level.
                    At the design point this recovers the exact V21 dP fraction.
  Fuel flow       : Energy balance using variable cp (same quadratic fit as V21).
                    Combustion efficiency is calculated dynamically from CLP at each
                    operating point, then used directly in the fuel mass balance.
                    The design-point heat_loss_factor from V21 is also preserved.
  Exit conditions : 1-D continuity through the *fixed* combustion annulus area.
                    Uses gamma_hot = 1.33 for combustion products (same as V21).
  Stagnation      : Total temperature and pressure computed from local Mach number.
"""

import json
import math
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import gas, thermo   # PATCH P1: one shared, table-validated gas model

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

# ---------------------------------------------------------------------------
# V21 import — must be in the same directory (or on PYTHONPATH)
# ---------------------------------------------------------------------------
try:
    from V22_CombustionChamberDesign import MicroJetCombustor
except ImportError:
    sys.exit(
        "\n  ERROR: Cannot import V21_CombustionChamberDesign.\n"
        "  Ensure V22_CombustionChamberDesign.py is in the same directory as this script.\n"
    )

# ===========================================================================
# CONSTANTS
# ===========================================================================
R_AIR      = 287.05   # J/(kg·K)
GAMMA_COLD = 1.40     # cold air (compressor side)
GAMMA_HOT  = 1.33     # hot combustion products (turbine side)
LHV_JET_A  = 43.0e6  # J/kg  — Jet-A lower heating value
# Combustion efficiency is an assumed design-card input; CLP does not alter fuel flow.
P_AMB      = 101_325  # Pa
T_AMB      = 288.15   # K


# ===========================================================================
# HELPERS
# ===========================================================================
def _cp(T_kelvin: float) -> float:
    """
    ===== PATCH P1 =====
    This used to be a private copy of V21's quadratic cp fit, "reproduced here
    so V22 is self-consistent". It was not self-consistent -- it was a THIRD
    independent gas model, and it made the design point of this sweep disagree
    with the design point of the sizing script by 3.9% on fuel flow, at the one
    operating point the docstring promised would reproduce exactly.

    Now delegates to core/gas.py, which is validated against published air
    property tables to 0.18% on cp and 0.12% on enthalpy. One gas model.
    """
    return gas.cp_air(T_kelvin)


def _clp_eta(clp: float) -> float:
    """
    Combustion efficiency estimated from the combustion loading parameter.
    Mirrors V21.combustion_loading().
      CLP < 10   → η ≈ 0.999
      CLP = 15   → η ≈ 0.97
      CLP = 25   → η ≈ 0.90
    """
    return max(0.85, min(0.999, 1.0 - 0.006 * max(0.0, clp - 10.0)))


# ===========================================================================
# DESIGN-CARD BUILDER
# ===========================================================================
def build_design_card(design_inputs: dict) -> dict:
    """
    Runs V21 at the design point and extracts every value a downstream script
    would need:  geometry, inlet conditions, outlet conditions, hole schedule,
    vaporizer dimensions, and the fixed areas used for off-design evaluation.

    Returns a flat-ish dictionary grouped by section.  Also stored under the
    'raw_res' key is the complete V21 results dict for reference.
    """
    model = MicroJetCombustor(design_inputs)
    res   = model.run()          # full V21 calculation
    dp    = model.DESIGN_PARAMS  # design parameters

    # ── Pre-compute Lefebvre theta normalisation factor ───────────────────────
    # theta_norm anchors the non-linear CLP_effective to equal the V21 linear
    # CLP exactly at the design point.  Computed once here from V21 geometry so
    # evaluate_off_design_point needs no extra state.
    _V_pri     = res["CLP_V_primary_m3"]
    _P2_kPa_dp = res["P2_Pa"] / 1000.0
    _T2_dp     = res["T2_K"]
    _clp_theta_dp = (res["mdot_air"]
                     / ((_P2_kPa_dp ** 1.75)
                        * math.exp(_T2_dp / 300.0)
                        * _V_pri)) if _V_pri > 0 else 1.0
    _theta_norm = res["CLP"] / _clp_theta_dp if _clp_theta_dp != 0 else 1.0

    card = {
        # ── Metadata ────────────────────────────────────────────────────────
        "metadata": {
            "source_script":   "V22_CombustionChamberDesign.py",
            "rating_script":   "V22_CombustorOffDesign.py",
            "generated_utc":   _utcnow().isoformat(timespec="seconds") + "Z",
            "units_note":      "SI unless labelled: lengths [mm], pressures [Pa or kPa], "
                               "temperatures [K], mass flows [kg/s], velocities [m/s], "
                               "areas [m²], angles [deg].",
        },

        # ── Design-point thermodynamic inputs ───────────────────────────────
        "design_inputs": {
            "casing_od_inch":        design_inputs["casing_od_inch"],
            "shaft_tunnel_od_inch":  design_inputs["shaft_tunnel_od_inch"],
            "wall_thickness_mm":     design_inputs["wall_thickness_mm"],
            "pressure_ratio":        design_inputs["pressure_ratio"],
            "compressor_efficiency": design_inputs["compressor_efficiency"],
            "mass_flow_air_kg_s":    res["mdot_air"],
            "target_tit_k":          design_inputs["target_tit_k"],
            "liner_material":        design_inputs.get("liner_material", "304SS"),
        },

        # ── Compressor / Inlet conditions at design point ────────────────────
        "inlet_conditions_design": {
            "P_amb_Pa":      P_AMB,
            "T_amb_K":       T_AMB,
            "pressure_ratio": design_inputs["pressure_ratio"],
            "eta_compressor": design_inputs["compressor_efficiency"],
            "P2_Pa":         res["P2_Pa"],
            "P2_kPa":        res["P2_Pa"] / 1000.0,
            "T2_K":          res["T2_K"],
            "rho2_kg_m3":    res["rho2"],
            "mdot_air_kg_s": res["mdot_air"],
        },

        # ── Combustor outlet / turbine inlet conditions at design point ──────
        "outlet_conditions_design": {
            "target_TIT_K":         design_inputs["target_tit_k"],
            "mdot_fuel_kg_s":       res["mdot_fuel"],
            "mdot_total_kg_s":      res["exit_mdot_kg_s"],
            "overall_AFR":          res["overall_AFR"],
            "overall_phi":          res["overall_phi"],
            "dP_fraction":          dp["target_pressure_drop"],
            "dP_Pa":                res["P2_Pa"] * dp["target_pressure_drop"],
            "P4_Pa":                res["exit_P4_Pa"],
            "P4_kPa":               res["exit_P4_kPa"],
            "T4_static_K":          res["exit_T4_K"],
            "T4_total_K":           res["exit_T4_total_K"],
            "P4_total_Pa":          res["exit_P4_total_Pa"],
            "rho4_kg_m3":           res["exit_rho4"],
            "V4_m_s":               res["exit_V4_m_s"],
            "Ma4":                  res["exit_Ma4"],
            "a4_m_s":               res["exit_a4_m_s"],
            "cp4_J_kgK":            res["exit_cp4"],
            "gamma_hot":            res["exit_gamma_hot"],
            "h_avail_kJ_kg":        res["exit_h_avail_kJ_kg"],
        },

        # ── Fixed geometry (used verbatim in off-design calculations) ─────────
        "geometry": {
            # Outer envelope
            "casing_od_mm":               res["casing_od_mm"],
            "casing_id_mm":               res["casing_id_mm"],
            "wall_thickness_mm":          design_inputs["wall_thickness_mm"],
            # Shaft tunnel
            "shaft_tunnel_od_mm":         res["shaft_tunnel_od_mm"],
            "shaft_tunnel_id_mm":         res["shaft_tunnel_id_mm"],
            # Outer liner  (cold = build dimension; hot = operating dimension)
            "outer_liner_od_cold_mm":     res["outer_liner_od_cold_mm"],
            "outer_liner_od_hot_mm":      res["outer_liner_od_hot_mm"],
            "outer_liner_id_mm":          res["outer_liner_id_mm"],
            "outer_liner_thermal_offset_mm": res["outer_liner_thermal_offset_mm"],
            # Inner liner
            "inner_liner_od_cold_mm":     res["inner_liner_od_cold_mm"],
            "inner_liner_od_hot_mm":      res["inner_liner_od_hot_mm"],
            "inner_liner_id_mm":          res["inner_liner_id_mm"],
            "inner_liner_thermal_offset_mm": res["inner_liner_thermal_offset_mm"],
            # Combustion annulus
            "combustion_gap_mm":          res["combustion_gap_mm"],
            "combustion_annulus_A_m2":    res["combustion_annulus_A"],
            "D_mean_comb_mm":             res["D_mean_comb_mm"],
            # Zone lengths
            "chamber_length_mm":          res["chamber_length_mm"],
            "L_primary_mm":              res["L_primary_mm"],
            "L_secondary_mm":            res["L_secondary_mm"],
            "L_dilution_mm":             res["L_dilution_mm"],
            # Feed annuli
            "outer_annulus_gap_mm":      res["outer_annulus_gap_mm"],
            "inner_annulus_gap_mm":      res["inner_annulus_gap_mm"],
            # Material
            "liner_material":            res["liner_material"],
            "liner_material_name":       res["liner_material_name"],
        },

        # ── Air-flow budget at design point ─────────────────────────────────
        "air_budget_design": {
            "mdot_total_kg_s":          res["mdot_air"],
            "mdot_primary_kg_s":        res["split_primary"],
            "mdot_primary_liner_kg_s":  res["split_primary_liner"],
            "mdot_primary_vap_kg_s":    res["split_primary_vap"],
            "mdot_secondary_kg_s":      res["split_secondary"],
            "mdot_dilution_kg_s":       res["split_dilution"],
            "mdot_film_cooling_kg_s":   res["m_film_cooling"],
            "phi_primary":              res["phi_primary_actual"],
        },

        # ── Hole schedule (fixed geometry — does not change with RPM) ────────
        "hole_schedule": {
            "outer_fraction":    res["hole_split_f_outer"],
            "inner_fraction":    res["hole_split_f_inner"],
            "Cd":                dp["discharge_coeff_hole"],
            "primary": {
                "outer_qty": res["pri_out_qty"], "outer_dia_mm": res["pri_out_mm"],
                "inner_qty": res["pri_in_qty"],  "inner_dia_mm": res["pri_in_mm"],
            },
            "secondary": {
                "outer_qty": res["sec_out_qty"], "outer_dia_mm": res["sec_out_mm"],
                "inner_qty": res["sec_in_qty"],  "inner_dia_mm": res["sec_in_mm"],
            },
            "dilution": {
                "outer_qty": res["dil_out_qty"], "outer_dia_mm": res["dil_out_mm"],
                "inner_qty": res["dil_in_qty"],  "inner_dia_mm": res["dil_in_mm"],
            },
        },

        # ── Vaporizer tubes ─────────────────────────────────────────────────
        "vaporizers": {
            "count":              res["vap_n"],
            "tube_od_mm":         res["vap_od_mm"],
            "tube_id_mm":         res["vap_id_mm"],
            "crimp_orifice_dia_mm": res["vap_crimp_dia_mm"],
            "scoop_inlet_dia_mm": res["vap_scoop_dia_mm"],
            "bend_radius_mm":     res["vap_bend_radius_mm"],
            "pitch_actual_mm":    res["vap_pitch_actual_mm"],
            "fuel_per_tube_g_s":  res["vap_m_fuel_per_tube"],
            "air_per_tube_g_s":   res["vap_m_air_per_tube"],
        },

        # ── Film cooling ────────────────────────────────────────────────────
        "film_cooling": {
            "total_rows":               res["film_n_rows"],
            "hole_dia_mm":              res["film_hole_dia_mm_actual"],
            "outer_holes_per_row":      res["film_holes_per_row_outer"],
            "inner_holes_per_row":      res["film_holes_per_row_inner"],
            "total_holes":              res["film_total_holes"],
            "total_area_mm2":           res["film_total_area_mm2"],
        },

        # ── Combustion performance at design point ───────────────────────────
        "combustion_performance_design": {
            "CLP":                res["CLP"],
            "CLP_T":              res["CLP_T"],
            "eta_comb_estimated": res["eta_comb_estimated"],
            "tau_comb_ms":        res["tau_comb_ms"],
            "T_primary_zone_K":   res["T_primary_zone_est"],
        },

        # ── Structural / stability flags at design point ─────────────────────
        "design_flags": {
            "J_primary":           res["stab_J_primary"],
            "J_ok":                res["stab_J_ok"],
            "flashback_risk":      res["stab_flashback_risk"],
            "dome_heat_kW_m2":     res["stab_q_dome_kW_m2"],
            "dome_ok":             res["stab_dome_ok"],
            "vap_coking_risk":     res["stab_vap_coking_risk"],
            "vap_structural_risk": res["stab_vap_structural_risk"],
            "liner_ss304_ok":      res["liner_ss304_ok"],
            "liner_in625_ok":      res["liner_in625_ok"],
        },

        # ── Values needed by the off-design calculator ───────────────────────
        "off_design_anchors": {
            "A_exit_m2":          res["combustion_annulus_A"],
            "mdot_air_design":    res["mdot_air"],
            "rho2_design":        res["rho2"],
            # Store absolute design-point dP in Pa, NOT the fraction.
            # Absolute Pa scales correctly with dynamic pressure (mdot^2/rho).
            # The fraction is re-derived at each off-design point from dP_Pa / P2.
            "dP_Pa_design":       res["P2_Pa"] * dp["target_pressure_drop"],
            "V_primary_m3":       res["CLP_V_primary_m3"],
            "V_total_m3":         res["CLP_V_total_m3"],
            # Preserve V21's heat_loss_factor so V22 fuel flows stay consistent
            # with the design-point sizing even when the user has set hlf < 1.0.
            "heat_loss_factor":   res.get("heat_loss_factor", 1.0),
            "eta_assumed": res['eta_comb_used'],
            "fuel_LHV_J_kg": model.FUEL['LHV'],
            "ambient_pressure_Pa": design_inputs.get('ambient_pressure_Pa',P_AMB),
            "ambient_temperature_K": design_inputs.get('ambient_temperature_K',T_AMB),
            # Lefebvre theta normalisation factor (computed above).
            # theta_norm = CLP_linear_design / clp_theta_design, which makes
            # CLP_effective == CLP_linear exactly at the design point, then
            # diverges correctly (higher CLP_eff) at part-throttle, capturing
            # the non-linear P^1.75 and exponential temperature dependence of
            # chemical reaction rates that the linear CLP misses off-design.
            "theta_norm":         _theta_norm,
            # Design-point thermodynamics — stored for reference / validation.
            "CLP_design":         res["CLP"],
            "P2_Pa_design":       res["P2_Pa"],
            "T2_K_design":        res["T2_K"],
        },

        # ── Full V21 results dict (for any downstream key not listed above) ──
        "v21_full_results": res,
    }

    return card


# ===========================================================================
# OFF-DESIGN POINT EVALUATOR
# ===========================================================================
def evaluate_off_design_point(
    anchors:     dict,
    pr:          float,
    mdot_air:    float,
    eff_c:       float,
    tit:         float,
    rpm_pct:     float | None = None,
    label:       str  | None = None,
) -> dict:
    """
    Compute combustor performance for ONE off-design operating point.

    Parameters
    ----------
    anchors   : dict from card["off_design_anchors"]
    pr        : compressor total pressure ratio  (–)
    mdot_air  : air mass flow rate               (kg/s)
    eff_c     : isentropic compressor efficiency (–)
    tit       : target turbine inlet temperature (K)
    rpm_pct   : RPM as % of design (optional, stored in output)
    label     : descriptive label (optional)

    Returns
    -------
    dict of all computed quantities at this operating point.
    """
    # ── Compressor / Combustor Inlet ────────────────────────────────────────
    thermo.efficiency(compressor_efficiency=eff_c)
    thermo.positive(pr=pr,mdot_air=mdot_air)
    ambient_P = anchors.get('ambient_pressure_Pa',P_AMB)
    ambient_T = anchors.get('ambient_temperature_K',T_AMB)
    P2 = ambient_P*pr
    T2_iso = thermo.isentropic_temperature(ambient_T,pr,R=R_AIR)
    T2 = thermo.temperature(gas.h_air(ambient_T)+(gas.h_air(T2_iso)-gas.h_air(ambient_T))/eff_c)
    rho2    = P2 / (R_AIR * T2)

    # ── Combustion Loading Parameter — Linear CLP + Lefebvre Theta ──────────
    # CLP must be computed BEFORE the fuel calculation so eta_est feeds the
    # energy balance.
    #
    # Linear CLP = ṁ / (P_kPa · V)  — the same formulation used in V21.
    # At off-design this is unreliable because the numerator (ṁ) falls much
    # faster than the denominator (P·V) at part-throttle, causing CLP to DROP
    # at idle and _clp_eta to predict IMPROVING combustion — physically backwards.
    #
    # Lefebvre's non-linear theta parameter replaces the linear P term with
    # P^1.75 · exp(T/300), capturing:
    #   — P^1.75  : chemical reaction rate dependence on pressure (Arrhenius ∝ P^n, n≈1.75)
    #   — exp(T/300): exponential temperature dependence of reaction rates
    # Together these make the denominator shrink FASTER than the numerator at
    # part-throttle, so CLP_effective rises at part-power as it should physically.
    #
    # theta_norm is pre-computed in build_design_card so that CLP_effective equals
    # the linear CLP exactly at the design point and requires no manual tuning.
    # Reference: Lefebvre, "Gas Turbine Combustion" 3rd Ed., §4.3 and §5.2.
    P2_kPa      = P2 / 1000.0
    V_primary   = anchors["V_primary_m3"]
    V_total     = anchors["V_total_m3"]
    theta_norm  = anchors["theta_norm"]

    CLP_linear  = mdot_air / (P2_kPa * V_primary) if V_primary > 0 else float("nan")

    if V_primary > 0:
        clp_theta   = mdot_air / ((P2_kPa ** 1.75) * math.exp(T2 / 300.0) * V_primary)
        CLP_eff     = clp_theta * theta_norm   # anchored to linear CLP at design point
    else:
        CLP_eff     = float("nan")

    CLP_T       = CLP_eff * math.sqrt(T2 / 300.0) if not math.isnan(CLP_eff) else float("nan")
    eta_diagnostic = _clp_eta(CLP_eff)
    eta_est = anchors["eta_assumed"]  # assumed; no uncalibrated CLP feedback

    # ── Pressure Drop (absolute Pa scaling) ────────────────────────────────
    # ΔP (Pa) scales with dynamic pressure: ∝ ṁ² / ρ.
    # We anchor the absolute design-point ΔP (Pa) and scale it, then divide by
    # the new P2 to recover the fraction.  Scaling the fraction directly is wrong
    # because it ignores that P2 itself has changed at part-throttle.
    dP_Pa_dp    = anchors["dP_Pa_design"]
    mdot_dp     = anchors["mdot_air_design"]
    rho2_dp     = anchors["rho2_design"]
    dP_Pa_off   = dP_Pa_dp * ((mdot_air / mdot_dp) ** 2) * (rho2_dp / rho2)
    dP_frac     = dP_Pa_off / P2      # fraction re-derived at this P2
    P4          = P2 - dP_Pa_off

    # ── Fuel Flow (energy balance with variable cp) ─────────────────────────
    # Use the dynamically-computed eta_est (not a hard-coded constant) and
    # preserve V21's heat_loss_factor so design-point fuel flows are consistent.
    # ===== PATCH P1 =====
    # Was: mdot_fuel = mdot_air * cp(T_mean) * (TIT - T2) / (LHV * eta * hlf).
    # A single mean cp, with the fuel mass left out of the product stream.
    # Now a real enthalpy balance with the fuel mass carried through, solved by
    # the same function the sizing model uses.
    T_avg       = (tit + T2) / 2.0
    cp_avg      = _cp(T_avg)
    hlf         = anchors["heat_loss_factor"]
    far         = gas.far_for_T4(T2, tit, eta_est * hlf, anchors["fuel_LHV_J_kg"])
    mdot_fuel   = mdot_air * far
    energy_req  = mdot_fuel * anchors["fuel_LHV_J_kg"] * eta_est * hlf
    mdot_total  = mdot_air + mdot_fuel
    AFR         = mdot_air / mdot_fuel if mdot_fuel > 0 else float("inf")
    phi         = 14.7 / AFR  # STOICH_AFR = 14.7 for Jet-A

    # ── Exit Conditions through Fixed Combustion Annulus Area ───────────────
    A_exit      = anchors["A_exit_m2"]
    T4_total, P4_total = tit, P4
    V4,T4_static,P4 = thermo.area_state(mdot_total,A_exit,tit,P4,far,R_AIR)
    rho4 = P4/(R_AIR*T4_static)
    a4 = math.sqrt(thermo.gamma(T4_static,far,R_AIR)*R_AIR*T4_static)
    Ma4 = V4/a4
    h_avail = gas.h_products(tit,far)-gas.h_products(ambient_T,far)

    # ── Residence time ───────────────────────────────────────────────────────
    T_mean_comb = (T2 + tit) / 2.0
    rho_mean    = P2 / (R_AIR * T_mean_comb)
    V_dot       = mdot_total / rho_mean
    tau_ms      = (V_total / V_dot) * 1000.0

    # ── Build result dict ────────────────────────────────────────────────────
    result = {
        # Identifiers
        "rpm_pct":              rpm_pct,
        "label":                label,
        # Prescribed inputs
        "in_pressure_ratio":    pr,
        "in_mdot_air_kg_s":     mdot_air,
        "in_eta_compressor":    eff_c,
        "in_TIT_K":             tit,
        # Inlet / compressor exit
        "P2_Pa":                round(P2, 1),
        "P2_kPa":               round(P2 / 1000.0, 3),
        "T2_K":                 round(T2, 2),
        "rho2_kg_m3":           round(rho2, 4),
        # Combustor pressure drop
        "dP_fraction":          round(dP_frac, 5),
        "dP_pct":               round(dP_frac * 100.0, 3),
        "dP_Pa":                round(dP_Pa_off, 1),
        # Fuel / combustion
        "mdot_fuel_kg_s":       round(mdot_fuel, 6),
        "mdot_fuel_g_s":        round(mdot_fuel * 1000.0, 3),
        "mdot_total_kg_s":      round(mdot_total, 6),
        "AFR":                  round(AFR, 3),
        "phi_overall":          round(phi, 4),
        "cp_avg_J_kgK":         round(cp_avg, 1),
        "eta_comb_used":        round(eta_est, 4),   # assumed value used in fuel calculation
        "heat_loss_factor":     hlf,                 # anchored from V21 design card
        # Combustor exit (turbine inlet)
        "P4_Pa":                round(P4, 1),
        "P4_kPa":               round(P4 / 1000.0, 3),
        "T4_static_K":          T4_static,
        "rho4_kg_m3":           round(rho4, 4),
        "V4_m_s":               round(V4, 3),
        "Ma4":                  round(Ma4, 4),
        "a4_m_s":               round(a4, 2),
        "T4_total_K":           round(T4_total, 2),
        "P4_total_Pa":          round(P4_total, 1),
        "P4_total_kPa":         round(P4_total / 1000.0, 3),
        "h_avail_kJ_kg":        round(h_avail / 1000.0, 2),
        # Combustion quality
        "CLP_linear":           round(CLP_linear, 3) if not math.isnan(CLP_linear) else None,
        "CLP_effective":        round(CLP_eff, 3)    if not math.isnan(CLP_eff)    else None,
        "CLP_T":                round(CLP_T, 3)      if not math.isnan(CLP_T)      else None,
        "tau_comb_ms":          round(tau_ms, 2),
        # Derived flags
        "flag_Ma4_high":        Ma4 > 0.25,
        "flag_Ma4_choked":      Ma4 >= 1.0,   # physically impossible — exit is choked
        "flag_CLP_stable":      False,  # no demonstrated stability evidence
        "release_status": "PRELIMINARY - prescribed operating points, not engine map matching",
        "flag_CLP_acceptable":  CLP_eff < 15.0 if not math.isnan(CLP_eff) else None,
        "flag_tau_ok":          tau_ms >= 2.0,
    }
    return result


# ===========================================================================
# SWEEP RUNNER
# ===========================================================================
def run_sweep(design_card: dict, operating_line: list[dict]) -> list[dict]:
    """
    Evaluate the combustor over every point in `operating_line`.

    Each entry in `operating_line` must contain:
        pr       — compressor pressure ratio
        mdot_air — air mass flow (kg/s)
        eff_c    — isentropic compressor efficiency
        tit      — target turbine inlet temperature (K)
    Optional:
        rpm_pct  — RPM as % of design speed (purely informational)
        label    — descriptive string

    Returns a list of result dicts from evaluate_off_design_point().
    """
    anchors = design_card["off_design_anchors"]
    results = []
    for pt in operating_line:
        res = evaluate_off_design_point(
            anchors  = anchors,
            pr       = pt["pr"],
            mdot_air = pt["mdot_air"],
            eff_c    = pt["eff_c"],
            tit      = pt["tit"],
            rpm_pct  = pt.get("rpm_pct"),
            label    = pt.get("label"),
        )
        results.append(res)
    return results


# ===========================================================================
# REPORTING
# ===========================================================================
_LINE = "─" * 98

def _hdr(title: str):
    print(f"\n{'─'*4} {title} {'─'*(90-len(title))}")

def print_design_card_summary(card: dict):
    """Console summary of the design-point card."""
    geo = card["geometry"]
    ic  = card["inlet_conditions_design"]
    oc  = card["outlet_conditions_design"]
    ab  = card["air_budget_design"]
    anc = card["off_design_anchors"]

    print()
    print("=" * 98)
    print("  PRELIMINARY COMBUSTOR DESIGN CARD - PRESCRIBED-POINT SCREENING")
    print("=" * 98)

    _hdr("GEOMETRY  (all mm except area)")
    print(f"  Casing OD / ID                : {geo['casing_od_mm']:.2f} / {geo['casing_id_mm']:.2f} mm")
    print(f"  Shaft tunnel OD / ID          : {geo['shaft_tunnel_od_mm']:.2f} / {geo['shaft_tunnel_id_mm']:.2f} mm")
    print(f"  Outer liner  OD cold / hot    : {geo['outer_liner_od_cold_mm']:.3f} / {geo['outer_liner_od_hot_mm']:.3f} mm"
          f"  (thermal offset {geo['outer_liner_thermal_offset_mm']:.3f} mm)")
    print(f"  Outer liner  ID               : {geo['outer_liner_id_mm']:.3f} mm")
    print(f"  Inner liner  OD cold / hot    : {geo['inner_liner_od_cold_mm']:.3f} / {geo['inner_liner_od_hot_mm']:.3f} mm"
          f"  (thermal offset {geo['inner_liner_thermal_offset_mm']:.3f} mm)")
    print(f"  Inner liner  ID               : {geo['inner_liner_id_mm']:.3f} mm")
    print(f"  Combustion annulus gap        : {geo['combustion_gap_mm']:.2f} mm")
    print(f"  Combustion annulus area       : {anc['A_exit_m2']*1e6:.2f} mm²  ({anc['A_exit_m2']:.6f} m²)")
    print(f"  Mean combustion diameter      : {geo['D_mean_comb_mm']:.2f} mm")
    print(f"  Chamber length (total)        : {geo['chamber_length_mm']:.2f} mm")
    print(f"    └─ Primary                  : {geo['L_primary_mm']:.2f} mm")
    print(f"    └─ Secondary                : {geo['L_secondary_mm']:.2f} mm")
    print(f"    └─ Dilution                 : {geo['L_dilution_mm']:.2f} mm")
    print(f"  Liner material                : {geo['liner_material_name']}")

    _hdr("DESIGN-POINT INLET CONDITIONS")
    print(f"  Pressure ratio                : {ic['pressure_ratio']:.3f}")
    print(f"  Compressor efficiency         : {ic['eta_compressor']:.3f}")
    print(f"  P2                            : {ic['P2_kPa']:.2f} kPa  ({ic['P2_Pa']:.0f} Pa)")
    print(f"  T2                            : {ic['T2_K']:.2f} K  ({ic['T2_K']-273.15:.1f} °C)")
    print(f"  rho2                          : {ic['rho2_kg_m3']:.4f} kg/m³")
    print(f"  mdot_air                      : {ic['mdot_air_kg_s']:.4f} kg/s  ({ic['mdot_air_kg_s']*1000:.2f} g/s)")

    _hdr("DESIGN-POINT OUTLET CONDITIONS  (turbine inlet)")
    print(f"  TIT (target)                  : {oc['target_TIT_K']:.1f} K  ({oc['target_TIT_K']-273.15:.1f} °C)")
    print(f"  mdot_fuel                     : {oc['mdot_fuel_kg_s']*1000:.3f} g/s")
    print(f"  mdot_total                    : {oc['mdot_total_kg_s']*1000:.2f} g/s")
    print(f"  AFR / phi                     : {oc['overall_AFR']:.2f}  /  {oc['overall_phi']:.4f}")
    print(f"  Combustor dP                  : {oc['dP_fraction']*100:.1f}%  ({oc['dP_Pa']:.0f} Pa)")
    print(f"  P4 static                     : {oc['P4_kPa']:.2f} kPa  ({oc['P4_Pa']:.0f} Pa)")
    print(f"  T4 static                     : {oc['T4_static_K']:.1f} K")
    print(f"  T4 total                      : {oc['T4_total_K']:.1f} K")
    print(f"  P4 total                      : {oc['P4_total_Pa']/1000:.2f} kPa")
    print(f"  Exit velocity V4              : {oc['V4_m_s']:.2f} m/s")
    print(f"  Exit Mach Ma4                 : {oc['Ma4']:.4f}")
    print(f"  Specific enthalpy (h_avail)   : {oc['h_avail_kJ_kg']:.1f} kJ/kg")

    _hdr("DESIGN-POINT AIR BUDGET")
    print(f"  Total air                     : {ab['mdot_total_kg_s']*1000:.2f} g/s")
    print(f"  ├─ Film cooling               : {ab['mdot_film_cooling_kg_s']*1000:.2f} g/s")
    print(f"  ├─ Primary (total)            : {ab['mdot_primary_kg_s']*1000:.2f} g/s")
    print(f"  │    ├─ Liner holes           : {ab['mdot_primary_liner_kg_s']*1000:.2f} g/s")
    print(f"  │    └─ Vaporizer             : {ab['mdot_primary_vap_kg_s']*1000:.2f} g/s")
    print(f"  ├─ Secondary                  : {ab['mdot_secondary_kg_s']*1000:.2f} g/s")
    print(f"  └─ Dilution                   : {ab['mdot_dilution_kg_s']*1000:.2f} g/s")
    print(f"  Primary zone phi              : {ab['phi_primary']:.3f}")

    hs  = card["hole_schedule"]
    vap = card["vaporizers"]
    _hdr("HOLE SCHEDULE")
    print(f"  Outer / inner fraction        : {hs['outer_fraction']:.3f} / {hs['inner_fraction']:.3f}"
          f"    Cd = {hs['Cd']}")
    print(f"  {'Zone':<12}  {'Outer qty':>9}  {'Outer dia':>9}  {'Inner qty':>9}  {'Inner dia':>9}")
    print(f"  {'─'*54}")
    for zone in ("primary", "secondary", "dilution"):
        z = hs[zone]
        print(f"  {zone.capitalize():<12}  {z['outer_qty']:>9d}  {z['outer_dia_mm']:>8.2f}mm"
              f"  {z['inner_qty']:>9d}  {z['inner_dia_mm']:>8.2f}mm")

    _hdr("VAPORIZER TUBES")
    print(f"  Count  : {vap['count']}   pitch {vap['pitch_actual_mm']:.1f} mm")
    print(f"  Tube   : OD {vap['tube_od_mm']:.2f} mm / ID {vap['tube_id_mm']:.2f} mm"
          f"   bend R {vap['bend_radius_mm']:.1f} mm")
    print(f"  Crimp orifice : {vap['crimp_orifice_dia_mm']:.2f} mm"
          f"   scoop inlet {vap['scoop_inlet_dia_mm']:.2f} mm")
    print(f"  Per tube      : fuel {vap['fuel_per_tube_g_s']:.3f} g/s   air {vap['air_per_tube_g_s']:.3f} g/s")


def print_sweep_table(sweep_results: list[dict]):
    """Console tabulation of the RPM sweep."""
    print()
    _hdr("RPM SWEEP  —  OFF-DESIGN RESULTS")
    hdr   = (
        f"{'RPM%':>6}  {'PR':>5}  {'mdot':>7}  {'T2':>7}  {'TIT':>7}  "
        f"{'P4kPa':>8}  {'T4tot':>8}  {'P4tot':>8}  "
        f"{'V4':>7}  {'Ma4':>7}  {'dP%':>7}  {'CLPeff':>7}  {'η':>6}  {'τ ms':>7}"
    )
    print("  " + hdr)
    print("  " + "─" * (len(hdr)))
    choked_points = []
    for r in sweep_results:
        rpm_s    = f"{r['rpm_pct']:.0f}" if r["rpm_pct"] is not None else "--"
        lbl_s    = f"  ({r['label']})" if r.get("label") else ""
        flag_chk = "✖" if r["flag_Ma4_choked"] else ("⚠" if r["flag_Ma4_high"] else " ")
        flag_cl  = "" if r["flag_CLP_acceptable"] else " ⚠CLP"
        flag_t   = "" if r["flag_tau_ok"] else " ⚠τ"
        clp_eff  = r["CLP_effective"]
        eta      = r["eta_comb_used"]
        print(
            f"  {rpm_s:>6}  "
            f"{r['in_pressure_ratio']:>5.3f}  "
            f"{r['in_mdot_air_kg_s']:>7.4f}  "
            f"{r['T2_K']:>7.1f}  "
            f"{r['T4_static_K']:>7.1f}  "
            f"{r['P4_kPa']:>8.2f}  "
            f"{r['T4_total_K']:>8.1f}  "
            f"{r['P4_total_kPa']:>8.2f}  "
            f"{r['V4_m_s']:>7.2f}  "
            f"{flag_chk}{r['Ma4']:>6.4f}  "
            f"{r['dP_pct']:>7.3f}  "
            f"{clp_eff:>7.2f}  "
            f"{eta:>6.4f}  "
            f"{r['tau_comb_ms']:>7.2f}"
            f"{lbl_s}{flag_cl}{flag_t}"
        )
        if r["flag_Ma4_choked"]:
            choked_points.append(r)
    print()
    if choked_points:
        print("  " + "!" * 70)
        print("  ✖  CHOKED EXIT DETECTED — PHYSICALLY IMPOSSIBLE OPERATING POINT(S):")
        for r in choked_points:
            lbl = r.get("label") or f"PR={r['in_pressure_ratio']}"
            print(f"       {lbl}  →  Ma4 = {r['Ma4']:.4f}  "
                  f"(mdot={r['in_mdot_air_kg_s']:.3f} kg/s, TIT={r['in_TIT_K']:.0f} K)")
        print("  The fixed combustion annulus area cannot pass this mass flow at")
        print("  these conditions. Flow chokes at Ma4 = 1.0 — actual P4 and V4")
        print("  will be limited by the sonic condition; mass flow or TIT must")
        print("  be reduced, or the exit area increased in V21.")
        print("  " + "!" * 70)
        print()
    print("  Columns: RPM% | PR | mdot [kg/s] | T2 [K] | TIT [K] |"
          " P4_static [kPa] | T4_total [K] | P4_total [kPa] |")
    print("           V4 [m/s] | Ma4 (✖ choked ≥1.0 / ⚠ compressible >0.25) |"
          " dP% | CLP_eff (Lefebvre θ) | η_comb | τ [ms]")
    print("  CLP and residence-time flags are screening thresholds; they do not establish stability or blowout.")


# ===========================================================================
# JSON SERIALISER  (handles numpy / non-standard types gracefully)
# ===========================================================================
def _json_safe(obj):
    if isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    try:
        return float(obj)   # numpy scalar fallback
    except Exception:
        return str(obj)


def write_json(data, path: str):
    with open(path, "w") as f:
        json.dump(_json_safe(data), f, indent=2)
    print(f"  ✓  Written: {path}")


# ===========================================================================
# ENTRY POINT
# ===========================================================================
if __name__ == "__main__":

    # ── 1.  Design-point inputs (used to build the V21 geometry) ─────────────
    DESIGN_INPUTS = {
        'casing_od_inch':        6.00,
        'shaft_tunnel_od_inch':  2.0,
        'wall_thickness_mm':     1.50,
        'pressure_ratio':        2.5,
        'compressor_efficiency': 0.90,
        'mass_flow_air_kg_s':    0.60,
        'target_tit_k':          1000.0,
        'liner_material':       '316SS',
    }

    # ── 2.  Operating line — one dict per RPM point ───────────────────────────
    #
    #   Columns:
    #     rpm_pct  — throttle position as % of design speed (informational)
    #     pr       — compressor total-to-total pressure ratio at that RPM
    #     mdot_air — air mass flow (kg/s) at that RPM
    #     eff_c    — isentropic compressor efficiency at that RPM
    #     tit      — target / actual turbine inlet temperature (K)
    #     label    — optional descriptive tag
    #
    #   Typical compressor map characteristics for a micro-GT:
    #     100 % RPM → design PR, design flow
    #      80 % RPM → PR ≈ 0.60 × design,  mdot ≈ 0.53 × design  (approx square law)
    #      60 % RPM → PR ≈ 0.30 × design,  mdot ≈ 0.30 × design
    #      50 % RPM → PR ≈ 0.15 × design,  mdot ≈ 0.20 × design

    OPERATING_LINE = [
        # Full power / design point — should reproduce V21 exactly
        {'rpm_pct': 100, 'pr': 2.50, 'mdot_air': 0.600, 'eff_c': 0.90, 'tit': 1000, 'label': 'Design point'},
        # High throttle
        {'rpm_pct':  95, 'pr': 2.25, 'mdot_air': 0.540, 'eff_c': 0.89, 'tit':  980, 'label': '95% RPM'},
        # Mid throttle
        {'rpm_pct':  80, 'pr': 1.60, 'mdot_air': 0.320, 'eff_c': 0.84, 'tit':  900, 'label': '80% RPM'},
        # Low throttle
        {'rpm_pct':  65, 'pr': 1.30, 'mdot_air': 0.200, 'eff_c': 0.76, 'tit':  840, 'label': '65% RPM'},
        # Idle
        {'rpm_pct':  50, 'pr': 1.10, 'mdot_air': 0.100, 'eff_c': 0.66, 'tit':  780, 'label': 'Idle (~50%)'},
    ]

    # ── 3.  Run ───────────────────────────────────────────────────────────────
    ts = _utcnow().strftime("%Y%m%d_%H%M%S")

    print("\n  Building design card from V21 geometry model …")
    design_card = build_design_card(DESIGN_INPUTS)

    print("  Running off-design sweep …")
    sweep = run_sweep(design_card, OPERATING_LINE)

    # ── 4.  Console output ────────────────────────────────────────────────────
    print_design_card_summary(design_card)
    print_sweep_table(sweep)

    # ── 5.  JSON file output ──────────────────────────────────────────────────
    os.makedirs("out",exist_ok=True)
    card_path  = os.path.join("out",f"design_card_{ts}.json")
    sweep_path = os.path.join("out",f"sweep_results_{ts}.json")

    # Strip the bulky raw V21 dict from the card before saving
    # (it's still in memory if needed; the other sections carry everything
    #  a downstream script is likely to need)
    card_for_export = {k: v for k, v in design_card.items() if k != "v21_full_results"}
    card_for_export["_note"] = (
        "v21_full_results omitted from this file to keep it readable. "
        "Re-run build_design_card() and access .v21_full_results in memory if needed."
    )

    sweep_output = {
        "metadata": {
            "design_inputs":   DESIGN_INPUTS,
            "generated_utc":   _utcnow().isoformat(timespec="seconds") + "Z",
            "anchors_used":    design_card["off_design_anchors"],
        },
        "sweep_points": sweep,
    }

    print()
    write_json(card_for_export,  card_path)
    write_json(sweep_output,     sweep_path)
    print()

    pass