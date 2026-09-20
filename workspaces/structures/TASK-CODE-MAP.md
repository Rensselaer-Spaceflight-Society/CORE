# Structures task codes: what each one means, and what is new

[Structures team page](README.md) · [Coordination](../coordination/README.md) ·
[Guided lesson contract](../python/interactive/CONTRACT.md)

This map exists so that adding guided lessons does not quietly change what an existing
task code means or move anybody off the work they already took. **S1 and S2 keep their
original meanings, their original cards and their original worksheets.** Nothing below
reassigns a person, and the private name-to-slot roster stays out of this repository.

## Existing codes — unchanged

| Code | Meaning | Card | Original worksheet | Status |
|---|---|---|---|---|
| S1 | Read one bearing datasheet; DN screen; identify what DN cannot approve | [S1-shaft-bearings.md](S1-shaft-bearings.md) | [s1_bearing_screen.py](../python/structures/s1_bearing_screen.py) | Unchanged |
| S2 | Explain an inlet drawing and pressure terms; labelled sketch and missing-input list | [S2-inlet.md](S2-inlet.md) | [s2_inlet_flow.py](../python/structures/s2_inlet_flow.py) | Unchanged |

Both edit-and-run worksheets still work exactly as before and are still checked by
`python workspaces/python/check_worksheets.py`. Anyone part-way through one should
finish it; the guided lessons are additions, not replacements, and no S1 or S2 answer
already written into a card's Findings section is touched by this change.

## New extensions

| Code | Meaning | Guided lesson | Owner role | Relationship to existing codes |
|---|---|---|---|---|
| S3-STRESS | One pressure wall: free-body diagram, input/load ledger, thin-wall hoop and axial stress, applicability and what the screen excludes | [pressure_wall.py](../python/interactive/lessons/structures/pressure_wall.py) | Structures lead reviews; Safety for anything pressurised | New. Uses the pressure vocabulary S2 introduces (absolute vs gauge, total vs static) and applies it to the casing wall instead of the inlet. |
| S4-BEND | Bending `σ = M·y/I`, shaft torsion `τ = T·r/J`, and the difference between area second moment, polar area second moment and mass moment of inertia. Optional deflection exercise | [beam_and_shaft.py](../python/interactive/lessons/structures/beam_and_shaft.py) | Structures lead reviews; Safety for rotating hardware | New. Feeds back into **S1**: it shows that the DP-2 candidate 8 mm journal is set by the bearing bore and not by torsion, which is the same shaft S1 is reading a datasheet for, and it flags that config/seed.yaml still carries the earlier baseline's 15 mm bore. |
| C2-FAB | Fabrication feasibility and weld-development package for a candidate nonrotating sheet-metal demonstrator: stock, forming limits, joint access, process and filler evidence, fixturing, distortion, inspection, tolerance stack, shop questions, cash vs in-kind | [fabrication_coupon.py](../python/interactive/lessons/structures/fabrication_coupon.py) | Structures lead **and** the shop/welding authority; Chief engineer for spending; Safety before anything runs | Extension of **C2** (shop capability) into structures. C2's original card and worksheet are unchanged; C2-FAB is the deeper package for a member with actual welding experience. |

### Why C2-FAB sits in the structures track

The original [C2 card](../combustion-systems/C2-fabrication.md) asks for a capability
checklist and a paper sequence, and it stays exactly that. C2-FAB goes further — a
demonstrator, a coupon matrix, an inspection plan and a tolerance stack — because the
parts it is about (casing, liner, brackets) are structures parts, and because the
clearance it protects, `casing_fit_margin_min_m` in
[`config/limits.yaml`](../../config/limits.yaml), is a structures constraint. It is
filed under `lessons/structures/` for that reason and coordinated with Combustion &
Systems through the [interface register](../coordination/interfaces.md).

The lesson ID keeps the `C2-` prefix so the lineage is obvious and nobody reads it as a
brand-new unrelated assignment.

## What the new lessons deliberately do not do

- They do not renumber, retire or supersede S1 or S2.
- They do not assign anyone to a task. Codes and anonymous slots only; the roster is
  private and stays that way.
- They do not overwrite any prior answer. Each learner's session is saved separately
  under `out/learning/<slot>/<lesson-id>/<session-id>/`, so two people working through
  the same lesson never share a file, and an existing card Findings block is untouched.
- They do not change the engine model, any configuration value or any limit. The
  lessons import nothing from `core/`, `modules/` or `run.py`; their arithmetic is
  separate teaching code in
  [`_structures_math.py`](../python/interactive/lessons/structures/_structures_math.py).
- They do not approve anything. Completion is learning evidence. Engineering release
  runs through `config/readiness.yaml`, the named reviewers and Safety, exactly as
  before.

## Existing student code

[`object tests/object-example.py`](object%20tests/object-example.py) is preserved
byte-for-byte. Its one unfinished expression, the fix, and why its 2 MPa / 200 mm loads
must stay clearly separate from DP-2 are written up in
[`object tests/README.md`](object%20tests/README.md).
