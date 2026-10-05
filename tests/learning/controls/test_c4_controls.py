"""Meaningful checks for the C4 controls lesson and its teaching model."""

from pathlib import Path
import sys

import pytest

REPO = Path(__file__).resolve().parents[3]
PLATFORM = REPO / "workspaces" / "python" / "interactive"
sys.path.insert(0, str(PLATFORM))

from learning_model import calculate, questions, validate_lesson
from runtime import discover
from lessons.controls._control_model import (first_order_step,
                                             proportional_command,
                                             simulate_step)


def test_c4_is_discoverable_and_visual_is_local():
    lesson, source = discover()["C4"]
    validate_lesson(lesson)
    assert source.name == "c4_control_system.py"
    assert (source.parent / "control_loop.svg").exists()
    assert len(questions(lesson)) >= 15


def test_first_order_step_has_expected_limits():
    assert first_order_step(0, 100, 1, 1) == pytest.approx(63.21205588)
    assert first_order_step(100, 0, 1, 1) == pytest.approx(36.78794412)
    with pytest.raises(ValueError):
        first_order_step(0, 100, 0, 1)
    with pytest.raises(ValueError):
        first_order_step(0, 100, 1, 0)


def test_proportional_command_clips_without_hiding_bad_inputs():
    assert proportional_command(100, 0, 0.5) == pytest.approx(0.5)
    assert proportional_command(100, -200, 1) == 1.0
    assert proportional_command(100, 100, 1, 0.2) == pytest.approx(0.2)
    with pytest.raises(ValueError):
        proportional_command(0, 10, 1)
    with pytest.raises(ValueError):
        proportional_command(100, 10, -1)


def test_simulate_step_is_monotonic_toward_target():
    samples = simulate_step(100, 0, 2, 0.5, 4)
    values = [value for _, value in samples]
    assert values[0] == 0
    assert all(left < right < 100 for left, right in zip(values, values[1:]))
    assert samples[-1][0] == pytest.approx(2.0)


def test_c4_calculation_uses_answers_and_reports_missing_inputs():
    lesson, _ = discover()["C4"]
    answers = {
        "starting_rpm": {"status": "answered", "value": 0},
        "commanded_rpm": {"status": "answered", "value": 100},
        "plant_tau_s": {"status": "answered", "value": 1},
        "sample_period_s": {"status": "answered", "value": 1},
    }
    result = calculate(lesson, answers)[0]
    assert result["status"] == "computed"
    assert result["value"] == pytest.approx(63.21205588)
    result = calculate(lesson, {"starting_rpm": answers["starting_rpm"]})[0]
    assert result["status"] == "missing_inputs"
