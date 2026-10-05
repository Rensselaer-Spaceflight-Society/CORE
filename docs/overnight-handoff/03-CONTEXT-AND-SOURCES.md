# Context, conflicts and research starting points

This is a source guide, not a substitute for reading the implementation or current vendor documentation. Repository facts were inspected October 4, 2026 at local commit `98c4167`. Public pages below were opened October 4, 2026; listings are not stock confirmation, quotes or supplier approval for CORE.

## Current user intent and precedence

The user wants substantial autonomous overnight progress through component designs, their connections, manufacturability, cost and self-sustain assessment. The team will own final native CAD and detailed engineering analysis. Latest explicit budget instruction: **“Aim for $5500 and extend to $6000 as the max ceiling.”**

Use direct current user instructions first, then the current source/data and clearly identified project decisions. Preserve conflicting historical material as history. The newer budget records a purchased turbine wheel plus finishing and guide-vane casting route; use that as the working procurement direction, with exact items still unselected. Budget stock sizes are not engineering approvals.

## Important local inputs

| Source | What it establishes |
|---|---|
| `docs/preliminary-design-roadmap.md` | Code survey, module gaps and integration order |
| `docs/model-review.md` | Corrected numerical conventions and unresolved physical evidence |
| `docs/project/dp2-review.md` | Candidate values, conflicting assumptions and limits of the cycle screen |
| `docs/combustor-dp2.md` | Latest standalone combustor changes and option meanings |
| `docs/project/checks/dp2_screen.py` | Reproducible prescribed cycle arithmetic; imposes power demand |
| `config/seed.yaml`, `variables.yaml`, `cad_map.yaml` | Current old-baseline inputs, scalar interfaces and length export mapping |
| `config/readiness.yaml`, `core/readiness.py` | Pending evidence and current fingerprint scope |
| `workspaces/coordination/interfaces.md`, `decisions.md`, `quotes.md` | Open shared interfaces, decisions and unconfirmed quotations |
| `docs/project/budget-cap.md` | Historical $5,000 plan and missing-cost risks; amount superseded for this assignment |
| October 2 `CORE_Itemized_Budget.xlsx` | Newer line-item estimate and recorded purchased-wheel route; target superseded by current user instruction |

Budget workbook absolute path: `C:\Users\andyc\OneDrive\Desktop\CORE\outputs\core-budget-20261002-fbef9859\CORE_Itemized_Budget.xlsx`. It is outside Git. Worksheet name: `Parts budget`.

The neighboring September 7 budget brief and older approximately $32,000 estimate are historical. Do not reintroduce their procurement scope or combine them with the newer budget. The September 20 agent handoff pack largely concerns education/lesson software, not this engineering implementation objective.

## What was actually checked in the code survey

- `python -m pytest -q`: 163 passed on Python 3.13 in approximately 40 seconds. This total includes learning-platform tests.
- `python run.py --status`: 14 modules, 11 draft, 3 stub, 0 verified.
- `python run.py --graph --report-only`: baseline solved and exported 35 dimensions; 15/16 numerical screens passed.
- `python scripts/generate_dependencies.py --check`: passed.
- All 10 evidence categories remain pending; the fingerprint adds an eleventh reported blocker.
- No native CAD/STEP files were found in the surveyed repository. Do not infer that the team has none elsewhere.

Baseline values: 250 N sizing target, PR 3.2, roughly 0.484 kg/s, 66,000 rpm, 125.1 mm computed compressor diameter, 184.4 mm casing OD and 413.9 mm estimated overall length. Critical separation was approximately 0.1003 against a configured 0.20 criterion. These are **old-baseline results**, not DP-2 results.

DP-2 candidate values in the project review: 0.30 kg/s; PR 1.63; 66,000 rpm calculation point; nominal 76.13/57.04 mm exducer/inducer; 1,150 K TIT; proposed 152.4/149.4 mm casing OD/ID. Exact wheel/map, bearing, turbine and NGV selection remain open. Speed and TIT are candidate analysis inputs, not demonstrated operating limits.

The archived 6% loss cycle screen reports approximately T03 348.10 K, P03 163.51 kPa, fuel 23.72 kg/h and thrust 98.10 N. The standalone combustor uses 4% prescribed loss, a 50.8 mm tunnel, 1.5 mm nominal hot-model liner wall, 2 ms bulk residence time and eight vaporizers. These are not one accepted integrated engine.

## High-risk implementation traps

1. M01 sizes flow from thrust and imposes turbine work. M10 computes wheel dimensions. A purchased-wheel case needs a genuinely different input direction.
2. M11 has no loss model; station 3 meaning and compressor-map control-volume boundaries need reconciliation before adding diffuser losses.
3. M20 does not expose all new library options, hardcodes 316SS and passes casing wall as the shared legacy wall. `n_holes_dil_count` comes only from `dil_out_qty`; DP-2 has different inner/outer dilution counts.
4. M30 uses proportional component lengths; M34 is an envelope/mass estimate. Neither defines mating faces or a real shaft/support arrangement.
5. M13 rotor mass/disc/bore geometry is simplified; M33 is blade centrifugal screening. It is not a purchased-wheel strength/life analysis.
6. M31's introductory prose overstates DN selection. Actual code gives a DN/axial-force/stiffness screen, not a selected bearing.
7. M32 is a lumped undamped model. A more sophisticated library still needs credible geometry, supports, damping and validation.
8. `run.py` multiplies every mapped CAD number by 1,000. The mapping cannot simply be extended to angles, counts and inertias without fixing export semantics.
9. `core/module.py` accepts scalar numbers/bools. Add supporting artifacts for arrays/tables instead of forcing arbitrary objects through the state.
10. `core/readiness.py` fingerprints selected Python/YAML inputs, not arbitrary future geometry/map files. Extend coverage deliberately and avoid circular output hashing.
11. Some solver/seed/RPM-sweep comments describe removed efficiency feedback or CLP behavior. Prefer executed implementation and current review over comments.
12. `tests/test_pipeline.py` intentionally exposes the unreleased baseline's critical-speed failure. Green software tests are not green engineering checks.
13. Material names conflict across seed, combustor, limit comments and budget stock. Resolve each component's actual material and temperature basis; do not copy a favorable allowable across alloys.

## October 2 budget findings

Read-only inspection traced the formulas and independently summed quantity × unit cost for the direct lines. No workbook edits or current-price re-quotation were performed for this packet.

| Item | USD | Workbook location/basis |
|---|---:|---|
| Direct parts, services and travel | 5,402 | `G120`; quantity × unit-cost sum of item rows 9–118 |
| Freight | 200 | `G122:G124` |
| Tax allowance | 450 | `G126`; 8% on direct excluding $200 travel plus freight, rounded upward to $25 |
| Manufacturing/price reserve | 550 | `G127`; 10% of direct cost rounded upward to $25 |
| Total estimate | **6,602** | `G129`, also `G3` |
| Old workbook target | 5,950 | `K4`; superseded by this conversation |
| Conditional total | 5,942 | `G148`; tax-exempt purchasing plus $185 confirmed borrowing/existing equipment, with reserve recalculated |

Against the **new** user instruction, the baseline is $1,102 above the $5,500 target and $602 above the $6,000 ceiling. The conditional $5,942 scenario is $442 above target and only $58 below ceiling; its prerequisites are unconfirmed. Do not present it as established savings or comfortable cost margin.

Important item assumptions: R01 compressor $150; R02 purchased turbine $650; R03 NGV casting $400; R04 two candidate bearings $300 total; S01 finishing $125; S02 post-finishing inspection $125; S03 assembly balancing $200; S04 balancing fixture $75. These are budget allowances/benchmarks with varying evidence, not a selected compatible package. The supplier's 85 mm turbine comparator is not the nominal 88.2 mm DP-2 rotor.

Stock examples requiring rerating: C01 0.060-inch sheet is 1.524 mm cold stock, not exactly the 1.5 mm hot-model wall; C02 2-inch tube with 0.065-inch wall is a stock proxy; C03 8 mm vaporizer tubing differs from the model's roughly 8.14 mm OD. The workbook assumes free campus machining/welding labor and reviewed shared test-site/containment/calibration access. Verify scope and availability; a local heat shield is not the assumed shared containment.

## Primary-source research starting points

Use these as entry points. Fetch the relevant current drawing/table and cite the exact applicability in each component record. Do not copy list prices or specifications into the candidate without checking the specific item.

| Source | Appropriate use and limitation |
|---|---|
| [NASA compressor–turbine matching](https://www.grc.nasa.gov/www/k-12/airplane/ctmatch.html) | Explains compressor/turbine work matching and design/off-design distinction. Introductory relations do not validate CORE's maps or geometry. |
| [Garrett GT3076R](https://www.garrettmotion.com/racing-and-performance/performance-catalog/turbo/gt3076r/) | Manufacturer geometry/map reference for its product; check the map's wheel/housing and corrected-condition applicability to any substitute. |
| [JETMAX turbine wheels](https://www.jetmax.ch/en/turbine_wheels.htm) | Lists 66, 70 and 85 mm families, blank/finished options and linked drawings. Use for purchased candidates and evidence questions, not automatic CORE compatibility. |
| [JETMAX guide vanes](https://www.jetmax.ch/en/nozzle_guide_vanes.htm) | Lists vane families and drawings, including an 85 mm blank. Establish finishing, throat and rotor matching separately. |
| [Special Metals alloy 718 technical bulletin](https://www.specialmetals.com/documents/technical-bulletins/inconel/inconel-alloy-718.pdf) | Material/condition/temperature reference when 718 is actually relevant; not a property source for another alloy or a wheel-specific allowable. |
| [NASA Chemical Equilibrium with Applications](https://www.nasa.gov/glenn/research/chemical-equilibrium-with-applications/) | Starting point for independent equilibrium-property comparison. Does not establish finite-rate combustion stability or vaporizer behavior. |
| [ROSS documentation](https://ross.readthedocs.io/en/stable/) | Documented rotor, shaft, disk and bearing models, examples and validation. Match installed version; benchmark any analysis and expose uncertain supports. |

Additional exact-part searches needed: selected wheel manufacturer; selected bearing's speed/preload/lubrication data; selected pump/driver/valve curves; actual sheet/tube material properties; balancing and finishing service acceptance; and available shop process limits. If a source is inaccessible, identify the requested datum precisely and continue with bounded assumptions rather than inventing it.
