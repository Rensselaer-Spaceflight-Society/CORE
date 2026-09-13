"""S2 - Explain an inlet drawing and pressure terms.  CORE first-meeting worksheet.

WHAT THIS IS
  A 30-45 minute guided activity. The deliverable is a LABELLED SKETCH of the
  engine inlet plus a short list of what is missing. This script teaches the
  three ideas the sketch needs - area, speed, Mach number - and shows you why
  one number in the old inlet paperwork is not what it was labelled as.

HOW TO USE IT
  1. Run it once and read what it prints:   python s2_inlet_flow.py
  2. Sketch the bellmouth. Paper is fine.
  3. Edit the block below marked YOUR ANSWERS. Nothing else.
  4. Save, run again, hand the printed block to your lead.

WHAT THIS IS NOT
  It does not re-cut CAD, optimise a lip radius, or clear any printed part for
  running. It does not import the engine model.
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
SKETCH = UNKNOWN               # e.g. "bellmouth sketch on paper, throat and
                               #       inducer marked, photo in meeting folder"

# 2. Did you find an actual inlet drawing or script in this repository?
#    Look, then answer honestly. The DP-2 review notes that several files the
#    old notes refer to are not in the current checkout, so NOT_FOUND is a
#    likely and completely acceptable answer. Say where you looked.
INLET_DRAWING = answer(
    value=UNKNOWN,             # e.g. NOT_FOUND
    source=UNKNOWN,            # e.g. "searched repo for 'inlet' and 'bellmouth'"
    uncertainty=UNKNOWN,
)

# 3. A Mach number to try in the throat. Pick one, see what diameter it
#    implies, then try another. This is iteration by hand, and it is how
#    engineers actually use a formula like this.
TRY_THIS_MACH_NUMBER = answer(
    value=UNKNOWN,             # e.g. 0.24
    units="(no units)",
    source="a number I chose to try",
    basis=EXAMPLE,
)

# 4. In your own words: why can the static pressure in an ideal throat be
#    lower than ambient without any total pressure having been lost?
WHY_STATIC_DROPS_WITHOUT_LOSS = UNKNOWN

# 5. What is missing before anybody can size this part for real? List up to
#    three things.
MISSING_INPUT_1 = UNKNOWN
MISSING_INPUT_2 = UNKNOWN
MISSING_INPUT_3 = UNKNOWN

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

GAMMA = 1.4                    # ratio of specific heats for air
R_AIR = 287.05                 # J/(kg K)
T0 = 288.15                    # K,  ambient total temperature
P0 = 101325.0                  # Pa, ambient total pressure
MDOT = 0.30                    # kg/s, DP-2 candidate air flow
INDUCER_MM = 57.04             # mm, DP-2 candidate compressor inducer diameter
OLD_THROAT_MM = 102.0          # mm, the diameter the existing inlet was drawn at
OLD_MASS_FLOW = 0.50           # kg/s, the flow the existing inlet was drawn for


def static_over_total(mach):
    return (1.0 + 0.5 * (GAMMA - 1.0) * mach * mach) ** (-GAMMA / (GAMMA - 1.0))


def throat_diameter_mm(mach, mdot):
    """Diameter that passes mdot at this Mach number, from ambient air."""
    temperature = T0 / (1.0 + 0.5 * (GAMMA - 1.0) * mach * mach)
    speed_of_sound = math.sqrt(GAMMA * R_AIR * temperature)
    velocity = mach * speed_of_sound
    pressure = P0 * static_over_total(mach)
    density = pressure / (R_AIR * temperature)
    area = mdot / (density * velocity)
    return 1000.0 * math.sqrt(4.0 * area / math.pi)


def lesson(ws):
    ws.heading("what the inlet does, in plain language")
    ws.say("Point a funnel at the wind and you collect more air than the pipe "
           "behind it would on its own. Our inlet is a funnel - a bellmouth - "
           "whose job is to feed the compressor a smooth, even, undisturbed "
           "stream of air.")
    ws.say("It sounds like the easiest part on the engine and in a sense it "
           "is: nothing in it moves, nothing in it gets hot, and it can "
           "probably be printed for a first test. But if the air arrives at "
           "the compressor lopsided or already churned up, the compressor "
           "cannot make the pressure ratio anybody assumed, and everything "
           "downstream inherits the problem.")

    ws.heading("the words you need")
    ws.terms([
        ("static pressure",
         "What a small hole in the wall of the duct feels, right there."),
        ("total pressure",
         "What you would measure if you brought the air smoothly to a complete "
         "stop. Static plus the extra from its motion."),
        ("Mach number, M",
         "Speed divided by the speed of sound, right there. No units. The "
         "formula is M = V / a, where a = sqrt(gamma * R * T). Note that it "
         "is divided by a SPEED, not by an area - see the trap below."),
        ("throat",
         "The narrowest point. Air goes fastest there, so its static pressure "
         "is lowest there."),
        ("pressure recovery",
         "How much TOTAL pressure survives the inlet, as a fraction. A perfect "
         "inlet has a recovery of 1.0. It is a measure of loss, and it is not "
         "the same thing as the static-to-total ratio at the throat."),
    ])

    ws.heading("the trap in this task, and it is a good one")
    ws.say("The old inlet paperwork records a number, 0.9852, and calls it "
           "pressure recovery. It is not. It is the ratio of static to total "
           "pressure at the throat, which is simply what happens when air "
           "speeds up. A perfect, frictionless, lossless bellmouth has that "
           "ratio too. It has lost nothing.")
    ws.say("You can see this from the formula, which comes out of "
           "compressible flow and needs no measurement at all. Static over "
           "total = (1 + 0.2 * M^2) raised to the power -3.5.")
    ws.example([
        "At M = 0.147, the Mach number the old part was drawn for:",
        "",
        "  1 + 0.2 * 0.147^2        = 1.004322",
        "  1.004322 ^ -3.5          = 0.9850",
        "",
        "So 0.985 falls straight out of the Mach number. No losses were",
        "involved in producing it. Calling it a recovery says the inlet is",
        "1.5 percent lossy, which we have not measured and do not know.",
        "",
        "Real recovery needs a friction and lip-separation model, or a test.",
        "Finding out that a documented number means something different from",
        "its label is one of the most useful things anybody does on an",
        "engineering project, and it is what your task card is pointing at.",
    ])
    ws.say("Your task card also mentions that the old analysis divides "
           "velocity by area instead of by the speed of sound when it "
           "calculates Mach number, even though the plotted result is right. "
           "Before you go and fix that, find the file. The DP-2 review is "
           "clear that several files the old notes refer to are not in the "
           "current checkout, and that you should compare actual versions "
           "before assigning an alleged bug. Today's job is to look, and to "
           "record what you find, including NOT FOUND.")

    ws.heading("the numbers the project already has")
    ws.legend()
    ws.given("ambient total temperature", T0, "K", CANDIDATE)
    ws.given("ambient total pressure", P0 / 1000.0, "kPa", CANDIDATE)
    ws.given("speed of sound at that temperature",
             math.sqrt(GAMMA * R_AIR * T0), "m/s", REPO_CHECK,
             "sqrt(1.4 * 287.05 * 288.15)")
    ws.given("DP-2 candidate air flow", MDOT, "kg/s", CANDIDATE)
    ws.given("DP-2 candidate compressor inducer diameter", INDUCER_MM, "mm",
             CANDIDATE)
    ws.given("diameter the existing inlet was drawn at", OLD_THROAT_MM, "mm",
             EXAMPLE, "from the old inlet record; the drawing itself may not "
                      "be in this repository")
    ws.given("air flow the existing inlet was drawn for", OLD_MASS_FLOW,
             "kg/s", EXAMPLE)
    ws.blank()
    ws.say("Two flows, one part. The existing inlet was drawn for 0.50 kg/s "
           "and DP-2 proposes 0.30 kg/s. Less air through the same hole means "
           "slower air, which sounds harmless, but the throat should really be "
           "matched to the compressor inducer, because that is where the true "
           "minimum area is. Both facts point the same way: the part needs "
           "re-sizing. Not by you, not today.")


def your_calculation(ws):
    ws.heading("now try a Mach number and see what diameter it needs")
    ws.say("Pick a Mach number in the answers block, run this, and look at the "
           "diameter it gives. Too big? Try a higher Mach number. Too small? "
           "Lower. Three or four goes and you will have a feel for it, which "
           "is worth more than a formula you did not wrestle with.")

    mach = ws.compute(
        "static pressure divided by total pressure at your Mach number",
        lambda m: static_over_total(m),
        {"Mach number you chose": TRY_THIS_MACH_NUMBER},
        comment="Remember what this is: a consequence of speed, not a loss.",
    )
    diameter = ws.compute(
        "throat diameter that passes 0.30 kg/s at your Mach number",
        lambda m: throat_diameter_mm(m, MDOT),
        {"Mach number you chose": TRY_THIS_MACH_NUMBER},
        units="mm",
        comment="Compare this with the 57.04 mm inducer. A throat far larger "
                "than the inducer is not really the throat at all.",
    )
    if diameter is not None:
        ws.compute(
            "your throat diameter divided by the inducer diameter",
            lambda d: d / INDUCER_MM,
            {"throat diameter (mm)": diameter},
            units="times",
            comment="Around 1.1 or so is the sort of ratio a matched bellmouth "
                    "has. Well above that and the real minimum area is the "
                    "compressor, not your throat.",
        )
    ws.compute(
        "for comparison, the diameter the OLD flow would need at your Mach number",
        lambda m: throat_diameter_mm(m, OLD_MASS_FLOW),
        {"Mach number you chose": TRY_THIS_MACH_NUMBER},
        units="mm",
        comment="Same Mach number, more air, bigger hole. This is why a "
                "drawing made for one mass flow cannot be reused at another "
                "without re-sizing.",
    )


def main():
    ws = Worksheet(
        code="S2",
        title="Explain an inlet drawing and pressure terms",
        card="workspaces/structures/S2-inlet.md",
        review_role="Structures lead",
    )
    ws.header()
    lesson(ws)
    your_calculation(ws)

    ws.heading("what finishing looks like")
    ws.bullets([
        "One labelled sketch: the bellmouth, the throat, the inducer behind "
        "it, with area, speed and Mach marked and M = V / a written on it.",
        "One or two sentences on why an ideal throat can have low static "
        "pressure and still have lost nothing.",
        "A short list of what is missing before this part can be sized for "
        "real.",
        "Whether the old inlet drawing or script exists here, and where you "
        "looked.",
    ])
    ws.say("Not today: re-cutting CAD, optimising the lip radius, choosing "
           "between printing and machining, or declaring any part cleared to "
           "run. And do not fix an equation in a file you have not opened.")

    ws.record("inlet drawing or script found", INLET_DRAWING)
    ws.record("Mach number tried", TRY_THIS_MACH_NUMBER)

    ws.submission(date=DATE, learned=WHAT_I_LEARNED, unknown=STILL_UNKNOWN,
                  question=QUESTION_FOR_LEAD, next_step=NEXT_SMALL_STEP)
    ws.done_when([
        ("a labelled sketch exists and is described", SKETCH),
        ("whether the old inlet file exists, and where you looked",
         INLET_DRAWING),
        ("a Mach number you tried", TRY_THIS_MACH_NUMBER),
        ("why static pressure can drop with no loss",
         WHY_STATIC_DROPS_WITHOUT_LOSS),
        ("missing input 1", MISSING_INPUT_1),
        ("missing input 2", MISSING_INPUT_2),
        ("one question for the lead", QUESTION_FOR_LEAD),
    ])
    ws.finish()


if __name__ == "__main__":
    main()
