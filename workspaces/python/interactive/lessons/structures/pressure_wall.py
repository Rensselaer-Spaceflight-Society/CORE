"""S3-STRESS - Track A, lesson 1: what load is on the casing wall, and what is not.

Run it:  python workspaces/python/interactive/lessons/structures/pressure_wall.py
Preview: same command with --preview  (read-only, writes nothing)

This extends the structures track. It does not replace S1 (bearing datasheet)
or S2 (inlet drawing); see workspaces/structures/TASK-CODE-MAP.md.
"""

from pathlib import Path
import sys

_HERE = Path(__file__).resolve().parent
for _folder in (_HERE.parents[1], _HERE):
    if str(_folder) not in sys.path:
        sys.path.insert(0, str(_folder))

from runtime import Calculation, Lesson, Question, Step, run_lesson  # noqa: E402
import _structures_math as sm  # noqa: E402

MPA = 1.0e6


def build_lesson():
    return Lesson(
        id="S3-STRESS", version="1.0",
        title="One pressure wall: draw the load, then size the stress",
        review_role="Structures lead (Safety for any running or pressurised hardware)",
        minutes="30-45",
        prerequisites=(
            "This lesson is about ONE specific part: the CORE candidate outer "
            "casing. Everyone works that same wall, so your recorded geometry and "
            "pressure can be compared against everyone else's - which is how a "
            "stale drawing revision gets caught. If your lead wants a different "
            "wall analysed, do that as a separate second pass afterwards.",
            "Paper and a pencil. The first deliverable is a sketch, not a number.",
            "No hardware, no pressure test, no purchase. Nothing rotates or is "
            "pressurised for this lesson.",
        ),
        sources=(
            "Air Force Flight Dynamics Laboratory, Stress Analysis Manual, "
            "October 1986, Sec. 8.3.1 (thin pressure vessels): "
            "https://engineeringlibrary.org/reference/simple-thin-pressure-vessels-air-force-stress-manual",
            "P. Kelly, Solid Mechanics Part I, Sec. 7.3 The Thin-walled Pressure "
            "Vessel Theory (Univ. of Auckland): "
            "https://pkel015.connect.amazon.auckland.ac.nz/SolidMechanicsBooks/Part_I/BookSM_Part_I/07_ElasticityApplications/07_Elasticity_Applications_03_Presure_Vessels.pdf",
            "docs/project/dp2-review.md - DP-2 candidate parameters and their status",
            "docs/project/checks/dp2_screen.py - the prescribed cycle screen that "
            "produces the candidate P3; run it yourself, it changes no configuration",
            "docs/model-review.md - open mechanical assumptions, including "
            "temperature-dependent allowables and outer-liner buckling",
            "config/seed.yaml and config/limits.yaml - the casing wall, material "
            "density and assembly clearance the model currently uses",
            "modules/m34_casing.py - the module that owns D_casing_out_m",
            "workspaces/structures/object tests/object-example.py - the existing "
            "structures example this lesson builds on",
        ),
        steps=(
            Step(
                "fbd", "1. Draw it before you calculate it",
                "Start on paper. Draw the wall as a line. Draw an arrow for every "
                "push on it and every thing that holds it still. That picture is "
                "the free-body diagram, and it is the whole job; the algebra "
                "afterwards is bookkeeping.\n\n"
                "For a pressurised cylinder there are only a few arrows. Gas "
                "presses outward on the inside face, everywhere, at right angles "
                "to the surface. Air presses inward on the outside face. The wall "
                "material is stretched around the circumference resisting the "
                "difference - that stretch is HOOP stress. If the ends of the "
                "cylinder are closed AND those ends hang off this same wall, the "
                "pressure pushing on the end caps also stretches the wall along "
                "its length - that is AXIAL stress, and it is half the hoop "
                "stress. If the ends are open, or the end load is carried by tie "
                "bolts, a flange or the shaft instead, this wall does not see it.\n\n"
                "So the first question is not 'what is the stress', it is 'what is "
                "holding what'. Get that wrong and every digit afterwards is "
                "wrong too.",
                (
                    Question(
                        "wall_component",
                        "Which section of the candidate casing are you analysing? Say "
                        "where it starts and where it stops.",
                        evidence=False,
                        hint="For example: 'the CORE candidate outer casing cylinder, "
                             "between the compressor backplate and the turbine end flange'. "
                             "Name the plain cylindrical run you are treating, not the whole "
                             "engine.",
                    ),
                    Question(
                        "load_path",
                        "In one or two sentences: what pushes on this wall, and what holds it still?",
                        evidence=False,
                        hint="Use /text for several lines. Describe your sketch in words - "
                             "inside pressure, outside pressure, mounts, flanges, bolts.",
                    ),
                    Question(
                        "end_condition",
                        "Does this wall carry the pressure end load itself?",
                        kind="choice",
                        choices=("closed ends carried by this wall",
                                 "open ended, or the end load is carried by something else",
                                 "UNKNOWN - to confirm with the lead"),
                        hint="This choice decides whether the axial-stress number later in "
                             "the lesson applies to your part at all. Record where you got "
                             "the arrangement from - a drawing, the lead, or your own "
                             "assumption (basis: hypothesis).",
                    ),
                ),
                visual="pressure_wall.html",
            ),
            Step(
                "ledger", "2. The input ledger: every number gets a label",
                "Now write down the inputs. Each one needs a value, a unit and a "
                "place it came from. This is the part people skip and it is the "
                "part that causes wrong answers.\n\n"
                "PRESSURE. There is no such thing as 'the pressure' on its own. "
                "ABSOLUTE pressure is measured from vacuum. GAUGE pressure is "
                "measured from whatever is outside, usually ambient air. A wall "
                "does not care about either one by itself - it feels the "
                "DIFFERENCE across it, p_inside minus p_outside. The Air Force "
                "Stress Analysis Manual writes the formula that way on purpose. "
                "So this lesson asks for two absolute pressures, and subtracts "
                "them where you can see it happen. If your source gave you gauge, "
                "say what ambient it was gauged against and convert it yourself.\n\n"
                "For the CORE candidate casing, the prescribed cycle screen in "
                "docs/project/checks/dp2_screen.py reports compressor delivery "
                "P3 = 163.51 kPa absolute at the DP-2 design point, against "
                "101.325 kPa ambient. That difference is about 62.2 kPa. Run the "
                "screen and read it yourself rather than trusting this paragraph. "
                "And note what that number is NOT: it is a screen at one "
                "prescribed point, not a measured casing static pressure, not a "
                "proof or burst pressure, not a surge or transient case, and not "
                "containment evidence.\n\n"
                "GEOMETRY. Inner diameter and wall thickness, from a drawing with "
                "a revision if you can get one. The DP-2 note proposes a casing "
                "152.4 mm outside and 149.4 mm inside, which is a 1.5 mm wall; "
                "config/seed.yaml carries casing_wall_m = 0.0015 as 6061. Check "
                "whether those two still agree before you use either.\n\n"
                "TEMPERATURE. Here is the trap. The DP-2 candidate turbine inlet "
                "total temperature is about 1150 K. That is the GAS. It is not "
                "the temperature of this metal. A wall's temperature is set by "
                "what heats it, what cools it and what it is connected to - "
                "radiation and convection in, convection to the annulus air and "
                "conduction to the flanges out. In a reverse-flow engine the "
                "outer casing is on the cold side of the liner and is washed by "
                "compressor delivery air. It runs far cooler than the flame, but "
                "'far cooler' is not a number and you cannot pick a material "
                "allowable from a guess. docs/model-review.md lists "
                "temperature-dependent allowables as an unresolved assumption, "
                "and dp2-review.md item 7 makes the same point for the turbine.",
                (
                    Question(
                        "p_internal_abs",
                        "Internal pressure on this wall, ABSOLUTE",
                        kind="number", units="kPa", minimum=0, maximum=100000,
                        comparison_key="core.casing.candidate.internal_pressure_abs_kPa",
                        hint="If your source is gauge, add the ambient you are gauging "
                             "against and say so in assumptions. Two students reading the "
                             "same file is not two independent confirmations - say in "
                             "'source' exactly which file and revision you read.",
                    ),
                    Question(
                        "p_external_abs",
                        "Pressure on the OUTSIDE of this wall, ABSOLUTE",
                        kind="number", units="kPa", minimum=0, maximum=100000,
                        hint="Usually ambient. 101.325 kPa is the standard sea-level value "
                             "the cycle screen uses; Troy, NY is not at sea level and the "
                             "weather moves it. Entering 0 here means a vacuum outside - "
                             "only correct if that is really the case.",
                    ),
                    Question(
                        "pressure_reference",
                        "How did you establish the pressure reference?",
                        kind="choice",
                        choices=("source gave absolute pressure directly",
                                 "source gave gauge; I converted using a stated ambient",
                                 "UNKNOWN - the source does not say which it is"),
                        hint="'The source does not say' is a real and useful finding. "
                             "Record it rather than guessing.",
                    ),
                    Question(
                        "wall_id",
                        "Inner diameter of the wall",
                        kind="number", units="mm", minimum=0, maximum=10000,
                        comparison_key="core.casing.candidate.inner_diameter_mm",
                        hint="From a drawing with a revision if you can get one. If you are "
                             "working from the DP-2 note instead, say that in 'source' and "
                             "use basis: candidate.",
                    ),
                    Question(
                        "wall_t",
                        "Wall thickness",
                        kind="number", units="mm", minimum=0, maximum=1000,
                        comparison_key="core.casing.candidate.wall_thickness_mm",
                        hint="Nominal, minimum or measured? Sheet has a thickness tolerance "
                             "and forming thins the outside of a bend. Say which one you "
                             "have in 'assumptions'.",
                    ),
                    Question(
                        "support_assumption",
                        "How is this wall supported and attached? What did you have to assume?",
                        hint="Mount points, flanges, joints, anything that restrains it. "
                             "If you are assuming, use basis: hypothesis and say so.",
                    ),
                    Question(
                        "material_evidence",
                        "What material is this wall, and what is your evidence?",
                        hint="Alloy and temper both matter: 6061-T6 and 6061-O are the same "
                             "alloy with very different strength. A line in a config file is "
                             "a modelling choice, not a material certificate.",
                    ),
                    Question(
                        "wall_temperature_basis",
                        "What do you actually know about this wall's METAL temperature?",
                        hint="Not the gas temperature. What heats it, what cools it, and "
                             "what evidence do you have for either? 'UNKNOWN, no thermal "
                             "evidence exists yet' is an honest and useful answer here - "
                             "use /skip for UNKNOWN or /not-found with your search trail.",
                    ),
                ),
                visual="pressure_wall.html",
            ),
            Step(
                "stress", "3. Do it by hand first, then let the machine agree with you",
                "The thin-wall result, from the Air Force Stress Analysis Manual "
                "Sec. 8.3.1 and any mechanics text:\n\n"
                "    hoop      sigma_h = (p_i - p_o) * r / t\n"
                "    axial     sigma_a = (p_i - p_o) * r / (2t)   [closed ends only]\n\n"
                "Work the hoop one out yourself, on paper, from the numbers you "
                "just recorded. Then compare. If you and the machine disagree, "
                "one of you has a unit problem, and finding it is the single most "
                "useful thing in this lesson.\n\n"
                "Units cancel like this. Pressure is Pa = N/m^2. Radius and "
                "thickness are both metres, so r/t is dimensionless. N/m^2 times "
                "a dimensionless number is N/m^2, which is Pa. Stress and "
                "pressure share a unit; that is not a coincidence, they are both "
                "force over area. 1 MPa = 1,000,000 Pa = 1 N/mm^2. If you left "
                "diameters in mm and pressure in kPa, you are out by a factor of "
                "a thousand somewhere - which is exactly the kind of error that "
                "makes a wall look 1000x safer than it is.\n\n"
                "Two worked references. The EXAMPLE in the existing structures "
                "file object-example.py uses 2 MPa across a 200 mm bore with a "
                "1 mm wall and gets 200 MPa on the inner radius. Those are "
                "teaching loads chosen to make the arithmetic clear; they are NOT "
                "CORE loads. The CORE CANDIDATE casing - 62.2 kPa across a "
                "149.4 mm bore with a 1.5 mm wall - comes out near 3.1 MPa. The "
                "two differ by a factor of about 64. A number with no label is "
                "how the wrong one of those ends up in somebody's drawing.\n\n"
                "You will also see two hoop results below, one on the mid-wall "
                "radius and one on the inner radius. Kelly Sec. 7.3 says either "
                "is acceptable for a thin wall and 'results for all three should "
                "be close'. The gap between them is a free, honest measure of how "
                "much this idealisation is worth on your geometry. It is about "
                "1% on the candidate casing. It is not a safety margin.",
                (
                    Question(
                        "hand_hoop_mpa",
                        "Your OWN hand-worked hoop stress, from your recorded numbers",
                        kind="number", units="MPa", minimum=0, maximum=1.0e6,
                        hint="Convert to metres and Pa first, then divide by 1e6 at the end. "
                             "Write your working on the paper with the sketch. Use basis "
                             "'student' - this is your arithmetic, not a sourced value - with "
                             "source 'own hand calculation from the ledger above'. In "
                             "'uncertainty', say which radius convention you used and that "
                             "this is an arithmetic check, not evidence about the part.",
                    ),
                    Question(
                        "unit_cancellation",
                        "Write out how the units cancel to give a stress.",
                        evidence=False,
                        hint="Something like: (N/m^2) * (m / m) = N/m^2 = Pa. Say it in your "
                             "own words; this is the check that catches mm/m mistakes.",
                    ),
                ),
                visual="pressure_wall.html",
            ),
            Step(
                "applicability", "4. Where this screen stops being true",
                "Thin-wall membrane theory assumes the stress is uniform through "
                "the thickness. That is only nearly true when the wall is thin "
                "compared with the radius. The Air Force Stress Analysis Manual "
                "Sec. 8.3.1 draws the line at r/t greater than ten. Kelly Sec. "
                "7.3 puts the same rule in its author's words: below about a "
                "tenth of the radius, the actual stress \"will vary by less than "
                "about 5%\" through the thickness. "
                "Inside that region the formula is a good screen. Outside it you "
                "need the thick-wall (Lame) solution and a different conversation.\n\n"
                "Even INSIDE that region, look at what this screen still does not "
                "know about:\n\n"
                "  * BUCKLING. A thin wall with net pressure on the OUTSIDE, or "
                "    with axial compression from mounts, can collapse long before "
                "    it reaches any tensile stress number. docs/model-review.md "
                "    lists outer-liner external-pressure buckling as unresolved.\n"
                "  * HOLES AND CUTOUTS. Every instrumentation boss, igniter "
                "    penetration and bolt hole raises the local stress well above "
                "    the membrane value. A hole in a uniform tension field roughly "
                "    triples it before you add anything else.\n"
                "  * WELDS AND JOINTS. A weld is a different material with a "
                "    different history, and a girth joint sees only half the hoop "
                "    stress - so a seam that is fine in one direction can be the "
                "    weak line in the other. Track B (C2-FAB) is about exactly this.\n"
                "  * TEMPERATURE. Material properties fall with temperature, and "
                "    they are not linear. Room-temperature data is not a hot-part "
                "    allowable.\n"
                "  * FATIGUE AND CYCLES. Start, run, shut down, cool. A stress "
                "    that is harmless once may not be harmless a thousand times.\n\n"
                "None of these disappear because a screening number looked small. "
                "Write them down so the next person knows they are still open.",
                (
                    Question(
                        "thin_wall_judgement",
                        "Does the thin-wall screen apply to YOUR geometry?",
                        kind="choice",
                        choices=("yes - r/t is greater than 10",
                                 "no - r/t is 10 or less, this needs a thick-wall solution",
                                 "UNKNOWN - I do not have the geometry yet"),
                        hint="The lesson computes r/t for you below. Cite the criterion you "
                             "are judging against in 'source' - the AFFDL manual section is "
                             "in this lesson's source list.",
                    ),
                    Question(
                        "excluded_effects",
                        "Name at least three things this screen does NOT cover for your wall.",
                        evidence=False,
                        hint="Use /text. Pick the ones that are real for YOUR part - does it "
                             "have holes? a seam? does anything bolt to it? does it get hot?",
                    ),
                    Question(
                        "allowable_source",
                        "Where would a defensible design allowable for this wall come from?",
                        hint="Not from this lesson. Name the kind of document you would need "
                             "and the conditions it has to state - alloy, temper, "
                             "temperature, welded or parent metal, loading direction. Say "
                             "plainly why an ultimate tensile strength at room temperature "
                             "is not the answer. NOT FOUND with a search trail is fine.",
                    ),
                ),
                visual="pressure_wall.html",
            ),
            Step(
                "handoff", "5. Hand it on",
                "You now have a sketch, a labelled ledger, a screening number and "
                "a list of what is still unknown. That is a complete, useful piece "
                "of work, and it is not an approval of anything.\n\n"
                "What happens next is not yours to decide alone: the structures "
                "lead owns the casing analysis, Safety owns anything pressurised "
                "or rotating, and the shop/welding authority owns how it gets "
                "made. Your job here is to make their next decision easier by "
                "saying clearly what you found and what you could not.",
                (
                    Question(
                        "lead_decision",
                        "What does the structures lead need to decide or confirm?",
                        evidence=False, role="decision",
                        hint="Be specific. 'Which drawing revision is current for the casing' "
                             "beats 'check the casing'.",
                    ),
                    Question(
                        "next_step",
                        "What is your next small step?",
                        evidence=False, role="next_step",
                        hint="One step, 30 minutes or less. Finding one document counts.",
                    ),
                ),
            ),
        ),
        calculations=(
            Calculation(
                "delta_p", "Pressure difference across the wall",
                ("p_internal_abs", "p_external_abs"),
                lambda p_internal_abs, p_external_abs: sm.delta_p_pa(
                    p_internal_abs, p_external_abs) / 1000.0,
                units="kPa",
                method="delta_p = p_internal_abs - p_external_abs, both absolute, in kPa. "
                       "This is the quantity the wall actually feels; it equals the gauge "
                       "pressure only when the outside is exactly at the gauge reference.",
                version="1",
                limitations="One steady operating point. Not a proof, burst, surge or "
                            "transient pressure, and not a measured value.",
            ),
            Calculation(
                "r_over_t", "Mid-wall radius / thickness (thin-wall applicability)",
                ("wall_id", "wall_t"),
                lambda wall_id, wall_t: sm.r_over_t(wall_id, wall_t),
                units="dimensionless",
                method="r_over_t = ((ID + t)/2) / t with ID and t in mm. Thin-wall membrane "
                       "theory is applicable above 10 per AFFDL Stress Analysis Manual "
                       "Sec. 8.3.1; Kelly Sec. 7.3 states the same rule as the stress "
                       "varying by less than about 5% through the thickness.",
                version="1",
                limitations="Applicability screen for the FORMULA only. It says nothing about "
                            "whether the wall is strong enough, and nothing about buckling, "
                            "holes, welds, temperature or fatigue.",
            ),
            Calculation(
                "hoop_mean_radius", "Hoop stress on the mid-wall radius",
                ("p_internal_abs", "p_external_abs", "wall_id", "wall_t"),
                lambda p_internal_abs, p_external_abs, wall_id, wall_t: sm.hoop_stress_pa(
                    p_internal_abs, p_external_abs, wall_id, wall_t) / MPA,
                units="MPa",
                method="sigma_h = (p_i - p_o) * r_mean / t, r_mean = (ID + t)/2. AFFDL Stress "
                       "Analysis Manual Sec. 8.3.1. Inputs kPa and mm, converted to Pa and m "
                       "inside the function, result divided by 1e6.",
                version="1",
                limitations="Membrane stress in a plain cylindrical wall at one steady "
                            "pressure. Excludes ends, holes, welds, joints, mounts, thermal "
                            "stress, buckling, fatigue and stress concentration. COMPUTED, "
                            "not measured; it is not compared against any allowable and it "
                            "is not an approval.",
            ),
            Calculation(
                "hoop_inner_radius", "Hoop stress on the inner radius (object-example.py convention)",
                ("p_internal_abs", "p_external_abs", "wall_id", "wall_t"),
                lambda p_internal_abs, p_external_abs, wall_id, wall_t:
                    sm.hoop_stress_inner_radius_pa(
                        p_internal_abs, p_external_abs, wall_id, wall_t) / MPA,
                units="MPa",
                method="sigma_h = (p_i - p_o) * r_inner / t, r_inner = ID/2. Same formula on "
                       "the inner radius, matching workspaces/structures/'object tests'/"
                       "object-example.py. Kelly Sec. 7.3 allows inner, outer or mean radius "
                       "for a thin wall.",
                version="1",
                limitations="Shown alongside the mid-wall result so the difference between "
                            "the two conventions is visible. That difference is a measure of "
                            "the idealisation, NOT a safety margin. Same exclusions as the "
                            "mid-wall result.",
            ),
            Calculation(
                "axial_closed_end", "Axial stress, CLOSED ends carried by this wall",
                ("p_internal_abs", "p_external_abs", "wall_id", "wall_t"),
                lambda p_internal_abs, p_external_abs, wall_id, wall_t:
                    sm.axial_stress_closed_end_pa(
                        p_internal_abs, p_external_abs, wall_id, wall_t) / MPA,
                units="MPa",
                method="sigma_a = (p_i - p_o) * r_mean / (2t), exactly half the mid-wall hoop "
                       "stress. AFFDL Stress Analysis Manual Sec. 8.3.1.",
                version="1",
                limitations="APPLIES ONLY if you recorded 'closed ends carried by this wall' "
                            "in step 1. If the ends are open, or the end load is taken by "
                            "tie bolts, a flange or the shaft, this number is not a load on "
                            "your part. The lesson cannot check your end condition for you.",
            ),
        ),
    )


if __name__ == "__main__":
    raise SystemExit(run_lesson(build_lesson(), __file__))
