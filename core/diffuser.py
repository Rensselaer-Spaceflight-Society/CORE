"""Preliminary vaned (channel/wedge) radial diffuser geometry and checks.

Geometry chain from the impeller exit (D2, b2, Cm2, Ctheta2):

  vaneless space  D2 -> D3 = vaneless_ratio * D2, width b3 = width_ratio * b2.
                  Free-vortex swirl r Ctheta = const (wall friction neglected),
                  meridional velocity from continuity -> leading-edge flow angle
                  alpha3 (from radial). Vanes are set at zero incidence to it.
  throat          total area for a chosen throat Mach number (isentropic from the
                  stage exit total state); compared with the opening available at
                  the leading-edge pitch, o_max = (pi D3 / Z) cos(alpha3).
  channel         mean-line estimate to the exit diameter D4 with an
                  exit flow angle alpha4 = alpha3 - turning; area ratio, length,
                  equivalent divergence angle and exit velocity/Mach. Independent
                  endpoint angles do not define a straight channel; the finished
                  vane curve, thickness and throat transitions remain unresolved.

Loss accounting: the published compressor map already includes Garrett's own
diffuser and volute between the wheel and its pressure-measurement plane. The
CORE vaned diffuser is assumed to perform at least as well, so NO separate
diffuser total-pressure loss is subtracted (that would double count). The
static-pressure recovery coefficient is an assumption reported for the team's
CFD/rig comparison. The 90-degree turn and deswirl into the combustor annuli is
a separate loss, estimated here as K_turn * q_exit and compared with the
pressure-ledger allowance in the matching model.
"""
from __future__ import annotations

import math

from core import gas, thermo


def design(mdot, T0, P0, D2, b2, Cm2, Ct2, vaneless_ratio, D4, n_vanes, width_ratio=1.0,
           M_throat=0.70, exit_turning_deg=12.0, cp_assumed=0.60, turn_K=1.0, R=287.05, exit_width_growth=1.0):
    for k, v in dict(mdot=mdot, T0=T0, P0=P0, D2=D2, b2=b2, Cm2=Cm2, vaneless_ratio=vaneless_ratio,
                     D4=D4, width_ratio=width_ratio).items():
        thermo.positive(**{k: v})
    if not 1.0 < vaneless_ratio < D4 / D2:
        raise ValueError('vaneless ratio must place the vane leading edge between D2 and the exit')
    if n_vanes < 5 or n_vanes != int(n_vanes):
        raise ValueError('diffuser vane count must be an integer >= 5')
    if not 0.2 < M_throat < 0.95:
        raise ValueError('throat Mach target outside the subsonic design range')
    D3 = vaneless_ratio * D2
    b3 = width_ratio * b2
    Ct3 = Ct2 * D2 / D3
    Cm3 = Cm2 * (D2 * b2) / (D3 * b3)
    for _ in range(60):          # continuity with static density
        T3, P3 = thermo.static(T0, P0, math.hypot(Cm3, Ct3), R=R)
        rho3 = P3 / (R * T3)
        Cm_new = mdot / (rho3 * math.pi * D3 * b3)
        if abs(Cm_new - Cm3) < 1e-10:
            break
        Cm3 = Cm_new
    C3 = math.hypot(Cm3, Ct3)
    alpha3 = math.degrees(math.atan2(Ct3, Cm3))
    g3 = thermo.gamma(T3, R=R)
    M3 = C3 / math.sqrt(g3 * R * T3)
    # throat
    vmax, _ = thermo.sonic(T0, 0.0, R)
    def mach_at(v):
        T, P = thermo.static(T0, P0, v, R=R)
        return v / math.sqrt(thermo.gamma(T, R=R) * R * T)
    v_th = thermo.bisect(lambda v: mach_at(v) - M_throat, 1.0, vmax * 0.999)
    T_th, P_th = thermo.static(T0, P0, v_th, R=R)
    A_th = mdot / (P_th / (R * T_th) * v_th)
    pitch3 = math.pi * D3 / n_vanes
    o_req = A_th / (n_vanes * b3)
    o_max = pitch3 * math.cos(math.radians(alpha3))
    # channel exit
    alpha4 = alpha3 - exit_turning_deg
    pitch4 = math.pi * D4 / n_vanes
    w4 = pitch4 * math.cos(math.radians(alpha4)) * 0.85   # 15 % allowance for vane thickness at exit
    AR = w4 / o_req * exit_width_growth                    # axial width may grow from b3 at the throat to the exit
    L = 0.5 * (D4 - D3) / math.cos(math.radians(0.5 * (alpha3 + alpha4)))
    two_theta = 2 * math.degrees(math.atan((w4 - o_req) / (2 * L)))
    # equivalent conical divergence of the rectangular channel (area-equivalent radii)
    r_th = math.sqrt(o_req * b3 / math.pi)
    r_ex = math.sqrt(w4 * b3 * exit_width_growth / math.pi)
    two_theta_eq = 2 * math.degrees(math.atan((r_ex - r_th) / L))
    # Density rises through a compressible diffuser. V_exit = V_th / AR
    # would violate continuity at the reported static state.
    v4, T4, P4 = thermo.area_state(mdot, A_th * AR, T0, P0, R=R)
    M4 = v4 / math.sqrt(thermo.gamma(T4, R=R) * R * T4)
    q4 = 0.5 * P4 / (R * T4) * v4 ** 2
    q_th = 0.5 * P_th / (R * T_th) * v_th ** 2
    cp_ideal = (P4 - P_th) / q_th
    return dict(D_le_m=D3, b_m=b3, alpha_le_deg=alpha3, C_le_m_s=C3, M_le=M3,
                A_throat_m2=A_th, throat_width_m=o_req, throat_width_available_m=o_max,
                throat_open_ratio=o_req / o_max, M_throat=M_throat, n_vanes=int(n_vanes),
                D_exit_m=D4, alpha_exit_deg=alpha4, exit_width_m=w4, exit_axial_width_m=b3 * exit_width_growth,
                area_ratio=AR, channel_length_m=L,
                L_over_W=L / o_req, divergence_2theta_deg=two_theta, divergence_equivalent_cone_deg=two_theta_eq,
                C_exit_m_s=v4, M_exit=M4, T_exit_static_K=T4, P_exit_static_Pa=P4,
                exit_flow_area_m2=A_th * AR,
                cp_ideal=cp_ideal, cp_assumed=cp_assumed, static_rise_assumed_Pa=cp_assumed * q_th,
                turn_loss_frac=turn_K * q4 / P0,
                flags=([f'required throat opening {o_req*1e3:.2f} mm exceeds available {o_max*1e3:.2f} mm']
                       if o_req > o_max else [])
                + ([f'in-plane divergence 2theta {two_theta:.1f} deg outside 6-12 deg channel-diffuser band']
                   if not 6 <= two_theta <= 12 else [])
                + ([f'equivalent-cone divergence {two_theta_eq:.1f} deg above ~10 deg (stall risk)'] if two_theta_eq > 10 else []))
