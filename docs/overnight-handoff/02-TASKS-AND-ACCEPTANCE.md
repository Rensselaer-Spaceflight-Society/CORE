# Ordered task list and completion checks

Use these IDs in a progress log. For each task record `not started`, `in progress`, `implemented and checked`, `partially complete`, or `blocked by named input`. Keep separate software and engineering-evidence status. A task with an empty adapter and no meaningful case is not implemented and checked.

Budget for this run: **$5,500 target; $6,000 maximum total cash**.

## Execution sequence

1. T00–T02 establish the working baseline and data contracts.
2. T03–T04 identify feasible purchased-component constraints. Start T13's cost screen immediately; avoid detailing an unaffordable or unsupported combination.
3. Build an early thin end-to-end candidate through T05–T08 and T11. It may initially use explicit bounded assumptions. Integrate often.
4. Deepen T05–T10, T12 and T13 against that same candidate. Feed findings back into component choice and geometry.
5. Finish T14–T15 and the morning report. Do not use all available time on isolated components and leave integration to a later agent.

T09 and T10 can start once the shared contracts exist. T14's export schema should be defined in T02 and exercised by the first integrated case. Detailed native CAD remains the team's work.

## T00 — Establish workspace and source identity

- [ ] Read instructions and current Git status; preserve all existing changes and handoff files.
- [ ] Record source revision, branch, Python/dependency versions and available analysis tools.
- [ ] Read the source hierarchy and conflict list in `03-CONTEXT-AND-SOURCES.md`.
- [ ] Create a concise progress/decision log and candidate-output directory convention.
- [ ] Locate relevant supplied CAD, analysis, inventory and vendor data if present; distinguish absent from not inspected.

**Complete when:** the active repository and protected existing work are unambiguous, and the next agent can resume from the progress log. No remote publication or hardware action is needed.

## T01 — Reproduce and capture the baseline

- [ ] Run the existing tests, module-status report, graph/report run and generated-dependency check.
- [ ] Save machine-readable baseline station/geometry/check outputs, labeled as the old 250 N case.
- [ ] Reproduce the DP-2 cycle screen and standalone combustor result separately.
- [ ] Write a compact discrepancy table covering flow, PR, efficiencies, loss, casing, walls, bearing concept and material assumptions.

**Complete when:** existing results are reproducible or any failures are explicitly diagnosed. The baseline critical-speed failure remains visible. Old-engine and DP-2 results cannot be confused.

## T02 — Implement shared configuration and result contracts

- [ ] Add named case selection while keeping the existing default/regression case reproducible.
- [ ] Separate thrust-sizing, prescribed-flow screening and fixed-geometry rating modes.
- [ ] Define station IDs and loss boundaries, component/part IDs, datums and hot/cold conventions.
- [ ] Add schema-validated component/geometry/map/analysis records alongside scalar state.
- [ ] Define source selection for imported versus calculated quantities with one producer per variable.
- [ ] Extend design identity to all design-defining data files; detect stale analysis/geometry associations.
- [ ] Write case-specific outputs and a manifest. Failed runs must not leave older successful results looking current.

**Checks:** baseline regression; missing/conflicting inputs; unit mismatch; changed input changes fingerprint; metadata-only run timestamp does not; source switching is explicit; run outputs do not cross-contaminate.

## T03 — Fix the compressor and reconcile the cycle

- [ ] Investigate the exact wheel candidate and available map/drawing applicability.
- [ ] Record inducer/exducer/bore/axial interfaces, source dimensions and unknowns.
- [ ] Hold purchased geometry fixed; keep sizing calculations as diagnostics or a separate mode.
- [ ] Support prescribed airflow directly and compute thrust as an output for that screen.
- [ ] Import legitimate map/characteristic data with corrected-reference conditions and bounded interpolation.
- [ ] Quantify uncertainty when only a related wheel/map is available; keep it out of confirmed-data fields.
- [ ] Establish one common inlet/fuel/station definition for all component entry points.

**Checks:** wheel dimensions invariant during rating; corrected-condition round trip; map boundary rejection; consistent gas units; separate sizing closure from performance prediction; shared-state agreement with standalone components.

## T04 — Screen purchased turbine and NGV combinations early

- [ ] Compare at least the leading documented available combination against the DP-2 nominal turbine envelope. Add a second meaningful candidate if the first is incompatible or inadequately documented.
- [ ] Obtain accessible drawings and record dimensions, material/process information, cost, supplier restrictions and missing data.
- [ ] Check stage geometry, rotation, bore/attachment, flow area and plausible work/flow demand against T03.
- [ ] Connect mean-line triangles and independently supported capacity/loss information where available.
- [ ] Model blank versus finished dimensions and finishing scope separately; do not modify a purchased blade profile by scaling to the desired diameter.
- [ ] Decide whether to carry forward the candidate, change the cycle/size, or report a specific unresolved match.

**Complete when:** there is a traceable preferred candidate or a quantitative reason no candidate can yet be selected. A catalog thrust range or listed diameter alone does not complete matching.

## T05 — Define inlet, diffuser and pressure-path interfaces

- [ ] Define inlet/shroud/backplate and impeller-exit geometry, with applicable clearance and datum references.
- [ ] Replace M11's bare geometric scaling with a useful preliminary passage definition and sourced loss/recovery treatment.
- [ ] Include vane count, gap, widths, throat/exit areas, angles/coordinates or an explicit geometry-source artifact.
- [ ] Define reverse-turn and distribution volumes; connect to both combustor feed paths.
- [ ] Explain whether the compressor map already includes diffuser/housing performance, and remove any duplicate loss accounting.
- [ ] Check realizable passages, mass continuity, Mach behavior and machining access.

**Checks:** no missing physical transition; each pressure loss counted once; total/static conventions agree at interfaces; passage dimensions support the reported flow area.

## T06 — Complete the combustor's engine interface and preliminary geometry

- [ ] Expose current library controls through M20: separate walls/material, inner-annulus sizing, side-specific hole counts and diagnostics.
- [ ] Reconcile 4% and 6% prescribed losses in common-case comparisons; record the chosen provisional basis.
- [ ] Preserve exact branch and fuel mass balances and local injection-head accounting.
- [ ] Publish independent inner/outer hole diameter, quantity, row position, clocking and film rows.
- [ ] Define dome, vaporizer centerlines/bends, scoop/crimp, fuel feeds, igniter, discharge transition and mounting/expansion scheme.
- [ ] Calculate cold-stock dimensions consistently; separate stocked cold thickness from the old model's hot thickness input.
- [ ] Check circumferential/axial/diagonal spacing, film/main-hole overlap, weld seams, bend exclusions and tool access.
- [ ] Rerate practical stock/whole-hole choices rather than silently rounding analytical dimensions.
- [ ] Record thermal/vaporization/stability assessments and their evidence limits; identify the highest-value team analysis or rig measurement.

**Checks:** identical-input standalone/pipeline agreement; inner and outer flow/count preservation; pressure-budget feasibility; cold/hot round trip; actual stock changes propagate; impossible patterns fail visibly.

## T07 — Close turbine-exit, nozzle and flow capacity

- [ ] Connect turbine/NGV interface states, actual annulus/throat definitions and local shroud.
- [ ] Define nozzle contour, wall, length and mounting against the actual turbine exit.
- [ ] Implement or connect fixed-area capacity/rating and appropriate choked/unchoked behavior.
- [ ] Include pressure thrust where required and consistent backpressure coupling.
- [ ] Export section coordinates or sufficient parameterization for native CAD.

**Checks:** common mass flow and state at boundaries; physical local Mach/choking treatment; fixed geometry across operating cases; area and temperature sensitivity; no fictitious pressure gain in passive losses.

## T08 — Replace the mechanical envelope with an assembly definition

- [ ] Establish engine axis, origin and angular reference, component faces and axial/radial envelopes.
- [ ] Define a stepped shaft with seats, shoulders, fillets, retainers, spacers, bearing locations and wheel interfaces.
- [ ] Select or bound bearing/preload/lubrication candidates against exact supplier evidence.
- [ ] Include compressor/turbine mass, CG, polar/diametral inertia and all relevant rotating hardware.
- [ ] Define carrier, tunnel, seal, shroud, casing, liner support, flange and mount geometry.
- [ ] Perform first-order shaft/load, clearance and fit-stack checks with declared assumptions.
- [ ] Add data exchange for the team's structural and rotordynamic analyses; add a credible supported-rotor calculation if practical.
- [ ] Assess material/temperature, hot/cold growth, external-pressure liner buckling and retention load paths at the level supported.
- [ ] Show assembly and removal order, access to nuts/fasteners/probes and balancing interfaces.

**Checks:** mating dimensions agree; rotor and bearing centers have actual positions; no hidden use of proportional shaft-length estimates in the detailed candidate; incompatible bore/seat fails; actual geometry drives masses/analysis; critical-speed limitations remain exposed.

## T09 — Audit gas properties and engineering correlations

- [ ] Inventory equations/correlations that control a consequential dimension or feasibility conclusion.
- [ ] Check units, definitions, validity range and cited source. Flag inherited unsupported comments.
- [ ] Compare shared gas-property/fuel/work calculations with suitable independent reference information where available.
- [ ] Explain the products-property surrogate and sensitivity to its uncertainty.
- [ ] Audit hot gas versus metal temperature, material condition and time-dependent strength/life assumptions.
- [ ] Keep revised methods behind explicit, documented choices and regression cases.

**Checks:** reference data is independent of production implementation; discrepancy and validity bounds are reported; no equilibrium-property result is labeled as flame-stability proof.

## T10 — Integrate fuel, starting, electrical and instrumentation requirements

- [ ] Define complete fuel hardware and branch network; connect required delivered flow and differential pressure to real candidate curves where available.
- [ ] Include shutdown/isolation components, filters, fittings, power and mounting in both geometry and cost.
- [ ] Define starter torque-speed/power and mechanical attachment requirements and unknowns.
- [ ] Add lubrication flow/power demands if relevant and account for them once in the engine balances.
- [ ] Produce a signal dictionary and channel plan with locations, units, range, response/latency and invalid-data behavior.
- [ ] Add synthetic controller/plant-interface tests for saturation, stale/missing sensors, failure to light indication and shutdown requests.
- [ ] Keep hardware control disabled and unapproved thresholds distinct from illustrative simulation values.

**Checks:** liquid and air pressure budgets stay separate; sensor channels measure the quantities claimed; EGT is not TIT; electrical/start/fuel requirements appear in the BOM and assembly interfaces.

## T11 — Implement and exercise whole-engine matching

- [ ] Document independent inputs, unknowns, component characteristics and residual equations.
- [ ] Match common-shaft compressor/turbine conditions and fixed nozzle/NGV geometry with correct mass/energy accounting.
- [ ] Include mechanical/accessory demand without double counting efficiency/loss terms.
- [ ] Test the solver on independent/simple and explicitly synthetic cases before real-engine interpretation.
- [ ] Reject invalid map branches, infeasible geometry and unconverged roots; report a failed point rather than recycling a previous solution.
- [ ] Report steady torque balance with zero starter contribution and separate acceleration/starting requirements.
- [ ] Where necessary data is missing, calculate conditional requirements/bounds and list exactly what prevents a physical match claim.

**Checks:** fixed geometry stays fixed; both flow-capacity and power constraints are evaluated; residuals include units/scales; repeated valid starts reproduce a solution or expose multiple branches; imposed M01 power balance is not used as independent evidence.

## T12 — Test robustness and find the limiting assumptions

- [ ] Choose source-supported or explicitly illustrative ranges for major uncertain inputs.
- [ ] Evaluate physically consistent operating/environmental cases and adverse combinations, not only one favorable nominal point.
- [ ] Include component losses/efficiencies, drag/leakage, geometry/stock tolerances, nozzle/NGV area, support properties and thermal clearance as relevant.
- [ ] Treat categorical changes (wheel choice, material, bearing type, hole count) as distinct candidates.
- [ ] Rank dominant sensitivities and identify feasibility boundaries, uncertainty gaps and tolerances worth controlling.
- [ ] Compare a small set of candidate improvements; preserve the underlying fixed geometry for every rated case.

**Complete when:** the report states what breaks first, how much uncertainty the conclusion tolerates, and which measurement/analysis would change the decision. Do not report a statistical reliability percentage from arbitrary distributions.

## T13 — Reconcile manufacturing route and total cash cost

- [ ] Start from the October 2 parts budget when available; retain each source row ID for traceability.
- [ ] Replace stock-price proxies only after the candidate geometry shows the real stock/quantity/finishing need.
- [ ] Record make/buy, setups, fixtures, special processes, welds, inspection, balance and shop-capability assumptions per part.
- [ ] Calculate nesting/cut lengths with kerf, bend/weld allowances and waste where relevant; do not assume a sheet fits all parts without checking.
- [ ] Include specialist finishing, post-finishing inspection, assembled balance/fixture, freight/tax, tooling, consumables, test support and reserve.
- [ ] Track actual/committed/forecast and unconfirmed inventory separately; do not claim a complete cash forecast if spend-to-date is unknown.
- [ ] Compare total to $5,500 target and $6,000 ceiling; identify required savings and the design consequences.
- [ ] Keep unconfirmed tax exemption, borrowing, sponsorship and site/containment access as conditional scenarios.
- [ ] If over ceiling, compare a simpler full-engine candidate or a clearly scoped staged plan; do not omit essential scope to report success.

**Checks:** quantity × cost and rollups reconcile; unknown prices remain visible; no duplicate bought rotor/billet cost or sponsor credit; listed vs delivered price distinguished; contingency remains explicit.

## T14 — Produce the CAD handoff and traceability package

- [ ] Export per-part parameters with explicit units, reference temperatures, datum, tolerances/status and source identity.
- [ ] Export angles, counts, coordinates, masses/inertias and lengths with correct conversion rules.
- [ ] Include component and assembly interface tables, row patterns, centerlines and station/section coordinates.
- [ ] Generate a useful preliminary cross-section/assembly diagram from the same data, with known limitations stated.
- [ ] Include BOM part IDs and geometry revision links; list what the team must supply before detailed CAD can be finished.
- [ ] Round-trip the data through a reader; test duplicate names, missing required parameters and stale imports.
- [ ] Check a complete input-to-CAD propagation path and compare candidate revisions in a concise change report.

**Complete when:** the team can begin coherent native CAD without inventing hidden mating dimensions. A dimension CSV alone does not complete this task. Native CAD rebuild verification is recorded only if actually performed.

## T15 — Final integration, review and morning report

- [ ] Run applicable full tests, worksheet compatibility, generated-dependency checks and every documented candidate command.
- [ ] Verify the run from a clean output directory/environment as practical; capture actual logs and package versions.
- [ ] Review contradictions between component records, source data, geometry, matching, CAD and cost.
- [ ] Fix significant findings and rerun affected checks.
- [ ] Populate `MORNING_REPORT.md`, the progress log and remaining-work register with actual results.
- [ ] List implementation completion separately from engineering verification and missing physical evidence.
- [ ] Preserve all pending release evidence and unresolved engineering screens.

**Complete when:** a reviewer can reproduce the selected candidate, trace its important numbers and understand both the strongest supported conclusion and the remaining blockers. Return exact paths and commands, not just a claim that everything is done.
