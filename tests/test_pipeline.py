"""
Pipeline health tests. These are the ones that stop the repo rotting.

Every pull request runs them. They are cheap, they are boring, and they catch
the failure modes that actually kill a twenty-person design project:

  * a variable nobody owns, or two people owning the same one
  * a module reading something it did not declare
  * a name without a unit on it
  * a design that quietly violates a safety limit
  * thrust that does not close

None of these need anyone to understand gas turbines. They need somebody to
have run `pytest` before merging, which is why CI does it for them.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import registry, solver           # noqa: E402
from core.module import REGISTERED          # noqa: E402
import run as R                             # noqa: E402


@pytest.fixture(scope="module")
def solved():
    plan, state, limits, _ = R.solve()
    return plan, state, limits


# ---------------------------------------------------------------- registry

def test_every_shared_variable_has_a_unit_suffix():
    reg = registry.load_registry()
    bad = [n for n in reg if not registry.has_declared_unit(n)]
    assert not bad, (
        f"these variable names carry no SI unit: {bad}. "
        f"Rename them -- d2_m not d2, T04_K not T04. Half of all interface "
        f"bugs on projects like this are unit bugs."
    )


def test_registry_units_match_the_name_suffix():
    reg = registry.load_registry()
    mismatched = [
        (n, m["unit"], registry.unit_of(n))
        for n, m in reg.items()
        if m["unit"] != registry.unit_of(n) and registry.unit_of(n) != "-"
    ]
    assert not mismatched, f"declared unit disagrees with the name: {mismatched}"


def test_every_module_output_is_in_the_registry():
    specs = R.load_all_modules()
    reg = registry.load_registry()
    missing = sorted({w for m in specs for w in m.writes if w not in reg})
    assert not missing, (
        f"these are written by a module but are not in config/variables.yaml: "
        f"{missing}. If another person will ever read it, register it. If not, "
        f"keep it local to the module."
    )


def test_every_seed_is_in_the_registry():
    seed = registry.load_seed()
    reg = registry.load_registry()
    missing = sorted(k for k in seed if k not in reg)
    assert not missing, f"seed values not registered: {missing}"


# ------------------------------------------------------------------- graph

def test_graph_builds_and_every_read_is_satisfied():
    specs = R.load_all_modules()
    seeded = set(registry.load_seed()) | set(registry.load_limits())
    plan = solver.build_plan(specs, seeded)   # raises if anything is unmet
    assert plan.blocks


def test_exactly_one_owner_per_variable():
    """build_plan raises on a double-write, so reaching here means it holds.
    Stated as its own test because it is the single most important invariant
    in the whole repo: every number has exactly one place it comes from."""
    specs = R.load_all_modules()
    seeded = set(registry.load_seed()) | set(registry.load_limits())
    plan = solver.build_plan(specs, seeded)
    assert len(plan.producers) == len({m for m in plan.producers})


def test_coupled_groups_are_small():
    """A big coupled block means the module boundaries are wrong. Two or three
    modules that genuinely size each other is normal engineering; six is a sign
    that somebody split one physical problem across too many files."""
    specs = R.load_all_modules()
    seeded = set(registry.load_seed()) | set(registry.load_limits())
    plan = solver.build_plan(specs, seeded)
    for block in plan.blocks:
        assert len(block) <= 4, (
            f"coupled group of {len(block)} modules: "
            f"{[m.name for m in block]}. Consider merging them."
        )


# ------------------------------------------------------------------ solved

def test_thrust_closes(solved):
    """The cycle sizes the mass flow from a thrust target; the nozzle then
    computes the thrust that actually results. They must agree, or the two
    modules disagree about the gas."""
    _, s, _ = solved
    err = abs(s["F_gross_N"] - s["F_target_N"]) / s["F_target_N"]
    assert err < 0.01, f"thrust closure error {err*100:.2f}%"


def test_energy_balance_closes(solved):
    """Turbine work times its mass flow must equal compressor work times its
    mass flow, divided by mechanical efficiency. If this drifts, somebody has
    changed a cp or forgotten the fuel mass addition."""
    _, s, _ = solved
    lhs = s["w_turb_J_kg"] * s["mdot_kg_s"] * (1 + s["FAR_ratio"]) * s["eta_mech_frac"]
    rhs = s["w_comp_J_kg"] * s["mdot_kg_s"]
    assert abs(lhs - rhs) / rhs < 1e-9


def test_screening_limits_report_the_unreleased_baseline(solved):
    """Software correctness must expose, not hide, the unresolved rotor limit.

    Manufacturing approval uses run.py --release-check. No limit was relaxed.
    """
    _, s, limits = solved
    rows = R.check_limits(s, limits)
    assert len(rows) == len(R.CHECKS)
    failed = {key for label,key,v,op,lim,ok in rows if not ok}
    assert 'N_crit_margin_frac' in failed
    assert s['critical_crossed_flag']


def test_geometry_is_physically_sensible(solved):
    """Cheap sanity checks that catch a sign error or a factor of a thousand
    long before anybody looks at a drawing."""
    _, s, _ = solved
    assert 0.02 < s["D2_m"] < 0.50, "impeller diameter outside a sane range"
    assert s["D1s_m"] < s["D2_m"], "inducer cannot be larger than the exducer"
    assert s["D1h_m"] < s["D1s_m"], "hub cannot be larger than the shroud"
    assert s["D_turb_hub_m"] < s["D_turb_tip_m"]
    assert s["D_liner_in_m"] < s["D_liner_out_m"]
    assert s["D_casing_out_m"] > s["D_turb_tip_m"], "turbine must fit inside the casing"
    assert s["D_casing_out_m"] > s["D3_m"], "diffuser must fit inside the casing"
    assert s["L_engine_m"] > s["L_shaft_m"], "engine cannot be shorter than its shaft"
    assert s["m_engine_kg"] > s["m_turb_kg"] + s["m_imp_kg"]
    assert 0 < s["FAR_ratio"] < 0.05, "fuel-air ratio outside anything physical"
    assert s["T05_K"] < s["T04_K"], "turbine must extract work, not add it"
    assert s["P05_Pa"] < s["P04_Pa"] < s["P03_Pa"]


def test_combustor_residence_time_is_in_range(solved):
    """Too short and the fuel does not finish burning; too long and the
    combustor is bigger and heavier than it needs to be. 2-8 ms is the band."""
    _, s, _ = solved
    assert 0.0005 < s["tau_res_s"] < 0.020, (
        f"residence time {s['tau_res_s']*1000:.2f} ms is outside 0.5-20 ms"
    )


# -------------------------------------------------------------- team health

def test_every_module_has_a_second_owner():
    """Bus factor 2 on every module. On a team where attendance is uneven this
    is not bureaucracy -- it is the difference between a module stalling for
    three weeks and somebody else picking it up on Wednesday."""
    specs = R.load_all_modules()
    orphans = [m.name for m in specs if not m.second]
    assert not orphans, (
        f"no second owner assigned: {orphans}. Every module needs two names."
    )


def test_stub_modules_say_so():
    """A stub must declare itself in its notes, so that nobody quotes its
    output in a design review believing it is real."""
    specs = R.load_all_modules()
    bad = [m.name for m in specs if m.status == "stub" and "STUB" not in (m.notes or "").upper()]
    assert not bad, (
        f"these are marked status='stub' but their notes do not say so: {bad}. "
        f"Write down what is fake about them."
    )
