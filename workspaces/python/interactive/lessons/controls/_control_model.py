"""Small, deterministic teaching model for the C4 controls lesson.

This is deliberately a *toy* model.  It is useful for learning how a plant,
sensor and proportional command fit together, and for creating synthetic
signals for a future Simulink model.  It is not a combustor, turbine, rotor,
or safety model and must not be connected to an actuator.
"""

from __future__ import annotations

import math


def _finite_positive(value: float, name: str) -> float:
    """Return a finite positive value or explain the bad model input."""
    if isinstance(value, bool) or not math.isfinite(float(value)) or value <= 0:
        raise ValueError(f"{name} must be a finite number greater than zero")
    return float(value)


def first_order_step(current: float, target: float, time_constant_s: float,
                     sample_period_s: float) -> float:
    """Advance a first-order state by one sample.

    The update is the exact zero-order-hold solution of
    ``dx/dt = (target - x) / tau``.  Using ``-expm1`` keeps the fraction
    accurate for very small sample periods.  ``current`` and ``target`` are
    intentionally unit-agnostic; the lesson uses rpm, but the same equation
    can illustrate a temperature or pressure signal.
    """
    tau = _finite_positive(time_constant_s, "time_constant_s")
    dt = _finite_positive(sample_period_s, "sample_period_s")
    if isinstance(current, bool) or isinstance(target, bool):
        raise ValueError("current and target must be numeric")
    current = float(current)
    target = float(target)
    if not math.isfinite(current) or not math.isfinite(target):
        raise ValueError("current and target must be finite")
    fraction = -math.expm1(-dt / tau)
    return current + fraction * (target - current)


def proportional_command(target: float, measured: float, gain: float,
                         feedforward: float = 0.0) -> float:
    """Return a normalized, clipped teaching command in the range 0..1.

    This is the algebra that a student can translate into a Simulink
    proportional block.  It has no integral, derivative, anti-windup,
    startup sequencing, limits, or fault handling.  Those are deliberate
    follow-on design tasks and are not silently supplied here.
    """
    if isinstance(target, bool) or isinstance(measured, bool) or isinstance(gain, bool):
        raise ValueError("target, measured and gain must be numeric")
    target = float(target)
    measured = float(measured)
    gain = float(gain)
    feedforward = float(feedforward)
    if not all(math.isfinite(x) for x in (target, measured, gain, feedforward)):
        raise ValueError("controller inputs must be finite")
    if target <= 0 or gain < 0:
        raise ValueError("target must be positive and gain cannot be negative")
    raw = feedforward + gain * (target - measured) / target
    return min(1.0, max(0.0, raw))


def simulate_step(target: float, starting_value: float, time_constant_s: float,
                  sample_period_s: float, steps: int) -> list[tuple[float, float]]:
    """Return ``(time_s, value)`` samples for a constant target step."""
    if isinstance(steps, bool) or int(steps) != steps or steps < 1:
        raise ValueError("steps must be a positive integer")
    dt = _finite_positive(sample_period_s, "sample_period_s")
    value = float(starting_value)
    if not math.isfinite(value) or not math.isfinite(float(target)):
        raise ValueError("target and starting_value must be finite")
    samples = [(0.0, value)]
    for index in range(1, int(steps) + 1):
        value = first_order_step(value, target, time_constant_s, dt)
        samples.append((index * dt, value))
    return samples
