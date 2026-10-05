# C8-ELEC · Electrical system

[Back to workspaces](../README.md) · [Guided lesson](../python/interactive/lessons/electrical/README.md)

**Time:** 30–45 minutes. **Review role:** Electrical/system integration lead; Safety, Controls and Instrumentation review the interfaces.

Run:

```powershell
py -3.13 workspaces/python/interactive/launch.py --lesson C8-ELEC --slot P01
```

The lesson teaches a beginner to trace a complete battery-to-load-to-return
path, separate power/measurement/command wiring, record candidate loads and
interfaces, walk through failures, and prepare a non-energized drawing review.
It does not select ratings or authorize powered hardware tests.

The repository's [editable SVG schematic](../python/interactive/lessons/electrical/electrical_overview.svg)
is intentionally staged. Every connection still needs a source, destination,
return, protection question and evidence before implementation.
