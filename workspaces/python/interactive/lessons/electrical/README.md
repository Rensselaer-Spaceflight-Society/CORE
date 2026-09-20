# C8-ELEC · electrical system lesson

Run the guided activity from the repository root:

```powershell
py -3.13 workspaces/python/interactive/launch.py --lesson C8-ELEC --slot P01
```

The first useful result is a power tree and I/O table. It then asks the learner
to reason through battery sag, invalid sensors, controller reset, stuck outputs
and manual stop, followed by a drawing-only bring-up checklist.

`electrical_overview.svg` is both the viewable diagram and editable source. It
separates power, measurement, command and safety-inhibit paths and intentionally
leaves ratings, connectors and protection choices unresolved. The lesson's
arithmetic only checks `P = V × I` and `E = P × t`; it does not approve a battery,
fuse, driver, connector, wire or energized test.
