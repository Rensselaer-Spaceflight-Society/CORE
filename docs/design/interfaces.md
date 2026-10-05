# PD-1 interfaces, stations, datums and ownership

Machine-readable sources (no duplicated numbers here):

| Content | File |
|---|---|
| Station numbering, total/static and hot/cold conventions, loss boundaries, flow/power ledger | [`data/interfaces/station_convention.yaml`](../../data/interfaces/station_convention.yaml) |
| Mating faces, fits/clearances, x positions and diameters (23 interfaces) | `results/pd1-jm85/cad/cad_bundle.json → interfaces` |
| Typed part parameters (185), patterns (combustor rows, vaporizers, diffuser vanes, fasteners, sensor ports), sections (nozzle contour, shaft profile, stations) | `results/pd1-jm85/cad/cad_bundle.json` |
| Signals: units, ranges, latency, invalid-data behaviour | [`data/systems/signals.yaml`](../../data/systems/signals.yaml) |
| Shared scalar quantities (the repository ICD) | [`config/variables.yaml`](../../config/variables.yaml) (151 entries added on this branch) |
| Design-point station table | `results/pd1-jm85/station_table.csv` |

## Frame and datums

- x along the engine axis, **positive aft**; origin = compressor wheel backface plane, cold, as assembled.
- r radial; angular zero at top dead centre; positive **clockwise viewed from the front** (looking aft).
- All CAD dimensions are **cold at 293 K**. Hot values are derived from stated metal temperatures (clearances.json).
- Rotation direction is an open interface (IF-ROT): confirm from the purchased compressor and turbine wheels
  before cutting diffuser vanes, NGV-related features or nut thread hands.

## Station and loss boundaries (summary)

0 ambient → **2** compressor face (inlet loss) → **3** stage exit = vaned-diffuser exit (map covers wheel +
diffuser) → **31** combustor inlet (turn/deswirl loss) → **4** liner discharge (combustor loss; T04 = TIT basis)
→ **41** NGV inlet after tunnel-leak re-entry (adiabatic mixing) → **45** rotor inlet (static, mean line) →
**5** turbine exit → **7** nozzle inlet (jet pipe + dissipated swirl) → **8** nozzle exit.
Each loss is counted once; internal liner air splits are not losses; mechanical losses are explicit (no
mechanical efficiency is applied on top).

## Interface table (from the bundle)

| ID | Parts | Feature | Relation / fit |
|---|---|---|---|
| IF-ROT | CW-01 ↔ TR-01 | rotation / blade handedness | must agree (inspect) |
| IF-CW-SH | CW-01 ↔ SH-01 | wheel bore on 6 mm seat | slip/transition proposed, clamped by M6 nut; **finished seat diameter unresolved** until the bore is measured (`SH01_COMPRESSOR_FINISHED_SEAT_DIA`) |
| IF-CW-DF | CW-01 ↔ DF-01 | backface running clearance | 0.40 mm axial (shim) |
| IF-SL-BR1 | SL-01 ↔ BR-01 | sleeve face on inner ring | clamp |
| IF-SH-BR1 | SH-01 ↔ BR-01 | front journal | k5 |
| IF-BR1-BC1 | BR-01 ↔ BC-01 | front bearing in steel sleeve | J6 + retaining ring |
| IF-BC1-DF | BC-01 ↔ DF-01 | sleeve in backplate pocket on two O-rings | soft damped mount, anti-rotation pin |
| IF-DF-CS | DF-01 ↔ CS-01 | backplate rim spigot | g6/H7, 12 × M4 |
| IF-TU-DF | TU-01 ↔ DF-01 | tunnel front on backplate spigot | press/retained |
| IF-TU-BC2 | TU-01 ↔ BC-02 | tunnel rear slip joint | sliding (no fight with casing) |
| IF-BC2-NG | BC-02 ↔ NG-01 | rear carrier in the NGV hub pocket | **UNRESOLVED**: the Ø48 pocket in the blank is blind (centre web + boss); finished passage, carrier location and fit are a team decision (manufacturing-and-budget.md §2) |
| IF-BR2-BC2 | BR-02 ↔ BC-02 | floating outer ring + wave spring | G6 sliding, ~40 N |
| IF-SH-TR | SH-01 ↔ TR-01 | turbine bore on 10 mm seat | **fit unresolved**: the nominal 9.99 ±0.005 mm bore on a 10.000 mm seat is a 5–15 µm interference; M8 clamp proposal; assembly method, hub stress and approved fit need review |
| IF-TR-NG-TIP | TR-01 ↔ NG-01 | tip clearance to finished shroud | 0.35 mm radial cold |
| IF-TR-NG-AX | TR-01 ↔ NG-01 | NGV TE to rotor LE | 2.0 mm cold |
| IF-CB-NG | CB-04/05 ↔ NG-01 | discharge cones onto NGV rings | sliding; liners located at rear |
| IF-CB-CS | CB-01 ↔ CS-01 | dome on 3 radial pins in casing slots | radial + axial sliding |
| IF-NG-CS2 | NG-01 ↔ CS-02 | NGV flange to casing rear cover | 12 × M3 hot fasteners on PCD 98 + gasket; cover ID clears the Ø92 outer ring |
| IF-EX-NG | EX-01 ↔ NG-01 | nozzle flange to NGV casting rear face | shared bolts; nozzle starts at the casting rear face |
| IF-FUEL | FU-01 ↔ CS-01 | manifold through casing, needles into sticks | liquid budget separate from air budget |
| IF-IGN | IG-01 ↔ CS-01/CB-02 | igniter boss | M10 |
| IF-STARTER | ST-01 ↔ CW-01 | cone on compressor nut | one-way clutch, disengaging |
| IF-MOUNT | CS-01 ↔ stand | two clamp bands | band clamps |

## Ownership (roles)

| Interface group | Primary | Reviewer |
|---|---|---|
| Compressor wheel/housing/diffuser (IF-CW-*, IF-DF-*) | Turbomachinery | Structures |
| Turbine/NGV (IF-TR-*, IF-BC2-NG, IF-NG-CS2) | Turbomachinery | Structures + Safety |
| Shaft/bearings/supports (IF-SH-*, IF-BR*, IF-BC*) | Structures | Turbomachinery |
| Combustor/casing/fuel/igniter (IF-CB-*, IF-FUEL, IF-IGN) | Combustion & Systems | Structures |
| Starter, signals, electrical | Combustion & Systems | Safety |

Roles only; no approvals are recorded here.
