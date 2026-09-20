"""Checks for the structures/fabrication guided lessons (S3-STRESS, S4-BEND, C2-FAB).

These test the teaching arithmetic against independent hand calculations, the
failure behaviour on invalid geometry, the unit conventions, the separation of
EXAMPLE loads from DP-2 candidate loads, and that UNKNOWN / NOT FOUND never
turn into a fabricated zero.

They do not test the engine model and they do not approve anything.
"""

import json
import math
from pathlib import Path
import subprocess
import sys

import pytest

REPO = Path(__file__).resolve().parents[3]
PLATFORM = REPO / "workspaces" / "python" / "interactive"
DOMAIN = PLATFORM / "lessons" / "structures"
sys.path.insert(0, str(PLATFORM))
sys.path.insert(0, str(DOMAIN))

from learning_model import calculate, make_answer, questions, validate_lesson  # noqa: E402
from learning_store import Session, export_session, read_json, validate_record  # noqa: E402
from runtime import discover  # noqa: E402
import _structures_math as sm  # noqa: E402

LESSON_IDS = ("S3-STRESS", "S4-BEND", "C2-FAB")

# Loads from workspaces/structures/'object tests'/object-example.py. TEACHING ONLY.
EXAMPLE_DP_KPA = 2000.0
EXAMPLE_ID_MM = 200.0
EXAMPLE_T_MM = 1.0

# DP-2 CANDIDATE casing, from docs/project/checks/dp2_screen.py and dp2-review.md.
# A prescribed-cycle screen under review, not a measured or approved load.
AMBIENT_KPA = 101.325
DP2_P3_ABS_KPA = 163.5081525
DP2_CASING_ID_MM = 149.4
DP2_CASING_T_MM = 1.5


@pytest.fixture(scope="module")
def catalog():
    return discover()


# ---------------------------------------------------------------- lesson shape

def test_all_three_lessons_are_discovered_and_valid(catalog):
    for lesson_id in LESSON_IDS:
        assert lesson_id in catalog, f"{lesson_id} not discovered by the launcher"
        validate_lesson(catalog[lesson_id][0])


def test_helper_module_is_not_discovered_as_a_lesson(catalog):
    sources = {source.name for _, source in catalog.values()}
    assert "_structures_math.py" not in sources


def test_every_step_has_a_readable_visual_that_exists(catalog):
    for lesson_id in LESSON_IDS:
        lesson, source = catalog[lesson_id]
        for step in lesson.steps:
            if not step.visual:
                continue
            asset = source.parent / step.visual
            assert asset.is_file(), f"{lesson_id}/{step.id}: missing {step.visual}"
            assert asset.suffix.lower() in (".html", ".svg", ".png")
            text = asset.read_text(encoding="utf-8")
            # Self-contained: no CDN, no network, no live server required.
            for forbidden in ("http://", "https://cdn", "<script src=", "fetch("):
                assert forbidden not in text, f"{asset.name} must not need the network"


def test_numeric_questions_declare_units_and_evidence_questions_are_not_bypassed(catalog):
    for lesson_id in LESSON_IDS:
        lesson, _ = catalog[lesson_id]
        for q in questions(lesson):
            if q.kind in ("number", "integer"):
                assert q.units, f"{lesson_id}.{q.id}: numeric question needs units"
            if q.role in ("decision", "next_step"):
                assert not q.evidence, f"{lesson_id}.{q.id}: handoff questions take no source"


def test_calculation_inputs_are_all_numeric_questions(catalog):
    for lesson_id in LESSON_IDS:
        lesson, _ = catalog[lesson_id]
        kinds = {q.id: q.kind for q in questions(lesson)}
        for calc in lesson.calculations:
            for key in calc.inputs:
                assert kinds[key] in ("number", "integer"), (
                    f"{lesson_id}.{calc.id} reads non-numeric question {key}")
            assert calc.limitations, f"{lesson_id}.{calc.id} must state its limits"


def test_comparison_keys_are_only_on_shared_physical_quantities(catalog):
    """A comparison key claims 'same quantity, same part, same conditions'."""
    keyed = {}
    for lesson_id in LESSON_IDS:
        lesson, _ = catalog[lesson_id]
        for q in questions(lesson):
            if q.comparison_key:
                keyed.setdefault(q.comparison_key, []).append((lesson_id, q.id, q.units))
    assert keyed, "expected at least one shared quantity for the reviewer to group"
    for key, entries in keyed.items():
        assert key.startswith("core."), f"{key} should be namespaced to the project"
        assert len({units for _, _, units in entries}) == 1, (
            f"{key} is reported in more than one unit; the reviewer does not convert")


# ------------------------------------------------- hand checks on the mechanics

def test_hoop_stress_matches_an_independent_hand_calculation():
    # EXAMPLE loads, inner-radius convention, exactly as object-example.py wrote it:
    # sigma = 2e6 Pa * 0.100 m / 0.001 m = 200e6 Pa.
    got = sm.hoop_stress_inner_radius_pa(
        EXAMPLE_DP_KPA + AMBIENT_KPA, AMBIENT_KPA, EXAMPLE_ID_MM, EXAMPLE_T_MM)
    assert got == pytest.approx(200.0e6, rel=1e-12)

    # Mid-wall radius convention (AFFDL 8.3.1): r = (200 + 1)/2 = 100.5 mm.
    mean = sm.hoop_stress_pa(
        EXAMPLE_DP_KPA + AMBIENT_KPA, AMBIENT_KPA, EXAMPLE_ID_MM, EXAMPLE_T_MM)
    assert mean == pytest.approx(2.0e6 * 0.1005 / 0.001, rel=1e-12)


def test_axial_stress_is_exactly_half_the_hoop_stress():
    args = (DP2_P3_ABS_KPA, AMBIENT_KPA, DP2_CASING_ID_MM, DP2_CASING_T_MM)
    assert sm.axial_stress_closed_end_pa(*args) == pytest.approx(
        sm.hoop_stress_pa(*args) / 2.0, rel=1e-15)


def test_delta_p_uses_the_difference_not_the_absolute_pressure():
    """Same difference, different absolute pair, same stress. That is the point."""
    as_absolute = sm.hoop_stress_pa(DP2_P3_ABS_KPA, AMBIENT_KPA,
                                    DP2_CASING_ID_MM, DP2_CASING_T_MM)
    gauge = DP2_P3_ABS_KPA - AMBIENT_KPA
    as_gauge_pair = sm.hoop_stress_pa(gauge, 0.0, DP2_CASING_ID_MM, DP2_CASING_T_MM)
    assert as_absolute == pytest.approx(as_gauge_pair, rel=1e-12)
    assert sm.delta_p_pa(DP2_P3_ABS_KPA, AMBIENT_KPA) == pytest.approx(62183.15, abs=0.5)


def test_example_and_dp2_loads_stay_separated_by_about_65x():
    """If these ever converge, an EXAMPLE load has leaked into the candidate case."""
    example = sm.hoop_stress_pa(EXAMPLE_DP_KPA + AMBIENT_KPA, AMBIENT_KPA,
                                EXAMPLE_ID_MM, EXAMPLE_T_MM)
    candidate = sm.hoop_stress_pa(DP2_P3_ABS_KPA, AMBIENT_KPA,
                                  DP2_CASING_ID_MM, DP2_CASING_T_MM)
    assert example / candidate == pytest.approx(64.3, rel=0.02)
    assert candidate == pytest.approx(3.128e6, rel=1e-3)


def test_convention_spread_is_small_but_not_zero():
    """Mean vs inner radius differ by t/(2r); about 1% on the candidate casing."""
    args = (DP2_P3_ABS_KPA, AMBIENT_KPA, DP2_CASING_ID_MM, DP2_CASING_T_MM)
    spread = (sm.hoop_stress_pa(*args) / sm.hoop_stress_inner_radius_pa(*args)) - 1.0
    assert spread == pytest.approx(DP2_CASING_T_MM / DP2_CASING_ID_MM, rel=1e-9)
    assert 0.005 < spread < 0.02


def test_thin_wall_applicability_criterion_is_the_cited_one():
    """AFFDL Stress Analysis Manual Sec. 8.3.1: applicable above r/t = 10."""
    assert sm.THIN_WALL_MIN_R_OVER_T == 10.0
    assert sm.r_over_t(DP2_CASING_ID_MM, DP2_CASING_T_MM) == pytest.approx(50.3, rel=1e-3)
    assert sm.thin_wall_applicable(DP2_CASING_ID_MM, DP2_CASING_T_MM)
    # Boundary: r_mean/t = 10 exactly when ID = 19t. Strictly greater is required.
    assert not sm.thin_wall_applicable(19.0, 1.0)
    assert sm.thin_wall_applicable(19.1, 1.0)
    assert not sm.thin_wall_applicable(100.0, 20.0)  # thick wall: needs Lame


def test_section_properties_against_closed_form():
    d = 8.0
    assert sm.second_moment_area_tube_m4(d, 0.0) == pytest.approx(
        math.pi * (d / 1000.0) ** 4 / 64.0, rel=1e-15)
    assert sm.polar_moment_area_tube_m4(d, 0.0) == pytest.approx(
        2.0 * sm.second_moment_area_tube_m4(d, 0.0), rel=1e-15)
    assert sm.second_moment_area_solid_round_m4(d) == pytest.approx(
        sm.second_moment_area_tube_m4(d, 0.0), rel=1e-15)
    # A 4 mm bore in an 8 mm shaft removes 25% of the area but only 6.25% of I.
    loss = 1.0 - sm.second_moment_area_tube_m4(8.0, 4.0) / sm.second_moment_area_tube_m4(8.0, 0.0)
    assert loss == pytest.approx(0.0625, rel=1e-12)


def test_area_moment_and_mass_moment_are_different_quantities():
    """m^4 versus kg*m^2. They must never be interchangeable."""
    area = sm.second_moment_area_solid_round_m4(76.13)          # m^4
    mass = sm.mass_moment_inertia_solid_cylinder_kg_m2(0.2, 76.13)  # kg*m^2
    assert area == pytest.approx(1.6489e-6, rel=1e-3)
    assert mass == pytest.approx(1.4489e-4, rel=1e-3)
    assert abs(math.log10(mass / area)) > 1  # different scale, different dimension


def test_torsion_matches_16T_over_pi_d_cubed_and_the_m30_relation():
    torque, d = 2.6147, 8.0
    closed_form = 16.0 * torque / (math.pi * (d / 1000.0) ** 3)
    assert sm.torsional_shear_solid_round_pa(torque, d) == pytest.approx(closed_form, rel=1e-12)
    assert sm.torsional_shear_solid_round_pa(torque, d) == pytest.approx(26.0e6, rel=1e-2)
    # m30_shaft.py inverts the same relation: this torque needs only ~3.6 mm.
    d_needed = (16.0 * torque / (math.pi * 280.0e6)) ** (1.0 / 3.0) * 1000.0
    assert d_needed == pytest.approx(3.62, rel=1e-2)
    assert d_needed < d, "the candidate journal is set by the bearing bore, not torsion"


def test_bending_stress_against_hand_calculation():
    # 10 N*m on a 10 mm solid bar: I = pi*d^4/64, y = 5 mm.
    i = sm.second_moment_area_solid_round_m4(10.0)
    assert sm.bending_stress_pa(10.0, 5.0, i) == pytest.approx(10.0 * 0.005 / i, rel=1e-15)
    assert sm.bending_stress_solid_round_pa(10.0, 10.0) == pytest.approx(
        32.0 * 10.0 / (math.pi * 0.01 ** 3), rel=1e-12)
    # Sign of the moment does not change the magnitude of the stress.
    assert sm.bending_stress_solid_round_pa(-10.0, 10.0) == pytest.approx(
        sm.bending_stress_solid_round_pa(10.0, 10.0), rel=1e-15)


def test_deflection_formula_and_its_cube_law():
    delta = sm.midspan_deflection_simple_central_load_m(
        100.0, 200.0, 205.0, sm.second_moment_area_solid_round_m4(10.0))
    expected = 100.0 * 0.2 ** 3 / (
        48.0 * 205.0e9 * sm.second_moment_area_solid_round_m4(10.0))
    assert delta == pytest.approx(expected, rel=1e-15)
    doubled = sm.midspan_deflection_simple_central_load_m(
        100.0, 400.0, 205.0, sm.second_moment_area_solid_round_m4(10.0))
    assert doubled / delta == pytest.approx(8.0, rel=1e-12)


# --------------------------------------------------- invalid geometry behaviour

@pytest.mark.parametrize("thickness", [0.0, -1.0, -0.001])
def test_zero_or_negative_thickness_is_refused_not_divided_by(thickness):
    for fn in (sm.hoop_stress_pa, sm.hoop_stress_inner_radius_pa,
               sm.axial_stress_closed_end_pa):
        with pytest.raises(ValueError, match="greater than zero"):
            fn(DP2_P3_ABS_KPA, AMBIENT_KPA, DP2_CASING_ID_MM, thickness)
    with pytest.raises(ValueError):
        sm.r_over_t(DP2_CASING_ID_MM, thickness)


@pytest.mark.parametrize("diameter", [0.0, -5.0])
def test_zero_or_negative_diameter_is_refused(diameter):
    with pytest.raises(ValueError):
        sm.hoop_stress_pa(DP2_P3_ABS_KPA, AMBIENT_KPA, diameter, DP2_CASING_T_MM)
    with pytest.raises(ValueError):
        sm.second_moment_area_solid_round_m4(diameter)


def test_bore_larger_than_outside_diameter_is_refused():
    with pytest.raises(ValueError, match="smaller than the outer"):
        sm.second_moment_area_tube_m4(8.0, 8.0)
    with pytest.raises(ValueError, match="smaller than the outer"):
        sm.polar_moment_area_tube_m4(8.0, 12.0)


def test_net_external_pressure_is_refused_as_a_buckling_problem():
    """Hoop tension does not apply; the error must say so rather than return a negative."""
    with pytest.raises(ValueError, match="buckling"):
        sm.hoop_stress_pa(50.0, AMBIENT_KPA, DP2_CASING_ID_MM, DP2_CASING_T_MM)
    with pytest.raises(ValueError, match="buckling"):
        sm.axial_stress_closed_end_pa(AMBIENT_KPA, AMBIENT_KPA,
                                      DP2_CASING_ID_MM, DP2_CASING_T_MM)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_inputs_are_refused_everywhere(bad):
    with pytest.raises(ValueError):
        sm.hoop_stress_pa(bad, AMBIENT_KPA, DP2_CASING_ID_MM, DP2_CASING_T_MM)
    with pytest.raises(ValueError):
        sm.bending_stress_pa(bad, 5.0, 1e-8)
    with pytest.raises(ValueError):
        sm.torsional_shear_pa(bad, 4.0, 1e-8)
    with pytest.raises(ValueError):
        sm.stack_tolerance_mm(0.1, bad)


def test_booleans_are_not_accepted_as_numbers():
    with pytest.raises(ValueError):
        sm.hoop_stress_pa(True, AMBIENT_KPA, DP2_CASING_ID_MM, DP2_CASING_T_MM)
    with pytest.raises(ValueError):
        sm.coupon_stock_area_mm2(50.0, 25.0, True, 20.0)


# ---------------------------------------------------------- fabrication maths

def test_coupon_stock_area_includes_the_scrap_allowance():
    assert sm.coupon_stock_area_mm2(100.0, 50.0, 6, 20.0) == pytest.approx(36000.0, rel=1e-12)
    assert sm.coupon_stock_area_mm2(100.0, 50.0, 6, 0.0) == pytest.approx(30000.0, rel=1e-12)


@pytest.mark.parametrize("count", [0, -1, 2.5])
def test_coupon_count_must_be_a_whole_positive_number(count):
    with pytest.raises(ValueError):
        sm.coupon_stock_area_mm2(100.0, 50.0, count, 20.0)


def test_cash_cost_never_subtracts_donated_value():
    """Confirmed in-kind is recorded separately so it is credited exactly once."""
    assert sm.cash_stock_cost_usd(120.0, 18.5) == pytest.approx(138.5, rel=1e-12)
    assert sm.cash_stock_cost_usd(0.0, 0.0) == 0.0
    with pytest.raises(ValueError):
        sm.cash_stock_cost_usd(-50.0, 10.0)  # a donation is not a negative price


def test_tolerance_stack_is_worst_case_and_reports_interference():
    assert sm.stack_tolerance_mm(0.7, 0.5, 0.3) == pytest.approx(1.5, rel=1e-12)
    # Worst case, deliberately not root-sum-square.
    rss = math.sqrt(0.7 ** 2 + 0.5 ** 2 + 0.3 ** 2)
    assert sm.stack_tolerance_mm(0.7, 0.5, 0.3) > rss
    assert sm.radial_clearance_after_stack_mm(2.0, 0.7, 0.5, 0.3) == pytest.approx(0.5, rel=1e-12)
    # Negative means interference and must be reported, not clipped to zero.
    assert sm.radial_clearance_after_stack_mm(2.0, 1.5, 1.0, 0.4) == pytest.approx(-0.9, rel=1e-12)
    # Signs are ignored: a tolerance is a magnitude here.
    assert sm.radial_clearance_after_stack_mm(2.0, -0.7, 0.5, 0.3) == pytest.approx(0.5, rel=1e-12)
    with pytest.raises(ValueError):
        sm.stack_tolerance_mm()


def test_clearance_stack_matches_the_limits_file_floor():
    """config/limits.yaml requires 2 mm radial clearance for the liner in the casing."""
    text = (REPO / "config" / "limits.yaml").read_text(encoding="utf-8")
    assert "casing_fit_margin_min_m: 0.002" in text, (
        "the C2-FAB lesson teaches against this value; update both together")


# ------------------------------------------------- end-to-end record behaviour

def _answer(value, **extra):
    entry = dict(value=value, basis="candidate", source="test fixture",
                 uncertainty="synthetic test data, not a CORE input")
    entry.update(extra)
    return entry


def _fill(session, values):
    for q in questions(session.lesson):
        if q.id in values:
            session.record(q, values[q.id])


def test_s3_session_computes_the_candidate_casing_and_exports(tmp_path, catalog):
    lesson = catalog["S3-STRESS"][0]
    session = Session.create(lesson, "P01", tmp_path / "drafts")
    _fill(session, {
        "wall_component": _answer("candidate outer casing cylinder", basis="candidate"),
        "load_path": _answer("internal gas out, ambient in, flanges at both ends"),
        "end_condition": _answer("closed ends carried by this wall"),
        "p_internal_abs": _answer(DP2_P3_ABS_KPA),
        "p_external_abs": _answer(AMBIENT_KPA),
        "pressure_reference": _answer("source gave absolute pressure directly"),
        "wall_id": _answer(DP2_CASING_ID_MM),
        "wall_t": _answer(DP2_CASING_T_MM),
        "support_assumption": _answer("assumed flange supported", basis="hypothesis"),
        "material_evidence": _answer("6061 per config/seed.yaml comment"),
        "wall_temperature_basis": _answer("no thermal evidence yet"),
        "hand_hoop_mpa": _answer(3.13),
        "unit_cancellation": _answer("Pa * m / m = Pa"),
        "thin_wall_judgement": _answer("yes - r/t is greater than 10"),
        "excluded_effects": _answer("buckling, holes, welds, fatigue"),
        "allowable_source": _answer("needs a welded allowable at temperature"),
        "lead_decision": _answer("confirm the current casing drawing revision"),
        "next_step": _answer("find the casing drawing"),
    })
    assert session.data["status"] == "ready_for_review"
    assert session.data["review_status"] == "unreviewed"

    results = {r["id"]: r for r in session.data["computed"]}
    assert results["delta_p"]["value"] == pytest.approx(62.183, rel=1e-3)
    assert results["r_over_t"]["value"] == pytest.approx(50.3, rel=1e-3)
    assert results["hoop_mean_radius"]["value"] == pytest.approx(3.128, rel=1e-3)
    assert results["hoop_inner_radius"]["value"] == pytest.approx(3.097, rel=1e-3)
    assert results["axial_closed_end"]["value"] == pytest.approx(1.564, rel=1e-3)
    for result in results.values():
        assert result["basis"] == "computed"
        assert result["status"] == "computed"
        assert result["units"] in ("MPa", "kPa", "dimensionless")

    folder = export_session(session, tmp_path / "out")
    data = validate_record(read_json(folder / "answers.json"))
    assert data["drafts"] == {}
    summary = (folder / "summary.md").read_text(encoding="utf-8")
    assert "not approve a design" in summary
    assert "3.128" in summary or "3.12" in summary


def test_unknown_and_not_found_do_not_become_zero(tmp_path, catalog):
    lesson = catalog["S3-STRESS"][0]
    session = Session.create(lesson, "P02", tmp_path / "drafts")
    by_id = {q.id: q for q in questions(lesson)}
    session.record(by_id["p_internal_abs"], {"status": "unknown"})
    session.record(by_id["p_external_abs"], {
        "status": "not_found",
        "reason": "checked dp2-review.md and seed.yaml; no ambient stated for the test site"})
    session.record(by_id["wall_id"], _answer(DP2_CASING_ID_MM))
    session.record(by_id["wall_t"], _answer(DP2_CASING_T_MM))

    answers = session.data["answers"]
    assert answers["p_internal_abs"]["value"] is None
    assert answers["p_external_abs"]["value"] is None
    assert answers["p_external_abs"]["reason"]

    results = {r["id"]: r for r in session.data["computed"]}
    assert results["delta_p"]["status"] == "missing_inputs"
    assert results["delta_p"]["value"] is None
    assert results["hoop_mean_radius"]["value"] is None
    # r/t only needs the geometry, so it still computes.
    assert results["r_over_t"]["status"] == "computed"
    assert session.data["status"] == "in_progress"


def test_not_found_requires_a_search_trail(catalog):
    lesson = catalog["S3-STRESS"][0]
    q = {question.id: question for question in questions(lesson)}["wall_t"]
    with pytest.raises(ValueError, match="search trail"):
        make_answer(q, {"status": "not_found"}, "2026-09-20T00:00:00+00:00")


def test_answered_engineering_numbers_require_source_and_uncertainty(catalog):
    lesson = catalog["S3-STRESS"][0]
    q = {question.id: question for question in questions(lesson)}["wall_t"]
    with pytest.raises(ValueError, match="source and uncertainty"):
        make_answer(q, {"value": 1.5, "basis": "candidate"}, "2026-09-20T00:00:00+00:00")


def test_invalid_geometry_in_a_session_is_reported_not_silently_zeroed(catalog):
    """A zero thickness passes the input bound but must not produce a stress."""
    lesson = catalog["S3-STRESS"][0]
    answers = {
        "p_internal_abs": make_answer(
            {q.id: q for q in questions(lesson)}["p_internal_abs"],
            _answer(DP2_P3_ABS_KPA), "2026-09-20T00:00:00+00:00"),
        "p_external_abs": make_answer(
            {q.id: q for q in questions(lesson)}["p_external_abs"],
            _answer(AMBIENT_KPA), "2026-09-20T00:00:00+00:00"),
        "wall_id": make_answer({q.id: q for q in questions(lesson)}["wall_id"],
                               _answer(DP2_CASING_ID_MM), "2026-09-20T00:00:00+00:00"),
        "wall_t": make_answer({q.id: q for q in questions(lesson)}["wall_t"],
                              _answer(0.0), "2026-09-20T00:00:00+00:00"),
    }
    results = {r["id"]: r for r in calculate(lesson, answers)}
    assert results["hoop_mean_radius"]["status"] == "invalid_inputs"
    assert results["hoop_mean_radius"]["value"] is None
    assert "greater than zero" in results["hoop_mean_radius"]["error"]


def test_external_pressure_case_is_reported_as_invalid_with_an_explanation(catalog):
    lesson = catalog["S3-STRESS"][0]
    by_id = {q.id: q for q in questions(lesson)}
    stamp = "2026-09-20T00:00:00+00:00"
    answers = {
        "p_internal_abs": make_answer(by_id["p_internal_abs"], _answer(50.0), stamp),
        "p_external_abs": make_answer(by_id["p_external_abs"], _answer(AMBIENT_KPA), stamp),
        "wall_id": make_answer(by_id["wall_id"], _answer(DP2_CASING_ID_MM), stamp),
        "wall_t": make_answer(by_id["wall_t"], _answer(DP2_CASING_T_MM), stamp),
    }
    results = {r["id"]: r for r in calculate(lesson, answers)}
    assert results["hoop_mean_radius"]["status"] == "invalid_inputs"
    assert "buckling" in results["hoop_mean_radius"]["error"]
    # The pressure difference itself is still reportable, and negative.
    assert results["delta_p"]["value"] < 0


def test_c2fab_optional_costs_and_negative_clearance(tmp_path, catalog):
    lesson = catalog["C2-FAB"][0]
    session = Session.create(lesson, "P03", tmp_path / "drafts")
    _fill(session, {
        "coupon_length": _answer(120.0), "coupon_width": _answer(60.0),
        "coupon_count": _answer(6), "scrap_percent": _answer(25.0),
        "stock_price": _answer(140.0), "shipping_cost": _answer(22.0),
        "nominal_clearance": _answer(2.0), "roundness_tol": _answer(1.5),
        "distortion_allow": _answer(1.0), "fitup_tol": _answer(0.4),
    })
    results = {r["id"]: r for r in session.data["computed"]}
    assert results["stock_area"]["value"] == pytest.approx(54000.0, rel=1e-9)
    assert results["cash_cost"]["value"] == pytest.approx(162.0, rel=1e-9)
    assert results["clearance_left"]["value"] == pytest.approx(-0.9, rel=1e-9)
    assert results["clearance_left"]["status"] == "computed"
    assert "NEGATIVE" in results["clearance_left"]["limitations"]
    assert "NOT subtracted" in results["cash_cost"]["limitations"]
    assert "counted exactly once" in results["cash_cost"]["limitations"]


def test_s4bend_optional_deflection_is_skipped_without_inventing_inputs(tmp_path, catalog):
    lesson = catalog["S4-BEND"][0]
    session = Session.create(lesson, "P04", tmp_path / "drafts")
    _fill(session, {
        "outer_d": _answer(8.0), "inner_d": _answer(0.0),
        "bending_moment": _answer(0.062), "y_distance": _answer(4.0),
        "shaft_torque": _answer(2.6147),
    })
    results = {r["id"]: r for r in session.data["computed"]}
    assert results["I_area"]["value"] == pytest.approx(2.0106e-10, rel=1e-3)
    assert results["J_polar"]["value"] == pytest.approx(4.0212e-10, rel=1e-3)
    assert results["torsion_tau"]["value"] == pytest.approx(26.0, rel=1e-2)
    # Optional inputs untouched: no defaults substituted.
    assert results["midspan_deflection"]["status"] == "missing_inputs"
    assert results["midspan_deflection"]["value"] is None


def test_records_for_two_slots_never_share_a_file(tmp_path, catalog):
    lesson = catalog["S3-STRESS"][0]
    first = Session.create(lesson, "P01", tmp_path / "drafts")
    second = Session.create(lesson, "P02", tmp_path / "drafts")
    assert first.folder != second.folder
    assert first.data["session_id"] != second.data["session_id"]
    by_id = {q.id: q for q in questions(lesson)}
    first.record(by_id["wall_t"], _answer(1.5))
    second.record(by_id["wall_t"], _answer(2.0))
    assert read_json(first.folder / "answers.json")["answers"]["wall_t"]["value"] == 1.5
    assert read_json(second.folder / "answers.json")["answers"]["wall_t"]["value"] == 2.0


# ------------------------------------------------------------------- real CLI

def _cli(*args):
    return subprocess.run([sys.executable, str(DOMAIN / args[0]), *map(str, args[1:])],
                          input="", capture_output=True, text=True, encoding="utf-8",
                          cwd=REPO, timeout=60)


@pytest.mark.parametrize("script", ["pressure_wall.py", "beam_and_shaft.py",
                                    "fabrication_coupon.py"])
def test_help_and_preview_run_without_writing_anything(tmp_path, script):
    before = sorted(p.name for p in (REPO / "out").glob("*")) if (REPO / "out").exists() else []

    assert _cli(script, "--help").returncode == 0
    preview = _cli(script, "--preview")
    assert preview.returncode == 0, preview.stderr
    assert "UNKNOWN or NOT FOUND" in preview.stdout
    assert "No files were written" in preview.stdout

    after = sorted(p.name for p in (REPO / "out").glob("*")) if (REPO / "out").exists() else []
    assert before == after, "--help/--preview must not create anything under out/"
    # And nothing landed in the temporary directory either.
    assert not list(tmp_path.iterdir())


def test_noninteractive_run_without_answers_refuses_rather_than_guessing():
    result = _cli("pressure_wall.py", "--slot", "P01")
    assert result.returncode == 2
    assert "preview" in (result.stdout + result.stderr).lower()


def test_answers_batch_is_validated_before_a_session_exists(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"wall_t": {"value": -3.0, "basis": "candidate",
                                          "source": "x", "uncertainty": "y"}}),
                   encoding="utf-8")
    result = _cli("pressure_wall.py", "--slot", "P01", "--answers", str(bad),
                  "--data-dir", str(tmp_path / "data"))
    assert result.returncode == 2
    assert not (tmp_path / "data").exists(), "no session may be created from a bad batch"
