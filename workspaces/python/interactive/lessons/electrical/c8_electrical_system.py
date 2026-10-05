"""C8-ELEC: turn a list of electrical parts into a reviewable system concept.

This is a desk-only lesson.  It teaches a newcomer to distinguish power,
measurement and command paths, record unknown ratings, and reason through
failure behavior before drawing an energized wiring build.
"""

from pathlib import Path
import sys

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parents[2]))
sys.path.insert(0, str(_HERE))
from runtime import Calculation, Lesson, Question, Step, run_lesson

from _electrical_model import energy_wh, power_w, total_power_w


def build_lesson():
    return Lesson(
        id="C8-ELEC",
        version="1.0",
        title="Build the electrical power tree and interface table",
        review_role=("Electrical/system integration lead; Safety lead reviews inhibit and fault behavior; "
                     "Controls and Instrumentation leads review signal compatibility"),
        minutes="30-45",
        prerequisites=(
            "Read the local electrical diagram before answering.",
            "Use UNKNOWN or NOT FOUND when a part number, load, rating or return path is not established.",
            "Do not energize a circuit, connect fuel, run a starter, or copy a rating from an unrelated part.",
        ),
        sources=(
            "docs/project/dp2-review.md",
            "workspaces/coordination/interfaces.md",
            "workspaces/python/interactive/lessons/controls/c4_control_system.py",
            "workspaces/combustion-systems/C6-instrumentation.md",
            "https://www.ti.com/lit/an/sbaa632/sbaa632.pdf",
            "https://www.ti.com/product/ADS1115",
            "https://www.mathworks.com/help/simulink/complex-logic.html",
        ),
        steps=(
            Step(
                "power-path",
                "1. Trace one complete power path",
                "Voltage is a difference between two points; current needs a complete "
                "path back to its source. Power is P = V x I. The battery is not a "
                "magic 12 V box: its voltage changes with chemistry, state of charge, "
                "temperature, charger and load sag. A fuse limits fault energy; it is "
                "not a voltage regulator, and software cannot replace a physical "
                "disconnect. Start by tracing battery positive -> protection/disconnect "
                "-> one load -> return. Then do the same for the logic/sensor branch. "
                "Never assume a sensor signal return and protective chassis earth are "
                "the same connection without documenting the design.",
                (
                    Question(
                        "battery_candidate",
                        "What battery or supply candidate is being considered, and what evidence is still missing?",
                        hint=("Record chemistry, nominal voltage, usable voltage range, capacity/current data, "
                              "source and limits. A bare '12 V battery' is not enough."),
                    ),
                    Question(
                        "power_path_table",
                        "Write a first power-tree table for battery, protection, starter, pump, logic and returns.",
                        evidence=False,
                        hint=("Use rows: block | source | destination | return | protection question | "
                              "rating status. Use /text; leave ratings TBD."),
                    ),
                    Question(
                        "return_strategy",
                        "Where do signal returns, high-current returns and protective earth/chassis connect - or remain separate?",
                        evidence=False,
                        role="decision",
                    ),
                ),
                visual="electrical_overview.svg",
            ),
            Step(
                "load-budget",
                "2. Make a load budget without inventing ratings",
                "For a fictional example only, 12 V x 2 A = 24 W, and 24 W for 30 "
                "seconds is 0.20 Wh. That arithmetic does not tell us whether a "
                "pump starts at 2 A, whether a starter stalls at 2 A, or whether a "
                "battery can supply the transient without sag. Record normal, peak or "
                "stall current, voltage range, duty cycle, source and uncertainty for "
                "each load. Keep the starter and pump branches separate; a total that "
                "hides their peaks cannot size a protection question.",
                (
                    Question(
                        "logic_voltage_v", "Candidate logic/sensor supply voltage (optional)",
                        kind="number", units="V", minimum=0, maximum=100,
                        required=False, hint="Use a datasheet value and note whether it is nominal or allowed range.",
                    ),
                    Question(
                        "logic_current_a", "Candidate logic/sensor current (optional)",
                        kind="number", units="A", minimum=0, maximum=100,
                        required=False, hint="State whether this is normal or peak current.",
                    ),
                    Question(
                        "pump_voltage_v", "Candidate pump supply voltage (optional)",
                        kind="number", units="V", minimum=0, maximum=100,
                        required=False,
                    ),
                    Question(
                        "pump_current_a", "Candidate pump current (optional)",
                        kind="number", units="A", minimum=0, maximum=1000,
                        required=False,
                    ),
                    Question(
                        "starter_voltage_v", "Candidate starter supply voltage (optional)",
                        kind="number", units="V", minimum=0, maximum=100,
                        required=False,
                    ),
                    Question(
                        "starter_peak_current_a", "Candidate starter peak or stall current (optional)",
                        kind="number", units="A", minimum=0, maximum=2000,
                        required=False,
                    ),
                    Question(
                        "starter_peak_duration_s", "Illustrative starter peak duration (optional)",
                        kind="number", units="s", minimum=0, maximum=3600,
                        required=False,
                        hint="This is for energy arithmetic, not an approved starter timer.",
                    ),
                    Question(
                        "load_budget_table",
                        "Write the load-budget rows for logic, pump, starter, optional ignition and any auxiliary.",
                        evidence=False,
                        hint=("Use columns: load | normal current | peak/start/stall current | voltage range | "
                              "duty cycle | source | return/protection question | unknown. Do not fill an unknown with zero. Use /text."),
                    ),
                    Question(
                        "load_unknowns",
                        "Which load, duty cycle, voltage range or protection rating is still NOT FOUND?",
                        evidence=False,
                        role="decision",
                    ),
                ),
            ),
            Step(
                "interfaces",
                "3. Separate power wiring, measurement wiring and command wiring",
                "A microcontroller pin carries a logic signal; it does not directly "
                "power a starter, pump or igniter. A driver, relay, contactor or other "
                "reviewed interface must carry the load current, and inductive loads "
                "need a documented transient-control path. A tachometer output and an "
                "EGT conditioner output also need compatible voltage, reference, "
                "frequency/range and validity behavior. Use the C4 signal names as a "
                "coordination starting point, but let Instrumentation own the exact "
                "sensor and conditioner choice. Do not connect a nominal 12 V signal to "
                "a logic-level input by assumption.",
                (
                    Question(
                        "io_table",
                        "Write an I/O table for RPM, EGT, fuel command, start enable, fault status and shutdown inhibit.",
                        evidence=False,
                        hint=("Rows: signal | source | destination | power/reference | interface type | logic level/range | "
                              "update timing | invalid-data behavior. Use /text."),
                    ),
                    Question(
                        "rpm_interface",
                        "What RPM interface is being considered, and what must Instrumentation still verify?",
                        hint=("A Hall/gear-tooth idea is a starting point, not proof of gap, target, frequency, "
                              "output type, pull-up, shielding or mounting suitability."),
                    ),
                    Question(
                        "egt_interface",
                        "What EGT sensor/conditioner interface is being considered, and what is still unknown?",
                        hint=("Record thermocouple type if known, conditioner supply/output, reference and response limits."),
                    ),
                    Question(
                        "driver_boundary",
                        "Which outputs require a power driver instead of a microcontroller pin, and what protection question follows?",
                        evidence=False,
                        role="decision",
                    ),
                ),
            ),
            Step(
                "failure-walkthrough",
                "4. Walk through failures before drawing a powered build",
                "The safe result of a failure is not always 'turn everything off' in the "
                "same way. A battery sag may reset logic while high-current loads remain "
                "connected; an unplugged sensor may look like zero, stale data or an "
                "out-of-range value; a stuck output needs an independent inhibit path. "
                "For each case, say what the controller requests, what hardware "
                "physically prevents, what the operator sees, and what remains a lead "
                "decision. This is a design review exercise, not an approval to test.",
                (
                    Question("battery_sag_response", "What should happen when battery voltage sags or the controller resets?", evidence=False),
                    Question("sensor_unplugged_response", "What should happen when RPM or EGT is unplugged or invalid?", evidence=False),
                    Question("controller_reset_response", "What output state should be guaranteed during a microcontroller reset?", evidence=False),
                    Question("stuck_output_response", "How would the system inhibit a stuck pump/starter/ignition command?", evidence=False),
                    Question("manual_stop_response", "Trace the manual emergency-stop path from operator action to each relevant load.", evidence=False),
                    Question("safety_open_question", "Which failure behavior needs Safety or the lead to decide before implementation?", evidence=False, role="decision"),
                ),
            ),
            Step(
                "bring-up",
                "5. Leave a staged, non-energized bring-up checklist",
                "The first electrical milestone is a drawing review and continuity "
                "reasoning. A useful staged schematic labels every source, destination, "
                "return, connector and protection question. It does not require a large "
                "CAD package: the repository SVG is both viewable and editable source, "
                "and the table you write can become the next revision. Before any power "
                "is applied, check that the drawing agrees with the I/O table, no logic "
                "pin is asked to carry load current, every load has a return, emergency "
                "inhibit behavior is visible and unresolved ratings stay marked TBD.",
                (
                    Question(
                        "bring_up_checklist",
                        "Write five non-energized checks for the next design review.",
                        evidence=False,
                        hint=("Include drawing consistency, polarity/return continuity, connector identity, "
                              "inhibit path and independent review. No powered test steps yet."),
                    ),
                    Question(
                        "schematic_revision",
                        "What should the next schematic revision add or correct?",
                        evidence=False,
                    ),
                    Question(
                        "electrical_handoff",
                        "Summarize the most useful electrical finding for the team in three sentences.",
                        evidence=False,
                    ),
                    Question(
                        "electrical_next_step",
                        "What is the next small desk-only task, and who must review it?",
                        evidence=False,
                        role="next_step",
                    ),
                ),
            ),
        ),
        calculations=(
            Calculation(
                "logic_power",
                "Logic branch power",
                ("logic_voltage_v", "logic_current_a"),
                lambda logic_voltage_v, logic_current_a: power_w(logic_voltage_v, logic_current_a),
                units="W",
                method="P = V x I",
                version="1",
                limitations="Candidate arithmetic only; does not select a regulator, wire, fuse or battery.",
            ),
            Calculation(
                "pump_power",
                "Pump branch power",
                ("pump_voltage_v", "pump_current_a"),
                lambda pump_voltage_v, pump_current_a: power_w(pump_voltage_v, pump_current_a),
                units="W",
                method="P = V x I",
                version="1",
                limitations="Candidate arithmetic only; pump starting and stall behavior remain unknown.",
            ),
            Calculation(
                "starter_peak_power",
                "Starter peak power",
                ("starter_voltage_v", "starter_peak_current_a"),
                lambda starter_voltage_v, starter_peak_current_a: power_w(starter_voltage_v, starter_peak_current_a),
                units="W",
                method="P_peak = V x I_peak",
                version="1",
                limitations="Peak/stall current must come from the exact candidate and conditions; this is not a rating.",
            ),
            Calculation(
                "starter_peak_energy",
                "Illustrative starter peak energy",
                ("starter_voltage_v", "starter_peak_current_a", "starter_peak_duration_s"),
                lambda starter_voltage_v, starter_peak_current_a, starter_peak_duration_s:
                    energy_wh(power_w(starter_voltage_v, starter_peak_current_a), starter_peak_duration_s),
                units="Wh",
                method="E = P x t / 3600, with P in W and t in seconds",
                version="1",
                limitations="Illustrative energy only; it is not an approved starter time or battery-sizing result.",
            ),
        ),
    )


if __name__ == "__main__":
    raise SystemExit(run_lesson(build_lesson(), __file__))
