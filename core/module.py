"""
The module contract.

Every component of the engine is one Python function wrapped in @module.
The decorator does three jobs:

  1. Declares what the function READS and WRITES, which is how the solver
     builds the dependency graph. You never call another module directly
     and you never thread a dict through a chain -- you declare, and the
     runner works out the order.

  2. Records who owns it (primary + second) and how mature it is, so that
     `python run.py --status` can print an honest maturity board.

  3. Validates at run time that you actually wrote what you promised, and
     that you did not read anything you did not declare. This is what stops
     the "who changed my number?" class of bug.

Writing a module:

    from core.module import module

    @module(
        reads=["mdot_kg_s", "T04_K"],
        writes=["A8_m2"],
        owner="CSYS-1", second="CSYS-2",
        status="draft",
        title="Exhaust nozzle sizing",
    )
    def nozzle(s):
        area = s["mdot_kg_s"] * 0.01 / s["T04_K"]
        return {"A8_m2": area}

`s` is the shared state. Read from it with s["name"]. Return a dict of the
variables you promised to write. That is the whole contract.
"""

from __future__ import annotations
import functools
import inspect
import math
from collections.abc import Mapping

REGISTERED: dict[str, "ModuleSpec"] = {}

VALID_STATUS = ("stub", "draft", "verified")


class ModuleSpec:
    """Everything the solver and the status board need to know about one module."""

    def __init__(self, fn, reads, writes, owner, second, status, title, notes, tier):
        self.fn = fn
        self.name = fn.__name__
        self.reads = tuple(reads)
        self.writes = tuple(writes)
        self.owner = owner
        self.second = second
        self.status = status
        self.title = title
        self.notes = notes
        self.tier = tier
        self.source_file = inspect.getsourcefile(fn) or "?"

    def __repr__(self):
        return f"<ModuleSpec {self.name} [{self.status}] {len(self.reads)}->{len(self.writes)}>"

    def run(self, state):
        """Call the module with a read-guarded view of state, validate its output."""
        view = _TrackedState(state, allowed=set(self.reads), module_name=self.name)
        out = self.fn(view)

        if not isinstance(out, dict):
            raise ModuleError(
                f"{self.name}: must return a dict of {{variable: value}}, got {type(out).__name__}."
            )

        promised = set(self.writes)
        actual = set(out)

        missing = promised - actual
        if missing:
            raise ModuleError(
                f"{self.name}: declared it writes {sorted(missing)} but did not return "
                f"{'them' if len(missing) > 1 else 'it'}. Either compute the value or "
                f"remove it from writes=."
            )

        extra = actual - promised
        if extra:
            raise ModuleError(
                f"{self.name}: returned {sorted(extra)} which {'are' if len(extra) > 1 else 'is'} "
                f"not in its writes= list. Add {'them' if len(extra) > 1 else 'it'} to writes= so "
                f"the rest of the team can see where {'they come' if len(extra) > 1 else 'it comes'} from."
            )

        for k, v in out.items():
            if isinstance(v, bool):
                continue
            if not isinstance(v, (int, float)):
                raise ModuleError(
                    f"{self.name}: '{k}' is a {type(v).__name__}. State variables must be "
                    f"plain numbers (or bool). Put arrays and objects in out/ as a file instead."
                )
            if k.endswith("_count") and (not math.isfinite(v) or v < 0 or int(v) != v):
                raise ModuleError(f"{self.name}: {k} must be a nonnegative integer count")
            if not math.isfinite(v):
                raise ModuleError(f"{self.name}: '{k}' must be finite (NaN/infinity rejected).")

        return out


class ModuleError(Exception):
    pass


class _TrackedState(Mapping):
    """Immutable snapshot exposing only declared dependencies through all APIs."""
    def __init__(self, backing, allowed, module_name):
        self._backing = {k: backing[k] for k in allowed if k in backing}
        self._allowed = frozenset(allowed)
        self._module = module_name

    def __getitem__(self, key):
        if key not in self._allowed:
            raise ModuleError(f"{self._module}: undeclared read '{key}'")
        return self._backing[key]

    def __iter__(self):
        return iter(self._backing)

    def __len__(self):
        return len(self._backing)

    def __setitem__(self, key, value):
        raise ModuleError(f"{self._module}: state is read-only; return outputs")


def module(*, reads, writes, owner, second=None, status="stub", title="", notes="", tier=0):
    """Register a function as an engine module. See the docstring at the top of this file."""
    if status not in VALID_STATUS:
        raise ValueError(f"status must be one of {VALID_STATUS}, got '{status}'")
    if not writes:
        raise ValueError("a module that writes nothing has no effect -- declare its outputs")

    def deco(fn):
        spec = ModuleSpec(fn, reads, writes, owner, second, status, title, notes, tier)
        if spec.name in REGISTERED:
            raise ValueError(
                f"two modules are both named '{spec.name}'. Module names must be unique "
                f"across the whole repo."
            )
        REGISTERED[spec.name] = spec

        @functools.wraps(fn)
        def wrapper(s):
            return fn(s)

        wrapper.spec = spec
        return wrapper

    return deco
