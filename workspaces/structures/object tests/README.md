# About `object-example.py`

[Structures team page](../README.md) · [Task code map](../TASK-CODE-MAP.md)

`object-example.py` in this folder is **existing student work and it has deliberately
not been edited**. It is the record of what was actually taught in a structures
session — dataclasses, a hoop-stress method, and a shaft class that was still being
written when the session ended. That history is worth more intact than tidied, so the
new guided lessons were built alongside it rather than on top of it.

This note explains what it does, the one thing that stops it running, and why its
numbers must not be carried into a CORE drawing.

## What it teaches, and teaches well

It puts a formula inside the object it describes. `PressureVessel` holds its own
thickness, bore and pressures, and `hoop()` uses them. That is the right instinct: the
number and the geometry it came from stay together, which is exactly the habit the
S3-STRESS lesson is built around.

## The one defect, and the one-line fix

The file does not currently parse. Python reports:

```
File "workspaces/structures/object tests/object-example.py", line 34
    self.polar_moment_inertia = np.pi*
                                      ^
SyntaxError: invalid syntax
```

Line 34 is an expression that was never finished — `np.pi*` with nothing after the
operator. Everything above it is fine; `SyntaxError` is raised for the whole file, so
the working `PressureVessel` class above cannot run either. (The bare `return` at the
end of `funct` is legal Python, not a second error. It returns `None`.)

For a solid round shaft the intended quantity is the **polar second moment of area**:

```python
J = pi * r**4 / 2        # equivalently pi * d**4 / 32,  units m^4
```

so line 34 completes as:

```python
self.polar_moment_inertia = np.pi * self.radius**4 / 2
```

**Whoever wrote this file owns that edit.** It is left for them to make rather than
applied here, because a one-line completion in somebody else's half-written class is
the kind of change that quietly erases what they were thinking. The structures lead
can confirm it in thirty seconds. Nothing in the repository currently imports or runs
this file, and CI does not compile this folder, so the defect blocks nothing.

Worth noticing while you are there: the attribute name `polar_moment_inertia` is one
letter away from *mass* moment of inertia, which is a different quantity in different
units (kg·m², not m⁴). S4-BEND spends a step on that distinction because it is the
most common way a structures calculation goes silently wrong.

## Its numbers are EXAMPLE loads, not CORE loads

```python
combustor = PressureVessel(1e-3, 0.2, 2e6, 0)   # t = 1 mm, ID = 200 mm, 2 MPa, 0 Pa outside
print('Hoop Stress (Pa) = ', combustor.hoop())  # 200 MPa on the inner radius
```

Those are teaching values chosen so the arithmetic is easy to follow. They are **not**
the CORE candidate engine:

| | This example | CORE candidate casing (DP-2 screen) |
|---|---|---|
| Pressure difference | 2 MPa | ≈ 62.2 kPa |
| Inner diameter | 200 mm | 149.4 mm |
| Wall thickness | 1 mm | 1.5 mm |
| Hoop stress, inner radius | **200 MPa** | **≈ 3.10 MPa** |

A factor of about 65. The candidate figures come from
[`docs/project/checks/dp2_screen.py`](../../../docs/project/checks/dp2_screen.py)
(compressor delivery P3 = 163.51 kPa absolute against 101.325 kPa ambient) and the
casing envelope proposed in [`docs/project/dp2-review.md`](../../../docs/project/dp2-review.md).
Both remain **candidates under review**, not approved design values.

Two smaller notes on the example, both of which the lesson turns into habits:

- It passes `pressure_ext = 0`, meaning a perfect vacuum outside. If the 2 MPa was
  meant as a *gauge* pressure then the difference is the same either way — which is
  precisely why S3-STRESS asks for two absolute pressures and subtracts them where you
  can see it happen.
- `hoop()` uses `inner_diam * 0.5`, the **inner** radius. Kelly, *Solid Mechanics
  Part I* §7.3 allows the inner, outer or mean radius for a thin wall; the AFFDL
  *Stress Analysis Manual* §8.3.1 uses the mean. S3-STRESS reports both so the gap
  between them is visible — about 1% on the candidate casing. That gap measures the
  idealisation. It is not a safety margin.
- There is no guard on `thickness = 0` or a negative thickness, and no check that
  `r/t > 10` before applying a thin-wall formula. The lesson helpers raise an
  explanatory error in both cases instead of returning a plausible-looking number.

## Where the structured version lives

The guided lessons are separate files and do not modify anything in this folder:

- [`S3-STRESS`](../../python/interactive/lessons/structures/pressure_wall.py) — free-body
  diagram, input ledger, thin-wall hoop and axial stress, applicability.
- [`S4-BEND`](../../python/interactive/lessons/structures/beam_and_shaft.py) — bending,
  torsion, and the three quantities called I. This is where the unfinished `Shaft`
  idea is developed properly.
- [`C2-FAB`](../../python/interactive/lessons/structures/fabrication_coupon.py) —
  fabrication feasibility and weld development.

Run one with, for example:

```
python workspaces/python/interactive/lessons/structures/pressure_wall.py --preview
```

Completing any of them is learning evidence. It is not engineering approval.
