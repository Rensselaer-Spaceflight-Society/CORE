"""T4 - Inventory existing CAD without redrawing it.  CORE first-meeting worksheet.

WHAT THIS IS
  A 30-45 minute guided activity. You are going to find out what drawings and
  models this project actually has, where they live, and whether they were
  drawn for the same engine. You will not draw anything.

HOW TO USE IT
  1. Run it once and read what it prints:   python t4_cad_inventory.py
  2. Fill in up to three rows in the block below marked YOUR ANSWERS.
  3. Save, run again, hand the printed block to your lead.

WHAT THIS IS NOT
  It does not import the engine model and cannot change any design value. It
  does not open, move, rename, overwrite or delete a single CAD file.
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
                                  UNKNOWN, Worksheet, answer, as_number,
                                  has_value, is_not_found)
except ImportError:
    print("Could not find worksheet_common.py.")
    print("Keep this file in its team folder next to the other worksheets,")
    print("or use the starter bundle. See workspaces/python/HOW-TO-RUN.md.")
    raise SystemExit(1)


# ===========================================================================
#  YOUR ANSWERS - this is the only part of the file you need to edit.
# ===========================================================================

DATE = UNKNOWN                 # e.g. "2026-09-17"

# Up to three things. A thing can be a CAD model, a drawing, a dimension
# table, or a page of the DP-2 review. If you cannot find any CAD at all,
# that is a genuine and important finding: fill the rows in from the DP-2
# candidate table instead and put NOT FOUND under "where it lives".
#
# Status must be one of: available / missing / needs review

CAD_INVENTORY = [
    {
        "what it is":               UNKNOWN,   # e.g. "combustor liner, STEP file"
        "where it lives":           UNKNOWN,   # e.g. "team Drive > CAD > combustor"
        "revision or date":         UNKNOWN,   # e.g. "rev C, 2026-04-11"
        "one dimension from it":    UNKNOWN,   # e.g. "liner outer diameter 120"
        "units":                    UNKNOWN,   # e.g. "mm"
        "drawn for mass flow kg/s": UNKNOWN,   # e.g. 0.60, or NOT_FOUND
        "status":                   UNKNOWN,   # available / missing / needs review
    },
    {
        "what it is":               UNKNOWN,
        "where it lives":           UNKNOWN,
        "revision or date":         UNKNOWN,
        "one dimension from it":    UNKNOWN,
        "units":                    UNKNOWN,
        "drawn for mass flow kg/s": UNKNOWN,
        "status":                   UNKNOWN,
    },
    {
        "what it is":               UNKNOWN,
        "where it lives":           UNKNOWN,
        "revision or date":         UNKNOWN,
        "one dimension from it":    UNKNOWN,
        "units":                    UNKNOWN,
        "drawn for mass flow kg/s": UNKNOWN,
        "status":                   UNKNOWN,
    },
]

# The turbine tip clearance, if any document states it. Almost certainly
# NOT_FOUND today. Recording that it is missing is the useful outcome.
STATED_TIP_CLEARANCE_MM = answer(
    value=UNKNOWN,
    units="mm",
    source=UNKNOWN,
    uncertainty=UNKNOWN,
)

# One mating surface you want to ask Structures about (optional stretch).
MATING_SURFACE_QUESTION = UNKNOWN

# Your writing.
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

DP2_MASS_FLOW = 0.30           # kg/s, DP-2 candidate
CASING_ID_MM = 149.4           # mm, DP-2 candidate
TURBINE_TIP_MM = 88.2          # mm, DP-2 candidate
VALID_STATUS = ("available", "missing", "needs review")


def lesson(ws):
    ws.heading("what this job actually is")
    ws.say("Imagine building a house where the plumber has one set of plans, "
           "the electrician has an older set, and the roofer has a sketch "
           "somebody made on a napkin. Everything fits on its own drawing. "
           "Nothing fits on site.")
    ws.say("That is the situation this project is in right now, and it is "
           "nobody's fault - it is what happens when a design changes and the "
           "drawings do not all change with it. Your job today is the boring, "
           "unglamorous, genuinely important one: find out what we are actually "
           "holding, and write it down in one place.")
    ws.say("You are not fixing it today. You are not redrawing anything. "
           "Somebody has to know what exists before anybody can decide what to "
           "keep.")

    ws.heading("the words you need")
    ws.terms([
        ("revision",
         "Which version of a drawing this is. Without one, two people can "
         "honestly disagree about what a part looks like and both be right. "
         "A date is a usable substitute if there is no revision letter."),
        ("datum",
         "The face or line everything else is measured from. If two drawings "
         "measure from different datums, their dimensions do not add up even "
         "when both are correct."),
        ("mating surface",
         "Where two parts actually touch. This is where errors show up first, "
         "and it is what Structures will want to talk to you about."),
        ("interface",
         "A dimension, load or signal that crosses between two people's work. "
         "CORE keeps these in workspaces/coordination/interfaces.md, one row "
         "each, so nobody has to guess."),
        ("clearance",
         "The gap between a moving part and the thing nearest to it. Note the "
         "word NEAREST - see the trap below."),
    ])

    ws.heading("the trap in this task")
    ws.legend()
    ws.given("casing inner diameter", CASING_ID_MM, "mm", CANDIDATE)
    ws.given("turbine tip diameter", TURBINE_TIP_MM, "mm", CANDIDATE)
    ws.given("radial gap between those two circles",
             (CASING_ID_MM - TURBINE_TIP_MM) / 2.0, "mm", CANDIDATE,
             "arithmetic on the two candidate diameters above")
    ws.blank()
    ws.say("Thirty millimetres sounds like a comfortable gap. It is also "
           "completely the wrong number, and the DP-2 review says so "
           "explicitly: turbine tip clearance is measured to the SHROUD right "
           "around the blade, not to the outer casing. In a small engine that "
           "clearance is a fraction of a millimetre, it is one of the things "
           "that most affects efficiency, and no document we have states it.")
    ws.say("So one of your inventory rows should be the shroud, and its status "
           "is very likely 'missing'. Writing NOT FOUND next to something "
           "important is a better day's work than writing a number nobody "
           "checked.")

    ws.heading("the other thing to look for")
    ws.say("The DP-2 review notes that parts of our CAD were drawn for "
           "different air flows - roughly 0.50 kg/s for the inlet and 0.60 "
           "kg/s for the combustor, while DP-2 proposes 0.30 kg/s. If you can "
           "find what flow a model was drawn for, record it. This worksheet "
           "will flag anything that does not match.")
    ws.example([
        "An inventory row that is doing its job looks like this:",
        "",
        "  what it is               : combustor liner, SolidWorks part",
        "  where it lives           : team Drive > CAD > combustor > rev C",
        "  revision or date         : rev C, 2026-04-11",
        "  one dimension from it    : liner outer diameter 120",
        "  units                    : mm",
        "  drawn for mass flow kg/s : 0.60",
        "  status                   : needs review",
        "",
        "Every value above is invented for this example. Do not copy them.",
        "The point is the shape: a name, a place, a version, one measurable",
        "thing with its units, and an honest status.",
    ])


def your_inventory(ws):
    ws.heading("your inventory")
    rows = []
    complete = 0
    for index, item in enumerate(CAD_INVENTORY, start=1):
        filled = sum(1 for key in item if has_value(item[key])
                     or is_not_found(item[key]))
        if filled == len(item):
            complete += 1
        def shown(key):
            value = item[key]
            if is_not_found(value):
                return NOT_FOUND
            return str(value) if has_value(value) else "-"

        rows.append([
            str(index),
            shown("what it is") if has_value(item["what it is"]) else "(empty row)",
            shown("revision or date"),
            "{0} {1}".format(shown("one dimension from it"),
                             shown("units")).replace("- -", "-").strip(),
            shown("status"),
        ])
    ws.table(["#", "what it is", "revision", "one dimension", "status"], rows)

    if complete == 0:
        ws.say("No rows filled in yet. Fill in at least three fields on one "
               "row and run this again - it will start checking them for you.")
        return

    ws.say("Checks this worksheet can do for you:")
    problems = []
    for index, item in enumerate(CAD_INVENTORY, start=1):
        if not has_value(item["what it is"]):
            continue
        status = str(item["status"]).strip().lower()
        if has_value(item["status"]) and status not in VALID_STATUS:
            problems.append("row {0}: status '{1}' is not one of {2}".format(
                index, item["status"], " / ".join(VALID_STATUS)))
        if has_value(item["one dimension from it"]) and not has_value(item["units"]):
            problems.append("row {0}: a dimension with no units is not a "
                            "dimension".format(index))
        flow = as_number(item["drawn for mass flow kg/s"])
        if flow is not None and abs(flow - DP2_MASS_FLOW) > 1e-9:
            problems.append(
                "row {0}: drawn for {1} kg/s, DP-2 proposes {2} kg/s - this "
                "model does not describe the candidate engine".format(
                    index, flow, DP2_MASS_FLOW))
        if is_not_found(item["where it lives"]):
            problems.append("row {0}: file not found - make sure the status "
                            "says 'missing', not 'available'".format(index))
    if problems:
        ws.bullets(problems)
        ws.say("None of these are mistakes on your part. They are findings. "
               "Put the important ones in your notes for the lead.")
    else:
        ws.bullets(["Nothing inconsistent found in what you have entered so "
                    "far. That is not the same as complete."])

    ws.compute(
        "difference between a stated tip clearance and the casing gap",
        lambda stated: (CASING_ID_MM - TURBINE_TIP_MM) / 2.0 - stated,
        {"stated tip clearance (mm)": STATED_TIP_CLEARANCE_MM},
        units="mm",
        comment="If you found a real stated clearance, this shows how far the "
                "casing gap is from it. If you did not, leave it UNKNOWN - "
                "that absence is your finding.",
    )


def main():
    ws = Worksheet(
        code="T4",
        title="Inventory existing CAD without redrawing it",
        card="workspaces/turbomachinery/T4-assembly.md",
        review_role="Turbomachinery lead; Structures lead for interfaces",
    )
    ws.header(safety_line="Desk work only today. Read-only. Do not scrap, "
                          "overwrite, rename or re-cut any CAD file.")
    lesson(ws)
    your_inventory(ws)

    ws.heading("what finishing looks like")
    ws.bullets([
        "Three inventory rows, each labelled available, missing or needs "
        "review.",
        "At least one dimension written down with its units.",
        "An honest NOT FOUND wherever the file or the revision is not there.",
        "One question for Structures about a surface where two parts meet.",
    ])
    ws.say("Not today: freezing an interface, rebuilding the assembly, or "
           "deciding what gets scrapped. Those follow from the inventory, and "
           "they are the lead's call with the Chief engineer.")

    ws.record("stated turbine tip clearance", STATED_TIP_CLEARANCE_MM)

    ws.submission(date=DATE, learned=WHAT_I_LEARNED, unknown=STILL_UNKNOWN,
                  question=QUESTION_FOR_LEAD, next_step=NEXT_SMALL_STEP)
    ws.done_when([
        ("inventory row 1 named", CAD_INVENTORY[0]["what it is"]),
        ("inventory row 1 status", CAD_INVENTORY[0]["status"]),
        ("inventory row 2 named", CAD_INVENTORY[1]["what it is"]),
        ("inventory row 2 status", CAD_INVENTORY[1]["status"]),
        ("inventory row 3 named", CAD_INVENTORY[2]["what it is"]),
        ("inventory row 3 status", CAD_INVENTORY[2]["status"]),
        ("tip clearance found, or NOT FOUND", STATED_TIP_CLEARANCE_MM),
        ("one question for the lead", QUESTION_FOR_LEAD),
    ])
    ws.finish()


if __name__ == "__main__":
    main()
