# Individual research submissions

Guided lessons explicitly export `answers.json` and `summary.md` into unique folders:

`<anonymous-slot>/<lesson-id>/<session-id>-r<revision>-<random>/`

Commit only the intended exported folder. Drafts and recovery snapshots stay under ignored `out/learning/`. Do not put the private roster, credentials, confidential supplier messages, large CFD results, or executable code in a research submission.

Different students and repeat exports have different paths, reducing merge conflicts. A lead can generate the local review view with:

```sh
python workspaces/python/interactive/review.py
```

The report reads JSON only. Sources and calculated results still need technical review. These records never set engineering inputs or approve hardware.
