# Handoff: independently verify the PD-1 engine design and codebase

You are picking up an engineering review that was cut off mid-task. Your job is to **verify the PD-1
turbojet preliminary design and the code that produces it**. Clear every claim the evidence supports, correct
what is wrong, and leave honestly open what cannot be settled.

"Exonerate" here means *establish with evidence that a claim or a piece of code is correct*. It does not mean
"approve". A claim you cannot check stays open, with the reason and the input that would settle it.

Treat everything below as a lead, not a fact. That includes this handoff, the two earlier agents' reports, and
every number in `docs/design/`. Facts marked **[verified at handoff]** were checked on 2026-10-04 at about
14:10 local time. Everything else must be checked by you.

---

## 1. Hard rules (inherited from the original task; do not relax them)

- Work only in `C:\Users\andyc\OneDrive\Desktop\CORE\github-core`, on the local branch
  `feat/preliminary-design-integration` (base commit `98c4167` on `main`). Keep all work local.
- Do **not** purchase, contact suppliers, publish (no artifacts, no pushes, no uploads), control hardware,
  release anything for manufacture, or record approvals or reviews that did not happen.
- **Do not commit** unless the user asks. If they do, author attribution is *atciamb only*: no
  `Co-Authored-By` or Claude attribution lines.
- Preserve the user's own work untouched: the modification to `README.md`, everything in
  `docs/overnight-handoff/`, and `docs/preliminary-design-roadmap.md`.
- Do not change `config/limits.yaml`, and do not mark evidence reviewed in `config/readiness.yaml`.
- Read the budget workbook read-only:
  `C:\Users\andyc\OneDrive\Desktop\CORE\outputs\core-budget-20261002-fbef9859\CORE_Itemized_Budget.xlsx`.
- Missing data is not zero. An unknown check is not a pass. Never invent maps, quotes, test results or
  supplier data.
- Never weaken a check, a limit or a test to make something pass. If a check is wrong, fix its logic, add a
  regression test and explain the change.
- Keep the line between *preliminary calculation* and *demonstrated operation* explicit in everything you
  write.
- Do not infer a deadline. Work until the plan below is done or you are blocked on a decision that belongs to
  the user.

## 2. Where things are

| What | Where |
|---|---|
| Original task and acceptance criteria | `docs/overnight-handoff/00-START-HERE.md` … `04-OUTPUT-CONTRACTS.md` (read all five first) |
| Design reports | `docs/design/`: `MORNING_REPORT.md`, `design-basis.md`, `component-reviews.md`, `interfaces.md`, `manufacturing-and-budget.md`, `verification.md`, `remaining-work.md`, `limits-and-correlations-audit.md`, `PROGRESS.md` |
| Snapshotted run outputs (authoritative tables in `SUMMARY.md`) | `docs/design/results/<case>/` for `pd1-jm85`, `dp2-prescribed`, `baseline-250N` |
| Full run folders | `out/<case>/<fingerprint12>/`, with `out/<case>/LATEST.json` pointing at the newest |
| Case definitions | `config/cases/*.yaml` |
| Versioned component, map, budget, systems and interface data | `data/` |
| New calculation code | `core/`: `engine_match`, `turbine_rating`, `compressor_map`, `candidate`, `assembly`, `rotor_fe`, `postprocess`, `robustness`, `budget`, `exports`, `cad_export`, `figures`, `systems`, `controls_sim`, `cases`, `records`, `diffuser` |
| Pipeline modules | `modules/` (new `m29_layout.py`; modified m01, m10–m13, m20, m30, m32, m34, m40) |
| Case runner | `run_case.py` |
| Snapshot tool | `scripts/make_design_snapshot.py` |
| New tests | `tests/test_design_records.py`, `test_design_physics.py`, `test_design_mechanics.py` |
| Supplier drawings (downloaded by the reviewer; not in the repo) | `C:\Users\andyc\OneDrive\Desktop\CORE\tmp\pdfs\pd1-audit\` (`tw85.pdf/.png`, `ngv85.pdf/.png`); source URLs are in `data/components/*jetmax*.yaml` |
| Pre-change baseline logs | `docs/design/baseline/` (163 tests passed before this work) |

**PD-1 in one paragraph.** A GT3076R-class 76 mm compressor wheel (56 trim), rated on a digitized Garrett
GT3076R map used as a *related-wheel proxy*, feeds a CORE vaned diffuser (19 vanes, Ø126 mm exit). That feeds
a front-dome annular combustor with 8 J-vaporizers in a 152.4 mm casing. The turbine is a purchased JETMAX TW85
finished wheel with a JETMAX NGV85 casting finished by CORE, followed by a Ø54 mm conical nozzle. It uses
10 × 26 × 8 hybrid bearings on assumed soft O-ring mounts. The steady range is 56–68 krpm, with the design
point at 68 krpm. The operating point is **solved** by fixed-geometry matching with zero starter torque
(`core/engine_match.py`), not imposed. The NGV throat and exit angle (65°) and the rotor exit angle (−58°) are
**assumptions**.

## 3. What has happened so far

1. **Author agent** (the overnight pass). It built the framework above and produced the report set.
   Its final runs were `out/pd1-jm85/af33609c34b6`, `out/dp2-prescribed/5e76b39e58df` and
   `out/baseline-250N/fba44cd60269`.
2. **Reviewer agent.** It audited the author's work, made fixes, and was cut off twice by usage limits. It
   reported these findings and fixes (all **unverified** until you check them):

| # | Reviewer finding | Reported fix | Where to look |
|---|---|---|---|
| R1 | numpy, scipy and matplotlib missing from `requirements.txt` | added | `requirements.txt` |
| R2 | Two shaft-fit checks were one-sided and could pass incompatible dimensions: "turbine seat equals journal" (9.99 mm bore over a 10 mm journal) and "compressor seat diameter vs bore" (5.99 mm bore) | replaced by `unknown` checks "turbine bore / journal assembly fit" and "compressor bore / seat finished fit" | `core/assembly.py` (≈ l.265–280); `test_nominal_wheel_interference_is_not_a_validated_fit` |
| R3 | Turbine outlet state missed the energy balance by ≈ 2.2 kJ/kg at the design point | work debit applied at a fixed passage static pressure; mass, energy and Euler now close | `core/turbine_rating.py` (≈ l.250–320); `test_penalised_turbine_exit_closes_mass_energy_and_euler` |
| R4 | The starter/battery failure appeared in `manifest.json` but not in `candidate_checks.json` | added to the checks file | `run_case.py` |
| R5 | Invalid model conditions could be labeled "feasible" | turbine validity flags now count as a robustness failure and fail a new candidate check, "turbine correlation validity over steady range" | `core/robustness.py` ≈ l.40–55; `run_case.py` ≈ l.258–264; flags in `turbine_rating.py` ≈ l.292–303 |
| R6 | Sign of the axial thermal growth was reversed | fixed | `core/assembly.py: axial_growth`; `test_shaft_expansion_opens_axial_gap_when_stationary_ngv_does_not_expand` |
| R7 | Pressure thrust should use the geometric exit area (mass flow uses Cd·A) | fixed | `core/engine_match.py` ≈ l.176, `modules/m40_nozzle.py`; `test_fixed_nozzle_pressure_thrust_uses_geometric_exit_area` |
| R8 | M12 (NGV module) was not reading the same rated state as the engine match | now reads the imported/rated point | `modules/m12_ngv.py` (`cycle_imported_point_flag`) |
| R9 | Supplier drawings confirm the main TW85 dimensions and cited prices. **But the NGV85 blank's Ø48 hub pocket is blind, with a central web**, so it is not an open passage for the shaft and rear bearing carrier | through-bore marked unresolved in the CAD bundle; check changed to `unknown` "NGV hub through-bore for rear carrier" | `core/assembly.py` ≈ l.244–264; `test_ngv_blind_hub_pocket_is_not_reported_as_finished_through_bore` |
| R10 | The snapshot validator tried to hash `manifest.json` against itself, so it rejected every snapshot | manifest excluded from its own hash check | `scripts/make_design_snapshot.py` ≈ l.119–136 |
| R11 | Controller starter-release timing | changed in the synthetic controller | `core/controls_sim.py`; `test_controller_releases_starter_in_transition_step`, `test_synthetic_normal_start_reaches_run_with_starter_released` |

   Between 13:13 and 13:25 the reviewer also edited files its chat does not describe:
   - `core/readiness.py` (see §4)
   - `core/candidate.py`, `core/diffuser.py`, `core/exports.py`, `core/cases.py`
   - `modules/m11_diffuser.py`, `modules/m30_shaft.py`
   - `config/cases/pd1-jm85.yaml`, `config/variables.yaml`
   - `data/budget/pd1_adjustments.yaml`, `data/components/assembly_pd1.yaml`,
     `data/components/ngv_jetmax_ngv85.yaml`
   - `tests/test_design_physics.py`, `tests/test_design_records.py`

   Most new files are **untracked**, so git has no "before" version. To see what the reviewer changed, compare
   the *outputs*: `out/pd1-jm85/af33609c34b6/` (pre-review) against `out/pd1-jm85/cf53eecfed2f/` (the
   reviewer's last run), plus `c78db791990f` (an intermediate run). Each manifest lists its design files.
3. **The reviewer was cut off** right after changing the NGV hub-passage check (R9) at 13:59. That was
   *after* its final case run (13:49) and snapshot (13:50).

## 4. State at handoff

- **[verified at handoff]** No Python process was running, so no other session was editing the tree.
  `core/assembly.py` and `tests/test_design_mechanics.py` compile.
- **[verified at handoff]** `python -m pytest -q` gave **229 passed** in 146 s, and
  `python scripts/generate_dependencies.py --check` reported the doc as current.
- **[verified at handoff]** **All three snapshots are stale.** The code changed after the last runs:

| Case | Snapshot / LATEST fingerprint | Current design fingerprint |
|---|---|---|
| pd1-jm85 | `cf53eecfed2f` | `64f67d87ca0b` |
| dp2-prescribed | `bcaa0d59c831` | `9c6dd70a809e` |
| baseline-250N | `9f22df80bbc0` | `46f157f3d24c` |

- **[verified at handoff]** The reviewer's snapshot (`cf53eecfed2f`) reports:
  - candidate checks: 45 pass, 4 fail, 3 unknown
    - fail: outer liner seam, inner liner seam, turbine correlation validity (Re < 2e4 at 56 and 58 krpm),
      starter current 142 A against 66 A
    - unknown: turbine bore/journal fit, compressor bore/seat fit, self-sustain below the map
  - robustness: 93 points; 62 feasible, 29 fails, 2 unresolved
    - 27 of the 29 failures are turbine-validity failures at 56 krpm
    - the other 2 are the combined-adverse case at 66 and 68 krpm (T04 ≈ 1312–1313 K)
  - CAD bundle: 182 parameters (148 provisional, 19 fixed purchased, 13 envelope only, 5 unresolved)
- **Known contradictions in `docs/design/MORNING_REPORT.md`** (the reviewer edited it at 13:58):
  - "Run status: current and internally consistent" — false now (see the table above).
  - "228 tests passing" — the suite is now 229.
  - The *Outcome strength* paragraph still says there is margin "in every single-parameter perturbation
    evaluated". That is true for the T04 screen alone, but it hides the 27 validity failures and the failing
    validity check. Feasibility at the low end of the steady range (56–58 krpm) currently rests on a turbine
    loss correlation outside its Reynolds-number range.
  - Check `PROGRESS.md`, `verification.md`, `design-basis.md` and `component-reviews.md` (all edited
    13:55–13:56) for the same drift.
- **`core/readiness.py` change.** The legacy `design_fingerprint` now also hashes everything under `data/` and
  `run_case.py`. This is existing user tooling. Find out whether it changes `python run.py --report-only`
  (baseline: 15/16 limits, 35 CAD parameters, 11 evidence blockers). Also find out whether it silently
  invalidates or validates any reviewed evidence recorded against the old fingerprint. Report what you find
  either way, and do not "fix" evidence status yourself.

## 5. How to work in this environment

- Windows 11, with Git Bash and PowerShell. Python 3.13.2: numpy 2.3.1, scipy 1.17.1, matplotlib 3.10.8,
  PyYAML 6.0.3, pytest 9.0.3. No ROSS, FEA, CFD, CAD application or CEA.
- The repository sits in **OneDrive**, so expect transient file locks.
  - `RunFolder.commit` already retries the rename and falls back to a copy.
  - The existing test `tests/learning/test_platform.py::test_corrupt_and_interrupted_save_recovers_latest_history`
    can fail under heavy CPU load with a real Windows `PermissionError`. Re-run it alone before calling it a
    regression.
- **Memory is tight.** The machine has 16 GB with about 3 GB free.
  - Claude Code kills background shells when memory is critically low *and the session is idle*.
  - `python run_case.py pd1-jm85 --robustness` takes about 12 minutes, longer than the 10-minute foreground
    limit. Run it in the background and keep the session active with light reading meanwhile.
  - Run one heavy job at a time.
  - The user can disable the reaping by starting Claude Code with
    `CLAUDE_CODE_DISABLE_BG_SHELL_PRESSURE_REAP=1`.
  - The full test suite takes about 2.5 minutes.
- **Every edit** under `core/`, `modules/`, `config/`, `data/`, or to `run.py`, `run_case.py` or
  `requirements.txt` changes the fingerprint of **all three** cases.
  - Batch your fixes, then rerun all three cases, then snapshot.
  - `scripts/make_design_snapshot.py` refuses stale runs, but it **deletes and rewrites**
    `docs/design/results/<case>/` when the run is current. Only run it after a deliberate rerun.
- `docs/` is not fingerprinted, so editing reports does not stale runs.

## 6. Plan

### Phase 0: orient and protect (no design edits yet)

1. Read the five files in `docs/overnight-handoff/`, then `docs/design/MORNING_REPORT.md`, `PROGRESS.md`,
   `verification.md` and `remaining-work.md`.
2. Run `git status --short` and the staleness check below, and confirm the §4 facts still hold. If anything
   changed after 2026-10-04 14:10, find out what before you continue.
3. Make a local safety copy of the working tree, excluding `out/`, outside the repository, for example a
   timestamped tar in `C:\Users\andyc\OneDrive\Desktop\CORE\tmp\backups\`. Most of this work is untracked and
   has no history. Do not commit.
4. Run the baseline commands and record the results:

   ```
   python -m pytest -q
   python scripts/generate_dependencies.py --check
   python workspaces/python/check_worksheets.py
   python run.py --report-only
   ```

   Staleness check (no side effects):

   ```
   python -c "import json;from pathlib import Path;from core import cases as C
   for c in ('pd1-jm85','dp2-prescribed','baseline-250N'):
       i=json.loads(Path(f'out/{c}/LATEST.json').read_text());m=json.loads((Path('out')/i['run_dir']/'manifest.json').read_text())
       k=C.load_case(c);print(c,i['fingerprint'][:12],C.case_fingerprint(k,C.case_records(k),extra=m.get('run_options'))[:12])"
   ```

### Phase 1: re-verify each reviewer fix (R1–R11 and the readiness change)

For each item: read the code, read the regression test, and confirm the test would have failed on the old
logic. Then check the result **independently**, by hand or with a short script that does not import the code
under test. Record a verdict: *verified*, *corrected* (with what you changed) or *open* (with what is needed).

- **R1.** Grep every third-party import in `core/`, `modules/`, `scripts/`, `run*.py` and `tests/`, and
  confirm each one is in `requirements.txt`. If memory allows, create a clean virtual environment in a temp
  folder, `pip install -r requirements.txt`, and run the suite there.
- **R2 and R9 (fits and assembly path).**
  - Confirm no document, interface or CAD-bundle entry still presents these fits or the NGV hub passage as
    settled. Look at `interfaces.md` (IF-CW-SH, IF-SH-TR, IF-BC2-NG), `component-reviews.md`, and the
    assembly order in `manufacturing-and-budget.md` §2 ("insert the shaft assembly from the rear … rear
    carrier seats in the NGV hub bore Ø48").
  - Compare the NGV85 and TW85 dimensions in `data/components/` against the drawings in
    `tmp/pdfs/pd1-audit/`.
  - The blind pocket with a central web undermines the rear-bearing support path and the insertion sequence.
    Describe the design options (bore through the web and retain a support ring, a separate rear bearing
    housing, and so on) as **team decisions**. Do not pick one silently.
- **R3.** From `design_point.json` (and `station_table.csv`), recompute at the design point:
  - h01 − h02 against the reported work
  - Euler work U·(Cθ1 − Cθ2) at the mean radius
  - exit continuity ṁ = ρ·Cx·A
  - η_tt
  - T05 from the energy balance

  Use the repository gas model only for properties. State the residuals.
- **R4 and R5 (classification consistency).**
  - Confirm the manifest's failed and unknown lists equal the non-pass entries of `candidate_checks.json` and
    the `SUMMARY.md` tables.
  - Assess the taxonomy: outside the map → *unresolved*, but turbine correlation outside its Re range →
    *fails*.
  - Recommend and document one consistent rule. A model-validity exceedance arguably means "the model cannot
    tell" (unknown or unresolved), not "the engine fails". But do not quietly relabel it to make results look
    better, and do not change it without explaining the effect on every headline claim.
  - Report the actual Re values at 56–68 krpm against the 2e4 bound, and say what the bound is based on.
- **R6.** Sketch the axial load paths: front bearing locates the rotor; NGV via the casing rear cover and/or
  the rear carrier spigot. Hand-compute the NGV-TE-to-rotor-LE gap change from the stated temperatures and
  expansion coefficients. Confirm the sign *and* that the reference path for the NGV matches the stack
  (`core/assembly.py: build_stack`, IF-NG-CS2, IF-BC2-NG).
- **R7.** Confirm that thrust = ṁ·V8 + A8,geom·(P8 − P0), with mass flow through Cd·A8, in both
  `engine_match` and M40, and that the two agree. At the design point the nozzle is unchoked (NPR ≈ 1.10), so
  pressure thrust should be about zero; confirm.
- **R8.** Confirm M12's outputs equal the turbine block of `design_point.json` for the same state.
- **R10.** Confirm that the snapshot tool hashes every kept output except the manifest, and that it rejects a
  tampered output. Try this on a **copy** of a run folder, not the real one.
- **R11.** Read the controller state machine and confirm the starter release, the abort paths, and that
  `HardwareOutputs` stays disabled.
- **`core/readiness.py`.** See §4.

### Phase 2: independent audit of what nobody has checked yet

Reproduce each headline number independently, by hand or with a minimal script, and flag any disagreement
above about 1 %.

- **Cycle.**
  - Compressor power ṁ·Δh0 against the reported value.
  - Turbine power, and the shaft balance with bearing and windage losses.
  - Combustor FAR against fuel flow, LHV and combustion efficiency.
  - T04 from the energy balance, and the T04/T41 mixing with tunnel leak re-entry.
  - The pressure ledger, with each loss counted exactly once.
- **Compressor map.**
  - Corrected flow and speed directions and reference conditions (545 °R, 28.4 inHg).
  - The β-line interpolation, and no extrapolation in speed or β.
  - Reproduce from `data/maps/gt3076r_compressor_digitized.csv` the claim that the DP-2 point (0.30 kg/s,
    PR 1.63 at 66 krpm) is not on the map.
- **Turbine mean line.**
  - Velocity triangles; U at the mean radius; ψ (≈ 0.73), φ (≈ 0.51), reaction.
  - The Soderberg coefficient with aspect and Re corrections, and tip leakage.
  - Judge whether η_tt ≈ 0.84 is plausible for an 85 mm model-turbine stage at Re of about 2e4. Say clearly
    if it looks optimistic.
- **Matching.**
  - Residual definitions; uniqueness, using multi-start from distant guesses.
  - Trends: a smaller nozzle should give higher T04 and lower β.
  - Repeat the throat-area feasibility window and the nozzle trim table at two or three points by
    independent re-solve.
- **Combustor.** The 2.5 % loss / 1.4 ms basis, hole-area sums, the dilution penetration screen, and the
  seam-check geometry and its two failures.
- **Nozzle.** V8 with Cv, mass flow with Cd, and the half-angle.
- **Rotordynamics.**
  - Check the rigid-body modes with an independent 2-DOF rigid rotor on two springs: mass and inertias from
    `rotordynamics.json` and `cad_bundle.json` (ROTOR mass ≈ 0.417 kg), with the stated span and k.
  - Check the first bending mode with a simple beam estimate.
  - Confirm the separation margin and the support-stiffness sensitivity (the claim that stiffness must stay
    below about 3–5 N/µm).
- **Structures.**
  - Shaft torsion τ = 16T/(πd³). For example, T ≈ 1.29 N·m on the 6 mm seat should give ≈ 30.5 MPa
    nominal.
  - Kt assumptions, tip-clearance thermal and centrifugal growth, liner buckling, casing hoop stress.
- **Assembly stack and CAD.**
  - Station x positions, part overlaps, the cross-section figure against the stack.
  - Bundle units and types, no values on unresolved parameters, and every "supplied" value traced to a
    document.
- **Budget.**
  - Reproduce $6,602 from the workbook, read-only, including its formulas: tax 8 % on direct excluding travel
    plus freight, reserve 10 % of direct, both rounded up to $25.
  - Then the PD-1 adjustments, the nominal $6,752, the adverse $8,027, and the computed savings routes. Every
    saving must stay *unconfirmed*.
- **Provenance.** Spot-check `seed_provenance.json` and `assumptions_register.json`. Every number tagged
  "supplied" needs a source, and every assumption must be visible in the reports.

### Phase 3: fix, rerun, snapshot, reconcile

1. For each confirmed defect, make the smallest fix and add a regression test that fails without it.
2. Run the full test suite, then rerun **all three** cases, one at a time:

   ```
   python run_case.py pd1-jm85 --robustness     # ~12 min; background, keep the session active
   python run_case.py dp2-prescribed
   python run_case.py baseline-250N
   python scripts/make_design_snapshot.py
   ```

3. Reconcile every number and claim in `docs/design/*.md` against the new `SUMMARY.md` files. That includes
   the run status, test counts, check counts, robustness counts, CAD status counts, the outcome statement, the
   cost table and the "what would reverse it" list. If a report and `SUMMARY.md` disagree, the report is
   wrong.
4. Rerun the Phase 0 commands and confirm that nothing regressed and the legacy report is unchanged, or that
   any change is explained.

### Phase 4: deliverables

1. **`docs/design/independent-verification.md`**, containing:
   - one row per claim or finding: R1–R11, the readiness change, each Phase 2 item, and each headline number
     in `MORNING_REPORT.md`
   - for each row: method, independent result, repository result, difference, and a verdict (verified,
     corrected or open)
   - for open rows: the specific measurement, analysis or supplier answer that would close it
2. Updated `MORNING_REPORT.md`, `verification.md`, `PROGRESS.md` and `remaining-work.md` that match the final
   snapshots exactly.
3. A final chat answer containing:
   - a one-paragraph verdict
   - a list of defects found and fixed, each with its regression test
   - the claims you could not clear and why
   - exact commands, results and fingerprints
   - the decisions that belong to the team, including the NGV hub/rear-bearing path, the validity-failure
     taxonomy, the wheel identity, the budget confirmations and the liner fabrication route

The verdict must be scoped honestly. "Verified" can apply only to things you actually reproduced. The design
remains a preliminary calculation, conditional on assumed turbine/NGV throats and angles, a proxy compressor
map, an unmodeled combustor, and an unknown low-speed and starting region.
