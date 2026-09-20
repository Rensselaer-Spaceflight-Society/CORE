"""Small electrical arithmetic helpers for the C8 teaching lesson.

These functions only express unit relationships.  They do not select a fuse,
wire, connector, battery, driver or power supply, and they cannot approve an
energized test.
"""

from __future__ import annotations

import math


def _finite_nonnegative(value: float, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"{name} must be numeric") from None
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{name} must be finite and non-negative")
    return number


def power_w(voltage_v: float, current_a: float) -> float:
    """Return electrical power in watts from volts and amps."""
    return _finite_nonnegative(voltage_v, "voltage_v") * _finite_nonnegative(current_a, "current_a")


def energy_wh(power_w_value: float, duration_s: float) -> float:
    """Return energy in watt-hours from power in watts and seconds."""
    power = _finite_nonnegative(power_w_value, "power_w")
    duration = _finite_nonnegative(duration_s, "duration_s")
    return power * duration / 3600.0


def total_power_w(*loads_w: float) -> float:
    """Add explicitly supplied load powers; no implicit load is invented."""
    if not loads_w:
        raise ValueError("supply at least one load")
    return sum(_finite_nonnegative(load, "load_power_w") for load in loads_w)
