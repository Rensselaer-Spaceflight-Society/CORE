# Python worksheets: start here

[Back to the first-meeting workspace](../README.md) · [How to run and submit one](HOW-TO-RUN.md) · [Guidance for leads](LEAD-REVIEW.md)

Each task code has one small Python file. It teaches you what your component does, explains the few words you need, shows one worked example, and gives you clearly marked places to write down what you found.

**You do not need to know Python.** You do not need to know anything about engines either. The only part of the file you change is a block near the top marked `YOUR ANSWERS`, and it is plain text with comments telling you what goes where.

Every worksheet runs before you touch it. It will not crash, and it will not invent a number for you — it tells you what is still missing and stops there.

**Nothing in these files can change the engine design.** They do not import the model in `core/` or `modules/`, they read no configuration, and they write no files. A filled worksheet is learning evidence. Turning any of it into a project value is a lead's decision, reviewed separately.

## Find your task code

| Code | Worksheet | What you will do | Task card |
|---|---|---|---|
| T1 | [`turbomachinery/t1_compressor_map.py`](turbomachinery/t1_compressor_map.py) | Find a real compressor map, and correct a flow number the way a map expects | [T1](../turbomachinery/T1-compressor.md) |
| T2 | [`turbomachinery/t2_pressure_path.py`](turbomachinery/t2_pressure_path.py) | Sketch the air path, and work out what one dynamic head costs | [T2](../turbomachinery/T2-diffuser.md) |
| T3 | [`turbomachinery/t3_velocity_triangle.py`](turbomachinery/t3_velocity_triangle.py) | Draw one velocity triangle, and find the blade speed behind it | [T3](../turbomachinery/T3-turbine.md) |
| T4 | [`turbomachinery/t4_cad_inventory.py`](turbomachinery/t4_cad_inventory.py) | List what CAD actually exists, and check it describes one engine | [T4](../turbomachinery/T4-assembly.md) |
| T5 / SAFE1 | [`turbomachinery/t5_rotor_energy.py`](turbomachinery/t5_rotor_energy.py) | Work out stored rotor energy, and why 20% faster is 44% worse | [T5](../turbomachinery/T5-rotor-energy.md) |
| S1 | [`structures/s1_bearing_screen.py`](structures/s1_bearing_screen.py) | Read one bearing page, and see what a screening number cannot tell you | [S1](../structures/S1-shaft-bearings.md) |
| S2 | [`structures/s2_inlet_flow.py`](structures/s2_inlet_flow.py) | Sketch the inlet, and find out why one documented number is mislabelled | [S2](../structures/S2-inlet.md) |
| C1 | [`combustion-systems/c1_station_sheet.py`](combustion-systems/c1_station_sheet.py) | Build the station sheet, and mark the fuel-flow discrepancy | [C1](../combustion-systems/C1-combustor.md) |
| C2 | [`combustion-systems/c2_shop_capability.py`](combustion-systems/c2_shop_capability.py) | Write the shop questions, and size a flat blank and a drilling job | [C2](../combustion-systems/C2-fabrication.md) |
| C3 | [`combustion-systems/c3_fuel_blocks.py`](combustion-systems/c3_fuel_blocks.py) | Draw the fuel blocks, and untangle 29 kg/h from 29 L/h | [C3](../combustion-systems/C3-fuel.md) |
| C4 | [`combustion-systems/c4_controller_states.py`](combustion-systems/c4_controller_states.py) | Write the controller states, and see why timers beat thermocouples | [C4](../combustion-systems/C4-controls.md) |
| C5 | [`combustion-systems/c5_model_interface.py`](combustion-systems/c5_model_interface.py) | Agree five signals, and try the shaft power balance | [C5](../combustion-systems/C5-model-interface.md) |
| C6 | [`combustion-systems/c6_instrument_rows.py`](combustion-systems/c6_instrument_rows.py) | Compare three measurements, and find where resolution is thrown away | [C6](../combustion-systems/C6-instrumentation.md) |
| C7 | [`combustion-systems/c7_start_trade.py`](combustion-systems/c7_start_trade.py) | Compare two starting methods, and price the electricity | [C7](../combustion-systems/C7-start-options.md) |

The task card is the authority on what is in and out of scope for your assignment. The worksheet teaches the topic and collects your answers. If the two ever disagree, the card wins — and tell your lead, because one of them needs fixing.

## Three things worth knowing before you start

**Writing `NOT FOUND` is a real answer.** If you look for something and it is not published, that is a result, and often a more useful one than a number. What is never acceptable is inventing a plausible-looking value to fill a gap. The worksheets are built around that rule: they will happily report that they cannot compute something yet.

**Three kinds of number, kept apart.** Every value a worksheet shows you carries a tag:

| Tag | Means |
|---|---|
| `EXAMPLE` | Invented to demonstrate the arithmetic. Never copy it into a CORE document. |
| `CANDIDATE` | A DP-2 proposal under review. Not approved, not an operating value. |
| `REPO CHECK` | Reproduced by [`docs/project/checks/dp2_screen.py`](../../docs/project/checks/dp2_screen.py), this repository's own screening script. |

DP-2 is a candidate design point, not a validated engine. The [review](../../docs/project/dp2-review.md) reproduces roughly 98 N in a prescribed cycle calculation; it does not show the engine can sustain itself. Read the review rather than treating its numbers as instructions.

**Nothing today touches hardware.** No first-meeting worksheet asks you to handle fuel, enter a shop, run a machine, attach anything to a rotor, demonstrate an ignition, or operate anything that spins. Those are later tasks with their own reviews and their own prerequisites, arranged by your lead.

## Run one

```bash
python workspaces/python/turbomachinery/t1_compressor_map.py
```

Three options are built in:

| Command | What it does |
|---|---|
| `python <worksheet>` | The lesson, your progress, and a block to paste into your card |
| `python <worksheet> --form` | A blank form you can print and fill in by hand |
| `python <worksheet> --help` | A reminder of the above |

No Python on your machine today? [HOW-TO-RUN.md](HOW-TO-RUN.md) has a route that needs none.

## For leads

```bash
python workspaces/python/check_worksheets.py     # verify all 14 still behave
python workspaces/python/make_bundle.py          # build a handout zip in out/worksheets/
```

[LEAD-REVIEW.md](LEAD-REVIEW.md) covers what to check before a finding enters a shared design record.
