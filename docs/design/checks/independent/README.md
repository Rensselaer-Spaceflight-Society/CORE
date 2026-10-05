# Independent checks (verification pass, 2026-10-04)

Scripts written during the independent verification recorded in
[`../../independent-verification.md`](../../independent-verification.md). They recompute repository results
from the run outputs, the case file and the component records with their own equations. They are evidence
for the arithmetic and the conventions only; they are not physical validation.

Rules they follow:

- They import **no code under test**: no engine, rating, map, combustor, assembly, rotor, CAD, budget or module
  code. The only repository import is `core.gas` for gas *properties* (enthalpy, cp) where noted.
  `phase1/` probes are the exception: they exercise the repository code on purpose (labelled *probe*).
- They read the snapshot in `docs/design/results/<case>/` by default; pass another run folder as the first
  argument. Run them from the repository root.
- Each prints one line per comparison (independent value, repository value, difference) and exits 1 on any
  unexplained difference above its tolerance (normally 1 %).
- The budget scripts open the workbook outside the repository **read-only** and check its SHA-256 before and
  after.

| Folder / script | Checks | Imports from the repository |
|---|---|---|
| `cycle_turbine/r3_turbine_check.py` | R3 outlet closure (energy, Euler, continuity, η_tt, T05); re-rating of the turbine mean line from the reported inlet state; pre-review energy gap | `core.gas` properties |
| `cycle_turbine/cycle_closure.py` | compressor/turbine power, bearing and windage losses, FAR and fuel, T04→T41 mixing, pressure ledger, nozzle and thrust along the operating line | `core.gas` properties |
| `cycle_turbine/reynolds_validity.py` | turbine Reynolds numbers vs the 2e4 flag (Sutherland air viscosity) | `core.gas` properties |
| `map_matching/map_checks.py` | corrected-flow/speed reference, β-line interpolation, map domain, DP-2 off-map claim, blade-work coefficient, surge margin | `core.gas` properties |
| `map_matching/match_resolve.py` | own engine model: design-point and 56 krpm re-solve, nozzle-trim points, feasibility-window edges | `core.gas` properties |
| `map_matching/probe_matching.py`, `probe_inner_grid.py` | probes of `core.engine_match` (uniqueness, trends, inner-grid miss) | code under test (probe) |
| `comb_nozzle_struct/check_comb_nozzle_struct.py` | R7 nozzle and thrust, combustor residence/holes/penetration/seam/ligaments, shaft torsion and stress, tip clearance, liner buckling, casing hoop stress | `core.gas` properties |
| `rotor_cad/*.py` | rigid-body and bending modes by independent models; support-stiffness sensitivity; stack/CAD bundle audit | none / probe as labelled |
| `budget_provenance/budget_check.py` | workbook $6,602 with its formulas, CSV extraction, PD-1 scenarios and routes | none (workbook read-only) |
| `budget_provenance/provenance_check.py` | "supplied" values have sources; provenance labels match record bases; assumptions visible in the reports | none |
| `budget_provenance/nozzle_nesting_check.py` | nozzle flat patterns against the C01 remainder strip | none |
| `phase1/axial_growth_check.py` | R6 axial growth by hand, plus the stack-faithful load path | none |
| `phase1/readiness_compare.py` | legacy readiness fingerprint and blockers, committed vs working tree (needs `git show HEAD:core/readiness.py > <file>` as its argument) | `core.readiness` (probe) |
| `phase1/snapshot_probe.py` | snapshot validator on temporary copies: intact, tampered, missing and stale runs | snapshot script (probe) |
| `phase1/viscosity_probe.py` | turbine Re and η_tt with the current viscosity law against the pre-fix law | `core.turbine_rating` (probe) |
