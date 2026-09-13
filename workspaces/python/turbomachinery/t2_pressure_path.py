"""T2 - Sketch the diffuser-to-combustor air path.  CORE first-meeting worksheet.

WHAT THIS IS
  A 30-45 minute guided activity. The main deliverable is a SKETCH on paper.
  This script teaches you what to put on it, then does one small pressure
  calculation with you so the sketch has a number attached.

HOW TO USE IT
  1. Run it once and read what it prints:   python t2_pressure_path.py
  2. Draw the sketch. Paper is fine. A phone photo is fine.
  3. Edit the block below marked YOUR ANSWERS. Nothing else.
  4. Save, run again, and hand the printed block to your lead.

WHAT THIS IS NOT
  It does not import the engine model and cannot change any design value.
  It does not choose a casing diameter and does not settle a loss budget.
"""

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

# 1. Your sketch. Describe it in one line so the lead knows what to look for.
SKETCH = UNKNOWN               # e.g. "paper sketch, photo in the meeting folder,
                               #       compressor exit to liner, 5 stations named"

# 2. Three places on YOUR sketch where you think total pressure is lost.
#    Plain language is fine. "Where the pipe suddenly gets wider" is a real
#    answer and has a real name (sudden expansion).
LOSS_PLACE_1 = UNKNOWN
LOSS_PLACE_2 = UNKNOWN
LOSS_PLACE_3 = UNKNOWN

# 3. The station names you and C1 agreed to use, in order along the air path.
#    If you have not spoken to C1 yet, write NOT_FOUND and say so in your
#    question for the lead.
STATION_NAMES = UNKNOWN        # e.g. "3 compressor exit, 3.1 diffuser exit,
                               #       3.5 liner inlet, 4 NGV inlet"

# 4. The annulus you drew. Use the casing inner diameter DP-2 proposes, and
#    a liner outer diameter that YOU choose for the sketch. The liner size is
#    not decided - you are drawing one possibility so the arithmetic has
#    something to chew on.
CASING_INNER_DIAMETER_MM = answer(
    value=149.4,               # DP-2 candidate; change it if your lead says so
    units="mm",
    source="docs/project/dp2-review.md candidate table",
    basis=CANDIDATE,
)
SKETCH_LINER_OUTER_DIAMETER_MM = answer(
    value=UNKNOWN,             # e.g. 120 - a number you picked for the sketch
    units="mm",
    source="my own sketch, not a project value",
    uncertainty="not a decided dimension",
    basis=EXAMPLE,
)

# 5. A measured total-pressure loss from a real engine of this class, if you
#    can find one, so we can compare. Do not guess. NOT_FOUND is fine.
REFERENCE_ENGINE_LOSS_PERCENT = answer(
    value=UNKNOWN,             # e.g. 12
    units="percent of combustor inlet total pressure",
    source=UNKNOWN,            # which engine, which document, which page
    uncertainty=UNKNOWN,
)

# 6. A loss coefficient K for one feature, WITH the reference it came from.
#    Leave this UNKNOWN unless you have an actual source. The DP-2 review
#    says plainly that a K of 20 to 60 "requires an applicable reference",
#    so this worksheet will not compute anything from a guessed K.
LOSS_COEFFICIENT_K = answer(
    value=UNKNOWN,
    units="(multiples of one dynamic head)",
    source=UNKNOWN,            # textbook, paper or handbook - name it
    uncertainty=UNKNOWN,
)

# 7. Your writing.
WHAT_I_LEARNED = [
    UNKNOWN,
    UNKNOWN,
    UNKNOWN,
]
STILL_UNKNOWN = UNKNOWN
QUESTION_FOR_LEAD = UNKNOWN    # the card asks for one about a local area or pressure
NEXT_SMALL_STEP = UNKNOWN

# ===========================================================================
#  END OF YOUR ANSWERS.
# ===========================================================================

R_AIR = 287.05                 # J/(kg K), the gas constant for air
T3 = 348.10                    # K   - repository screen result for DP-2
P3 = 163510.0                  # Pa  - repository screen result for DP-2
MDOT = 0.30                    # kg/s - DP-2 candidate air flow


def lesson(ws):
    ws.heading("what the diffuser does, in plain language")
    ws.say("Put your thumb over a garden hose and the water shoots out fast. "
           "Take your thumb off and it dribbles out slow. A diffuser is the "
           "second one, on purpose: the passage gets wider, the air slows "
           "down, and the push it makes against the walls goes up.")
    ws.say("Air leaves our compressor wheel moving fast. The combustor cannot "
           "use fast air - a flame in a 100 m/s wind blows out. So between "
           "them sits a diffuser, whose whole job is to trade speed for "
           "pressure before the air ever meets fuel.")
    ws.say("Reverse-flow means the air does not go straight on. It dumps into "
           "a ring-shaped gap around the outside of the combustor liner, runs "
           "backwards along it, turns 180 degrees at the far end, and comes "
           "forward again inside the liner. That fold is what makes the engine "
           "short. It also costs pressure, which is your problem.")

    ws.heading("the one idea this task is really about")
    ws.terms([
        ("static pressure",
         "What a little hole in the wall of the duct feels. The squeeze the "
         "air is under right where it is."),
        ("dynamic head",
         "The extra push the air has because it is moving: one half times "
         "density times speed squared. Written q."),
        ("total pressure",
         "Static plus dynamic. The pressure you would measure if you brought "
         "the air smoothly to a complete stop. Think of it as the air's whole "
         "budget."),
        ("a loss",
         "A drop in TOTAL pressure. Slowing air down in a diffuser lowers "
         "dynamic and raises static and is NOT a loss - it is the point. "
         "Friction, sudden expansions, sharp turns and mixing lower the total. "
         "Those are losses, and they never come back."),
        ("reference velocity",
         "A bookkeeping speed: the flow divided by density and a chosen area. "
         "It is only meaningful if you say which area you used. Different "
         "areas give different answers to the same question."),
    ])
    ws.say("Write that fourth one on your sketch somewhere. Half of the "
           "confusion in combustor design comes from people mixing up a "
           "pressure that moved and a pressure that vanished.")

    ws.heading("why your sketch matters this year")
    ws.legend()
    ws.given("compressor pressure ratio", 1.63, "(ratio)", CANDIDATE)
    ws.given("combustor inlet total temperature T3", T3, "K", REPO_CHECK,
             "docs/project/checks/dp2_screen.py")
    ws.given("combustor inlet total pressure P3", P3 / 1000.0, "kPa", REPO_CHECK,
             "docs/project/checks/dp2_screen.py")
    ws.given("casing outer / inner diameter", "152.4 / 149.4", "mm", CANDIDATE)
    ws.blank()
    ws.say("DP-2 runs at a pressure ratio of about 1.63 instead of the 2.8 the "
           "earlier design point used. There is simply less pressure in the "
           "engine, so every percent lost matters more. The DP-2 review puts "
           "the point where the engine stops making positive pressure at the "
           "turbine exit at roughly 21 percent combustor loss at nominal "
           "component efficiencies, and around 12 to 14 percent if those "
           "efficiencies disappoint. Read section 3 of the review for what is "
           "being held fixed in each of those numbers - they are not the same "
           "calculation.")
    ws.say("So: how many percent do the features on your sketch cost? Nobody "
           "on this project knows yet. That is the honest state of it, and it "
           "is why we start by counting the features rather than by picking a "
           "number.")

    ws.heading("a worked example, so the arithmetic is not a mystery")
    ws.say("Density comes from the ideal gas law: density = pressure divided "
           "by (gas constant times temperature). Speed comes from continuity: "
           "the same mass has to get through, so speed = mass flow divided by "
           "(density times area).")
    ws.example([
        "Air at the combustor inlet, using the repository screen values:",
        "  density = 163510 Pa / (287.05 * 348.10 K)   = 1.6364 kg/m3",
        "",
        "A ring-shaped gap between a 149.4 mm casing bore and a 120 mm liner",
        "(120 mm is invented here purely to have a number):",
        "  area  = pi/4 * (0.1494^2 - 0.120^2)          = 0.006220 m2",
        "  speed = 0.30 / (1.6364 * 0.006220)           = 29.47 m/s",
        "  q     = 0.5 * 1.6364 * 29.47^2               = 711 Pa",
        "",
        "And 711 Pa is 0.43 percent of the 163510 Pa total pressure.",
        "",
        "That is the punchline. ONE dynamic head in this annulus is under half",
        "a percent. Real engines of this class measure around 12 percent total",
        "combustor loss. So the loss is not one dynamic head - it is dozens of",
        "them, spread across the dump, the turn, the scoops and every hole.",
        "Counting features is the job. Estimating from casing area alone is",
        "what produced the 1.3 to 3.8 percent figure the DP-2 review flags as",
        "disagreeing with measurement by about a factor of three.",
    ])


def your_calculation(ws):
    ws.heading("now do it for the annulus you drew")
    density = P3 / (R_AIR * T3)
    ws.given("air density at the combustor inlet", density, "kg/m3", REPO_CHECK,
             "ideal gas law from the T3 and P3 above")
    ws.blank()

    area = ws.compute(
        "annulus area on your sketch",
        lambda casing, liner: 3.141592653589793 / 4.0
        * ((casing / 1000.0) ** 2 - (liner / 1000.0) ** 2),
        {"casing inner diameter (mm)": CASING_INNER_DIAMETER_MM,
         "liner outer diameter you drew (mm)": SKETCH_LINER_OUTER_DIAMETER_MM},
        units="m2",
        comment="If this came out negative or zero, your liner is not smaller "
                "than the casing. Check the two numbers.",
    )
    if area is not None and area > 0:
        speed = ws.compute(
            "reference velocity in that annulus",
            lambda a: MDOT / (density * a),
            {"annulus area (m2)": area},
            units="m/s",
            comment="This treats the whole air flow as going down this one "
                    "gap. In the real engine the flow splits between branches, "
                    "so this is a first look, not a loss budget. Say which "
                    "area you used whenever you quote a reference velocity.",
        )
        if speed is not None:
            head = ws.compute(
                "one dynamic head q",
                lambda v: 0.5 * density * v * v,
                {"reference velocity (m/s)": speed},
                units="Pa",
            )
            if head is not None:
                ws.compute(
                    "one dynamic head as a share of P3",
                    lambda q: 100.0 * q / P3,
                    {"dynamic head (Pa)": head},
                    units="percent",
                )
                ws.compute(
                    "how many dynamic heads a real engine's measured loss is",
                    lambda q, pct: (pct / 100.0 * P3) / q,
                    {"dynamic head (Pa)": head,
                     "measured loss you found (percent)":
                         REFERENCE_ENGINE_LOSS_PERCENT},
                    units="dynamic heads",
                    comment="Fill in a measured loss from a real engine with a "
                            "source to see this. It is the single most useful "
                            "sanity check in your whole task.",
                )
                ws.compute(
                    "loss from one feature, using a K you can cite",
                    lambda q, k: 100.0 * k * q / P3,
                    {"dynamic head (Pa)": head,
                     "loss coefficient K with a named reference":
                         LOSS_COEFFICIENT_K},
                    units="percent of P3",
                    comment="Deliberately blank until you have a reference for "
                            "K. Do not pick one today. The point of running "
                            "this line is to feel how fast the answer moves "
                            "when K changes.",
                )


def main():
    ws = Worksheet(
        code="T2",
        title="Sketch the diffuser-to-combustor air path",
        card="workspaces/turbomachinery/T2-diffuser.md",
        review_role="Turbomachinery lead",
    )
    ws.header()
    lesson(ws)
    your_calculation(ws)

    ws.heading("what to put on the sketch")
    ws.bullets([
        "Compressor exit, diffuser, the two feed annuli, and the liner.",
        "An arrow for the air, all the way round the fold.",
        "A name and a number for each station, even if the number is a "
        "question mark.",
        "Three crosses where you think total pressure is lost, with a word "
        "each.",
        "One question to ask C1 about where their loss budget starts, so the "
        "two of you do not count the same feature twice or miss it entirely.",
    ])
    ws.say("Not today: choosing a casing diameter, optimising anything, or "
           "promising a scoop velocity. The DP-2 review specifically says the "
           "35 m/s scoop threshold in the supplied notes is not established by "
           "the evidence we have. Your sketch and one question are the whole "
           "deliverable.")

    ws.record("liner outer diameter used on my sketch",
              SKETCH_LINER_OUTER_DIAMETER_MM)
    ws.record("measured combustor loss from a reference engine",
              REFERENCE_ENGINE_LOSS_PERCENT)
    ws.record("loss coefficient K with a reference", LOSS_COEFFICIENT_K)

    ws.submission(date=DATE, learned=WHAT_I_LEARNED, unknown=STILL_UNKNOWN,
                  question=QUESTION_FOR_LEAD, next_step=NEXT_SMALL_STEP)
    ws.done_when([
        ("a sketch exists and is described", SKETCH),
        ("loss place 1", LOSS_PLACE_1),
        ("loss place 2", LOSS_PLACE_2),
        ("loss place 3", LOSS_PLACE_3),
        ("station names, agreed with C1 or marked NOT FOUND", STATION_NAMES),
        ("the liner diameter you drew", SKETCH_LINER_OUTER_DIAMETER_MM),
        ("one question for the lead", QUESTION_FOR_LEAD),
    ])
    ws.finish()


if __name__ == "__main__":
    main()
