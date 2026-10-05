# Structures

[Back to start](../README.md)

**Lead role:** Structures lead. Begin with a five-minute explanation of this team's function, then one worked example. Give each person their code from the private roster. Review findings before assigning follow-on work.

| Card | First-meeting output | Guided Python worksheet |
|---|---|---|
| [S1](S1-shaft-bearings.md) | Read one bearing datasheet | [s1_bearing_screen.py](../python/structures/s1_bearing_screen.py) |
| [S2](S2-inlet.md) | Explain an inlet drawing and pressure terms | [s2_inlet_flow.py](../python/structures/s2_inlet_flow.py) |

## Follow-on guided lessons

Longer interactive lessons that save your answers, sources and assumptions as you go
and let you stop and resume. S1 and S2 above are unchanged; these are additions. The
[task code map](TASK-CODE-MAP.md) records exactly what each code means and confirms
that nobody has been reassigned.

| Code | What you produce | Lesson |
|---|---|---|
| S3-STRESS | A labelled free-body diagram, an input/load ledger tied to the real casing interface, and a unit-checked thin-wall stress with its applicability stated | [pressure_wall.py](../python/interactive/lessons/structures/pressure_wall.py) |
| S4-BEND | Bending and torsion screening on a stated support condition, and the difference between area second moment, polar area second moment and mass moment of inertia | [beam_and_shaft.py](../python/interactive/lessons/structures/beam_and_shaft.py) |
| C2-FAB | A fabrication feasibility and weld-development package: demonstrator, coupon matrix, inspection plan, tolerance stack and the decisions the team owes an answer to | [fabrication_coupon.py](../python/interactive/lessons/structures/fabrication_coupon.py) |

```
python workspaces/python/interactive/launch.py --list
python workspaces/python/interactive/lessons/structures/pressure_wall.py --preview
```

`--preview` prints the whole lesson as a read-only form and writes nothing, so you can
read it without Python set up for saving. See
[SETUP.md](../python/interactive/SETUP.md) for slots, saving and submission.

Existing student code in [`object tests/`](object%20tests/) is preserved as written;
[its README](object%20tests/README.md) explains what it teaches, the one unfinished
expression in it, and why its 2 MPa example loads must stay separate from DP-2.

Two primary members cannot simultaneously own complete shaft, bearing, casing, inlet, nozzle and stand design. T4 helps with assembly inventory; T5 helps with energy questions. The lead retains the unassigned casing/nozzle/stand work and prioritizes it after the meeting.

Each card includes its own Findings section. Keep notes there until they need a separate analysis artifact; add a linked subfolder only when there is actual work to store. Do not create a folder per person or duplicate CAD files. For a shared value use the [interface register](../coordination/interfaces.md).
