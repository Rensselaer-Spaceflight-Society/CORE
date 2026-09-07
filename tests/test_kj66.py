"""
KJ66 regression tests -- the oracle.

The point of these tests is that a new member can write a module, run this
suite, and know whether their physics is right before it has ever touched
CORE's own design. That is worth more than any amount of code review.

READ THIS BEFORE TRUSTING THE BASELINE:

The published KJ66 numbers come from at least six independent sources measured
or simulated at different operating points, and they DO NOT form a single
self-consistent cycle. test_cycle_closure_gap_is_documented below quantifies
the gap rather than hiding it. The practical consequence for CORE:

  * Use the KJ66 to validate GEOMETRY and STRESS modules. There it is excellent
    -- the blade root force check below lands within 7% of Schreckling's own
    worked example.

  * Do NOT use it to validate the CYCLE. Feed it its own published pressure
    ratio, compressor efficiency, turbine inlet temperature and combustor loss
    and it produces about a third of its published thrust. Something in that
    set is measured somewhere else, and nobody has published which.

Run with:  python -m pytest tests/ -v
"""

import math
import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import registry, solver, gas   # noqa: E402
import run as R                          # noqa: E402


CYCLE_ONLY = {"m01_cycle", "m40_nozzle"}


def solve_with(cycle_only=False, **overrides):
    """Solve the pipeline with overridden seed values.

    cycle_only=True runs just the cycle and the nozzle. The KJ66 cycle tests
    below need that: they push CORE's seed to the KJ66's pressure ratio and
    turbine inlet temperature while leaving CORE's casing and mass flow alone,
    which is a combination no real combustor can be sized for. The point of
    those tests is the CYCLE closure gap, so the combustor is not involved.
    """
    specs = R.load_all_modules()
    if cycle_only:
        specs = [m for m in specs if m.name in CYCLE_ONLY]
    seed = registry.load_seed()
    seed.update({k: float(v) for k, v in overrides.items()})
    limits = registry.load_limits()
    guesses = registry._coerce_numbers(
        registry.load_yaml("initial_guess.yaml"), "initial_guess.yaml"
    )
    plan = solver.build_plan(specs, set(seed) | set(limits))
    state = dict(seed)
    state.update(limits)
    state, _ = solver.run_plan(plan, state, guesses=guesses)
    return state


BASE = registry.load_baseline()
PERF = BASE["performance"]
GEOM = BASE["geometry"]


# ===========================================================================
# GEOMETRY AND STRESS -- these validate well
# ===========================================================================

def test_blade_root_force_matches_schreckling():
    """Historical force comparison exercises M33; not a full rotor validation."""
    from modules.m33_turb_stress import m33_turb_stress
    rh,rt=.022,.033
    state=dict(A_annulus_turb_m2=math.pi*(rt**2-rh**2),N_rpm=117000.,
        rho_turb_kg_m3=8000.,D_turb_tip_m=2*rt,D_turb_hub_m=2*rh,
        h_blade_m=rt-rh,n_blades_turb_count=23.,m_blade_kg=.001,
        r_blade_cg_m=(rh+rt)/2,A_blade_root_m2=1e-5,sigma_allow_turb_Pa=500e6)
    out=m33_turb_stress.spec.run(state)
    assert out['F_blade_root_N']==pytest.approx(4430,rel=.08)



def test_turbine_mean_diameter_consistent_with_tip_and_blade_height():
    """66 mm tip, 11 mm blade -> 55 mm mean. Schreckling states all three
    independently, so they are a free consistency check on our geometry
    convention (mean = tip - blade height, i.e. hub = tip - 2*height)."""
    tip = GEOM["D_turb_tip_m"]["value"]
    h = GEOM["h_blade_m"]["value"]
    mean_implied = tip - h
    assert abs(mean_implied - GEOM["D_turb_mean_m"]["value"]) < 1e-4


def test_stress_speed_margin_is_not_a_burst_prediction():
    from modules.m33_turb_stress import m33_turb_stress
    state=dict(A_annulus_turb_m2=.002,N_rpm=117000.,rho_turb_kg_m3=8000.,
        D_turb_tip_m=.066,D_turb_hub_m=.044,h_blade_m=.011,n_blades_turb_count=23.,
        m_blade_kg=.001,r_blade_cg_m=.0275,A_blade_root_m2=1e-5,sigma_allow_turb_Pa=500e6)
    out=m33_turb_stress.spec.run(state)
    assert out['blade_stress_speed_margin_ratio']**2*out['sigma_root_Pa']==pytest.approx(500e6)



def test_kj66_bearing_DN_is_below_our_limit():
    """8 mm bore at 117,000 rpm = 0.94e6 DN, on plain steel bearings fed with
    oil premixed in the fuel. A useful reality check on how conservative our
    own DN limit is."""
    DN = GEOM["d_bearing_bore_m"]["value"] * 1000 * PERF["N_max_rpm"]["value"]
    limits = registry.load_limits()
    assert DN < limits["DN_max_mm_rpm"]
    assert DN > 5e5, "sanity: this should be a demanding bearing application"


# ===========================================================================
# CYCLE -- this does NOT validate, and that is the finding
# ===========================================================================

def test_cycle_closure_gap_is_documented():
    """Feed the model the KJ66's own published cycle numbers and it produces
    roughly a third of the published thrust.

    This test asserts the gap is STILL THERE, deliberately. If somebody
    'fixes' the cycle module by tuning it until the KJ66 closes, this test
    fails and tells them to stop -- because the right answer is that the
    published numbers disagree with each other, not that our thermodynamics
    is wrong.

    If you find the source that resolves this, update kj66_baseline.yaml and
    delete this test with a note saying what you found.
    """
    s = solve_with(
        cycle_only=True,
        PR_c_ratio=PERF["PR_c_ratio"]["value"],
        eta_c_isen=PERF["eta_c_isen"]["value"],
        T04_K=PERF["T04_K"]["value"],
        dP34_frac=PERF["dP34_frac"]["value"],
        N_rpm=PERF["N_max_rpm"]["value"],
        F_target_N=PERF["F_gross_N"]["value"],
    )
    thrust_at_published_mdot = s["Fs_N_per_kg_s"] * PERF["mdot_kg_s"]["value"]
    published = PERF["F_gross_N"]["value"]
    shortfall = 1.0 - thrust_at_published_mdot / published

    assert 0.5 < shortfall < 0.85, (
        f"the KJ66 closure gap changed (now {shortfall*100:.0f}% short). "
        f"If that is because you found better source data, update "
        f"config/kj66_baseline.yaml and this test's bounds together."
    )


def test_reconciling_kj66_needs_an_impossible_temperature():
    """The turbine inlet temperature that WOULD reconcile 75 N at 0.23 kg/s is
    around 1300 K, which implies an exhaust temperature near 1200 K against a
    published EGT of 843 K. So the inconsistency cannot be resolved by
    adjusting T04 alone."""
    target_Fs = PERF["F_gross_N"]["value"] / PERF["mdot_kg_s"]["value"]

    lo, hi = 900.0, 1900.0
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        s = solve_with(
            cycle_only=True,
            PR_c_ratio=PERF["PR_c_ratio"]["value"],
            eta_c_isen=PERF["eta_c_isen"]["value"],
            T04_K=mid, dP34_frac=PERF["dP34_frac"]["value"],
            N_rpm=PERF["N_max_rpm"]["value"], F_target_N=PERF["F_gross_N"]["value"],
        )
        if s["Fs_N_per_kg_s"] < target_Fs:
            lo = mid
        else:
            hi = mid

    assert 1200 < mid < 1450, f"reconciling T04 came out {mid:.0f} K"
    s = solve_with(
        cycle_only=True,
        PR_c_ratio=PERF["PR_c_ratio"]["value"], eta_c_isen=PERF["eta_c_isen"]["value"],
        T04_K=mid, dP34_frac=PERF["dP34_frac"]["value"],
        N_rpm=PERF["N_max_rpm"]["value"], F_target_N=PERF["F_gross_N"]["value"],
    )
    assert s["T05_K"] > PERF["T05_K"]["value"] + 250, (
        "the reconciling temperature should imply an EGT far above the published one"
    )


def test_kj66_nozzle_is_not_choked():
    """At an overall pressure ratio under 2 with a 12% combustor loss, there is
    not enough pressure left to choke the nozzle. Worth knowing, because it
    means the KJ66's exhaust is back-pressure sensitive in a way CORE's higher
    pressure ratio design may not be."""
    s = solve_with(
        cycle_only=True,
        PR_c_ratio=PERF["PR_c_ratio"]["value"], eta_c_isen=PERF["eta_c_isen"]["value"],
        T04_K=PERF["T04_K"]["value"], dP34_frac=PERF["dP34_frac"]["value"],
        N_rpm=PERF["N_max_rpm"]["value"], F_target_N=PERF["F_gross_N"]["value"],
    )
    assert s["nozzle_choked_flag"] == 0.0
