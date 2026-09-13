"""C3 - Draw the fuel-system blocks.  CORE first-meeting worksheet.

WHAT THIS IS
  A 30-45 minute guided activity. The deliverable is a BLOCK DIAGRAM on
  paper. This script explains what each block is for, then walks you through
  one unit conversion that is currently a genuine trap in our own documents.

HOW TO USE IT
  1. Run it once and read what it prints:   python c3_fuel_blocks.py
  2. Draw the blocks. Paper is fine.
  3. Edit the block below marked YOUR ANSWERS. Nothing else.
  4. Save, run again, hand the printed block to your lead.

WHAT THIS IS NOT
  No fuel handling of any kind today. No pump is powered, nothing is filled,
  nothing is flowed. This worksheet contains no pump, valve or fuel-control
  code and cannot drive anything.
"""

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
for _folder in (_HERE, _HERE.parent):
    if str(_folder) not in sys.path:
        sys.path.insert(0, str(_folder))
try:
    from worksheet_common import (CANDIDATE, EXAMPLE, NOT_FOUND, REPO_CHECK,
                                  UNKNOWN, Worksheet, answer, has_value)
except ImportError:
    print("Could not find worksheet_common.py.")
    print("Keep this file in its team folder next to the other worksheets,")
    print("or use the starter bundle. See workspaces/python/HOW-TO-RUN.md.")
    raise SystemExit(1)


# ===========================================================================
#  YOUR ANSWERS - this is the only part of the file you need to edit.
# ===========================================================================

DATE = UNKNOWN                 # e.g. "2026-09-17"

# 1. Your block diagram.
SKETCH = UNKNOWN               # e.g. "block diagram on paper, six blocks,
                               #       photo in the meeting folder"

# 2. Where on your diagram does somebody need to KNOW the pressure, and
#    where do they need to know the flow? Name the spots.
PRESSURE_MUST_BE_KNOWN_AT = UNKNOWN
FLOW_MUST_BE_KNOWN_AT = UNKNOWN

# 3. Three compatibility requirements nobody has answered yet. A
#    compatibility requirement is something that has to match between two
#    parts, or between a part and the fuel, before they can work together.
COMPATIBILITY_UNKNOWN_1 = UNKNOWN
COMPATIBILITY_UNKNOWN_2 = UNKNOWN
COMPATIBILITY_UNKNOWN_3 = UNKNOWN

# 4. Fuel density. Look it up and cite where. Kerosene-type fuels are usually
#    quoted somewhere between about 775 and 840 kg/m3 at 15 degrees C, and
#    which end you are at changes the answer below by several percent.
FUEL_DENSITY = answer(
    value=UNKNOWN,             # e.g. 800
    units="kg/m3",
    source=UNKNOWN,            # a datasheet or standard - name it
    uncertainty=UNKNOWN,       # e.g. "varies with temperature and batch"
)

# 5. Optional stretch: one candidate pump you found, and whether the vendor
#    restricts it to their own engines.
CANDIDATE_PUMP = answer(
    value=UNKNOWN,             # e.g. "vendor X model Y"
    source=UNKNOWN,
    uncertainty=UNKNOWN,       # e.g. "page says 'for our engines only'"
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

BURN_NOTE_KG_H = 22.9          # DP-2 note's full-power fuel flow
BURN_SCREEN_KG_H = 23.72       # what the repository screen reproduces
ALLOWANCE_KG_H = 29.0          # DP-2's sizing allowance - a mass flow


def lesson(ws):
    ws.heading("what a fuel system is, in plain language")
    ws.say("A fuel system is plumbing with opinions. It takes liquid out of a "
           "tank and delivers a controlled amount to the right place at the "
           "right pressure, and it has to keep doing that while the engine "
           "changes its mind about how much it wants.")
    ws.say("Ours is short: a tank, a filter so grit does not reach anything "
           "precise, a pump with something driving it, a valve that can shut "
           "the fuel off completely, and a manifold that splits the flow "
           "between the tubes that spray it into the combustor.")
    ws.say("The two things that make it interesting are that the pump has to "
           "push against the pressure already inside the combustor, and that "
           "it has to be accurate at low flow as well as high. An engine that "
           "idles at less than half speed spends most of its life near the "
           "bottom of the pump's range, which is exactly where cheap pumps "
           "are worst.")

    ws.heading("the words you need")
    ws.terms([
        ("mass flow and volume flow",
         "Kilograms per hour and litres per hour. Connected by density, and "
         "NOT interchangeable. Confusing them is the trap in this task."),
        ("delivery pressure",
         "What the pump has to produce. It is not one number - it is combustor "
         "pressure plus everything the fuel has to push through on the way: "
         "filter, line, fittings, injector."),
        ("shutoff",
         "A valve that stops fuel completely, independently of whether the "
         "pump is doing what it was told. Safety cares about this one more "
         "than about any other block on your diagram."),
        ("compatibility",
         "Whether two parts actually work together: this pump with this fuel, "
         "this fitting with this thread, this seal with this liquid. A vendor "
         "who restricts a pump to their own engines is telling you the "
         "compatibility question has not been answered for ours."),
        ("allowance",
         "A deliberately generous number used to size hardware so that being "
         "wrong is survivable. Not a prediction."),
    ])

    ws.heading("the trap in this task")
    ws.legend()
    ws.given("full-power fuel flow, DP-2 note", BURN_NOTE_KG_H, "kg/h", CANDIDATE)
    ws.given("full-power fuel flow, repository screen", BURN_SCREEN_KG_H,
             "kg/h", REPO_CHECK, "docs/project/dp2-review.md")
    ws.given("sizing allowance DP-2 asks for", ALLOWANCE_KG_H, "kg/h",
             CANDIDATE, "a MASS flow - read the units carefully")
    ws.blank()
    ws.say("DP-2 contains the phrase 'Fuel flow 22.9 kg/h, approximately 29 "
           "L/h' and, separately, the instruction 'size the fuel system for 29 "
           "kg/h'. Those two 29s are different quantities that happen to share "
           "a digit, and if you size a pump for 29 litres per hour because you "
           "half-remembered the number, you will be about 20 percent short.")
    ws.example([
        "Back out the density DP-2 is implying from its own pair of numbers:",
        "",
        "  22.9 kg/h divided by 29 L/h            = 0.79 kg per litre",
        "                                         = about 790 kg/m3",
        "",
        "That sits inside the usual range for kerosene-type fuel, so the pair",
        "is self-consistent. Now use the same density on the ALLOWANCE:",
        "",
        "  29 kg/h / 0.790 kg/L                   = 36.7 L/h",
        "  36.7 L/h / 60                          = 0.61 L/min",
        "",
        "So the volume the pump must be able to deliver is about 36.7 L/h,",
        "not 29 L/h. Same word, same digits, different quantity, and a fifth",
        "of the pump's capacity riding on whether anyone noticed.",
        "",
        "The 790 kg/m3 above is a deduction from DP-2's own arithmetic, not a",
        "stated fuel property. Look up a real density with a real source.",
    ])

    ws.heading("one more thing to keep straight")
    ws.say("The DP-2 review makes a point that is easy to miss and expensive "
           "to get wrong: keep the air budget and the fuel budget apart. A "
           "pressure figure that describes liquid fuel moving through pipes "
           "tells you nothing about the air pressure available to a vaporizer "
           "passage. They are different fluids doing different jobs in "
           "different places. If you find yourself using one to size the "
           "other, stop and ask your lead.")


def your_calculation(ws):
    ws.heading("now do it with a density you can cite")
    volume_allow = ws.compute(
        "volume flow for the 29 kg/h allowance",
        lambda density: ALLOWANCE_KG_H / (density / 1000.0),
        {"fuel density (kg/m3)": FUEL_DENSITY},
        units="L/h",
        comment="Dividing by density/1000 converts kg/m3 into kg per litre.",
    )
    if volume_allow is not None:
        ws.compute(
            "the same thing per minute",
            lambda v: v / 60.0,
            {"volume flow (L/h)": volume_allow},
            units="L/min",
            comment="This is the number to compare against a pump's published "
                    "flow curve.",
        )
    ws.compute(
        "volume flow at the repository screen's actual burn rate",
        lambda density: BURN_SCREEN_KG_H / (density / 1000.0),
        {"fuel density (kg/m3)": FUEL_DENSITY},
        units="L/h",
        comment="The difference between this and the allowance above is the "
                "margin you are deliberately buying. Say in your notes that "
                "it is margin, not a prediction.",
    )
    ws.compute(
        "how much margin the allowance represents",
        lambda: 100.0 * (ALLOWANCE_KG_H - BURN_SCREEN_KG_H) / BURN_SCREEN_KG_H,
        {},
        units="percent",
        comment="This one needs nothing from you - it is the same number in "
                "mass terms, and it does not depend on density at all. Worth "
                "noticing why.",
    )


def main():
    ws = Worksheet(
        code="C3",
        title="Draw the fuel-system blocks",
        card="workspaces/combustion-systems/C3-fuel.md",
        review_role="Combustion & Systems lead",
    )
    ws.header(safety_line="Desk work only today. No fuel handling, no filling, "
                          "no powered pump, no flow test of any kind.")
    lesson(ws)
    your_calculation(ws)

    ws.heading("what to put on the diagram")
    ws.bullets([
        "Tank, filter, pump and whatever drives it, shutoff valve, manifold, "
        "and the tubes that feed the combustor.",
        "An arrow for the fuel, from tank to combustor.",
        "A mark wherever somebody will need to know the pressure.",
        "A mark wherever somebody will need to know the flow.",
        "A note of what happens if the pump stops but the valve does not.",
    ])
    ws.say("Not today: choosing a pump, sizing an orifice, deciding a system "
           "pressure drop, or handling fuel. The DP-2 review notes that one "
           "commonly cited pump is explicitly restricted by its vendor to "
           "their own engines, so compatibility is an open procurement "
           "question rather than a solved one.")

    ws.record("fuel density used", FUEL_DENSITY)
    ws.record("candidate pump found", CANDIDATE_PUMP)

    ws.submission(date=DATE, learned=WHAT_I_LEARNED, unknown=STILL_UNKNOWN,
                  question=QUESTION_FOR_LEAD, next_step=NEXT_SMALL_STEP)
    ws.done_when([
        ("a block diagram exists and is described", SKETCH),
        ("where pressure must be known", PRESSURE_MUST_BE_KNOWN_AT),
        ("where flow must be known", FLOW_MUST_BE_KNOWN_AT),
        ("compatibility unknown 1", COMPATIBILITY_UNKNOWN_1),
        ("compatibility unknown 2", COMPATIBILITY_UNKNOWN_2),
        ("compatibility unknown 3", COMPATIBILITY_UNKNOWN_3),
        ("fuel density with a source", FUEL_DENSITY),
        ("one question for the lead", QUESTION_FOR_LEAD),
    ])
    ws.finish()


if __name__ == "__main__":
    main()
