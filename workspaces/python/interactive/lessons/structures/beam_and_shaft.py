"""S4-BEND - Track A, lesson 2: bending, torsion, and three things called "I".

Run it:  python workspaces/python/interactive/lessons/structures/beam_and_shaft.py
Preview: same command with --preview  (read-only, writes nothing)

Follows S3-STRESS. Finishes the unfinished shaft idea in
workspaces/structures/'object tests'/object-example.py without touching that
file - see workspaces/structures/object tests/README.md for why.
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


def _i_section(outer_d, inner_d):
    return sm.second_moment_area_tube_m4(outer_d, inner_d)


def _j_section(outer_d, inner_d):
    return sm.polar_moment_area_tube_m4(outer_d, inner_d)


def build_lesson():
    return Lesson(
        id="S4-BEND", version="1.0",
        title="Bending, torsion, and the three different things called I",
        review_role="Structures lead (Safety for any rotating hardware or spin test)",
        minutes="30-45",
        prerequisites=(
            "Do S3-STRESS first if you have not. This lesson assumes you have "
            "drawn one free-body diagram already.",
            "Agree with your lead which shaft or beam you are looking at. The "
            "worked references use the CORE candidate shaft.",
            "Nothing rotates, nothing is loaded, nothing is bought for this lesson.",
        ),
        sources=(
            "modules/m30_shaft.py - the module that owns d_shaft_m, torque_Nm and "
            "L_bear_span_m; read how it actually sizes the shaft",
            "config/seed.yaml - tau_allow_shaft_Pa, E_shaft_Pa, rho_shaft_kg_m3 and "
            "the comments beside them",
            "config/limits.yaml - N_crit_margin_min_frac and DN_max_mm_rpm",
            "docs/model-review.md - preliminary critical speed, startup crossing, and "
            "the open mechanical assumptions list",
            "docs/project/dp2-review.md - candidate speed, rotor energy and the "
            "bearing-speed warning",
            "docs/project/checks/dp2_screen.py - compressor power and rotor energy "
            "at the candidate point",
            "workspaces/structures/S1-shaft-bearings.md - the existing S1 card this "
            "lesson hands back to",
        ),
        steps=(
            Step(
                "loads", "1. A shaft is a beam that also twists",
                "Two different things happen in a shaft and they do not mix.\n\n"
                "BENDING. Anything hanging off the shaft - a compressor wheel at one "
                "end, a turbine wheel at the other - pulls sideways under its own "
                "weight, under any out-of-balance force, and under gyroscopic loads "
                "when the engine yaws. That sideways load, times a distance, is a "
                "bending MOMENT, in newton-metres. It stretches one side of the "
                "shaft and squashes the other. Halfway between is a line that is "
                "neither: the NEUTRAL AXIS. Stress grows with distance from it.\n\n"
                "    sigma = M * y / I\n\n"
                "TORSION. The turbine twists one end of the shaft and the "
                "compressor resists at the other. That is a TORQUE, also in "
                "newton-metres, and it produces shear stress that grows with "
                "distance from the centreline.\n\n"
                "    tau = T * r / J\n\n"
                "Same units on M and T, completely different loads. Before either "
                "formula means anything you have to say where the supports are and "
                "where the load acts - a 'beam' with unstated supports has no "
                "answer, not a default one.",
                (
                    Question(
                        "component",
                        "Which shaft or beam are you analysing, and what hangs off it?",
                        evidence=False,
                        hint="For example: 'the CORE candidate shaft, compressor wheel at "
                             "one end, turbine wheel at the other, two bearings between'.",
                    ),
                    Question(
                        "support_condition",
                        "How is it supported?",
                        kind="choice",
                        choices=("simply supported at two points",
                                 "built in (fixed) at both ends",
                                 "cantilever - held at one end only",
                                 "overhung - supported between two bearings with mass outboard",
                                 "UNKNOWN - I do not have this yet"),
                        hint="A real rotor on two bearings with wheels outboard is 'overhung', "
                             "and it is NOT the same as a simply supported beam. If you pick "
                             "something to make the arithmetic work, say so with "
                             "basis: hypothesis.",
                    ),
                    Question(
                        "load_position",
                        "Where does the load act, measured from what datum?",
                        hint="'Mid-span' and '35 mm outboard of the front bearing' give very "
                             "different moments. Name the datum you measured from.",
                    ),
                ),
                visual="shaft_sections.html",
            ),
            Step(
                "sections", "2. Three quantities, three jobs, and people call them all I",
                "This is the single most common mix-up in a first structures "
                "assignment, and it is worth thirty seconds of care.\n\n"
                "  I - SECOND MOMENT OF AREA, units m^4.\n"
                "      Pure geometry of the cross-section about a bending axis.\n"
                "      Solid round bar: I = pi*d^4/64. Used in M*y/I and in\n"
                "      deflection. Tells you how hard a section is to BEND.\n\n"
                "  J - POLAR second moment of area, units m^4.\n"
                "      Same idea, but about the centreline, for twisting.\n"
                "      Solid round bar: J = pi*d^4/32, which is exactly 2I.\n"
                "      Used in T*r/J. Tells you how hard a section is to TWIST.\n"
                "      (That neat J = 2I relation is true for round sections.\n"
                "      For a non-circular section, torsion needs a different\n"
                "      constant altogether, not the polar moment.)\n\n"
                "  I - MASS moment of inertia, units kg*m^2.\n"
                "      A different quantity that happens to share a letter. It\n"
                "      involves MASS, not just shape. Solid cylinder about its\n"
                "      spin axis: I = m*r^2/2. This is the I in rotational\n"
                "      kinetic energy 0.5*I*omega^2 - the 5.087 kJ the DP-2\n"
                "      screen reports for the rotor. It never appears in M*y/I\n"
                "      or T*r/J.\n\n"
                "Check yourself with units. m^4 and kg*m^2 are not the same kind "
                "of thing; if a number in m^4 turns up in an energy calculation, "
                "something is wrong.\n\n"
                "Notice the fourth power. Stiffness scales with d^4, so going from "
                "an 8 mm shaft to a 10 mm shaft more than doubles I. It also means "
                "a modest central bore costs very little: boring 4 mm out of an "
                "8 mm shaft removes a quarter of the metal but only about 6% of I. "
                "Enter 0 below for a solid shaft.",
                (
                    Question(
                        "outer_d",
                        "Outer diameter of the section you are analysing",
                        kind="number", units="mm", minimum=0, maximum=10000,
                        hint="At the section you care about. A stepped shaft has several; "
                             "pick one and say which in 'assumptions'.",
                    ),
                    Question(
                        "inner_d",
                        "Inner (bore) diameter - enter 0 for a solid shaft",
                        kind="number", units="mm", minimum=0, maximum=10000,
                        hint="0 is a real answer here, not a missing one. If the part is "
                             "bored and you do not know the bore, use UNKNOWN instead of 0.",
                    ),
                    Question(
                        "three_inertias",
                        "In your own words: what is the difference between the three I's, "
                        "and which one appears in 0.5*I*omega^2?",
                        evidence=False,
                        hint="Two or three sentences. Mention the units of each - that is "
                             "the part that actually protects you later.",
                    ),
                ),
                visual="shaft_sections.html",
            ),
            Step(
                "bending", "3. Bending stress",
                "sigma = M*y/I, with y measured from the NEUTRAL AXIS - the "
                "centreline of a symmetric round section, not the surface you "
                "happened to rest a ruler on. At the outer fibre y = d/2, and that "
                "is where the stress is highest in a plain section.\n\n"
                "Getting M is usually the hard part, and it is usually where the "
                "uncertainty lives. A wheel mass times gravity times an overhang "
                "gives you the static part. Out-of-balance force grows with the "
                "square of speed, and the DP-2 review records the chosen G2.5 "
                "balance grade as needing its own review. Gyroscopic loads need a "
                "manoeuvre case nobody has defined yet.\n\n"
                "If you do not have a defensible M, say UNKNOWN. A precise-looking "
                "stress computed from an invented moment is worse than no number, "
                "because the next person cannot see that you invented it.",
                (
                    Question(
                        "bending_moment",
                        "Bending moment at your section",
                        kind="number", units="N*m", minimum=-1.0e9, maximum=1.0e9,
                        hint="Show how you got it in 'assumptions' - for example "
                             "'0.18 kg wheel * 9.81 * 0.035 m overhang, static only, no "
                             "unbalance or gyroscopic term'. UNKNOWN is a legitimate answer.",
                    ),
                    Question(
                        "y_distance",
                        "Distance from the neutral axis to the point you are checking",
                        kind="number", units="mm", minimum=0, maximum=10000,
                        hint="Half the outer diameter for the outer fibre. Cite the same "
                             "drawing you used for the diameter.",
                    ),
                ),
                visual="shaft_sections.html",
            ),
            Step(
                "torsion", "4. Torsion, and the allowable that is not an allowable",
                "tau = T*r/J. For a solid round shaft that tidies up to "
                "tau = 16*T/(pi*d^3), which is exactly the relation m30_shaft.py "
                "uses - rearranged to solve for d from an assumed allowable shear "
                "stress.\n\n"
                "Read that module. It does something worth noticing:\n\n"
                "    d_shaft = max(d_from_torsion, d_bearing_bore)\n\n"
                "Work the torsion side out. At the DP-2 candidate point the "
                "compressor absorbs about 18.07 kW at 66,000 rpm. Torque is power "
                "divided by angular speed, and omega = 2*pi*66000/60 = 6,912 rad/s, "
                "so that is about 2.61 N*m. Be precise about which power you "
                "divided: m30_shaft.py uses SHAFT power, dividing compressor power "
                "by eta_mech_frac (0.98 in config/seed.yaml), which gives about "
                "2.67 N*m instead. A 2% difference changes no conclusion here, but "
                "knowing which number you used is the difference between a result "
                "and a rumour.\n\n"
                "Either torque, against the seed file's 280 MPa allowable shear, "
                "needs only about 3.6 mm of shaft. So `max()` never picks the "
                "torsion branch, and the shaft diameter is set by the BEARING BORE. "
                "That is the structural insight, and it holds whichever design "
                "point you are in.\n\n"
                "NOW BE CAREFUL, because this is where people go wrong. There are "
                "two different bearing bores in this repository and they belong to "
                "two different design points:\n\n"
                "  * config/seed.yaml has d_bearing_bore_m = 0.015, that is 15 mm\n"
                "    (its comment notes the KJ66 uses an 8 mm ISO 608). seed.yaml\n"
                "    is still the EARLIER 250 N / PR 3.2 baseline.\n"
                "  * DP-2 proposes an 8 mm journal - that is where the 8 mm x\n"
                "    66,000 rpm = 528,000 DN figure in docs/project/dp2-review.md\n"
                "    comes from, with a 608-class bearing.\n\n"
                "Run the numbers both ways and the shear stress is about 26 MPa in "
                "an 8 mm journal and about 4 MPa in a 15 mm one - a factor of more "
                "than six, purely from which document you took the bore out of. "
                "dp2-review.md says plainly that existing baseline results cannot "
                "be presented as DP-2 results. Mixing DP-2's power into the seed "
                "baseline's geometry, or the reverse, produces a number that is not "
                "true of either engine. Say which design point every input came "
                "from, and do not mix them.\n\n"
                "Whichever bore you use, the conclusion is the same and it is not "
                "reassurance: torsion is simply not the thing that decides this "
                "shaft. A comfortable torsion number tells you nothing about the "
                "things that do - bending, critical speed, bearing capability at "
                "528,000 DN, fits, and fatigue at stress risers.\n\n"
                "And about that 280 MPa. It is a line in config/seed.yaml commented "
                "'4340 steel, allowable shear'. That is a modelling input chosen to "
                "make the model run. It is not a material certificate, it names no "
                "temper, no heat treatment, no temperature, no surface finish, no "
                "fatigue basis and no safety factor. Do not promote a config value "
                "to an allowable by quoting it.",
                (
                    Question(
                        "shaft_torque",
                        "Design-point torque on this shaft",
                        kind="number", units="N*m", minimum=-1.0e9, maximum=1.0e9,
                        hint="Either read it from m30_shaft.py's output, or work it out as "
                             "power/omega yourself and say which you did. State in "
                             "'assumptions' whether you used compressor power or shaft power, "
                             "and which design point the power came from. These are genuinely "
                             "different numbers, so this answer is not grouped across "
                             "learners for comparison.",
                    ),
                    Question(
                        "tau_allow_basis",
                        "Where would a defensible allowable shear stress for this shaft "
                        "come from, and what conditions must it state?",
                        hint="Name the kind of document and the conditions. Say plainly why "
                             "a config comment, an ultimate tensile strength, or a "
                             "room-temperature handbook number is not the answer. NOT FOUND "
                             "with a search trail is a good result here.",
                    ),
                ),
                visual="shaft_sections.html",
            ),
            Step(
                "deflection", "5. Optional: deflection, but only now",
                "Deflection is the obvious next question and it is deliberately "
                "last, because the formula depends entirely on things you were "
                "asked to state in step 1.\n\n"
                "For a SIMPLY SUPPORTED span with a SINGLE CENTRAL load:\n\n"
                "    delta = P * L^3 / (48 * E * I)\n\n"
                "Change the supports and the 48 changes with it - 192 for built-in "
                "ends, and a cantilever with a tip load is P*L^3/(3*E*I), sixteen "
                "times softer than the simply supported case. Same bar, same load, "
                "answers a factor of sixty-four apart. This is why 'what is holding "
                "it' had to come first.\n\n"
                "Note the L^3. Deflection is brutally sensitive to span, so the "
                "bearing span is a bigger lever than the shaft diameter.\n\n"
                "These three questions are OPTIONAL. If you have not got a real "
                "span, load and modulus, use /skip on all three - the lesson will "
                "record the deflection as not calculated rather than inventing "
                "inputs. Skipping honestly is the right answer here.",
                (
                    Question(
                        "supports_stated",
                        "Have you recorded an actual support condition and load position, "
                        "rather than assuming one to make this work?",
                        kind="boolean", evidence=False,
                        hint="Answer no if you guessed. Answering no is fine; it just means "
                             "the deflection number below is illustrative, and you should "
                             "say so when you hand it over.",
                    ),
                    Question(
                        "span", "Span between supports (optional)",
                        kind="number", units="mm", minimum=0, maximum=100000, required=False,
                        hint="/skip if you do not have it. m30_shaft.py computes "
                             "L_bear_span_m as a fraction of shaft length - that is an "
                             "assumption, not a measurement.",
                    ),
                    Question(
                        "load_n", "Transverse load at mid-span (optional)",
                        kind="number", units="N", minimum=-1.0e9, maximum=1.0e9, required=False,
                        hint="/skip if you do not have it. Say whether this is static weight "
                             "only or includes an unbalance estimate.",
                    ),
                    Question(
                        "modulus", "Elastic modulus E at the temperature you care about (optional)",
                        kind="number", units="GPa", minimum=0, maximum=2000, required=False,
                        hint="config/seed.yaml has E_shaft_Pa = 205 GPa. That is a "
                             "room-temperature steel value. If your part runs hot, say so "
                             "in 'uncertainty'.",
                    ),
                ),
                visual="shaft_sections.html",
            ),
            Step(
                "limits", "6. What a comfortable stress number still does not buy you",
                "Everything in this lesson is elastic, static, plain-section "
                "screening. Write down what it leaves open for YOUR part:\n\n"
                "  * STRESS CONCENTRATION. Steps, shoulders, keyways, circlip "
                "    grooves, cross-holes and thread runouts all raise local stress "
                "    well above the plain-section value. Rotating shafts fail at "
                "    those features, not in the middle of a smooth length.\n"
                "  * FATIGUE. A rotating shaft under a steady sideways load sees "
                "    fully reversed bending on every revolution. At 66,000 rpm that "
                "    is 1,100 cycles every second. A stress that is harmless once is "
                "    a different question a million cycles later.\n"
                "  * CRITICAL SPEED. docs/model-review.md reports a preliminary "
                "    bending critical speed near 23,400 rpm, says startup crosses "
                "    it, and says separation from the proposed continuous range is "
                "    about 10% against a 20% criterion in config/limits.yaml. That "
                "    is a stiffness-and-mass problem. No amount of stress margin "
                "    fixes it, and note that this figure belongs to the earlier "
                "    baseline, not to DP-2.\n"
                "  * BUCKLING AND COMBINED LOADS. Axial compression, and bending "
                "    plus torsion acting together, are not covered by either "
                "    formula on its own.\n"
                "  * TEMPERATURE. E and every strength property fall with "
                "    temperature, and not linearly.\n\n"
                "None of these go away because a screening number looked small.",
                (
                    Question(
                        "not_covered",
                        "Which of these is most likely to actually decide YOUR part, and why?",
                        evidence=False,
                        hint="Use /text. Pick one and argue it in two or three sentences. "
                             "There is no single right answer; the reasoning is the point.",
                    ),
                    Question(
                        "critical_speed_note",
                        "Why does a low stress not answer the critical-speed problem?",
                        evidence=False,
                        hint="One or two sentences in your own words. If you are not sure, "
                             "read the critical-speed row in docs/model-review.md first.",
                    ),
                ),
            ),
            Step(
                "handoff", "7. Hand it on",
                "You have a stated support condition, a section, screening numbers "
                "with their units, and an explicit list of what is still open. That "
                "is a useful contribution to the S1 bearing/shaft work and to the "
                "T4 assembly interface, and it approves nothing.",
                (
                    Question(
                        "lead_decision",
                        "What does the structures lead need to decide or confirm?",
                        evidence=False, role="decision",
                        hint="Specific beats broad. 'Is the 8 mm journal fixed by the bearing "
                             "choice, or still open?' is a real question.",
                    ),
                    Question(
                        "next_step",
                        "What is your next small step?",
                        evidence=False, role="next_step",
                        hint="One step, 30 minutes or less.",
                    ),
                ),
            ),
        ),
        calculations=(
            Calculation(
                "I_area", "Second moment of AREA (bending)",
                ("outer_d", "inner_d"),
                lambda outer_d, inner_d: _i_section(outer_d, inner_d),
                units="m^4",
                method="I = pi*(do^4 - di^4)/64, diameters in mm converted to m. "
                       "di = 0 gives the solid-bar result pi*d^4/64.",
                version="1",
                limitations="Geometry only. Says nothing about material, strength or load. "
                            "Units are m^4 - this is NOT the kg*m^2 mass moment of inertia "
                            "used in rotor energy.",
            ),
            Calculation(
                "J_polar", "POLAR second moment of area (torsion)",
                ("outer_d", "inner_d"),
                lambda outer_d, inner_d: _j_section(outer_d, inner_d),
                units="m^4",
                method="J = pi*(do^4 - di^4)/32 = 2I, diameters in mm converted to m. "
                       "Valid for circular sections only; a non-circular section needs a "
                       "torsion constant, not a polar moment.",
                version="1",
                limitations="Geometry only, circular sections only. Not a mass property.",
            ),
            Calculation(
                "bending_sigma", "Bending stress at your chosen point",
                ("bending_moment", "y_distance", "outer_d", "inner_d"),
                lambda bending_moment, y_distance, outer_d, inner_d: sm.bending_stress_round_pa(
                    bending_moment, y_distance, outer_d, inner_d) / MPA,
                units="MPa",
                method="sigma = |M|*y/I with M in N*m, y in mm converted to m and "
                       "I = pi*(do^4 - di^4)/64. Magnitude only; one side of the section is "
                       "in tension and the other in compression. y is rejected if it falls "
                       "outside the section (y > do/2) or inside the bore (y < di/2), because "
                       "there is no material there to carry a stress.",
                version="1",
                limitations="Elastic, static, plain prismatic section, no stress "
                            "concentration, no combined torsion, no fatigue, no temperature "
                            "effect. COMPUTED from a moment you supplied; it is only as good "
                            "as that moment, and it is not compared to any allowable.",
            ),
            Calculation(
                "torsion_tau", "Torsional shear stress at the outer surface",
                ("shaft_torque", "outer_d", "inner_d"),
                lambda shaft_torque, outer_d, inner_d: sm.torsional_shear_pa(
                    shaft_torque, outer_d / 2.0, _j_section(outer_d, inner_d)) / MPA,
                units="MPa",
                method="tau = |T|*r/J at r = do/2, with T in N*m, diameters in mm and "
                       "J = pi*(do^4 - di^4)/32. For a solid shaft this equals "
                       "16*T/(pi*d^3), the relation m30_shaft.py inverts to size the shaft.",
                version="1",
                limitations="Elastic, circular section, no keyway, step, hole or other stress "
                            "riser, no combined bending, no fatigue. Comparing it to "
                            "tau_allow_shaft_Pa from config/seed.yaml would compare it to a "
                            "modelling input, not to a qualified allowable.",
            ),
            Calculation(
                "midspan_deflection", "Optional: mid-span deflection, simply supported, central load",
                ("load_n", "span", "modulus", "outer_d", "inner_d"),
                lambda load_n, span, modulus, outer_d, inner_d:
                    sm.midspan_deflection_simple_central_load_m(
                        load_n, span, modulus, _i_section(outer_d, inner_d)) * 1000.0,
                units="mm",
                method="delta = |P|*L^3/(48*E*I), P in N, L in mm converted to m, E in GPa "
                       "converted to Pa, I in m^4; result converted back to mm.",
                version="1",
                limitations="SIMPLY SUPPORTED span with a SINGLE CENTRAL load only. The 48 "
                            "becomes 192 for built-in ends and the form changes entirely for "
                            "a cantilever or an overhung rotor. If you answered 'no' to the "
                            "supports question, treat this as illustrative arithmetic and "
                            "say so. Elastic, small deflection, uniform section, no shear "
                            "deformation, E at the temperature you stated.",
            ),
        ),
    )


if __name__ == "__main__":
    raise SystemExit(run_lesson(build_lesson(), __file__))
