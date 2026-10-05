# Guided research: run, learn, save

Run one Python file. It explains a small idea, asks what you found and saves your answers automatically. You can stop and resume. Nothing uploads itself or changes the engine model.

```powershell
py -3.13 workspaces/python/interactive/launch.py
```

On macOS/Linux use `python3` instead of `py -3.13`. Python 3.11–3.13 works; no extra packages are needed. Keep the whole folder together.

**START1 is the working introductory lesson.** C4 prepares the controls team to agree signals and a safe state concept before opening Simulink. C8-ELEC prepares the electrical team to document power, measurement, command and inhibit paths. The remaining topic packages are being built separately. The [14 existing edit-and-run worksheets](../README.md#find-your-task-code) remain available.

| Task | Direct launch file | What you produce |
|---|---|---|
| START1 | `lessons/orientation/start_here.py` (inside this folder) | One sourced finding, a question for the lead and a next step; optional cost arithmetic |
| C4 | `lessons/controls/c4_control_system.py` (inside this folder) | Signal contract, five-state safety concept and a reproducible synthetic plant response |
| C8-ELEC | `lessons/electrical/c8_electrical_system.py` (inside this folder) | Power tree, I/O table, failure walkthrough and non-energized bring-up checklist |

Use your lead's assigned slot, such as P01; keep names out of public records. GitHub commits still show the contributor's normal account identity.

The controls you need:

- `/help`: all controls; `/progress`: what is recorded and missing.
- `/skip`: UNKNOWN; `/not-found`: save where you looked and what was missing.
- `/back`, `/edit finding`: revisit an answer; `/text`: several lines of text.
- `/visual`: open an optional local diagram.
- `/quit`: leave; accepted answers and draft fields are already saved.
- `/export`: create a folder you can review and share; it does not commit or upload.

Run the launcher again with the same slot to choose a saved session. Saved drafts are under `out/learning/`. Exports are under `workspaces/submissions/`, one folder per session snapshot. You do not need to edit lesson code to contribute.

[Setup and contribution commands](SETUP.md) · [Lead review and demonstration](LEAD-GUIDE.md) · [Lesson author contract](CONTRACT.md) · [Next-agent handoff](NEXT-AGENTS.md)

No Python today? Someone can run `launch.py --lesson START1 --preview` to print the lesson and a form. A paper/shared-document finding is welcome; your lead can transfer it into a reviewed record.

The program checks that evidence is recorded, not that it is correct. “Ready for review” is not approval to purchase, manufacture or operate hardware.
