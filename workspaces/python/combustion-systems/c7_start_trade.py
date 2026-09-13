"""C7 - Compare starting methods as a desk study.  CORE first-meeting worksheet.

WHAT THIS IS
  A 30-45 minute guided activity, entirely on paper. You will compare two
  ways of getting the engine lit, side by side, and work out the electrical
  demand of one of them.

HOW TO USE IT
  1. Run it once and read what it prints:   python c7_start_trade.py
  2. Edit the block below marked YOUR ANSWERS. Nothing else.
  3. Save, run again, hand the printed block to your lead.

  Write it so that somebody else could pick it up and finish it. A good desk
  study is complete in itself and does not depend on one person still being
  available in November.

WHAT THIS IS NOT
  No ignition demonstration, no fuel, no gas bottle, no igniter test, no
  hardware of any kind today. This file contains no ignition, starter or fuel
  control code and cannot drive anything. It is a comparison table and some
  arithmetic about electricity.
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

# 1. The comparison. Fill in both columns for each row. Where you do not
#    know a cost, write NOT_FOUND - never zero. A zero in a cost column is
#    read by everybody downstream as "free", and that is how budgets break.
COMPARISON = [
    {
        "question":       "extra parts this method needs",
        "gas assisted":   UNKNOWN,
        "direct kerosene": UNKNOWN,
    },
    {
        "question":       "electrical power it needs",
        "gas assisted":   UNKNOWN,
        "direct kerosene": UNKNOWN,
    },
    {
        "question":       "delivered cost, with a source",
        "gas assisted":   UNKNOWN,
        "direct kerosene": UNKNOWN,
    },
    {
        "question":       "what the controller has to switch",
        "gas assisted":   UNKNOWN,
        "direct kerosene": UNKNOWN,
    },
    {
        "question":       "what could go wrong, and how you would know",
        "gas assisted":   UNKNOWN,
        "direct kerosene": UNKNOWN,
    },
    {
        "question":       "what it adds to the safety conversation",
        "gas assisted":   UNKNOWN,
        "direct kerosene": UNKNOWN,
    },
]

# 2. Two questions to hand to C3 (fuel) and C4 (controls).
QUESTION_FOR_C3_FUEL = UNKNOWN
QUESTION_FOR_C4_CONTROLS = UNKNOWN

# 3. For the electrical arithmetic. Find real figures if you can, and cite
#    them; otherwise leave them UNKNOWN and the sums stay blank.
IGNITER_POWER_W = answer(
    value=UNKNOWN,             # e.g. 37
    units="W",
    source=UNKNOWN,            # a manufacturer page
    uncertainty=UNKNOWN,
)
SUPPLY_VOLTAGE_V = answer(
    value=UNKNOWN,             # e.g. 7.2
    units="V",
    source=UNKNOWN,
)
ATTEMPT_DURATION_S = answer(
    value=UNKNOWN,             # e.g. 20
    units="s",
    source="a duration I chose for the comparison",
    basis=EXAMPLE,
)
BATTERY_CAPACITY_AH = answer(
    value=UNKNOWN,             # e.g. 2.0
    units="Ah",
    source=UNKNOWN,
)

# 4. Your writing.
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
    ws.heading("why an engine needs starting at all")
    ws.say("A jet engine cannot start itself, for the same reason you cannot "
           "push-start a car that is already stopped on a flat road by sitting "
           "in it. The turbine only makes power once hot gas is flowing, and "
           "hot gas only flows once the compressor is already turning. "
           "Somebody has to break into the circle from outside.")
    ws.say("Two separate things have to happen. The shaft has to be spun up to "
           "a speed where the compressor is delivering usefully - that is the "
           "starter's job. And the fuel has to be set alight and stay alight - "
           "that is the igniter's job. Your card is about the second one.")
    ws.say("Lighting kerosene is harder than it sounds. It is not very "
           "volatile at room temperature, and it is being sprayed into a "
           "draught. There are two established ways round that, and your task "
           "is to lay them side by side honestly.")

    ws.heading("the two paths, in plain language")
    ws.terms([
        ("gas-assisted start",
         "Light a small flow of an easily-ignited gas first, and use that "
         "flame to light the kerosene. The common approach across commercial "
         "model turbines. Cheap and well proven - but it puts a bottle of "
         "pressurised flammable gas on the test stand, which is a real "
         "addition to the safety case rather than a paperwork detail."),
        ("direct kerosene start",
         "No bottle. Instead a much hotter electrical element does the "
         "lighting on its own. Simpler to set up and fewer things on the "
         "stand, but it needs significantly more electrical power, on its own "
         "supply, and its failure modes tend to be electrical: wiring "
         "resistance, tired batteries, unprimed lines."),
        ("trade study",
         "Laying two options side by side against the same questions, with "
         "sources, and saying what you would choose and why. The value is in "
         "the comparison being fair, not in the conclusion being bold."),
        ("delivered cost",
         "What it actually costs to have the thing in your hand: price plus "
         "shipping plus tax plus whatever fittings it turns out to need. Not "
         "the number on the product page."),
        ("NOT FOUND",
         "The correct entry for a cost you could not establish. Zero is not. "
         "The project's quote log says this explicitly, and it exists because "
         "somebody, somewhere, once wrote zero."),
    ])

    ws.heading("what this comparison feeds")
    ws.say("This is not a side quest. Until it is decided, three other people "
           "are blocked: the fuel system does not know whether it needs a gas "
           "branch, the controller does not know how many outputs it is "
           "switching, and Safety cannot finish the hazard list. A clean "
           "decision memo with its working shown unblocks all three.")
    ws.say("It is also bounded. The DP-2 review lists the start method as one "
           "of the open decisions, with the lead owning the final call. Your "
           "job is to make that call easy to make, not to make it.")

    ws.heading("a worked example, so the arithmetic is not a mystery")
    ws.say("Electrical demand is the one part of this comparison you can put "
           "real numbers on from a desk. Power in watts, divided by supply "
           "voltage, gives the current the wiring has to carry. Power times "
           "time gives the energy each attempt costs.")
    ws.example([
        "A ceramic igniter drawing 37 W from a 7.2 V pack, for a 20 second",
        "start attempt:",
        "",
        "  current  = 37 W / 7.2 V                = 5.14 A",
        "  energy   = 37 W * 20 s                 = 740 J",
        "           = 740 / 3600                  = 0.206 Wh",
        "",
        "A 2.0 Ah pack at 7.2 V holds:",
        "",
        "  capacity = 2.0 Ah * 7.2 V              = 14.4 Wh",
        "  attempts = 14.4 / 0.206                = 70",
        "",
        "Seventy attempts sounds like plenty. It is also an upper bound that",
        "assumes the battery gives up every joule it holds, at full voltage,",
        "at 5 amps, with nothing else drawing from it. None of those are",
        "true. Real packs sag under load, lose capacity when drained fast,",
        "and are usually also feeding the starter, the valves and the",
        "electronics. And a glowing element does not last forever.",
        "",
        "That gap between the tidy arithmetic and reality is the useful part.",
        "Put the number in your table with the assumptions written next to",
        "it, and it becomes evidence. Put it in bare and it becomes a claim",
        "somebody will rely on.",
        "",
        "All four figures above are illustrative. Find real ones and cite",
        "them.",
    ])


def your_calculation(ws):
    ws.heading("now do it with figures you can cite")
    ws.compute(
        "current the igniter draws",
        lambda power, volts: power / volts,
        {"igniter power (W)": IGNITER_POWER_W,
         "supply voltage (V)": SUPPLY_VOLTAGE_V},
        units="A",
        comment="This is what the wiring, the connectors and the switching "
                "device all have to carry. It is a number worth having before "
                "anybody orders a connector.",
    )
    energy = ws.compute(
        "energy used in one start attempt",
        lambda power, seconds: power * seconds,
        {"igniter power (W)": IGNITER_POWER_W,
         "attempt duration (s)": ATTEMPT_DURATION_S},
        units="J",
    )
    capacity = ws.compute(
        "energy the battery pack holds",
        lambda amp_hours, volts: amp_hours * volts * 3600.0,
        {"battery capacity (Ah)": BATTERY_CAPACITY_AH,
         "supply voltage (V)": SUPPLY_VOLTAGE_V},
        units="J",
    )
    if energy is not None and capacity is not None:
        ws.compute(
            "upper bound on start attempts per charge",
            lambda total, each: total / each,
            {"battery energy (J)": capacity, "energy per attempt (J)": energy},
            units="attempts",
            comment="Upper bound, and a generous one. Write next to it what it "
                    "ignores: voltage sag, capacity loss at high current, "
                    "everything else on the same pack, and element wear.",
        )


def your_table(ws):
    ws.heading("your comparison")
    rows = []
    for item in COMPARISON:
        rows.append([
            item["question"],
            str(item["gas assisted"]) if has_value(item["gas assisted"]) else "-",
            str(item["direct kerosene"])
            if has_value(item["direct kerosene"]) else "-",
        ])
    ws.table(["question", "gas assisted", "direct kerosene"], rows)

    notes = []
    for item in COMPARISON:
        for column in ("gas assisted", "direct kerosene"):
            value = item[column]
            if as_number(value) == 0.0 and has_value(value):
                notes.append("{0} / {1}: a zero here reads as 'free' or 'none' "
                             "to everyone downstream. If you do not know, "
                             "write NOT FOUND.".format(item["question"], column))
        filled = [has_value(item[c]) for c in ("gas assisted", "direct kerosene")]
        if any(filled) and not all(filled):
            notes.append("{0}: only one column filled - a half-filled row is "
                         "not a comparison".format(item["question"]))
    if notes:
        ws.bullets(notes)
    elif any(has_value(item["gas assisted"]) for item in COMPARISON):
        ws.bullets(["Nothing inconsistent in what you have entered so far."])
    else:
        ws.say("Nothing entered yet. Start with the first row - counting parts "
               "is easy and it frames everything else.")


def main():
    ws = Worksheet(
        code="C7",
        title="Compare starting methods as a desk study",
        card="workspaces/combustion-systems/C7-start-options.md",
        review_role="Combustion & Systems lead; Safety lead reviews hazards",
    )
    ws.header(safety_line="Paper and arithmetic only today. No igniter test, "
                          "no fuel, no gas bottle, no pressurised anything, "
                          "no ignition demonstration.")
    lesson(ws)
    your_table(ws)
    your_calculation(ws)

    ws.heading("what finishing looks like")
    ws.bullets([
        "A two-column comparison where both columns are filled for every row.",
        "Costs sourced, or honestly marked NOT FOUND.",
        "One question each for C3 and C4.",
        "A note that somebody else could finish without talking to you.",
    ])
    ws.say("Not today: demonstrating an ignition, presenting fuel to anything, "
           "handling a pressure bottle, or making the decision. Igniter "
           "testing is a separate, separately reviewed task, and the lead owns "
           "the final choice of start method.")
    ws.say("If you find a manufacturer's manual, label its numbers as that "
           "engine's. Published start timings and thresholds describe the "
           "engine they were measured on, and copying them into CORE is one of "
           "the specific things the DP-2 review warns against.")

    ws.record("igniter power", IGNITER_POWER_W)
    ws.record("supply voltage", SUPPLY_VOLTAGE_V)
    ws.record("attempt duration assumed", ATTEMPT_DURATION_S)
    ws.record("battery capacity", BATTERY_CAPACITY_AH)

    ws.submission(date=DATE, learned=WHAT_I_LEARNED, unknown=STILL_UNKNOWN,
                  question=QUESTION_FOR_LEAD, next_step=NEXT_SMALL_STEP)
    ws.done_when([
        ("extra parts, both columns", COMPARISON[0]["gas assisted"]),
        ("electrical power, both columns", COMPARISON[1]["gas assisted"]),
        ("delivered cost or NOT FOUND, both columns",
         COMPARISON[2]["gas assisted"]),
        ("what the controller switches, both columns",
         COMPARISON[3]["gas assisted"]),
        ("failure modes, both columns", COMPARISON[4]["gas assisted"]),
        ("safety burden, both columns", COMPARISON[5]["gas assisted"]),
        ("question for C3", QUESTION_FOR_C3_FUEL),
        ("question for C4", QUESTION_FOR_C4_CONTROLS),
    ])
    ws.finish()


if __name__ == "__main__":
    main()
