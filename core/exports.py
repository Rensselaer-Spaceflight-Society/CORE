"""Write CAD bundle, figures, systems budgets and cost tables for a candidate run."""
from __future__ import annotations

import math

from core import cad_export, cases
from core.records import ROOT

FRAME = dict(axis='x along engine centreline, positive aft (gas-flow direction)',
             origin='compressor wheel backface plane, cold, as assembled',
             radial='r from the axis', angular_zero='top dead centre',
             angular_positive='clockwise viewed from the front (looking aft)',
             reference_temperature_K=293.0,
             rotation='shaft rotation direction to be confirmed from the purchased wheels (compressor and turbine '
                      'blade handedness must agree) - see interface IF-ROT')


def _m(v):
    return v


def build_bundle(case, recs, res, fp):
    B = cad_export.Bundle(fp, case['case_id'])
    st, x, p = res['state'], res['stack']['x'], res['p_stack']
    c, t, n, a, b = recs['compressor'], recs['turbine'], recs['ngv'], recs['assembly'], recs['bearings']
    comb, lay = res['comb'], res['layout']
    sc = comb['thermal_scale_ratio']
    FP = 'fixed purchased geometry'
    # ---------------- compressor wheel (purchased)
    for nm, key, qt in (('CW01_EXDUCER_DIA', 'exducer_diameter', 'length'),
                        ('CW01_EXDUCER_EXT_TIP_DIA', 'exducer_extended_tip_diameter', 'length'),
                        ('CW01_INDUCER_DIA', 'inducer_diameter', 'length'),
                        ('CW01_EXIT_BLADE_HEIGHT', 'exducer_tip_height', 'length'),
                        ('CW01_SUPER_BACK_HEIGHT', 'super_back_height', 'length'),
                        ('CW01_BORE_DIA', 'bore_diameter', 'length')):
        B.add(nm, 'CW-01', qt, c.si(key), 'supplied', 'record compressor_wheel / Kinugawa listing',
              'supplier', 'purchased part', FP)
    B.add('CW01_FULL_BLADES', 'CW-01', 'count', c.param('full_blade_count')['value'], 'supplied', 'Kinugawa listing',
          'n/a', '', FP)
    B.add('CW01_INDUCER_HUB_DIA', 'CW-01', 'length', c.si('inducer_hub_diameter_assumed'), 'assumption',
          'record (hub/tip 0.33 assumption)', 'measure', 'needed for shroud contour', 'envelope only')
    B.add('CW01_AXIAL_LENGTH_ENVELOPE', 'CW-01', 'length', c.si('backface_to_nose_length_envelope'), 'assumption',
          'record envelope', 'measure', 'sets nut/thread stack', 'envelope only')
    B.add('CW01_SHROUD_CONTOUR', 'CW-01', 'length', None, 'unresolved', 'not published',
          note='Scan or measure the blade tip profile before machining the housing shroud.')
    B.add('CW01_MASS', 'CW-01', 'mass', c.si('mass_estimate'), 'assumption', 'record', 'weigh', '', 'envelope only')
    B.add('CW01_IP', 'CW-01', 'inertia', c.si('polar_inertia_estimate'), 'assumption', 'record', 'measure/CAD', '', 'envelope only')
    # ---------------- housing, diffuser/backplate
    D2 = st['D2_m']
    B.add('CH01_INDUCER_SHROUD_DIA', 'CH-01', 'length', c.si('inducer_diameter') + 2 * a.si('shroud_tip_clearance'),
          'design', 'inducer + 2 x shroud clearance', '+0.02/0 mm', 'sets tip clearance; machine to measured wheel', 'provisional design')
    B.add('CH01_OD', 'CH-01', 'length', a.si('casing_od'), 'design', 'matches casing OD', '+/-0.1 mm', 'flange register')
    B.add('DF01_FLOOR_X', 'DF-01', 'length', x['diffuser_floor'], 'calculated', 'flush with wheel hub disc face (super back)',
          '+/-0.05 mm', 'step at impeller exit; shim at assembly', 'provisional design')
    B.add('DF01_REAR_FACE_X', 'DF-01', 'length', x['backplate_rear'], 'design', 'assembly record')
    B.add('DF01_BACKFACE_RECESS_X', 'DF-01', 'length', a.si('backface_clearance'), 'design', 'assembly record',
          '+/-0.05 mm (shim)', 'running axial clearance to wheel backface')
    B.add('DF01_VANE_LE_DIA', 'DF-01', 'length', st['D_diff_le_m'], 'calculated', 'M11 vaneless ratio x D2', '+/-0.1 mm', '')
    B.add('DF01_EXIT_DIA', 'DF-01', 'length', st['D3_m'], 'design', 'case diffuser.exit_diameter_m', '+/-0.2 mm', '')
    B.add('DF01_VANE_COUNT', 'DF-01', 'count', st['n_vanes_diff_count'], 'design', 'case diffuser.vane_count (coprime with 11 blades)', 'n/a', '')
    B.add('DF01_CHANNEL_WIDTH', 'DF-01', 'length', st['b_diff_m'], 'design', 'case diffuser.channel_width_m',
          '+0.05/0 mm', 'flow area at throat; matches impeller exit height')
    B.add('DF01_EXIT_AXIAL_WIDTH', 'DF-01', 'length', res['diffuser']['exit_axial_width_m'], 'design',
          'channel width x exit growth (case)', '+0.1/0 mm', 'exit area ratio')
    B.add('DF01_FRONT_BEARING_POCKET_X0', 'DF-01', 'length', x['fb_front'] - 0.001, 'calculated', 'stack (recessed pocket)')
    B.add('DF01_VANE_LE_ANGLE', 'DF-01', 'angle', st['alpha_diff_le_deg'], 'calculated', 'M11 free-vortex flow angle (from radial)', '+/-1 deg', 'incidence')
    B.add('DF01_VANE_EXIT_ANGLE', 'DF-01', 'angle', res['diffuser']['alpha_exit_deg'], 'calculated', 'M11 (LE angle - turning)', '+/-1 deg', '')
    B.add('DF01_THROAT_WIDTH', 'DF-01', 'length', st['diff_throat_width_m'], 'calculated', 'M11 throat Mach target', '+/-0.05 mm',
          'sets diffuser capacity')
    B.add('DF01_SEAL_BORE_DIA', 'DF-01', 'length', a.si('front_sleeve_od') + 2 * a.si('labyrinth_radial_clearance'), 'design',
          'sleeve OD + 2 x labyrinth clearance', '+0.02/0 mm', 'leakage to tunnel')
    B.add('DF01_OD', 'DF-01', 'length', a.si('backplate_od'), 'design', 'assembly record', 'g6 to casing ID', 'spigot register')
    # ---------------- shaft and rotating stack
    for s in res['stack']['sections']:
        # thread sections carry the minor diameter in the rotor model; CAD gets the nominal size
        tag = s.name.split(' (')[0].upper().replace(' ', '_').replace('-', '_')
        dia = s.od / 0.85 if 'thread' in s.name else s.od
        tol, why = ('general', 'nominal thread size; the rotor model uses 0.85 x nominal as the minor diameter') \
            if 'thread' in s.name else ('general', '')
        if 'journal' in s.name:
            tol, why = 'k5 (+0.001/+0.007 mm)', 'bearing inner-ring light interference (confirm supplier fit table)'
        elif 'turbine seat' in s.name:
            tol, why = 'UNRESOLVED - supplier/fit review required', '10 mm envelope vs 9.99 mm bore; thermal assembly and hub stress unverified'
        elif 'compressor seat' in s.name:
            tol, why = 'grind to measured bore -0.002/-0.006 mm', 'aluminium wheel slip/transition fit'
        fit_pending = 'seat' in s.name and ('compressor' in s.name or 'turbine' in s.name)
        B.add(f'SH01_{tag}_DIA', 'SH-01', 'length', dia, 'assumption' if fit_pending else 'design',
              'assembly record / core.assembly', tol, why,
              status='envelope only' if fit_pending else 'provisional design')
        B.add(f'SH01_{tag}_X0', 'SH-01', 'length', s.z0, 'calculated', 'core.assembly stack')
        B.add(f'SH01_{tag}_LEN', 'SH-01', 'length', s.length, 'calculated', 'core.assembly stack')
    for tag in ('COMPRESSOR', 'TURBINE'):
        B.add(f'SH01_{tag}_FINISHED_SEAT_DIA', 'SH-01', 'length', None, 'unresolved',
              'measured bore and approved fit required', note='Do not machine the nominal envelope diameter.')
    B.add('SH01_SHOULDER_FILLET_R', 'SH-01', 'length', a.si('shoulder_fillet_r'), 'design', 'assembly record',
          'max', 'below bearing inner-ring chamfer')
    B.add('SH01_MASS', 'SH-01', 'mass', res['stack']['shaft_mass_kg'], 'calculated', 'stack sections x 7850 kg/m3')
    B.add('ROT_MASS', 'ROTOR', 'mass', res['stack']['rotor_mass_kg'], 'calculated', 'stack (wheel masses estimated)')
    B.add('ROT_CG_X', 'ROTOR', 'length', res['stack']['rotor_cg_x_m'], 'calculated', 'stack')
    B.add('ROT_IP', 'ROTOR', 'inertia', res['stack']['rotor_Ip_kg_m2'], 'calculated', 'stack')
    B.add('SL01_FRONT_SLEEVE_OD', 'SL-01', 'length', a.si('front_sleeve_od'), 'design', 'assembly record', 'h6', 'seal + ring abutment')
    B.add('SL01_FRONT_SLEEVE_LEN', 'SL-01', 'length', x['fb_front'], 'calculated', 'stack', '+/-0.01 mm', 'clamp stack length')
    B.add('SL02_REAR_SPACER_OD', 'SL-02', 'length', a.si('rear_spacer_od'), 'design', 'assembly record')
    B.add('SL02_REAR_SPACER_LEN', 'SL-02', 'length', a.si('rear_spacer_length'), 'design', 'assembly record', '+/-0.01 mm',
          'sets turbine axial position vs NGV')
    # ---------------- bearings and carriers
    B.add('BR_BORE', 'BR-01/02', 'length', b.si('bore'), 'supplied', 'Monton MTSV7000 listing', 'supplier', '', FP)
    B.add('BR_OD', 'BR-01/02', 'length', b.si('outer_diameter'), 'supplied', 'Monton MTSV7000 listing', 'supplier', '', FP)
    B.add('BR_WIDTH', 'BR-01/02', 'length', b.si('width'), 'supplied', 'Monton MTSV7000 listing', 'supplier', '', FP)
    B.add('BR01_CENTRE_X', 'BR-01', 'length', x['fb_c'], 'calculated', 'stack')
    B.add('BR02_CENTRE_X', 'BR-02', 'length', x['rb_c'], 'calculated', 'stack')
    B.add('BC01_BORE', 'BC-01', 'length', b.si('outer_diameter'), 'design', 'bearing OD', 'J6 (locating)',
          'front bearing locates the rotor axially')
    B.add('BC02_BORE', 'BC-02', 'length', b.si('outer_diameter'), 'design', 'bearing OD', 'G6 (floating)',
          'rear outer ring slides under wave-spring preload')
    B.add('BC02_SPIGOT_OD', 'BC-02', 'length', n.si('hub_ring_bore'), 'design', 'NGV blank hub pocket 48 mm (blind, centre web)',
          'g6', 'locates rear carrier in NGV hub; hot', 'envelope only',
          note='Depends on the open NGV hub decision (IF-BC2-NG, NG01_HUB_THROUGH_BORE_FINISHED): bore the web and keep '
               'the pocket, remove the web, or support the rear bearing elsewhere.')
    B.add('BC_SUPPORT_STIFFNESS_TARGET', 'BC-01/02', 'stiffness', st['k_support_N_m'], 'assumption',
          'case rotor_support (soft elastomer mount)', 'n/a', 'rotordynamic design target; verify by test')
    B.add('BC01_SLEEVE_OD', 'BC-01', 'length', None, 'unresolved',
          'sleeve OD = backplate pocket diameter, with O-ring grooves; not designed yet',
          note='The figure draws bearing OD + 6 mm as a placeholder; the stack envelope only bounds it by the tunnel ID.')
    # ---------------- tunnel, casing
    B.add('TU01_OD', 'TU-01', 'length', a.si('tunnel_od_stock'), 'design', '2 in tube stock (C02)', 'stock')
    B.add('TU01_WALL', 'TU-01', 'length', a.si('tunnel_wall_stock'), 'design', '0.065 in stock wall (C02)', 'stock')
    B.add('TU01_X0', 'TU-01', 'length', x['backplate_rear'], 'calculated', 'stack')
    B.add('TU01_X1', 'TU-01', 'length', x['ngv_front'] - 0.001, 'calculated', 'stack', note='rear end slides in BC-02 (slip joint)')
    B.add('CS01_OD', 'CS-01', 'length', a.si('casing_od'), 'design', 'DP-2 envelope', '+/-0.3 mm', 'rolled sheet')
    B.add('CS01_WALL', 'CS-01', 'length', a.si('casing_wall_stock'), 'design', '0.060 in sheet (C01)', 'stock')
    B.add('CS01_X0', 'CS-01', 'length', x['casing_front'], 'calculated', 'stack')
    B.add('CS01_X1', 'CS-01', 'length', x['casing_rear_cover'], 'calculated', 'stack')
    B.add('CS01_FRONT_BOLTS', 'CS-01', 'count', a.param('casing_front_bolt_count')['value'], 'design', 'assembly record', 'n/a',
          '', note='M4 into backplate rim, equally spaced from 15 deg')
    B.add('CS02_REAR_COVER_ID', 'CS-02', 'length', n.si('outer_ring_od') + 0.001, 'design', 'NGV outer ring OD + 1 mm',
          '+0.2/0 mm', 'must clear the NGV outer ring; bolts on the flange land')
    # ---------------- combustor
    B.add('CB_DOME_X', 'CB-01', 'length', x['dome'], 'calculated', 'stack')
    B.add('CB02_OUTER_LINER_OD', 'CB-02', 'length', comb['outer_liner_od_cold_mm'] / 1e3, 'calculated', 'M20 (cold)',
          '+/-0.3 mm', 'rolled sheet; annulus area')
    B.add('CB02_OUTER_LINER_ID', 'CB-02', 'length', comb['outer_liner_id_cold_mm'] / 1e3, 'calculated', 'M20 (cold)', '+/-0.3 mm')
    B.add('CB03_INNER_LINER_OD', 'CB-03', 'length', comb['inner_liner_od_cold_mm'] / 1e3, 'calculated', 'M20 (cold)', '+/-0.3 mm')
    B.add('CB03_INNER_LINER_ID', 'CB-03', 'length', comb['inner_liner_id_cold_mm'] / 1e3, 'calculated', 'M20 (cold)', '+/-0.3 mm')
    B.add('CB_LINER_LENGTH', 'CB-02/03', 'length', comb['chamber_length_cold_mm'] / 1e3, 'calculated', 'M20 (cold)', '+/-0.5 mm')
    B.add('CB_LINER_WALL', 'CB-02/03', 'length', comb['liner_wall_thickness_mm'] / sc / 1e3, 'design',
          '0.060 in sheet (cold); M20 rated at this stock', 'stock')
    B.add('CB_TRANSITION_LENGTH', 'CB-04/05', 'length', a.si('transition_length'), 'design', 'assembly record')
    B.add('CB04_OUTER_CONE_END_DIA', 'CB-04', 'length', n.si('vane_tip_diameter'), 'assumption',
          'NGV vane tip diameter (assumed)', 'fit to measured NGV outer ring', '', 'provisional design')
    B.add('CB05_INNER_CONE_END_DIA', 'CB-05', 'length', n.si('vane_hub_diameter'), 'supplied', 'NGV85 hub ring OD',
          'slip fit +0.1/+0.3 mm', 'thermal growth allowance')
    for zone, v in lay['zone_lengths_cold_m'].items():
        B.add(f'CB_ZONE_{zone.upper()}_LEN', 'CB-02/03', 'length', v, 'calculated', 'M20 zone split (cold)')
    for r in lay['rows']:
        tag = f"CB_{r['side'].upper()}_{r['row'].upper()}"
        B.add(f'{tag}_X', 'CB-02' if r['side'] == 'outer' else 'CB-03', 'length', r['x_from_dome_m'], 'calculated',
              'postprocess.combustor_layout rule (x from dome face)', '+/-0.3 mm', 'jet location')
        B.add(f'{tag}_DIA', 'CB-02' if r['side'] == 'outer' else 'CB-03', 'length', r['dia_m'], 'calculated',
              'M20 (cold)', '+/-0.05 mm', 'flow area (sets branch split)')
        B.add(f'{tag}_COUNT', 'CB-02' if r['side'] == 'outer' else 'CB-03', 'count', r['count'], 'calculated', 'M20', 'n/a', '')
    B.add('VP_COUNT', 'VP-01', 'count', comb['vap_n'], 'calculated', 'M20 pitch rule')
    B.add('VP_TUBE_OD_MODEL', 'VP-01', 'length', comb['vap_od_mm'] / 1e3, 'calculated', 'M20 sizing',
          'rerate to stock', 'see stock note', note='nearest stock 1/4 in (6.35 mm) x 0.035 in; rerate before release')
    B.add('VP_TUBE_ID_MODEL', 'VP-01', 'length', comb['vap_id_mm'] / 1e3, 'calculated', 'M20 sizing')
    B.add('VP_CRIMP_DIA', 'VP-01', 'length', comb['vap_crimp_dia_mm'] / 1e3, 'calculated', 'M20 pressure allocation', '+/-0.05 mm')
    B.add('VP_SCOOP_DIA', 'VP-01', 'length', comb['vap_scoop_dia_mm'] / 1e3, 'calculated', 'M20 pressure allocation', '+/-0.05 mm')
    stick = lay['vaporizer_stick']
    B.add('VP_STRAIGHT_LEG', 'VP-01', 'length', stick['straight_leg_m'], 'design', 'J-stick rule 0.6 L')
    B.add('VP_BEND_RADIUS', 'VP-01', 'length', stick['bend_centerline_radius_m'], 'calculated', 'M20 1.5 x OD')
    B.add('VP_FIRST_ANGLE', 'VP-01', 'angle', 0.0, 'design', 'clocking rule: vaporizer 0 at top dead centre')
    B.add('IG_ANGLE', 'IG-01', 'angle', lay['igniter']['angle_deg'], 'design', 'midway between vaporizers 0 and 1')
    B.add('IG_X_FROM_DOME', 'IG-01', 'length', lay['igniter']['x_from_dome_m'], 'design', 'mid primary zone')
    # ---------------- NGV and turbine
    B.add('NG01_HUB_THROUGH_BORE_FINISHED', 'NG-01', 'length', None, 'unresolved',
          'JETMAX blank drawing has a centre web; finished carrier/shaft passage is not defined',
          note='Requires machining plan and remaining-web/hub strength review before CAD release.')
    B.add('NG01_HUB_DIA', 'NG-01', 'length', n.si('vane_hub_diameter'), 'supplied', 'JETMAX NGV85 blank drawing', 'supplier', '', FP)
    B.add('NG01_TIP_DIA', 'NG-01', 'length', n.si('vane_tip_diameter'), 'assumption', 'inferred, not dimensioned', 'measure', '', 'envelope only')
    B.add('NG01_FLANGE_OD', 'NG-01', 'length', n.si('flange_od'), 'supplied', 'JETMAX NGV85 blank drawing', 'supplier', '', FP)
    B.add('NG01_SHROUD_BORE_FINISH', 'NG-01', 'length', t.si('tip_diameter') + 2 * t.si('tip_clearance_design'), 'design',
          'wheel tip + 2 x cold clearance', '+0.02/0 mm', 'sets turbine tip clearance; machine after measuring wheel')
    B.add('NG01_BOLT_PCD', 'NG-01', 'length', a.si('ngv_flange_pcd'), 'design', 'assembly record', '+/-0.1 mm',
          'hole edge distance on a 6 mm land')
    B.add('NG01_BOLTS', 'NG-01', 'count', a.param('ngv_flange_bolt_count')['value'], 'design', 'assembly record', 'n/a', '',
          note='M3 A286 or equivalent hot-strength bolts')
    B.add('NG01_BOLT_HOLE', 'NG-01', 'length', a.si('ngv_flange_bolt_hole'), 'design', 'M3 clearance')
    B.add('NG01_FRONT_X', 'NG-01', 'length', x['ngv_front'], 'calculated', 'stack (casting front face)')
    B.add('NG01_VANE_LE_X', 'NG-01', 'length', x['ngv_le'], 'calculated', 'stack (vane TE one axial gap ahead of the rotor)')
    B.add('NG01_FLANGE_FRONT_X', 'NG-01', 'length', x['ngv_flange_front'], 'calculated', 'stack (casing rear cover face)')
    B.add('NG01_VANE_COUNT', 'NG-01', 'count', n.param('vane_count_estimate')['value'], 'assumption', 'drawing estimate', 'count part', '', 'envelope only')
    B.add('NG01_EXIT_ANGLE', 'NG-01', 'angle', n.param('exit_flow_angle')['value'], 'assumption', 'typical value', 'measure', '', 'envelope only')
    B.add('NG01_THROAT_AREA_ASSUMED', 'NG-01', 'area', st['A_throat_ngv_m2'], 'assumption', 'annulus x cos(assumed angle)',
          'measure', 'highest-value measurement', 'envelope only')
    for nm, key, qt in (('TR01_TIP_DIA', 'tip_diameter', 'length'), ('TR01_HUB_DIA', 'hub_diameter', 'length'),
                        ('TR01_BORE_DIA', 'bore_diameter', 'length'), ('TR01_BOSS_DIA', 'hub_boss_diameter', 'length'),
                        ('TR01_RIM_WIDTH', 'blade_axial_width_at_rim', 'length'), ('TR01_BOSS_LENGTH', 'hub_boss_total_length', 'length'),
                        ('TR01_BOSS_SIDE_A', 'hub_boss_protrusion_side_a', 'length')):
        B.add(nm, 'TR-01', qt, t.si(key), 'supplied', 'JETMAX TW85 finished drawing', 'supplier', '', FP)
    B.add('TR01_ROTOR_LE_X', 'TR-01', 'length', x['rotor_le'], 'calculated', 'stack')
    B.add('TR01_BLADE_COUNT', 'TR-01', 'count', t.param('blade_count_estimate')['value'], 'assumption', 'drawing estimate', 'count', '', 'envelope only')
    B.add('TR01_MASS', 'TR-01', 'mass', t.si('mass_estimate'), 'calculated', 'envelope estimate', 'weigh', '', 'envelope only')
    B.add('TR01_IP', 'TR-01', 'inertia', t.si('polar_inertia_estimate'), 'calculated', 'envelope estimate', 'measure', '', 'envelope only')
    B.add('TR01_BLADE_SECTIONS', 'TR-01', 'length', None, 'unresolved', 'not published',
          note='Do not model purchased blade profiles from guesses; scan or obtain supplier CAD.')
    # ---------------- exhaust, inlet
    noz = res['nozzle']
    B.add('EX01_ENTRY_DIA', 'EX-01', 'length', 2 * noz['points'][0]['r_outer_m'], 'design', 'shroud bore')
    B.add('EX01_EXIT_DIA', 'EX-01', 'length', 2 * noz['points'][-1]['r_outer_m'], 'design',
          'matched nozzle area (case)', '+/-0.2 mm', 'area +/-0.75 % moves T04 (see robustness)')
    B.add('EX01_LENGTH', 'EX-01', 'length', a.si('nozzle_length'), 'design', 'assembly record')
    B.add('EX01_HALF_ANGLE', 'EX-01', 'angle', noz['half_angle_deg'], 'calculated', 'contour')
    B.add('EX02_TAILCONE_LENGTH', 'EX-02', 'length', a.si('tailcone_length'), 'design', 'assembly record')
    B.add('EX02_TAILCONE_BASE_DIA', 'EX-02', 'length', t.si('hub_diameter'), 'supplied', 'turbine hub diameter')
    B.add('IN01_LIP_RADIUS', 'IN-01', 'length', a.si('bellmouth_lip_radius'), 'design', 'assembly record')
    B.add('IN01_LENGTH', 'IN-01', 'length', a.si('bellmouth_length'), 'design', 'assembly record')
    B.add('ENGINE_LENGTH', 'ASSY', 'length', res['stack']['engine_length_m'], 'calculated', 'inlet lip to nozzle exit')
    # ---------------- interfaces
    I = B.interface
    I('IF-ROT', 'CW-01', 'TR-01', 'rotation direction / blade handedness', relation='must agree',
      note='Inspect both purchased wheels; record rotation viewed from front before machining the NGV/diffuser vanes.')
    I('IF-CW-SH', 'CW-01', 'SH-01', 'wheel bore on compressor seat', x['cw_nose'], c.si('bore_diameter'),
      'slip/transition proposed; finished seat diameter unresolved',
      'clamped by M6 nut against seal sleeve; seat from the measured bore (SH01_COMPRESSOR_FINISHED_SEAT_DIA)')
    I('IF-CW-DF', 'CW-01', 'DF-01', 'backface running clearance', 0.0, None, f'{a.si("backface_clearance")*1e3:.2f} mm axial')
    I('IF-SL-BR1', 'SL-01', 'BR-01', 'sleeve face on bearing inner ring', x['fb_front'], a.si('front_sleeve_od'), 'clamp')
    I('IF-SH-BR1', 'SH-01', 'BR-01', 'front journal', x['fb_c'], st['shaft_journal_d_m'], 'k5 light interference')
    I('IF-BR1-BC1', 'BR-01', 'BC-01', 'front bearing (locating) in steel sleeve', x['fb_c'],
      b.si('outer_diameter'), 'J6 + retaining ring', 'sleeve shoulder takes forward thrust')
    I('IF-BC1-DF', 'BC-01', 'DF-01', 'bearing sleeve in backplate hub pocket on two O-rings (soft damped mount)', x['fb_c'],
      None, 'O-ring radial squeeze; anti-rotation pin', 'pocket recessed 6 mm into the backplate hub to shorten the overhang')
    I('IF-DF-CS', 'DF-01', 'CS-01', 'backplate rim spigot in casing', x['diffuser_floor'], a.si('backplate_od'), 'g6/H7, 12 x M4')
    I('IF-TU-DF', 'TU-01', 'DF-01', 'tunnel front end on backplate rear spigot', x['backplate_rear'], a.si('tunnel_od_stock'),
      'press/retained')
    I('IF-TU-BC2', 'TU-01', 'BC-02', 'tunnel rear end slip joint', x['ngv_front'], a.si('tunnel_od_stock'),
      'sliding; joint geometry UNRESOLVED',
      'tunnel must not fight the casing load path; the joint is not defined by the envelopes (tunnel ID < carrier '
      'spigot envelope) and depends on the NGV hub decision (IF-BC2-NG)')
    I('IF-BC2-NG', 'BC-02', 'NG-01', 'rear carrier in NGV hub pocket; centre-web passage unresolved',
      x['ngv_front'], n.si('hub_ring_bore'), 'UNRESOLVED - finish-machining and fit review',
      '48 mm is a blind pocket in the blank drawing, not a finished through bore')
    I('IF-BR2-BC2', 'BR-02', 'BC-02', 'rear housing bore, floating with wave-spring preload', x['rb_c'], b.si('outer_diameter'),
      'G6 sliding')
    I('IF-SH-TR', 'SH-01', 'TR-01', 'turbine bore on seat', x['boss_front'], t.si('bore_diameter'), 'fit unresolved',
      'M8 clamp proposal; nominal interference, hub stress and assembly over the journal require review')
    I('IF-TR-NG-TIP', 'TR-01', 'NG-01', 'tip clearance to finished shroud', x['rotor_le'], t.si('tip_diameter'),
      f'{t.si("tip_clearance_design")*1e3:.2f} mm radial cold')
    I('IF-TR-NG-AX', 'TR-01', 'NG-01', 'NGV TE to rotor LE gap', x['ngv_te'], None, f'{a.si("ngv_rotor_axial_gap")*1e3:.1f} mm cold')
    I('IF-CB-NG', 'CB-04/05', 'NG-01', 'liner discharge cones slip onto NGV outer ring / hub ring', x['ngv_front'], None,
      'sliding, liners located at rear', 'liner thermal growth ~1 mm axial taken at the dome supports')
    I('IF-CB-CS', 'CB-01', 'CS-01', 'dome radial pins (3 at 120 deg) in casing slots', x['dome'], None,
      'radial + axial sliding', 'allows liner growth; vaporizer fuel needles enter sticks with clearance')
    I('IF-NG-CS2', 'NG-01', 'CS-02', 'NGV flange front face to casing rear cover', x['ngv_flange_front'], n.si('flange_od'),
      '12 x M3 hot fasteners + gasket', 'x is the mating face (flange front face); the cover plate lies just ahead of it')
    I('IF-EX-NG', 'EX-01', 'NG-01', 'nozzle flange to NGV flange rear', x['nozzle_entry'], None, 'shared bolts')
    I('IF-FUEL', 'FU-01', 'CS-01', 'fuel manifold through casing to vaporizer needles', x['dome'] - 0.004, None,
      'fitting + needles', f'{int(comb["vap_n"])} needles; liquid fuel budget separate from vaporizer air budget')
    I('IF-IGN', 'IG-01', 'CS-01/CB-02', 'igniter boss', x['dome'] + lay['igniter']['x_from_dome_m'], None, 'M10 boss', '')
    I('IF-STARTER', 'ST-01', 'CW-01', 'starter cone on compressor nut', x['comp_nut_front'], None,
      'one-way clutch, disengaging', 'starter bracket struts in inlet add inlet blockage (in inlet loss allowance)')
    I('IF-MOUNT', 'CS-01', 'stand', 'two clamp bands on casing to stand plate', x['casing_front'] + 0.03, a.si('casing_od'),
      'band clamps', 'second band at x_casing_rear - 30 mm')
    # ---------------- patterns and sections
    B.patterns['combustor_rows'] = lay['rows']
    B.patterns['vaporizers'] = lay['vaporizers']
    B.patterns['vaporizer_stick'] = lay['vaporizer_stick']
    B.patterns['igniter'] = lay['igniter']
    B.patterns['diffuser_vanes'] = dict(count=int(st['n_vanes_diff_count']), le_diameter_mm=st['D_diff_le_m'] * 1e3,
                                        exit_diameter_mm=st['D3_m'] * 1e3, le_angle_from_radial_deg=st['alpha_diff_le_deg'],
                                        exit_angle_from_radial_deg=res['diffuser']['alpha_exit_deg'],
                                        first_vane_angle_deg=0.0,
                                        rule='equally spaced; endpoint angles are flow targets, not a finished vane curve',
                                        geometry_status='curved centreline, thickness and throat transitions unresolved')
    B.patterns['fasteners'] = dict(casing_front=dict(count=int(a.param('casing_front_bolt_count')['value']), size='M4',
                                                     first_angle_deg=15.0, pcd_mm=a.si('casing_od') * 1e3 - 6.0),
                                   ngv_flange=dict(count=int(a.param('ngv_flange_bolt_count')['value']), size='M3 hot-strength',
                                                   first_angle_deg=15.0, pcd_mm=a.si('ngv_flange_pcd') * 1e3))
    B.patterns['sensor_ports'] = [
        dict(id='P03', what='compressor delivery static tap (outer annulus)', x_mm=x['dome'] * 1e3, angle_deg=90.0, thread='1/8 NPT boss'),
        dict(id='T03', what='compressor delivery thermocouple (bead, outer annulus)', x_mm=x['dome'] * 1e3, angle_deg=270.0, thread='M6 compression'),
        dict(id='EGT', what='exhaust gas temperature probe (3 mm sheathed K, nozzle entry)', x_mm=(x['nozzle_entry'] + 0.01) * 1e3,
             angle_deg=45.0, thread='M8 compression', note='EGT is NOT turbine inlet temperature'),
        dict(id='PF', what='fuel pressure transducer at manifold inlet', x_mm=None, angle_deg=None, thread='1/8 NPT tee'),
        dict(id='N', what='speed pickup at compressor nut (optical or Hall with magnet)', x_mm=x['comp_nut_front'] * 1e3,
             angle_deg=0.0, thread='bracket in inlet'),
    ]
    B.sections['nozzle_contour'] = [dict(x_mm=q['x_m'] * 1e3, r_outer_mm=q['r_outer_m'] * 1e3, r_tailcone_mm=q['r_tailcone_m'] * 1e3)
                                    for q in noz['points']]
    prof = []
    for s in res['stack']['sections']:
        d = s.od / 0.85 if 'thread' in s.name else s.od
        prof += [dict(x_mm=s.z0 * 1e3, r_mm=d * 500), dict(x_mm=(s.z0 + s.length) * 1e3, r_mm=d * 500)]
    B.sections['shaft_profile'] = prof
    B.sections['shaft_profile_status'] = 'nominal envelope only; finished wheel fits unresolved'
    B.sections['stations_mm'] = {k: v * 1e3 for k, v in x.items()}
    return B


def write_all(case, recs, res, folder, log):
    fp = folder.fp
    B = build_bundle(case, recs, res, fp)
    notes = ['Cold (293 K) build dimensions unless a parameter says otherwise.',
             'Purchased-part values are copied from supplier records; do not rescale them.',
             'Parameters with status "unresolved - do not model" have no value; obtain the measurement first.',
             'Tolerances are proposals with a reason; general tolerance ISO 2768-m elsewhere.',
             'This bundle has not been rebuilt in native CAD by the software; no CAD rebuild is claimed.']
    folder.write_json('cad/cad_bundle.json', cases.clean_floats(B.to_json(FRAME, notes)))
    folder.write_text('cad/cad_parameters.csv', B.to_csv())
    # read back and validate
    cad_export.read_bundle(folder.path('cad/cad_bundle.json'), expected_fingerprint=fp)
    log.append(f'CAD bundle: {len(B.params)} parameters, {len(B.interfaces)} interfaces; read-back validated')
    from core import figures, systems, budget
    figures.write_all(case, recs, res, folder, log)
    systems.write_all(case, recs, res, folder, log)
    budget.write_all(case, recs, res, folder, log)
