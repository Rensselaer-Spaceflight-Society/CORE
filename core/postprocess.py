"""Detailed component definitions and mechanical screens from a solved state.

Everything here is derived from the module state and the case/records; nothing
feeds back into the state (single producer). Functions return plain dicts so the
CAD exporter, figures and reports read the same numbers.
"""
from __future__ import annotations

import math

import numpy as np

from core import assembly, gas, thermo
from core.records import Check


# ---------------------------------------------------------------------------- combustor layout
def combustor_layout(res, seam_angle_deg=None, seam_halfwidth_m=0.003, bend_exclusion_m=0.003):
    """Row positions, clocking and interference checks for both liners (cold).

    Axial positions are measured aft from the dome face (cold) by a stated rule:
    primary row at 0.55 L_pz, secondary at L_pz + 0.5 L_sz, dilution at
    L_pz + L_sz + 0.4 L_dz; film rows 4 mm from the dome, at the two zone
    boundaries and at L_pz + L_sz + 0.85 L_dz (clear of the dilution jets). Clocking:
    vaporizer k at 360 k / n_vap (0 deg = top, clockwise from the front);
    primary and secondary holes at +/- a quarter vaporizer pitch; dilution holes
    evenly spaced with a half-step offset; inner dilution counts differ from outer,
    so the inner/outer jets are staggered. The igniter sits midway between
    vaporizers 0 and 1 in the primary zone.
    """
    sc = res['thermal_scale_ratio']
    Lpz, Lsz, Ldz = (res['L_primary_mm'] / sc / 1e3, res['L_secondary_mm'] / sc / 1e3,
                     res['L_dilution_mm'] / sc / 1e3)
    n_vap = res['vap_n']
    pitch = 360.0 / n_vap
    rows = []

    def add(name, side, x, d, angles, kind):
        rows.append(dict(row=name, side=side, x_from_dome_m=x, dia_m=d, count=len(angles),
                         angles_deg=[round(a % 360.0, 4) for a in angles], kind=kind))
    L = res['chamber_length_cold_mm'] / 1e3
    diam = {'outer': res['outer_liner_id_cold_mm'] / 1e3, 'inner': res['inner_liner_od_cold_mm'] / 1e3}
    wall_cold = res['liner_wall_thickness_mm'] / sc / 1e3
    lig_min = max(2 * wall_cold, 0.0015)
    checks, worst, seams, film_adjust = [], {}, {}, {}
    for side, short in (('outer', 'out'), ('inner', 'in')):
        R = diam[side] / 2
        dpri = res[f'pri_{short}_mm'] / sc / 1e3
        dsec = res[f'sec_{short}_mm'] / sc / 1e3
        ddil = res[f'dil_{short}_mm'] / sc / 1e3
        npri, nsec, ndil = res[f'pri_{short}_qty'], res[f'sec_{short}_qty'], res[f'dil_{short}_qty']
        per_p, per_s, per_d = npri // n_vap, nsec // n_vap, ndil // n_vap
        ap = [k * pitch + (j + 0.5) * pitch / per_p - pitch / 2 for k in range(n_vap) for j in range(per_p)]
        asec = [k * pitch + (j + 0.5) * pitch / per_s - pitch / 2 for k in range(n_vap) for j in range(per_s)]
        ad = [k * pitch + (j + 0.5) * pitch / per_d for k in range(n_vap) for j in range(per_d)]
        add('primary', side, 0.55 * Lpz, dpri, ap, 'main')
        add('secondary', side, Lpz + 0.5 * Lsz, dsec, asec, 'main')
        add('dilution', side, Lpz + Lsz + 0.4 * Ldz, ddil, ad, 'main')
        main = [(r['row'], r['x_from_dome_m'], a, r['dia_m']) for r in rows if r['side'] == side for a in r['angles_deg']]
        if seam_angle_deg is None:
            # longitudinal weld seam where it is farthest from every main-hole edge
            def clearance(th):
                return min(R * math.radians(min(abs(h[2] - th), 360 - abs(h[2] - th))) - h[3] / 2 for h in main)
            seam = max((i * 0.25 for i in range(1440)), key=clearance)
        else:
            seam = seam_angle_deg
        seams[side] = seam
        # film rows clocked with the seam at mid-pitch; holes still inside the seam band are removed and
        # the remaining film holes enlarged to keep the same total film area (flow allocation unchanged)
        nf = res[f'film_holes_per_row_{side}']
        df = res[f'film_hole_dia_{side}_mm'] / sc / 1e3
        angles = [seam + (j + 0.5) * 360.0 / nf for j in range(nf)]
        keep = [a for a in angles if R * math.radians(min(abs(a - seam) % 360, 360 - abs(a - seam) % 360))
                >= seam_halfwidth_m + df / 2]
        df_new = df * math.sqrt(nf / len(keep)) if keep else df
        film_adjust[side] = dict(holes_per_row_model=nf, holes_per_row_layout=len(keep), dia_model_m=df, dia_layout_m=df_new,
                                 note='same total film area; holes inside the seam band omitted')
        film_x = [0.004, Lpz, Lpz + Lsz, Lpz + Lsz + 0.85 * Ldz]
        for i, x in enumerate(film_x[:res['film_n_rows']]):
            add(f'film{i + 1}', side, x, df_new, keep, 'film')
        srows = [r for r in rows if r['side'] == side]
        holes = [(r['row'], r['x_from_dome_m'], a, r['dia_m']) for r in srows for a in r['angles_deg']]
        # all pairs on this liner (surface distance on the developed cylinder)
        best = (1e9, None)
        for i in range(len(holes)):
            ni, xi, ai, di = holes[i]
            for j in range(i + 1, len(holes)):
                nj, xj, aj, dj = holes[j]
                dth = math.radians(min(abs(ai - aj), 360 - abs(ai - aj)))
                dist = math.hypot(xi - xj, R * dth) - 0.5 * (di + dj)
                if dist < best[0]:
                    best = (dist, (ni, nj, round(xi * 1e3, 2), round(xj * 1e3, 2), ai, aj))
        worst[side] = best
        checks.append(Check.compare(f'{side} liner minimum ligament (all rows, axial+diagonal+circumferential)',
                                    best[0], '>=', lig_min, 'm', 'calculated',
                                    f'closest pair {best[1]}; minimum max(2 t_cold, 1.5 mm)'))
        # seam exclusion: longitudinal weld seam at seam_angle
        seam_hits = [h for h in holes if R * math.radians(min(abs(h[2] - seam), 360 - abs(h[2] - seam)))
                     < seam_halfwidth_m + h[3] / 2]
        checks.append(Check('%s liner holes clear of weld seam at %.2f deg' % (side, seam),
                            'pass' if not seam_hits else 'fail', len(seam_hits), 0, 'count', '<= 0', 'design',
                            f'{len(seam_hits)} holes within {seam_halfwidth_m*1e3:.1f} mm + radius of the seam'))
        # bend exclusion near dome flange and discharge cone
        near = [h for h in holes if h[1] - h[3] / 2 < bend_exclusion_m or h[1] + h[3] / 2 > L - bend_exclusion_m]
        checks.append(Check('%s liner holes clear of dome/transition bends' % side, 'pass' if not near else 'fail',
                            len(near), 0, 'count', '<= 0', 'design', f'{bend_exclusion_m*1e3:.0f} mm bend exclusion'))
    vaps = [dict(index=k, angle_deg=k * pitch, od_m=res['vap_od_mm'] / 1e3, id_m=res['vap_id_mm'] / 1e3,
                 crimp_m=res['vap_crimp_dia_mm'] / 1e3, scoop_m=res['vap_scoop_dia_mm'] / 1e3,
                 mean_diameter_m=res['D_mean_comb_mm'] / sc / 1e3) for k in range(n_vap)]
    straight = 0.6 * L
    bend_r = res['vap_bend_radius_mm'] / 1e3
    stick = dict(type='J (walking-stick) vaporizer: inlet through dome, straight leg aft, 180 deg bend, discharge toward dome',
                 straight_leg_m=straight, bend_centerline_radius_m=bend_r,
                 return_leg_m=max(straight - 2 * bend_r, 0.0),
                 developed_length_m=straight + math.pi * bend_r + max(straight - 2 * bend_r, 0.0),
                 model_effective_length_m=res['chamber_length_mm'] / 1e3 * 1.5 + 2 * res['vap_od_mm'] / 1e3,
                 note='Legs separated by 2 x bend radius; bend plane chosen below from the available space.')
    od = res['vap_od_mm'] / 1e3
    envelope = 2 * bend_r + od
    gap = res['combustion_gap_mm'] / sc / 1e3
    tang = math.pi * res['D_mean_comb_mm'] / sc / 1e3 / n_vap - 0.003     # pitch less 3 mm between neighbours
    if envelope + 0.002 <= gap:
        stick['bend_plane'] = 'radial-axial'
        checks.append(Check.compare('vaporizer J-bend fits combustion annulus height', envelope + 0.002, '<=', gap, 'm', 'design'))
    else:
        stick['bend_plane'] = 'circumferential-axial (radial height insufficient)'
        checks.append(Check.compare('vaporizer J-bend fits circumferentially between neighbouring sticks', envelope, '<=',
                                    tang, 'm', 'design', f'radial gap {gap*1e3:.1f} mm < bend envelope {envelope*1e3:.1f} mm'))
    igniter = dict(angle_deg=0.5 * pitch, x_from_dome_m=0.5 * Lpz, side='outer',
                   note='Through outer casing and outer liner into the primary zone between vaporizers 0 and 1; '
                        'plug reach and boss sealing to be set from the selected plug (budget C08).')
    return dict(rows=rows, vaporizers=vaps, vaporizer_stick=stick, igniter=igniter,
                zone_lengths_cold_m=dict(primary=Lpz, secondary=Lsz, dilution=Ldz), chamber_length_cold_m=L,
                ligament_min_m=lig_min, closest_pairs={k: dict(distance_m=v[0], pair=v[1]) for k, v in worst.items()},
                checks=checks, seam_angle_deg=seams, film_adjustment=film_adjust)


# ---------------------------------------------------------------------------- nozzle
def nozzle_contour(stack, p, n=21):
    """Conical outer wall + conical tailcone; annular area must fall monotonically to the exit."""
    x0 = stack['x']['nozzle_entry']
    L = p['nozzle_length_m']
    r_in0 = 0.5 * p['tw_tip_d_m'] + p['tw_tip_clearance_m']
    r_ex = 0.5 * p['nozzle_exit_d_m']
    r_hub = 0.5 * p['tw_hub_d_m']
    Ltc = p['tailcone_length_m']
    pts = []
    for i in range(n):
        x = L * i / (n - 1)
        r_o = r_in0 + (r_ex - r_in0) * x / L
        r_t = max(r_hub * (1 - x / Ltc), 0.0) if x < Ltc else 0.0
        pts.append(dict(x_m=x0 + x, r_outer_m=r_o, r_tailcone_m=r_t, area_m2=math.pi * (r_o ** 2 - r_t ** 2)))
    areas = [q['area_m2'] for q in pts]
    i_min = int(np.argmin(areas))
    half_angle = math.degrees(math.atan((r_in0 - r_ex) / L))
    checks = [Check('nozzle throat at exit plane (no internal minimum)', 'pass' if i_min == len(pts) - 1 else 'fail',
                    pts[i_min]['x_m'] - pts[-1]['x_m'], 0.0, 'm', '== 0', 'design',
                    'annular area minimum location relative to the exit plane'),
              Check.compare('outer-wall half angle', half_angle, '<=', 15.0, 'deg', 'design',
                            'conical convergent nozzle guideline; no separation analysis')]
    return dict(points=pts, half_angle_deg=half_angle, exit_area_m2=areas[-1],
                inlet_annulus_area_m2=areas[0], checks=checks)


# ---------------------------------------------------------------------------- rotor dynamics
def rotor_dynamics(stack, N_low, N_high, G_grade_mm_s=2.5, speeds=None, k_range=None):
    model = assembly.rotor_model(stack, max_element_length=0.006)
    bound = 1.5 * N_high
    crits = model.critical_speeds(bound, n_modes=4, n_grid=30)
    speeds = speeds or list(np.linspace(0.02 * bound, bound, 25))
    campbell = []
    for N in speeds:
        ms = model.modes(N, 10)
        campbell.append(dict(N_rpm=N, modes=[dict(freq_rpm=m['freq_rpm'], whirl=m['whirl'],
                                                  damping_ratio=m['damping_ratio']) for m in ms[:8]]))
    # mode shapes at the critical speeds (normalised lateral displacement along the shaft)
    shapes = []
    for c in crits:
        ms = [m for m in model.modes(c['N_crit_rpm'], 12) if m['whirl'] == 'forward']
        if ms:
            m = min(ms, key=lambda q: abs(q['freq_rpm'] - c['N_crit_rpm']))
            shapes.append(dict(N_crit_rpm=c['N_crit_rpm'], damping_ratio=m['damping_ratio'],
                               z_m=model.z.tolist(), shape=list(m['shape_x'])))
    # unbalance response: ISO 1940 grade G at N_high, both wheels, in phase and opposed
    omega_h = N_high * 2 * math.pi / 60
    e = G_grade_mm_s * 1e-3 / omega_h
    discs = {d.name: d for d in stack['discs']}
    cw, tw = discs['compressor wheel'], discs['turbine wheel']
    resp = []
    for N in np.linspace(0.05 * N_high, 1.2 * N_high, 47):
        for label, ph in (('in_phase', 0.0), ('opposed', math.pi)):
            amp, forces = model.unbalance_response(N, [(cw.z, cw.mass * e, 0.0), (tw.z, tw.mass * e, ph)])
            resp.append(dict(N_rpm=float(N), case=label,
                             amp_compressor_m=float(amp[model.node_index(cw.z)]),
                             amp_turbine_m=float(amp[model.node_index(tw.z)]),
                             max_amp_m=float(amp.max()), bearing_forces_N=forces))
    sep = min((max(N_low - c['N_crit_rpm'], c['N_crit_rpm'] - N_high, 0.0) / N_high for c in crits),
              default=(bound - N_high) / N_high)
    out = dict(critical_speeds=crits, separation_frac=sep, campbell=campbell, mode_shapes=shapes,
               unbalance=dict(grade_G_mm_s=G_grade_mm_s, eccentricity_m=e, response=resp),
               supports=[dict(name=s.name, z_m=s.z, k_N_m=s.k, c_N_s_m=s.c) for s in stack['supports']],
               element_length_m=0.006, n_nodes=model.n_nodes)
    if k_range:
        sens = []
        for k in k_range:
            mk = assembly.rotor_model(stack, max_element_length=0.006, k=k)
            sens.append(dict(k_N_m=k, critical_speeds=[c['N_crit_rpm'] for c in mk.critical_speeds(bound, 4, 30)]))
        out['support_stiffness_sensitivity'] = sens
    # discretisation convergence on the candidate (lowest three criticals)
    conv = []
    for h in (0.012, 0.006, 0.003):
        mh = assembly.rotor_model(stack, max_element_length=h)
        conv.append(dict(element_length_m=h, critical_speeds=[c['N_crit_rpm'] for c in mh.critical_speeds(bound, 4, 30)]))
    out['mesh_convergence'] = conv
    return out


# ---------------------------------------------------------------------------- thermal / mechanical
def clearances(stack, p, dp, mats, N_rpm):
    """Steady hot clearances with assumed metal temperatures (stated)."""
    t = dp['turbine']
    cp = gas.cp_products(t['T1_K'], dp['flows']['FAR_mixed'])
    T_rel = t['T1_K'] + t['W1_m_s'] ** 2 / (2 * cp)          # rotor relative total temperature
    T_tip_metal = T_rel - 30.0                                 # assumption: tip metal ~30 K below relative total
    T41, T3 = dp['stations']['T41_K'], dp['stations']['T3_K']
    T_shroud = 0.85 * T41 + 0.15 * T3                          # assumption: shroud cooled by annulus air side
    a_w = mats.si('ni_cast_alpha_mean_to_1000K')
    a_s = mats.si('ngv_alpha_mean')
    E_w = mats.si('ni_cast_E_1000K')
    nominal = assembly.tip_clearance_hot(p, T_tip_metal, T_shroud, N_rpm, a_w, a_s, E_w)
    lo, hi = mats.si_range('ngv_alpha_mean')
    adverse = assembly.tip_clearance_hot(p, T_tip_metal, T_shroud, N_rpm, a_w, lo, E_w)
    favourable = assembly.tip_clearance_hot(p, T_tip_metal, T_shroud, N_rpm, a_w, hi, E_w)
    # transient bound: shroud already cooled to annulus-air temperature while the wheel is still hot
    shutdown = assembly.tip_clearance_hot(p, T_tip_metal, T3 + 50.0, N_rpm * 0.3, a_w, a_s, E_w)
    T_shaft = 0.5 * (T3 + 0.6 * T41)                           # assumption: tunnel air + rear heat soak
    T_tunnel = 0.5 * (T3 + 0.8 * dp['stations']['T4_K'])
    ax = assembly.axial_growth(stack, T_shaft, T_tunnel, T3 + 20.0, 12.3e-6, mats.si('ss316_alpha_mean_to_900K'),
                               mats.si('ss316_alpha_mean_to_900K'))
    ch = [Check.compare('turbine tip clearance, steady hot (nominal alpha)', nominal['hot_m'], '>=', 0.05e-3, 'm',
                        'calculated', 'assumed metal temperatures; centrifugal solid-disc growth'),
          Check.compare('turbine tip clearance, steady hot (low shroud alpha)', adverse['hot_m'], '>=', 0.05e-3, 'm',
                        'calculated'),
          Check.compare('turbine tip clearance, shutdown bound (cool shroud, hot wheel)', shutdown['hot_m'], '>=', 0.0,
                        'm', 'calculated', 'transient bound, not a transient analysis'),
          Check.compare('NGV-rotor axial gap after growth', p['ngv_rotor_axial_gap_m'] + ax['ngv_rotor_gap_change_m'],
                        '>=', 0.8e-3, 'm', 'calculated'),
          Check.compare('rear bearing float demand vs preload spring travel', abs(ax['rear_bearing_float_m']), '<=',
                        0.5e-3, 'm', 'design', 'wave spring working travel assumed 0.5 mm')]
    return dict(assumed_temperatures_K=dict(rotor_relative_total=T_rel, turbine_tip_metal=T_tip_metal,
                                            ngv_shroud=T_shroud, shaft_mean=T_shaft, tunnel_mean=T_tunnel,
                                            casing=T3 + 20.0),
                tip=dict(nominal=nominal, low_shroud_alpha=adverse, high_shroud_alpha=favourable, shutdown_bound=shutdown),
                axial=ax, checks=ch)


def shaft_and_structure(stack, state, mats, dp, comb_res):
    N = state['N_rpm']
    omega = N * 2 * math.pi / 60
    P_c = dp['powers']['P_compressor_W'] + dp['powers']['P_bearings_W'] * 0.5
    torque = P_c / omega
    # bending at the front-bearing shoulder from compressor overhang unbalance + 1 g + 2 g handling margin
    e = 2.5e-3 / (state['N_operating_max_rpm'] * 2 * math.pi / 60)
    m_c = [d for d in stack['discs'] if d.name == 'compressor wheel'][0].mass
    F = m_c * (e * omega ** 2 + 3 * 9.81)
    M = F * stack['comp_overhang_m']
    ss = assembly.shaft_stress(stack, torque, M)
    sy = mats.si('s4140_yield_RT')
    se = mats.si('s4140_endurance_RT') * 0.6        # surface/size/reliability factors ~0.6 (assumption)
    ch = [Check.compare('shaft peak von Mises vs 0.5 yield (4140 RT)', ss['von_mises_peak_Pa'], '<=', 0.5 * sy, 'Pa',
                        'assumption', 'stress concentration Kt 2.0 bending / 1.6 torsion at the 6 mm seat'),
          Check.compare('shaft alternating bending vs corrected endurance', ss['sigma_b_peak_Pa'], '<=', se, 'Pa',
                        'assumption', 'rotating bending from overhang loads; Goodman mean-torsion effect neglected'),
          # The checks above use the smallest seat/journal section; the threaded ends are not in them.
          Check('shaft threaded ends: torque share, nut preload and thread Kt', 'unknown', None, None, 'Pa',
                'not evaluated', 'unresolved',
                'M6/M8 ends (minor diameter ~0.85 x nominal) may carry part of the wheel torque through the clamped '
                'nut plus the clamp preload; neither is modelled, so the seat value is not shown to govern.')]
    # outer liner external pressure (annulus static above liner static) and buckling
    E_liner = 175e9
    D = comb_res['outer_liner_od_cold_mm'] / 1e3
    t = comb_res['liner_wall_thickness_mm'] / comb_res['thermal_scale_ratio'] / 1e3
    Lb = comb_res['chamber_length_cold_mm'] / 1e3
    dP_ext = comb_res['dP_outer_holes_Pa']
    b = assembly.outer_liner_buckling(D, t, Lb, E_liner)
    ch.append(Check.compare('outer liner elastic buckling margin (knockdown 0.5)', b['p_cr_knocked_down_Pa'] / dP_ext,
                            '>=', 3.0, '-', 'calculated', 'Windenburg-Trilling; creep buckling at temperature not covered'))
    # casing hoop stress
    P3 = dp['stations']['P3_Pa']
    Dc = state['casing_od_m']
    tc = state['casing_wall_m']
    hoop = (P3 - dp['stations']['P0_Pa']) * (Dc / 2) / tc
    ch.append(Check.compare('casing hoop stress vs 0.3 x 316 yield (seam-welded)', hoop, '<=', 0.3 * mats.si('ss316_yield_RT'),
                            'Pa', 'assumption', 'membrane stress only; flange/joint and fragment containment NOT covered'))
    return dict(torque_Nm=torque, bending_moment_Nm=M, shaft=ss, liner_buckling=dict(b, external_dP_Pa=dP_ext,
                D_m=D, t_m=t, L_m=Lb, E_Pa=E_liner), casing_hoop_Pa=hoop, checks=ch)
