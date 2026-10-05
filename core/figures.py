"""Figures generated from the same run data (no hand-placed geometry)."""
from __future__ import annotations

import math

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt                     # noqa: E402
from matplotlib.patches import Polygon, Rectangle   # noqa: E402

from core.compressor_map import CompressorMap, LB_MIN_TO_KG_S   # noqa: E402
from core.records import ROOT                       # noqa: E402

STAMP = 'PRELIMINARY - NOT FOR MANUFACTURE'


def _save(fig, folder, name):
    for ext in ('png', 'svg'):
        fig.savefig(folder.path(f'figures/{name}.{ext}'), dpi=140, bbox_inches='tight')
    plt.close(fig)


def cross_section(res, folder, fp):
    st, x = res['stack'], res['stack']['x']
    comb, lay = res['comb'], res['layout']
    fig, ax = plt.subplots(figsize=(15, 6.2))
    mm = 1e3
    colors = dict(make='#9fb7d9', buy='#f2c06b', **{'buy+finish': '#f5a35c'})
    p = res['p_stack']
    stt = res['state']
    clr = 0.0003
    # compressor housing: inlet duct + shroud following the schematic wheel envelope + cover over the vanes
    ch = [(x['cw_nose'] - 0.008, p['cw_D1s_m'] / 2 + clr), (x['cw_nose'], p['cw_D1s_m'] / 2 + clr),
          (x['diffuser_cover'], p['cw_D2_m'] / 2 + clr), (x['diffuser_cover'], p['casing_od_m'] / 2),
          (x['cw_nose'] - 0.008, p['casing_od_m'] / 2)]
    ax.add_patch(Polygon([(a * mm, b * mm) for a, b in ch], closed=True, facecolor=colors['make'], edgecolor='k', lw=0.6, alpha=0.75))
    ax.text((x['cw_nose'] - 0.004) * mm, p['casing_od_m'] / 2 * mm + 0.6, 'CH-01', fontsize=6)
    # diffuser vane ring (between cover and diffuser floor)
    ax.add_patch(Rectangle((x['diffuser_cover'] * mm, stt['D_diff_le_m'] / 2 * mm), (x['diffuser_floor'] - x['diffuser_cover']) * mm,
                           (stt['D3_m'] - stt['D_diff_le_m']) / 2 * mm, facecolor='none', edgecolor='k', hatch='///', lw=0.6))
    ax.text(x['diffuser_cover'] * mm, stt['D3_m'] / 2 * mm + 0.6, 'vanes', fontsize=6)
    # backplate: recess under the wheel, seal bore, bearing pocket
    pocket_r = p['brg_od_m'] / 2 + 0.003
    seal_r = p['front_sleeve_od_m'] / 2 + 0.0001
    dfp = [(x['diffuser_floor'], p['cw_D2_ext_m'] / 2 + clr), (x['diffuser_floor'], p['backplate_od_m'] / 2),
           (x['backplate_rear'], p['backplate_od_m'] / 2), (x['backplate_rear'], pocket_r), (x['fb_front'] - 0.001, pocket_r),
           (x['fb_front'] - 0.001, seal_r), (p['backface_clearance_m'], seal_r), (p['backface_clearance_m'], p['cw_D2_ext_m'] / 2 + clr)]
    ax.add_patch(Polygon([(a * mm, b * mm) for a, b in dfp], closed=True, facecolor=colors['make'], edgecolor='k', lw=0.6, alpha=0.75))
    ax.text(x['backplate_rear'] * mm, p['backplate_od_m'] / 2 * mm - 4, 'DF-01', fontsize=6)
    for q in st['parts']:
        if q['id'] in ('CB-04', 'CB-05', 'EX-01', 'EX-02', 'SH-01', 'CW-01', 'TR-01', 'CH-01', 'DF-01'):
            continue
        ax.add_patch(Rectangle((q['x0'] * mm, q['r_in'] * mm), (q['x1'] - q['x0']) * mm, (q['r_out'] - q['r_in']) * mm,
                               facecolor=colors.get(q['make'], '#cccccc'), edgecolor='k', lw=0.6, alpha=0.75))
        ax.text(0.5 * (q['x0'] + q['x1']) * mm, q['r_out'] * mm + 0.6, q['id'], fontsize=6, ha='center')
    # liner discharge cones (actual end points)
    sc = comb['thermal_scale_ratio']
    r_ol, r_il = comb['outer_liner_id_cold_mm'] / 2 / mm, comb['inner_liner_od_cold_mm'] / 2 / mm
    for (r0, r1) in ((r_ol, p['ngv_tip_d_m'] / 2), (r_il, p['ngv_hub_d_m'] / 2)):
        ax.plot([x['liner_end'] * mm, x['ngv_front'] * mm], [r0 * mm, r1 * mm], 'k-', lw=1.6)
    # NGV vane passage (LE..TE between hub and tip)
    ax.add_patch(Rectangle((x['ngv_le'] * mm, p['ngv_hub_d_m'] / 2 * mm), (x['ngv_te'] - x['ngv_le']) * mm,
                           (p['ngv_tip_d_m'] - p['ngv_hub_d_m']) / 2 * mm, facecolor='none', edgecolor='k', hatch='\\', lw=0.6))
    # NGV blank hub: the 48 mm pocket is blind (centre web and boss on the supplier drawing).
    # The finished shaft/carrier passage is an open decision, so mark the region instead of
    # letting the envelopes read as an open bore.
    r_pocket = p['ngv_hub_pocket_d_m'] / 2
    ax.add_patch(Rectangle((x['ngv_front'] * mm, 0), (x['ngv_ring_rear'] - x['ngv_front']) * mm, r_pocket * mm,
                           facecolor='none', edgecolor='red', hatch='xx', lw=0.8, ls='--', alpha=0.5))
    ax.text(x['ngv_ring_rear'] * mm + 1, r_pocket * mm - 6, 'NGV blank: centre web + boss inside\nthe 48 mm pocket; '
            'shaft/carrier\npassage UNRESOLVED', fontsize=5.5, color='red')
    # shaft profile
    xs, rs = [], []
    for s in st['sections']:
        d = s.od / 0.85 if 'thread' in s.name else s.od
        xs += [s.z0 * mm, (s.z0 + s.length) * mm]
        rs += [d / 2 * mm, d / 2 * mm]
    ax.fill_between(xs, 0, rs, color='#666666', alpha=0.85, step=None, label='stepped shaft (SH-01)')
    # compressor wheel envelope (schematic)
    cw = Polygon([(x['cw_nose'] * mm, p['shaft_comp_seat_d_m'] / 2 * mm), (x['cw_nose'] * mm, p['cw_D1s_m'] / 2 * mm),
                  (-p['cw_super_back_m'] * mm - p['cw_b2_m'] * mm, p['cw_D2_m'] / 2 * mm),
                  (-p['cw_super_back_m'] * mm, p['cw_D2_ext_m'] / 2 * mm), (0, p['cw_D2_ext_m'] / 2 * mm),
                  (0, 7.0)], closed=True, facecolor='#f2c06b', edgecolor='k', lw=0.8)
    ax.add_patch(cw)
    ax.text(x['cw_nose'] * mm + 4, p['cw_D1s_m'] / 2 * mm - 8, 'CW-01\n(schematic\nenvelope)', fontsize=6)
    # turbine wheel
    ax.add_patch(Rectangle((x['rotor_le'] * mm, p['tw_hub_d_m'] / 2 * mm), p['tw_rim_width_m'] * mm,
                           (p['tw_tip_d_m'] - p['tw_hub_d_m']) / 2 * mm, facecolor='#f2c06b', edgecolor='k', lw=0.8))
    ax.add_patch(Rectangle((x['rotor_le'] * mm, p['tw_boss_d_m'] / 2 * mm), p['tw_rim_width_m'] * mm,
                           (p['tw_hub_d_m'] - p['tw_boss_d_m']) / 2 * mm, facecolor='#e8b45f', edgecolor='k', lw=0.6))
    ax.add_patch(Rectangle((x['boss_front'] * mm, p['shaft_journal_d_m'] / 2 * mm), p['tw_boss_total_m'] * mm,
                           (p['tw_boss_d_m'] - p['shaft_journal_d_m']) / 2 * mm, facecolor='#e8b45f', edgecolor='k', lw=0.6))
    ax.text(x['rotor_le'] * mm, p['tw_tip_d_m'] / 2 * mm + 1, 'TR-01', fontsize=6)
    # nozzle + tailcone
    pts = res['nozzle']['points']
    ax.plot([q['x_m'] * mm for q in pts], [q['r_outer_m'] * mm for q in pts], 'k-', lw=1.6)
    ax.plot([q['x_m'] * mm for q in pts if q['r_tailcone_m'] > 0] + [pts[0]['x_m'] * mm + p['tailcone_length_m'] * mm],
            [q['r_tailcone_m'] * mm for q in pts if q['r_tailcone_m'] > 0] + [0], 'k-', lw=1.2)
    ax.text(pts[-1]['x_m'] * mm, pts[-1]['r_outer_m'] * mm + 2, 'EX-01 exit', fontsize=6)
    # bearings
    for sp in st['supports']:
        ax.plot([sp.z * mm], [p['brg_od_m'] / 2 * mm * 0.75], 'rx', ms=9, mew=2)
    # combustor hole rows (outer and inner liner positions)
    for r in lay['rows']:
        if r['kind'] != 'main':
            continue
        rr = (comb['outer_liner_od_cold_mm'] / 2 if r['side'] == 'outer' else comb['inner_liner_id_cold_mm'] / 2)
        ax.plot([(x['dome'] + r['x_from_dome_m']) * mm] * 2, [rr - 2, rr + 2], color='firebrick', lw=2)
    for v in lay['vaporizers'][:1]:
        L = lay['vaporizer_stick']['straight_leg_m']
        rm = v['mean_diameter_m'] / 2
        ax.plot([x['dome'] * mm - 6, (x['dome'] + L) * mm], [rm * mm + 3, rm * mm + 3], color='darkgreen', lw=2)
        ax.plot([(x['dome'] + L) * mm, x['dome'] * mm + 10], [rm * mm - 3, rm * mm - 3], color='darkgreen', lw=2)
        ax.text(x['dome'] * mm + 8, rm * mm + 5, 'J-vaporizer (1 of n)', fontsize=6, color='darkgreen')
    ax.axhline(0, color='k', lw=0.8, ls='-.')
    ax.set_xlabel('x [mm] (aft +, origin = compressor wheel backface, cold)')
    ax.set_ylabel('r [mm]')
    ax.set_aspect('equal')
    ax.set_xlim(x['inlet_lip'] * mm - 5, x['nozzle_exit'] * mm + 10)
    ax.set_ylim(-3, p['casing_od_m'] / 2 * mm + 12)
    ax.set_title(f'PD-1 half cross-section from run data (fingerprint {fp[:12]}) - SCHEMATIC envelopes for purchased wheels; '
                 f'rectangles are part envelopes, not CAD geometry\n{STAMP}', fontsize=8)
    _save(fig, folder, 'cross_section')


def compressor_map(res, folder):
    cm = CompressorMap(ROOT / 'data/maps/gt3076r_compressor.yaml')
    fig, ax = plt.subplots(figsize=(9, 7))
    for ln in cm.lines:
        ax.plot(ln.q / LB_MIN_TO_KG_S, ln.pr, 'k-', lw=1)
        ax.text(ln.q[-1] / LB_MIN_TO_KG_S + 0.3, ln.pr[-1], f'{ln.n_corr:,.0f}', fontsize=7)
        sc = ax.scatter(ln.eta_q / LB_MIN_TO_KG_S, [float(ln._pr(q)) for q in ln.eta_q], c=ln.eta, cmap='viridis',
                        vmin=0.58, vmax=0.78, s=14, zorder=3)
    ax.plot([ln.q[0] / LB_MIN_TO_KG_S for ln in cm.lines], [ln.pr[0] for ln in cm.lines], 'r--', lw=1, label='digitized surge end')
    pts = [q for q in res['line'] if 'beta' in q]
    ax.plot([q['compressor']['Q_corr_kg_s'] / LB_MIN_TO_KG_S for q in pts], [q['compressor']['PR'] for q in pts], 'bo-',
            ms=4, label='PD-1 matched operating line (assumed turbine angles)')
    dp = res['design_point']
    ax.plot([dp['compressor']['Q_corr_kg_s'] / LB_MIN_TO_KG_S], [dp['compressor']['PR']], 'b*', ms=14, label='PD-1 design point')
    q_dp2 = cm.corrected_flow(0.30, 288.15, 101325 * 0.99) / LB_MIN_TO_KG_S
    ax.plot([q_dp2], [1.63], 'ms', ms=9, label='DP-2 prescribed point (0.30 kg/s, PR 1.63 @ 66 krpm)')
    plt.colorbar(sc, ax=ax, label='isentropic efficiency at digitized anchors')
    ax.set_xlabel('corrected flow [lb/min] (Garrett reference 545 R / 28.4 inHg - secondary source)')
    ax.set_ylabel('pressure ratio')
    ax.set_xlim(0, 60)
    ax.set_ylim(1.0, 2.6)
    ax.legend(fontsize=7, loc='upper left')
    ax.set_title('Garrett GT3076R map, digitized: RELATED-WHEEL PROXY for the 11+0 billet wheel\n' + STAMP, fontsize=9)
    _save(fig, folder, 'compressor_map_operating_line')


def campbell(res, folder):
    rd = res['rotor']
    fig, ax = plt.subplots(figsize=(8, 6))
    Ns = [c['N_rpm'] for c in rd['campbell']]
    nmax = max(len(c['modes']) for c in rd['campbell'])
    for k in range(nmax):
        for wh, style in (('forward', 'b-'), ('backward', 'g--')):
            ys = []
            for c in rd['campbell']:
                ms = [m['freq_rpm'] for m in c['modes'] if m['whirl'] == wh]
                ys.append(ms[k] if k < len(ms) else float('nan'))
            ax.plot(Ns, ys, style, lw=1, label=f'{wh} whirl' if k == 0 else None)
    ax.plot(Ns, Ns, 'k-', lw=1.2, label='1x synchronous')
    lo, hi = res['state']['N_operating_min_rpm'], res['state']['N_operating_max_rpm']
    ax.axvspan(lo, hi, color='orange', alpha=0.2, label='steady operating range')
    for c in rd['critical_speeds']:
        ax.plot([c['N_crit_rpm']], [c['N_crit_rpm']], 'ro')
        ax.text(c['N_crit_rpm'], c['N_crit_rpm'] * 1.04, f"{c['N_crit_rpm']:,.0f}", fontsize=7)
    ax.set_xlabel('shaft speed [rpm]')
    ax.set_ylabel('natural frequency [rpm-equivalent]')
    ax.set_ylim(0, 1.6 * hi)
    ax.legend(fontsize=7)
    ax.set_title('FE Campbell diagram (Rayleigh beam, gyroscopic, ASSUMED soft supports)\n' + STAMP, fontsize=9)
    _save(fig, folder, 'campbell')
    fig, ax = plt.subplots(figsize=(8, 5))
    for case, style in (('in_phase', '-'), ('opposed', '--')):
        r = [q for q in rd['unbalance']['response'] if q['case'] == case]
        ax.plot([q['N_rpm'] for q in r], [q['amp_turbine_m'] * 1e6 for q in r], 'r' + style, label=f'turbine wheel ({case})')
        ax.plot([q['N_rpm'] for q in r], [q['amp_compressor_m'] * 1e6 for q in r], 'b' + style, label=f'compressor wheel ({case})')
    ax.axvspan(lo, hi, color='orange', alpha=0.2)
    ax.set_xlabel('shaft speed [rpm]')
    ax.set_ylabel('orbit radius [um]')
    ax.legend(fontsize=7)
    ax.set_title(f'Unbalance response, ISO 1940 G{rd["unbalance"]["grade_G_mm_s"]} at max continuous (linear, assumed damping)\n'
                 + STAMP, fontsize=9)
    _save(fig, folder, 'unbalance_response')


def operating_line(res, folder, T04_max):
    pts = [q for q in res['line'] if 'beta' in q]
    N = [q['N_rpm'] for q in pts]
    fig, axs = plt.subplots(2, 2, figsize=(11, 7))
    axs[0, 0].plot(N, [q['T04_K'] for q in pts], 'r-o', ms=3, label='T04 combustor exit')
    axs[0, 0].plot(N, [q['stations']['T5_K'] for q in pts], 'm-o', ms=3, label='T5 turbine exit (~EGT)')
    axs[0, 0].axhline(T04_max, color='k', ls='--', lw=0.8, label='T04 screen (not an allowable)')
    axs[0, 0].set_ylabel('K'); axs[0, 0].legend(fontsize=7)
    axs[0, 1].plot(N, [q['thrust_N'] for q in pts], 'b-o', ms=3)
    axs[0, 1].set_ylabel('gross thrust [N]')
    axs[1, 0].plot(N, [q['compressor']['SM_flow'] for q in pts], 'g-o', ms=3, label='surge margin (flow)')
    axs[1, 0].plot(N, [q['turbine']['ngv_flow_fraction_of_max'] for q in pts], 'k-o', ms=3, label='NGV flow / choke flow')
    axs[1, 0].plot(N, [q['compressor']['eta'] for q in pts], 'c-o', ms=3, label='compressor eta')
    axs[1, 0].plot(N, [q['turbine']['eta_tt'] for q in pts], 'y-o', ms=3, label='turbine eta_tt (model)')
    axs[1, 0].legend(fontsize=7)
    axs[1, 1].plot(N, [q['flows']['fuel_kg_h'] for q in pts], 'k-o', ms=3)
    axs[1, 1].set_ylabel('fuel [kg/h]')
    for a in axs.flat:
        a.set_xlabel('shaft speed [rpm]')
        a.grid(alpha=0.3)
    fig.suptitle('PD-1 fixed-geometry operating line, zero starter torque (conditional on assumed turbine angles '
                 'and map proxy)\n' + STAMP, fontsize=9)
    _save(fig, folder, 'operating_line')


def write_all(case, recs, res, folder, log):
    cross_section(res, folder, folder.fp)
    compressor_map(res, folder)
    campbell(res, folder)
    operating_line(res, folder, case['engine'].get('T04_screen_max_K', 1150.0))
    log.append('figures: cross_section, compressor_map_operating_line, campbell, unbalance_response, operating_line')
