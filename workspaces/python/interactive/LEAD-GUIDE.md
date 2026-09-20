# Reviewing guided research

Students submit an exported directory containing `answers.json` and `summary.md`. Keep it under `workspaces/submissions/<slot>/<lesson>/<export-folder>/`. Review data without running student-supplied Python. Keep the name-to-slot roster private.

## Five-minute demonstration

```powershell
py -3.13 workspaces/python/interactive/demo.py
```

Open the printed HTML path. This creates **fictional** P00/P99 work beneath ignored `out/learning-demo/`, not public submissions. One record has an invented $10 + $3 subtotal; the other records unavailable shipping, so its subtotal remains uncomputed. Neither is real procurement evidence.

Try the real introductory interview:

```powershell
py -3.13 workspaces/python/interactive/lessons/orientation/start_here.py --slot P01
```

Use `/quit` midway through source entry, then rerun and choose the session. The draft is retained. Use `/export` to make a review bundle. The learner can send it to you or open a PR themselves. Shared lesson source is not changed by their answers.

## Generate the review view

```powershell
py -3.13 workspaces/python/interactive/review.py
```

Open `out/learning-review/index.html`. The report groups by individual session and shows:

- Findings, sources/revisions, assumptions and uncertainty.
- Questions needing a lead decision and the next small step.
- Missing/NOT FOUND evidence and calculated outputs with input provenance.
- Repeated/differing reports only when authors declared the same comparison key and units.
- Malformed exports, duplicate snapshots and separate human review annotations.

For multiple exports of one session, it shows the highest revision and preserves old files. If two exports disagree at the same revision, both appear with a notice. Multiple distinct sessions remain separate; it does not guess which one a learner intended to replace. Review notes apply only to the exact JSON snapshot digest they reference.

The HTML escapes user text and links to full local evidence. It does not import lesson or submission scripts. “Ready for review” means required fields were recorded (including explicit NOT FOUND), not that sources are correct. The report is not a student ranking or authentication system.

## Record a human review note

Use the exact exported `answers.json` path, not the placeholder below:

```powershell
py -3.13 workspaces/python/interactive/review.py --record "workspaces/submissions/P01/START1/EXPORT-FOLDER/answers.json" --role "Sub-team lead" --outcome follow_up --note "Please confirm the exact part and datasheet revision."
```

Outcomes are `follow_up`, `source_checked` and `candidate_recorded`. Notes are separate files in that export's `reviews/` directory. They are human-entered annotations, not authenticated signatures or hardware approval. A review never changes the student's answer to make it agree with a preferred value.

If you carry a finding into an interface/decision/quote record, cite its export/session and record the engineering review there. No tool promotes student answers into `config/`, `core/` or `modules/`.

## Distribute and verify

```powershell
py -3.13 workspaces/python/interactive/make_bundle.py
py -3.13 -m pytest tests/learning -q
py -3.13 workspaces/python/check_worksheets.py
```

The guided bundle is `out/worksheets/core-guided-learning.zip`. It preserves its directory layout, includes sources needed by START1, and excludes student sessions. Give each person their slot plus the lesson code/launch file. No account is needed to run it. Rebuild after lessons change and retain older bundles for unfinished sessions on old lesson revisions.

The old `workspaces/python/make_bundle.py` still packages the original edit-and-run worksheets. Their checker remains intact. Both systems can coexist; do not tell students that the old worksheets automatically save answers.

## Before the topic agents start

Send each its existing assignment prompt plus [NEXT-AGENTS.md](NEXT-AGENTS.md) and [CONTRACT.md](CONTRACT.md). Their lessons should use this runtime and separate file ownership. The final integration pass will follow after their outputs arrive; it is not complete merely because this platform is ready.
