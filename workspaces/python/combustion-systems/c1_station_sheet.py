"""C1 - Build a shared station-information sheet.  CORE first-meeting worksheet.

WHAT THIS IS
  A 30-45 minute guided activity. You are going to make the one-page table
  that everybody else on the project reads when they need to know what the
  air is doing where it meets the fuel - and, just as importantly, where each
  of those numbers came from.

HOW TO USE IT
  1. Run it once and read what it prints:   python c1_station_sheet.py
  2. Read the candidate table and the recalculation paragraph in
     docs/project/dp2-review.md.
  3. Fill in the block below marked YOUR ANSWERS.
  4. Save, run again, hand the printed block to your lead.

WHAT THIS IS NOT
  It does not import the engine model and cannot change any design value. It
  does not re-size a liner and does not settle a pressure budget.
"""

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
for _folder in (_HERE, _HERE.parent):
    if str(_folder) not in sys.path:
        sys.path.insert(0, str(_folder))
try:
    from worksheet_common import (CANDIDATE, EXAMPLE, NOT_FOUND, REPO_CHECK,
                                  UNKNOWN, Worksheet, answer, as_number,
                                  has_value)
except ImportError:
    print("Could not find worksheet_common.py.")
    print("Keep this file in its team folder next to the other worksheets,")
    print("or use the starter bundle. See workspaces/python/HOW-TO-RUN.md.")
    raise SystemExit(1)


# ===========================================================================
#  YOUR ANSWERS - this is the only part of the file you need to edit.
# ===========================================================================

DATE = UNKNOWN                 # e.g. "2026-09-17"

# Five rows. For each one: the number, its units, and how it came to exist.
#
# "how it came to exist" must be one of these four words:
#   chosen    somebody picked it because they were free to
#   assumed   somebody had to put something, and this is the placeholder
#   computed  it falls out of the other numbers; you cannot pick it separately
#   measured  somebody measured it on real hardware
#
# Rule of thumb: if changing it would change other numbers, it is chosen or
# assumed. If it changes only when something else does, it is computed.
# Nothing in DP-2 is measured. That is itself worth noticing.

STATION_SHEET = [
    {
        "quantity":  "combustor inlet total temperature T3",
        "value":     UNKNOWN,          # e.g. 348.10
        "units":     UNKNOWN,          # e.g. "K"
        "how":       UNKNOWN,          # chosen / assumed / computed / measured
        "source":    UNKNOWN,          # where in the review you read it
    },
    {
        "quantity":  "combustor inlet total pressure P3",
        "value":     UNKNOWN,
        "units":     UNKNOWN,
        "how":       UNKNOWN,
        "source":    UNKNOWN,
    },
    {
        "quantity":  "air mass flow",
        "value":     UNKNOWN,
        "units":     UNKNOWN,
        "how":       UNKNOWN,
        "source":    UNKNOWN,
    },
    {
        "quantity":  "fuel flow",
        "value":     UNKNOWN,
        "units":     UNKNOWN,
        "how":       UNKNOWN,
        "source":    UNKNOWN,
    },
    {
        "quantity":  "casing outer diameter",
        "value":     UNKNOWN,
        "units":     UNKNOWN,
        "how":       UNKNOWN,
        "source":    UNKNOWN,
    },
]

# The fuel-air ratio you want to use for the arithmetic below. There is more
# than one in circulation; that is the point of this exercise.
FUEL_AIR_RATIO = answer(
    value=UNKNOWN,             # e.g. 0.0212, or 0.02196 - try both
    units="kg fuel per kg air",
    source=UNKNOWN,            # say which one you used and where it came from
    uncertainty=UNKNOWN,
)

# In one sentence: what is the fuel-flow discrepancy, and why does it matter?
FUEL_DISCREPANCY_NOTE = UNKNOWN

# Your question for T2 about where their loss budget stops and yours starts.
QUESTION_FOR_T2 = UNKNOWN

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

HOW_WORDS = ("chosen", "assumed", "computed", "measured")
AIR_FLOW = 0.30                # kg/s, DP-2 candidate
NOTE_FAR = 0.0212              # the DP-2 note's fuel-air ratio
REPO_FAR = 0.02196             # the repository screen's fuel-air ratio
ALLOWANCE_KG_H = 29.0          # DP-2's "size the fuel system for this" figure
# What the repository screen reproduces, for the consistency check below.
SCREEN_VALUES = {
    "combustor inlet total temperature T3": (348.10, "K"),
    "combustor inlet total pressure P3": (163.51, "kPa"),
    "air mass flow": (0.30, "kg/s"),
    "fuel flow": (23.72, "kg/h"),
    "casing outer diameter": (152.4, "mm"),
}


def lesson(ws):
    ws.heading("what a station sheet is for")
    ws.say("A recipe that says 'bake until done' is not a recipe. A design "
           "that says 'the air arrives hot and under pressure' is not a "
           "design. A station sheet is the page that says exactly how hot and "
           "exactly how much pressure, at each numbered place along the "
           "engine, in units everyone agrees on.")
    ws.say("Stations are just numbered spots along the air path. Station 3 is "
           "roughly where air leaves the compressor and enters your combustor. "
           "Station 4 is where hot gas leaves it. Every team uses those "
           "numbers, which is why they have to mean the same thing to all of "
           "us.")
    ws.say("Your combustor is the component the DP-2 review puts closest to "
           "the edge. At a pressure ratio of about 1.63 there is not much "
           "pressure in the engine to start with, so pressure lost in the "
           "combustor is what decides whether this engine can keep itself "
           "running. You cannot budget a loss until you know what you are "
           "losing it from. Hence the sheet, and hence today.")

    ws.heading("the words you need")
    ws.terms([
        ("station",
         "A numbered place along the air path. Station 3 is combustor inlet, "
         "station 4 is combustor exit / turbine inlet."),
        ("total temperature and pressure",
         "The values you would measure bringing the flow smoothly to rest. "
         "Cycle calculations use total conditions almost everywhere. Mixing "
         "total and static values in the same table is a classic way to "
         "produce a confidently wrong answer."),
        ("fuel-air ratio, FAR",
         "Kilograms of fuel per kilogram of air. A small number, around 0.02. "
         "Multiply it by air flow to get fuel flow."),
        ("chosen, assumed, computed",
         "Three completely different kinds of number that look identical once "
         "they are in a table. Labelling which is which is most of the value "
         "of this task."),
        ("allowance",
         "A deliberately generous figure used for sizing hardware, so that "
         "being wrong is survivable. It is not a prediction and it should "
         "never be copied into a performance table."),
    ])

    ws.heading("what the repository reproduces")
    ws.legend()
    ws.given("combustor inlet total temperature T3", 348.10, "K", REPO_CHECK)
    ws.given("combustor inlet total pressure P3", 163.51, "kPa", REPO_CHECK)
    ws.given("air mass flow", AIR_FLOW, "kg/s", CANDIDATE)
    ws.given("fuel-air ratio from the repository screen", REPO_FAR,
             "kg/kg", REPO_CHECK)
    ws.given("fuel-air ratio quoted in the DP-2 note", NOTE_FAR, "kg/kg",
             CANDIDATE, "the note and the screen disagree - see below")
    ws.given("casing outer diameter", 152.4, "mm", CANDIDATE)
    ws.blank()
    ws.say("Everything above is in docs/project/dp2-review.md. Go and read it "
           "there rather than copying from this screen, because part of the "
           "task is finding out which paragraph each number lives in.")

    ws.heading("the discrepancy you are being asked to mark")
    ws.say("Three fuel numbers are in circulation and they are not the same:")
    ws.example([
        "  from the note's fuel-air ratio:",
        "     0.30 kg/s * 0.0212 * 3600 s/h      = 22.90 kg/h",
        "",
        "  from the repository screen's ratio:",
        "     0.30 kg/s * 0.02196 * 3600 s/h     = 23.72 kg/h",
        "",
        "  the sizing allowance DP-2 asks for:    29 kg/h",
        "",
        "  22.90 to 23.72 is a 3.6 percent gap, which is a real disagreement",
        "  between two calculations and needs reconciling before anybody",
        "  publishes a common station table.",
        "",
        "  23.72 to 29 is a 22 percent gap, and that one is not a",
        "  disagreement at all - it is a deliberate margin for sizing the",
        "  pump and lines. The DP-2 review says plainly that it is an",
        "  allowance, not a demonstrated correction.",
        "",
        "Two gaps, two completely different meanings, and a table that does",
        "not say which is which will mislead somebody in October.",
    ])


def your_sheet(ws):
    ws.heading("your station sheet")
    rows = []
    for item in STATION_SHEET:
        rows.append([
            item["quantity"],
            str(item["value"]) if has_value(item["value"]) else "-",
            str(item["units"]) if has_value(item["units"]) else "-",
            str(item["how"]) if has_value(item["how"]) else "-",
        ])
    ws.table(["quantity", "value", "units", "how it came to exist"], rows)

    notes = []
    for item in STATION_SHEET:
        name = item["quantity"]
        if has_value(item["value"]) and not has_value(item["units"]):
            notes.append("{0}: a number without units is not an answer".format(name))
        how = str(item["how"]).strip().lower()
        if has_value(item["how"]) and how not in HOW_WORDS:
            notes.append("{0}: '{1}' is not one of {2}".format(
                name, item["how"], " / ".join(HOW_WORDS)))
        if how == "measured":
            notes.append("{0}: nothing in DP-2 has been measured on hardware. "
                         "If you meant 'taken from a supplier datasheet', that "
                         "is still not a measurement of our engine.".format(name))
        value = as_number(item["value"])
        expected = SCREEN_VALUES.get(name)
        if value is not None and expected is not None:
            target, units = expected
            if target and abs(value - target) / abs(target) > 0.05:
                notes.append(
                    "{0}: you wrote {1}, the repository screen reproduces "
                    "about {2} {3}. Neither is automatically wrong - check "
                    "whether you are quoting a different source, and say which "
                    "in your notes.".format(name, value, target, units))
        if has_value(item["value"]) and not has_value(item["source"]):
            notes.append("{0}: no source recorded".format(name))

    if notes:
        ws.say("Things worth a second look:")
        ws.bullets(notes)
    elif any(has_value(item["value"]) for item in STATION_SHEET):
        ws.bullets(["Nothing inconsistent in what you have entered so far."])
    else:
        ws.say("Nothing entered yet. Open docs/project/dp2-review.md, fill in "
               "a row, and run this again.")


def your_calculation(ws):
    ws.heading("now do the fuel arithmetic yourself")
    fuel = ws.compute(
        "fuel flow from the fuel-air ratio you chose",
        lambda far: AIR_FLOW * far * 3600.0,
        {"fuel-air ratio": FUEL_AIR_RATIO},
        units="kg/h",
        comment="Air flow is 0.30 kg/s and there are 3600 seconds in an hour.",
    )
    if fuel is not None:
        ws.compute(
            "how far the 29 kg/h sizing allowance sits above your number",
            lambda f: 100.0 * (ALLOWANCE_KG_H - f) / f,
            {"your fuel flow (kg/h)": fuel},
            units="percent",
            comment="Whatever this comes out as, write in your notes that it "
                    "is a sizing allowance and not a prediction. That sentence "
                    "is the deliverable.",
        )
        ws.compute(
            "difference from the repository screen's 23.72 kg/h",
            lambda f: 100.0 * (f - 23.72) / 23.72,
            {"your fuel flow (kg/h)": fuel},
            units="percent",
        )


def main():
    ws = Worksheet(
        code="C1",
        title="Build a shared station-information sheet",
        card="workspaces/combustion-systems/C1-combustor.md",
        review_role="Combustion & Systems lead",
    )
    ws.header()
    lesson(ws)
    your_sheet(ws)
    your_calculation(ws)

    ws.heading("what finishing looks like")
    ws.bullets([
        "Five rows, each with a value, its units, and whether it was chosen, "
        "assumed or computed.",
        "One sentence marking the fuel-flow discrepancy.",
        "One question for T2 about where their loss budget stops and yours "
        "starts - so that between you, every feature is counted once and "
        "none is counted twice.",
    ])
    ws.say("Not today: re-sizing the liner, settling the residence time, or "
           "adopting any casing loss estimate as a measured loss. The DP-2 "
           "review is explicit that a casing-area estimate is not a local "
           "feed-annulus, hole or turn area, and the shared pressure budget "
           "is later work with your lead and T2.")

    ws.record("fuel-air ratio used", FUEL_AIR_RATIO)
    for item in STATION_SHEET:
        ws.record(item["quantity"], answer(
            value=item["value"], units=str(item["units"]),
            source=item["source"],
            uncertainty="recorded as: {0}".format(item["how"])))

    ws.submission(date=DATE, learned=WHAT_I_LEARNED, unknown=STILL_UNKNOWN,
                  question=QUESTION_FOR_LEAD, next_step=NEXT_SMALL_STEP)
    ws.done_when([
        ("T3 value and units", STATION_SHEET[0]["value"]),
        ("P3 value and units", STATION_SHEET[1]["value"]),
        ("air flow value and units", STATION_SHEET[2]["value"]),
        ("fuel flow value and units", STATION_SHEET[3]["value"]),
        ("casing outer diameter value and units", STATION_SHEET[4]["value"]),
        ("the fuel-flow discrepancy, in one sentence", FUEL_DISCREPANCY_NOTE),
        ("a question for T2 about the loss-budget boundary", QUESTION_FOR_T2),
    ])
    ws.finish()


if __name__ == "__main__":
    main()
