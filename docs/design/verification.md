# Verification record

What was checked, how, and what it does **not** establish. Software checks show the code does what it says;
they are not engine evidence. The independent re-check of 2026-10-04 is recorded claim by claim in
[`independent-verification.md`](independent-verification.md); its scripts and saved outputs are in
[`checks/independent/`](checks/independent/README.md). Logs: `docs/design/baseline/` (pre-change baseline),
`docs/design/results/<case>/run.log` and `manifest.json` (per-run identity).

## Commands (run from the repository root, Python 3.13.2)

```
python -m pytest -q                                   # full suite (existing + new)
python scripts/generate_dependencies.py --check       # generated graph doc is current
python workspaces/python/check_worksheets.py          # 14 learning worksheets still run
python run.py --report-only                           # legacy baseline report (unchanged numbers)
python run_case.py baseline-250N                      # legacy case through the case runner
python run_case.py dp2-prescribed                     # DP-2 prescribed-flow screen
python run_case.py pd1-jm85 --robustness              # candidate: match, pipeline, components, CAD, BOM, robustness
python scripts/make_design_snapshot.py                # durable copies + SUMMARY.md tables (refuses stale or incomplete runs)
python docs/design/checks/gas_property_audit.py       # independent NIST-JANAF property comparison
python docs/design/checks/independent/<area>/<script>.py   # independent re-checks; see the README there
```

## Layered evidence

"Independent" means a script or hand calculation that does not import the code under test (gas properties
from `core.gas` only, where stated). Tests are software checks of the implementation.

| Layer | Check | Method / reference | Result |
|---|---|---|---|
| Equations, units | Air cp fit | NIST-JANAF species mixture (independent data) | within ±0.2 % 300–1500 K (`test_air_fit_against_nist_janaf_species_mixture`) |
| | Products surrogate | Frozen complete combustion of C12H23 from NIST-JANAF | surrogate 1.2 % low (FAR 0.0139), 1.8–2.0 % low (FAR 0.022) — documented bias |
| | Hot-gas viscosity (turbine Re) | Tabulated air (Incropera & DeWitt Table A.4) | **corrected**: old law 18 % low; Sutherland now within 2–4 % (`test_turbine_viscosity_matches_tabulated_air`) |
| | Newton property inversions | Against bisection inversions of the same model | < 1e-6 K over 300 random states |
| | Soderberg coefficient | Hand value (ε 90°, b/H 1/3) | exact |
| | Corrected flow/speed | Independent unit conversion of 545 °R / 28.4 inHg; round trip | 302.78 K / 96,173 Pa; exact |
| Components | Turbine rating | Independent re-implementation of the documented mean line from the reported inlet state (`cycle_turbine/r3_turbine_check.py`) | every reported output reproduced to < 1e-6; energy, Euler and continuity residuals 0 |
| | Compressor map | Independent CSV interpolation (`map_matching/map_checks.py`) | PR, η, flow at 56 and 68 krpm to < 1e-6; no extrapolation; DP-2 off the map |
| | Diffuser | Throat continuity, opening-ratio flag (tests) | pass; not independently recomputed |
| | Rotor FE | Analytic benchmarks (tests); independent lumped-beam, rigid-rotor and transfer-matrix models (`rotor_cad/rotor_independent.py`) | criticals to ≤ 0.05 %; separation reproduced |
| | Rotor FE on PD-1 | Mesh 12/6/3 mm; own model at 3/1.5 mm | converged to < 1 rpm / ~10 rpm |
| | Combustor layout | Inner/outer counts, film area, seam and ligament geometry recomputed (`comb_nozzle_struct/…`) | reproduced; seam failure confirmed unavoidable with these rows |
| | Combustor sizing basis | 1-D momentum balance of the liner | **open**: sized holes consistent with ≈ 5 % loss, not the 2.5 % basis |
| | Dilution penetration | Lefebvre definitions | **open**: 0.67 with the code's definitions, ≈ 0.89 with Lefebvre's |
| Interfaces | M01 imported point | Rejects stale compressor work / fuel balance, mode conflicts, missing imports | pass |
| | M12 imported point | Reports the rated NGV station, not an isentropic re-solve at T04 | pass (`test_m12_fixed_ngv_reports_the_rated_point_when_imported`); equal to the turbine block |
| | M20 inlet | Follows P031/mdot_comb, not P03/mdot, when they differ | pass |
| | Module path vs match | M40 fixed nozzle capacity vs imported hot flow | residual ~1e-12 |
| | DP-2 screen | Pipeline prescribed mode vs archived `dp2_screen.py` | T03 348.10 K, P03 163.51 kPa, 23.72 kg/h, 98.1 N reproduced |
| | Baseline regression | `baseline-250N` case state vs pre-change snapshot | identical except the two re-modelled diffuser outputs |
| Matching | Residual closure | Independent residual evaluation of the repository point (`map_matching/match_resolve.py`) | r_mass ~1e-10, r_power ~1e-13 |
| | Independent re-solve | Own engine model (own map interpolation, turbine mean line, nozzle) | design point, 56 krpm and three trim points to < 1e-6 |
| | Multiple starts | Probe: 7 of 8 distant starts reach the same root, one fails to converge; 41-point β scan finds one branch | unique at the probed points (not a proof). `verify_point` cannot leave an infeasible start, so its "failed start" is weaker evidence than it reads |
| | Root next to choke | Inner power-balance grid could miss a root between the last feasible point and choke | **corrected** (`test_inner_power_balance_finds_root_next_to_choke`) |
| | Trend physics | Smaller nozzle → higher T04, lower β, more thrust | pass (test and independent probe) |
| Robustness | Status rule | One model-validity rule (unresolved, never feasible); range checks unknown when extrapolated | **corrected** (`test_model_validity_is_unresolved_not_failed_and_never_feasible`, `test_range_checks_do_not_pass_on_extrapolated_points`) |
| | Threshold table | Failure reported just past the boundary; boundaries of physical screens with validity reported separately | **corrected** (`test_threshold_reports_failure_just_past_the_boundary`) |
| | Points | 93 case-speed points | 10 feasible, 2 fail (combined adverse T04 1317 K), 81 unresolved (turbine correlation out of range, or below the map) |
| Mechanics | Stack geometry | 33 stations recomputed from the records; ordering; clamp stacks | exact |
| | Envelopes | Inverted CB-05 box; tailcone vs rotating nut/shaft end; tunnel vs carrier envelope | **corrected** / now `unknown` checks (`test_stack_part_envelopes_are_well_formed`, `test_rotating_shaft_end_inside_tailcone_envelope_is_not_passed`, `test_tunnel_carrier_joint_uses_the_stack_envelopes`) |
| | Fits | Bores from the records; 5–15 µm nominal turbine interference | `unknown`, by design (`test_fit_checks_follow_the_purchased_wheel_bores`) |
| | Axial growth | Hand calculation (`phase1/axial_growth_check.py`) | sign verified (gap opens); stack-faithful path +25 µm more |
| | Shaft, clearance, buckling, hoop | Independent formulas (`comb_nozzle_struct/…`) | reproduced; threaded ends not covered (now an `unknown` check) |
| CAD | Bundle schema | Unit/type consistency, duplicates, unresolved values, stale fingerprint, read-back | pass; stiffness now its own type (N/µm); thread parameters named as nominal sizes |
| | Purchased values | Records vs supplier drawings | TW85 (7) and NGV85 (2) match; CW-01 and bearing listings not re-read |
| Budget | Workbook reproduction | Independent read-only extraction with the workbook formulas (`budget_provenance/budget_check.py`) | $6,602 and every PD-1 scenario exact |
| | Provenance | Labels from the record basis; case inputs in the register | **corrected** (`test_seed_provenance_labels_carry_the_record_basis`, `test_assumptions_register_includes_case_level_inputs`) |
| Controls (synthetic) | Start sequence, starter release in the transition step, failure to light, stale/invalid sensors, overspeed, operator stop, saturation, hardware disabled | pass (synthetic plant only) |
| Run integrity | Failed run marks LATEST stale; outputs separated by fingerprint; snapshot refuses stale, tampered **and missing listed** outputs | pass (`test_snapshot_*`; `phase1/snapshot_probe.py` on copies) |
| | Fingerprint scope | Every file under `data/` plus case, config and source | pass (`test_case_loading_and_identity`) |
| Legacy readiness | Old vs new `design_fingerprint` scope | Same 11 blockers; no reviewed evidence exists | `phase1/readiness_compare.py` |

## Not run / not available

- ROSS or any commercial rotordynamics/FEA/CFD solver — not installed; FE benchmarked against analytic cases
  and independent models instead.
- Native CAD rebuild — no CAD application was exercised; the bundle is validated by read-back only.
- Equilibrium chemistry (CEA) — not run; frozen-composition comparison only.
- Any hardware, rig or engine test.

## Test totals

| Run | Result |
|---|---|
| Baseline before the integration pass (`docs/design/baseline/pytest_baseline.log`) | 163 passed |
| Start of the verification (14:49) | 229 passed in 151 s |
| Clean virtual environment with only `requirements.txt` | 229 passed in 173 s |
| Final code (verification fixes + 15 new tests) | **244 passed** in 116 s |
| `generate_dependencies.py --check` | current |
| `check_worksheets.py` | 14 checked, 0 problems |
| `run.py --report-only` | 15/16 legacy limits, 35 CAD parameters, 11 evidence blockers — identical to baseline |
| `gas_property_audit.py` | air within ±0.2 %; products surrogate −1.2 % (FAR 0.0139) |
| Known flaky test | `tests/learning/test_platform.py::test_corrupt_and_interrupted_save_recovers_latest_history` can hit a Windows `PermissionError` under heavy load (OneDrive); rerun alone before treating it as a regression |

Case runs: `results/` is generated from the current fingerprints (`pd1-jm85` `4a7560bfca63`, `dp2-prescribed` `d3cc73ced0c7`, `baseline-250N` `cda5fff53d3a`). The snapshot validator checks the
retained artifact hashes, refuses runs whose listed outputs are missing, and deliberately excludes
`manifest.json` from its own hash comparison.
