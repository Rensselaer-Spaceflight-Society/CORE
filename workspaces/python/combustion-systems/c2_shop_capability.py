"""C2 - Find out what the shop can actually do.  CORE first-meeting worksheet.

WHAT THIS IS
  A 30-45 minute guided activity, entirely at a desk. You will write the
  questions that have to be answered before anybody can make a combustor
  liner, and you will draft the order the job would happen in.

HOW TO USE IT
  1. Run it once and read what it prints:   python c2_shop_capability.py
  2. Edit the block below marked YOUR ANSWERS. Nothing else.
  3. Save, run again, hand the printed block to your lead.

WHAT THIS IS NOT
  No shop entry, no machine, no forming, no welding, no cutting today. This
  worksheet cannot authorise any of those and neither can a filled card. The
  normal shop training and access rules apply and your lead arranges them.
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

# 1. Five questions, one per process. Write the question you would actually
#    ask a shop technician - specific enough that the answer is useful.
#    "Can you roll sheet?" is weak. "What is the thinnest and widest sheet
#    the roll will take, and what is the smallest diameter it can form?" is
#    a question that gets you a usable answer.
QUESTION_ROLLING = UNKNOWN
QUESTION_DRILLING = UNKNOWN
QUESTION_WELDING = UNKNOWN
QUESTION_TOOLING = UNKNOWN
QUESTION_INSPECTION = UNKNOWN

# 2. Equipment you already know the shop has. Only list what you are sure
#    about. Everything else goes in the missing list.
KNOWN_EQUIPMENT = [
    UNKNOWN,
    UNKNOWN,
]

# 3. What you do not know and could not find out from a desk.
MISSING_INFORMATION = [
    UNKNOWN,
    UNKNOWN,
]

# 4. How shop access and training are actually confirmed, according to your
#    LEAD - not according to any older document. Old task cards carry dates
#    and rules that may no longer hold, and the DP-2 review says so.
ACCESS_AND_TRAINING = answer(
    value=UNKNOWN,             # what the lead told you
    source=UNKNOWN,            # who told you, and when
    uncertainty=UNKNOWN,
)

# 5. A paper sequence for a NON-RUNNING mock-up liner: the order the job
#    would happen in. Numbered steps, plain language, one action each. Six to
#    ten steps is plenty. This is a draft for the lead, not a work order.
PAPER_SEQUENCE = [
    UNKNOWN,
    UNKNOWN,
    UNKNOWN,
]

# 6. The mock-up you are sizing the arithmetic around. These are numbers YOU
#    pick for the exercise; no liner dimension has been decided.
SKETCH_LINER_OUTER_DIAMETER_MM = answer(
    value=UNKNOWN,             # e.g. 120
    units="mm",
    source="my own sketch, not a project value",
    basis=EXAMPLE,
)
SKETCH_WALL_THICKNESS_MM = answer(
    value=UNKNOWN,             # e.g. 1.0
    units="mm",
    source="my own sketch, not a project value",
    basis=EXAMPLE,
)
SKETCH_HOLE_COUNT = answer(
    value=UNKNOWN,             # e.g. 110
    units="holes",
    source="my own sketch, not a project value",
    basis=EXAMPLE,
)
MINUTES_PER_HOLE = answer(
    value=UNKNOWN,             # e.g. 1.5 - ask somebody who has done it
    units="minutes",
    source=UNKNOWN,
    uncertainty=UNKNOWN,
)

# 7. Your writing.
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


def lesson(ws):
    ws.heading("why this task exists")
    ws.say("A design that cannot be built is not a design. It is a picture. "
           "Plenty of student engine projects have produced a beautiful CAD "
           "model of a liner that nobody could roll, drill or weld with the "
           "equipment actually in the building.")
    ws.say("The combustor liner is a thin metal tube with a lot of carefully "
           "placed holes in it. Every one of those things - the thinness, the "
           "rolling, the holes, the joining - is a question for whoever runs "
           "the machines. Your job today is to ask the questions properly, "
           "before the drawing is finished rather than after.")
    ws.say("Nothing about this is hands-on today. You are not going into the "
           "shop, you are not touching a machine, and you are not taking a "
           "quiz off your own back. You are writing the list.")

    ws.heading("the words you need")
    ws.terms([
        ("gauge",
         "How thick the sheet is. Often given as a gauge number rather than "
         "millimetres, and the numbering runs backwards - a bigger gauge "
         "number is thinner metal. Always convert to mm and say so."),
        ("rolling",
         "Bending flat sheet into a cylinder by feeding it between rollers. "
         "Every roll has a minimum diameter and a maximum thickness it can "
         "manage, and thin stainless is fussy."),
        ("TIG welding",
         "Joining with a tungsten electrode and a shielding gas. Precise, and "
         "controllable enough for thin sheet - but the heat makes thin metal "
         "move, which is why the order of the tacks matters so much."),
        ("fixture",
         "A jig that holds the work in exactly the right place, so that a "
         "hundred holes end up where the drawing says and not where the hand "
         "drifted. Usually the fixture is more work than the part."),
        ("traveller",
         "A numbered list of steps that goes with the part through the shop. "
         "Each step gets ticked off. It is the difference between a plan and "
         "a hope."),
    ])

    ws.heading("two small numbers that make the job real")
    ws.say("You do not need the finished liner design to feel the shape of "
           "this job. Two pieces of arithmetic will do it.")
    ws.example([
        "FLAT BLANK LENGTH. To roll a tube you start with a flat strip. How",
        "long? Not the outside circumference and not the inside one - the",
        "metal stretches on the outside of the bend and squashes on the",
        "inside, and the length that stays put is roughly the middle of the",
        "wall.",
        "",
        "  a 120 mm outside diameter tube in 1.0 mm sheet:",
        "    middle-of-wall diameter = 120 - 1.0        = 119.0 mm",
        "    flat length = pi * 119.0                   = 373.8 mm",
        "",
        "  Using the outside diameter instead would give 377.0 mm - about",
        "  3 mm too long, which on a butt joint is a visible, annoying gap.",
        "",
        "HOLE TIME. Say the liner has 110 holes and each takes a minute and",
        "a half to set up and drill:",
        "",
        "    110 * 1.5 minutes                          = 165 minutes",
        "                                               = 2.8 hours",
        "",
        "  That is one person for the better part of a shop session, for one",
        "  part, if nothing goes wrong. It is why a drilling fixture is worth",
        "  building and why hole count is a schedule question and not just a",
        "  drawing detail.",
        "",
        "Every number in this example is invented. Use your own.",
    ])


def your_calculation(ws):
    ws.heading("now do it for the mock-up you are imagining")
    ws.compute(
        "flat blank length for your tube",
        lambda outer, wall: math.pi * (outer - wall),
        {"liner outer diameter (mm)": SKETCH_LINER_OUTER_DIAMETER_MM,
         "wall thickness (mm)": SKETCH_WALL_THICKNESS_MM},
        units="mm",
        comment="This uses the middle of the wall. Real sheet metal work uses "
                "a bend allowance that depends on the material and the "
                "process - which is exactly the sort of thing to ask the shop "
                "about, and a good fifth question.",
    )
    ws.compute(
        "drilling time for your hole count",
        lambda holes, minutes: holes * minutes / 60.0,
        {"number of holes": SKETCH_HOLE_COUNT,
         "minutes per hole": MINUTES_PER_HOLE},
        units="hours",
        comment="If you could not find a sensible minutes-per-hole figure, "
                "leave it UNKNOWN and put it on your questions list. Asking "
                "somebody who has done it is a better answer than guessing.",
    )


def your_plan(ws):
    ws.heading("your questions and your sequence")
    labelled = [
        ("rolling", QUESTION_ROLLING),
        ("drilling", QUESTION_DRILLING),
        ("welding", QUESTION_WELDING),
        ("tooling", QUESTION_TOOLING),
        ("inspection", QUESTION_INSPECTION),
    ]
    rows = [[name, str(q) if has_value(q) else "- not written yet -"]
            for name, q in labelled]
    ws.table(["process", "your question"], rows)

    steps = [s for s in PAPER_SEQUENCE if has_value(s)]
    if steps:
        ws.say("Your paper sequence, as it stands:")
        ws.bullets(["{0}. {1}".format(i, s) for i, s in enumerate(steps, 1)],
                   marker="   ")
        if len(steps) < 6:
            ws.say("Six to ten steps usually shakes out the gaps. Think about "
                   "what happens between the ones you have: how does the part "
                   "get held, when does it get checked, what happens if a hole "
                   "is in the wrong place.")
    else:
        ws.say("No sequence written yet. Start with 'cut the flat blank to "
               "length' and work forwards. Do not worry about being right; "
               "worry about leaving nothing out.")


def main():
    ws = Worksheet(
        code="C2",
        title="Find out what the shop can actually do",
        card="workspaces/combustion-systems/C2-fabrication.md",
        review_role="Combustion & Systems lead; Chief engineer for procurement",
    )
    ws.header(safety_line="Desk work only today. No shop entry, no machine, "
                          "no forming, no welding, no cutting. Shop training "
                          "and access are arranged by your lead.")
    lesson(ws)
    your_calculation(ws)
    your_plan(ws)

    ws.heading("what finishing looks like")
    ws.bullets([
        "Five questions, one per process, specific enough to be answerable.",
        "A short list of equipment you are sure exists, and a longer list of "
        "what you could not confirm.",
        "A rough paper sequence for a non-running mock-up.",
        "What your lead told you about how shop access and training are "
        "confirmed this semester.",
    ])
    ws.say("Not today: completing a safety quiz because a worksheet told you "
           "to, walking the shop, or committing to a fabrication route. Dates "
           "and rules in older task cards may no longer hold - ask your lead "
           "rather than acting on them.")

    ws.record("liner outer diameter used in the arithmetic",
              SKETCH_LINER_OUTER_DIAMETER_MM)
    ws.record("wall thickness used in the arithmetic", SKETCH_WALL_THICKNESS_MM)
    ws.record("hole count used in the arithmetic", SKETCH_HOLE_COUNT)
    ws.record("minutes per hole", MINUTES_PER_HOLE)
    ws.record("how shop access and training are confirmed", ACCESS_AND_TRAINING)

    ws.submission(date=DATE, learned=WHAT_I_LEARNED, unknown=STILL_UNKNOWN,
                  question=QUESTION_FOR_LEAD, next_step=NEXT_SMALL_STEP)
    ws.done_when([
        ("question about rolling", QUESTION_ROLLING),
        ("question about drilling", QUESTION_DRILLING),
        ("question about welding", QUESTION_WELDING),
        ("question about tooling", QUESTION_TOOLING),
        ("question about inspection", QUESTION_INSPECTION),
        ("at least one piece of equipment you are sure about",
         KNOWN_EQUIPMENT[0]),
        ("at least one thing you could not confirm", MISSING_INFORMATION[0]),
        ("how access and training are confirmed", ACCESS_AND_TRAINING),
        ("a paper sequence, at least three steps", PAPER_SEQUENCE[2]),
        ("one question for the lead", QUESTION_FOR_LEAD),
    ])
    ws.finish()


if __name__ == "__main__":
    main()
