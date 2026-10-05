"""PD-1 axial assembly stack, stepped shaft, part envelopes and mechanical checks.

One function, build_stack(p), turns a flat dictionary of SI scalars into the
assembly definition. The module pipeline (modules/m29_layout.py) calls it with
state values and publishes scalar summaries; the CAD/BOM exporter calls it with
the same final state, so the scalar state and the exported geometry cannot
disagree. Frame: x along the axis, positive aft, origin at the compressor wheel
backface (cold); r radial. All positions are cold assembly values.

Checks here are first-order screens with stated assumptions: fits from nominal
tolerances, steady thermal growth from assumed metal temperatures, centrifugal
growth of a solid disc, shaft stress with a stress-concentration factor, and the
outer-liner external-pressure buckling estimate. They are not FEA, life or
supplier acceptance.
"""
from __future__ import annotations

import math

from core.records import Check
from core.rotor_fe import RotorModel, ShaftSection, Disc, Support

# keys build_stack requires (SI units); the layout module's reads mirror this list
REQUIRED = (
    'cw_length_m', 'cw_super_back_m', 'cw_cg_from_backface_m', 'cw_mass_kg', 'cw_Ip_kg_m2', 'cw_Id_kg_m2',
    'cw_D2_m', 'cw_D2_ext_m', 'cw_D1s_m', 'cw_b2_m',
    'front_thread_length_m', 'compressor_nut_length_m', 'backface_clearance_m', 'backplate_rear_face_x_m',
    'backplate_od_m', 'front_sleeve_od_m', 'front_bearing_gap_m', 'front_bearing_recess_m',
    'brg_width_m', 'brg_bore_m', 'brg_od_m',
    'shaft_journal_d_m', 'shaft_body_d_m', 'shaft_comp_seat_d_m', 'shaft_rear_thread_d_m',
    'rear_thread_length_m', 'turbine_nut_length_m', 'rear_spacer_length_m', 'rear_spacer_od_m',
    'ngv_rotor_axial_gap_m', 'plenum_gap_m', 'transition_length_m',
    'liner_length_cold_m', 'outer_liner_od_cold_m', 'outer_liner_id_cold_m',
    'inner_liner_od_cold_m', 'inner_liner_id_cold_m',
    'ngv_axial_chord_m', 'ngv_hub_d_m', 'ngv_tip_d_m', 'ngv_flange_od_m', 'ngv_overall_height_m', 'ngv_vane_ring_height_m',
    'ngv_outer_ring_od_m', 'ngv_bolt_pcd_m', 'ngv_bolt_hole_d_m', 'ngv_hub_pocket_d_m', 'cw_bore_d_m', 'tw_bore_d_m',
    'tw_tip_d_m', 'tw_hub_d_m', 'tw_rim_width_m', 'tw_boss_d_m', 'tw_boss_total_m', 'tw_boss_side_a_m',
    'tw_mass_kg', 'tw_Ip_kg_m2', 'tw_Id_kg_m2', 'tw_tip_clearance_m',
    'casing_od_m', 'casing_wall_m', 'tunnel_od_m', 'tunnel_wall_m',
    'nozzle_exit_d_m', 'nozzle_length_m', 'tailcone_length_m', 'bellmouth_length_m',
    'diffuser_exit_d_m', 'diffuser_vane_height_m',
    'rho_shaft_kg_m3', 'E_shaft_Pa', 'k_support_N_m', 'c_support_N_s_m',
)

STEEL = 7850.0

# Stack inputs that are already published by other modules (single producer):
STATE_MAP = {
    'cw_D2_m': 'D2_m', 'cw_D1s_m': 'D1s_m', 'cw_b2_m': 'b2_m', 'cw_mass_kg': 'm_imp_kg',
    'tw_tip_d_m': 'D_turb_tip_m', 'tw_hub_d_m': 'D_turb_hub_m', 'tw_mass_kg': 'm_turb_kg',
    'tw_Ip_kg_m2': 'I_turb_kg_m2', 'tw_tip_clearance_m': 't_tip_clear_m',
    'liner_length_cold_m': 'L_liner_cold_m', 'outer_liner_od_cold_m': 'D_liner_out_cold_m',
    'outer_liner_id_cold_m': 'D_outer_liner_id_cold_m', 'inner_liner_od_cold_m': 'D_liner_in_cold_m',
    'inner_liner_id_cold_m': 'D_inner_liner_id_cold_m', 'diffuser_exit_d_m': 'D3_m',
    'diffuser_vane_height_m': 'b_diff_m', 'tunnel_od_m': 'D_shaft_tunnel_m', 'brg_bore_m': 'd_bearing_bore_m',
}
DERIVED = {'nozzle_exit_d_m': 'A8_fixed_m2'}   # diameter from the fixed nozzle area seed
STACK_READS = sorted({STATE_MAP.get(k, DERIVED.get(k, k)) for k in REQUIRED})


def params_from_state(s):
    p = {}
    for k in REQUIRED:
        if k in DERIVED:
            p[k] = math.sqrt(4 * s[DERIVED[k]] / math.pi)
        else:
            p[k] = s[STATE_MAP.get(k, k)]
    return p


def _ring_mass(od, idd, length, rho):
    return rho * math.pi / 4 * (od * od - idd * idd) * length


def build_stack(p):
    missing = [k for k in REQUIRED if k not in p]
    if missing:
        raise KeyError(f'assembly stack inputs missing: {missing}')
    bad = [k for k in REQUIRED if not math.isfinite(p[k]) or p[k] < 0]
    if bad:
        raise ValueError(f'assembly stack inputs must be finite and nonnegative: {bad}')
    x = {}
    x['cw_backface'] = 0.0
    x['cw_nose'] = -p['cw_length_m']
    x['shaft_front'] = x['cw_nose'] - p['front_thread_length_m']
    x['comp_nut_front'] = x['cw_nose'] - p['compressor_nut_length_m']
    x['diffuser_floor'] = -p['cw_super_back_m']
    x['diffuser_cover'] = x['diffuser_floor'] - p['diffuser_vane_height_m']
    x['backplate_rear'] = p['backplate_rear_face_x_m']
    # front bearing pocket recessed into the backplate hub (shortens the compressor overhang)
    x['fb_front'] = x['backplate_rear'] + p['front_bearing_gap_m'] - p['front_bearing_recess_m']
    x['fb_rear'] = x['fb_front'] + p['brg_width_m']
    x['fb_c'] = 0.5 * (x['fb_front'] + x['fb_rear'])
    x['dome'] = x['backplate_rear'] + p['plenum_gap_m']
    x['liner_end'] = x['dome'] + p['liner_length_cold_m']
    # NGV casting: vane ring (supplied height) then the shroud/flange section that surrounds the rotor.
    # Vanes end one axial gap before the shroud section; the rotor leading edge sits at its start.
    x['ngv_front'] = x['liner_end'] + p['transition_length_m']
    x['rotor_le'] = x['ngv_front'] + p['ngv_vane_ring_height_m']
    x['ngv_te'] = x['rotor_le'] - p['ngv_rotor_axial_gap_m']
    x['ngv_le'] = x['ngv_te'] - p['ngv_axial_chord_m']
    if x['ngv_le'] < x['ngv_front'] - 1e-12:
        raise ValueError('NGV vane chord + axial gap exceed the supplied vane-ring height')
    x['rotor_te'] = x['rotor_le'] + p['tw_rim_width_m']
    x['tw_c'] = 0.5 * (x['rotor_le'] + x['rotor_te'])
    x['boss_front'] = x['rotor_le'] - p['tw_boss_side_a_m']
    x['boss_rear'] = x['boss_front'] + p['tw_boss_total_m']
    x['rs_front'] = x['boss_front'] - p['rear_spacer_length_m']
    x['rb_rear'] = x['rs_front']
    x['rb_front'] = x['rb_rear'] - p['brg_width_m']
    x['rb_c'] = 0.5 * (x['rb_front'] + x['rb_rear'])
    x['shaft_rear'] = x['boss_rear'] + p['rear_thread_length_m']
    x['ngv_ring_rear'] = x['ngv_front'] + p['ngv_overall_height_m']
    x['casing_front'] = x['diffuser_floor']
    x['ngv_flange_front'] = x['ngv_front'] + p['ngv_vane_ring_height_m']
    x['casing_rear_cover'] = x['ngv_flange_front'] - p['casing_wall_m']   # cover bolts to the flange front face
    # nozzle flange bolts to the rear face of the NGV casting (its shroud section surrounds the rotor)
    x['nozzle_entry'] = max(x['rotor_te'] + 0.002, x['ngv_ring_rear'])
    x['nozzle_exit'] = x['nozzle_entry'] + p['nozzle_length_m']
    x['inlet_lip'] = x['cw_nose'] - 0.008 - p['bellmouth_length_m']
    x['cw_cg'] = -p['cw_cg_from_backface_m']

    # ---- shaft sections -------------------------------------------------------
    d6, d10, d13 = p['shaft_comp_seat_d_m'], p['shaft_journal_d_m'], p['shaft_body_d_m']
    dthr = p['shaft_rear_thread_d_m']
    E, rho = p['E_shaft_Pa'], p['rho_shaft_kg_m3']
    sec = [
        ShaftSection(x['shaft_front'], x['cw_nose'] - x['shaft_front'], 0.85 * d6, E=E, rho=rho, name='front thread M6 (minor dia)'),
        ShaftSection(x['cw_nose'], 0.0 - x['cw_nose'], d6, E=E, rho=rho, name='compressor seat'),
        ShaftSection(0.0, x['fb_front'], d6, E=E, rho=rho, name='seal-sleeve seat'),
        ShaftSection(x['fb_front'], x['fb_rear'] - x['fb_front'], d10, E=E, rho=rho, name='front journal'),
        ShaftSection(x['fb_rear'], x['rb_front'] - x['fb_rear'], d13, E=E, rho=rho, name='body'),
        ShaftSection(x['rb_front'], x['rb_rear'] - x['rb_front'], d10, E=E, rho=rho, name='rear journal'),
        ShaftSection(x['rb_rear'], x['boss_front'] - x['rb_rear'], d10, E=E, rho=rho, name='rear spacer seat'),
        ShaftSection(x['boss_front'], x['boss_rear'] - x['boss_front'], d10, E=E, rho=rho, name='turbine seat'),
        ShaftSection(x['boss_rear'], x['shaft_rear'] - x['boss_rear'], 0.85 * dthr, E=E, rho=rho, name='rear thread M8 (minor dia)'),
    ]
    # ---- rotating masses ------------------------------------------------------
    brg_rot = 0.45 * _ring_mass(p['brg_od_m'], p['brg_bore_m'], p['brg_width_m'], STEEL) * 0.5
    sleeve_m = _ring_mass(p['front_sleeve_od_m'], d6, x['fb_front'], STEEL)
    rspacer_m = _ring_mass(p['rear_spacer_od_m'], d10, p['rear_spacer_length_m'], STEEL)
    nut_c = _ring_mass(0.010, d6, p['compressor_nut_length_m'], STEEL)
    nut_t = _ring_mass(0.013, dthr, p['turbine_nut_length_m'], STEEL)
    discs = [
        Disc(x['cw_cg'], p['cw_mass_kg'], p['cw_Ip_kg_m2'], p['cw_Id_kg_m2'], 'compressor wheel'),
        Disc(x['comp_nut_front'] + 0.5 * p['compressor_nut_length_m'], nut_c, 0.0, 0.0, 'compressor nut'),
        Disc(0.5 * x['fb_front'], sleeve_m, 0.0, 0.0, 'front seal sleeve'),
        Disc(x['fb_c'], brg_rot, 0.0, 0.0, 'front bearing inner ring + balls (share)'),
        Disc(x['rb_c'], brg_rot, 0.0, 0.0, 'rear bearing inner ring + balls (share)'),
        Disc(0.5 * (x['rs_front'] + x['boss_front']), rspacer_m, 0.0, 0.0, 'rear spacer'),
        Disc(x['tw_c'], p['tw_mass_kg'], p['tw_Ip_kg_m2'], p['tw_Id_kg_m2'], 'turbine wheel'),
        Disc(x['boss_rear'] + 0.5 * p['turbine_nut_length_m'], nut_t, 0.0, 0.0, 'turbine nut'),
    ]
    supports = [Support(x['fb_c'], p['k_support_N_m'], p['c_support_N_s_m'], 'front bearing'),
                Support(x['rb_c'], p['k_support_N_m'], p['c_support_N_s_m'], 'rear bearing')]
    shaft_mass = sum(s.rho * s.A * s.length for s in sec)
    rot_mass = shaft_mass + sum(d.mass for d in discs)
    rot_cg = (sum(s.rho * s.A * s.length * (s.z0 + 0.5 * s.length) for s in sec)
              + sum(d.mass * d.z for d in discs)) / rot_mass
    Ip_total = (sum(s.rho * s.length * math.pi / 32 * (s.od ** 4 - s.id ** 4) for s in sec)
                + sum(d.Ip for d in discs))

    # ---- static part envelopes (x0, x1, r_in, r_out) --------------------------
    R = lambda d: 0.5 * d
    cas_id = p['casing_od_m'] - 2 * p['casing_wall_m']
    tun_id = p['tunnel_od_m'] - 2 * p['tunnel_wall_m']
    parts = [
        dict(id='IN-01', name='Inlet bellmouth + screen', x0=x['inlet_lip'], x1=x['cw_nose'] - 0.008,
             r_in=R(p['cw_D1s_m']), r_out=R(p['cw_D1s_m']) + 0.02, make='make', material='6061 sheet / 304 mesh'),
        dict(id='CH-01', name='Compressor housing (inducer shroud + diffuser cover)', x0=x['cw_nose'] - 0.008,
             x1=x['diffuser_cover'], r_in=R(p['cw_D1s_m']), r_out=R(p['casing_od_m']), make='make', material='6061-T6 block'),
        dict(id='CW-01', name='Compressor wheel', x0=x['cw_nose'], x1=0.0, r_in=R(d6), r_out=R(p['cw_D2_ext_m']),
             make='buy', material='forged Al (grade unconfirmed)', rotating=True),
        dict(id='DF-01', name='Diffuser / backplate', x0=x['diffuser_cover'], x1=x['backplate_rear'],
             r_in=R(p['front_sleeve_od_m']) + 0.0001, r_out=R(p['backplate_od_m']), make='make', material='6061-T651 plate'),
        dict(id='BC-01', name='Front bearing sleeve (soft mount) in backplate pocket', x0=x['fb_front'] - 0.001,
             x1=x['fb_rear'] + 0.003,
             r_in=R(p['brg_od_m']), r_out=R(tun_id), make='make', material='6061-T6 bar'),
        dict(id='BR-01', name='Front bearing (locating)', x0=x['fb_front'], x1=x['fb_rear'], r_in=R(p['brg_bore_m']),
             r_out=R(p['brg_od_m']), make='buy', material='hybrid angular contact'),
        dict(id='SH-01', name='Stepped shaft', x0=x['shaft_front'], x1=x['shaft_rear'], r_in=0.0, r_out=R(d13),
             make='make', material='4140 prehard', rotating=True),
        dict(id='TU-01', name='Shaft tunnel', x0=x['backplate_rear'], x1=x['ngv_front'] - 0.001,
             r_in=R(tun_id), r_out=R(p['tunnel_od_m']), make='make', material='316 tube'),
        dict(id='BC-02', name='Rear bearing carrier (hot)', x0=x['rb_front'] - 0.004, x1=x['ngv_te'],
             r_in=R(p['brg_od_m']), r_out=R(p['ngv_hub_pocket_d_m']), make='make', material='stainless/alloy steel'),
        dict(id='BR-02', name='Rear bearing (floating, spring preload)', x0=x['rb_front'], x1=x['rb_rear'],
             r_in=R(p['brg_bore_m']), r_out=R(p['brg_od_m']), make='buy', material='hybrid angular contact'),
        dict(id='CB-01', name='Combustor dome', x0=x['dome'], x1=x['dome'] + p['casing_wall_m'],
             r_in=R(p['inner_liner_id_cold_m']), r_out=R(p['outer_liner_od_cold_m']), make='make', material='316 sheet'),
        dict(id='CB-02', name='Outer liner (cylinder)', x0=x['dome'], x1=x['liner_end'],
             r_in=R(p['outer_liner_id_cold_m']), r_out=R(p['outer_liner_od_cold_m']), make='make', material='316 sheet'),
        dict(id='CB-03', name='Inner liner (cylinder)', x0=x['dome'], x1=x['liner_end'],
             r_in=R(p['inner_liner_id_cold_m']), r_out=R(p['inner_liner_od_cold_m']), make='make', material='316 sheet'),
        dict(id='CB-04', name='Outer discharge transition (cone)', x0=x['liner_end'], x1=x['ngv_front'],
             r_in=R(p['ngv_tip_d_m']), r_out=R(p['outer_liner_od_cold_m']), make='make', material='316 sheet'),
        # cone from the inner liner down to the NGV hub ring: the envelope spans both radii
        dict(id='CB-05', name='Inner discharge transition (cone)', x0=x['liner_end'], x1=x['ngv_front'],
             r_in=min(R(p['inner_liner_id_cold_m']), R(p['ngv_hub_d_m'])),
             r_out=max(R(p['inner_liner_id_cold_m']), R(p['ngv_hub_d_m'])), make='make', material='316 sheet'),
        dict(id='NG-01', name='NGV ring (finished casting)', x0=x['ngv_front'], x1=x['ngv_ring_rear'],
             r_in=R(p['ngv_hub_pocket_d_m']), r_out=R(p['ngv_flange_od_m']), make='buy+finish', material='cast heat-resisting steel'),
        dict(id='TR-01', name='Turbine wheel', x0=x['boss_front'], x1=x['boss_rear'], r_in=R(d10),
             r_out=R(p['tw_tip_d_m']), make='buy', material='cast Ni alloy (unconfirmed)', rotating=True),
        dict(id='CS-01', name='Outer casing', x0=x['casing_front'], x1=x['casing_rear_cover'],
             r_in=R(cas_id), r_out=R(p['casing_od_m']), make='make', material='316 sheet, rolled + seam weld'),
        dict(id='CS-02', name='Casing rear cover (bolted to NGV flange front face)', x0=x['casing_rear_cover'],
             x1=x['casing_rear_cover'] + p['casing_wall_m'], r_in=R(p['ngv_outer_ring_od_m']) + 0.0005,
             r_out=R(p['casing_od_m']), make='make', material='316 sheet'),
        dict(id='EX-01', name='Exhaust nozzle', x0=x['nozzle_entry'], x1=x['nozzle_exit'],
             r_in=R(p['nozzle_exit_d_m']), r_out=R(p['tw_tip_d_m']) + 0.0035, make='make', material='316 sheet'),
        dict(id='EX-02', name='Tailcone', x0=x['nozzle_entry'], x1=x['nozzle_entry'] + p['tailcone_length_m'],
             r_in=0.0, r_out=R(p['tw_hub_d_m']), make='make', material='316 sheet'),
    ]
    for q in parts:
        q.setdefault('rotating', False)

    out = dict(x=x, sections=sec, discs=discs, supports=supports, parts=parts,
               shaft_mass_kg=shaft_mass, rotor_mass_kg=rot_mass, rotor_cg_x_m=rot_cg, rotor_Ip_kg_m2=Ip_total,
               bearing_span_m=x['rb_c'] - x['fb_c'],
               comp_overhang_m=x['fb_c'] - x['cw_cg'], turb_overhang_m=x['tw_c'] - x['rb_c'],
               shaft_length_m=x['shaft_rear'] - x['shaft_front'],
               engine_length_m=x['nozzle_exit'] - x['inlet_lip'],
               tunnel_id_m=tun_id, casing_id_m=cas_id)
    out['checks'] = geometric_checks(p, out)
    return out


def rotor_model(stack, max_element_length=0.004, k=None, c=None):
    sup = stack['supports']
    if k is not None or c is not None:
        sup = [Support(s.z, k if k is not None else s.k, c if c is not None else s.c, s.name) for s in sup]
    return RotorModel(stack['sections'], stack['discs'], sup, max_element_length)


def geometric_checks(p, st):
    """Interference/consistency screens on the cold stack. Each returns a Check."""
    x = st['x']
    R = lambda d: 0.5 * d
    ch = []
    # rotating parts must not overlap each other axially along the shaft
    ch.append(Check.compare('rear spacer length positive', x['boss_front'] - x['rs_front'], '>=', 0.002, 'm',
                            'design', 'turbine boss to rear bearing spacer'))
    ch.append(Check.compare('front seal sleeve length (labyrinth, >= 4 mm)', x['fb_front'], '>=', 0.004, 'm', 'design',
                            'room for a 3-tooth labyrinth between wheel backface and front bearing'))
    # rear bearing must sit inside the NGV hub bore region / tunnel end
    ch.append(Check.compare('rear bearing ahead of turbine boss', x['rb_rear'], '<=', x['boss_front'], 'm', 'design'))
    # combustor and NGV radial fit inside casing
    cas_id = st['casing_id_m']
    ch.append(Check.compare('outer liner OD inside casing ID (radial gap)', 0.5 * (cas_id - p['outer_liner_od_cold_m']),
                            '>=', 0.004, 'm', 'calculated', 'outer annulus must exist (cold)'))
    ch.append(Check.compare('inner liner ID outside tunnel OD (radial gap)', 0.5 * (p['inner_liner_id_cold_m'] - p['tunnel_od_m']),
                            '>=', 0.003, 'm', 'calculated', 'inner annulus must exist (cold)'))
    ch.append(Check.compare('NGV flange inside casing ID', p['ngv_flange_od_m'], '<=', cas_id, 'm', 'supplied'))
    ch.append(Check.compare('diffuser exit inside casing ID', p['diffuser_exit_d_m'], '<=', cas_id - 0.006, 'm', 'design'))
    # The supplier drawing shows a 48 mm blind pocket with a central web.  It
    # is useful as an envelope check, but it is not evidence of a finished
    # through passage for the rear carrier.  Keep the envelope arithmetic and
    # expose the missing machining/web-support decision separately.
    ch.append(Check.compare('rear carrier OD inside NGV hub pocket envelope', p['brg_od_m'] + 0.010, '<=',
                            p['ngv_hub_pocket_d_m'], 'm', 'design',
                            f'bearing OD + 5 mm carrier wall each side inside the {p["ngv_hub_pocket_d_m"] * 1e3:.1f} mm '
                            'blind pocket'))
    ch.append(Check('NGV hub through-bore for rear carrier', 'unknown', None, None, 'm',
                    'finished through-bore and retained web support', 'unresolved',
                    'Supplier drawing shows a blind 48 mm pocket and central web. Define the finished through-bore, '
                    'remaining web/support material, and machining access before treating the rear carrier path as fit.'))
    # Tunnel rear end vs the rear carrier. The carrier's body/spigot geometry is not defined (it follows the
    # NGV hub decision); the stack envelopes overlap axially, so judge the joint with the stack's own BC-02
    # envelope rather than an assumed carrier body.
    bc2 = next(q for q in st['parts'] if q['id'] == 'BC-02')
    tu = next(q for q in st['parts'] if q['id'] == 'TU-01')
    overlap_x = min(bc2['x1'], tu['x1']) - max(bc2['x0'], tu['x0'])
    radial = bc2['r_out'] - tu['r_in']                      # > 0: carrier envelope larger than the tunnel bore
    if overlap_x > 0 and radial > 0:
        ch.append(Check('tunnel / rear carrier slip joint', 'unknown', radial, 0.0, 'm', '<= 0 (or a defined joint)',
                        'unresolved',
                        f'TU-01 (ID {2 * tu["r_in"] * 1e3:.2f} mm) and the BC-02 envelope (OD {2 * bc2["r_out"] * 1e3:.2f} mm) '
                        f'overlap {overlap_x * 1e3:.1f} mm axially; the sliding joint is not defined and depends on the '
                        'NGV hub decision'))
    else:
        ch.append(Check.compare('tunnel / rear carrier slip joint', max(radial, 0.0) if overlap_x > 0 else 0.0,
                                '<=', 0.0, 'm', 'design'))
    # shaft shoulders vs bearing abutment (typical catalog minimum ~12.5 mm for 10x26x8)
    ch.append(Check.compare('shaft body shoulder >= bearing abutment min', p['shaft_body_d_m'], '>=', 0.0125, 'm', 'assumption',
                            'typical catalog da_min for 7000 size; replace with supplier value'))
    # bores from the purchased-part records; the turbine seat is a journal-diameter section of the stack
    ch.append(Check('turbine bore / journal assembly fit', 'unknown',
                    p['tw_bore_d_m'] - p['shaft_journal_d_m'], None, 'm', 'approved clearance/interference interval',
                    'unresolved',
                    f'Nominal bore minus seat (negative = interference). A {p["tw_bore_d_m"] * 1e3:.3f} mm wheel bore does '
                    f'not slide freely onto a {p["shaft_journal_d_m"] * 1e3:.2f} mm seat. Measured tolerances, assembly '
                    'method (thermal), fit and hub stress need review.'))
    ch.append(Check('compressor bore / seat finished fit', 'unknown',
                    p['cw_bore_d_m'] - p['shaft_comp_seat_d_m'], None, 'm', 'approved clearance/interference interval',
                    'unresolved',
                    f'Nominal {p["shaft_comp_seat_d_m"] * 1e3:.2f} mm seat is an envelope, not a finished dimension for a '
                    f'{p["cw_bore_d_m"] * 1e3:.3f} mm bore. Set the finished diameter from the measured wheel and approved fit.'))
    ch.append(Check.compare('journal nominal matches selected bearing bore',
                            abs(p['shaft_journal_d_m'] - p['brg_bore_m']), '<=', 1e-9, 'm', 'design',
                            'nominal compatibility only; actual bearing fit remains unverified'))
    ch.append(Check.compare('nozzle exit smaller than turbine exit annulus OD', p['nozzle_exit_d_m'], '<=', p['tw_tip_d_m'], 'm', 'design'))
    # rear cover / NGV flange bolting: holes must sit on the flange land outside the NGV outer ring
    land_in = next(q['r_in'] for q in st['parts'] if q['id'] == 'CS-02')   # cover inner edge as built in the stack
    hole_in = R(p['ngv_bolt_pcd_m']) - R(p['ngv_bolt_hole_d_m'])
    hole_out = R(p['ngv_bolt_pcd_m']) + R(p['ngv_bolt_hole_d_m'])
    ch.append(Check.compare('rear cover inner edge clears NGV outer ring', land_in - R(p['ngv_outer_ring_od_m']), '>=', 0.0004,
                            'm', 'supplied'))
    ch.append(Check.compare('NGV flange bolt holes: edge distance to cover inner edge', hole_in - land_in, '>=', 0.0005, 'm',
                            'design', 'hot fasteners on the 6 mm flange land'))
    ch.append(Check.compare('NGV flange bolt holes: edge distance to flange OD', R(p['ngv_flange_od_m']) - hole_out, '>=',
                            0.001, 'm', 'design'))
    ch.append(Check.compare('nozzle starts at or behind the NGV casting rear face', x['nozzle_entry'] - x['ngv_ring_rear'],
                            '>=', 0.0, 'm', 'design'))
    # rotating rear end vs the static tailcone: no geometry defines a running clearance there yet
    protrusion = x['shaft_rear'] - x['nozzle_entry']
    if protrusion > 0:
        ch.append(Check('shaft end and turbine nut vs tailcone', 'unknown', protrusion, 0.0, 'm',
                        '<= 0 or a defined hollow tailcone clearance', 'unresolved',
                        f'shaft end and turbine nut reach {protrusion * 1e3:.1f} mm past the tailcone base plane; the '
                        'tailcone must be an open hollow shell with a running clearance, which is not defined'))
    else:
        ch.append(Check.compare('shaft end and turbine nut vs tailcone', protrusion, '<=', 0.0, 'm', 'design'))
    return ch


# ---------------------------------------------------------------------------- thermal growth
def tip_clearance_hot(p, T_tip_metal, T_shroud, N_rpm, alpha_wheel, alpha_shroud, E_wheel, rho_wheel=8000.0, nu=0.3):
    """Radial turbine tip clearance at steady state [m].

    Wheel: thermal growth of the tip radius at a uniform tip-metal temperature
    plus centrifugal rim growth of a solid disc (1-nu) rho w^2 b^3 / (4E), plus
    blade elongation approximated by the same strain field (small). Shroud:
    thermal growth of the finished bore radius. Transient closure (shroud cooling
    faster on shutdown) is NOT modelled and is listed as a test requirement.
    """
    r_tip = 0.5 * p['tw_tip_d_m']; b = 0.5 * p['tw_hub_d_m']
    omega = N_rpm * 2 * math.pi / 60
    dr_th = alpha_wheel * r_tip * (T_tip_metal - 293.0)
    dr_cf = (1 - nu) * rho_wheel * omega ** 2 * b ** 3 / (4 * E_wheel)
    blade_h = r_tip - b
    dr_blade = rho_wheel * omega ** 2 * (r_tip ** 2 - b ** 2) * 0.5 * blade_h / E_wheel * 0.5
    r_shroud = r_tip + p['tw_tip_clearance_m']
    dr_sh = alpha_shroud * r_shroud * (T_shroud - 293.0)
    return dict(cold_m=p['tw_tip_clearance_m'], hot_m=p['tw_tip_clearance_m'] + dr_sh - dr_th - dr_cf - dr_blade,
                wheel_thermal_m=dr_th, wheel_centrifugal_m=dr_cf + dr_blade, shroud_thermal_m=dr_sh)


def axial_growth(stack, T_shaft, T_tunnel, T_casing, alpha_shaft, alpha_tunnel, alpha_casing):
    """Steady relative axial growth [m] from the locating (front) bearing.

    Load paths: shaft carries the turbine aft; the casing (cool, compressor-delivery
    air) locates the NGV; the tunnel is assumed to slide in the rear carrier so it
    does not fight the casing. Returns NGV-rotor gap change and rear bearing
    float demand (to be taken by the preload spring).
    """
    x = stack['x']
    L_turb = x['tw_c'] - x['fb_c']
    L_rb = x['rb_c'] - x['fb_c']
    L_ngv = x['ngv_te'] - x['casing_front']
    shaft_turb = alpha_shaft * L_turb * (T_shaft - 293.0)
    shaft_rb = alpha_shaft * L_rb * (T_shaft - 293.0)
    casing = alpha_casing * L_ngv * (T_casing - 293.0)
    tunnel = alpha_tunnel * (x['ngv_le'] - x['backplate_rear']) * (T_tunnel - 293.0)
    return dict(rotor_aft_growth_m=shaft_turb, ngv_aft_growth_m=casing,
                ngv_rotor_gap_change_m=shaft_turb - casing,
                rear_bearing_float_m=shaft_rb - casing, tunnel_vs_casing_slip_m=tunnel - casing)


# ---------------------------------------------------------------------------- shaft stress
def shaft_stress(stack, torque_Nm, bending_moment_Nm, Kt_torsion=1.6, Kt_bending=2.0):
    """Peak nominal and concentrated stresses in the smallest loaded torque section.

    Torque passes from the turbine to the compressor through every section between
    them; the compressor seat (6 mm) carries full torque. Bending moment input is
    the unbalance/gyroscopic/manoeuvre estimate at the most loaded shoulder.
    """
    d_min = min(s.od for s in stack['sections'] if 'seat' in s.name or 'journal' in s.name or s.name == 'body')
    tau = 16 * torque_Nm / (math.pi * d_min ** 3)
    sig = 32 * bending_moment_Nm / (math.pi * d_min ** 3)
    return dict(d_min_m=d_min, tau_nom_Pa=tau, sigma_b_nom_Pa=sig,
                tau_peak_Pa=Kt_torsion * tau, sigma_b_peak_Pa=Kt_bending * sig,
                von_mises_peak_Pa=math.sqrt((Kt_bending * sig) ** 2 + 3 * (Kt_torsion * tau) ** 2))


# ---------------------------------------------------------------------------- liner buckling
def outer_liner_buckling(D_m, t_m, L_m, E_Pa, nu=0.3, knockdown=0.5):
    """Windenburg-Trilling short-cylinder external-pressure collapse estimate.

    p_cr = 2.42 E / (1-nu^2)^0.75 * (t/D)^2.5 / (L/D - 0.45 (t/D)^0.5)
    (US Experimental Model Basin formula for simply supported short cylinders),
    multiplied by an imperfection/perforation knockdown. Elastic; creep buckling at
    temperature is not covered.
    """
    tD, LD = t_m / D_m, L_m / D_m
    p_el = 2.42 * E_Pa / (1 - nu * nu) ** 0.75 * tD ** 2.5 / (LD - 0.45 * tD ** 0.5)
    return dict(p_cr_elastic_Pa=p_el, p_cr_knocked_down_Pa=knockdown * p_el, knockdown=knockdown)
