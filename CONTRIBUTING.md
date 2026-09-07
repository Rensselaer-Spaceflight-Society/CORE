# Contributing to CORE

Start with an engineering issue. Name a primary owner, a second reviewer, the inputs needed, the output to deliver, and a measurable acceptance criterion. Role names in module headers are staffing slots, not proof that a person has accepted ownership.

1. Create a branch from current `main` and reference the issue.
2. Change a coherent component/interface. Use SI units and declare every module read/write. Each calculated quantity has one producer.
3. Add regression checks for the failure being corrected. Test conservation and independent reference cases, not just copies of the implementation.
4. Run `python -m pytest`, `python run.py --report-only`, and `python scripts/generate_dependencies.py --check`.
5. Open a pull request with the behavior change, before/after results, tests, limitations and any updated diagrams.
6. Obtain a second-person engineering review. Limits, material assumptions, rotating parts and release evidence need the relevant engineering/Safety reviewer.
7. Merge the reviewed change; regenerate drawings from the same revision and record the design fingerprint.

Software CI may pass while the design violates a screening limit. Keep that violation in the readiness artifact and issue tracker. Do not relax a threshold to make a code correction pass.

`--release-check` checks evidence completeness and design identity; it does not authenticate signatures or replace technical approval. Do not mark evidence `reviewed` before the named reviewer has approved its referenced artifact.

GitHub enforcement depends on branch-protection settings. `CODEOWNERS` requests review but cannot alone guarantee independent approval. @atciamb is the repository contact until subsystem reviewers are nominated.
