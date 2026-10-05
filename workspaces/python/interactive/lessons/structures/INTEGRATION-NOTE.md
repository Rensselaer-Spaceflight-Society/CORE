# Integration note — structures & fabrication lessons

For the platform owner. Three lessons, one helper, three visuals, one test module.
Nothing outside `lessons/structures/`, `tests/learning/structures/` and the structures
workspace documentation was changed.

## What landed

| Lesson | ID | Entry point |
|---|---|---|
| Pressure wall: FBD, input ledger, thin-wall hoop/axial, applicability | `S3-STRESS` | `lessons/structures/pressure_wall.py` |
| Bending, torsion, and the three quantities called I | `S4-BEND` | `lessons/structures/beam_and_shaft.py` |
| Fabrication feasibility and weld development | `C2-FAB` | `lessons/structures/fabrication_coupon.py` |

Helper: `_structures_math.py` (leading underscore, so `discover()` skips it).
Visuals: `pressure_wall.html`, `shaft_sections.html`, `coupon_plan.html` — self-contained,
no CDN, no network, no script tags; a test asserts that.

Launch:

```
python workspaces/python/interactive/launch.py --list
python workspaces/python/interactive/launch.py --lesson S3-STRESS --slot P01
# or run a lesson file directly; --preview is read-only
python workspaces/python/interactive/lessons/structures/pressure_wall.py --preview
```

## Contract conformance

- `build_lesson()` is deterministic, starts no interview and writes no files.
- No import of `core/`, `modules/` or `run.py`; no configuration is read or mutated;
  no network or hardware access at import time or at any other time.
- All calculation inputs are numeric question IDs; every `Calculation` carries a
  `method`, a `version` and non-empty `limitations`.
- Question IDs are unique per lesson; no lesson ID collides with an existing one.
- Shared runtime files, the schema, the launcher, setup, CI and other agents' paths
  are untouched.
- Tests live in `tests/learning/structures/test_structures_lessons.py`. The basename is
  unique across `tests/`, so the absence of `__init__.py` (matching the existing
  `tests/learning/`) does not collide.

## Comparison-key convention (proposed repo-wide)

Three questions carry a `comparison_key`, all on the same physical part under the same
conditions — the CORE candidate outer casing:

```
core.casing.candidate.internal_pressure_abs_kPa
core.casing.candidate.inner_diameter_mm
core.casing.candidate.wall_thickness_mm
```

Pattern: `core.<part>.<status>.<quantity>_<unit>`. Suggest the other topic agents follow
it so `review.py` groups sanely across domains. Verified against two exported records:
the reviewer correctly reported *"Different reports: check sources/conditions"* for
1.5 mm vs 2.0 mm, and *"Repeated value: not independent verification"* where both
learners had copied the same file. No key is placed on a student-selected component or
on a generic price, per the contract.

## One request for a future contract revision (not blocking)

`Calculation.inputs` must be numeric question IDs, so a calculation cannot read a
`choice` answer. In `S3-STRESS` the axial-stress result is only physically meaningful
when the learner recorded *"closed ends carried by this wall"* in step 1. Today that
precondition lives in the calculation's `limitations` text and in the teaching copy,
which is honest but relies on the learner reading it.

If a v2 schema is opened, a declarative guard — something like
`Calculation(..., applies_when=("end_condition", "closed ends carried by this wall"))`,
producing a `not_applicable` status alongside `missing_inputs` and `invalid_inputs` —
would let the record state plainly that a number does not apply to the learner's part.
Please do not add it for this lesson alone; it is only worth doing if other domains hit
the same shape. The lessons are complete and correct without it.

## Notes for the integration pass

- `make_bundle.py` picks the three lesson modules, the helper and the three visuals up
  automatically (`.py` and `.html` are already in its suffix list), and this note with
  them. Verified: 8 entries in the built ZIP come from this domain.
- No new dependency. Standard library only, Python 3.11–3.13.
- The lessons change no engineering input, so `python run.py --report-only` is
  unaffected by them.
- Resolved: the CRLF→LF noise a fresh clone showed came from `legacy/v5/`, which was
  removed from `main` on 2026-10-05.
- The worked numbers are DP-2 and seed-baseline values, labelled as such. The PD-1
  candidate merged into `main` on 2026-10-05 supersedes DP-2 for design work; see
  [`workspaces/structures/README.md`](../../../../structures/README.md).

## Handoff beyond the platform

These lessons produce learner evidence and nothing else. The decisions they surface
belong to the structures lead (casing and shaft design, clearances), the shop and
welding authority (process capability, training, any weld procedure), Safety (anything
that runs, spins or holds pressure) and the Chief engineer (money and supplier
contact). Task-code lineage and the promise that S1/S2 are unchanged are recorded in
[`workspaces/structures/TASK-CODE-MAP.md`](../../../../structures/TASK-CODE-MAP.md).
