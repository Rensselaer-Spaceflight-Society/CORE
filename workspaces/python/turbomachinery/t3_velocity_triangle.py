"""T3 - Learn one turbine velocity triangle.  CORE first-meeting worksheet.

WHAT THIS IS
  A 30-45 minute guided activity. The deliverable is a LABELLED SKETCH of one
  velocity triangle. This script explains what a velocity triangle is, then
  walks you through the three numbers that fix the one on your page.

HOW TO USE IT
  1. Run it once and read what it prints:   python t3_velocity_triangle.py
  2. Ask your lead to draw the triangle with you once. Then draw it yourself.
  3. Edit the block below marked YOUR ANSWERS. Nothing else.
  4. Save, run again, hand the printed block to your lead.

WHAT THIS IS NOT
  Not a stage design. No blade twist, no throat sizing, no choking verdict,
  no material choice. Those are later, mentored, reviewed work.
"""

import math
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
for _folder in (_HERE, _HERE.parent):
    if str(_folder) not in sys.path:
        sys.path.insert(0, str(_folder))
try:
    from worksheet_common import (CANDIDATE, EXAMPLE, NOT_FOUND, REPO_CHECK,
                                  UNKNOWN, Worksheet, answer)
except ImportError:
    print("Could not find worksheet_common.py.")
    print("Keep this file in its team folder next to the other worksheets,")
    print("or use the starter bundle. See workspaces/python/HOW-TO-RUN.md.")
    raise SystemExit(1)


# ===========================================================================
#  YOUR ANSWERS - this is the only part of the file you need to edit.
# ===========================================================================

DATE = UNKNOWN                 # e.g. "2026-09-17"

# 1. Your sketch.
SKETCH = UNKNOWN               # e.g. "paper triangle, photo in meeting folder,
                               #       U, V and W labelled with units"

# 2. The three velocities, in your own words, with units. Say what each one
#    means physically - not the textbook definition, yours.
WHAT_IS_U = UNKNOWN            # e.g. "how fast the blade itself is moving, m/s"
WHAT_IS_V = UNKNOWN            # e.g. "..."
WHAT_IS_W = UNKNOWN            # e.g. "..."

# 3. In one or two sentences: what does the work the turbine extracts get
#    used for? (There is a very short answer and it is the whole reason the
#    turbine exists.)
WHAT_TURBINE_WORK_SUPPLIES = UNKNOWN

# 4. The loading coefficient you are using for the sketch. DP-2 proposes 1.0.
#    Use that unless your lead tells you otherwise. It is a candidate, not a
#    decision, and choosing it properly is a later assignment.
LOADING_COEFFICIENT_PSI = answer(
    value=1.0,
    units="(no units)",
    source="docs/project/dp2-review.md; DP-2 proposes psi = 1.0",
    uncertainty="candidate value, not selected by analysis",
    basis=CANDIDATE,
)

# 5. The flow coefficient. DP-2 proposes 0.9, deliberately away from the
#    usual efficiency optimum in order to shorten the blade.
FLOW_COEFFICIENT_PHI = answer(
    value=0.9,
    units="(no units)",
    source="docs/project/dp2-review.md; DP-2 proposes phi = 0.9",
    uncertainty="candidate value; the trade against efficiency is not settled",
    basis=CANDIDATE,
)

# 6. Your writing.
WHAT_I_LEARNED = [
    UNKNOWN,
    UNKNOWN,
    UNKNOWN,
]
STILL_UNKNOWN = UNKNOWN
QUESTION_FOR_LEAD = UNKNOWN
NEXT_SMALL_STEP = UNKNOWN

# ===========================================================================
#  END OF YOUR ANSWERS.
# ===========================================================================

DELTA_H0 = 60300.0             # J/kg  - DP-2 candidate stage work
SHAFT_RPM = 66000.0            # rpm   - DP-2 candidate shaft speed
ANNULUS_TIP_MM = 88.2          # mm    - DP-2 candidate turbine tip diameter
ANNULUS_HUB_MM = 53.9          # mm    - DP-2 candidate turbine hub diameter
OMEGA = SHAFT_RPM * 2.0 * math.pi / 60.0


def lesson(ws):
    ws.heading("what a turbine does, in plain language")
    ws.say("A windmill takes energy out of moving air and turns a shaft. Our "
           "turbine is a windmill in a hurricane of hot gas, about 25 mm "
           "across, spinning a thousand times a second.")
    ws.say("Here is the part that surprises people. The turbine is not there "
           "to make thrust. It is there to pay the compressor. Every joule the "
           "compressor needs to squeeze air has to come out of the hot gas "
           "first, and the turbine is the only thing collecting it. Thrust is "
           "made by whatever is left over, at the nozzle.")
    ws.say("That is why this task is load-bearing. If the turbine cannot "
           "collect enough, the shaft slows down, the compressor delivers "
           "less, the turbine collects even less, and the engine stops. Nobody "
           "has proved our turbine can collect enough. That proof is the "
           "semester.")

    ws.heading("the velocity triangle, using a train")
    ws.say("Stand on a train moving at 30 m/s and walk forward at 2 m/s. "
           "Someone on the platform sees you moving at 32 m/s. You feel like "
           "you are moving at 2 m/s. Both are true. They are just measured "
           "from different places.")
    ws.say("Gas arriving at a turbine blade is the same. It has one speed "
           "measured from the engine casing, and a different speed measured "
           "from the blade, because the blade is running away underneath it. "
           "A velocity triangle is the picture that connects the two, and it "
           "is a triangle because velocities add like arrows.")
    ws.terms([
        ("U, blade speed",
         "How fast the blade itself is travelling round, in m/s. It is just "
         "rotation speed times radius. Bigger wheel or faster shaft means "
         "bigger U."),
        ("V, absolute velocity",
         "The gas speed as measured from the engine, standing still. This is "
         "what the stationary guide vanes upstream control."),
        ("W, relative velocity",
         "The gas speed as measured from the blade, riding along with it. This "
         "is what the blade actually has to deal with, and it is what sets the "
         "blade's shape."),
        ("the rule",
         "V = U + W, added as arrows, not as numbers. Draw it and the triangle "
         "appears. Add them as plain numbers and you will get a wrong answer "
         "that looks reasonable, which is worse."),
        ("loading coefficient psi",
         "Stage work divided by U squared. It says how hard you are asking one "
         "row of blades to work. Around 1 is a normal, comfortable ask; much "
         "more than 2 and you are demanding a lot of turning."),
        ("flow coefficient phi",
         "Axial gas speed divided by U. Low phi means a long thin blade; high "
         "phi means a short stubby one. DP-2 picks 0.9, which is higher than "
         "the usual efficiency optimum, on purpose, to keep the blade short "
         "and its root stress down."),
    ])

    ws.heading("the numbers the project already has")
    ws.legend()
    ws.given("stage work per kg of gas", DELTA_H0 / 1000.0, "kJ/kg", CANDIDATE)
    ws.given("shaft speed", SHAFT_RPM, "rpm", CANDIDATE)
    ws.given("shaft speed in rad/s", OMEGA, "rad/s", CANDIDATE,
             "66000 * 2 * pi / 60")
    ws.given("turbine tip diameter", ANNULUS_TIP_MM, "mm", CANDIDATE)
    ws.given("turbine hub diameter", ANNULUS_HUB_MM, "mm", CANDIDATE)
    ws.given("turbine annulus area", math.pi / 4.0
             * (ANNULUS_TIP_MM ** 2 - ANNULUS_HUB_MM ** 2), "mm2", REPO_CHECK,
             "docs/project/checks/dp2_screen.py reproduces 3828 mm2")
    ws.blank()

    ws.heading("a worked example, so the arithmetic is not a mystery")
    ws.say("If you set the loading coefficient psi to exactly 1, then by "
           "definition stage work equals U squared, so U is just the square "
           "root of the stage work. That is the whole of the optional stretch "
           "on your task card, and it is worth doing by hand once.")
    ws.example([
        "  psi = 1.0, stage work = 60300 J/kg",
        "  U = sqrt(60300)                      = 245.6 m/s",
        "",
        "Blade speed is rotation speed times radius, so the radius that gives",
        "that blade speed at 66,000 rpm is:",
        "  omega  = 66000 * 2 * pi / 60         = 6911.5 rad/s",
        "  radius = 245.6 / 6911.5              = 0.03553 m  = 35.5 mm",
        "  so the mean diameter is about         71.1 mm",
        "",
        "Now compare that with the annulus DP-2 proposes: 88.2 mm at the tip",
        "and 53.9 mm at the hub. The middle of those is (88.2 + 53.9) / 2,",
        "which is 71.05 mm. The two agree to better than a tenth of a",
        "millimetre.",
        "",
        "That agreement is not a coincidence and it is not proof the design is",
        "good. It just means DP-2's annulus and DP-2's loading coefficient are",
        "telling the same story. Finding that out for yourself, in two lines",
        "of arithmetic, is exactly the skill this task is teaching.",
    ])


def your_calculation(ws):
    ws.heading("now do it with your own coefficients")
    blade_speed = ws.compute(
        "mean blade speed U",
        lambda psi: math.sqrt(DELTA_H0 / psi),
        {"loading coefficient psi": LOADING_COEFFICIENT_PSI},
        units="m/s",
        comment="From psi = stage work / U^2, rearranged.",
    )
    if blade_speed is not None:
        mean_d = ws.compute(
            "mean diameter that gives that blade speed at 66,000 rpm",
            lambda u: 2000.0 * u / OMEGA,
            {"mean blade speed (m/s)": blade_speed},
            units="mm",
        )
        if mean_d is not None:
            dp2_mean = (ANNULUS_TIP_MM + ANNULUS_HUB_MM) / 2.0
            ws.compute(
                "difference from the DP-2 annulus mean diameter",
                lambda d: d - dp2_mean,
                {"your mean diameter (mm)": mean_d},
                units="mm",
                comment="DP-2's annulus mean diameter is {0:.2f} mm. A small "
                        "difference means your coefficient and DP-2's annulus "
                        "are consistent. A large one means one of them has "
                        "moved, and the lead needs to know which."
                        .format(dp2_mean),
            )
        ws.compute(
            "axial gas velocity Cx",
            lambda u, phi: u * phi,
            {"mean blade speed (m/s)": blade_speed,
             "flow coefficient phi": FLOW_COEFFICIENT_PHI},
            units="m/s",
            comment="This is the arrow that points straight down the engine on "
                    "your sketch. The other arrow, the swirl, is what the "
                    "guide vanes upstream have to create.",
        )
    ws.compute(
        "tip blade speed divided by hub blade speed",
        lambda tip, hub: tip / hub,
        {"tip diameter (mm)": ANNULUS_TIP_MM, "hub diameter (mm)": ANNULUS_HUB_MM},
        comment="Blade speed is proportional to radius, so the tip of this "
                "blade is moving over one and a half times as fast as its "
                "root. One triangle cannot describe both ends. That is why a "
                "real blade is twisted, and why it is harder to machine. Note "
                "it as a question; do not try to design the twist today.",
    )


def main():
    ws = Worksheet(
        code="T3",
        title="Learn one turbine velocity triangle",
        card="workspaces/turbomachinery/T3-turbine.md",
        review_role="Turbomachinery lead",
    )
    ws.header()
    lesson(ws)
    your_calculation(ws)

    ws.heading("what finishing looks like")
    ws.bullets([
        "One triangle on paper with U, V and W labelled, and units on each.",
        "One or two sentences saying what turbine work is for.",
        "One question. 'Why is phi 0.9 and not the optimum?' is an excellent "
        "one to ask.",
    ])
    ws.say("Not today: designing the stage, sizing the nozzle guide vane "
           "throat, deciding whether anything chokes, or picking a material. "
           "The DP-2 review is explicit that overall turbine pressure ratio "
           "does not tell you whether a local passage chokes, and that the "
           "material question needs metal-temperature and life evidence we do "
           "not have. Your sketch is not an input to any of that yet.")

    ws.record("loading coefficient psi used", LOADING_COEFFICIENT_PSI)
    ws.record("flow coefficient phi used", FLOW_COEFFICIENT_PHI)

    ws.submission(date=DATE, learned=WHAT_I_LEARNED, unknown=STILL_UNKNOWN,
                  question=QUESTION_FOR_LEAD, next_step=NEXT_SMALL_STEP)
    ws.done_when([
        ("a labelled triangle exists and is described", SKETCH),
        ("what U is, in your words, with units", WHAT_IS_U),
        ("what V is, in your words, with units", WHAT_IS_V),
        ("what W is, in your words, with units", WHAT_IS_W),
        ("what turbine work supplies", WHAT_TURBINE_WORK_SUPPLIES),
        ("one question for the lead", QUESTION_FOR_LEAD),
    ])
    ws.finish()


if __name__ == "__main__":
    main()
