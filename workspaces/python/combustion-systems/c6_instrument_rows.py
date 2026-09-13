"""C6 - Compare three measurement needs.  CORE first-meeting worksheet.

WHAT THIS IS
  A 30-45 minute guided activity. You will build three rows - speed,
  temperature, pressure - saying what has to be measured, over what range,
  how fast, and where you found out. Then three small calculations show why
  each of those three is harder than it looks.

HOW TO USE IT
  1. Run it once and read what it prints:   python c6_instrument_rows.py
  2. Edit the block below marked YOUR ANSWERS. Nothing else.
  3. Save, run again, hand the printed block to your lead.

WHAT THIS IS NOT
  No magnet is attached to anything, no probe is heated, no calibration is
  claimed. Nothing is wired up today.
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

# 1. Three rows. Mark anything you could not find as NOT_FOUND - that is a
#    real answer and it tells the lead where the gaps are.
MEASUREMENT_ROWS = [
    {
        "what":            "shaft speed",
        "units":           UNKNOWN,   # e.g. "rpm"
        "candidate range": UNKNOWN,   # e.g. "0 to 70000"
        "how fast must it respond": UNKNOWN,   # your question, or a number
        "source":          UNKNOWN,   # where you looked
    },
    {
        "what":            "exhaust gas temperature",
        "units":           UNKNOWN,   # e.g. "K"
        "candidate range": UNKNOWN,
        "how fast must it respond": UNKNOWN,
        "source":          UNKNOWN,
    },
    {
        "what":            "compressor delivery pressure",
        "units":           UNKNOWN,   # careful: psia or psig? say which
        "candidate range": UNKNOWN,
        "how fast must it respond": UNKNOWN,
        "source":          UNKNOWN,
    },
]

# 2. For the speed calculation: how many pulses would your sensor produce per
#    turn of the shaft? One magnet on the shaft gives one.
PULSES_PER_REVOLUTION = answer(
    value=UNKNOWN,             # e.g. 1
    units="pulses per rev",
    source="the sensing arrangement I am assuming",
    basis=EXAMPLE,
)

# 3. For the temperature calculation: the maximum temperature of a probe you
#    found in a catalogue, and its response time if it is published.
PROBE_MAXIMUM_TEMPERATURE_K = answer(
    value=UNKNOWN,             # e.g. 1199
    units="K",
    source=UNKNOWN,            # the catalogue page
    uncertainty=UNKNOWN,
)
PROBE_RESPONSE_TIME_S = answer(
    value=UNKNOWN,             # e.g. 0.6, or NOT_FOUND
    units="s",
    source=UNKNOWN,
    uncertainty=UNKNOWN,       # under what conditions was it measured?
)

# 4. For the pressure calculation: two sensor ranges to compare, and how many
#    bits the converter has.
SENSOR_RANGE_A_PSI = answer(
    value=UNKNOWN,             # e.g. 100
    units="psi full scale",
    source=UNKNOWN,
)
SENSOR_RANGE_B_PSI = answer(
    value=UNKNOWN,             # e.g. 30
    units="psi full scale",
    source=UNKNOWN,
)
CONVERTER_BITS = answer(
    value=UNKNOWN,             # e.g. 12
    units="bits",
    source=UNKNOWN,
)

# 5. In your own words: what is the difference between accuracy and
#    resolution, and between psia and psig?
ACCURACY_VS_RESOLUTION = UNKNOWN
PSIA_VS_PSIG = UNKNOWN

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

SHAFT_RPM = 66000.0            # DP-2 candidate maximum
T5_SCREEN_K = 1099.17          # repository screen turbine exit temperature
T5_NOTE_K = 1096.0             # the DP-2 note's figure for the same thing
P3_KPA = 163.51                # repository screen combustor inlet pressure
KPA_PER_PSI = 6.894757
ATMOSPHERE_PSI = 14.6959
BOARD_SAMPLES_PER_SECOND = 860.0   # a commonly cited low-cost ADC board figure


def lesson(ws):
    ws.heading("why this matters more than it sounds")
    ws.say("An engine you cannot measure is an expensive noise source. If the "
           "goal is to find out whether this thing can keep itself running, "
           "then the data from the first runs IS the result. Everything else "
           "is preparation for collecting it.")
    ws.say("Three quantities do most of the work: how fast the shaft is "
           "turning, how hot the gas leaving the turbine is, and what pressure "
           "the compressor is delivering. Each one is a different kind of hard, "
           "and today you are going to find out how.")

    ws.heading("the words you need")
    ws.terms([
        ("range",
         "The span a sensor can read at all. Outside it, the reading is not "
         "wrong - it is meaningless."),
        ("resolution",
         "The smallest change the system can show. Set by the sensor's range "
         "divided by how many steps the converter has."),
        ("accuracy",
         "How close the reading is to the truth. Completely different from "
         "resolution: a sensor can display four decimal places and still be "
         "fifty degrees out. Resolution is how finely it lies to you."),
        ("psia and psig",
         "Absolute and gauge. Gauge reads zero in open air; absolute reads "
         "about 14.7 psi there. Mixing them up costs you one atmosphere, "
         "every time, silently."),
        ("response time",
         "How long a sensor takes to catch up with a change. A temperature "
         "probe tough enough to live in an exhaust is necessarily slow, "
         "because its protective sheath has to heat up first."),
    ])

    ws.heading("the numbers the project already has")
    ws.legend()
    ws.given("candidate maximum shaft speed", SHAFT_RPM, "rpm", CANDIDATE)
    ws.given("turbine exit temperature, repository screen", T5_SCREEN_K, "K",
             REPO_CHECK, "docs/project/dp2-review.md")
    ws.given("turbine exit temperature, DP-2 note", T5_NOTE_K, "K", CANDIDATE,
             "the note and the screen differ by about 3 K - say which you used")
    ws.given("combustor inlet pressure P3", P3_KPA, "kPa", REPO_CHECK)
    ws.given("P3 expressed in psi absolute", P3_KPA / KPA_PER_PSI, "psia",
             REPO_CHECK, "163.51 kPa divided by 6.894757")
    ws.blank()

    ws.heading("three traps, one per row")
    ws.example([
        "SPEED. One magnet on the shaft, one pulse per turn:",
        "",
        "  66000 rpm / 60                        = 1100 pulses per second",
        "",
        "1100 Hz is electronically easy - a counter handles it without",
        "effort. But people sometimes reach for a general-purpose analogue-",
        "to-digital board instead. A commonly cited low-cost board manages",
        "860 samples per second IN TOTAL, shared between its channels. To",
        "reconstruct a 1100 Hz signal you need more than 2200 samples per",
        "second on that channel alone. It is not close, and sharing four",
        "channels makes it ten times worse. Use a digital counter for speed.",
        "",
        "TEMPERATURE. DP-2 puts turbine exit temperature around 1099 K. If a",
        "probe is rated to 1199 K:",
        "",
        "  1199 - 1099                           = 100 K of headroom",
        "",
        "That is the headroom at the DESIGN point, on a good day. An",
        "over-temperature event is exactly the thing you most want to",
        "measure, and it is exactly the thing that goes off the top of the",
        "scale. And the DP-2 review notes this got harder, not easier: the",
        "lower pressure ratio means less expansion through the turbine, so",
        "the gas leaves hotter than the earlier design point predicted.",
        "",
        "PRESSURE. P3 is about 23.7 psi absolute, which is about 9 psi on a",
        "gauge. Put that on a 0-100 psi sensor read by a 12-bit converter:",
        "",
        "  steps available = 2^12                = 4096",
        "  resolution      = 100 / 4096          = 0.0244 psi per step",
        "",
        "  on a 0-30 psi sensor instead:",
        "  resolution      = 30 / 4096           = 0.0073 psi per step",
        "",
        "Over three times finer, for a signal that never goes near 100 psi.",
        "Choosing a range four times too big throws away three quarters of",
        "your resolution before the first measurement.",
        "",
        "Every catalogue figure above is an example. Find your own and cite",
        "it.",
    ])


def your_calculation(ws):
    ws.heading("now do it with the parts you found")
    ws.compute(
        "pulse frequency at maximum shaft speed",
        lambda pulses: SHAFT_RPM / 60.0 * pulses,
        {"pulses per revolution": PULSES_PER_REVOLUTION},
        units="Hz",
        comment="Then ask: is a counter or a sampled converter the right tool "
                "for this? Your answer, with a reason, is a good finding.",
    )
    ws.compute(
        "samples per second per channel if four channels share the board",
        lambda: BOARD_SAMPLES_PER_SECOND / 4.0,
        {},
        units="samples/s",
        comment="Compare with the pulse frequency above. This is why the "
                "budget review says a shared converter is not a speed counter.",
    )
    ws.compute(
        "temperature headroom above the screen value at the design point",
        lambda probe_max: probe_max - T5_SCREEN_K,
        {"probe maximum temperature (K)": PROBE_MAXIMUM_TEMPERATURE_K},
        units="K",
        comment="Headroom at the design point is not headroom during an "
                "excursion. Say in your notes how much margin you think is "
                "needed and why - that is the real deliverable here.",
    )
    resolution_a = ws.compute(
        "resolution of sensor A",
        lambda full_scale, bits: full_scale / (2.0 ** bits),
        {"sensor A full scale (psi)": SENSOR_RANGE_A_PSI,
         "converter bits": CONVERTER_BITS},
        units="psi per step",
    )
    resolution_b = ws.compute(
        "resolution of sensor B",
        lambda full_scale, bits: full_scale / (2.0 ** bits),
        {"sensor B full scale (psi)": SENSOR_RANGE_B_PSI,
         "converter bits": CONVERTER_BITS},
        units="psi per step",
    )
    if resolution_a is not None and resolution_b is not None:
        ws.compute(
            "how many times finer sensor B reads",
            lambda a, b: a / b,
            {"resolution A": resolution_a, "resolution B": resolution_b},
            units="times",
            comment="Resolution only. It says nothing about accuracy, and a "
                    "finer sensor that is badly calibrated is still wrong.",
        )
    ws.compute(
        "P3 expressed as a gauge pressure",
        lambda: P3_KPA / KPA_PER_PSI - ATMOSPHERE_PSI,
        {},
        units="psig",
        comment="The same pressure, 14.7 psi lower, because gauge sensors "
                "read zero in open air. Always write which one you mean.",
    )


def your_rows(ws):
    ws.heading("your three rows")
    rows = []
    for item in MEASUREMENT_ROWS:
        rows.append([
            item["what"],
            str(item["units"]) if has_value(item["units"]) else "-",
            str(item["candidate range"])
            if has_value(item["candidate range"]) else "-",
            str(item["source"]) if has_value(item["source"]) else "-",
        ])
    ws.table(["what to measure", "units", "candidate range", "source"], rows)

    notes = []
    for item in MEASUREMENT_ROWS:
        if has_value(item["candidate range"]) and not has_value(item["units"]):
            notes.append("{0}: a range without units".format(item["what"]))
        if (item["what"] == "compressor delivery pressure"
                and has_value(item["units"])
                and "psi" in str(item["units"]).lower()
                and "psia" not in str(item["units"]).lower()
                and "psig" not in str(item["units"]).lower()):
            notes.append("compressor delivery pressure: 'psi' on its own is "
                         "ambiguous - write psia or psig")
        if not has_value(item["source"]) and has_value(item["units"]):
            notes.append("{0}: no source recorded".format(item["what"]))
    if notes:
        ws.bullets(notes)


def main():
    ws = Worksheet(
        code="C6",
        title="Compare three measurement needs",
        card="workspaces/combustion-systems/C6-instrumentation.md",
        review_role="Combustion & Systems lead",
    )
    ws.header(safety_line="Desk work only today. No magnet attached to "
                          "anything rotating, no flame or heat-gun test, no "
                          "calibration claim, no wiring.")
    lesson(ws)
    your_rows(ws)
    your_calculation(ws)

    ws.heading("what finishing looks like")
    ws.bullets([
        "Three rows with units, a candidate range, a response-time question "
        "and one source each.",
        "Anything you could not find marked NOT FOUND.",
        "One sentence on accuracy versus resolution, and one on psia versus "
        "psig.",
    ])
    ws.say("Not today: attaching anything to a rotor, testing a probe with a "
           "flame or a heat gun, or claiming a calibration. An ice bath and "
           "boiling water check two points near room temperature; they say "
           "nothing about a probe's behaviour at a thousand kelvin or about "
           "how fast it responds. Safety reviews any protection the "
           "instruments need.")

    ws.record("pulses per revolution assumed", PULSES_PER_REVOLUTION)
    ws.record("probe maximum temperature", PROBE_MAXIMUM_TEMPERATURE_K)
    ws.record("probe response time", PROBE_RESPONSE_TIME_S)
    ws.record("sensor A full scale", SENSOR_RANGE_A_PSI)
    ws.record("sensor B full scale", SENSOR_RANGE_B_PSI)
    ws.record("converter bits", CONVERTER_BITS)

    ws.submission(date=DATE, learned=WHAT_I_LEARNED, unknown=STILL_UNKNOWN,
                  question=QUESTION_FOR_LEAD, next_step=NEXT_SMALL_STEP)
    ws.done_when([
        ("speed row: units", MEASUREMENT_ROWS[0]["units"]),
        ("speed row: source", MEASUREMENT_ROWS[0]["source"]),
        ("temperature row: units", MEASUREMENT_ROWS[1]["units"]),
        ("temperature row: source", MEASUREMENT_ROWS[1]["source"]),
        ("pressure row: units, psia or psig", MEASUREMENT_ROWS[2]["units"]),
        ("pressure row: source", MEASUREMENT_ROWS[2]["source"]),
        ("accuracy versus resolution, in your words", ACCURACY_VS_RESOLUTION),
        ("psia versus psig, in your words", PSIA_VS_PSIG),
        ("one question for the lead", QUESTION_FOR_LEAD),
    ])
    ws.finish()


if __name__ == "__main__":
    main()
