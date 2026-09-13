"""S1 - Read one bearing datasheet.  CORE first-meeting worksheet.

WHAT THIS IS
  A 30-45 minute guided activity. You will read one real bearing catalogue
  page, write down what it actually promises, and work out one screening
  number. You will not select a bearing.

HOW TO USE IT
  1. Run it once and read what it prints:   python s1_bearing_screen.py
  2. Edit the block below marked YOUR ANSWERS. Nothing else.
  3. Save, run again, hand the printed block to your lead.

WHAT THIS IS NOT
  Not a bearing selection, not a life calculation you should trust, not a
  spin-rig plan. Nothing rotates today.
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

# 1. The exact bearing whose page you read. Not "a 608" - the actual part,
#    from the actual supplier, with the actual suffix.
EXACT_BEARING = answer(
    value=UNKNOWN,             # e.g. "Timken 608-C3"
    source=UNKNOWN,            # the catalogue page you read
    uncertainty=UNKNOWN,
)

# 2. Its bore diameter, from that page.
BORE_MM = answer(
    value=UNKNOWN,             # e.g. 8
    units="mm",
    source=UNKNOWN,
)

# 3. The speeds the catalogue actually lists, and under what lubrication.
#    Most catalogues list two: one with oil, one with grease. They are very
#    different numbers and the difference is the whole point.
CATALOGUE_SPEED_OIL_RPM = answer(
    value=UNKNOWN,             # e.g. 39000
    units="rpm",
    source=UNKNOWN,
    uncertainty=UNKNOWN,       # e.g. "listed as an example condition, not a limit"
)
CATALOGUE_SPEED_GREASE_RPM = answer(
    value=UNKNOWN,             # e.g. 33000
    units="rpm",
    source=UNKNOWN,
    uncertainty=UNKNOWN,
)

# 4. Exactly what the catalogue says that speed figure means. Copy the
#    wording. "Limiting speed", "reference speed" and "example condition"
#    are three different promises and only one of them is a limit.
WHAT_THE_SPEED_FIGURE_MEANS = UNKNOWN

# 5. Two loads or conditions the catalogue needs, that nobody on CORE has
#    told it yet. Think: what does the bearing not know about our engine?
UNKNOWN_CONDITION_1 = UNKNOWN
UNKNOWN_CONDITION_2 = UNKNOWN

# 6. Optional stretch: describe your stepped-shaft sketch if you drew one.
STEPPED_SHAFT_SKETCH = UNKNOWN   # e.g. "6 mm wheel bore stepping up to 8 mm
                                 #       journal, labelled CANDIDATE"

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

CORE_SHAFT_RPM = 66000.0       # DP-2 candidate shaft speed
CANDIDATE_JOURNAL_MM = 8.0     # DP-2 candidate bearing journal diameter


def lesson(ws):
    ws.heading("what a bearing does, in plain language")
    ws.say("A skateboard wheel spins freely because there is a ring of little "
           "steel balls between the moving part and the still part. Without "
           "them the wheel would grind on the axle and stop. That is a "
           "bearing, and ours does the same job for the engine shaft.")
    ws.say("The difference is the numbers. A skateboard wheel might reach a "
           "few hundred revolutions per minute. Our shaft is proposed at "
           "66,000, which is eleven hundred revolutions every second, next to "
           "a combustor, for minutes at a time. At those speeds the balls "
           "themselves are being flung outwards hard enough to matter, the "
           "cage that holds them apart becomes a structural part, and how the "
           "oil or grease gets in and out stops being a detail.")
    ws.say("This is the subsystem the DP-2 review is most cautious about, and "
           "your task today is deliberately small: read one real page, and "
           "write down what it does and does not promise.")

    ws.heading("the words you need")
    ws.terms([
        ("bore",
         "The hole in the middle, in mm. A 608 bearing has an 8 mm bore. This "
         "is the number that has to match the shaft."),
        ("DN",
         "Bore in mm multiplied by speed in rpm. A rough screening number used "
         "across the whole bearing industry to say 'is this in the right "
         "ballpark at all'. It is a filter, not a decision."),
        ("lubrication",
         "Oil or grease. The same bearing is rated for very different speeds "
         "depending on which, and on how the lubricant is delivered. Grease is "
         "simpler and slower. Oil is faster and brings a whole system with "
         "it."),
        ("preload",
         "A deliberate squeeze applied to the bearing so its parts cannot "
         "rattle. Get it wrong in one direction and the shaft wobbles; wrong "
         "in the other and the bearing cooks itself."),
        ("L10 life",
         "The time by which one bearing in ten is expected to have failed. It "
         "depends on the load, and it assumes the bearing is being used inside "
         "all its other conditions. Calculating L10 from the weight of the "
         "rotor alone tells you almost nothing, because the loads that matter "
         "here are not weight."),
    ])

    ws.heading("the trap in this task")
    ws.legend()
    ws.given("candidate journal diameter", CANDIDATE_JOURNAL_MM, "mm", CANDIDATE)
    ws.given("candidate shaft speed", CORE_SHAFT_RPM, "rpm", CANDIDATE)
    ws.given("DN for those two", 528000, "mm rpm", REPO_CHECK,
             "docs/project/checks/dp2_screen.py reproduces 528000")
    ws.blank()
    ws.say("Here is the argument you are being asked to examine, and it is a "
           "tempting one. The earlier design point needed 800,000 DN. DP-2 "
           "only needs 528,000. That is a big improvement, so an ordinary 8 mm "
           "bearing should be fine now.")
    ws.say("The DP-2 review does not accept it, and the reason is worth "
           "understanding because it applies far beyond bearings. DN is a "
           "screening index built from two numbers. The catalogue page is "
           "built from many more: cage material, lubrication method, preload, "
           "operating temperature, how the bearing is fitted into its housing, "
           "the direction and size of the load, and how long you want it to "
           "last. A good DN does not buy you any of those. It only means you "
           "have not been ruled out yet.")
    ws.say("The specific number in front of us: one manufacturer lists an "
           "example for this bearing size at 39,000 rpm with oil and 33,000 "
           "rpm with grease. We are proposing 66,000. Your job is to read the "
           "page and find out exactly what those figures are - a hard limit, a "
           "reference condition, or an example - and to write down what the "
           "page would need to know about our engine before anyone could "
           "answer the real question.")

    ws.example([
        "  DN = bore in mm  x  speed in rpm",
        "",
        "  CORE candidate :  8 mm x 66000 rpm   = 528,000 mm rpm",
        "  catalogue oil  :  8 mm x 39000 rpm   = 312,000 mm rpm",
        "  catalogue grease: 8 mm x 33000 rpm   = 264,000 mm rpm",
        "",
        "  528,000 / 312,000 = 1.69   we are asking for 69 percent more",
        "  528,000 / 264,000 = 2.00   or exactly double, on grease",
        "",
        "The catalogue numbers above are the ones quoted in the DP-2 review.",
        "Do not take them from here - go and read the page yourself, because",
        "checking what a source really says is the entire skill this task",
        "is teaching.",
    ])


def your_calculation(ws):
    ws.heading("now do it with the page you read")
    dn = ws.compute(
        "DN for the bearing you found, at CORE's candidate speed",
        lambda bore: bore * CORE_SHAFT_RPM,
        {"bore (mm)": BORE_MM},
        units="mm rpm",
    )
    if dn is not None:
        ws.compute(
            "how much faster we want to run than the catalogue's oil figure",
            lambda speed: CORE_SHAFT_RPM / speed,
            {"catalogue speed with oil (rpm)": CATALOGUE_SPEED_OIL_RPM},
            units="times",
            comment="A number above 1 means we are asking for more than the "
                    "page offers. Write down by how much, and say in your "
                    "findings what the page calls that figure.",
        )
        ws.compute(
            "how much faster we want to run than the catalogue's grease figure",
            lambda speed: CORE_SHAFT_RPM / speed,
            {"catalogue speed with grease (rpm)": CATALOGUE_SPEED_GREASE_RPM},
            units="times",
        )
        ws.compute(
            "DN at the catalogue's own oil speed, for comparison",
            lambda bore, speed: bore * speed,
            {"bore (mm)": BORE_MM,
             "catalogue speed with oil (rpm)": CATALOGUE_SPEED_OIL_RPM},
            units="mm rpm",
            comment="Two DN numbers for the same bearing. The gap between them "
                    "is what the catalogue is telling you, and it is the "
                    "reason DN on its own cannot approve anything.",
        )


def main():
    ws = Worksheet(
        code="S1",
        title="Read one bearing datasheet",
        card="workspaces/structures/S1-shaft-bearings.md",
        review_role="Structures lead",
    )
    ws.header(safety_line="Desk work only today. No spin rig, no rotor "
                          "assembly, no full-speed anything.")
    lesson(ws)
    your_calculation(ws)

    ws.heading("what finishing looks like")
    ws.bullets([
        "A small table: the exact part, its bore, and the catalogue speed with "
        "the lubrication condition attached.",
        "The catalogue's own wording for what that speed figure means.",
        "Two loads or conditions the catalogue needs and nobody has supplied.",
    ])
    ws.say("Not today: choosing a bearing, computing an L10 life from the "
           "weight of the rotor, planning a spin rig, or deciding between "
           "steel and hybrid ceramic. The DP-2 review is explicit that a "
           "generic part does not gain speed margin from a DN number, and "
           "that exact cage, lubrication, preload, temperature, fits, thrust "
           "and life conditions all matter. Those come later, with the lead "
           "and with Safety.")

    ws.record("exact bearing read", EXACT_BEARING)
    ws.record("bore", BORE_MM)
    ws.record("catalogue speed, oil", CATALOGUE_SPEED_OIL_RPM)
    ws.record("catalogue speed, grease", CATALOGUE_SPEED_GREASE_RPM)

    ws.submission(date=DATE, learned=WHAT_I_LEARNED, unknown=STILL_UNKNOWN,
                  question=QUESTION_FOR_LEAD, next_step=NEXT_SMALL_STEP)
    ws.done_when([
        ("exact bearing part, or NOT FOUND", EXACT_BEARING),
        ("bore in mm", BORE_MM),
        ("catalogue speed with oil", CATALOGUE_SPEED_OIL_RPM),
        ("catalogue speed with grease", CATALOGUE_SPEED_GREASE_RPM),
        ("what the catalogue says that figure means",
         WHAT_THE_SPEED_FIGURE_MEANS),
        ("unknown load or condition 1", UNKNOWN_CONDITION_1),
        ("unknown load or condition 2", UNKNOWN_CONDITION_2),
        ("one question for the lead", QUESTION_FOR_LEAD),
    ])
    ws.finish()


if __name__ == "__main__":
    main()
