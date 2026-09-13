"""C5 - Agree the model-to-controller interface.  CORE first-meeting worksheet.

WHAT THIS IS
  A 30-45 minute guided activity, all desk work. You and C4 are going to
  agree what information passes between an engine model and a controller,
  before either of you builds anything. Then one small power-balance sum
  shows why "the exhaust has positive pressure" is not the same as "the
  engine can keep itself running".

HOW TO USE IT
  1. Run it once and read what it prints:   python c5_model_interface.py
  2. Sit down with C4 and fill in the five rows together.
  3. Edit the block below marked YOUR ANSWERS. Nothing else.
  4. Save, run again, hand the printed block to your lead.

WHAT THIS IS NOT
  It does not import the engine model and cannot change any design value.
  It is not an off-design solver and contains no controller code. Every
  number you type here is synthetic - a made-up value used to test whether
  the interface makes sense, not a claim about our engine.
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

# 1. Five signals that cross between the model and the controller.
#    "direction" must be either "model -> controller" or "controller -> model".
#    "if it is missing" is the field people skip and then regret.
SIGNALS = [
    {
        "signal":           UNKNOWN,   # e.g. "shaft speed"
        "units":            UNKNOWN,   # e.g. "rpm"
        "direction":        UNKNOWN,   # model -> controller / controller -> model
        "update rate":      UNKNOWN,   # e.g. "100 per second"
        "if it is missing": UNKNOWN,   # e.g. "mark invalid; do not hold last value"
    },
    {
        "signal":           UNKNOWN,
        "units":            UNKNOWN,
        "direction":        UNKNOWN,
        "update rate":      UNKNOWN,
        "if it is missing": UNKNOWN,
    },
    {
        "signal":           UNKNOWN,
        "units":            UNKNOWN,
        "direction":        UNKNOWN,
        "update rate":      UNKNOWN,
        "if it is missing": UNKNOWN,
    },
    {
        "signal":           UNKNOWN,
        "units":            UNKNOWN,
        "direction":        UNKNOWN,
        "update rate":      UNKNOWN,
        "if it is missing": UNKNOWN,
    },
    {
        "signal":           UNKNOWN,
        "units":            UNKNOWN,
        "direction":        UNKNOWN,
        "update rate":      UNKNOWN,
        "if it is missing": UNKNOWN,
    },
]

# 2. Two sentences, in your own words: why does positive exhaust pressure
#    NOT prove the engine can sustain itself?
WHY_POSITIVE_PRESSURE_IS_NOT_PROOF_1 = UNKNOWN
WHY_POSITIVE_PRESSURE_IS_NOT_PROOF_2 = UNKNOWN

# 3. For the power-balance sum. These are SYNTHETIC numbers you choose to
#    explore the arithmetic with. They are not predictions about our turbine
#    and must never be quoted as such.
MECHANICAL_EFFICIENCY = answer(
    value=0.98,
    units="(a ratio)",
    source="DP-2 assumption, repeated in docs/project/dp2-review.md",
    uncertainty="assumed, not measured",
    basis=CANDIDATE,
)
SYNTHETIC_TURBINE_POWER_KW = answer(
    value=UNKNOWN,             # e.g. 17.0 - a made-up number to test the sum
    units="kW",
    source="synthetic value chosen to exercise the arithmetic",
    uncertainty="not a prediction about any real turbine",
    basis=EXAMPLE,
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

COMPRESSOR_POWER_KW = 18.07    # repository screen result for the DP-2 point
DIRECTIONS = ("model -> controller", "controller -> model")


def lesson(ws):
    ws.heading("what you are actually building towards")
    ws.say("Pilots train in simulators because crashing a simulator is "
           "cheap. A plant model is a simulator for our engine: a piece of "
           "software that behaves enough like the real thing that a "
           "controller can be developed and tested against it long before "
           "anybody lights a match.")
    ws.say("For that to work, the model and the controller have to agree on "
           "what they are saying to each other. Not roughly - exactly. Same "
           "names, same units, same directions, same idea of what happens "
           "when a number does not arrive. Interfaces that were agreed by "
           "assumption rather than by conversation are where projects lose "
           "weeks.")
    ws.say("That conversation is today's task. Half an hour now, with C4, "
           "saves a fortnight in November.")

    ws.heading("the words you need")
    ws.terms([
        ("interface",
         "The agreed list of things that cross a boundary between two "
         "people's work. Name, units, direction, how often, and what happens "
         "if it is missing."),
        ("direction",
         "Who produces it and who consumes it. Shaft speed goes model to "
         "controller. A fuel demand goes controller to model. Writing the "
         "arrow down prevents both of you assuming the other owns it."),
        ("validity",
         "Whether a number should be believed. A signal that has stopped "
         "arriving is not the same as a signal that is zero, and a controller "
         "that treats them the same will eventually do something startling."),
        ("residual",
         "In a solver, how far from balanced something is. Zero means it "
         "balances. Our engine has two that matter: does the same amount of "
         "gas get through every component, and does the turbine produce what "
         "the compressor consumes."),
        ("self-sustaining",
         "The engine keeps running at a stable operating point without help. "
         "It needs all of: enough turbine power, components that pass "
         "compatible flows, combustion that stays lit, and losses small "
         "enough to live with."),
    ])

    ws.heading("the trap in this task, and it is the project's central one")
    ws.legend()
    ws.given("compressor power at the DP-2 point", COMPRESSOR_POWER_KW, "kW",
             REPO_CHECK, "docs/project/checks/dp2_screen.py")
    ws.given("turbine exit total pressure at the DP-2 point", 120.85, "kPa",
             REPO_CHECK, "above the 101.325 kPa ambient")
    ws.given("assumed mechanical efficiency", 0.98, "(ratio)", CANDIDATE)
    ws.blank()
    ws.say("Turbine exit pressure comes out above ambient. It is tempting to "
           "read that as 'the engine works'. The DP-2 review spends its first "
           "correction explaining why it is not, and the reason is worth "
           "understanding properly because it is the difference between a "
           "screening calculation and an engine.")
    ws.say("The screening calculation IMPOSES the power balance. It starts by "
           "saying 'the turbine produces exactly what the compressor needs' "
           "and works out what temperatures and pressures follow. It never "
           "asks whether a real turbine of that size, with that gas, at that "
           "speed, could actually produce it. The answer comes out consistent "
           "because it was assumed consistent.")
    ws.bullets([
        "A pressure check says: given that balance, there is pressure left at "
        "the exit.",
        "Self-sustain asks: can the balance be met at all, by real hardware, "
        "with real losses, at more than one speed?",
        "Those are different questions and only the first one has been "
        "answered.",
    ])
    ws.say("Positive exit pressure is necessary. It is nowhere near "
           "sufficient. Writing those two sentences yourself, in your own "
           "words, is the main deliverable on this card.")

    ws.heading("a worked example, so the arithmetic is not a mystery")
    ws.example([
        "The compressor needs 18.07 kW. The shaft is not perfectly efficient",
        "- bearings and seals take a cut - so the turbine has to produce more",
        "than the compressor consumes:",
        "",
        "  required turbine power = 18.07 / 0.98    = 18.44 kW",
        "",
        "Now suppose somebody hands you a synthetic figure of 17.0 kW for",
        "what a turbine might actually manage at some speed:",
        "",
        "  residual = 17.00 - 18.44                 = -1.44 kW",
        "",
        "Negative. At that operating point the shaft would slow down, and as",
        "it slowed the compressor would deliver less, and the turbine would",
        "produce less still. That is what failing to self-sustain looks like",
        "in arithmetic.",
        "",
        "The 17.0 kW is invented. Nobody knows our turbine's real number yet.",
        "Finding it out honestly, across a whole range of speeds, is the",
        "later work this card is the first step towards.",
    ])


def your_table(ws):
    ws.heading("your interface table")
    rows = []
    for item in SIGNALS:
        rows.append([
            str(item["signal"]) if has_value(item["signal"]) else "-",
            str(item["units"]) if has_value(item["units"]) else "-",
            str(item["direction"]) if has_value(item["direction"]) else "-",
            str(item["if it is missing"])
            if has_value(item["if it is missing"]) else "-",
        ])
    ws.table(["signal", "units", "direction", "if it is missing"], rows)

    notes = []
    for index, item in enumerate(SIGNALS, start=1):
        if not has_value(item["signal"]):
            continue
        direction = str(item["direction"]).strip().lower()
        if has_value(item["direction"]) and direction not in DIRECTIONS:
            notes.append("row {0}: direction should be one of '{1}' or '{2}'"
                         .format(index, DIRECTIONS[0], DIRECTIONS[1]))
        if not has_value(item["units"]):
            notes.append("row {0}: no units. A signal without units is an "
                         "argument waiting to happen".format(index))
        if not has_value(item["if it is missing"]):
            notes.append("row {0}: nothing written for what happens when this "
                         "signal does not arrive - that is the field that "
                         "matters most".format(index))
    if notes:
        ws.bullets(notes)
    elif any(has_value(item["signal"]) for item in SIGNALS):
        ws.bullets(["Nothing inconsistent in what you have entered so far."])
    else:
        ws.say("Nothing entered yet. Good candidates to start with: shaft "
               "speed, exhaust gas temperature, fuel demand, a run/stop "
               "request, and one health or validity flag.")


def your_calculation(ws):
    ws.heading("now do the power balance yourself")
    required = ws.compute(
        "turbine power the compressor requires",
        lambda eta: COMPRESSOR_POWER_KW / eta,
        {"mechanical efficiency": MECHANICAL_EFFICIENCY},
        units="kW",
    )
    if required is not None:
        residual = ws.compute(
            "residual: synthetic turbine power minus what is required",
            lambda turbine, need: turbine - need,
            {"synthetic turbine power (kW)": SYNTHETIC_TURBINE_POWER_KW,
             "required turbine power (kW)": required},
            units="kW",
            comment="Positive means the shaft would speed up at this point. "
                    "Negative means it would slow down. Zero is the balance a "
                    "real solver hunts for at every speed - not just at one.",
        )
        if residual is not None:
            ws.say("Remember what that number is and is not. It used a "
                   "synthetic turbine power that you invented to exercise the "
                   "arithmetic. It says nothing whatsoever about our turbine, "
                   "and it must not be quoted outside this worksheet as though "
                   "it did.")


def main():
    ws = Worksheet(
        code="C5",
        title="Agree the model-to-controller interface",
        card="workspaces/combustion-systems/C5-model-interface.md",
        review_role="Combustion & Systems lead",
    )
    ws.header(safety_line="Desk work only today. Synthetic numbers, paper and "
                          "conversation. No hardware, no fuel, no hazardous "
                          "material of any kind is involved in this task.")
    lesson(ws)
    your_table(ws)
    your_calculation(ws)

    ws.heading("what finishing looks like")
    ws.bullets([
        "Five rows, agreed with C4, using synthetic values only.",
        "Two sentences in your own words on why positive exhaust pressure "
        "does not prove self-sustain.",
        "One row in the shared interface register that you and C4 both own - "
        "workspaces/coordination/interfaces.md, not two rows.",
    ])
    ws.say("Not today: building a nonlinear off-design solver, tuning a "
           "governor, or accepting any startup performance number. Those need "
           "a compressor map, turbine geometry and a pressure-loss budget "
           "that nobody has yet, plus mentoring. Today is the interface.")

    ws.record("mechanical efficiency used", MECHANICAL_EFFICIENCY)
    ws.record("synthetic turbine power used", SYNTHETIC_TURBINE_POWER_KW)

    ws.submission(date=DATE, learned=WHAT_I_LEARNED, unknown=STILL_UNKNOWN,
                  question=QUESTION_FOR_LEAD, next_step=NEXT_SMALL_STEP)
    ws.done_when([
        ("signal 1 named", SIGNALS[0]["signal"]),
        ("signal 2 named", SIGNALS[1]["signal"]),
        ("signal 3 named", SIGNALS[2]["signal"]),
        ("signal 4 named", SIGNALS[3]["signal"]),
        ("signal 5 named", SIGNALS[4]["signal"]),
        ("why positive pressure is not proof, sentence 1",
         WHY_POSITIVE_PRESSURE_IS_NOT_PROOF_1),
        ("why positive pressure is not proof, sentence 2",
         WHY_POSITIVE_PRESSURE_IS_NOT_PROOF_2),
        ("one question for the lead", QUESTION_FOR_LEAD),
    ])
    ws.finish()


if __name__ == "__main__":
    main()
