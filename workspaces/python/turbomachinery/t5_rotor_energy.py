"""T5 / SAFE1 - Understand rotor energy and its unknowns.  CORE worksheet.

WHAT THIS IS
  A 30-45 minute guided activity. You will work out how much energy is stored
  in a spinning rotor, find out how fast that number grows with speed, and
  list what a containment review would still need to know. This is one piece
  of work that serves both the T5 card and the Safety SAFE1 role.

HOW TO USE IT
  1. Run it once and read what it prints:   python t5_rotor_energy.py
  2. Edit the block below marked YOUR ANSWERS. Nothing else.
  3. Save, run again, hand the printed block to the Safety lead.

WHAT THIS IS NOT
  Not a burst-speed claim, not a shield design, not approval of any material,
  and absolutely not authorisation to spin anything. Nothing rotates today.
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

# 1. The rotor's moment of inertia. DP-2 supplies an ESTIMATE. It has not
#    been measured and it has not been taken from a finished CAD model.
#    Leave the value alone unless your lead gives you a better one; what
#    matters today is that you label it honestly.
ROTOR_INERTIA = answer(
    value=2.13e-4,
    units="kg m2",
    source="DP-2 note, repeated in docs/project/dp2-review.md",
    uncertainty="ESTIMATE - not measured, not from a released CAD model",
    basis=CANDIDATE,
)

# 2. The shaft speed you want to look at.
SHAFT_SPEED_RPM = answer(
    value=66000,
    units="rpm",
    source="DP-2 candidate maximum shaft speed",
    uncertainty="candidate, not an approved operating speed",
    basis=CANDIDATE,
)

# 3. Two facts a containment review would need that nobody has yet.
#    Think about it as: if a piece came off, what would somebody have to know
#    to decide whether a shield stops it?
MISSING_FACT_1 = UNKNOWN
MISSING_FACT_2 = UNKNOWN

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

IDLE_ESTIMATE_RPM = 30100.0    # DP-2's hypothesis, explicitly not a setpoint
GRAVITY = 9.81                 # m/s2


def rpm_to_rad_s(rpm):
    return rpm * 2.0 * math.pi / 60.0


def lesson(ws):
    ws.heading("what stored rotational energy is")
    ws.say("Spin a bicycle wheel hard and try to stop it with your hand. It "
           "fights you. That fight is energy you put in, stored in the "
           "spinning, and it comes back out when something stops it.")
    ws.say("Our rotor is a compressor wheel and a turbine wheel on one shaft, "
           "turning about eleven hundred times a second. If any part of it "
           "comes loose, the energy has to go somewhere, and it goes outward, "
           "fast. That is the whole reason Safety reviews this project before "
           "anybody stands near it.")
    ws.say("Today you are going to put a number on that energy. Not to decide "
           "anything - just so the number exists, is written down, and is "
           "labelled with how confident we are in it. Which is: not very.")

    ws.heading("the words you need")
    ws.terms([
        ("moment of inertia, I",
         "How hard it is to spin something up or slow it down. Mass matters, "
         "but where the mass sits matters more: the same metal moved further "
         "from the centre is much harder to spin. Units kg m2."),
        ("angular velocity, omega",
         "Rotation speed in radians per second. It is rpm times 2 pi divided "
         "by 60. Formulas want radians per second, not rpm, and getting this "
         "conversion wrong is the single most common error in the topic."),
        ("stored energy, E",
         "One half times I times omega squared. Units joules. Note omega is "
         "SQUARED - that is the whole story of this worksheet."),
        ("containment",
         "Making sure that if a piece comes off, it stops somewhere safe. It "
         "is a design task with its own review, and it needs much more than "
         "one energy number."),
        ("burst speed",
         "The speed at which a wheel tears itself apart. We do not know ours. "
         "Do not claim one today, and be careful of any document that does "
         "without saying how it got there."),
    ])

    ws.heading("the numbers the project already has")
    ws.legend()
    ws.given("estimated rotor inertia", 2.13e-4, "kg m2", CANDIDATE,
             "an ESTIMATE; DP-2 does not say how it was obtained")
    ws.given("candidate maximum shaft speed", 66000, "rpm", CANDIDATE)
    ws.given("stored energy at that speed", 5.087, "kJ", REPO_CHECK,
             "docs/project/checks/dp2_screen.py reproduces 5087 J")
    ws.given("stored energy at 120 percent speed", 7.326, "kJ", REPO_CHECK,
             "docs/project/checks/dp2_screen.py")
    ws.blank()

    ws.heading("a worked example, so the arithmetic is not a mystery")
    ws.example([
        "Step 1 - turn rpm into radians per second:",
        "  omega = 66000 * 2 * pi / 60           = 6911.5 rad/s",
        "",
        "Step 2 - put it in the energy formula:",
        "  E = 0.5 * 0.000213 * 6911.5^2         = 5087 J  = 5.09 kJ",
        "",
        "Step 3 - now try 20 percent faster. Do not recompute from scratch;",
        "just notice that omega is squared, so the energy goes up by 1.2",
        "squared, which is 1.44:",
        "  E at 79200 rpm = 5087 * 1.44          = 7326 J  = 7.33 kJ",
        "",
        "That is the lesson. A 20 percent overspeed is not 20 percent worse.",
        "It is 44 percent worse. Anything that squares a speed punishes",
        "overspeed much harder than intuition suggests, and intuition is what",
        "people bring to a test stand.",
        "",
        "For a sense of scale, 5087 J is about what it takes to lift a 1 kg",
        "bag of sugar 519 metres straight up. That is a scale analogy and",
        "nothing more. The DP-2 review is blunt that energy comparisons do",
        "not design containment: fragment mass, shape, direction and speed",
        "do, and we have none of those yet.",
    ])


def your_calculation(ws):
    ws.heading("now do it yourself")
    omega = ws.compute(
        "angular velocity omega",
        lambda rpm: rpm_to_rad_s(rpm),
        {"shaft speed (rpm)": SHAFT_SPEED_RPM},
        units="rad/s",
    )
    energy = None
    if omega is not None:
        energy = ws.compute(
            "stored energy E",
            lambda inertia, w: 0.5 * inertia * w * w,
            {"rotor inertia (kg m2)": ROTOR_INERTIA,
             "angular velocity (rad/s)": omega},
            units="J",
            comment="Divide by 1000 for kJ. Compare it with the 5087 J above: "
                    "if you left the inputs alone, it should match.",
        )
    if energy is not None:
        ws.compute(
            "stored energy at 120 percent of that speed",
            lambda e: e * 1.44,
            {"stored energy (J)": energy},
            units="J",
            comment="The multiplier is 1.2 squared = 1.44, not 1.2. Write that "
                    "sentence in your findings; it is the one thing from this "
                    "worksheet that everybody on the team should know.",
        )
        ws.compute(
            "stored energy at DP-2's estimated idle speed",
            lambda inertia: 0.5 * inertia * rpm_to_rad_s(IDLE_ESTIMATE_RPM) ** 2,
            {"rotor inertia (kg m2)": ROTOR_INERTIA},
            units="J",
            comment="DP-2 guesses idle near 30,100 rpm. The review calls that "
                    "a hypothesis, not a setpoint. Even so, notice that 'idle' "
                    "still stores about a kilojoule. There is no speed at "
                    "which this rotor is casually safe.",
        )
        ws.compute(
            "height you would have to lift 1 kg for the same energy",
            lambda e: e / GRAVITY,
            {"stored energy (J)": energy},
            units="m",
            comment="A scale analogy for a conversation, not an input to any "
                    "shield design.",
        )


def main():
    ws = Worksheet(
        code="T5 / SAFE1",
        title="Understand rotor energy and its unknowns",
        card="workspaces/turbomachinery/T5-rotor-energy.md",
        review_role="Safety lead, with Structures and Turbomachinery leads",
    )
    ws.header(safety_line="Desk arithmetic only. Nothing spins today. No "
                          "burst-speed claim, no shield design, no approval "
                          "of surplus material, no rotor test.")
    lesson(ws)
    your_calculation(ws)

    ws.heading("what finishing looks like")
    ws.bullets([
        "One energy number you worked out yourself, with the inertia clearly "
        "labelled as an estimate.",
        "The sentence about 1.44, in your own words.",
        "Two facts a containment review would need and nobody has.",
    ])
    ws.say("Good candidates for those two facts, if you are stuck: how heavy "
           "is the biggest piece that could come off and where would it go; "
           "what is the wheel actually made of and can we prove it; what speed "
           "does it fail at; what is the shield made of and has anyone checked "
           "it against a fragment rather than against a number. You only need "
           "two, and 'we do not know' is the correct answer to all of them "
           "right now.")
    ws.say("Not today: deciding the containment design, approving a surplus "
           "turbine blank, or doing the stress and life analysis. Those are "
           "later, separately reviewed work. This same finding is what Safety "
           "records for SAFE1 - do not write it up twice.")

    ws.record("rotor inertia used", ROTOR_INERTIA)
    ws.record("shaft speed used", SHAFT_SPEED_RPM)

    ws.submission(date=DATE, learned=WHAT_I_LEARNED, unknown=STILL_UNKNOWN,
                  question=QUESTION_FOR_LEAD, next_step=NEXT_SMALL_STEP)
    ws.done_when([
        ("rotor inertia used, labelled as an estimate", ROTOR_INERTIA),
        ("shaft speed used", SHAFT_SPEED_RPM),
        ("missing containment fact 1", MISSING_FACT_1),
        ("missing containment fact 2", MISSING_FACT_2),
        ("one question for the Safety lead", QUESTION_FOR_LEAD),
    ])
    ws.finish()


if __name__ == "__main__":
    main()
