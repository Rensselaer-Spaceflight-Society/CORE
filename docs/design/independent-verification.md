# Independent verification of the PD-1 design and code

PRELIMINARY - NOT FOR MANUFACTURE. Verification pass of 2026-10-04 (afternoon), following
[`REVIEW-HANDOFF.md`](REVIEW-HANDOFF.md). Branch `feat/preliminary-design-integration` on base `98c4167`; nothing
committed, pushed, purchased, sent or published; `README.md`, `docs/overnight-handoff/` and
`docs/preliminary-design-roadmap.md` untouched; `config/limits.yaml` and `config/readiness.yaml` unchanged; the
budget workbook was only read (SHA-256 `46364aee…`, unchanged before and after).

**What the verdicts mean.** *Verified*: this pass reproduced the number or the logic itself — by hand, by a
script that does not import the code under test, or by reading the code against an independent reference.
*Corrected*: a defect was found, fixed with the smallest change and pinned by a regression test that fails on
the old logic. *Open*: it cannot be settled here; the row names the measurement, analysis or supplier answer
that would settle it. Reproducing the model's arithmetic is **not** evidence that the engine works. Every
engineering result here is a preliminary calculation, conditional on assumed turbine/NGV throats and angles, a
proxy compressor map, an unmodelled combustor and an unknown low-speed/starting region.

**Final runs and snapshots** (all current; the snapshot tool refused nothing):

| Case | Run / snapshot | Notes |
|---|---|---|
| `pd1-jm85` | `4a7560bfca63` (with robustness; 1161 s) | 39 pass / 3 fail / 13 unknown candidate checks; robustness 10 feasible / 2 fail / 81 unresolved |
| `dp2-prescribed` | `d3cc73ced0c7` | limits unchanged; 13 impeller-exit/diffuser state values changed by the blade-work fix (F5) |
| `baseline-250N` | `cda5fff53d3a` | state identical to the previous run (legacy regression intact) |

Independent scripts and their saved outputs (`*.out`, all exit 0 on the final snapshot):
[`checks/independent/`](checks/independent/README.md). Forked sub-reviews did the first recomputations on run
`cf53eecfed2f`; every number below was re-run on the final snapshot by the script named in the row.

## 1. Verdict

The arithmetic holds. Independent re-implementations reproduce the cycle, the turbine mean line, the compressor
map interpolation, the fixed-geometry match (design point, 56 krpm and three trim points, to 1e-6), the nozzle,
the combustor sizing arithmetic, the structures screens, the rotordynamics (to 0.05 %), the assembly stack (33
stations, exact) and the budget (to the dollar). The reviewer's eleven findings were real and its fixes worked,
but two were incomplete (R2, R9) and one introduced an inconsistent rule (R5). This pass found and fixed fifteen
further defects, each with a regression test; the ones that change conclusions are a turbine viscosity 18 % too
low (the turbine loss correlation is now out of range at 56–66 krpm), threshold labels and a solver miss near
choke (the feasibility windows were wrong), and a DP-2 work coefficient computed with the power-input factor
inverted. Re-run with one validity rule, PD-1 is **conditionally feasible at the 68 krpm design point and
unresolved below it**; the rotordynamic margin depends on unmeasured mount stiffness **and** damping; the
rear-bearing path through the blind NGV hub and the assembly order are not established; two combustor screens
pass only on modelling approximations; the predicted turbine efficiency (0.85) is probably optimistic. Nothing
here shows that the engine will self-sustain.

## 2. Starting state (Phase 0, 14:46–14:58)

| Fact | Result |
|---|---|
| Changes after the handoff time (14:10) | only `REVIEW-HANDOFF.md` and a `run.py --report-only` output at 14:12; no Python process running |
| `python -m pytest -q` | 229 passed in 151 s |
| `generate_dependencies.py --check`; worksheets | current; 14 checked, 0 problems |
| `run.py --report-only` | 15/16 limits (critical-speed separation 0.1003 fails), 35 CAD parameters, 11 evidence blockers |
| Staleness | all three runs stale: pd1 `cf53eecfed2f` vs current `64f67d87ca0b`, dp2 `bcaa0d59c831` vs `9c6dd70a809e`, baseline `9f22df80bbc0` vs `46f157f3d24c`; the only design file that differed from the run manifests was `core/assembly.py` (the 13:59 R9 edit) |
| Safety copy | `..\tmp\backups\github-core-worktree-20261004-144736.tar.gz` (all 146 modified/untracked files; `out/` excluded). Some `.git` files are OneDrive cloud-only placeholders that could not be read ("cloud file provider exited unexpectedly"), so `git log` fails; `git status/diff/show` work |

## 3. The reviewer's findings R1–R11 and the readiness change

Each row: what the reviewer claimed, how it was re-checked, what the independent check found, the verdict.
"Test fails on old logic" was confirmed by reading the test against the pre-fix outputs (`out/pd1-jm85/af33609c34b6`)
or, where the old code no longer exists (untracked files), against the behaviour it pins.

| ID | Reviewer claim | Independent method | Independent result | Repository (final) | Verdict | Evidence / what would close it |
|---|---|---|---|---|---|---|
| R1 | numpy, scipy, matplotlib missing from `requirements.txt`; added | Every import in `core/ modules/ scripts/ tests/ run*.py workspaces/ docs/`; fresh venv with only `pip install -r requirements.txt` (numpy 2.5.3, scipy 1.18.1, matplotlib 3.11.2, pytest 9.1.1, PyYAML 6.0.3), then the full suite | Third-party imports are exactly numpy, scipy, matplotlib, PyYAML, pytest; clean venv **229 passed** | 5 entries | **verified** | Versions are lower bounds only (not pinned) |
| R2 | Two one-sided fit checks passed incompatible sizes; replaced by `unknown` | Pre-review run `af33609c34b6`: "turbine seat equals journal" passed 10.00 mm vs a 9.99 mm bore, "compressor seat diameter vs bore" passed 6.00 vs 6.00 for a 5.99 mm bore. Supplier drawing: TW85 bore Ø9.99 ±0.005 | Old checks were wrong; nominal 5–15 µm interference on a 10.000 mm seat; the compressor seat is an envelope | both fit checks `unknown`, value −0.010 mm | **verified; corrected** — the bores were hard-coded (9.99/5.99) in `core/assembly.py`; now read from the wheel records, and the reason text no longer says the wheel must "pass a journal" (it goes onto its seat from the rear) | `test_nominal_wheel_interference_is_not_a_validated_fit` (fails on the old names/logic); new `test_fit_checks_follow_the_purchased_wheel_bores`. Interfaces, component reviews and the CAD bundle no longer call either fit settled. To close: measured bores, approved fits, assembly method, hub stress |
| R3 | Turbine exit missed the energy balance by ≈ 2.2 kJ/kg; work debit now applied at fixed passage static pressure | Own enthalpy balance and own re-rating with `core.gas` properties only (`cycle_turbine/r3_turbine_check.py`), on the final snapshot and on `af33609c34b6` | Pre-fix: exit state short by **−2,222.3 J/kg = w_Euler − w** (T05 debited, static state and P05 not). Final: h01 − h05 = w = 45,465.25 J/kg (residual 0.0000), Euler at the mixed plane exact, continuity 0.203549 kg/s at NGV, passage and mixed plane, η_tt 0.846, T05 797.587 K | same to < 1e-6 % | **verified** | `test_penalised_turbine_exit_closes_mass_energy_and_euler` (fails on old logic: no mixed-out exit). Note: the fix itself raised η_tt by ≈ 0.007 at the design point |
| R4 | Starter/battery failure was in the manifest but not in `candidate_checks.json` | Compare manifest failed/unknown lists with the checks file, `SUMMARY.md` and `design_readiness.json` | `af33609c34b6`: manifest 3 fails, file 2 (starter missing) — confirmed. `c78db791990f`, `cf53eecfed2f` and the final run: all four agree | equal | **verified** | No dedicated test (ordering in `run_case.main`); the snapshot tool now also refuses runs whose listed outputs are missing |
| R5 | Invalid model conditions could be labelled feasible; turbine validity flags now fail robustness and a candidate check | Pre/post robustness counts; code reading; Re recomputed with an independent viscosity (Sutherland, within 2 % of tabulated air) | Confirmed: pre-review 89 of 93 points "feasible" including 27 with the turbine correlation out of range. But (a) the fix made the taxonomy inconsistent (map domain → unresolved; Re range → fails) and left range checks passing on flagged points; (b) the Re values used a viscosity **18–21 % too low**; (c) the 2e4 bound has **no source** (Soderberg's basis is Re 1e5) | flags at 56–66 krpm; 68 krpm rotor Re 20,024 | **corrected** (viscosity; one validity rule — §7) — the rule is a **team decision** | `test_turbine_viscosity_matches_tabulated_air`, `test_model_validity_is_unresolved_not_failed_and_never_feasible`, `test_range_checks_do_not_pass_on_extrapolated_points`. Rotor Re over 56–68 krpm: 15,555 (56 krpm), 16,354, 17,129, 17,881, 18,613, 19,326 (66 krpm), 20,024 (68 krpm). To close: stage efficiency data at Re ≈ 2e4 |
| R6 | Sign of the axial thermal growth was reversed | Hand calculation from the stack and stated temperatures (`phase1/axial_growth_check.py`). Load path: the front bearing locates the rotor; the NGV is located by the casing → rear cover → NGV flange front face, and its vane trailing edge sits one gap ahead of that face in the hot casting | Shaft (12.3e-6/K, ΔT 125.3 K over 133.5 mm) moves the rotor aft 206 µm; casing (18e-6/K, ΔT 60.4 K) moves the NGV aft 151 µm: the gap **opens** +54 µm (pre-review run: closed 53 µm — wrong sign). The stack-faithful path (rotor LE, cover, hot NGV return, aluminium backplate) gives +78 µm | +54 µm | **verified** (sign); approximation noted | `test_shaft_expansion_opens_axial_gap_when_stationary_ngv_does_not_expand` (fails on old sign). Rear-bearing float is 24 µm in the code, ≈ 123 µm if the carrier is held at the NGV and grows forward — still < 0.5 mm, but the carrier path is open (R9) |
| R7 | Pressure thrust must use the geometric exit area (flow uses Cd·A) | Read both producers; own nozzle (own sonic search, Cv on velocity, Cd on flow) | Both use F = ṁ·V8 + A8,geom·(P8 − P0) with ṁ = Cd·A8·ρ8·V8; V8 202.23 m/s; F 41.164 N; NPR 1.101 against a critical NPR of 1.953 → pressure thrust exactly 0; every operating-line point unchoked (NPR ≤ 1.155), so R7 changes **no** PD-1 number | M40 and match agree to 3e-13 | **verified** | `test_fixed_nozzle_pressure_thrust_uses_geometric_exit_area` (fails on old logic: 23 N difference at the test's choked state). Open convention: capacity uses Cd × Cv (≈ 0.94 of ideal) — see §8 |
| R8 | M12 did not read the rated point | Compare `state.json` with the turbine block of `design_point.json` | M_ngv_exit, P_ngv_exit, T_ngv_exit identical to M1, P1, T1 (bit-for-bit); throat 1.4936e-3 m², 65°, not choked | identical | **verified** | New `test_m12_fixed_ngv_reports_the_rated_point_when_imported` (an isentropic re-solve at T04 would fail it) |
| R9 | NGV85 hub pocket is blind with a central web; through-bore marked unresolved | Read the supplier drawing (ngv85.pdf/png); stack positions | Ø48 pocket **11 mm deep** from the front (vane-ring) face, then a centre web (≈ 6 mm plus shallow rear grooves) and a conical boss reaching aft to the 34 mm overall height, inside the rotor's shroud section. In the stack the rear bearing sits in the pocket, but the rear spacer, the Ø14 turbine boss (from x = 130.8 mm) and BC-02 (to x = 136.8 mm) pass through the web zone (pocket bottom ≈ 129.8 mm): the stack implicitly assumes the web removed | check `unknown`; `NG01_HUB_THROUGH_BORE_FINISHED` unresolved | **verified (finding real); corrected** where the fix was incomplete: `BC02_SPIGOT_OD` was still "provisional design" (now envelope only), IF-TU-BC2 and IF-BC2-NG now read unresolved, the cross-section now marks the hub region, the pocket diameter comes from the record, and the reports no longer present the hub bore or the rear-insertion assembly order as settled | **Team decision** (options in `manufacturing-and-budget.md` §2): bore the web and keep the pocket as the carrier seat; remove the web; a separate rear housing; or a carrier flanged to the machined web. Then a machining plan and a strength/stiffness check |
| R10 | Snapshot validator hashed `manifest.json` against itself and rejected every snapshot | Run the snapshot tool on **copies** of a run folder in a temp root (`phase1/snapshot_probe.py`) | Intact copy accepted; tampered output rejected; tampered manifest hash rejected; stale fingerprint rejected; **a listed output deleted from the run folder was accepted** (the old results folder is deleted first, so a SUMMARY section such as robustness silently disappears) | — | **verified; corrected** (missing listed outputs now rejected) | `test_snapshot_accepts_current_run_without_hashing_its_own_manifest` (fails on the pre-R10 logic), `test_snapshot_rejects_tampered_or_missing_listed_output` (fails before this pass) |
| R11 | Starter release timing in the synthetic controller | Read the state machine; run its tests | ASSIST → SELF_SUSTAIN_CHECK returns starter 0 in the same step; every abort (e-stop, operator stop, missing/invalid/stale/future/out-of-range sensor, overspeed, EGT trip, failure to light, no self-sustain) goes to SHUTDOWN with fuel 0 and the valve closed; FAULT latches; `HardwareOutputs.enabled` is always False and `enable()` raises | — | **verified** (synthetic plant only) | `test_controller_releases_starter_in_transition_step` (fails if the transition step still commands the starter), `test_synthetic_normal_start_reaches_run_with_starter_released`, abort-path tests. Thresholds remain illustrative |
| RD | `core/readiness.py` legacy fingerprint now also hashes `data/**` and `run_case.py` | Compute the committed (`git show HEAD:core/readiness.py`) and current fingerprints and blocker lists on the same tree (`phase1/readiness_compare.py`); read `config/readiness.yaml` at HEAD and now | `design_fingerprint: pending` and all 10 evidence items `pending`, at HEAD and now: **no reviewed evidence exists**, so nothing was silently invalidated or validated. Blockers identical (11 = 10 pending + fingerprint mismatch). Coverage grows by 15 files. Direction is fail-safe: once evidence is recorded, any edit under `data/` invalidates it | `run.py --report-only` unchanged: 15/16 limits, 35 CAD parameters, 11 blockers | **verified** | Coarse scope (a budget-only edit also invalidates engineering evidence) — a team choice, not a defect |

## 4. Independent audit of the rest (Phase 2)

Repository values are from the final snapshot. "Diff" is relative unless stated.

### 4.1 Cycle (`cycle_turbine/cycle_closure.py`, `r3_turbine_check.py`)

| Item | Independent result | Repository | Diff | Verdict |
|---|---|---|---|---|
| Compressor power ṁ·Δh0 (Δh0 from T03, map η) | 9,136.8 W | 9,136.8 W | < 1e-6 | verified |
| Turbine power ṁ_t·w | 9,254.4 W | 9,254.4 W | < 1e-6 | verified |
| Bearings (SKF/Palmgren, f0 1.7, 8 cSt, 40 N preload) + disc windage (Cm 0.004) | 98.4 + 19.3 W | same | < 1e-6 | verified; net shaft power 0 to ~1e-12 of P_c; no mechanical efficiency is applied on top, so nothing is counted twice |
| FAR from ṁ_comb·h3 + ṁ_f·η_b·LHV = (ṁ_comb + ṁ_f)·h4 | 0.013444, 9.529 kg/h | same | < 1e-6 | verified |
| T04 → T41 with 2 % tunnel leak re-entry (mass-weighted enthalpy) | 838.46 K, FAR_mix 0.013175, ṁ_t 0.20355 kg/s | same | < 1e-6 | verified |
| Pressure ledger, each loss once | inlet 0.88 %, turn/deswirl 2.000 %, combustor 2.500 %, mixing 0, jet pipe 1 % + swirl head 667 Pa, nozzle Cd/Cv; compressor stage loss inside the map | same chain P0 → P8 | exact | verified; the turbine row no longer prints its expansion in the loss column |
| Closure along the operating line 55–80 krpm | worst < 1e-10 relative | — | — | verified |

### 4.2 Compressor map (`map_matching/map_checks.py`)

| Item | Independent result | Repository | Diff | Verdict |
|---|---|---|---|---|
| Corrected flow ṁ√θ/δ and speed N/√θ at the compressor face (after the inlet loss), reference 545 °R / 28.4 inHg | 302.778 K / 96,173 Pa; N_corr 69,705 rpm; Q 0.18768 kg/s | same | ≤ 0.001 % | verified (reference convention itself from a secondary source; +19 K T04 if it were 288.15 K / 101.325 kPa) |
| β-line interpolation at 68 and 56 krpm (own parser: β linear in Q, PCHIP along a line, linear in N_corr) | PR 1.4865, η 0.7634; 56 krpm PR 1.318 | same | < 1e-6 | verified; another reasonable interpolation moves PR ≤ 0.18 % |
| No extrapolation in speed or β | rejects N_corr < 55,864 or > 144,956 rpm and β outside 0–1; lowest line = 54,498 rpm physical at 288 K | same rules | — | verified |
| DP-2 point (0.30 kg/s, PR 1.63, 66 krpm) not on the map | needs 0.2806 kg/s corrected; the 66 krpm line chokes at 0.2356 corrected = **0.2519 kg/s at PR 1.285**; 0.30 kg/s first on a line at 77,645 rpm (PR 1.41); PR 1.63 at 0.30 kg/s at **83,792 rpm** | "outside map"; 85,000 rpm on a 2.5 krpm grid | −1.4 % | verified |
| Work-coefficient argument | blade (Euler) coefficient Δh0/(PIF·U2²) = **0.837** vs Stanitz σ(11) = 0.820 | was 0.905; now 0.837 | — | **corrected** (PIF applied the wrong way in the fixed-wheel diagnostic); the conclusion survives only while η_c < 0.735 |
| Surge-margin definition SM = 1 − Q_surge/Q at constant corrected speed | 68 krpm 0.580, 56 krpm 0.575 | same | < 1e-6 | verified |

### 4.3 Turbine mean line (`cycle_turbine/r3_turbine_check.py`, `reynolds_validity.py`)

| Item | Independent result | Repository | Verdict |
|---|---|---|---|
| U at mean radius (r_m 35 mm, 68 krpm) | 249.23 m/s | 249.23 | verified |
| ψ, φ, reaction | 0.732, 0.515, 0.487 | same | verified |
| Triangles: β1, deflection, M1, M2,rel | −7.31°, 50.7°, 0.464, 0.438 | same | verified |
| Soderberg with aspect-ratio and Re corrections (Dixon & Hall) | NGV ζ 0.1040, rotor ζ 0.1026 | same | verified (arithmetic) |
| Tip leakage work debit (1 − K_tip·c/H), K_tip 2, c 0.35 mm, H 15 mm | 4.67 % work debit → 3.88 % relative η drop (η without debit 0.880) | same | verified as documented; if K_tip is meant as the usual efficiency-debit coefficient the model is ≈ 17 % lenient (modelling note) |
| Reynolds numbers (throat hydraulic diameter, Sutherland air) | rotor 15,555 (56 k) … 20,024 (68 k); NGV 20,961 … 26,831 | same to 0.05 % | verified; flagged 56–66 krpm |
| Basis of the 2e4 flag | none found in code, docs or the cited reference; Soderberg's basis is Re 1e5 (steady points at 0.16–0.20 of it) | — | **open** (team: keep, change, or replace by an explicit loss band) |
| Is η_tt ≈ 0.846 plausible for an 85 mm model-turbine stage at Re ≈ 2e4? | Without the tip debit the model gives 0.880 — a large-turbine value. Losses ×1.5 → 0.798, ×2 → 0.754, ×3 → 0.679. The (1e5/Re)^¼ correction cannot represent laminar separation; no trailing-edge, roughness or casting-finish loss; blade angles assumed. No measured efficiency of a comparable stage was found | — | **open — probably optimistic.** To close: stage test data (cold-flow rig or engine) |

### 4.4 Matching (`map_matching/match_resolve.py`, `probe_matching.py`, `probe_inner_grid.py`)

| Item | Independent result | Repository | Verdict |
|---|---|---|---|
| Residual definitions | unknowns β ∈ [0, 1], T04 ∈ [T03 + 40, 1500] K; r_mass = (ṁ_noz − ṁ_t)/ṁ_t, r_power = (P_t − P_c − P_mech)/P_c; both < 1e-6 to accept; choke handled as infeasibility inside the rating | as documented | verified |
| Independent re-solve at the design point | own model (own map, mean line, nozzle, own loss anchoring): β 0.6616, T04 848.02 K, 41.164 N, 9.529 kg/h; own residuals at the repository point 4.6e-11 / 7.8e-12 | same | verified (≤ 1e-6 on ~40 quantities) |
| 56 krpm point; nozzle-trim points 60°/50 mm, 72°/58 mm, 56°/54 mm | reproduced (56 krpm: β 0.6311, T04 849.81 K, 26.17 N) | same | verified (≤ 1e-6) |
| Uniqueness (probe of the final code, `probe_matching.out`) | 41-point β scans find one branch at 68 and 56 krpm; the power residual is monotone in T04 at the design β (one root); 7 of 8 distant starts reach the same root, 1 does not converge | one branch | verified at the probed points (not a proof). `verify_point` returns a constant from infeasible starts (its "failed start" (0.8, 1200 K) is NGV-choked), so it is weak evidence |
| Trend: smaller nozzle → higher T04, lower β | A8 × 0.90 → 1.10: T04 894.6 → 816.6 K, β 0.626 → 0.686, thrust 45.4 → 37.6 N | same direction | verified |
| Feasibility window and threshold labels | own model and own screens confirm both final NGV edges (0.97 × 699 mm² → NGV within 5 % of choke; 1.03 × 2506 mm² → T04 1176 K). Before the fix the lower NGV edge was an **inner-grid miss** (a root next to choke was not found; matches exist at 0.90–0.97 × 737 mm²); upper edge label said "no steady match" where T04 exceeds the screen; rotor 900 mm² was not a boundary; several "failure beyond" labels named the far end of the bracket | — | **corrected** (`test_inner_power_balance_finds_root_next_to_choke`, `test_threshold_reports_failure_just_past_the_boundary`); final windows: NGV throat 699–2506 mm² (lower edge: NGV within 5 % of choke; upper: T04 screen), rotor throat 722–2788 mm², turbine loss multiplier ≤ 5.8, compressor η offset ≥ −0.23, combustor loss ≤ 27 % — boundaries of the physical screens; the turbine correlation is out of range at all but the smallest rotor throat |

### 4.5 Combustor (`comb_nozzle_struct/check_comb_nozzle_struct.py`)

| Item | Independent result | Repository | Verdict / to close |
|---|---|---|---|
| 1.4 ms residence | V = A·L = 3.238e-4 m³ at the density of (T3 + T4)/2 → 1.400 ms; at exit density it would be ≈ 1.0 ms | 1.4 ms | verified (arithmetic). It is a sizing input that sets the liner length, not a prediction |
| 2.5 % loss basis | Selected because 2.5 % passes every existing screen and the shorter liner shortens the bearing span; both 2.5 %/1.4 ms and 2.5 %/2.0 ms pass; every 3–6 % option fails dilution penetration | — | basis verified; the report's "only combination" wording was wrong (fixed). **Open:** with the code's uniform-liner-static assumption every hole discharges to the liner exit static, but the liner exit dynamic head (ρ4u4² ≈ 4.9 kPa) is comparable to the 6.0 kPa hole drop; a 1-D momentum balance puts the sized holes at ≈ 5 % loss (dome bound 5.8 %). The robustness 4/6 % cases cover the cycle effect. To close: combustor owner revisits the liner model; cold-flow pressure-drop test |
| Hole areas and branch balances | outer primary/secondary/dilution 159.9/302.8/810.0 mm², inner 117.9/223.2/597.1 mm², film 306.6 mm²; counts 16/16, 16/16, 32/24 kept; both branches close with film and vaporizers | same | verified (compressible orifice flow, Cd 0.6; 2.2 % below incompressible) |
| Dilution penetration 0.67 ≤ 0.75 | 0.67 with the code's definitions | same | arithmetic verified; **open**: the code uses the geometric diameter with the area-mean jet velocity and a fixed 1200 K mainstream. With Lefebvre's d_j = d·√Cd and U_j = √(2ΔP/ρ3) at 1200 K the ratio is ≈ 0.89 (fails); with an energy-balance mainstream (~1717 K) 0.56–0.74. To close: combustor owner fixes the definitions (Lefebvre & Ballal Ch. 4) |
| Weld-seam check (2 + 2 holes) | outer dilution holes at ±5.625°, inner at ±7.5° fall within 3 mm + radius of the 0° seam; dilution arc pitch 9.8/9.5 mm against the ≈ 11.6 mm a clear band needs, so at best one hole sits on the seam | 2 / 2 | verified — the failure is unavoidable with these rows on rolled sheet. Team decision: liner route |
| Ligaments ≥ 3.048 mm | 4.16 / 3.91 mm (outer/inner, all row pairs) | same | verified |

### 4.6 Nozzle

| Item | Independent result | Repository | Verdict |
|---|---|---|---|
| V8 with Cv on velocity; ṁ with Cd·A8·ρ8·V8; F | 202.23 m/s; 0.20355 kg/s; 41.164 N | same | verified |
| Half-angle; exit Ø54; throat at the exit | 11.21°; 2.290e-3 m²; annulus rises 23 % before converging, no internal minimum | same | verified |
| Ø69 mm "rescue" of the combined adverse case | exit area = 1.094 × the retained inlet annulus (not convergent any more); the rescued point is outside the turbine correlation range | report claimed a rescue | **corrected** in the report: it is invalid as a simple exit resize |
| Cd × Cv convention | capacity = Cd·A·ρ8·(Cv·V_is) → ≈ 0.94 of ideal flow; if Cd 0.97 is meant as the overall coefficient this double counts ≈ 3 % of capacity (≈ +12 K T04) | — | **open** (team convention; measured nozzle would settle it) |

### 4.7 Rotordynamics (`rotor_cad/rotor_independent.py`, `rotor_rigid_bearing_limit.py`)

| Item | Independent result | Repository | Diff | Verdict |
|---|---|---|---|---|
| Rotor mass, CG, polar inertia | 0.417429 kg, 84.90 mm, 1.1869e-4 kg·m² (solid cylinders + discs) | same | 0 | verified (wheel masses/inertias are estimates) |
| Rigid-body crossings | own lumped beam with damped supports 18,264 / 19,918 rpm (ζ 0.868/0.584); rigid 2-DOF rotor (no shaft flexibility) ≈ 6 % lower | 18,264 / 19,918 | ≤ 0.01 % | verified. They are damped crossings with ζ ≈ 0.6–0.9, not resonances (no response peak near them); undamped synchronous criticals are 23,231 / 31,769 rpm |
| First bending crossing | own lumped beam 88,012 rpm; transfer matrices (undamped) 90,976 rpm; hand single-mass estimates bracket it only to ±50 % | 88,024 | ≤ 0.05 % | verified |
| Separation from 56–68 krpm | 0.2943 (bending mode governs) | 0.2945 | < 0.1 % | verified |
| Mesh convergence | own model 3 / 1.5 mm within ~0.03 % | 12/6/3 mm within 1 rpm | — | verified |
| "Stiffness must stay below about 3–5 N/µm" | separation < 0.20 above ≈ 3.98 N/µm (c = 1000 N·s/m), ≈ 3.86 N/µm with no damping; at 5 N/µm 0.093 | — | — | **corrected**: ≈ 3.9 N/µm, not 5 |
| Sensitivity to the assumed damping (case range 300–3000 N·s/m) | at 2 N/µm: c 300 → 0.333; 1000 → 0.294; 2000 → 0.221; **3000 → bending crossing 80,766 rpm, separation 0.188 < 0.20**. Rigid-bearing limit 77,773 rpm | not reported before | — | **new finding**: the pass also needs c ≲ 2.6 kN·s/m; to close: measure mount stiffness and damping, modal tap test |
| Turbine orbit at G2.5 | 3.40e-7 m | same | < 0.01 % | verified |

### 4.8 Structures (`comb_nozzle_struct/…`)

| Item | Independent result | Repository | Verdict |
|---|---|---|---|
| Shaft torque and τ = 16T/(πd³) on the 6 mm seat | T = (P_c + ½P_brg)/ω = 1.290 N·m (the seat itself carries P_c/ω; code 0.5 % conservative); τ 30.42 MPa | same | verified |
| Kt 2.0 bending / 1.6 torsion; peak von Mises | consistent with the R0.4 shoulder fillet (r/d 0.067, D/d 1.67); 84.51 MPa vs 327.5 MPa | same | verified; **open**: threaded ends (M6 minor ≈ 5.1 mm: 49.6 MPa nominal if all torque passed through it) and nut preload not covered — now an explicit `unknown` check |
| Alternating bending | 6.01 MPa vs 240 MPa | same | verified |
| Tip clearance hot / low-α shroud / shutdown bound | 0.361 / 0.301 / 0.118 mm (worst shutdown corner 0.067 mm, still > 0) | same to ≤ 0.23 % | verified (assumed metal temperatures) |
| Outer-liner buckling margin | Windenburg–Trilling, knockdown 0.5: 1,295 | same | verified (E 175 GPa hard-coded; creep buckling open) |
| Casing hoop stress | (P3 − P0)·r/t = 2.40 MPa vs 61.5 MPa | same | verified (membrane only; not containment) |

### 4.9 Assembly stack and CAD (`rotor_cad/stack_cad_audit.py`)

| Item | Independent result | Verdict |
|---|---|---|
| 33 axial stations from the records | all exact; ordering monotonic; clamp stacks contiguous | verified |
| Part overlaps | inverted CB-05 envelope (r_in > r_out); static tailcone envelope containing the rotating turbine nut and M8 shaft end (7 mm × 6.5 mm); tunnel ID 47.5 mm vs BC-02 envelope 48.0 mm over 3 mm while a check said the tunnel cleared a 32 mm carrier | **corrected**: CB-05 envelope fixed; the tailcone and the tunnel/carrier joint are now `unknown` checks (geometry undefined) |
| Cross-section vs stack | every drawn rectangle, shaft corner and bearing marker within 0.02 mm of the stack; but NG-01 was drawn as an open Ø48 bore | **corrected**: the hub region is now marked as unresolved in the figure |
| Units and types | consistent except the support stiffness exported as a dimensionless ratio; thread parameters named "minor dia" but holding the nominal size | **corrected** (stiffness type N/µm; nominal thread names) |
| Unresolved parameters carry no value | 6 of 6, all null | verified |
| Supplied values traced | TW85 (7 values) and NGV85 (2) match the drawings exactly; CW-01 (7) and bearing (3) supplier listings not re-read | verified / open |
| Parameter count | 186 (147 provisional / 19 fixed purchased / 14 envelope only / 6 unresolved); the old report's 182 was an arithmetic slip (its own counts summed to 185) | corrected |
| BC-01 sleeve OD / backplate pocket diameter | undefined (figure placeholder 32 mm, envelope 47.5 mm) | **now an unresolved bundle parameter** (`BC01_SLEEVE_OD`) |
| Flags the audit still raises on the final snapshot | tailcone vs rotating nut/shaft end; tunnel/carrier envelope overlap; BC-01 pocket undefined; NG-01 drawn as a solid ring with an open bore (now overlaid with the unresolved-hub marking); IF-TU-BC2 joint not realisable from the envelopes | expected: each is now an `unknown` check, an unresolved parameter or a marked figure region, because the geometry is genuinely undefined |

### 4.10 Budget (`budget_provenance/budget_check.py`, workbook read-only)

| Item | Independent result | Repository | Verdict |
|---|---|---|---|
| Workbook direct G120 (rows 9–118, qty × unit) | $5,402 | $5,402 | verified |
| Freight G122:G124; tax G126 `=CEILING((G120−G118+SUM(G122:G124))*K2,K5)`; reserve G127 `=CEILING(G120*K3,K5)` | $200; $450; $550 | same | verified |
| Total G129 / G3; conditional G148 | $6,602; $5,942 | same | verified |
| CSV extraction vs workbook | 113 rows, 0 mismatches | — | verified |
| PD-1 nominal / adverse / tax-exempt / all-conditional | $6,752 / $8,027 / $6,302 / $5,422 | same | verified |
| Routes SV1+SV5+SV4 and +SV2+SV3 | $5,822 / $5,487 (tax and reserve recomputed with the workbook formulas) | same | verified |
| Savings SV1–SV6 unconfirmed; no duplicate rotor/billet; no sponsor credit; unknown prices not zero | all hold | — | verified |
| BOM lines (119) qty × nominal/adverse | 0 mismatches | — | verified |
| Report wording "prices not yet in any total" | four of six items are already in the adverse total | — | corrected in the reports |
| Stock rows | R09 ½ in bar too small for 13.0/13.5 mm parts; BC-01 has no linked stock row; C01 remainder strip claimed three times | — | **open** (budget owner) |

### 4.11 Provenance (`budget_provenance/provenance_check.py`)

| Item | Independent result | Verdict |
|---|---|---|
| Every "supplied" value has a dated source | 51 of 51 resolve to a source document (supplier drawings also carry a SHA-256) | verified |
| Provenance labels match the record basis | 7 stack values labelled "component record (purchased part)" were assumptions/estimates (wheel length, CG, inertias, NGV chord and tip); 2 "(design)" labels were assumptions (tip clearance, compressor seat) | **corrected**: labels now carry the record's own basis |
| Assumptions register complete | only record parameters were listed; the case-file inputs (losses, Cd/Cv, η_b, LHV, windage, supports, combustor seeds) were missing | **corrected** |
| Consequential assumptions visible in the reports | Cd/Cv 0.97, LHV 43 MJ/kg, windage Cm 0.004 and jet-pipe 1 % were in no report | **corrected** (design-basis §5) |

## 5. Headline numbers of the pre-verification MORNING_REPORT.md

"Old" = the report as edited at 13:58 (run `cf53eecfed2f` unless noted). "Final" = snapshot `4a7560bfca63`.
"Independent" = the script named, rerun on the final snapshot. The updated report carries the final values.

| # | Headline claim (old report) | Old | Final | Independent check | Verdict |
|---|---|---|---|---|---|
| H1 | "Run status: current and internally consistent" | current | runs were stale at 14:46 | staleness check: only `core/assembly.py` differed | **corrected** (was false); final runs current |
| H2 | Test suite | 228 passed | 244 passed | full suite; clean venv | corrected |
| H3 | Design point air flow / PR / η_c / β | 0.2014 kg/s / 1.485 / 0.763 / 0.664 | 0.2009 / 1.486 / 0.763 / 0.662 | `map_checks`, `match_resolve` | verified (final) |
| H4 | T04 | 845.6 K | 848.0 K | `cycle_closure` | verified; +2.4 K from the viscosity fix |
| H5 | Turbine η_tt | 0.851 | 0.846 | `r3_turbine_check` re-rating | arithmetic verified; value **open** (probably optimistic at Re ≈ 2e4) |
| H6 | NGV flow 74 % of choke | 0.739 | 0.740 | `r3_turbine_check` | verified |
| H7 | Fuel | 9.50 kg/h | 9.53 kg/h | `cycle_closure` | verified |
| H8 | Gross thrust | 41.2 N | 41.2 N (41.164) | `check_comb_nozzle_struct` | verified |
| H9 | Compressor / turbine power; bearings + windage | 9.149 / 9.267 kW; 118 W | 9.137 / 9.254 kW; 118 W | `cycle_closure` | verified |
| H10 | Residuals | < 1e-11 | 2.8e-12 / −3.1e-14 | independent residuals of the repository point | verified |
| H11 | Operating line 55–80 krpm (T04, thrust, SM) | 848.0 … 871.7 K | 850.9 … 874.2 K | `cycle_closure` (all 11 speeds) | verified (arithmetic) |
| H12 | "margin to the 1150 K T04 screen in every single-parameter perturbation" | — | model T04 ≤ 952 K in every single-parameter case | robustness rows | **corrected**: true of the model's T04, but at 77 of the 87 single-parameter points the turbine correlation is out of range (1 more is below the map), so only 9 are feasible evidence |
| H13 | NGV effective throat 1494 mm² at 65° | 1494 | 1494 | cosine rule on the annulus (assumed vane tip Ø87) | verified (assumption; −5.8/+3.9 % over the tip-diameter range) |
| H14 | Robustness 93 points: 62 feasible / 29 fail / 2 unresolved | 62/29/2 | **10 / 2 / 81** | own status rule | **corrected** (viscosity + one validity rule, §7) |
| H15 | Combined adverse T04 1312–1313 K | 1312–1313 | 1317 K | — (model output) | verified as model output; the point is also outside the correlation range |
| H16 | "Opening the nozzle to Ø69 mm brings the adverse point back below 1100 K" | Ø69 | Ø69.4; exit 1.094 × inlet annulus | `check_comb_nozzle_struct`; `robustness.json` | **corrected**: invalid as a simple resize; rescued point out of correlation range |
| H17 | NGV throat window 740–2520 mm² ("below no steady match, above T04") | 740–2520 | 699–2506 mm² (below: NGV within 5 % of choke) | own model and screens (`match_resolve` G) | **corrected** (lower edge was a solver miss) |
| H18 | Rotor throat window 900–2800 mm² | 900–2800 | 722–2788 mm² | `match_resolve` | **corrected** (the run itself said 900–2375 with wrong labels) |
| H19 | Proxy map tolerance ±5 % flow/pressure, −0.04 η | — | model T04 ≤ 887 K in each | robustness rows | verified as model output; unresolved where extrapolated |
| H20 | DP-2 chokes near 0.25 kg/s / PR 1.29 at 66 krpm | 0.25 / 1.29 | same | `map_checks`: 0.2519 kg/s at PR 1.285 | verified |
| H21 | DP-2 0.30 kg/s at PR 1.63 near 85 krpm | 85 krpm | 85 krpm (2.5 krpm grid) | `map_checks`: 83,792 rpm | verified ("near 84 krpm") |
| H22 | DP-2 work coefficient 0.905 vs slip 0.82 | 0.905 | 0.837 vs 0.820 | `map_checks` | **corrected** (conclusion survives only while η_c < 0.735) |
| H23 | TW70 fallback ≈ 788 K, ≈ 35 N at 68 krpm (Ø46) | 788 / 34.8 | 792 / 34.7 | — (model output) | model output (same correlations; 56 krpm out of range for Ø46/Ø50) |
| H24 | CAD bundle "182 parameters" (148/19/13/5) | 182 | 186 (147/19/14/6) | `stack_cad_audit` | **corrected** (old sum was 185) |
| H25 | Cash 6,602 / 6,752 / 8,027 / 6,302 / 5,822 / 5,487 / 5,422 | — | same | `budget_check` (workbook formulas) | verified exactly |
| H26 | "Prices not yet in any total" (six items) | — | four are in the adverse total | `budget_check` | corrected wording |
| H27 | Failing checks: liner seam ×2, starter 142 A vs 66 A | — | same (142.1 A) | seam geometry recomputed; starter not re-derived | seam verified (unavoidable); starter **open** (extrapolated bound) |
| H28 | Rotordynamics 18,256 / 19,916 / 88,272 rpm; separation 29.8 % | from `af33609c34b6` | 18,264 / 19,918 / 88,024 rpm; 29.4 % | `rotor_independent` | stale values corrected; verified; **conditional** on k ≲ 3.98 N/µm and c ≲ 2.6 kN·s/m |
| H29 | "mount stiffness must stay below about 3–5 N/µm" | 3–5 | ≈ 3.98 N/µm (3.86 undamped); damping limit ≈ 2.6 kN·s/m | stiffness and damping sweeps | **corrected** |
| H30 | Legacy report unchanged (15/16, 35, 11) | — | identical output | `run.py --report-only` | verified |

## 6. Defects found and fixed in this pass

Each fix is the smallest change that removes the defect; each has a regression test that fails on the old
logic (or, for presentation-only items, is checked in the final outputs).

| # | Defect (found by) | Fix | Regression test |
|---|---|---|---|
| F1 | Turbine Reynolds number used a hot-gas viscosity 18–21 % below air, overstating Re by ~20 % and the Soderberg-corrected efficiency by ~0.005 (cycle/turbine re-check) | `core/turbine_rating.mu_hot`: Sutherland's law for air | `test_turbine_viscosity_matches_tabulated_air` |
| F2 | Two validity rules at once (map domain → unresolved, turbine correlation → fails; map-confidence → fails) and range checks passing on extrapolated points (R5 review) | one model-validity rule (`core/robustness.status_of`, `run_case.candidate_extra_checks`); `model_validity` column | `test_model_validity_is_unresolved_not_failed_and_never_feasible`, `test_range_checks_do_not_pass_on_extrapolated_points` |
| F3 | Inner power-balance solve missed roots between the last feasible T04 grid point and choke, reporting "no steady match" (matching re-check) | edge refinement to the feasibility boundary before giving up (`core/engine_match._inner_T04`) | `test_inner_power_balance_finds_root_next_to_choke` |
| F4 | Threshold table named the failure at the far end of the bracket and let validity flags set "physical" boundaries (matching re-check) | report the failure just past the boundary; boundaries of physical screens, validity reported separately (`core/robustness.threshold_search`) | `test_threshold_reports_failure_just_past_the_boundary` |
| F5 | DP-2 work-coefficient diagnostic multiplied by the power-input factor instead of dividing (map re-check) | `modules/m10_compressor._fixed_wheel`: blade work = Δh0/PIF (legacy sizing branch left for the team) | extended `test_m10_fixed_wheel_keeps_purchased_geometry` |
| F6 | Snapshot accepted a run whose listed output had been deleted, silently dropping a SUMMARY section; small values printed as 0.001 vs 0.001 (R10 probe) | refuse missing listed outputs; four significant figures below 0.01 | `test_snapshot_accepts_current_run_without_hashing_its_own_manifest`, `test_snapshot_rejects_tampered_or_missing_listed_output`, `test_snapshot_tables_keep_small_values_distinguishable` |
| F7 | Wheel bores hard-coded in the fit checks; NGV pocket diameter derived as hub OD − 7.4 mm (R2/R9 review) | bores and pocket from the component records | `test_fit_checks_follow_the_purchased_wheel_bores` |
| F8 | Provenance labels called assumed or estimated values "component record (purchased part)" or "(design)" (provenance re-check) | labels carry the record's own basis | `test_seed_provenance_labels_carry_the_record_basis` |
| F9 | Assumptions register omitted every case-file input (provenance re-check) | case inputs added | `test_assumptions_register_includes_case_level_inputs` |
| F10 | Inverted CB-05 envelope; rotating nut/shaft end inside the static tailcone envelope with no check; tunnel/carrier envelopes interfering while a check passed on an assumed 32 mm carrier (stack/CAD re-check) | envelope fixed; two explicit `unknown` checks | `test_stack_part_envelopes_are_well_formed`, `test_rotating_shaft_end_inside_tailcone_envelope_is_not_passed`, `test_tunnel_carrier_joint_uses_the_stack_envelopes` |
| F11 | Shaft check silent about the threaded ends and nut preload (structures re-check) | explicit `unknown` check | visible in `candidate_checks.json` |
| F12 | CAD bundle: support stiffness typed as a ratio; thread parameters named "minor dia" but holding the nominal size; BC-02 spigot "provisional design" despite R9; IF-CW-SH, IF-TU-BC2 read as settled; IF-NG-CS2 placed at the cover, not the mating face; BC-01 sleeve OD undefined (stack/CAD re-check) | new `stiffness` type (N/µm); nominal thread names; spigot envelope only; interfaces say unresolved; mating-face x; `BC01_SLEEVE_OD` unresolved | stiffness read-back in `test_cad_bundle_units_and_read_back`; final bundle checked by `stack_cad_audit.py` |
| F13 | Cross-section drew the NGV as an open Ø48 bore (R9) | hub region marked "passage UNRESOLVED" | visual (`figures/cross_section.png`) |
| F14 | M12 imported-point behaviour had no test (R8) | — (behaviour was right) | `test_m12_fixed_ngv_reports_the_rated_point_when_imported` |
| F15 | Pressure ledger printed the turbine expansion in the loss column; bearing record said a 12 mm shaft body | presentation and record text | final outputs |

Not changed (team-owned or convention — see §9): legacy M10 sizing PIF; `core/combustor.py` viscosity law,
uniform-liner-static model and penetration definitions; nozzle Cd × Cv convention; `verify_point` starts;
hard-coded liner E; budget stock rows.

## 7. The model-validity rule (R5) and what it changes

**Before this pass** the outputs used two rules at once. A point below the lowest compressor speed line was
*unresolved* ("the model cannot tell"), but a point where the turbine loss correlation is outside its Reynolds
range was *fails* ("the engine fails"), and a point outside the medium-confidence map region was also *fails*.
At the same time the range checks over the steady range ("steady self-sustaining match at every rated speed",
"max T04", "min surge margin", NGV/rotor choke fractions) counted those same out-of-range points as passes.

**Rule applied now (recommended; the team decides).** One rule for every model domain:

| Result at a point | Robustness status | Candidate check |
|---|---|---|
| no steady match, or a physical screen exceeded (T04, surge margin, NGV/rotor choke) | `fails` (even if a model is also out of range — the out-of-range note is kept in `model_validity`) | `fail` |
| the only issue is a model outside its validity domain (below the map, outside the medium-confidence map region, turbine loss correlation outside its range) | `unresolved` | `unknown` |
| every implemented screen and validity flag passed | `feasible` | `pass` |

A range check that passes only because extrapolated points are included becomes `unknown`, with the
extrapolated speeds listed. Unresolved/unknown is never counted as feasible evidence, so the rule cannot make
the design look better: it moves points from "fails" to "cannot tell" and moves several range checks from
"pass" to "cannot tell". Reverting is a two-line change (`core/robustness.status_of`,
`run_case.candidate_extra_checks`).

**Why not "fails"?** Applied consistently it would have to call the hot-day 56 krpm point (below the map) an
engine failure, and the same for every speed where only the correlation is extrapolated — a claim about the
engine that the model cannot support. **Why not "pass with a caution"?** Because the correlation's validity is
a prerequisite of the screen, and a missing prerequisite cannot yield a pass (output contract §3).

The rule interacts with a second finding: the turbine Reynolds numbers were computed with a viscosity ~18 %
too low. With air viscosity the rotor Re is 1.56–2.00e4 over 56–68 krpm, so the (unsourced) 2e4 flag now
covers 56–66 krpm and the 68 krpm design point is only 0.1 % inside it. Effect on every headline claim:

| Headline claim | Before this pass (`cf53eecfed2f`) | After (`4a7560bfca63`) | Which change moved it |
|---|---|---|---|
| Outcome | "conditionally feasible at the modeled point … at every rated speed" | conditionally feasible at the 68 krpm design point; **unresolved** at 56–66 krpm | viscosity (correlation out of range at 56–66 krpm) + rule |
| Candidate checks | 45 pass / 4 fail / 3 unknown (52) | 39 pass / 3 fail / 13 unknown (55) | validity check fail → unknown; 5 range checks pass → unknown; tunnel check pass → unknown joint; new unknowns: NGV hub through-bore (13:59 edit), tailcone, threaded ends |
| "Steady self-sustaining match at every rated speed in range" | pass (7/7) | unknown (7/7 matched; 6 extrapolated) | rule |
| Max T04 / min surge margin / NGV and rotor choke over the steady range | pass | unknown (values 849.8 K, 0.575, 0.74, 0.71 — all inside the limits) | rule |
| Robustness 93 points | 62 feasible / 29 fails / 2 unresolved | 10 feasible / 2 fails / 81 unresolved | with only the rule: 62 / 2 / 29; with only the viscosity: 10 / 81 / 2 |
| Single-parameter feasibility windows | NGV 737–2513 mm², rotor 900–2375 mm², losses ≤ 3.35×, η ≥ −0.165, combustor ≤ 10 % | NGV 699–2506 mm², rotor 722–2788 mm², losses ≤ 5.8×, η ≥ −0.23, combustor ≤ 27 % (physical screens; the correlation is out of range at almost every boundary) | threshold labels, solver root next to choke, validity separated from physics |
| Nozzle trim table | 25 points: 19 clear, 2 over T04, 4 out of correlation range (counted as failures) | 25 points: 11 feasible, 2 fail (T04), 12 unresolved | viscosity + rule |
| DP-2 work coefficient | 0.905 vs slip 0.820 | 0.837 vs 0.820 | blade-work fix |
| Design point | T04 845.6 K, η_tt 0.851, 41.2 N | T04 848.0 K, η_tt 0.846, 41.2 N | viscosity |
| Rotordynamics | separation 29.7 % (report said 29.8 %) | 29.4 % | stack change of 0.17 mm (liner length) |
| Cash | $6,752 nominal | unchanged | — |

## 8. Claims that could not be cleared

| Claim | Why it stays open | Input that would close it |
|---|---|---|
| The turbine delivers η_tt ≈ 0.846 at Re ≈ 2e4 | Soderberg extrapolated 5–6× below its basis; no data for this stage | Stage test (cold-flow rig) or engine data; at minimum supplier design data |
| NGV throat 1494 mm² / rotor exit angle −58° | assumed angles; the match is most sensitive to them | Pin-gauge throat survey of both castings, blade/vane counts, rotation hand |
| The proxy map represents the purchased wheel | billet 11+0 ≠ mapped 6+6; housing and vaned diffuser differ | Choose the stock 452708-0001 wheel, or test the billet wheel |
| Feasibility at 56–66 krpm | turbine correlation outside its range there | as the first row |
| The combustor achieves 2.5 % loss and the dilution jets penetrate as screened | liner static and jet definitions questioned; combustion unmodelled | combustor owner's model review; cold-flow split and pressure-drop test; ignition/stability rig |
| Rear-bearing path and assembly order | NGV hub web; carrier location undefined | team decision + machining plan + strength/stiffness check |
| Wheel fits | nominal turbine interference; compressor seat only an envelope | measured bores; approved fits; hub stress |
| 20 % critical-speed separation | needs k ≲ 3.9 N/µm and c ≲ 2.6 kN·s/m, both assumed | mount stiffness/damping rig; modal tap test |
| Starter peak current 142 A | starter bound extrapolated below the map | motoring test of the assembled core |
| Self-sustain below the lowest map line, light-off, idle | no characteristic below ~54.5 krpm | motoring and first-light tests |
| CW-01 and bearing supplier listings | not re-read in this pass | re-read the listings or measure the parts |
| Cash under $6,000 | every saving unconfirmed; stock rows and landed cost open | tax status, site approval, quotes, spend-to-date, corrected stock rows |
| Physical self-sustain | no hardware evidence of any kind | engine test |

## 9. Decisions that belong to the team

1. **NGV hub / rear-bearing path** (R9): bore the web and keep the pocket as the carrier seat; remove the web;
   separate rear housing; or carrier flanged to the machined web. Each changes the assembly order, rear support
   stiffness and temperature, axial-growth path and balancing route.
2. **Validity-failure taxonomy** (R5): this pass applied "model outside its validity range → unresolved/unknown,
   never feasible; physical exceedance → fail". Keep it, or count validity exceedances as failures (§7 lists the
   effect). Also decide whether the unsourced Re ≥ 2e4 flag stays, changes, or is replaced by an explicit loss
   band — the 68 krpm design point is 0.1 % inside it.
3. **Compressor wheel identity**: stock Garrett 452708-0001 (matches the map) or billet 11+0 (needs its own
   characteristic).
4. **Budget confirmations**: tax-exempt purchasing, an approved test site with containment, the sensor choice,
   quotes (R02/R03 landed, R04, S03/S04, F01, grinding), spend-to-date and inventory, corrected stock rows.
5. **Liner fabrication route**: shop seam band, drawn tube for the outer liner, or a clocked dilution gap.
6. **Model conventions**: legacy M10 PIF (moves the baseline), nozzle Cd × Cv, the combustor's viscosity law,
   liner static model and penetration definitions.
7. The decisions already listed by the integration pass: combustor architecture naming, 68 krpm maximum
   continuous speed, nozzle trim set, balancing route, thrust measurement, TW85/NGV85 vs TW70/NGV70.

## 10. Commands and results of this pass

```
python -m pytest -q                                   # 244 passed in 116 s (final)
python scripts/generate_dependencies.py --check       # current
python workspaces/python/check_worksheets.py          # 14 checked, 0 problems
python run.py --report-only                           # 15/16, 35 CAD parameters, 11 blockers; output identical to Phase 0
python run_case.py pd1-jm85 --robustness              # 4a7560bfca63, 1161 s
python run_case.py dp2-prescribed                     # d3cc73ced0c7
python run_case.py baseline-250N                      # cda5fff53d3a
python scripts/make_design_snapshot.py                # all three snapshotted
bash: for each script in docs/design/checks/independent/*/  ->  python <script>.py > <script>.out   # all exit 0
```

Clean environment: `python -m venv` + `pip install -r requirements.txt` (numpy 2.5.3, scipy 1.18.1,
matplotlib 3.11.2, pytest 9.1.1, PyYAML 6.0.3) → 229 passed at the start of the pass.
