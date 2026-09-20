# Lesson-author contract — API and record schema v1

This is the shared interface for the next seven topic assignments. Build on this contract; do not create another logger. The runtime is Python 3.11–3.13 and standard-library only. Teaching modules are trusted repository code; student results are JSON data that the review tool never executes.

## File ownership and first integration

- Platform owner: files directly in this directory, shared navigation/setup, bundle generation, CI and `tests/learning/test_platform.py`.
- Controls: `lessons/controls/`; instrumentation: `lessons/instrumentation/`; electrical: `lessons/electrical/`; structures/fabrication: `lessons/structures/`; turbomachinery: `lessons/turbomachinery/`; CFD: `lessons/cfd/`.
- Each topic owns `tests/learning/<domain>/` for its checks. Keep shared helpers out of other agents' paths. Request platform changes in a short integration note.
- The engine explorer owns `docs/learning/engine-explorer/`. See [external visual integration](#external-visual-integration).
- One module per runnable lesson. Discovery reads `lessons/*/*.py`, so no central menu edit is necessary. Helper modules must start with `_`; assets can go in a subfolder. Do not duplicate lesson IDs.
- Do not import `core/`, `modules/` or `run.py`, mutate configuration, operate hardware, or make network calls at lesson import time. Lesson arithmetic stays clearly separate from the production solver.
- Use codes and anonymous slots publicly. No AI author identities, contributor entries or co-authorship trailers. Keep existing human Git attribution.

## Small complete example

Save as `lessons/<domain>/<task>.py`:

```python
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from runtime import Lesson, Step, Question, Calculation, run_lesson

def build_lesson():
    return Lesson(
        id="EXAMPLE1", version="1.0", title="Find one useful fact",
        review_role="Relevant sub-team lead",
        prerequisites=("Choose an exact component with your lead.",),
        sources=("Manufacturer document URL or repository reference",),
        steps=(Step(
            id="evidence", title="One small investigation",
            teaching="Explain the idea simply, then show what to look for.",
            questions=(Question(
                id="finding", prompt="What did you find?",
                hint="Record conditions and units in your answer.",
            ),),
        ),),
    )

if __name__ == "__main__":
    raise SystemExit(run_lesson(build_lesson(), __file__))
```

The runtime handles prompts, metadata, validation, drafts, saving, resume, progress and export. `build_lesson()` must be deterministic and must not start an interview or write files. The working [START1 lesson](lessons/orientation/start_here.py) demonstrates multiple steps, optional numbers, a calculation and a local diagram.

## The public objects

`Lesson(id, version, title, review_role, steps, prerequisites=(), minutes="30-45", sources=(), calculations=())`

`Step(id, title, teaching, questions, visual="")`

`Question(id, prompt, kind="text", units="", choices=(), minimum=None, maximum=None, required=True, evidence=True, hint="", role="finding", comparison_key="")`

`Calculation(id, title, inputs, function, units="", method="", version="1", limitations="")`

IDs contain letters, numbers, `_` or `-`, with a maximum of 64 characters. Question IDs are unique across the entire lesson. Step IDs and calculation IDs are also unique within their respective lists.

Question types:

| Kind | Behavior |
|---|---|
| `text` | Nonblank text; `/text` allows several lines |
| `number` | Finite numeric value, no unit suffix or thousands separator |
| `integer` | Whole finite number |
| `choice` | Exact member of `choices`, shown to the learner |
| `boolean` | yes/no, true/false, y/n |

Numeric units are set by the author, not inferred from student text. Bounds are input-validity checks, not hardware limits or design approval. `required=False` allows a learner to leave optional work unknown without blocking readiness.

With `evidence=True`, the interview asks for basis, source, source revision/page, assumptions and uncertainty/limits. Source and uncertainty are required for an answered finding. Use `evidence=False` for reflection, questions to the lead and next steps—not to bypass evidence for an engineering number.

Set `role="decision"` or `role="next_step"` to surface these answers at the top of lead review. These roles do not assign engineering ownership. For ordinary findings, leave `role="finding"`.

Only use `comparison_key` if records refer to the same physical quantity, exact part, location and conditions. For example `part123.revB.max_supply_voltage`. The reviewer groups equal keys and units, flags different reports and identifies repeated values. It performs no unit conversion or semantic inference. Two copied values do not establish independent agreement. Leave this blank for generic prices or unrelated student-selected components.

## Calculations

`inputs` is a tuple of numeric question IDs. The trusted callable receives their values as **keyword arguments**, so parameter names must match IDs. It returns one finite number. Add separate `Calculation` objects for multiple outputs. Callables must be pure and handle their physical domain; no files, hardware or network operations.

```python
Calculation(
    id="area", title="Circular area", inputs=("diameter",),
    function=lambda diameter: 3.141592653589793 * diameter**2 / 4,
    units="mm^2", method="A = pi*d^2/4; diameter in mm", version="1",
    limitations="Geometry example; no material or strength conclusion.",
)
```

Missing/UNKNOWN/NOT FOUND inputs yield `missing_inputs`, not zero. Invalid calculations yield `invalid_inputs`, not a clipped valid-looking result. Results retain input answer snapshots, method and version, units and limitations. They are always tagged `computed`, never `measured` or `approved`.

## Saving and versioning

Each learner uses an assigned slot such as `P01`; allowed syntax is `P` followed by 2–4 digits. Keep the name-to-slot roster elsewhere. P00 is used in the fictional demonstration.

Local files: `out/learning/<slot>/<lesson-id>/<random-session-id>/answers.json`, with numbered immutable snapshots in `history/`. Writes are atomic and protected against two windows overwriting the same session. Separate sessions never share a data file. Draft metadata fields are saved before the complete answer is accepted.

Students run the same command to choose a previous session, or provide `--slot P01 --resume SESSION_ID`. Recovery uses `--recover SESSION_ID` and copies the newest valid history into a new session. It preserves the damaged original. If a write fails, the program reports the failure; do not tell students their last entry is saved merely because they typed it.

The record stores lesson version, question definitions, teaching-content fingerprint and repository commit. Bump `version` whenever meaning, questions, units or calculations change. Changes to a calculation's implementation require a calculation/lesson version bump even if its text is unchanged. An incompatible session is not silently migrated: use the old bundle or start a new session. Keep existing student records.

Explicit `/export` or `--export` creates `workspaces/submissions/<slot>/<lesson-id>/<session-id>-r<revision>-<random>/`. It contains `answers.json` and `summary.md`. Each export gets its own folder. Unfinished drafts are excluded. There is no auto-upload, commit or shared CSV to merge.

## JSON schema 1

Top-level fields:

| Field | Meaning |
|---|---|
| `schema_version` | Integer 1 |
| `session_id`, `participant_slot` | Random UUID hex and anonymous slot |
| `lesson` | ID, version, title, reviewer role, sources, question definitions and fingerprint |
| `repository_commit` | Local source commit, bundle source revision, or `unknown` |
| `created_at`, `updated_at` | Timezone-qualified UTC ISO timestamps |
| `revision` | Positive monotonically increasing save revision |
| `current_step` | Zero-based **question** position; length means interview end |
| `answers` | Question-ID map of accepted answer records |
| `drafts` | Partial entries; omitted in exports by replacing with `{}` |
| `computed` | Calculated records with input evidence snapshots |
| `status` | `in_progress` or `ready_for_review`, derived from required answers |
| `review_status` | Always `unreviewed` in student records |
| `recovered_from` | Optional original session ID and snapshot revision |

An accepted answer includes `question_id`, `prompt`, `response_type`, `role`, `comparison_key`, `value`, `units`, `status`, `basis`, `source`, `source_revision`, `assumptions`, `uncertainty`, `reason` and `edited_at`.

- Answer `status`: `answered`, `unknown`, `not_found`. The latter two have JSON `null` value.
- Basis: `example`, `candidate`, `sourced`, `measured`, `hypothesis`, `student`.
- `not_found` needs a nonempty search trail in `reason`. It counts as recorded work for review, not proof of suitability.
- An answered evidence question needs source and uncertainty. `unknown` keeps a required question incomplete.
- This is a learning-data schema, not an authentication system. Students' claims and computed outputs still need review. The loader rejects structural problems, NaN, duplicate JSON keys, unsupported schema and student-declared approval.

`--answers FILE` is an explicit noninteractive batch mode for tests, imports or demonstrations. Its JSON is a map of question IDs to entries containing `value`/`status` and evidence fields; see [fictional-answers.json](examples/fictional-answers.json). The entire batch is validated before a session is created. It cannot set metadata or review approval. This is not automatic import of another application's arbitrary export.

## Visuals and external visual integration

`Step.visual` is a relative path to `.html`, `.svg` or `.png` inside that lesson's own directory. The learner chooses `/visual`. A missing browser or asset does not prevent the interview. Keep a useful text explanation too. Do not require a CDN, network access, account or live server for a basic visual.

For the full engine explorer, keep its application under `docs/learning/engine-explorer/`. Its team can export an observation JSON with an explicit schema/version and settings/model assumptions. Supply an integration note mapping those fields to lesson questions. The platform owner will add a reviewed adapter; do not forge a schema-1 session or import executable JavaScript/Python as a submission. Until the adapter exists, record the exported artifact's relative path and a short finding in a normal lesson. Do not duplicate the explorer into each lesson.

## Tests and handoff

1. Run your file directly with `--help` and `--preview` without any answers. These must not write files or require a GUI.
2. Test actual calculations against independent examples, units and domain limits. Test UNKNOWN/NOT FOUND without fabricated defaults.
3. Exercise a short interactive session and one interrupted/resumed answer. Validate visual content and navigation.
4. Run `python -m pytest tests/learning -q`. The existing engineering checks remain separate; follow CONTRIBUTING for the complete PR checks.
5. Provide changed paths, source evidence, actual results, limitations, launch command and a small integration note. Do not claim a simulator or external solver was run unless it was.

Do not edit the platform's schema/runtime to accommodate one lesson without coordinating. A learner's completed worksheet is never the engineering release gate.
