"""Reproduce limited DP-2 arithmetic; not a matched engine or release model.

Run from any directory with Python 3.11+. No input files are changed.
Property functions are the existing unvalidated product surrogate.
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from core import gas, thermo


def cycle(eta_c=0.72, eta_t=0.78, loss=0.06, fixed_work=False):
    t2, p2, t4, mdot = 288.15, 101325 * 0.99, 1150.0, 0.30
    if fixed_work:
        wc = 60300.0
        t3s = thermo.temperature(gas.h_air(t2) + wc * eta_c)
        p3 = thermo.pressure(t3s, t2, p2)
    else:
        p3 = p2 * 1.63
        t3s = thermo.isentropic_temperature(t2, 1.63)
        wc = (gas.h_air(t3s) - gas.h_air(t2)) / eta_c
    t3 = thermo.temperature(gas.h_air(t2) + wc)
    far = gas.far_for_T4(t3, t4, 0.96, 43e6)
    wt = wc / (0.98 * (1 + far))
    t5 = thermo.temperature(gas.h_products(t4, far) - wt, far)
    t5s = thermo.temperature(gas.h_products(t4, far) - wt / eta_t, far)
    p5_no_loss = thermo.pressure(t5s, t4, p3, far)
    p5 = p5_no_loss * (1 - loss)
    v, t8, _, choked = thermo.nozzle(t5, p5, 101325, far, Cv=0.97)
    area = mdot * (1 + far) / (101325 / (287.05 * t8) * v)
    return dict(T3_K=t3, P3_kPa=p3/1000, T5_K=t5, P5_kPa=p5/1000,
                compressor_kW=mdot*wc/1000, FAR=far, fuel_kg_h=mdot*far*3600,
                velocity_m_s=v, thrust_N=mdot*(1+far)*v,
                nozzle_diameter_mm=math.sqrt(4*area/math.pi)*1000,
                nozzle_choked=choked, zero_head_loss_percent=100*(1-101325/p5_no_loss))


if __name__ == '__main__':
    omega = 66000 * 2 * math.pi / 60
    print(json.dumps({
        'scope': 'Screen only: power balance imposed, no compressor/turbine map matching.',
        'arithmetic': {
            'tip_speed_m_s': omega*0.07613/2,
            'fuel_from_claimed_FAR_kg_h': 0.30*0.0212*3600,
            'uncorrected_flow_lb_min': 0.30*60/0.45359237,
            'energy_J': 0.5*2.13e-4*omega**2,
            'energy_at_120_percent_J': 0.5*2.13e-4*(omega*1.2)**2,
            'bearing_DN': 8*66000,
            'G2p5_eccentricity_um': 2.5/omega*1000,
            'turbine_annulus_mm2': math.pi/4*(88.2**2-53.9**2),
            'low_budget_with_15_percent': 3065*1.15,
            'high_budget_with_15_percent': 6130*1.15,
            'midpoint_with_15_percent': (3065+6130)/2*1.15,
        },
        'fixed_PR_screen': cycle(),
        'fixed_PR_lower_efficiency_screen': cycle(0.60,0.70),
        'fixed_work_nominal_screen': cycle(fixed_work=True),
        'fixed_work_lower_efficiency_screen': cycle(0.60,0.70,fixed_work=True),
    }, indent=2))
