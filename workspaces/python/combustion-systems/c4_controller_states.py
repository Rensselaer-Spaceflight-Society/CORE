"""C4 - Describe controller states on paper.  CORE first-meeting worksheet.

WHAT THIS IS
  A 30-45 minute guided activity. You will describe, in words, the states a
  controller would move through, and what evidence each move would need. Then
  one small calculation shows why some failures cannot be caught by a
  temperature sensor at all.

HOW TO USE IT
  1. Run it once and read what it prints:   python c4_controller_states.py
  2. Edit the block below marked YOUR ANSWERS. Nothing else.
  3. Save, run again, hand the printed block to your lead.

WHAT THIS IS NOT
  ** This file contains no control logic. ** There is no state machine here,
  no timer, no output, and nothing that could be connected to fuel, ignition,
  a starter or a rotor. It prints a table you wrote and does one piece of
  arithmetic. Trip thresholds are Safety's decision and stay TBD today.
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

# 1. The five states. For each one, say in plain words what it means, and
#    what would have to be TRUE before the controller is allowed to leave it.
#
#    Leave every speed, temperature and timer value as "TBD". Not because
#    numbers are hard, but because those numbers are Safety's decision and
#    they come from burst margin and material limits nobody has yet.
STATES = [
    {
        "state":              "OFF",
        "what it means":      UNKNOWN,   # e.g. "nothing is powered, fuel is shut"
        "evidence to leave":  UNKNOWN,   # e.g. "an operator asks for a start"
        "threshold":          "TBD",
    },
    {
        "state":              "CHECKS",
        "what it means":      UNKNOWN,
        "evidence to leave":  UNKNOWN,
        "threshold":          "TBD",
    },
    {
        "state":              "STARTING",
        "what it means":      UNKNOWN,
        "evidence to leave":  UNKNOWN,
        "threshold":          "TBD",
    },
    {
        "state":              "RUNNING",
        "what it means":      UNKNOWN,
        "evidence to leave":  UNKNOWN,
        "threshold":          "TBD",
    },
    {
        "state":              "FAULT",
        "what it means":      UNKNOWN,
        "evidence to leave":  UNKNOWN,
        "threshold":          "TBD",
    },
]

# 2. Two questions about what happens when a sensor fails. Not "what if it
#    breaks" - be specific. A sensor that reads a plausible but wrong number
#    is far more dangerous than one that reads nothing at all.
SENSOR_FAILURE_QUESTION_1 = UNKNOWN
SENSOR_FAILURE_QUESTION_2 = UNKNOWN

# 3. For the lag calculation. These are numbers you choose to explore with.
SENSOR_TIME_CONSTANT_S = answer(
    value=UNKNOWN,             # e.g. 5 - a sheathed thermocouple is slow
    units="s",
    source=UNKNOWN,            # a datasheet, if you can find one
    uncertainty=UNKNOWN,
)
HOW_FAST_THE_EVENT_IS_S = answer(
    value=UNKNOWN,             # e.g. 1 - some failures develop in under a second
    units="s",
    source="a duration I chose to explore",
    basis=EXAMPLE,
)
SIZE_OF_THE_REAL_EXCURSION_K = answer(
    value=UNKNOWN,             # e.g. 400 - how far the real gas temperature moves
    units="K",
    source="a size I chose to explore",
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


def lesson(ws):
    ws.heading("what a controller is, in plain language")
    ws.say("Think of somebody very careful lighting an old gas boiler. They "
           "check the room, open the gas a little, light it, watch for a "
           "flame, and if the flame does not appear within a few seconds they "
           "shut the gas off and start again. They never open the gas wide "
           "and hope.")
    ws.say("An engine controller is that person, written down, and running a "
           "thousand times a second. The important part is not the running - "
           "it is the checking, and the willingness to stop.")
    ws.say("A controller lives in one state at a time. It leaves a state only "
           "when it has evidence it is allowed to. Your job today is to write "
           "down those states and, for each move between them, what evidence "
           "would justify it. Not the numbers. The evidence.")

    ws.heading("the words you need")
    ws.terms([
        ("state",
         "One situation the controller can be in. OFF, CHECKS, STARTING, "
         "RUNNING, FAULT. At any moment it is in exactly one."),
        ("transition",
         "A move from one state to another, and the condition that allows it. "
         "Every transition should have a reason you can say out loud."),
        ("permissive",
         "A condition that must be true before something is allowed to happen. "
         "'The shutoff valve reports closed' is a permissive."),
        ("abort",
         "A planned, safe way to give up. Good controllers have several, each "
         "with a clear trigger. An abort branch that was never designed is a "
         "branch that will be improvised at the worst possible moment."),
        ("time constant",
         "How slowly a sensor catches up with reality. A sensor with a time "
         "constant of 5 seconds has seen only about two thirds of a sudden "
         "change after 5 seconds. See the calculation below - this is the "
         "single most important idea on this card."),
    ])

    ws.heading("the trap in this task, and it is the important one")
    ws.say("Some failures develop faster than a temperature sensor can "
           "possibly see them. That is not a sensor quality problem you can "
           "buy your way out of - a probe sturdy enough to survive in the "
           "exhaust is necessarily slow, because it has a metal sheath that "
           "has to heat up first.")
    ws.say("The consequence is a design rule, and it belongs in the first "
           "sentence of any controller specification for this engine: fast "
           "failures are caught by TIMERS, not by temperature. If a thing was "
           "supposed to happen within a certain time and it did not, stop - "
           "do not wait to see the temperature confirm it.")
    ws.example([
        "A sheathed thermocouple with a time constant of 5 seconds. The real",
        "gas temperature jumps 400 K in a failure that develops in 1 second.",
        "",
        "How much of that jump has the sensor seen after 1 second?",
        "",
        "  fraction seen = 1 - e^(-t / time constant)",
        "                = 1 - e^(-1 / 5)",
        "                = 1 - 0.8187              = 0.1813",
        "",
        "  what it reads = 0.1813 * 400 K          = 72.5 K above normal",
        "",
        "So a 400 K excursion looks like a 72 K wobble. If somebody sets an",
        "over-temperature trip at, say, 100 K above normal, it does not fire",
        "at all, and the engine keeps going while the real temperature is",
        "four hundred degrees high.",
        "",
        "The same sensor needs about 11.5 seconds to show 90 percent of the",
        "jump - that is the time constant times ln(10). By then it is over.",
        "",
        "The numbers above are illustrative. The design rule they demonstrate",
        "is not.",
    ])
    ws.blank()
    ws.say("Everything that follows in your table - every abort branch, every "
           "timeout - exists because of that idea. Write it in your own words "
           "in your findings; it is the thing your lead most wants to see you "
           "understand.")


def your_states(ws):
    ws.heading("your state table")
    rows = []
    for item in STATES:
        rows.append([
            item["state"],
            str(item["what it means"]) if has_value(item["what it means"]) else "-",
            str(item["evidence to leave"])
            if has_value(item["evidence to leave"]) else "-",
        ])
    ws.table(["state", "what it means", "evidence needed to leave it"], rows)

    notes = []
    for item in STATES:
        if as_number(item["threshold"]) is not None:
            notes.append(
                "{0}: a number has appeared in the threshold column. Trip "
                "thresholds are the Safety lead's decision and they come from "
                "burst margin and material limits that do not exist yet. Put "
                "it back to TBD and raise the number as a question instead."
                .format(item["state"]))
    if notes:
        ws.bullets(notes)
    if not any(has_value(item["what it means"]) for item in STATES):
        ws.say("Nothing written yet. Start with OFF - it is the easiest, and "
               "getting 'what has to be true before we leave OFF' right is "
               "most of the safety case.")


def your_calculation(ws):
    ws.heading("now do the lag arithmetic yourself")
    fraction = ws.compute(
        "fraction of a sudden change the sensor has seen",
        lambda tau, t: 1.0 - math.exp(-t / tau),
        {"sensor time constant (s)": SENSOR_TIME_CONSTANT_S,
         "how long the event takes (s)": HOW_FAST_THE_EVENT_IS_S},
        comment="A fraction, so 0.18 means 18 percent of the real change.",
    )
    if fraction is not None:
        ws.compute(
            "what the sensor actually reads",
            lambda f, real: f * real,
            {"fraction seen": fraction,
             "size of the real excursion (K)": SIZE_OF_THE_REAL_EXCURSION_K},
            units="K above normal",
            comment="Compare this with the real excursion you entered. The "
                    "gap between them is the argument for timers.",
        )
    ws.compute(
        "time for the sensor to show 90 percent of a change",
        lambda tau: tau * math.log(10.0),
        {"sensor time constant (s)": SENSOR_TIME_CONSTANT_S},
        units="s",
        comment="Now ask yourself: is the engine still there in that many "
                "seconds? That question, written down, is a good half of your "
                "deliverable.",
    )


def main():
    ws = Worksheet(
        code="C4",
        title="Describe controller states on paper",
        card="workspaces/combustion-systems/C4-controls.md",
        review_role="Combustion & Systems lead; Safety lead reviews fault concepts",
    )
    ws.header(safety_line="Paper and pencil only today. No firmware, no "
                          "hardware outputs, no fuel, no ignition, no starter, "
                          "no live actuator.")
    lesson(ws)
    your_states(ws)
    your_calculation(ws)

    ws.heading("what finishing looks like")
    ws.bullets([
        "One state sketch: five boxes, arrows between them, a word on each "
        "arrow saying what evidence allows it.",
        "Every speed, temperature and timer left as TBD.",
        "Two specific sensor-failure questions.",
    ])
    ws.say("Not today: writing firmware, connecting anything to a fuel or "
           "ignition output, or copying thresholds out of a production "
           "engine's manual. The DP-2 review is explicit that the estimated "
           "idle speed near 30,100 rpm is a hypothesis rather than a setpoint, "
           "and that published thresholds from other engines describe other "
           "engines. Agree signal names and units with C5 before either of "
           "you designs anything around them.")

    ws.record("sensor time constant used", SENSOR_TIME_CONSTANT_S)
    ws.record("event duration explored", HOW_FAST_THE_EVENT_IS_S)
    ws.record("size of excursion explored", SIZE_OF_THE_REAL_EXCURSION_K)

    ws.submission(date=DATE, learned=WHAT_I_LEARNED, unknown=STILL_UNKNOWN,
                  question=QUESTION_FOR_LEAD, next_step=NEXT_SMALL_STEP)
    ws.done_when([
        ("OFF described", STATES[0]["what it means"]),
        ("CHECKS described", STATES[1]["what it means"]),
        ("STARTING described", STATES[2]["what it means"]),
        ("RUNNING described", STATES[3]["what it means"]),
        ("FAULT described", STATES[4]["what it means"]),
        ("sensor-failure question 1", SENSOR_FAILURE_QUESTION_1),
        ("sensor-failure question 2", SENSOR_FAILURE_QUESTION_2),
        ("one question for the lead", QUESTION_FOR_LEAD),
    ])
    ws.finish()


if __name__ == "__main__":
    main()
