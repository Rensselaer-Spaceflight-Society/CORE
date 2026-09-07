"""M24: diagnostics from the EXACT M20 geometry; no second sizing solve.

All values use SI. The heat model, stability proxies and thin-wall hoop stress
are preliminary; buckling and temperature-dependent material evidence are open.
"""
from core.module import module

@module(tier=4,title="Frozen combustor diagnostic checks",owner="CSYS-2",second="SAFE-1",
        status="stub",notes="STUB: thermal, stability and buckling evidence unresolved.",
        reads=['comb_CLP_ratio', 'comb_tau_s', 'comb_q_dome_W_m2', 'comb_q_spread_W_m2', 'comb_J_primary_ratio', 'comb_dil_pen_ratio', 'comb_sigma_hoop_Pa', 'comb_hole_K_ratio'],
        writes=['CLP_ratio', 'tau_res_s', 'q_dome_W_m2', 'q_dome_spread_W_m2', 'J_primary_ratio', 'dil_pen_ratio', 'sigma_hoop_liner_Pa', 'hole_K_ratio'])
def m24_combustor_checks(s):
    return {
        "CLP_ratio": s["comb_CLP_ratio"],
        "tau_res_s": s["comb_tau_s"],
        "q_dome_W_m2": s["comb_q_dome_W_m2"],
        "q_dome_spread_W_m2": s["comb_q_spread_W_m2"],
        "J_primary_ratio": s["comb_J_primary_ratio"],
        "dil_pen_ratio": s["comb_dil_pen_ratio"],
        "sigma_hoop_liner_Pa": s["comb_sigma_hoop_Pa"],
        "hole_K_ratio": s["comb_hole_K_ratio"],
    }
