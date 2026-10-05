"""
M01 -- Design point cycle.

This is the root of the whole design. Every other module is downstream of it.

The important structural fact, and the one that surprises people: the design
point cycle is a SINGLE PASS. There is no global iteration. Given assumed
component efficiencies, you walk station 2 -> 3 -> 4 -> 5 -> 8 once and you are
done. The compressor-turbine work match is not solved iteratively -- the
turbine's job is simply "produce what the compressor consumes, divided by
mechanical efficiency", computed directly.

Component efficiencies are assumed inputs; no calibrated feedback model exists.

Mass flow is solved backwards from the thrust target: compute thrust per kg/s
of air, then divide. This is why F_target_N is the scale-setter -- it is the
only place the absolute size of the engine enters.

SOURCE SELECTION (one producer for every cycle variable, explicit mode):
  mode 0 (default, both flags absent/0): thrust sizing as above (legacy baseline).
  cycle_prescribed_flow_flag = 1: airflow is prescribed (mdot_prescribed_kg_s);
      thrust becomes an output. A design SCREEN; turbine work is still imposed.
  cycle_imported_point_flag = 1: every station value comes from a fixed-geometry
      operating point solved by core/engine_match.py (op_* seeds, written by
      run_case.py with the match fingerprint). Turbine work is the RATED value
      from the turbine model, not compressor demand / efficiency.
  mdot_comb_kg_s and P031_Pa are the combustor's own inlet flow and pressure:
  equal to mdot / P03 in modes 0 and 1; reduced by tunnel leakage and the
  diffuser-to-combustor turn loss in the imported mode.
"""

from core.module import module
from core import gas, thermo


@module(
    tier=1,
    title="Design point cycle and station table",
    owner="CYCLE-1", second="CYCLE-2",
    status="draft",
    reads=[
        "T00_K", "P00_Pa", "dP02_frac", "PR_c_ratio", "eta_c_isen",
        "cp_cold_J_kgK", "gamma_cold_ratio", "T04_K", "eta_b_frac",
        "LHV_fuel_J_kg", "dP34_frac", "eta_mech_frac", "cp_hot_J_kgK",
        "gamma_hot_ratio", "eta_t_isen", "R_gas_J_kgK", "Cv_nozzle_ratio",
    ],
    optional_reads=[
        "F_target_N", "cycle_prescribed_flow_flag", "mdot_prescribed_kg_s",
        "cycle_imported_point_flag", "op_mdot_air_kg_s", "op_mdot_comb_kg_s", "op_mdot_fuel_kg_s",
        "op_P02_Pa", "op_T03_K", "op_P03_Pa", "op_P031_Pa", "op_P04_Pa", "op_T05_K", "op_P05_Pa",
        "op_w_comp_J_kg", "op_w_turb_J_kg", "op_F_gross_N",
    ],
    writes=[
        "T02_K", "P02_Pa", "T03_K", "P03_Pa", "P04_Pa", "T05_K", "P05_Pa",
        "w_comp_J_kg", "w_turb_J_kg", "FAR_ratio", "Fs_N_per_kg_s",
        "mdot_kg_s", "mdot_fuel_kg_s", "mdot_comb_kg_s", "P031_Pa",
    ],
    notes="Single pass. Mode flags select thrust sizing, prescribed flow, or an imported matched point.",
)
def m01_cycle(s):
    prescribed = bool(s["cycle_prescribed_flow_flag"]) if "cycle_prescribed_flow_flag" in s else False
    imported = bool(s["cycle_imported_point_flag"]) if "cycle_imported_point_flag" in s else False
    if prescribed and imported:
        raise gas.GasError("select either prescribed flow or an imported operating point, not both")
    if imported:
        return _imported_point(s)
    thermo.efficiency(eta_c=s["eta_c_isen"], eta_t=s["eta_t_isen"], eta_m=s["eta_mech_frac"])
    if prescribed:
        thermo.positive(mdot_prescribed=s["mdot_prescribed_kg_s"])
    else:
        thermo.positive(PR=s["PR_c_ratio"], thrust=s["F_target_N"])
    if s["PR_c_ratio"] <= 1 or not all(0 <= s[k] < 1 for k in ("dP02_frac", "dP34_frac")):
        raise gas.GasError("invalid cycle pressure ratio/loss")
    cp_c = s["cp_cold_J_kgK"]
    cp_h = s["cp_hot_J_kgK"]
    g_c = s["gamma_cold_ratio"]
    g_h = s["gamma_hot_ratio"]
    R = s["R_gas_J_kgK"]

    # -- station 2: compressor inlet ----------------------------------------
    T02 = s["T00_K"]
    P02 = s["P00_Pa"] * (1.0 - s["dP02_frac"])

    # -- station 3: compressor exit -----------------------------------------
    PR = s["PR_c_ratio"]
    P03 = P02 * PR
    T03s = thermo.isentropic_temperature(T02, PR, R=R)
    w_comp = (gas.h_air(T03s)-gas.h_air(T02))/s["eta_c_isen"]
    T03 = thermo.temperature(gas.h_air(T02)+w_comp)

    # -- station 4: combustor exit / turbine inlet --------------------------
    P04 = P03 * (1.0 - s["dP34_frac"])
    T04 = s["T04_K"]

    # Fuel-air ratio from a real enthalpy balance, with the fuel mass carried
    # into the products. See core/gas.far_for_T4.
    #
    # This USED to be  far = (cp_h*T04 - cp_c*T03)/(eta_b*LHV - cp_h*T04)  with
    # cp_h and cp_c as constants. That is the textbook form, but a constant cp
    # with a zero-kelvin enthalpy datum over-predicted the fuel-air ratio by
    # 12-17% against air property tables -- which over-fuelled the engine and
    # propagated into the combustor air split and the pump sizing. Do not
    # reintroduce it.
    far = gas.far_for_T4(T03, T04, s["eta_b_frac"], s["LHV_fuel_J_kg"])

    # -- station 5: turbine exit --------------------------------------------
    # The work match. Turbine flow is (1 + FAR) times the air flow, so the
    # specific work the turbine must produce per kg of ITS OWN flow is smaller
    # than the compressor's specific work by that factor.
    w_turb = w_comp / (s["eta_mech_frac"] * (1.0 + far))
    T05 = thermo.temperature(gas.h_products(T04,far)-w_turb,far)
    T05_ideal = thermo.temperature(gas.h_products(T04,far)-w_turb/s["eta_t_isen"],far)
    P05 = thermo.pressure(T05_ideal,T04,P04,far,R)
    V8, T8, P8, choked = thermo.nozzle(T05,P05,s["P00_Pa"],far,R,Cv=s["Cv_nozzle_ratio"])

    # specific thrust, normalised per kg/s of AIR (not of hot gas)
    if choked:
        rho8 = gas.density(P8, T8, R)
        a8_per_kg = (1.0 + far) / (rho8 * V8)          # m2 per (kg/s of air)
        Fs = (1.0 + far) * V8 + a8_per_kg * (P8 - s["P00_Pa"])
    else:
        Fs = (1.0 + far) * V8

    mdot = s["mdot_prescribed_kg_s"] if prescribed else s["F_target_N"] / Fs

    return {
        "T02_K": T02, "P02_Pa": P02,
        "T03_K": T03, "P03_Pa": P03,
        "P04_Pa": P04,
        "T05_K": T05, "P05_Pa": P05,
        "w_comp_J_kg": w_comp,
        "w_turb_J_kg": w_turb,
        "FAR_ratio": far,
        "Fs_N_per_kg_s": Fs,
        "mdot_kg_s": mdot,
        "mdot_fuel_kg_s": mdot * far,
        "mdot_comb_kg_s": mdot,
        "P031_Pa": P03,
    }


def _imported_point(s):
    """Publish a fixed-geometry matched operating point without recomputing it.

    Consistency with this module's own gas model is checked rather than assumed:
    the compressor work implied by T03 and the combustor fuel balance must agree
    with the imported values, otherwise the point is stale or from another model.
    """
    names = ["op_mdot_air_kg_s", "op_mdot_comb_kg_s", "op_mdot_fuel_kg_s", "op_P02_Pa", "op_T03_K",
             "op_P03_Pa", "op_P031_Pa", "op_P04_Pa", "op_T05_K", "op_P05_Pa", "op_w_comp_J_kg",
             "op_w_turb_J_kg", "op_F_gross_N"]
    v = {n: s[n] for n in names}   # raises a clear ModuleError if any is missing
    T02 = s["T00_K"]
    w_c = gas.h_air(v["op_T03_K"]) - gas.h_air(T02)
    if abs(w_c - v["op_w_comp_J_kg"]) > 1e-6 * v["op_w_comp_J_kg"] + 1e-3:
        raise gas.GasError("imported compressor work disagrees with imported T03 (stale operating point?)")
    far = v["op_mdot_fuel_kg_s"] / v["op_mdot_comb_kg_s"]
    far_check = gas.far_for_T4(v["op_T03_K"], s["T04_K"], s["eta_b_frac"], s["LHV_fuel_J_kg"])
    if abs(far - far_check) > 1e-7 * far_check:
        raise gas.GasError("imported fuel flow disagrees with T03/T04 energy balance (stale operating point?)")
    if not v["op_P05_Pa"] < v["op_P04_Pa"] < v["op_P031_Pa"] <= v["op_P03_Pa"]:
        raise gas.GasError("imported pressures are not monotonic through the engine")
    return {
        "T02_K": T02, "P02_Pa": v["op_P02_Pa"],
        "T03_K": v["op_T03_K"], "P03_Pa": v["op_P03_Pa"],
        "P04_Pa": v["op_P04_Pa"],
        "T05_K": v["op_T05_K"], "P05_Pa": v["op_P05_Pa"],
        "w_comp_J_kg": v["op_w_comp_J_kg"], "w_turb_J_kg": v["op_w_turb_J_kg"],
        "FAR_ratio": far, "Fs_N_per_kg_s": v["op_F_gross_N"] / v["op_mdot_air_kg_s"],
        "mdot_kg_s": v["op_mdot_air_kg_s"], "mdot_fuel_kg_s": v["op_mdot_fuel_kg_s"],
        "mdot_comb_kg_s": v["op_mdot_comb_kg_s"], "P031_Pa": v["op_P031_Pa"],
    }
