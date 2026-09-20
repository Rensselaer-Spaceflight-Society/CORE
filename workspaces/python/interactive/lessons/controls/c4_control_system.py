"""C4: build a safe control-system concept from signals to a plant model.

The lesson is intentionally desk-only.  It teaches the vocabulary John and a
new controls teammate need before opening Simulink, then makes a few synthetic
calculations they can reproduce there.  It does not select trip thresholds,
claim engine performance, or drive an actuator.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from runtime import Calculation, Lesson, Question, Step, run_lesson

from _control_model import first_order_step, proportional_command


def build_lesson():
    return Lesson(
        id="C4",
        version="1.0",
        title="Build the control-system concept before opening Simulink",
        review_role=("Combustion & Systems lead; Safety lead reviews fault behavior; "
                     "Instrumentation and Electrical review signal interfaces"),
        minutes="45-60",
        prerequisites=(
            "Read the C4 card and look at the local control-loop diagram.",
            "Keep every threshold, trip value and actuator decision as TBD unless the leads have approved it.",
            "Use synthetic numbers only for the calculation; do not connect this lesson to hardware.",
        ),
        sources=(
            "docs/project/dp2-review.md",
            "workspaces/coordination/interfaces.md",
            "workspaces/combustion-systems/C5-model-interface.md",
            "workspaces/combustion-systems/C6-instrumentation.md",
        ),
        steps=(
            Step(
                "purpose",
                "1. Say what the controller is trying to protect and control",
                "A controller is a careful sequence of checks, commands and stops. "
                "For CORE, a student model may illustrate how a requested shaft speed "
                "becomes a synthetic fuel command and how the plant responds. It does "
                "not prove that the real engine can reach that speed. DP-2's speed, air "
                "flow and pressure ratio are candidate design inputs, not firmware "
                "setpoints. Start by writing the single decision your model should help "
                "the team make.",
                (
                    Question(
                        "control_goal",
                        "What one decision should this model help the team make?",
                        evidence=False,
                        hint=("Examples: agree which signals C4 and C5 exchange, "
                              "or see why a missing RPM signal must inhibit fuel."),
                    ),
                    Question(
                        "mode_of_interest",
                        "Which mode are you describing first?",
                        kind="choice",
                        choices=("pre-start checks", "assisted start", "steady running", "fault shutdown"),
                        evidence=False,
                    ),
                ),
                visual="control_loop.svg",
            ),
            Step(
                "signals",
                "2. Give every arrow a name, unit and failure behavior",
                "A Simulink block diagram becomes useful only when the arrows have a "
                "shared meaning. Name the input, its unit, its direction and what a "
                "missing or implausible value means. A tachometer value is a measured "
                "signal, while a fuel command is a request; neither one is proof that "
                "the hardware did what it was asked to do. C4 and C5 should agree on "
                "these rows before anyone tunes a controller.",
                (
                    Question(
                        "signal_contract",
                        "Write a small signal table for at least five signals.",
                        evidence=False,
                        hint=("For each: name | units | source/destination | valid range or "
                              "TBD | behavior if missing. Include RPM, EGT, fuel command "
                              "and at least one permissive/fault signal. Use /text."),
                    ),
                    Question(
                        "primary_feedback",
                        "Which feedback signal is the first one you would close the loop around?",
                        kind="choice",
                        choices=("shaft speed (RPM)", "EGT", "both with separate limits", "not decided"),
                        evidence=False,
                        role="decision",
                    ),
                    Question(
                        "signal_unknown",
                        "What signal or interface detail is still unknown and needs a lead decision?",
                        evidence=False,
                        role="decision",
                        hint="Examples: pulse-per-revolution convention, pressure reference, invalid-data flag.",
                    ),
                ),
            ),
            Step(
                "states",
                "3. Draw the state machine before writing control code",
                "Use five boxes: OFF, CHECKS, STARTING, RUNNING and FAULT. An arrow "
                "needs evidence before it can be taken. For example, a request to "
                "start is not evidence that the starter is ready, and a positive "
                "pressure reading is not evidence of self-sustaining operation. A "
                "timer can catch a missing event faster than a slow temperature probe. "
                "Do not invent trip numbers here; Safety and the leads must supply the "
                "limits after the rotor, materials and test enclosure are understood.",
                (
                    Question(
                        "start_permissives",
                        "What must be true before leaving CHECKS for STARTING?",
                        evidence=False,
                        hint="List observable evidence, such as valid sensors, closed shutoff and a safe test state.",
                    ),
                    Question(
                        "abort_triggers",
                        "Name three fault conditions that should move the controller to FAULT.",
                        evidence=False,
                        hint="Use conditions, not thresholds: missing RPM, lost power, invalid EGT, overspeed, etc.",
                    ),
                    Question(
                        "missing_rpm_behavior",
                        "If RPM disappears while fuel is commanded, what should the model do and why?",
                        evidence=False,
                        role="decision",
                    ),
                ),
            ),
            Step(
                "plant",
                "4. Try a one-minute plant model with synthetic numbers",
                "The simplest plant model says that a measured quantity moves toward a "
                "commanded quantity with a time constant: x_next = x + (target - x) * "
                "(1 - exp(-dt/tau)). It is a teaching approximation for a Simulink "
                "first-order block. The same shape can represent RPM or a sensor lag, "
                "but the values below are not engine data. Choose a small, clearly "
                "labeled example, run the calculation, and explain what it cannot tell "
                "you about combustion, compressor maps, turbine torque or safety.",
                (
                    Question(
                        "starting_rpm",
                        "Synthetic starting value for the calculation",
                        kind="number", units="rpm", minimum=0, maximum=100000,
                        required=False, evidence=False,
                        hint="Illustration only. Do not enter an operating threshold.",
                    ),
                    Question(
                        "commanded_rpm",
                        "Synthetic commanded value for the calculation",
                        kind="number", units="rpm", minimum=0, maximum=100000,
                        required=False, evidence=False,
                        hint="Illustration only; label it as a model command, not a setpoint.",
                    ),
                    Question(
                        "plant_tau_s",
                        "Synthetic plant time constant",
                        kind="number", units="s", minimum=0.001, maximum=100,
                        required=False, evidence=False,
                        hint="Pick a value to explore response speed; it is not measured engine behavior.",
                    ),
                    Question(
                        "sample_period_s",
                        "Synthetic controller sample period",
                        kind="number", units="s", minimum=0.000001, maximum=10,
                        required=False, evidence=False,
                        hint="Use the same units as the time constant.",
                    ),
                    Question(
                        "model_limitations",
                        "What does this simple model leave out?",
                        evidence=False,
                        hint=("Mention at least two of: fuel/air mixing, ignition, compressor/turbine maps, "
                              "shaft inertia, sensor noise, actuator limits, faults."),
                    ),
                ),
            ),
            Step(
                "handoff",
                "5. Leave a handoff that another teammate can use",
                "A good controls handoff is short and checkable. It includes the signal "
                "names, the state transitions, the synthetic model assumptions and one "
                "question for the leads. The next person should be able to reproduce "
                "your result in Simulink without guessing what an arrow means. Keep any "
                "unknown as UNKNOWN or TBD; a blank is harder to review.",
                (
                    Question(
                        "handoff_summary",
                        "Summarize the control concept in three to five sentences.",
                        evidence=False,
                    ),
                    Question(
                        "lead_decision",
                        "What decision or safety question should the leads review next?",
                        evidence=False,
                        role="decision",
                    ),
                    Question(
                        "next_step",
                        "What is the next small, desk-only step for the controls team?",
                        evidence=False,
                        role="next_step",
                    ),
                ),
            ),
        ),
        calculations=(
            Calculation(
                "rpm_one_sample",
                "Synthetic RPM after one first-order plant sample",
                ("starting_rpm", "commanded_rpm", "plant_tau_s", "sample_period_s"),
                lambda starting_rpm, commanded_rpm, plant_tau_s, sample_period_s:
                    first_order_step(starting_rpm, commanded_rpm, plant_tau_s, sample_period_s),
                units="rpm",
                method="x_next = x + (target - x) * (1 - exp(-dt/tau))",
                version="1",
                limitations=("Synthetic first-order response only. It is not an engine, "
                             "shaft-torque, combustion, map, sensor or safety prediction."),
            ),
        ),
    )


if __name__ == "__main__":
    raise SystemExit(run_lesson(build_lesson(), __file__))
