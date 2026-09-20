"""Checks for the electrical lesson and its unit arithmetic."""

from pathlib import Path
import sys

import pytest

REPO = Path(__file__).resolve().parents[3]
PLATFORM = REPO / "workspaces" / "python" / "interactive"
sys.path.insert(0, str(PLATFORM))

from learning_model import calculate, questions, validate_lesson
from runtime import discover
from lessons.electrical._electrical_model import energy_wh, power_w, total_power_w


def test_c8_is_discoverable_and_diagram_is_local():
    lesson, source = discover()["C8-ELEC"]
    validate_lesson(lesson)
    assert source.name == "c8_electrical_system.py"
    assert (source.parent / "electrical_overview.svg").exists()
    assert len(questions(lesson)) >= 25


def test_power_and_energy_units():
    assert power_w(12, 2) == pytest.approx(24)
    assert energy_wh(24, 30) == pytest.approx(0.2)
    assert total_power_w(24, 10, 2) == pytest.approx(36)
    with pytest.raises(ValueError):
        power_w(-1, 2)
    with pytest.raises(ValueError):
        energy_wh(24, -1)
    with pytest.raises(ValueError):
        total_power_w()


def test_electrical_calculations_need_explicit_inputs():
    lesson, _ = discover()["C8-ELEC"]
    answers = {
        "logic_voltage_v": {"status": "answered", "value": 5},
        "logic_current_a": {"status": "answered", "value": 0.2},
        "pump_voltage_v": {"status": "answered", "value": 12},
        "pump_current_a": {"status": "answered", "value": 2},
        "starter_voltage_v": {"status": "answered", "value": 12},
        "starter_peak_current_a": {"status": "answered", "value": 10},
        "starter_peak_duration_s": {"status": "answered", "value": 30},
    }
    results = {result["id"]: result for result in calculate(lesson, answers)}
    assert results["logic_power"]["value"] == pytest.approx(1)
    assert results["pump_power"]["value"] == pytest.approx(24)
    assert results["starter_peak_power"]["value"] == pytest.approx(120)
    assert results["starter_peak_energy"]["value"] == pytest.approx(1)
    missing = calculate(lesson, {"logic_voltage_v": answers["logic_voltage_v"]})
    assert missing[0]["status"] == "missing_inputs"


def test_diagram_keeps_power_measurement_command_and_safety_labels():
    svg = (PLATFORM / "lessons" / "electrical" / "electrical_overview.svg").read_text(encoding="utf-8")
    for label in ("BATTERY / CHARGER", "RPM SENSOR", "EGT + CONDITIONER",
                  "MICROCONTROLLER", "EMERGENCY INHIBIT", "OPTIONAL OUTPUTS",
                  "DATA LOGGING", "V / I MONITOR", "ratings TBD"):
        assert label in svg
