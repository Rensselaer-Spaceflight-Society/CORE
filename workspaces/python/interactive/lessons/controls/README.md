# C4 controls and plant lesson

Run the guided activity from the repository root:

```powershell
py -3.13 workspaces/python/interactive/launch.py --lesson C4 --slot P01
```

It walks a newcomer through the signal contract, five-state safety concept and
a synthetic first-order plant calculation before they open Simulink. The local
`control_loop.svg` is an optional diagram opened with `/visual`.

`_control_model.py` contains the deliberately small equations used by the
lesson. They are useful for checking a Simulink block against known values;
they are not an engine model and do not select limits, tune hardware or drive
an actuator. Keep all operating, trip and timer thresholds as `TBD` until the
component and Safety leads provide reviewed evidence.
