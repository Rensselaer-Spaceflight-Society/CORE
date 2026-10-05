# Execute the CORE preliminary engine design and integration work

You are the implementation and preliminary engineering integration agent for CORE, a student reverse-flow microjet. Work through this assignment carefully and persistently. Make changes, run calculations, reconcile interfaces, test the assembled software, and produce a reviewable candidate design. A plan alone does not satisfy this assignment.

## 1. Objective and working arrangement

The project objective is a successfully self-sustaining engine; thrust is secondary. Advance the design as far as the available evidence supports, with a total cash **target of $5,500 and hard maximum of $6,000**. Develop a plausible, manufacturable candidate and expose the specific reasons it may fail. A result that identifies an infeasible component combination and supplies a better-supported alternative is useful progress.

The team will build native CAD and perform/approve the detailed engineering analyses. You own the connecting software, source-grounded first-order calculations, complete preliminary component definitions, analysis exchange, verification and organized handoff. Do not leave everything awaiting human analysis: implement useful bounded calculations, candidate geometry and sensitivity studies now. Do not pretend that first-order calculations replace component maps, detailed CFD/FEA, supplier acceptance or experimental evidence.

Prefer the purchased turbine wheel plus compatible guide-vane casting/finishing route recorded in the October 2 project budget. Treat exact wheel and NGV selection as a candidate decision to substantiate. Preserve the possibility of a different size or matched pair if DP-2 cannot be supported. Do not default to designing a new high-temperature rotor from a generic billet.

Read this complete prompt, `02-TASKS-AND-ACCEPTANCE.md`, `03-CONTEXT-AND-SOURCES.md`, `04-OUTPUT-CONTRACTS.md`, and `../preliminary-design-roadmap.md` before implementing the shared interfaces.

## 2. Start from the actual repository

The expected working repository is `C:\Users\andyc\OneDrive\Desktop\CORE\github-core`. Inspect applicable `AGENTS.md` instructions, Git status, branch and current revision. Do not work in the older neighboring `core-engine` snapshot or `tmp/combustor-dp2-publish` checkout by accident. Preserve existing user changes, including untracked handoff documents. Keep changes on a suitable local feature branch; do not reset, clean or overwrite unrelated work.

Read `README.md`, `CONTRIBUTING.md`, the current model review, DP-2 review, combustor update, budget review, coordination registers, `run.py`, `core/`, `modules/`, configuration and relevant tests. Historical `HANDOFF.md`/`PATCHES.md` claims are superseded where current source or reviews disagree. Reinspect instead of assuming this packet is newer than all future changes.

Run the baseline tests, dependency check and preliminary report first. The October 4 baseline had 163 passing tests, 14 modules (11 draft, 3 stub), 35 CAD dimensions, and one failed critical-speed screen. Preserve a baseline snapshot of configuration, numerical outputs and checks. Record any discrepancy; do not weaken a test or limit to make a new design look better.

Use available tools and documented library APIs. Add dependencies only when they materially improve the result and can be reproduced. Keep optional specialized solvers out of the minimal runner's mandatory path where possible. Use an isolated environment for additions. Do not spend the whole run installing unavailable commercial tools.

## 3. Scope, autonomy and evidence discipline

Proceed without repeated clarification on reversible implementation choices. Make reasonable candidate decisions, record why, and compare alternatives when a decision materially affects geometry, cost or feasibility. If data is unavailable, continue the independent work and publish the exact missing input and its consequences. Do not mark a requirement complete merely because an import schema or TODO exists.

You may inspect sources, research public technical/vendor information, implement code, create local reports and draft candidate drawings/data. This assignment does not authorize purchases, supplier messages, publishing, production hardware control, manufacturing release or inventing a person's approval. Keep work local unless the user separately authorizes another action. No running hardware is required for this assignment.

Separate these forms of evidence in the data model and report:

- supplied/observed component data;
- primary-source reference information;
- calculation derived from stated inputs;
- provisional engineering assumption or proxy;
- result needing unavailable analysis or testing.

For important facts retain source, access date, units, applicability and uncertainty/range where supported. A third-party billet wheel is not proven to have the original manufacturer's map. Catalog material properties are not automatic component allowables. Missing data is not zero, and an unknown check is not a pass. Do not fabricate maps, mesh results, supplier curves, quotations or test evidence. Synthetic data is allowed only for clearly isolated software verification and illustrative sensitivity cases.

Do not silently change `config/limits.yaml`, record reviewed evidence, or label hardware verified to satisfy a summary. Existing limit comments also need an applicability audit; flag doubtful ones rather than treating them as universal engineering standards. If a new candidate needs a different criterion, document the proposal separately for team review.

## 4. Establish a single engine definition

Implement named configurations with explicit modes:

1. Preserve the existing thrust-driven sizing baseline for regression.
2. Add a candidate using prescribed flow and fixed purchased-component geometry.
3. Distinguish those design screens from genuine fixed-geometry operating-point matching.

Do not infer DP-2 airflow by tuning a thrust target until the numbers happen to agree. Do not overwrite purchased wheel geometry to satisfy Euler sizing. The selected compressor and turbine/NGV geometry must remain fixed during a rating run. Candidate changes need separate identities and a comparison.

Use one station convention, one shared gas-property implementation and one pressure/power/mass ledger. Explicitly distinguish total/static, absolute/gauge, hot/cold and axial/tangential/relative quantities. Document the control volume represented by compressor map pressure ratio and efficiency before adding a separate diffuser loss. Account for fuel addition, bleed, cooling and seal/lubrication air at their actual extraction and re-entry locations. Do not count an internal combustor air split as lost engine flow.

Maintain one producer for each computed state variable. Support imported versus calculated values through an explicit source-selection adapter, not two competing writers or silent overrides. Keep the numeric state contract, and place tables/coordinate arrays/component records in versioned supporting files. Validate and fingerprint all inputs that actually determine the design, including external analysis/map/geometry artifacts. Keep run timestamps outside the deterministic design identity.

Provide named per-run output directories so cases cannot overwrite each other or accidentally mix a fresh station table with stale geometry. Produce a manifest linking configuration, source revision, artifact hashes, assumptions and generated results.

## 5. Work through every component and its physical interfaces

For each component, produce the design record specified in `04-OUTPUT-CONTRACTS.md`. Include actual candidate parameters where defensible, equations and range of validity, upstream/downstream interfaces, manufacturing route, cost basis, checks and remaining evidence. Finish the following work in the dependency order in the task list.

**Inlet and compressor.** Identify the exact candidate wheel and reference conditions. Record inducer/exducer, bore, backface/axial dimensions, blade family, rotation and attachment information. Determine whether the available map applies to that wheel and housing. Import/trace legitimate map points and preserve digitization uncertainty if using a chart. Reject unsupported extrapolation by default. Calculate corrected conditions consistently. Establish a candidate operating region and explicitly define any reported surge-margin metric. Develop the inlet/shroud/backplate interfaces and inlet loss assumption.

**Diffuser and reverse-flow routing.** Replace bare diameter/velocity scaling with a useful geometry and loss/recovery model or an adapter to actual analysis. Define gap, width, passage count, throat/exit area, vane/channel representation and routing into the combustor feed annuli. Use a referenced correlation only within its domain. Resolve where each loss is counted. Review machining access and the physical turn geometry. An outer diameter alone is not a diffuser design.

**Turbine and NGV.** Screen purchasable, compatible candidates early. Distinguish catalog geometry from assumed aerodynamic parameters. Rate the selected geometry against the compressor work/flow demand rather than continually sizing it to deliver exactly that demand. Carry velocity triangles, angles, annulus areas, local states, throat capacity, incidence/deviation and losses to the extent supported. Check local absolute/relative Mach and the appropriate choking condition; the overall engine pressure ratio cannot establish local stage choking. Provide attachment, shroud and axial-clearance interfaces. For missing sections, obtain source drawings or keep explicit requirements; do not fabricate precision geometry for a purchased blade. Custom parametric geometry may be supplied as a separately labeled alternative with an honest fabrication assessment.

**Combustor and vaporizers.** Integrate existing library improvements through M20 before rewriting validated bookkeeping. Expose independent casing/liner/tunnel walls, material choice, inner-annulus sizing and independent inner/outer hole counts. Use one common inlet/fuel state. Compare the existing 4% and 6% prescribed-loss cases and select a justified provisional basis; do not call prescribed loss a prediction. Preserve exact air and local pressure balances. Define cold stock, liner surfaces, all row coordinates/counts/clocking, dome, tubes/scoops, igniter, fuel feeds, reverse-flow exit, mounts and expansion allowance. Check circumferential AND axial/diagonal ligament/interference geometry, seam and bend exclusions, and drill access. Stock rounding must trigger rerating of flow area, pressure, wall stress and fit. Treat ignition, vaporization, coking, blowout, recirculation and exit temperature pattern as physical mechanisms to assess; bulk residence time or one heat-flux number cannot establish all of them.

**Nozzle and hot-path transitions.** Define a realizable contour, length, wall, attachment and turbine-exit interface. Reconcile nozzle capacity with upstream flow at common states. Include pressure thrust when applicable and expose backpressure coupling. Keep geometry fixed for rating and include manufacturing tolerances in area sensitivity.

**Shaft, attachments and bearings.** Build an explicit stepped axial stack with component faces, shaft sections, bearing locations, shoulders, fillets, retention, preload/floating arrangement, seals and lubrication. Use actual or clearly estimated rotor masses, centers of gravity, polar and diametral inertias. Provide torsion/bending/load checks with material/temperature and stress-concentration assumptions. A torsional diameter floored by bearing bore does not define the seats or establish a compatible fit. Obtain exact bearing operating conditions where available; DN alone does not select a bearing. Check thrust direction/cases, thermal growth, preload changes, support stiffness/damping and lubrication consumption/routing.

**Rotordynamics and rotor strength.** Correct obvious model inconsistencies, add a useful supported-rotor model if practical, and connect team analysis import. If using ROSS or another solver, validate against its documented benchmark and a simple independent limiting case, then check discretization convergence for the candidate. Plot relevant modes, Campbell behavior and forced/unbalance response only when actually computed. Show sensitivity to uncertain supports. Review critical-speed crossing separately from steady operating separation. Do not call blade centrifugal stress a disc/rotor burst or life calculation. Include the requirements for supplier/process/thermal/life evidence and quantify what your first-order model can establish.

**Casing, supports, sealing and manufacture.** Replace proportional envelope lengths with real axial stations. Include compressor housing, diffuser/backplate, tunnel, bearing carriers, turbine shroud, liner supports, flanges, fasteners, sensor bosses and engine mounts. Carry pressure direction, external-pressure liner buckling, differential expansion and local metal temperature. Check assembly/disassembly order and tool access. Separate the pressure casing and heat shield from any fragment-containment function.

**Fuel, starter, electrical, controls and instrumentation.** Define selected or candidate pump/driver/valve/filter/injector hardware and a complete delivered-flow/pressure budget. Keep liquid pressure separate from vaporizer air pressure. Address manifold distribution and bearing-lube supply if applicable. Include starter torque-speed/power requirements, attachment and disengagement concept, electrical power/current budgets and signal units/timing. Identify sensor locations, ranges, resolution and response time from the purpose of each measurement. Distinguish measured EGT from turbine inlet temperature and from metal temperature. Implement useful synthetic controller/plant interface tests; keep unsupported thresholds explicitly provisional and hardware outputs disabled. Do not let full firmware development displace the integrated preliminary engine work.

## 6. Assess self-sustain without circular proof

This is the highest-value whole-engine assessment. The existing M01 imposes turbine work equal to compressor demand. Reprinting that equality or target thrust is not evidence that the selected turbine can produce the required work.

Create a fixed-geometry matching/rating path. State the independent inputs, unknowns, constraints and residuals. Use available component characteristics for compressor pressure/work, turbine flow/work and nozzle capacity. Include appropriate combustor/duct losses, fuel addition, cooling/bleed/leakage, mechanical/accessory loads and common shaft speed. Do not prescribe every operating quantity and then claim to have solved them.

At a candidate operating point, report mass, pressure/flow-capacity and shaft-power residuals with units, normalization and justified tolerances. Show compressor and turbine powers and all modeled losses separately. If a mechanical-efficiency term already represents a loss, do not subtract that loss a second time. Check solver bounds, initial-guess sensitivity, invalid branches and nonconvergence. Use supported local map interpolation and label each result by the evidence quality of its inputs.

At steady self-sustain the net shaft torque must balance with no starter contribution; acceleration requires positive net torque. A positive torque surplus at an arbitrarily prescribed state is not itself a steady operating solution. If transient screening is implemented, use a consistent inertia and torque balance, handle zero/low speed without dividing by zero, and use component characteristics valid for that region. Describe a route from assisted acceleration to a candidate self-sustaining region only to the extent supported. Do not infer ignition or starter-cutout speed from a tip-speed analogy. Do not call a favorable local net-torque slope proof of whole-engine dynamic stability.

If real maps/ratings are insufficient, still build and verify the solver on separately labeled synthetic cases; perform transparent parameter-bounded engine screens; identify the required turbine efficiency/capacity, maximum tolerable losses or other thresholds. Clearly label the real-engine conclusion as unresolved or conditional. Do not substitute made-up curves merely to obtain a root.

For the fixed candidate, evaluate physically consistent perturbations: ambient conditions, component efficiency/loss uncertainty, bearing/seal drag, leakage, nozzle/NGV area tolerance, combustor pressure loss and thermal growth. Derive ranges from evidence where possible; label illustrative ranges and avoid probabilities of success without justified distributions. Keep fixed wheel geometry, map consistency and coupled quantities intact across these cases. State which conclusion fails first and what measurable input would resolve it.

## 7. Design for fabrication and the actual budget

Use readily obtainable stock and realistic shop operations when they satisfy the design. Prefer simple turning, accessible milling/drilling and supported sheet/tube fabrication. The source workbook assumes free campus machining and welding labor; tool availability, process suitability, schedule and quality still need confirmation. Explain setups, fixturing, stock utilization, weld sequence/distortion, finishing, balance/inspection and assembly access for each custom part.

Do not describe a part as easily manufacturable merely because a solid model can be made. Separate design capability, shop capability and service/vendor acceptance. Identify which dimensions demand precision and why; do not give every dimension arbitrary tight tolerances. Track cold stock sizes and tolerances, and evaluate hot dimensions from the chosen material/temperature basis rather than shrinking commercially bought sheet twice.

Reconcile the October 2 itemized budget with the current candidate and current user instruction: $5,500 target, $6,000 maximum. Its $6,602 baseline is an estimate, not an authorized spend. Carry paid, committed and forecast amounts without double counting, and clearly flag missing actual-spend/inventory information. Include freight, tax assumptions, tooling, rework, inspection, balancing/fixtures, fuel/start/electrical hardware, instrumentation and test-support dependencies. Do not treat unknown prices as zero or foreign list prices as delivered USD quotes.

Retain the purchased turbine/NGV route unless a documented comparison supports an alternative. Do not charge rotor billet/heat treatment a second time when already included in purchased hardware; do include any required post-finishing inspection/balancing. Compare nominal and plausible adverse costs and identify the largest unresolved quote risks. Preserve a stated reserve. List cost-reduction options with physical consequences, not generic percentage discounts. Conditional borrowing, sponsorship and tax exemption stay conditional until supported. If no supportable full-scope design fits $6,000, report that result and propose scoped alternatives without labeling an incomplete engine budget complete.

## 8. Verify in layers and repair what you find

Verify equations/units, component behavior, interfaces, whole-engine closure, CAD export and cost completeness separately. Use conservation, independent hand calculations/reference cases, limiting cases and failure-path tests. Two wrappers calling the same function are an integration check, not independent physical validation. A golden output generated from the implementation under test is not its own reference.

Test mismatched units/reference conditions; invalid pressure/temperature/efficiency; unsupported map regions; missing/duplicate component IDs; wrong inner/outer counts; impossible fits; infeasible thermal clearance; stale imported results; nonconvergence; and missing prices/evidence. Ensure these produce explicit useful failures and cannot silently appear as zeros, favorable margins or complete coverage. Check that a parameter change actually propagates through dependent geometry, analysis identity, CAD and cost outputs.

Retain current meaningful tests, update expectations only with documented physical justification, add targeted tests for implemented behavior, regenerate dependency documentation and run the full required suite at integration milestones. Record precise commands, versions, exit status and logs. Use reproducible relative paths in the repository and explicit output identities. If optional solvers are unavailable, report their checks as not run.

Reserve a final integration/review pass. Trace at least one full path from candidate inputs through component geometry and losses to operating assessment, CAD parameters and BOM. Review unit conversions, borrowed assumptions, geometry fixed during rating, stale outputs, double counting and unsupported conclusions. Fix material findings and rerun affected checks.

## 9. Persist, prioritize and leave a useful morning handoff

Follow the task list. First deliver one working end-to-end candidate case; then improve the largest feasibility uncertainties. Keep a progress file containing completed task IDs, commands, important decisions, failures, next action and the state of any running process. Update it at meaningful milestones so work survives context loss. Keep candidate/source data and review records distinct from generated results.

Do not spend the run on a website, learning platform, decorative dashboard, broad framework rewrite or unbounded optimization. Do not stop because one vendor map is unavailable. Complete the useful engineering/software branches, quantify the gap and continue. If time/resources are limited, prioritize integrated configuration, actual purchased-component constraints, combustor integration, assembly data, matching/uncertainty, budget and the final handoff over optional visual polish or full firmware.

Use any delegated work only if separately authorized by the user/environment, with shared contracts and a single integration owner. This prompt does not require delegation to succeed. Do not create user-owned chats, recurring automations or external messages as an implementation shortcut.

Finish with the files and content required in `04-OUTPUT-CONTRACTS.md`, including a concise morning report that answers:

1. What candidate did you actually implement, and why?
2. Which components and interfaces are complete enough for preliminary CAD, and which dimensions remain provisional?
3. What did the fixed-geometry self-sustain assessment show, under which assumptions, and what could reverse it?
4. What is the full estimated cash requirement versus $5,500/$6,000, and which costs/support remain unconfirmed?
5. Which tests/calculations were run, what failed, and which engineering analyses remain unavailable?
6. What are the next five highest-impact team actions, with the specific measurement, decision, analysis or supplier answer required?

State the outcome at the strength the evidence supports: implemented software; numerically consistent candidate; conditionally feasible candidate; unresolved; or infeasible under stated assumptions. Only physical evidence can establish demonstrated engine operation. The purpose of this distinction is to direct the next engineering work precisely, not to excuse incomplete implementation.
