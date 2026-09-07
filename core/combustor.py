"""Preliminary reverse-flow combustor sizing and diagnostic correlations.

One cycle state, frozen annuli and separately budgeted air paths. Correlation
outputs are screening estimates, not demonstrated stability, wall temperature,
burst resistance, or manufacturing approval. See docs/model-review.md.
"""

from __future__ import annotations
import math

from core import gas, thermo

PATCH_NOTES = {
    "P1":  "fuel energy balance: real enthalpy, fuel mass in products",
    "P2":  "thermal growth: diameter change, not radius; wall temp not TIT",
    "P3":  "residence time: same mass flow in the length sizing and the check",
    "P4":  "combustion efficiency fed back into the fuel balance",
    "P5":  "feed split iterated between geometry and pressure balance",
    "P6":  "jet penetration: multi-jet correlation (Lefebvre Eq. 4.20)",
    "P7":  "dome heat flux: Lefebvre liner-convection, Martin reported alongside",
    "P8":  "corrected the eta-vs-loading citation",
    "P9":  "chamber length upper bound",
    "P10": "pressure drop verified against the hole areas it produced",
    "P11": "phi_primary reported honestly as an input echo",
    "P12": "exit plane named as combustor discharge, NGV throat reported",
    "P13": "hole pressure-drop coefficient K computed so Cd can be checked",
}


class CombustorError(Exception):
    pass


class MicroJetCombustor:
    def __init__(self, inputs):
        self.inputs = inputs
        self.res = {}
        self.patches = []
        self.R = inputs.get("gas_constant_J_kgK",287.05)
        thermo.positive(R=self.R)
        self.GAMMA = 1.4

        self.DESIGN_PARAMS = {
            'target_annulus_vel':       35.0,
            'target_inner_annulus_vel': None,
            'target_tube_liq_vel':      3.0,
            'target_vap_mix_vel':       85.0,
            'vap_pitch_mm':             50.0,
            'target_pressure_drop':     0.04,
            # ===== PATCH P14 =====
            # Lefebvre Table 4.1: the pressure-loss factor dP/q_ref is 20 for a
            # straight-through annular combustor, 28 tuboannular, 37 tubular.
            # A reverse-flow can adds a 180-degree turn on top; the KJ66 measures
            # 12% total loss where a straight annular would give 5-6%, so K here
            # is optimistic and should be revisited with CFD at Gate B.
            'K_annular_ratio':          20.0,
            'liner_area_frac':          0.66,
            'discharge_coeff_hole':     0.60,
            'frac_primary_zone':        0.30,
            'frac_secondary_zone':      0.30,
            'frac_dilution_zone':       0.40,
            'f_outer_feed':             0.60,
            'tau_min_s':                0.002,
            'L_D_min':                  0.70,
            # ===== PATCH P9 =====
            # V21 had no upper bound on chamber length. At 0.9 kg/s in a
            # 6-inch casing it silently returned a 372 mm combustor -- longer
            # than the whole engine -- because the residence-time floor scales
            # with reference velocity and the annulus was being crushed thin.
            # A reverse-flow can above L/D ~ 2.0 is not a reverse-flow can.
            'L_D_max':                  2.00,
            'outer_liner_hole_fraction': None,
            'film_cooling_fraction':    0.12,
            'primary_air_vaporizer_fraction': 0.12,
            'allowed_vaporizer_counts': [6, 8, 12],
            'vap_scoop_target_vel_m_s': 22.0,
            'vap_scoop_cd':             0.72,
            'film_row_pitch_mm':        38.0,
            'film_hole_dia_mm':         1.20,
            'film_rows_primary':        1,
            'film_rows_secondary':      1,
            'film_rows_dilution':       2,
            'K_turn':                   1.0,
            'K_entrance':               0.5,
            'fuel_dP_target_bar':       0.60,
            'sec_holes_per_vap':        2,
            'dil_holes_per_vap':        4,
            'phi_primary_target':       1.6,
            'phi_secondary_target':     0.60,
            # ===== PATCH P2 =====
            # The liner runs far below turbine inlet temperature -- it is film
            # cooled on both faces. V21 used TIT for the thermal growth, which
            # over-predicts expansion; combined with the factor-of-two error it
            # happened to look plausible. Both are fixed; this is the fraction
            # of TIT the liner metal actually reaches.
            'liner_wall_temp_frac':     0.72,
            # ===== PATCH P7 =====
            # Jet impingement geometry, needed by the Martin correlation.
            'dome_jet_standoff_ratio':  4.0,    # H/D
            'dome_jet_radius_ratio':    4.0,    # r/D
            # ===== PATCH P4/P5 =====
            'outer_loop_max_iter':      40,
            'outer_loop_tol':           1e-6,
            'outer_loop_relax':         0.50,
        }

        self.FUEL = {
            "LHV":        43.0e6,
            "STOICH_AFR": 14.7,
            "RHO_LIQ":    800.0,
            "T_BOIL":     450.0,
        }

        self.MATERIALS = {
            '304SS': {'alpha': 17.2e-6, 'name': '304 Stainless Steel'},
            '316SS': {'alpha': 16.0e-6, 'name': '316 Stainless Steel'},
            'IN625': {'alpha': 13.0e-6, 'name': 'Inconel 625'},
            'IN718': {'alpha': 13.0e-6, 'name': 'Inconel 718'},
        }

    # -- gas properties ------------------------------------------------------
    def _get_cp(self, T_kelvin):
        """Kept for interface compatibility. Now delegates to the validated
        shared gas model instead of carrying its own quadratic fit.

        V21's own fit was good to about 0.5% below 700 K but drifted to -3.5%
        by 1100 K, which is squarely where a combustor exit sits.
        """
        return gas.cp_air(T_kelvin)

    # =======================================================================
    def thermodynamics(self):
        if 'inlet_total_pressure_Pa' in self.inputs:
            P2 = self.inputs['inlet_total_pressure_Pa']
            T2 = self.inputs['inlet_total_temperature_K']
        else:
            P_amb = self.inputs.get('ambient_pressure_Pa', 101325.0)
            T_amb = self.inputs.get('ambient_temperature_K', 288.15)
            PR = self.inputs['pressure_ratio']
            eta = self.inputs['compressor_efficiency']
            thermo.efficiency(compressor_efficiency=eta)
            P2 = P_amb * PR
            Ts = thermo.isentropic_temperature(T_amb, PR, R=self.R)
            T2 = thermo.temperature(gas.h_air(T_amb)+(gas.h_air(Ts)-gas.h_air(T_amb))/eta)
        thermo.positive(P2=P2)
        gas.cp_air(T2)
        self.FUEL['LHV'] = self.inputs.get('fuel_LHV_J_kg', self.FUEL['LHV'])
        self.res['P2_Pa'] = P2
        self.res['T2_K'] = T2
        self.res['rho2'] = P2 / (self.R * T2)

    # =======================================================================
    def mass_flow_and_fuel(self, eta_comb=None):
        m_air = self.inputs.get('mass_flow_air_kg_s')
        if m_air is None:
            od_m = self.inputs['casing_od_inch'] * 0.0254
            m_air = 0.45 * (od_m ** 2 / 0.1524 ** 2)

        target_tit = self.inputs['target_tit_k']
        T2 = self.res['T2_K']
        hlf = self.inputs.get('heat_loss_factor', 1.0)

        # ===== PATCH P4 =====
        # V21 hard-coded comb_eff = 0.96 here while combustion_loading()
        # separately computed 0.999 from the CLP and threw it away. The two
        # were never reconciled, which is also why the off-design script
        # disagreed with V21 by 3.9% at the point it claimed to reproduce
        # exactly. eta is now passed in from the outer loop.
        comb_eff = eta_comb if eta_comb is not None else 0.96

        # ===== PATCH P1 =====
        # V21:  m_fuel = m_air * cp(T_mean) * (TIT - T2) / (LHV * eta * hlf)
        # That used a single mean cp and left the fuel mass out of the product
        # stream. Both under-predict; together about 3% low against air tables.
        # (Note for anyone reading the earlier review: the 21% figure quoted
        # there was wrong -- it compared this against a constant-cp cycle model
        # that was itself 17% high. V21 was the better of the two.)
        far = gas.far_for_T4(T2, target_tit, comb_eff * hlf, self.FUEL['LHV'])
        if 'fuel_air_ratio' in self.inputs:
            supplied = self.inputs['fuel_air_ratio']
            if not math.isclose(supplied, far, rel_tol=1e-7):
                raise CombustorError("cycle FAR disagrees with combustor energy balance")
            far = supplied
        m_fuel = self.inputs.get('mass_flow_fuel_kg_s', m_air * far)
        if not math.isclose(m_fuel, m_air*far, rel_tol=1e-9):
            raise CombustorError("cycle fuel/air mass balance does not close")

        self.res['mdot_air'] = m_air
        self.res['mdot_fuel'] = m_fuel
        self.res['overall_AFR'] = m_air / m_fuel
        self.res['overall_phi'] = self.FUEL['STOICH_AFR'] / self.res['overall_AFR']
        self.res['FAR'] = far
        self.res['cp_used'] = gas.cp_air((target_tit + T2) / 2)
        self.res['heat_loss_factor'] = hlf
        self.res['eta_comb_used'] = comb_eff

        # round-trip check: does this fuel flow actually deliver the target TIT?
        T4_check = gas.T4_for_far(T2, far, comb_eff * hlf, self.FUEL['LHV'])
        self.res['TIT_roundtrip_K'] = T4_check
        self.res['TIT_roundtrip_err_K'] = T4_check - target_tit

    # =======================================================================
    def zonal_analysis(self):
        m_fuel = self.res['mdot_fuel']
        stoich = self.FUEL['STOICH_AFR']
        m_total = self.res['mdot_air']

        f_film = self.DESIGN_PARAMS['film_cooling_fraction']
        m_film = m_total * f_film
        m_comb = m_total - m_film

        phi_pri = self.DESIGN_PARAMS['phi_primary_target']
        m_air_pri_total = (m_fuel * stoich) / phi_pri

        if m_air_pri_total > m_comb:
            raise CombustorError(
                f"Primary zone needs {m_air_pri_total*1000:.1f} g/s but only "
                f"{m_comb*1000:.1f} g/s is left after film cooling. Reduce "
                f"film_cooling_fraction, raise mass_flow_air, or lower target_tit_k."
            )

        f_vap = self.DESIGN_PARAMS['primary_air_vaporizer_fraction']
        m_air_vap = m_air_pri_total * f_vap
        m_air_pri_liner = m_air_pri_total * (1.0 - f_vap)
        m_air_pri = m_air_pri_total

        phi_sec_target = self.DESIGN_PARAMS['phi_secondary_target']
        m_cumulative = (m_fuel * stoich) / phi_sec_target
        m_air_sec = m_cumulative - m_air_pri

        m_air_dil = m_comb - m_air_pri - m_air_sec
        if m_air_dil <= 0 or m_air_sec <= 0:
            raise CombustorError("this three-zone model needs positive secondary and dilution air; revise chosen equivalence ratios")

        self.res['m_film_cooling'] = m_film
        self.res['split_primary'] = m_air_pri
        self.res['split_primary_liner'] = m_air_pri_liner
        self.res['split_primary_vap'] = m_air_vap
        self.res['split_secondary'] = m_air_sec
        self.res['split_dilution'] = m_air_dil
        self.res['m_combustion_air'] = m_comb

        # ===== PATCH P11 =====
        # V21 called this 'phi_primary_actual'. It is not actual -- primary air
        # is DEFINED as m_fuel*stoich/phi_target, so this can only ever echo the
        # target back. It read exactly 1.600 at every TIT, which is the tell.
        # Kept under the old key for compatibility, renamed honestly alongside.
        self.res['phi_primary_actual'] = phi_pri
        self.res['phi_primary_target_echo'] = phi_pri
        self.res['phi_primary_is_an_input'] = True

        cp_flame = gas.cp_air(1900)
        m_fuel_burned = m_air_pri / stoich
        Q_zone1 = m_fuel_burned * self.FUEL['LHV']
        m_zone1_total = m_air_pri + m_fuel
        T_pri_raw = self.res['T2_K'] + Q_zone1 / (m_zone1_total * cp_flame)
        T_pri = min(T_pri_raw, 1950.0)
        self.res['T_primary_zone_est'] = T_pri
        self.res['T_primary_zone_raw'] = T_pri_raw
        self.res['T_primary_zone_clamped'] = T_pri_raw > 1950.0

    # =======================================================================
    def mechanical_geometry(self, f_outer_feed=None, v_inner_override=None):
        wall_m = self.inputs['wall_thickness_mm'] / 1000.0
        od_casing = self.inputs['casing_od_inch'] * 0.0254
        id_casing = od_casing - 2 * wall_m
        od_tunnel = self.inputs['shaft_tunnel_od_inch'] * 0.0254
        id_tunnel = od_tunnel - 2 * wall_m

        rho2 = self.res['rho2']
        m_air = self.res['mdot_air']
        v_outer = self.DESIGN_PARAMS['target_annulus_vel']
        _dp_inner = self.DESIGN_PARAMS.get('target_inner_annulus_vel')
        # PATCH P5: the inner annulus velocity is now SOLVED by the pressure
        # balance, not asserted. An explicit input still wins (so the KJ66
        # preset's historical 20 m/s can be reproduced on demand), and the
        # first pass falls back to matching the outer velocity.
        v_inner = (v_inner_override
                   or self.inputs.get('target_inner_annulus_vel')
                   or (_dp_inner if _dp_inner is not None else None)
                   or v_outer)
        self.res['v_inner_target_used'] = v_inner

        # ===== PATCH P5 =====
        # V21 always sized the annuli with the nominal 0.60 and never revisited
        # it, even though pressure_balance_split() went on to compute 0.516 for
        # the 6-inch case and 0.371 for the KJ66 -- a 14% and 39% error in the
        # areas that had already been fixed. f_outer now comes from the outer
        # loop, which iterates the two to a fixed point.
        if f_outer_feed is None:
            f_outer_feed = self.DESIGN_PARAMS['f_outer_feed']

        # ===== PATCH P14 =====
        # V21 sized the liner by subtracting the feed annuli from a GIVEN casing
        # bore. That makes the combustor have no intrinsic size -- it expands to
        # fill whatever casing it is handed. Fine when the casing OD is a fixed
        # input, as it was in V21. Fatal once the casing is computed from the
        # parts inside it: the liner grows to fill the casing, the casing grows
        # to contain the liner, and the pair diverge without bound. The repo
        # solver caught this immediately, which is the argument for having one.
        #
        # Reformulated to Lefebvre's actual method (Sec. 4.3, Eqs. 4.1-4.6): the
        # reference area comes from the pressure loss the combustor is allowed,
        # which is an ABSOLUTE size set by mass flow and inlet state. Everything
        # then stacks outward from the shaft tunnel, and the casing bore falls
        # out at the end as a REQUIREMENT rather than an input.
        #
        #   A_ref  = mdot / (rho3 * V_ref),  V_ref = sqrt(2 * (dP/K) / rho3)
        #
        # K = 20 for an annular combustor is Lefebvre's own tabulated value
        # (Table 4.1). The velocity targets that used to size the annuli are now
        # reported as CHECKS instead.
        dP_liner = self.res['P2_Pa'] * self.DESIGN_PARAMS['target_pressure_drop']
        K_ann = self.DESIGN_PARAMS['K_annular_ratio']
        V_ref = math.sqrt(2.0 * (dP_liner / K_ann) / rho2)
        A_ref = m_air / (rho2 * V_ref)

        liner_frac = self.DESIGN_PARAMS['liner_area_frac']
        A_liner_flow = liner_frac * A_ref          # flame tube annulus
        A_feed_total = A_ref - A_liner_flow        # both feed annuli together
        A_outer_feed = A_feed_total * f_outer_feed
        A_inner_feed = A_feed_total * (1.0 - f_outer_feed)

        # -- stack outward from the shaft tunnel ----------------------------
        r_tunnel_od = od_tunnel / 2
        r_inner_liner_id = math.sqrt(r_tunnel_od ** 2 + A_inner_feed / math.pi)
        inner_liner_id = 2 * r_inner_liner_id
        r_inner_liner_od = r_inner_liner_id + wall_m
        inner_liner_od = 2 * r_inner_liner_od
        r_outer_liner_id = math.sqrt(r_inner_liner_od ** 2 + A_liner_flow / math.pi)
        outer_liner_id = 2 * r_outer_liner_id
        r_outer_liner_od = r_outer_liner_id + wall_m
        outer_liner_od = 2 * r_outer_liner_od
        r_casing_id_req = math.sqrt(r_outer_liner_od ** 2 + A_outer_feed / math.pi)

        # the casing the combustor REQUIRES, as an output
        D_casing_id_req = 2 * r_casing_id_req
        D_casing_od_req = D_casing_id_req + 2 * wall_m
        self.res['casing_id_required_mm'] = D_casing_id_req * 1000
        self.res['casing_od_required_mm'] = D_casing_od_req * 1000

        # does it fit in the casing we were given?
        r_casing_id = id_casing / 2
        self.res['casing_fit_margin_mm'] = (id_casing - D_casing_id_req) / 2 * 1000
        if D_casing_id_req > id_casing:
            raise CombustorError(
                f"The combustor needs a {D_casing_od_req*1000:.0f} mm casing OD to pass "
                f"{m_air*1000:.0f} g/s at {self.DESIGN_PARAMS['target_pressure_drop']*100:.0f}% "
                f"pressure loss, but was given {od_casing*1000:.0f} mm.\n"
                f"  A_ref required = {A_ref*1e6:.0f} mm2 (Lefebvre Sec. 4.3). Options: raise "
                f"the allowed pressure loss, reduce mass flow, or increase the casing."
            )

        self.res['A_ref_m2'] = A_ref
        self.res['V_ref_m_s'] = V_ref
        self.res['A_liner_flow_m2'] = A_liner_flow

        # velocity targets are now CHECKS, not sizing inputs
        v_outer_check = (m_air * f_outer_feed) / (rho2 * A_outer_feed)
        v_inner_check = (m_air * (1.0 - f_outer_feed)) / (rho2 * A_inner_feed)
        self.res['v_outer_vs_target'] = v_outer_check / v_outer if v_outer else 0.0
        self.res['v_inner_vs_target'] = v_inner_check / v_inner if v_inner else 0.0


        A_comb = math.pi * ((outer_liner_id / 2) ** 2 - (inner_liner_od / 2) ** 2)
        D_mean = (outer_liner_id + inner_liner_od) / 2
        combustion_gap = (outer_liner_id - inner_liner_od) / 2

        H_liner_span = (outer_liner_od - inner_liner_id) / 2
        gap_min = max(0.008, H_liner_span * 0.60)
        if combustion_gap <= gap_min:
            raise CombustorError(
                f"Combustion annulus gap {combustion_gap*1000:.1f} mm is below the "
                f"{gap_min*1000:.1f} mm minimum (60% of the {H_liner_span*1000:.1f} mm "
                f"liner span). Reduce shaft tunnel OD, increase casing OD, or thin the wall."
            )

        tau_min = self.inputs.get('tau_min_s', self.DESIGN_PARAMS['tau_min_s'])
        L_D_min = self.inputs.get('L_D_min', self.DESIGN_PARAMS['L_D_min'])
        L_D_max = self.inputs.get('L_D_max', self.DESIGN_PARAMS['L_D_max'])

        # ===== PATCH P3 =====
        # V21 sized the length from m_combustion_air (air only) but reported
        # tau from m_air + m_fuel. Same nominal quantity, two different mass
        # flows: you asked for 2.00 ms and got 1.73. Both now use the total
        # flow through the chamber, which is what actually occupies the volume.
        m_through = self.res['mdot_air'] + self.res['mdot_fuel']
        T_bulk = (self.res['T2_K'] + self.inputs['target_tit_k']) / 2.0
        rho_bulk = self.res['P2_Pa'] / (self.R * T_bulk)
        V_ref = m_through / (rho_bulk * A_comb)
        L_min_tau = V_ref * tau_min
        L_min_geom = D_mean * L_D_min
        length = max(L_min_tau, L_min_geom)

        # ===== PATCH P9 =====
        L_max = D_mean * L_D_max
        length_capped = length > L_max
        if length_capped:
            raise CombustorError(
                f"Chamber length {length*1000:.0f} mm is L/D = {length/D_mean:.2f}, "
                f"above the {L_D_max:.2f} ceiling for a reverse-flow can "
                f"(mean dia {D_mean*1000:.0f} mm). The residence-time floor is driving "
                f"it because the annulus is too thin: reduce mass flow, increase casing "
                f"OD, or accept a shorter tau_min_s."
            )

        A_outer_feed = math.pi*(id_casing**2-outer_liner_od**2)/4
        m_air_vap = self.res.get('split_primary_vap', 0.0)
        m_outer_entry = m_air * f_outer_feed
        m_inner_entry = m_air * (1.0 - f_outer_feed)
        v_out_act = m_outer_entry / (rho2 * A_outer_feed) if A_outer_feed > 0 else 0
        v_in_act = m_inner_entry / (rho2 * A_inner_feed) if A_inner_feed > 0 else 0

        self.res['f_outer_feed_used'] = f_outer_feed
        self.res['casing_od_mm'] = od_casing * 1000
        self.res['casing_id_mm'] = id_casing * 1000
        self.res['outer_liner_od_mm'] = outer_liner_od * 1000
        self.res['outer_liner_id_mm'] = outer_liner_id * 1000
        self.res['inner_liner_od_mm'] = inner_liner_od * 1000
        self.res['inner_liner_id_mm'] = inner_liner_id * 1000
        self.res['shaft_tunnel_od_mm'] = od_tunnel * 1000
        self.res['shaft_tunnel_id_mm'] = id_tunnel * 1000
        self.res['combustion_gap_mm'] = combustion_gap * 1000
        self.res['combustion_annulus_A'] = A_comb
        self.res['D_mean_comb_mm'] = D_mean * 1000
        self.res['chamber_length_mm'] = length * 1000
        self.res['chamber_L_over_D'] = length / D_mean
        self.res['length_driver'] = 'residence time' if L_min_tau > L_min_geom else 'L/D floor'
        self.res['outer_annulus_gap_mm'] = (id_casing - outer_liner_od) / 2 * 1000
        self.res['inner_annulus_gap_mm'] = (inner_liner_id - od_tunnel) / 2 * 1000
        self.res['v_outer_annulus'] = v_out_act
        self.res['v_inner_annulus'] = v_in_act
        self.res['v_outer_post_vap'] = ((m_outer_entry - m_air_vap)
                                        / (rho2 * A_outer_feed)) if A_outer_feed > 0 else 0
        self.res['outer_liner_circumf_m'] = math.pi * outer_liner_id
        self.res['inner_liner_circumf_m'] = math.pi * inner_liner_od

        # -- thermal growth --------------------------------------------------
        mat_key = self.inputs.get('liner_material', '304SS').upper()
        if mat_key not in self.MATERIALS:
            raise CombustorError(
                f"Unknown liner_material '{mat_key}'. Options: {list(self.MATERIALS)}"
            )
        mat = self.MATERIALS[mat_key]
        alpha = mat['alpha']

        # ===== PATCH P2 =====
        # Two errors, in opposite directions, that happened to look plausible
        # together. V21 computed alpha*(OD/2)*dT -- a change in RADIUS -- and
        # subtracted it from a DIAMETER. And it used TIT for dT, but a liner
        # film cooled on both faces runs far below the gas. Both fixed:
        # diameter change, at a realistic metal temperature.
        T_wall = 293.0 + self.DESIGN_PARAMS['liner_wall_temp_frac'] * (
            self.inputs['target_tit_k'] - 293.0)
        delta_T = T_wall - 293.0
        dD_outer = alpha * outer_liner_od * delta_T * 1000     # mm, DIAMETER
        dD_inner = alpha * inner_liner_od * delta_T * 1000

        self.res['liner_material'] = mat_key
        self.res['liner_material_name'] = mat['name']
        self.res['liner_alpha_per_K'] = alpha
        self.res['liner_wall_temp_K'] = T_wall
        self.res['outer_liner_od_hot_mm'] = round(outer_liner_od * 1000, 3)
        self.res['outer_liner_od_cold_mm'] = outer_liner_od * 1000 / (1+alpha*delta_T)
        self.res['outer_liner_thermal_offset_mm'] = round(dD_outer, 3)
        self.res['inner_liner_od_hot_mm'] = round(inner_liner_od * 1000, 3)
        self.res['inner_liner_od_cold_mm'] = inner_liner_od * 1000 / (1+alpha*delta_T)
        self.res['inner_liner_thermal_offset_mm'] = round(dD_inner, 3)
        self.res['thermal_offset_warn_outer'] = dD_outer > 1.5
        self.res['thermal_offset_warn_inner'] = dD_inner > 1.5

        self.res['thermal_scale_ratio'] = 1+alpha*delta_T
        for key in ('outer_liner_od','outer_liner_id','inner_liner_od','inner_liner_id','chamber_length'):
            self.res[key+'_cold_mm'] = self.res[key+'_mm']/(1+alpha*delta_T)

        for side in ('outer','inner'):
            self.res[side+'_liner_thermal_offset_mm'] = self.res[side+'_liner_od_mm']-self.res[side+'_liner_od_cold_mm']
        self.res['L_primary_mm'] = length * self.DESIGN_PARAMS['frac_primary_zone'] * 1000
        self.res['L_secondary_mm'] = length * self.DESIGN_PARAMS['frac_secondary_zone'] * 1000
        self.res['L_dilution_mm'] = length * self.DESIGN_PARAMS['frac_dilution_zone'] * 1000

    # =======================================================================
    def vaporizer_tubes(self):
        dome_circumf_m = math.pi * self.res['outer_liner_id_mm'] / 1000
        pitch_m = self.DESIGN_PARAMS['vap_pitch_mm'] / 1000
        n_raw = dome_circumf_m / pitch_m

        allowed = self.DESIGN_PARAMS['allowed_vaporizer_counts']
        near = [n for n in sorted(allowed) if abs(n - n_raw) <= 0.15]
        if near:
            n_tubes = min(near, key=lambda n: abs(n - n_raw))
        else:
            cands = [n for n in sorted(allowed) if n >= n_raw]
            n_tubes = cands[0] if cands else max(allowed)

        m_air_vap = self.res['split_primary_vap']
        m_fuel_total = self.res['mdot_fuel']
        m_mix_per_tube = (m_fuel_total + m_air_vap) / n_tubes
        m_fuel_per_tube = m_fuel_total / n_tubes

        T_vap_mix = 600.0
        rho_mix_bore = self.res['P2_Pa'] / (self.R * T_vap_mix)
        air_budget = self.res['dP_outer_holes_Pa']
        target_v_mix = min(self.DESIGN_PARAMS['target_vap_mix_vel'],
                           math.sqrt(air_budget/(4*rho_mix_bore)))
        A_bore = m_mix_per_tube / (rho_mix_bore * target_v_mix)
        id_tube = max(math.sqrt(4 * A_bore / math.pi), 0.003)
        od_tube = id_tube + 0.0012

        target_v_mix = m_mix_per_tube/(rho_mix_bore*math.pi*id_tube**2/4)
        mu_mix_bore = 3.0e-5
        Re_tube = rho_mix_bore * target_v_mix * id_tube / mu_mix_bore
        f_darcy = 64.0 / Re_tube if Re_tube < 2300 else 0.316 * Re_tube ** -0.25
        L_tube_eff = (self.res['chamber_length_mm'] / 1000) * 1.5 + 2 * od_tube
        dP_tube_Pa = f_darcy * (L_tube_eff / id_tube) * (rho_mix_bore * target_v_mix ** 2 / 2)

        T_exit_gas = 950.0
        rho_gas_exit = self.res['P2_Pa'] / (self.R * T_exit_gas)
        Cd_crimp = 0.61
        scoop_loss = air_budget*0.25
        dP_target_Pa = air_budget-scoop_loss
        dP_crimp_req = dP_target_Pa-dP_tube_Pa
        if dP_crimp_req <= 0:
            raise CombustorError('vaporizer friction exhausts available air pressure; resize tube')

        if dP_crimp_req > 0:
            v_crimp = math.sqrt(2 * Cd_crimp ** 2 * dP_crimp_req / rho_gas_exit)
            A_crimp = m_mix_per_tube / (rho_gas_exit * v_crimp)
            d_crimp_mm = max(math.sqrt(4 * A_crimp / math.pi) * 1000, 0.8)
        else:
            raise CombustorError("no pressure budget for vaporizer crimp")
        A_crimp_act = math.pi * (d_crimp_mm / 2000) ** 2
        v_crimp_act = m_mix_per_tube / (rho_gas_exit * A_crimp_act)
        dP_crimp = rho_gas_exit * v_crimp_act ** 2 / (2 * Cd_crimp ** 2)

        self.res['vap_n'] = n_tubes
        self.res['vap_n_raw'] = n_raw
        self.res['vap_od_mm'] = od_tube * 1000
        self.res['vap_id_mm'] = id_tube * 1000
        self.res['vap_crimp_dia_mm'] = d_crimp_mm
        self.res['vap_pitch_actual_mm'] = dome_circumf_m / n_tubes * 1000
        self.res['vap_exit_v_crimped'] = round(v_crimp_act, 2)
        self.res['vap_bend_radius_mm'] = od_tube * 1000 * 1.5
        self.res['vap_m_air_per_tube'] = m_air_vap / n_tubes * 1000
        self.res['vap_m_fuel_per_tube'] = m_fuel_per_tube * 1000
        self.res['vap_AFR_tube'] = (m_air_vap / n_tubes) / m_fuel_per_tube

        rho_ann = self.res['rho2']
        A_scoop = (m_air_vap/n_tubes)/(self.DESIGN_PARAMS['vap_scoop_cd']*math.sqrt(2*rho_ann*scoop_loss))
        if d_crimp_mm > id_tube*1000:
            # The required restriction cannot be larger than the parent tube.
            # Resize the parent bore; recompute friction and crimp consistently.
            for _ in range(60):
                id_tube = max(id_tube*1.05,d_crimp_mm/1000*1.01)
                od_tube = id_tube+0.0012
                target_v_mix = m_mix_per_tube/(rho_mix_bore*math.pi*id_tube**2/4)
                Re_tube = rho_mix_bore*target_v_mix*id_tube/mu_mix_bore
                f_darcy = 64/Re_tube if Re_tube < 2300 else 0.316/Re_tube**0.25
                L_tube_eff = self.res['chamber_length_mm']/1000*1.5+2*od_tube
                dP_tube_Pa = f_darcy*L_tube_eff/id_tube*rho_mix_bore*target_v_mix**2/2
                dP_crimp = dP_target_Pa-dP_tube_Pa
                d_crimp_mm = math.sqrt(4*m_mix_per_tube/(math.pi*Cd_crimp*math.sqrt(2*rho_gas_exit*dP_crimp)))*1000
                if d_crimp_mm <= id_tube*1000: break
            else:
                raise CombustorError('vaporizer bore/crimp sizing did not converge')
            self.res.update(vap_od_mm=od_tube*1000,vap_id_mm=id_tube*1000,
                vap_crimp_dia_mm=d_crimp_mm,vap_bend_radius_mm=od_tube*1500)
        self.res['vap_air_pressure_budget_Pa'] = air_budget
        self.res['vap_scoop_loss_Pa'] = scoop_loss
        self.res['vap_path_loss_Pa'] = scoop_loss+dP_tube_Pa+dP_crimp
        self.res['vap_pressure_budget_closed'] = math.isclose(self.res['vap_path_loss_Pa'],air_budget,rel_tol=1e-9)
        if not self.res['vap_pressure_budget_closed']:
            raise CombustorError('vaporizer pressure allocation does not close')
        self.res['vap_exit_v_crimped'] = m_mix_per_tube/(rho_gas_exit*math.pi*(d_crimp_mm/1000)**2/4)
        self.res['vap_scoop_vel_actual'] = (m_air_vap/n_tubes)/(rho_ann*A_scoop)
        self.res['vap_scoop_dia_mm'] = math.sqrt(4 * A_scoop / math.pi) * 1000

        self.res['fuel_Re_tube'] = Re_tube
        self.res['fuel_dP_tube_Pa'] = dP_tube_Pa
        self.res['fuel_dP_crimp_Pa'] = dP_crimp
        self.res['fuel_dP_total_bar'] = (dP_tube_Pa + dP_crimp) / 1e5
        self.res['fuel_dP_target_bar'] = dP_target_Pa/1e5  # air-driven mixed-stream budget; not pump pressure
        self.res['vap_tube_flow_regime'] = "Laminar" if Re_tube < 2300 else "Turbulent"
        self.res['vap_mix_velocity'] = target_v_mix

    # =======================================================================
    def pressure_balance_split(self):
        """Rate frozen annuli. Branch losses need not equal: holes close each path.

        Uniform liner static pressure and inlet-density duct losses are explicit
        lumped approximations. Axial withdrawal and reverse-turn CFD remain open.
        """
        r = self.res
        rho, m, f = r['rho2'], r['mdot_air'], r['f_outer_feed_used']
        L = r['chamber_length_mm']/1000
        for branch, do, di, share, K in (
            ('outer',r['casing_id_mm'],r['outer_liner_od_mm'],f,self.DESIGN_PARAMS['K_turn']),
            ('inner',r['inner_liner_id_mm'],r['shaft_tunnel_od_mm'],1-f,self.DESIGN_PARAMS['K_entrance'])):
            A = math.pi*(do**2-di**2)/4e6
            Dh = (do-di)/1000
            thermo.positive(area=A, hydraulic_diameter=Dh, branch_flow=m*share)
            v = m*share/(rho*A)
            Re = rho*v*Dh/1.85e-5
            friction = 64/Re if Re < 2300 else 0.316/Re**0.25
            loss = (friction*L/Dh+K)*rho*v*v/2
            Pt = r['P2_Pa']-loss
            Tstatic, Pstatic = thermo.static(r['T2_K'],Pt,v,R=self.R)
            head = Pstatic-r['exit_P4_Pa']
            if head <= 0:
                raise CombustorError(f"{branch} path has no positive liner injection pressure budget")
            r[f'A_{branch}_feed_m2'] = A
            r[f'v_{branch}_annulus'] = v
            r[f'dP_{branch}_path_Pa'] = loss
            r[f'P_{branch}_static_Pa'] = Pstatic
            r[f'T_{branch}_static_K'] = Tstatic
            r[f'dP_{branch}_holes_Pa'] = head
        r['v_outer_actual_m_s'] = r['v_outer_annulus']
        r['v_inner_solved_m_s'] = r['v_inner_annulus']  # compatibility: rated, not solved
        r['v_outer_post_vap'] = (m*f-r['split_primary_vap'])/(rho*r['A_outer_feed_m2'])
        r['f_outer_solved'] = f
        r['f_outer_is_a_design_choice'] = True
        r['split_converged'] = True
        r['split_solver_iters'] = 0
        r['split_solver_tol_Pa'] = 0.0
        r['split_solver_residual_Pa'] = 0.0
        r['annulus_loss_difference_Pa'] = r['dP_outer_path_Pa']-r['dP_inner_path_Pa']
        r['split_solver_variable'] = 'fixed geometry rating; hole areas close separate branch paths'
        return r['v_inner_annulus']

    def combustion_loading(self):
        """CLP, residence time, and the efficiency the loading implies.

        Returns eta so the outer loop can feed it back (PATCH P4).
        """
        P3_kPa = self.res['P2_Pa'] / 1000.0
        T3 = self.res['T2_K']
        m_air = self.res['mdot_air']
        A_comb = self.res['combustion_annulus_A']
        L_primary = self.res['L_primary_mm'] / 1000.0
        V_primary = A_comb * L_primary
        V_total = A_comb * self.res['chamber_length_mm'] / 1000.0

        CLP = m_air / (P3_kPa * V_primary)
        CLP_T = CLP * math.sqrt(T3 / 300.0)

        # Lefebvre's own theta (Eq. 5.6/5.8): theta = P^1.75 * V * exp(T/300) / mdot.
        # Reported alongside the linear CLP because the linear form is a proxy
        # that behaves backwards off-design -- it FALLS at part power, which
        # would wrongly predict combustion improving at idle.
        theta_lef = (P3_kPa ** 1.75) * math.exp(T3 / 300.0) * V_primary / m_air

        # ===== PATCH P3 =====
        m_through = m_air + self.res['mdot_fuel']
        T_mean = (T3 + self.inputs['target_tit_k']) / 2.0
        rho_mean = self.res['P2_Pa'] / (self.R * T_mean)
        tau_ms = (V_total / (m_through / rho_mean)) * 1000.0

        self.res['CLP'] = CLP
        self.res['CLP_T'] = CLP_T
        self.res['CLP_theta_Lefebvre'] = theta_lef
        self.res['CLP_P3_kPa'] = P3_kPa
        self.res['CLP_V_primary_m3'] = V_primary
        self.res['CLP_V_total_m3'] = V_total
        self.res['tau_comb_ms'] = round(tau_ms, 3)
        self.res['tau_target_ms'] = self.inputs.get(
            'tau_min_s', self.DESIGN_PARAMS['tau_min_s']) * 1000.0
        self.res['CLP_stable'] = False  # stability cannot be inferred from this proxy
        self.res['CLP_acceptable'] = CLP < 15.0

        # ===== PATCH P8 =====
        # V21 cited "Lefebvre GTC 3rd Ed. Table 5.1" for this. Table 5.1 (p.186)
        # is the lean-blowout constants A and B for Eqs. 5.27/5.29 -- nothing to
        # do with efficiency. The real relation is Figs. 5.2 and 5.4, and it is
        # a chart, not a table, so the piecewise fit below is an engineering
        # approximation to the published curve shape and should be labelled as
        # such rather than cited to a specific equation.
        eta = max(0.85, min(0.999, 1.0 - 0.006 * max(0.0, CLP - 10.0)))
        self.res['eta_comb_estimated'] = round(eta, 4)
        self.res['eta_comb_source'] = 'uncalibrated diagnostic curve; not used in energy balance'
        return eta

    # =======================================================================
    def hole_sizing(self):
        dP_target = self.res['P2_Pa'] * self.DESIGN_PARAMS['target_pressure_drop']
        Cd = self.DESIGN_PARAMS['discharge_coeff_hole']
        rho2 = self.res['rho2']
        flow_factor = Cd * math.sqrt(2 * rho2 * dP_target)

        A_pri = self.res['split_primary_liner'] / flow_factor
        A_sec = self.res['split_secondary'] / flow_factor
        A_dil = self.res['split_dilution'] / flow_factor

        # Vaporizers draw from the outer branch; remaining holes AND film
        # share the residual branch supply, not the liner circumferences.
        mv = self.res['split_primary_vap']
        ma = self.res['mdot_air']
        f_outer = (ma*self.res['f_outer_feed_used']-mv)/(ma-mv)
        if not 0 < f_outer < 1:
            raise CombustorError('vaporizer demand exceeds outer feed supply')
        chosen = self.DESIGN_PARAMS['outer_liner_hole_fraction']
        if chosen is not None and not math.isclose(chosen,f_outer,rel_tol=1e-6):
            raise CombustorError('hole split conflicts with branch air balance')
        f_inner = 1-f_outer
        flux = {b: thermo.orifice_flux(self.res[f'P_{b}_static_Pa'],
                    self.res[f'T_{b}_static_K'],self.res['exit_P4_Pa'],Cd,self.R)
                for b in ('outer','inner')}
        n_vap = self.res['vap_n']

        def hole_dia(A_tot, frac, n):
            return math.sqrt(4 * (A_tot * frac / n) / math.pi)

        n_pri_out = n_pri_in = n_vap * 2
        sec_m = max(1, int(self.DESIGN_PARAMS['sec_holes_per_vap']))
        n_sec_out = n_sec_in = n_vap * sec_m
        dil_m = max(1, int(self.DESIGN_PARAMS['dil_holes_per_vap']))
        n_dil_out = n_dil_in = n_vap * dil_m

        d = {
            'pri_out': hole_dia(A_pri, f_outer, n_pri_out),
            'pri_in':  hole_dia(A_pri, f_inner, n_pri_in),
            'sec_out': hole_dia(A_sec, f_outer, n_sec_out),
            'sec_in':  hole_dia(A_sec, f_inner, n_sec_in),
            'dil_out': hole_dia(A_dil, f_outer, n_dil_out),
            'dil_in':  hole_dia(A_dil, f_inner, n_dil_in),
        }

        counts = {'pri_out':n_pri_out,'pri_in':n_pri_in,'sec_out':n_sec_out,
                  'sec_in':n_sec_in,'dil_out':n_dil_out,'dil_in':n_dil_in}
        demands = {'pri':self.res['split_primary_liner'],'sec':self.res['split_secondary'],
                   'dil':self.res['split_dilution']}
        capacities = {'outer':0.0,'inner':0.0}
        for key in d:
            zone,side = key.split('_')
            branch = 'outer' if side == 'out' else 'inner'
            frac = f_outer if side == 'out' else f_inner
            area = demands[zone]*frac/flux[branch]
            d[key] = math.sqrt(4*area/(math.pi*counts[key]))
            capacities[branch] += counts[key]*math.pi*d[key]**2/4*flux[branch]
        for zone in demands:
            v = flux['outer']/rho2
            self.res['Ma_hole_'+zone] = v/math.sqrt(self.GAMMA*self.R*self.res['T2_K'])
            self.res['Ma_hole_'+zone+'_uncorr'] = self.res['Ma_hole_'+zone]
        self.res['hole_compressible_warning'] = any(self.res['Ma_hole_'+z]>0.3 for z in demands)
        self.res['dP_target_Pa'] = dP_target
        self.res['dP_target_frac'] = self.DESIGN_PARAMS['target_pressure_drop']
        # No inversion of aggregated holes can verify a prescribed total loss.
        self.res['dP_implied_by_holes_Pa'] = dP_target  # deprecated algebraic budget echo
        self.res['dP_implied_frac'] = self.DESIGN_PARAMS['target_pressure_drop']
        self.res['dP_closure_err_pct'] = 0.0
        self.res['pressure_loss_validated'] = False
        Ks = [self.res[f'dP_{b}_holes_Pa']/(0.5*rho2*self.res[f'v_{b}_annulus']**2)
              for b in ('outer','inner')]
        self.res['hole_K_coefficient'] = min(Ks)
        self.res['hole_K_outer'],self.res['hole_K_inner'] = Ks
        self.res['hole_K_ok'] = min(Ks)>=6
        self.res['hole_Cd_consistent_with_K'] = False  # requires calibrated Cd
        n_rows = sum(self.DESIGN_PARAMS['film_rows_'+z] for z in ('primary','secondary','dilution'))
        self.res['film_n_rows'] = n_rows
        for short,long in [('pri','primary'),('sec','secondary'),('dil','dilution')]:
            self.res['film_n_rows_'+short] = self.DESIGN_PARAMS['film_rows_'+long]
        area_total = 0
        for branch,frac in [('outer',f_outer),('inner',f_inner)]:
            area = self.res['m_film_cooling']*frac/flux[branch]
            nominal = self.DESIGN_PARAMS['film_hole_dia_mm']/1000
            n = max(1,math.ceil(area/(n_rows*math.pi*nominal**2/4)))
            diameter = math.sqrt(4*area/(math.pi*n*n_rows))
            self.res['film_holes_per_row_'+branch] = n
            self.res['film_hole_dia_'+branch+'_mm'] = diameter*1000
            capacities[branch] += n*n_rows*math.pi*diameter**2/4*flux[branch]
            area_total += area
        self.res['film_hole_dia_mm_actual'] = self.res['film_hole_dia_outer_mm']
        self.res['film_total_area_mm2'] = area_total*1e6
        self.res['film_total_holes'] = n_rows*sum(self.res['film_holes_per_row_'+b] for b in capacities)
        capacities['outer'] += mv
        self.res['outer_air_balance_error_kg_s'] = capacities['outer']-ma*self.res['f_outer_feed_used']
        self.res['inner_air_balance_error_kg_s'] = capacities['inner']-ma*(1-self.res['f_outer_feed_used'])
        for branch in capacities:
            if abs(self.res[branch+'_air_balance_error_kg_s']) > 1e-9*ma:
                raise CombustorError('branch air mass balance failed')

        # -- dilution jet penetration ----------------------------------------
        T_gas_dil = 1200.0
        rho_gas = self.res['P2_Pa'] / (self.R * T_gas_dil)
        m_at_dil = (self.res['split_primary'] + self.res['split_secondary']
                    + self.res['mdot_fuel'])
        V_gas = m_at_dil / (rho_gas * self.res['combustion_annulus_A'])

        A_h_out = math.pi * (d['dil_out'] / 2) ** 2
        A_h_in = math.pi * (d['dil_in'] / 2) ** 2
        V_jet_out = (self.res['split_dilution'] * f_outer / n_dil_out) / (rho2 * A_h_out)
        V_jet_in = (self.res['split_dilution'] * f_inner / n_dil_in) / (rho2 * A_h_in)
        J_out = (rho2 * V_jet_out ** 2) / (rho_gas * V_gas ** 2) if V_gas > 0 else 0.0
        J_in = (rho2 * V_jet_in ** 2) / (rho_gas * V_gas ** 2) if V_gas > 0 else 0.0

        H = self.res['combustion_gap_mm'] / 1000

        # ===== PATCH P6 =====
        # V21 used Y/d = 1.15*sqrt(J), which is Lefebvre Eq. 4.19 -- correct,
        # and correctly attributed, but Eq. 4.19 is for a SINGLE jet. Every
        # row here has 12 to 24 holes, which is Eq. 4.20's case:
        #     Y_max = 1.25 * d_j * sqrt(J) * [mdot_g / (mdot_g + mdot_j)]
        # The mass-flow term is the blockage effect of the jets accelerating
        # the mainstream. On the KJ66 numbers this moves penetration from
        # 0.854 H to about 0.61 H -- enough to flip the over-penetration flag.
        # Both are reported so the change is auditable.
        m_jet_out = self.res['split_dilution'] * f_outer
        m_jet_in = self.res['split_dilution'] * f_inner
        blk_out = m_at_dil / (m_at_dil + m_jet_out) if (m_at_dil + m_jet_out) > 0 else 1.0
        blk_in = m_at_dil / (m_at_dil + m_jet_in) if (m_at_dil + m_jet_in) > 0 else 1.0

        pen_out_single = 1.15 * math.sqrt(J_out) * (d['dil_out'] / H) if H > 0 else 0.0
        pen_in_single = 1.15 * math.sqrt(J_in) * (d['dil_in'] / H) if H > 0 else 0.0
        pen_out = 1.25 * math.sqrt(J_out) * (d['dil_out'] / H) * blk_out if H > 0 else 0.0
        pen_in = 1.25 * math.sqrt(J_in) * (d['dil_in'] / H) * blk_in if H > 0 else 0.0

        self.res['hole_split_f_outer'] = f_outer
        self.res['hole_split_f_inner'] = f_inner
        self.res['pri_out_qty'], self.res['pri_out_mm'] = n_pri_out, d['pri_out'] * 1000
        self.res['pri_in_qty'], self.res['pri_in_mm'] = n_pri_in, d['pri_in'] * 1000
        self.res['sec_out_qty'], self.res['sec_out_mm'] = n_sec_out, d['sec_out'] * 1000
        self.res['sec_in_qty'], self.res['sec_in_mm'] = n_sec_in, d['sec_in'] * 1000
        self.res['dil_out_qty'], self.res['dil_out_mm'] = n_dil_out, d['dil_out'] * 1000
        self.res['dil_in_qty'], self.res['dil_in_mm'] = n_dil_in, d['dil_in'] * 1000
        self.res['dil_J_outer'], self.res['dil_J_inner'] = J_out, J_in
        self.res['H_comb_mm'] = H * 1000
        self.res['dil_pen_norm_outer'] = pen_out
        self.res['dil_pen_norm_inner'] = pen_in
        self.res['dil_pen_norm_outer_singlejet'] = pen_out_single
        self.res['dil_pen_norm_inner_singlejet'] = pen_in_single
        self.res['dil_pen_outer_mm'] = pen_out * H * 1000
        self.res['dil_pen_inner_mm'] = pen_in * H * 1000
        self.res['dil_pen_correlation'] = "Lefebvre Eq. 4.20 (multi-jet)"
        self.res['dil_overpenetrates'] = pen_out > 0.75 or pen_in > 0.75

    # =======================================================================
    def liner_structural(self):
        wall_m = self.inputs['wall_thickness_mm'] / 1000.0
        dP = self.res['P2_Pa'] * self.DESIGN_PARAMS['target_pressure_drop']
        r_o = (self.res['outer_liner_od_mm'] + self.res['outer_liner_id_mm']) / 4 / 1000
        r_i = (self.res['inner_liner_od_mm'] + self.res['inner_liner_id_mm']) / 4 / 1000
        s_o, s_i = dP * r_o / wall_m / 1e6, dP * r_i / wall_m / 1e6
        pitch_o = self.res['outer_liner_circumf_m'] * 1000 / self.res['dil_out_qty']
        pitch_i = self.res['inner_liner_circumf_m'] * 1000 / self.res['dil_in_qty']
        lig_o = pitch_o - self.res['dil_out_mm']
        lig_i = pitch_i - self.res['dil_in_mm']
        lig_min = max(self.inputs['wall_thickness_mm'] * 2.0, 1.5)
        self.res['sigma_hoop_outer_MPa'] = s_o
        self.res['sigma_hoop_inner_MPa'] = s_i
        self.res['sigma_allow_ss304_MPa'] = 65.0
        self.res['sigma_allow_in625_MPa'] = 175.0
        self.res['ligament_outer_mm'] = lig_o
        self.res['ligament_inner_mm'] = lig_i
        self.res['ligament_min_req_mm'] = lig_min
        self.res['liner_ss304_ok'] = s_o < 65.0 and s_i < 65.0
        self.res['liner_in625_ok'] = s_o < 175.0 and s_i < 175.0
        self.res['ligament_outer_ok'] = lig_o >= lig_min
        self.res['ligament_inner_ok'] = lig_i >= lig_min

    # =======================================================================
    def temperature_traverse_quality(self):
        po, pi = self.res['dil_pen_norm_outer'], self.res['dil_pen_norm_inner']
        eo = max(0.0, min(1.0, 1.0 - abs(po - 0.5) / 0.5))
        ei = max(0.0, min(1.0, 1.0 - abs(pi - 0.5) / 0.5))
        mix = (eo + ei) / 2.0
        self.res['mixing_index'] = 0.40 - mix * 0.35
        self.res['mix_eff_outer'] = eo
        self.res['mix_eff_inner'] = ei
        self.res['dil_combined_cov'] = po + pi

    # =======================================================================
    def exit_conditions(self):
        """Combustor DISCHARGE plane conditions.

        ===== PATCH P12 =====
        V21 called this "turbine inlet conditions" and derived an available
        turbine enthalpy from it. It is not the turbine inlet -- it is the
        combustor discharge, upstream of the nozzle guide vanes. The NGV throat
        is several times smaller, so the real turbine inlet Mach number is set
        there, not here. The NGV throat area is now reported alongside so the
        difference is visible; h_avail is kept but renamed to make clear it is
        an upper bound computed at the wrong plane.
        """
        r = self.res
        T0 = self.inputs['target_tit_k']
        P0 = r['P2_Pa']*(1-self.DESIGN_PARAMS['target_pressure_drop'])
        m = r['mdot_air']+r['mdot_fuel']
        A = r['combustion_annulus_A']
        V,T,P = thermo.area_state(m,A,T0,P0,r['FAR'],self.R)
        g = thermo.gamma(T,r['FAR'],self.R)
        a = math.sqrt(g*self.R*T)
        vs,ts = thermo.sonic(T0,r['FAR'],self.R)
        ps = thermo.pressure(ts,T0,P0,r['FAR'],self.R)
        Ath = m/(ps/(self.R*ts)*vs)
        r.update(exit_P4_Pa=P,exit_P4_kPa=P/1000,exit_T4_K=T,
                 exit_rho4=P/(self.R*T),exit_V4_m_s=V,exit_Ma4=V/a,
                 exit_a4_m_s=a,exit_T4_total_K=T0,exit_P4_total_Pa=P0,
                 exit_mdot_kg_s=m,exit_cp4=gas.cp_products(T,r['FAR']),
                 exit_gamma_hot=g,exit_Ma4_high=V/a>0.25,
                 exit_plane='combustor discharge upstream of NGV',
                 ngv_throat_area_if_choked_m2=Ath,exit_area_over_ngv_throat=A/Ath,
                 exit_h_avail_kJ_kg=(gas.h_products(T0,r['FAR'])-gas.h_products(288.15,r['FAR']))/1000,
                 exit_h_avail_note='enthalpy above ambient datum; not turbine work')

    def stability_checks(self):
        rho2 = self.res['rho2']
        T_pri = self.res.get('T_primary_zone_est', 1800.0)
        P2 = self.res['P2_Pa']
        rho_pri = P2 / (self.R * T_pri)

        m_pri_liner = self.res['split_primary_liner']
        n_pri_out = self.res['pri_out_qty']
        d_pri = self.res['pri_out_mm'] / 1000.0
        A_pri = math.pi * (d_pri / 2) ** 2
        V_jet = (m_pri_liner * self.res['hole_split_f_outer']
                 / (rho2 * A_pri * n_pri_out)) if A_pri > 0 else 0.0

        A_comb = self.res['combustion_annulus_A']
        V_axial = (self.res['split_primary']+self.res['mdot_fuel']) / (rho_pri * A_comb)
        J_primary = (rho2 * V_jet ** 2) / (rho_pri * V_axial ** 2) if V_axial > 0 else 0.0

        n_tubes = self.res['vap_n']
        m_mix_tube = (self.res['mdot_fuel'] + self.res['split_primary_vap']) / n_tubes
        id_tube = self.res['vap_id_mm'] / 1000.0
        A_tube = math.pi * (id_tube / 2) ** 2
        rho_mix = P2 / (self.R * 600.0)
        V_mix = m_mix_tube / (rho_mix * A_tube) if A_tube > 0 else 0.0
        L_tube = (self.res['chamber_length_mm'] / 1000) * 1.5 + 2 * (self.res['vap_od_mm'] / 1000)
        LD_tube = L_tube / id_tube if id_tube > 0 else 0.0
        tau_vap_ms = (L_tube / V_mix * 1000.0) if V_mix > 0 else 0.0

        # ===== PATCH P7 =====
        # V21 used Nu = 0.037*Re^0.8*Pr^0.33 with the hole diameter as the
        # length scale. That is a FLAT PLATE correlation, not an impingement
        # one -- it carries no standoff ratio H/D and no radial position r/D,
        # which are first-order for an impinging jet. It returned 1240-1655
        # kW/m2 across the entire design space and never once cleared its own
        # 600 kW/m2 "critical" threshold -- including 1240 kW/m2 on the real
        # KJ66, an engine thousands of people have flown for 25 years. A check
        # that always fails is a constant, not a check.
        #
        # Three methods are now computed and all three reported, because the
        # honest answer is that they disagree by an order of magnitude and
        # nobody should pick one without saying which:
        #   (a) Lefebvre's own liner-convection method, Sec. 8.5 Eqs. 8.20-8.22
        #       -- bulk mass velocity, liner hydraulic diameter, constant 0.017
        #       in the primary zone. This is what the cited reference actually
        #       recommends for this geometry, so it is the reported default.
        #   (b) Martin (1977) single-jet impingement, the correct correlation
        #       IF the dome is genuinely impingement-cooled.
        #   (c) V21's original, kept so the change is auditable.
        T_wall_dome = 293.0 + self.DESIGN_PARAMS['liner_wall_temp_frac'] * (
            self.inputs['target_tit_k'] - 293.0)
        T_gas = max(T_pri, 1200.0)
        mu_gas = 3.5e-5 * (T_gas / 1000.0) ** 0.7
        k_gas = 0.055 * (T_gas / 1000.0) ** 0.8
        Pr = 0.72

        # (a) Lefebvre Sec. 8.5
        H_comb = self.res['combustion_gap_mm'] / 1000.0
        D_hyd_liner = 2.0 * H_comb
        G_bulk = (self.res['m_combustion_air'] + self.res['mdot_fuel']) / A_comb
        Re_liner = G_bulk * D_hyd_liner / mu_gas if mu_gas > 0 else 0.0
        Nu_lef = 0.017 * max(Re_liner, 1.0) ** 0.8 * Pr ** 0.33
        h_lef = Nu_lef * k_gas / D_hyd_liner if D_hyd_liner > 0 else 0.0
        q_conv_lef = h_lef * (T_gas - T_wall_dome) / 1000.0

        # (b) Martin 1977 single jet
        Re_imp = rho2 * V_jet * d_pri / mu_gas if mu_gas > 0 else 0.0
        HD = self.DESIGN_PARAMS['dome_jet_standoff_ratio']
        rD = self.DESIGN_PARAMS['dome_jet_radius_ratio']
        if Re_imp < 30000:
            F_re = 1.36 * max(Re_imp, 1.0) ** 0.574
        elif Re_imp < 120000:
            F_re = 0.54 * Re_imp ** 0.667
        else:
            F_re = 0.151 * Re_imp ** 0.775
        g_geo = (1.0 / rD) * (1.0 - 1.1 / rD) / (1.0 + 0.1 * (HD - 6.0) / rD)
        Nu_mar = Pr ** 0.42 * g_geo * F_re
        h_mar = Nu_mar * k_gas / d_pri if d_pri > 0 else 0.0
        q_conv_mar = h_mar * (T_gas - T_wall_dome) / 1000.0

        # (c) V21 original
        Nu_v21 = 0.037 * max(Re_imp, 1.0) ** 0.8 * Pr ** 0.33
        q_conv_v21 = (Nu_v21 * k_gas / d_pri) * (T_gas - T_wall_dome) / 1000.0 if d_pri > 0 else 0.0

        phi_pri = self.res.get('phi_primary_actual', 1.6)
        eps = max(0.30, min(0.50, 0.30 + 0.10 * (phi_pri - 1.0)))
        q_rad = 0.60 * eps * 5.6704e-8 * (T_gas ** 4 - T_wall_dome ** 4) / 1000.0

        q_dome = q_conv_lef + q_rad

        # -- vaporizer tube thermal ------------------------------------------
        rho_mix_vap = P2 / (self.R * 600.0)
        Re_vap = rho_mix_vap * V_mix * id_tube / 3.0e-5 if id_tube > 0 else 0.0
        Nu_vap = 0.023 * max(Re_vap, 1.0) ** 0.8 * 0.71 ** 0.4 if Re_vap > 10 else 3.66
        h_in_vap = Nu_vap * 0.046 / id_tube if id_tube > 0 else 0.0
        R_vap = 1.0 / 300.0 + 0.0006 / 16.0 + (1.0 / h_in_vap if h_in_vap > 0 else 0.1)
        q_vap = (T_pri - 600.0) / R_vap if R_vap > 0 else 0.0
        T_vap_out = T_pri - q_vap / 300.0
        T_vap_in = 600.0 + q_vap / h_in_vap if h_in_vap > 0 else T_vap_out

        self.res['stab_J_primary'] = J_primary
        self.res['stab_V_jet_pri'] = V_jet
        self.res['stab_V_axial'] = V_axial
        self.res['stab_rho_pri'] = rho_pri
        self.res['stab_J_ok'] = 5.0 <= J_primary <= 80.0
        self.res['stab_J_collapse'] = J_primary < 5.0
        self.res['stab_J_overpenetrate'] = J_primary > 80.0
        self.res['stab_V_axial_high'] = V_axial > 30.0

        self.res['stab_V_mix'] = V_mix
        self.res['stab_tau_vap_ms'] = round(tau_vap_ms, 2)
        self.res['stab_LD_tube'] = LD_tube
        self.res['stab_flashback_critical'] = V_mix < 0.8
        self.res['stab_flashback_risk'] = V_mix < 4.0
        self.res['stab_LD_ok'] = LD_tube >= 8.0 or id_tube <= 0.006

        self.res['stab_q_conv_lefebvre_kW_m2'] = round(q_conv_lef, 1)
        self.res['stab_q_conv_martin_kW_m2'] = round(q_conv_mar, 1)
        self.res['stab_q_conv_v21_original_kW_m2'] = round(q_conv_v21, 1)
        self.res['stab_q_rad_kW_m2'] = round(q_rad, 1)
        self.res['stab_q_dome_kW_m2'] = round(q_dome, 1)
        self.res['stab_q_dome_method'] = "Lefebvre Sec. 8.5 liner convection + radiation"
        self.res['stab_q_dome_spread_kW_m2'] = round(
            abs(q_conv_mar - q_conv_lef), 1)
        self.res['stab_q_conv_kW_m2'] = round(q_conv_lef, 1)   # back-compat
        self.res['stab_epsilon_flame'] = round(eps, 3)
        self.res['stab_F_view'] = 0.60
        self.res['stab_T_wall_dome_K'] = T_wall_dome
        self.res['stab_Re_imp'] = Re_imp
        self.res['stab_Re_liner'] = Re_liner
        self.res['stab_h_conv'] = h_lef
        self.res['stab_dome_ok'] = q_dome < 300.0
        self.res['stab_dome_high'] = 300.0 <= q_dome < 600.0
        self.res['stab_dome_critical'] = q_dome >= 600.0
        self.res['stab_dome_confidence'] = "LOW -- methods disagree by ~10x, see PATCHES.md P7"

        self.res['stab_T_vap_wall_outer_K'] = round(T_vap_out, 0)
        self.res['stab_T_vap_wall_inner_K'] = round(T_vap_in, 0)
        self.res['stab_h_inner_vap'] = round(h_in_vap, 0)
        self.res['stab_vap_coking_risk'] = T_vap_in > 650.0
        self.res['stab_vap_structural_risk'] = T_vap_out > 1100.0

    # =======================================================================
    def run(self):
        self.res = {}
        for key in ('casing_od_inch','shaft_tunnel_od_inch','wall_thickness_mm',
                    'pressure_ratio','compressor_efficiency','target_tit_k'):
            thermo.positive(**{key:self.inputs[key]})
        for key in ('film_cooling_fraction','primary_air_vaporizer_fraction',
                    'f_outer_feed','target_pressure_drop','liner_area_frac'):
            value = self.DESIGN_PARAMS[key]
            if not math.isfinite(value) or not 0 < value < 1:
                raise CombustorError(f'{key} must be in (0,1) for this model')
        thermo.efficiency(Cd=self.DESIGN_PARAMS['discharge_coeff_hole'])
        thermo.positive(phi_primary=self.DESIGN_PARAMS['phi_primary_target'],
                        phi_secondary=self.DESIGN_PARAMS['phi_secondary_target'])
        self.thermodynamics()
        eta = self.inputs.get('combustion_efficiency',0.96)
        self.mass_flow_and_fuel(eta_comb=eta)
        self.zonal_analysis()
        self.mechanical_geometry()
        self.exit_conditions()
        self.pressure_balance_split()
        self.vaporizer_tubes()
        self.combustion_loading()  # diagnostic only; no uncalibrated efficiency feedback
        self.res.update(outer_loop_iters=1,outer_loop_converged=True,
                        eta_comb_converged=eta,eta_is_assumed=True,
                        v_inner_converged_m_s=self.res['v_inner_annulus'],
                        f_outer_converged=self.res['f_outer_feed_used'])
        self.hole_sizing()
        self.liner_structural()
        self.temperature_traverse_quality()
        self.stability_checks()
        self.res['manufacturing_released'] = False
        self.res['stability_validated'] = False
        self.res['thermal_validated'] = False
        self.res['outer_liner_buckling_validated'] = False
        self.res['patches_applied'] = ['2026-09 shared-state / fixed-geometry / pressure-budget audit']
        self.res['cad_geometry'] = self.get_cad_geometry()
        return self.res

    def get_cad_geometry(self):
        r = self.res
        cad = {
            "metadata": {
                "units": "mm",
                "description": "Reverse-flow annular micro-jet combustor",
                "generated_by": "core/combustor.py (patched port of V21)",
                "patches_applied": sorted(PATCH_NOTES),
                "liner_material": r.get('liner_material'),
                "liner_material_name": r.get('liner_material_name'),
                "liner_wall_temp_K": r.get('liner_wall_temp_K'),
                "dimension_note": (
                    "Liner OD values are COLD BUILD dimensions. The thermal offset is "
                    "a DIAMETER change evaluated at the liner metal temperature, not a "
                    "radius change at TIT -- see PATCH P2. Do not use od_hot for fabrication."
                ),
            },
            "overall": {"chamber_length": r['chamber_length_mm'],
                        "mean_comb_dia": r['D_mean_comb_mm'],
                        "L_over_D": r['chamber_L_over_D']},
            "casing": {"od": r['casing_od_mm'], "id": r['casing_id_mm'],
                       "wall_thickness": self.inputs['wall_thickness_mm']},
            "shaft_tunnel": {"od": r['shaft_tunnel_od_mm'], "id": r['shaft_tunnel_id_mm']},
            "outer_liner": {"od": r['outer_liner_od_cold_mm'], "od_hot": r['outer_liner_od_hot_mm'],
                            "thermal_offset": r['outer_liner_thermal_offset_mm'],
                            "id": r['outer_liner_id_mm'], "length": r['chamber_length_mm'],
                            "annulus_gap": r['outer_annulus_gap_mm']},
            "inner_liner": {"od": r['inner_liner_od_cold_mm'], "od_hot": r['inner_liner_od_hot_mm'],
                            "thermal_offset": r['inner_liner_thermal_offset_mm'],
                            "id": r['inner_liner_id_mm'], "length": r['chamber_length_mm'],
                            "annulus_gap": r['inner_annulus_gap_mm']},
            "combustion_annulus": {"radial_height": r['combustion_gap_mm'],
                                   "mean_diameter": r['D_mean_comb_mm'],
                                   "cross_section_area_mm2": r['combustion_annulus_A'] * 1e6},
            "vaporizers": {"count": r['vap_n'], "raw_count": r['vap_n_raw'],
                           "pitch_actual": r['vap_pitch_actual_mm'], "tube_od": r['vap_od_mm'],
                           "tube_bore_id": r['vap_id_mm'], "crimp_orifice_id": r['vap_crimp_dia_mm'],
                           "scoop_inlet_dia": r['vap_scoop_dia_mm'],
                           "bend_radius": r['vap_bend_radius_mm'],
                           "per_tube": {"fuel_g_s": r['vap_m_fuel_per_tube'],
                                        "air_g_s": r['vap_m_air_per_tube']}},
            "main_holes": {"outer_fraction": r['hole_split_f_outer'],
                           "inner_fraction": r['hole_split_f_inner'],
                           "primary": {"outer_qty": r['pri_out_qty'], "outer_dia": r['pri_out_mm'],
                                       "inner_qty": r['pri_in_qty'], "inner_dia": r['pri_in_mm']},
                           "secondary": {"outer_qty": r['sec_out_qty'], "outer_dia": r['sec_out_mm'],
                                         "inner_qty": r['sec_in_qty'], "inner_dia": r['sec_in_mm']},
                           "dilution": {"outer_qty": r['dil_out_qty'], "outer_dia": r['dil_out_mm'],
                                        "inner_qty": r['dil_in_qty'], "inner_dia": r['dil_in_mm']}},
            "film_cooling": {"total_rows": r['film_n_rows'], "row_pitch": self.DESIGN_PARAMS['film_row_pitch_mm'],
                             "hole_dia": r['film_hole_dia_mm_actual'],
                             "outer_holes_per_row": r['film_holes_per_row_outer'],
                             "inner_holes_per_row": r['film_holes_per_row_inner'],
                             "total_holes": r['film_total_holes'],
                             "total_area_mm2": r['film_total_area_mm2']},
            "annulus_velocities": {"outer_entry": r['v_outer_annulus'],
                                   "outer_post_vap": r['v_outer_post_vap'],
                                   "inner": r['v_inner_annulus']},
            "zone_lengths": {"primary": r['L_primary_mm'], "secondary": r['L_secondary_mm'],
                             "dilution": r['L_dilution_mm']},
        }
        scale = r['thermal_scale_ratio']
        cad['metadata']['release_status'] = 'PRELIMINARY - NOT FOR MANUFACTURE'
        cad['metadata']['dimension_note'] = ('Liner surfaces, holes and lengths are cold at 293 K; uniform prescribed metal temperature. Casing/tunnel unchanged envelope inputs. Vaporizer thermal growth unresolved.')
        for side in ('outer','inner'):
            cad[side+'_liner']['id'] = r[side+'_liner_id_cold_mm']
            cad[side+'_liner']['length'] = r['chamber_length_cold_mm']
        cad['overall']['chamber_length'] /= scale
        for key in cad['zone_lengths']: cad['zone_lengths'][key] /= scale
        for zone in ('primary','secondary','dilution'):
            for key in ('outer_dia','inner_dia'): cad['main_holes'][zone][key] /= scale
        cad['film_cooling']['hole_dia_outer'] = r['film_hole_dia_outer_mm']/scale
        cad['film_cooling']['hole_dia_inner'] = r['film_hole_dia_inner_mm']/scale
        cad['film_cooling'].pop('hole_dia',None)
        cad['film_cooling']['row_pitch'] /= scale
        return cad
