# Foundation ready: instructions for the seven topic agents

Use this note alongside your numbered handoff prompt. The runtime and data contract are now implemented; do not rebuild them.

Until the foundation PR is merged, base your isolated branch on `origin/feat/guided-learning-platform`, not the older `main`. After merge, start from current `main`. Check the actual Git state first and preserve any local work.

Read [CONTRACT.md](CONTRACT.md), then inspect [start_here.py](lessons/orientation/start_here.py). Implement a deterministic `build_lesson()` and call `run_lesson(build_lesson(), __file__)` from the entry point. Adding a module under your domain automatically adds it to the launcher; no central menu or registry change is needed.

| Assignment | Owned directory below `lessons/` | Expected interface collaboration |
|---|---|---|
| Controls + plant | `controls/` | Publish semantic signal dictionary early for instrumentation/electrical |
| Instrumentation | `instrumentation/` | Match controls' signals; document electrical output and measurement behavior |
| Electrical | `electrical/` | Own wiring/power compatibility, not sensor physics or control logic |
| Structures + fabrication | `structures/` | Preserve existing student experiments; coordinate mounting and fabrication |
| Turbomachinery | `turbomachinery/` | Source maps/geometry and send boundary requirements to CFD/combustion |
| CFD | `cfd/` | Reproducible benchmark and bounded cold-flow evidence |
| Engine explorer | `docs/learning/engine-explorer/` from repository root | Supply a documented observation export and adapter proposal |

Put your tests under `tests/learning/<domain>/`. Helpers in a lesson domain start with `_` so the launcher does not discover them as lessons. Keep new optional dependencies specific to your domain and provide a read-only fallback; the basic launcher must remain standard-library only.

Do not alter shared runtime files, submission schemas, root navigation, setup, CI or another team's files. Propose needed shared changes in your handoff. Preserve existing lesson IDs or explicitly map changed assignments. Use task codes/slots, not names. Do not add AI attribution or co-authorship.

Run your entry point, its preview, your own meaningful tests and `python -m pytest tests/learning -q`. Report actual visual/solver checks and limitations. Push your branch and open a PR; do not merge it. Return your PR/commit, launch command and integration note to the platform owner for the final integration pass.
