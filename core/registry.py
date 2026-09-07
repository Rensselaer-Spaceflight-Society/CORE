"""
The variable registry -- this repo's Interface Control Document.

config/variables.yaml lists every number that crosses a boundary between two
people's work: its SI unit, what it means, and which module owns it. If a value
is not in there, it is not a shared number, and it should stay a local variable
inside one module.

The registry is what turns "who has the latest bearing seat diameter?" from a
Slack thread into a lookup.

Naming rule, enforced by tests: every variable name ends in its SI unit.
    d2_m, mdot_kg_s, T04_K, P03_Pa, N_rpm, sigma_root_Pa, eta_c_isen (-)
Anything ending in _mm, _bar, _psi, _degC or _rpm-that-should-be-rad-s is a bug
waiting to happen. RPM is the one non-SI exception, allowed because every
bearing and turbo datasheet on earth uses it; convert at the point of use.
"""

from __future__ import annotations
import os
import math
import yaml

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(HERE, "config")

# Suffixes we accept as declaring a unit. Keep this list short and boring.
KNOWN_UNITS = {
    "m": "metre",
    "m2": "square metre",
    "m3": "cubic metre",
    "kg": "kilogram",
    "s": "second",
    "K": "kelvin",
    "Pa": "pascal",
    "N": "newton",
    "Nm": "newton metre",
    "W": "watt",
    "J": "joule",
    "rpm": "revolutions per minute (allowed exception -- convert at use)",
    "rad_s": "radian per second",
    "m_s": "metre per second",
    "kg_s": "kilogram per second",
    "N_per_kg_s": "newton per kilogram per second (specific thrust)",
    "Pa_s": "pascal second (dynamic viscosity)",
    "per_K": "per kelvin (thermal expansion coefficient)",
    "W_m2": "watt per square metre (heat flux)",
    "m3_s": "cubic metre per second",
    "kg_m3": "kilogram per cubic metre",
    "J_kg": "joule per kilogram",
    "J_kgK": "joule per kilogram kelvin",
    "kg_m2": "kilogram square metre",
    "N_m": "newton per metre",
    "m2_rpm2": "square metre times rpm squared (AN^2 convention)",
    "mm_rpm": "millimetre times rpm (bearing DN convention)",
    "deg": "degree",
    "hr": "hour",
    "frac": "dimensionless fraction 0-1",
    "isen": "dimensionless isentropic efficiency",
    "ratio": "dimensionless ratio",
    "count": "dimensionless integer count",
    "flag": "boolean 0/1",
    "-": "dimensionless",
}


class RegistryError(Exception):
    pass


def load_yaml(name):
    path = os.path.join(CONFIG, name)
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_registry():
    raw = load_yaml("variables.yaml")
    out = {}
    for name, meta in raw.items():
        if not isinstance(meta, dict):
            raise RegistryError(f"variables.yaml: '{name}' must be a mapping with unit/desc/owner")
        meta.setdefault("unit", unit_of(name))
        meta.setdefault("desc", "")
        meta.setdefault("owner", "unassigned")
        meta.setdefault("frozen_at", None)
        out[name] = meta
    return out


def unit_of(name):
    """Pull the declared unit off the end of a variable name."""
    for suffix in sorted(KNOWN_UNITS, key=len, reverse=True):
        if suffix == "-":
            continue
        if name.endswith("_" + suffix):
            return suffix
    return "-"


def has_declared_unit(name):
    return unit_of(name) != "-" or name.endswith("_frac") or name.endswith("_ratio")


def _coerce_numbers(d, where):
    """YAML 1.1 does not parse 43.1e6 as a float -- it needs 43.1e+6 -- and that
    trips up everyone at least once. Coerce quietly rather than failing three
    modules downstream with a baffling type error."""
    out = {}
    for k, v in d.items():
        if isinstance(v, str):
            try:
                v = float(v)
            except ValueError:
                raise RegistryError(
                    f"{where}: '{k}' has the value {v!r}, which is not a number. "
                    f"Every entry in this file must be numeric."
                )
        elif isinstance(v, bool):
            v = 1.0 if v else 0.0
        elif not isinstance(v, (int, float)):
            raise RegistryError(f"{where}: '{k}' must be a number, got {type(v).__name__}")
        if not math.isfinite(v):
            raise RegistryError(f"{where}: {k} must be finite")
        out[k] = float(v)
    return out


def load_seed():
    """Human-chosen design values. Frozen at Gate A."""
    return _coerce_numbers(load_yaml("seed.yaml"), "config/seed.yaml")


def load_limits():
    """Safety-owned hard limits. Every module asserts against these; CI fails if
    any is violated. This is the Safety Director's veto, expressed as code."""
    return _coerce_numbers(load_yaml("limits.yaml"), "config/limits.yaml")


def load_baseline():
    """Published KJ66 numbers, used as the regression oracle."""
    return load_yaml("kj66_baseline.yaml")
