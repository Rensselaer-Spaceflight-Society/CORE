# Required outputs and review contract

Use existing repository conventions when they provide the same content. The paths below are proposed destinations, not files claimed to exist already. Avoid redundant databases or a large framework rewrite. The goal is a small set of traceable source records and automatically generated results the team can use.

## 1. Deliverable structure

| Proposed destination | Required content |
|---|---|
| `docs/design/PROGRESS.md` | Resume point, task IDs/status, branch/revision, changes, commands, current failures, next action |
| `docs/design/MORNING_REPORT.md` | Main result and the concise review described below |
| `docs/design/design-basis.md` | Candidate choice, fixed parts, objectives, operating cases, assumptions and decision rationale |
| `docs/design/component-reviews.md` or one record per component | Component-specific calculation, geometry, manufacture and evidence records |
| `docs/design/interfaces.md` plus machine-readable source | Station convention, mating geometry, shared loads/signals, datums and ownership |
| `docs/design/manufacturing-and-budget.md` plus itemized source | Make/buy/process review, full scope estimate and $5,500/$6,000 comparison |
| `docs/design/verification.md` | Test methods, reference cases, exact commands, results, limitations and evidence links |
| `docs/design/remaining-work.md` | Prioritized unresolved questions with their consequence, required input and affected components |
| Versioned configuration/data directories | Candidate inputs, legitimate map/source data, geometry, imported analyses and schema versions |
| `out/<candidate>/<run-id>/` or equivalent | Manifest, station/component/operating-case results, checks, CAD exports, figures, BOM/cost summary and logs |

Prefer generated tables wherever values originate in code, so reports cannot silently disagree with the current run. Small durable reference snapshots may live in the repository; large meshes, vendor files with redistribution restrictions and transient outputs should follow repository conventions.

## 2. Component record

Every physical component or purchased assembly needs the following information. Multiple small standard parts can share one assembly record if their identities, quantities and interfaces remain explicit.

| Field group | Minimum content |
|---|---|
| Identity | Part/component ID, candidate revision, purpose, make/buy status, source of geometry, software owner/module |
| Inputs | Relevant station state, flow, speed, load cases, material/temperature, boundary conditions and referenced upstream revision |
| Design | Actual candidate dimensions/geometry or exact supplier reference; free versus fixed parameters; equations/model and validity domain |
| Interfaces | Mating part/face, datum, axial/radial/angular relation, passages/areas, fluid connections, loads and electrical signals where relevant |
| Materials | Specific grade/condition/process basis; density, thermal expansion and allowables with sources; unresolved properties distinguished |
| Manufacture | Stock size, blank/finished distinction, operations, setups/fixtures, weld/finish/inspection/balance needs and shop assumptions |
| Verification | Independent/reference checks, conservation/interface checks, margin and uncertainty, actual test commands/results |
| Cost | BOM row IDs, quantity, unit/delivered basis, source/date, estimate versus quote, required services and uncertainty |
| Disposition | What is ready for preliminary CAD, what remains provisional, what blocks manufacture/operation and the next resolving action |

Do not represent unavailable supplier geometry with zeros. A bounded design envelope can support layout, but label it as an envelope and list the exact dimensions still needed. Review labels refer to the evidence actually obtained, not a role code in a module header.

## 3. Data and source identity

The existing module state remains numeric. Put strings, provenance, tables and coordinate arrays in supporting records. A minimal record for a parameter or imported result should carry:

```yaml
schema_version: 1
component_id: example_component
candidate_id: example_candidate
quantity: example_quantity
value: null
unit: m
basis: unknown
source_reference: null
source_revision_or_hash: null
geometry_fingerprint: null
operating_case_id: null
reference_temperature_K: null
validity_domain: null
uncertainty_or_bounds: null
notes: Required input has not been supplied.
```

This is a shape example, not an instruction to put nulls in the scalar solver or use the placeholder IDs as production data. Design a concise schema appropriate to the actual record type. A check result should separately record `pass`, `fail`, `unknown` or `not_applicable`, its value/margin, units, criterion, source and reason. A missing prerequisite cannot yield `pass`.

Fingerprint the source model, selected configuration, geometry/map/analysis data and relevant numerical settings. Keep the manifest deterministic except for separately identified run metadata. References to imported analyses must include the geometry and operating case they cover. If geometry changes, the old result becomes stale even when its filename does not change.

## 4. CAD handoff

Export machine-readable data and a short human-readable parameter guide. At minimum include:

- Global assembly axis, origin, positive directions, angular zero and part coordinate transforms.
- Per-part external/internal surfaces, axial stations, mating faces and interface dimensions.
- Fixed purchased geometry versus candidate designed geometry and missing supplier dimensions.
- Liner/hole/film/tube patterns with distinct inner/outer quantities, row positions, clocking and coordinates or a complete generation rule.
- Diffuser/turn/nozzle profiles and turbine/NGV geometry references; sufficient sections/coordinates when the team is to model them.
- Shaft seats, steps, fillets, bearing centers, spacers, retention and carrier/shroud interfaces.
- Ports, mounts, fastener patterns, lubrication/fuel/sensor access and assembly sequence references.
- Units and quantity types; lengths, angles, counts, areas, masses and inertias must not share a blanket conversion.
- Cold/reference dimensions and assumed operating growth, material and temperature basis; proposed tolerance and its reason/status.
- Source, candidate/design fingerprint and software version on the exported bundle.

Read the exported data back and verify units, counts, required fields and selected geometric relationships. Demonstrate one changed design parameter reaching affected component geometry, checks and exports. Never claim the native CAD assembly rebuilds successfully unless the actual CAD application/model was exercised.

Generate a useful cross-section or interface diagram from this data. Label it schematic where the geometry is not represented faithfully. The figure must agree with the data and should expose gaps/overlaps rather than conceal them with presentation choices.

## 5. Whole-engine and self-sustain result

Each reported operating case must state:

1. Fixed geometry and purchased part IDs; independent inputs and solved unknowns.
2. Component model/data basis, interpolation location and any unsupported assumption.
3. Station total/static states, air/fuel/bleed flows, shaft speed, component powers/torques and separately accounted losses.
4. Matching residuals with units, scales, tolerance rationale and convergence status.
5. Relevant map-domain, surge/choking, temperature, flow/pressure, clearance and mechanical screens, including unknowns.
6. Whether starter torque is zero, what evidence supports stable combustion, and what is unresolved about acceleration/starting.
7. Sensitivity cases, the first limiting condition and the measurements/analyses that could reverse the conclusion.

Use a plain conclusion such as “conditionally feasible at the modeled point under assumptions A–D; supplier turbine characteristic and combustion stability remain unresolved.” Do not turn that into “will run.” Conversely, do not hide a useful quantitative result behind only a generic disclaimer. State the actual calculated requirement, margin or failure.

If no credible real-engine match can be computed, deliver the verified matching software, conditional feasibility bounds and missing-data requests. Synthetic validation figures must be visibly labeled and separate from candidate-engine figures.

## 6. Manufacturing and budget result

For each BOM line retain stable ID, linked component, quantity/unit, specification, make/buy, existing/paid/committed/forecast status, cost basis/date/currency, shipping/tax treatment, in-kind status, lead-time evidence and unknowns. Material stock dimensions are purchasing inputs until geometry verifies them.

Report full-scope nominal and adverse totals, scope completeness, unresolved price exposure and the reserve basis. Compare against both the $5,500 target and $6,000 ceiling. Distinguish a total below ceiling from a total conditional on free services, borrowed equipment or tax exemption. Do not imply the adverse case is a statistical percentile unless its distribution is justified.

For savings proposals show the affected part/process, supported amount or range, engineering consequence, implementation dependency and whether the saving is confirmed. The user needs a prioritized route to the budget, not a lowered spreadsheet total with omitted scope.

## 7. Verification evidence matrix

| Layer | Evidence to deliver | Common false positive to avoid |
|---|---|---|
| Equations and units | Independent calculation/reference, dimensional consistency, valid-domain and limit cases | Expected value copied from the new production function |
| Components | Geometry/flow/load checks, input rejection and an applicable reference case | A plotted shape or module maturity label treated as physical validation |
| Interfaces | Shared-state agreement, source identity, conservation and data propagation | Two components using different definitions for the same station |
| Matching | Analytic/simple solver tests, bounded real-data run or explicit conditional bounds | Imposed turbine power balance presented as delivered turbine performance |
| Robustness | Consistent fixed-geometry perturbations and feasibility boundaries | Resizing hardware separately at every off-design point |
| Mechanics | Actual geometry/support assumptions, model benchmark/convergence and missing-evidence list | Generic DN or blade-root margin treated as full rotor qualification |
| CAD | Schema/round-trip checks, correct conversions, mating geometry and actual rebuild only if available | Successful CSV export treated as a complete assembly |
| Budget | Traceable quantities/costs, scope reconciliation and conditional savings separated | Missing quote converted to zero or donated equipment counted twice |
| Final integration | Reproducible commands/logs and an input-to-report trace | Green tests used to erase unresolved engineering screens |

Record numerical residual tolerances separately from engineering design margins. Choose and justify tolerances appropriate to each calculation; do not relax them solely to admit a bad case. Preserve tests that demonstrate expected rejection and failure behavior.

## 8. Morning report

Lead with the chosen candidate and strongest supported outcome. Keep the opening concise, then link the detailed evidence. Include:

- Source revision/branch, changed files and exact commands to reproduce baseline, candidate, matching/sensitivity, CAD export and budget.
- A component completion table separating implementation, preliminary CAD readiness and engineering evidence.
- A compact before/after table of consequential changes with input/assumption changes identified.
- The self-sustain conclusion, its assumptions, numerical residuals, worst important sensitivity and unverified mechanisms.
- Manufacturing route and total cash versus $5,500/$6,000, with unresolved costs/support.
- Test totals and failures, optional checks not run and known defects left unresolved.
- Five prioritized team actions. Each must name the needed answer/result and affected decision, such as exact supplier wheel geometry, bearing support coefficients, material temperature analysis or confirmed balancing service scope.
- A continuation note with the next executable task, avoiding repeated investigation.

Finish only with claims supported by the saved evidence. If a result is infeasible or unresolved, say so plainly and identify the best next design change or source of information.
