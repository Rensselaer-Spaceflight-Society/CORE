# PD-1 morning report — October 4, 2026 (updated after the independent verification)

PRELIMINARY - NOT FOR MANUFACTURE. Nothing here is a release, an approval or a test result. All work is
local, on branch `feat/preliminary-design-integration` (base `98c4167`); nothing was committed, pushed,
purchased, sent or published, and no hardware was commanded. `README.md`, `docs/overnight-handoff/` and
`docs/preliminary-design-roadmap.md` were left as found.

**Outcome strength.** PD-1 is a **numerically consistent candidate, conditionally feasible at its 68 krpm design
point** under stated assumptions: there the fixed-geometry match closes with zero starter torque, T04 848 K,
and the turbine loss correlation is (just) inside its range. Across the rest of the steady range, 56–66 krpm,
the match also closes, but the turbine loss correlation is used below its Reynolds-number range, so
feasibility there is **unresolved** by this model — neither shown to work nor shown to fail. Within the same
model the design point tolerates large turbine losses (it still matches with T04 ≤ 1150 K down to η_tt ≈ 0.51),
but every such statement is conditional on the assumed NGV/rotor throats and angles. Everything here is a
preliminary calculation, not demonstrated operation.

Still **unresolved**: the turbine/NGV flow geometry and the stage efficiency at Re ≈ 2e4 (the predicted 0.85 is
probably optimistic); the compressor characteristic of the actual wheel; combustion at PD-1's low pressure and
flow (and two combustor screens whose pass rests on modelling approximations); the low-speed/starting region;
and — new — **the rear-bearing path through the NGV casting**, whose 48 mm hub pocket is blind, so the assembly
order is not established. The 20 % critical-speed separation holds only for mount stiffness below ≈ 3.9 N/µm
**and** damping below ≈ 2.6 kN·s/m, both unmeasured. Cash is **over the $6,000 ceiling** in every unconditional
scenario.

Authoritative numbers: [`results/pd1-jm85/SUMMARY.md`](results/pd1-jm85/SUMMARY.md), generated from run
`out/pd1-jm85/4a7560bfca63/` (design fingerprint `4a7560bfca63`). If this report and SUMMARY.md disagree,
SUMMARY.md wins. Claim-by-claim verification: [`independent-verification.md`](independent-verification.md).

**Run status: current.** All three cases were rerun after the verification fixes and snapshotted:
`pd1-jm85` `4a7560bfca63` (with robustness, 19 min), `dp2-prescribed` `d3cc73ced0c7`, `baseline-250N`
`cda5fff53d3a`. The snapshot tool refused nothing; it now also refuses runs with a missing listed output. Full
suite: **244 passed** (229 before the verification; 15 regression tests added).

## 1. Candidate and why

**PD-1 (`config/cases/pd1-jm85.yaml`)** — GT3076R-class 76 mm compressor wheel (56 trim) with a CORE vaned
diffuser (19 vanes, Ø126 mm exit) → front-dome annular combustor with 8 J-vaporizers in the 152.4 mm casing →
**purchased JETMAX TW85 finished turbine + JETMAX NGV85 casting finished by CORE** → Ø54 mm conical nozzle.
10 × 26 × 8 hybrid bearings at both ends on soft damped mounts; 4140 stepped shaft; steady range 56–68 krpm.

Why this one:

1. **It is the purchased turbine/NGV route in the project materials** and the only one with documented
   dimensions (supplier drawings, re-read in the verification: wheel Ø85/Ø55, bore 9.99 ±0.005 mm, boss Ø14 × 19;
   NGV hub Ø55.4, flange Ø104, outer ring Ø92, **Ø48 hub pocket blind with a centre web**). It removes turbine
   and NGV design and casting from the critical path.
2. **The DP-2 operating point is not supported.** On the digitized GT3076R map the 76 mm wheel chokes near
   0.25 kg/s / PR 1.29 at 66 krpm; 0.30 kg/s at PR 1.63 first appears near 84 krpm (independent check;
   `results/dp2-prescribed/map_consistency.json` reports 85 krpm on a 2.5 krpm grid). A supporting check —
   corrected in the verification — puts the blade work coefficient PR 1.63 needs at 66 krpm at 0.837 against a
   Stanitz slip of 0.820 for 11 blades; that still exceeds slip, but only while η_c < 0.735, so the map carries
   the conclusion.
3. **The match is solved, not imposed.** Turbine work comes from a mean-line rating of the fixed stage; the
   operating point satisfies nozzle mass and shaft power balance with zero starter torque
   (`core/engine_match.py`, residuals ≤ 3e-12). An independent re-implementation reproduces it to 1e-6.
4. **A fallback exists on the same route.** JETMAX TW70 + finished NGV70 also matches across 56–68 krpm
   (T04 ≈ 792 K, ≈ 35 N at 68 krpm with a Ø46 mm nozzle; `robustness.json → alternative_candidate`), with the
   same correlations and the same low-speed Reynolds caveat.

Not chosen: DP-2 as proposed (point unsupported); a CORE-designed turbine (no time, no casting route); a folded
combustor wrapped around the turbine. The repository calls the combustor "reverse-flow"; the library geometry
is a front-dome annular combustor (design-basis §1). If the team means a folded combustor, the stack changes
completely.

## 2. CAD readiness

Bundle: `results/pd1-jm85/cad/cad_bundle.json` (186 typed parameters with units, basis, tolerance and reason;
23 interfaces; hole/vane/fastener patterns; nozzle, shaft and station sections), validated by read-back.
Status counts: 147 provisional design, 19 fixed purchased geometry, 14 envelope only, 6 unresolved - do not
model. (The earlier "182" was an arithmetic slip; the bundle had 185.)

| Can be modeled now (provisional) | Must wait |
|---|---|
| SH-01 stepped shaft profile, SL-01/02 | **NGV hub passage and BC-02 rear carrier** (blind Ø48 pocket with a centre web; team decision first) |
| TU-01 tunnel (except its rear slip joint), CS-01 casing, CS-02 rear cover (ID clears the Ø92 NGV outer ring) | **Finished compressor and turbine seat diameters** (measured bores, approved fits) |
| DF-01 backplate: OD, spigot, seal bore, 19 channels (LE Ø82.2, exit Ø126; vane angles moved ~1.5° after the blade-work correction) | **BC-01 sleeve OD / backplate pocket diameter** (`BC01_SLEEVE_OD`, not designed yet) |
| NG-01 finishing features: shroud bore Ø85.70, flange faces, 12 × M3 on PCD 98 | **CW-01 shroud contour → CH-01 shroud**: scan the purchased wheel first |
| EX-01/02 nozzle (Ø54 exit, plus a Ø50 trim spare), tailcone (as a hollow shell clearing the shaft end and nut), IN-01 bellmouth | **TR-01 blade sections and NGV vane geometry**: never model from guesses |
| CB-01 dome, CB-04/05 cones, VP-01 vaporizers (rerate to ¼ in stock first) | **Rotation direction (IF-ROT)**; **liner hole pattern (CB-02/03)** — the weld-seam check fails; bearing pockets until the supplier confirms speed and preload |

No native CAD application was available, so no CAD rebuild was performed. CAD masses and inertias should be
returned so rotordynamics can be rerun on the modeled parts (`remaining-work.md` #20).

## 3. Self-sustain result

Design point, 68 krpm ISA SLS, zero starter torque: 0.2009 kg/s, PR 1.486, η_c 0.763, T04 848.0 K, turbine
η_tt 0.846, NGV flow 74 % of choke, fuel 9.53 kg/h, gross thrust 41.2 N. Compressor 9.137 kW, turbine
9.254 kW, bearings plus windage 118 W. Mass and power residuals below 3e-12 (relative). Turbine rotor
Reynolds number 20,024 against the code's validity flag at 2e4.

Operating line (proxy map, matched at every speed 55–80 krpm):

| N (krpm) | 55 | 56 | 60 | 64 | 66 | 68 | 72 | 76 | 80 |
|---|---|---|---|---|---|---|---|---|---|
| T04 (K) | 850.9 | 849.8 | 847.3 | 846.9 | 847.3 | 848.0 | 855.3 | 864.5 | 874.2 |
| Thrust (N) | 25.0 | 26.2 | 31.0 | 36.0 | 38.6 | 41.2 | 47.6 | 54.7 | 62.0 |
| Surge margin (flow) | 0.574 | 0.575 | 0.579 | 0.580 | 0.580 | 0.580 | 0.579 | 0.577 | 0.574 |
| Turbine rotor Re (×1e3) | 15.1 | 15.6 | 17.1 | 18.6 | 19.3 | 20.0 | 21.5 | 23.0 | 24.4 |
| Turbine correlation in range | no | no | no | no | no | yes | yes | yes | yes |

**What it rests on (the assumptions that carry it):**

- NGV85 exit angle 65° → effective throat 1494 mm² (range 58–72° evaluated); rotor exit angle −58°.
- The GT3076R map stands in for the actual wheel (related-wheel proxy; billet 11+0 wheel ≠ mapped wheel). It is
  taken to include CORE's vaned diffuser.
- Soderberg turbine losses at rotor Re 1.6–2.0e4 (basis 1e5). The code's validity flag at Re 2e4 has no cited
  source. Combustor loss 2.5 %, turn/deswirl 2 %, tunnel leak 2 %, inlet 1 %, jet pipe 1 %, nozzle Cd/Cv 0.97.
- Bearing and windage losses from catalogue-type models.

**Robustness (fixed geometry, 31 cases × 56/66/68 krpm = 93 points), one validity rule.** A point is *fails*
when there is no steady match or a physical screen is exceeded; *unresolved* when its only problem is a model
outside its validity range; *feasible* otherwise. Result: **10 feasible, 2 fail, 81 unresolved** (79 because
the turbine correlation is below its Reynolds range, 2 because the corrected speed is below the map). The two
failures are the combined adverse case at 66 and 68 krpm (T04 1317 K). Every single-parameter case keeps the
model's T04 below 955 K, but at most of those points the correlation is out of range, so they are model
predictions, not feasibility evidence. Feasible points are all at 66–68 krpm (nominal 68 krpm, cold day,
rotor −65°, NGV throat −5 %, η_c +0.02, flow +5 %, leak 5 %, nozzle +3 %). The earlier count
(62 / 29 / 2) used a viscosity ~18 % too low and two different validity rules; see
`independent-verification.md` §7.

The "rescue" of the combined adverse case by opening the nozzle to Ø69 mm is **not** valid as a simple resize:
the exit would be larger than the retained inlet annulus (the nozzle would no longer converge), and the rescued
point is itself outside the turbine correlation range.

**What would reverse it** (single-parameter boundaries of the model's physical screens at 68 krpm; at most
boundaries the turbine correlation is already out of range):

1. NGV effective throat outside about **700–2500 mm²** (below: NGV within 5 % of choke; above: T04 exceeds
   the screen). Rotor throat outside about **720–2790 mm²**. **Measuring the throats is the single most valuable
   input.**
2. Turbine losses above about **5.8 × Soderberg** (η_tt ≈ 0.51 at that boundary; ×2 gives η_tt 0.75 and
   T04 895 K). Compressor efficiency more than 0.23 below the map; combustor loss above about 27 % at design
   flow function. These wide model margins all assume the throats and angles above.
3. Several adverse factors together (the combined case) with no nozzle change available.
4. A combustor that cannot hold a stable flame at about 1.46 bar and 9.5 kg/h (not modeled).
5. Self-sustain below about 55 krpm, which is **unknown**: the map starts there. Starter cut-out, light-off and
   idle are not established.

These windows show where the model's answer changes; they are not tolerance limits for parts.

## 4. Cash versus the $5,500 target and $6,000 ceiling

All lines are forecast; spend-to-date, commitments and inventory were not supplied. The workbook is reproduced
exactly first ($6,602; independently re-derived from the workbook formulas, read-only).

| Scenario | Total (USD) | vs $5,500 | vs $6,000 |
|---|---:|---:|---:|
| October 2 workbook | 6,602 | +1,102 | +602 |
| **PD-1 nominal** | **6,752** | **+1,252** | **+752** |
| PD-1 adverse (quote risk on flagged lines) | 8,027 | +2,527 | +2,027 |
| Nominal, tax-exempt only (conditional) | 6,302 | +802 | +302 |
| Nominal + tax-exempt + approved campus site + ratiometric sensors (route SV1+SV5+SV4, conditional) | 5,822 | +322 | −178 |
| Route SV1+SV5+SV4+SV2+SV3 (adds tool loans and nozzle nesting, conditional) | 5,487 | −13 | −513 |
| Nominal, every conditional option (SV1–SV6) | 5,422 | −78 | −578 |

**No unconditional scenario fits $6,000.** The smallest set of options that clears the ceiling needs two
confirmations (tax-exempt purchasing and an approved test site) plus a sensor decision.

- Inside the adverse total but not the nominal: assembled-core balancing (+$175), turbine/NGV landed cost
  (+$200, freight +$70; duty and VAT basis undocumented), fuel-pump compatibility (+$70).
- In **no** total: journal grinding (+$100–200 if outsourced), a drawn outer-liner tube if the seam forces it
  (+$60–80), a larger starter battery, and stock rows that do not match the parts (R09 bar too small, BC-01
  without a stock row). SV3's sheet strip is also claimed by the spare nozzle and a spare liner set.

Details: [`manufacturing-and-budget.md`](manufacturing-and-budget.md).

## 5. Tests, failures and unavailable analyses

| Check | Result |
|---|---|
| `python -m pytest -q` | **244 passed** (229 at the start of the verification; baseline before all of this work 163). A fresh virtual environment with only `requirements.txt` also passed (229 at that point) |
| `python scripts/generate_dependencies.py --check` | current |
| `python workspaces/python/check_worksheets.py` | 14 worksheets, 0 problems |
| `python run.py --report-only` | unchanged from baseline (15/16 legacy limits, 35 CAD parameters, 11 evidence blockers); output identical before and after the verification |
| `python run_case.py baseline-250N` | `cda5fff53d3a`; state identical to the previous run (legacy regression intact) |
| `python run_case.py dp2-prescribed` | `d3cc73ced0c7`; DP-2 arithmetic reproduced (T03 348.10 K, P03 163.51 kPa, 23.72 kg/h, 98.1 N); point rejected on the map; blade work coefficient 0.837 |
| `python run_case.py pd1-jm85 --robustness` | `4a7560bfca63`: 39 pass, 3 fail, 13 unknown candidate checks; 0 existing limit failures; CAD read-back validated; 93 robustness points |
| Independent checks (`docs/design/checks/independent/`) | every script exits 0 on the final snapshot: cycle, turbine, map, matching re-solve, nozzle, combustor arithmetic, structures, rotordynamics, stack/CAD, budget, provenance |
| `python docs/design/checks/gas_property_audit.py` | air cp within ±0.2 %; products surrogate 1.2–2.0 % low against frozen NIST-JANAF (documented bias) |

**Failing candidate checks (real, not hidden):**

1. **Outer and inner liner holes against the weld seam:** 2 holes each fall within 3 mm plus their radius of the
   seam. Independent check: unavoidable with these dilution rows on rolled sheet (arc pitch ≈ 9.8 mm against
   ≈ 11.6 mm needed). Remedies: a drawn 4 in × 0.065 in tube for the outer liner, a narrower seam band agreed
   with the shop, or a clocked dilution gap.
2. **Starter peak current:** about 142 A, against 66 A for a 2200 mAh 3S 30C LiPo. This uses the starter bound,
   which is extrapolated below the map (1.2 kW at 30 krpm). Only motoring data can settle the requirement.

**Unknown (not passed), 13:** the NGV hub through-bore; the tunnel/rear-carrier slip joint; both wheel fits;
the shaft end and turbine nut inside the tailcone envelope; the shaft's threaded ends; turbine correlation
validity over the steady range; the five range checks over the steady range (self-sustaining match at every
speed, max T04, min surge margin, NGV and rotor choke fractions — each met at every speed, but only with
extrapolated turbine losses at 56–66 krpm); and self-sustain below the lowest map speed line.

**Rotordynamics:** own FE model, benchmarked against analytic cases and reproduced by an independent
lumped-beam, rigid-rotor and transfer-matrix check, with soft supports assumed at 2 N/µm and 1000 N·s/m.
Crossings: 18,264 rpm and 19,918 rpm (rigid-body modes, damping ratios 0.87 and 0.58, crossed during starting;
they are not resonances) and 88,024 rpm (first bending). Separation from the 56–68 krpm range is **29.4 %**,
against 20 % required; mesh-converged. The margin is conditional: it falls below 20 % above about
**4.0 N/µm** stiffness (3.98 at the assumed damping, 3.86 with none) (at 5 N/µm the second rigid mode is at 49.7 krpm, inside the band) and, at
2 N/µm, above about **2.6 kN·s/m** damping, where the bending crossing drops toward the 77.8 krpm
rigid-bearing limit. **Mount stiffness and damping must be measured.**

**Not run or not available:** ROSS, FEA, CFD; native CAD rebuild; equilibrium chemistry (CEA); any rig or
engine test; the controller exists only against a synthetic plant, with hardware outputs disabled.

## 6. Next five team actions (specific inputs)

1. **Measure or obtain the turbine and NGV flow geometry.** NGV85 and TW85 throat areas (pin gauge at hub, mid
   and tip on every passage), vane and blade counts, rotation direction; or ask JETMAX for throat area, design
   point and stage efficiency. Enter `throat_area` (basis `supplied`, with source) in
   `data/components/ngv_jetmax_ngv85.yaml` and the rotor equivalent in `turbine_jetmax_tw85.yaml`. Rerun, and
   pick the nozzle from the trim table. *Owner: Turbomachinery.*
2. **Decide the NGV hub / rear-bearing path.** Bore the web and keep the pocket as the carrier seat, remove the
   web, use a separate rear housing, or flange the carrier to the machined web; then a machining plan and a
   strength/stiffness check, and the assembly order that follows. *Owner: Structures with Turbomachinery.*
3. **Fix the compressor wheel identity and the fits.** Choose the stock Garrett 452708-0001 (matches the map)
   or the billet 11+0 (needs its own characteristic). Measure both wheel bores; approve the fits and the
   turbine's assembly method. *Owner: Turbomachinery + Structures.*
4. **Close the budget confirmations:** tax-exempt purchasing status (SV1), an approved campus test site with
   containment (SV5), sensor choice (SV4), spend-to-date and inventory, quotes for R02/R03 (landed), R04,
   S03/S04, F01 and journal grinding, and corrected stock rows. *Owner: Chief engineer.*
5. **Liner route, combustor model and bearing mounts:**
   - the shop's minimum seam band, or a drawn 4 in × 0.065 in 316 outer-liner tube; then rerun the layout;
   - the combustor owner to revisit the uniform-liner-static loss model (≈ 5 % vs the 2.5 % basis) and the
     dilution-penetration definitions; plan a cold-flow split/pressure-drop test and a first-light test;
   - bearing supplier speed and preload; O-ring mount stiffness **and damping** on a simple rig (targets
     < 3.9 N/µm, < 2.6 kN·s/m); a motoring-test plan for the starter.

   *Owner: Combustion & Systems, Structures, with the shop.*

**Decisions that are the team's:**

- the NGV hub / rear-bearing path and the assembly order that follows
- the validity rule: keep "outside the model's range → unresolved, never feasible" (applied now) or count such
  points as failures; and whether the unsourced Re ≥ 2e4 flag stays
- compressor wheel identity; budget confirmations; liner fabrication route
- model conventions left unchanged: the legacy M10 power-input factor (moves the baseline), nozzle Cd × Cv,
  the combustor's viscosity law, liner static model and penetration definitions
- combustor architecture naming (front-dome annular, not folded); 68 krpm maximum continuous speed; nozzle trim
  set (Ø50/54/58); balancing route; whether thrust measurement is deferred (SV6); TW85/NGV85 primary versus
  TW70/NGV70 fallback, once the throats are known

## Run commands (repository root, Python 3.13)

```
python -m pytest -q                                   # ~2-4 min
python run_case.py pd1-jm85 --robustness              # ~20 min; candidate match, pipeline, CAD, BOM, robustness
python run_case.py dp2-prescribed                     # seconds
python run_case.py baseline-250N                      # seconds
python scripts/make_design_snapshot.py                # refuses failed, stale or incomplete runs; writes results/*/SUMMARY.md
python scripts/generate_dependencies.py --check
python workspaces/python/check_worksheets.py
python run.py --report-only
python docs/design/checks/gas_property_audit.py
python docs/design/checks/independent/<area>/<script>.py   # independent re-checks (README there)
```

## Artifacts

| What | Where |
|---|---|
| Independent verification (claim by claim) and its scripts/outputs | `docs/design/independent-verification.md`, `docs/design/checks/independent/` |
| Design basis, component reviews, interfaces, manufacturing and budget, verification, remaining work | `docs/design/*.md` |
| Generated tables per case (authoritative numbers) | `docs/design/results/<case>/SUMMARY.md` |
| Candidate data: station table, pressure ledger, power ledger, operating line, checks, assumptions register, seed provenance | `docs/design/results/pd1-jm85/` |
| CAD bundle and parameter CSV | `docs/design/results/pd1-jm85/cad/` |
| Figures: cross-section, map with operating line, Campbell, unbalance, operating line, robustness tornado | `docs/design/results/pd1-jm85/figures/` |
| BOM and cost summary | `docs/design/results/pd1-jm85/bom/` |
| Fuel, starter and electrical budgets | `docs/design/results/pd1-jm85/systems/` |
| Full run folders with manifests and fingerprints | `out/<case>/<fingerprint12>/`, `out/<case>/LATEST.json` |
| Versioned component, map, budget, systems and interface data | `data/` |
| Progress log and resume point | `docs/design/PROGRESS.md` |

## Continuation note

Start from `docs/design/PROGRESS.md`, `remaining-work.md` and `independent-verification.md`.

- Any edit under `core/`, `modules/`, `config/`, `data/` or the run scripts changes the design fingerprint of all
  three cases. Rerun them before snapshotting; the snapshot script refuses stale or incomplete runs.
- To bring in a measured throat, edit only the component record (basis `supplied` with a source) and rerun.
  The nozzle trim table in the new run then gives the matching nozzle.
- Do not change `config/limits.yaml` or mark evidence reviewed without the team.
- On Windows/OneDrive, the run-folder commit retries the rename and falls back to a copy if a file handle is
  held.
