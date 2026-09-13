"""T1 - Find the exact compressor and its map.  CORE first-meeting worksheet.

WHAT THIS IS
  A 30-45 minute guided activity. You do not need to know Python or turbine
  engines. You will read a compressor map, write down which exact part we are
  talking about, and do one small unit conversion that catches a real mistake.

HOW TO USE IT
  1. Run it once and read what it prints:   python t1_compressor_map.py
  2. Edit the block below marked YOUR ANSWERS. Nothing else.
  3. Save the file and run it again. It will tell you what is still missing.
  4. Copy the block it prints at the end to your lead, your card, or the
     first-meeting finding issue.

  No Python today? Run  python t1_compressor_map.py --form  on any machine
  that has it, or read HOW-TO-RUN.md for the paper route.

WHAT THIS IS NOT
  It does not import the engine model and cannot change any design value.
"""

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
for _folder in (_HERE, _HERE.parent):
    if str(_folder) not in sys.path:
        sys.path.insert(0, str(_folder))
try:
    from worksheet_common import (CANDIDATE, EXAMPLE, NOT_FOUND, REPO_CHECK,
                                  SOURCE, UNKNOWN, Worksheet, answer)
except ImportError:
    print("Could not find worksheet_common.py.")
    print("Keep this file in its team folder next to the other worksheets,")
    print("or use the starter bundle. See workspaces/python/HOW-TO-RUN.md.")
    raise SystemExit(1)


# ===========================================================================
#  YOUR ANSWERS - this is the only part of the file you need to edit.
#  Leave anything you could not find as UNKNOWN, or write NOT_FOUND if you
#  looked and it genuinely is not published. Do not invent a number.
# ===========================================================================

DATE = UNKNOWN                 # e.g. "2026-09-17"

# 1. Which exact compressor are we talking about?
#    A wheel diameter is not a part number. Two wheels can measure the same
#    and behave differently.
EXACT_PART = answer(
    value=UNKNOWN,             # e.g. "Garrett GT3076R, part number 700177-5011"
    source=UNKNOWN,            # the catalogue page or PDF you read
    uncertainty=UNKNOWN,       # e.g. "billet copies exist under several names"
)

# 2. The map you found for it.
MAP_SOURCE = answer(
    value=UNKNOWN,             # e.g. "Garrett performance catalogue, GT3076R map, p.12"
    source=UNKNOWN,            # link or file name
)

# 3. What are the three things on the map?  Write them in your own words,
#    with units, after you have found them on the picture.
MAP_X_AXIS = UNKNOWN           # e.g. "corrected air flow, lb/min"
MAP_Y_AXIS = UNKNOWN           # e.g. "pressure ratio, no units"
MAP_CURVED_LINES = UNKNOWN     # e.g. "constant corrected shaft speed, rpm"

# 4. The map's own reference conditions. Every map is drawn for a stated
#    inlet temperature and pressure. If the map does not say, write NOT_FOUND.
MAP_REF_TEMPERATURE_K = answer(
    value=UNKNOWN,             # e.g. 288.15
    units="K",
    source=UNKNOWN,
)
MAP_REF_PRESSURE_KPA = answer(
    value=UNKNOWN,             # e.g. 101.325
    units="kPa",
    source=UNKNOWN,
)

# 5. The wheel's maximum or rated shaft speed, from the map or datasheet.
RATED_SPEED_RPM = answer(
    value=UNKNOWN,             # e.g. 120000
    units="rpm",
    source=UNKNOWN,
    uncertainty=UNKNOWN,
)

# 6. Efficiency at the DP-2 point, read off the map. Read the island you land
#    in; do not interpolate heroically. If the point falls off the map, that
#    is an important finding: write NOT_FOUND and say so below.
EFFICIENCY_AT_DP2_POINT = answer(
    value=UNKNOWN,             # e.g. 0.68
    units="(a ratio, no units)",
    source=UNKNOWN,
    uncertainty=UNKNOWN,       # e.g. "read between the 0.66 and 0.70 islands"
)

# 7. Your writing.
WHAT_I_LEARNED = [
    UNKNOWN,                   # sentence 1
    UNKNOWN,                   # sentence 2
    UNKNOWN,                   # sentence 3
]
STILL_UNKNOWN = UNKNOWN
QUESTION_FOR_LEAD = UNKNOWN
NEXT_SMALL_STEP = UNKNOWN

# ===========================================================================
#  END OF YOUR ANSWERS. You can read on, but you do not need to change it.
# ===========================================================================


def lesson(ws):
    ws.heading("what a compressor does, in plain language")
    ws.say("Hold your hand out of a car window at speed and you feel the air "
           "push. Now imagine catching that air in a cup instead of letting it "
           "past. The air piles up and its pressure rises. A compressor does "
           "that on purpose, continuously.")
    ws.say("Ours is a centrifugal compressor: a wheel with curved blades spins "
           "very fast, flings air outwards the way water flies off a spinning "
           "bicycle wheel, and throws it into a wider passage where the air "
           "slows down. Air that slows down in a widening passage gains "
           "pressure. Speed in, pressure out.")
    ws.say("This costs power. Something has to turn that wheel, and in a jet "
           "engine that something is the turbine at the far end, connected by "
           "one shaft. If the turbine cannot supply what the compressor "
           "demands, the engine slows down and stops. That is why your task "
           "sits at the front of everybody else's.")

    ws.heading("the five words you need")
    ws.terms([
        ("pressure ratio",
         "Outlet pressure divided by inlet pressure. No units. DP-2 proposes "
         "about 1.63, meaning the air leaves at roughly 1.63 times the "
         "pressure it came in at."),
        ("mass flow",
         "How many kilograms of air pass every second. Written kg/s. Not the "
         "same as volume: hot air and cold air of the same volume weigh "
         "different amounts."),
        ("compressor map",
         "A picture of everything one particular wheel can do. Flow along the "
         "bottom, pressure ratio up the side, curved lines for shaft speed, "
         "and closed loops - 'islands' - showing efficiency."),
        ("surge and choke",
         "The left and right walls of the map. Surge is flow breaking down and "
         "reversing, violently. Choke is the passage running out of capacity. "
         "You want to sit well away from both."),
        ("corrected flow",
         "Flow rescaled to the map's stated reference temperature and "
         "pressure, so that one map works on a cold morning and a hot "
         "afternoon. Plotting raw kg/s on a corrected axis is a real and "
         "common mistake."),
    ])

    ws.heading("the numbers the project already has")
    ws.say("These are DP-2 proposals under review. They are not approved "
           "operating values, and your job today is not to confirm them.")
    ws.legend()
    ws.given("shaft speed", 66000, "rpm", CANDIDATE)
    ws.given("air mass flow", 0.30, "kg/s", CANDIDATE)
    ws.given("compressor pressure ratio", 1.63, "(ratio)", CANDIDATE)
    ws.given("exducer / inducer diameter", "76.13 / 57.04", "mm", CANDIDATE)
    ws.given("assumed compressor efficiency", 0.72, "(ratio)", CANDIDATE,
             "an assumption in DP-2, not a value read off any map")
    ws.given("mass flow in lb/min, plain conversion", 39.683, "lb/min",
             REPO_CHECK, "docs/project/checks/dp2_screen.py")
    ws.blank()
    ws.say("Read the short candidate table in docs/project/dp2-review.md "
           "before you start. It also explains why a billet wheel of the same "
           "diameter does not automatically inherit a cast wheel's published "
           "map: different blade shape, different surface, different supplier, "
           "different measured behaviour.")

    ws.heading("the one trap in this task")
    ws.say("A compressor map's flow axis is almost always CORRECTED flow. "
           "Converting 0.30 kg/s straight into lb/min gives 39.683 lb/min, and "
           "that number is correct as a unit conversion and wrong as a map "
           "coordinate. The correction rescales flow by the square root of "
           "temperature and divides by pressure, both measured against the "
           "map's own reference conditions.")
    ws.say("The formula, with T and P as the total conditions at the "
           "compressor inlet:")
    ws.bullets([
        "theta = inlet total temperature / map reference temperature",
        "delta = inlet total pressure / map reference pressure",
        "corrected flow = actual flow * sqrt(theta) / delta",
    ])
    ws.example([
        "Suppose the map is drawn for 288.15 K and 101.325 kPa, and on the",
        "day we run, the air entering the wheel is at 288.15 K and 100.31 kPa",
        "(sea-level air, minus a small inlet loss).",
        "",
        "  theta = 288.15 / 288.15                = 1.0000",
        "  delta = 100.31 / 101.325               = 0.9900",
        "  corrected flow = 0.30 * 1.0000 / 0.9900 = 0.30303 kg/s",
        "                                          = 40.08 lb/min",
        "",
        "So 39.68 lb/min and 40.08 lb/min are different points on the map.",
        "Only about 1 percent apart here - but on a hot day, or in a lab at",
        "altitude, the gap grows quickly. And if the map turns out to use a",
        "different reference condition, the gap can be much larger than this.",
    ])


def your_calculation(ws):
    ws.heading("now do it with the map you actually found")
    ws.say("This will stay blank until you have filled in the map's reference "
           "conditions above. That is the point: the correction cannot be done "
           "without them, so a map that does not state them is itself a "
           "finding worth reporting.")

    inlet_total_T = 288.15      # CANDIDATE: standard day used throughout DP-2
    inlet_total_P = 101.325 * 0.99   # CANDIDATE: ambient x 0.99 inlet recovery
    ws.given("inlet total temperature used here", inlet_total_T, "K", CANDIDATE)
    ws.given("inlet total pressure used here", inlet_total_P, "kPa", CANDIDATE,
             "101.325 kPa ambient with the 0.99 inlet recovery DP-2 assumes")
    ws.blank()

    theta = ws.compute(
        "theta (temperature ratio)",
        lambda ref: inlet_total_T / ref,
        {"map reference temperature (K)": MAP_REF_TEMPERATURE_K},
    )
    delta = ws.compute(
        "delta (pressure ratio)",
        lambda ref: inlet_total_P / ref,
        {"map reference pressure (kPa)": MAP_REF_PRESSURE_KPA},
    )
    if theta is not None and delta is not None:
        ws.compute(
            "corrected mass flow",
            lambda t, d: 0.30 * (t ** 0.5) / d,
            {"theta": theta, "delta": delta},
            units="kg/s",
            comment="Multiply by 132.277 to get lb/min, which is what most "
                    "turbocharger maps use.",
        )
        ws.compute(
            "corrected mass flow in map units",
            lambda t, d: 0.30 * (t ** 0.5) / d * 60 / 0.45359237,
            {"theta": theta, "delta": delta},
            units="lb/min",
            comment="This is the x-coordinate to plot. Compare it with the "
                    "39.683 lb/min plain conversion above and say in your "
                    "notes whether the difference matters here.",
        )

    ws.compute(
        "DP-2 speed as a fraction of the wheel's rated speed",
        lambda rated: 100.0 * 66000.0 / rated,
        {"rated speed (rpm)": RATED_SPEED_RPM},
        units="percent",
        comment="Published maps often stop at 40-50 percent speed. If 66,000 "
                "rpm is far down the map, say so - and note that DP-2's "
                "estimated idle near 30,100 rpm may be off the map entirely. "
                "That is a useful finding, not a failure.",
    )


def main():
    ws = Worksheet(
        code="T1",
        title="Find the exact compressor and its map",
        card="workspaces/turbomachinery/T1-compressor.md",
        review_role="Turbomachinery lead",
    )
    ws.header()
    lesson(ws)
    your_calculation(ws)

    ws.heading("what finishing looks like")
    ws.bullets([
        "A link or reference to one real compressor map.",
        "Three rows: the exact part, the map's reference conditions, and one "
        "question you could not answer.",
        "An honest NOT FOUND anywhere the information is not published.",
    ])
    ws.say("Not today: matching the map to our engine, judging surge or choke "
           "margin, running CFD, or confirming that 66,000 rpm is a good "
           "operating point. Those need the lead and later evidence. Today you "
           "are finding out what we are actually holding.")

    ws.record("exact compressor part", EXACT_PART)
    ws.record("map source", MAP_SOURCE)
    ws.record("map reference temperature", MAP_REF_TEMPERATURE_K)
    ws.record("map reference pressure", MAP_REF_PRESSURE_KPA)
    ws.record("rated shaft speed", RATED_SPEED_RPM)
    ws.record("efficiency read at the DP-2 point", EFFICIENCY_AT_DP2_POINT)

    ws.submission(date=DATE, learned=WHAT_I_LEARNED, unknown=STILL_UNKNOWN,
                  question=QUESTION_FOR_LEAD, next_step=NEXT_SMALL_STEP)
    ws.done_when([
        ("exact part number, or NOT FOUND", EXACT_PART),
        ("a map source you can link to", MAP_SOURCE),
        ("what the map's bottom axis shows", MAP_X_AXIS),
        ("what the map's side axis shows", MAP_Y_AXIS),
        ("what the curved lines show", MAP_CURVED_LINES),
        ("map reference temperature", MAP_REF_TEMPERATURE_K),
        ("map reference pressure", MAP_REF_PRESSURE_KPA),
        ("efficiency at the DP-2 point", EFFICIENCY_AT_DP2_POINT),
        ("one question for the lead", QUESTION_FOR_LEAD),
    ])
    ws.finish()


if __name__ == "__main__":
    main()
