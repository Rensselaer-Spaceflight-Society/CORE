# Shared interface register

[Coordination](README.md)

One row per shared quantity or signal. Use a source revision and two reviewing **roles**. `Candidate` is not `Accepted`. Record absolute vs. gauge and total vs. static for pressure; do not silently propagate a value that has changed. Split these starter rows when the actual quantities become clear.

| ID | Handoff | Quantity / units | Current source | Status | Reviewing roles |
|---|---|---|---|---|---|
| IF-01 | T1 → T2/C5 | Exact wheel/map, corrected flow and speed conventions | DP-2 candidate; exact supplier NOT FOUND | Open | Turbomachinery + Combustion & Systems |
| IF-02 | T2 ↔ C1 | Diffuser exit / liner inlet total states and local loss boundaries | DP-2 review; combined budget NOT FOUND | Open | Turbomachinery + Combustion & Systems |
| IF-03 | T3 → T4/T5/S1 | Turbine geometry, mass/inertia, loads and metal-temperature basis | DP-2 estimates only | Open | Turbomachinery + Structures; Safety for release |
| IF-04 | T4 ↔ S1/S2 | Shaft/wheel/inlet datums and fits, mm | Candidate 6 mm wheel bore / 8 mm journal; actual CAD NOT FOUND | Open | Turbomachinery + Structures |
| IF-05 | C3 → C4/C6 | Fuel command, delivered flow, pressure location and units | Pump/drive selection NOT FOUND | Open | Combustion & Systems; Safety for fault behavior |
| IF-06 | C4 ↔ C5 | Signal name, units, direction, timing and invalid-data behavior | First-meeting table pending | Open | Combustion & Systems; Safety for protection |

After review, link the source artifact and decision ID. Put implementation detail in the appropriate card or analysis, not in duplicated tables across teams.
