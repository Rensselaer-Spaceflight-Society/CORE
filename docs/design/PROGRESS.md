# Preliminary design integration — progress log

Resume point for the October 4, 2026 integration pass and the independent verification that followed it.
Updated at each milestone.

## Workspace identity

| Item | Value |
|---|---|
| Repository | `C:\Users\andyc\OneDrive\Desktop\CORE\github-core` |
| Base revision | `98c4167` (`main`) |
| Working branch | `feat/preliminary-design-integration` (local only; nothing pushed, nothing committed by any agent) |
| Protected user work | `README.md` modification, `docs/overnight-handoff/`, `docs/preliminary-design-roadmap.md` — left untouched |
| Other checkouts | `tmp/combustor-dp2-publish` (`fix/combustor-dp2`) and `core-engine` — not used |
| Python | 3.13.2; numpy 2.3.1, scipy 1.17.1, PyYAML 6.0.3, matplotlib 3.10.8, openpyxl 3.1.5 (read-only budget extraction), pytest 9.0.3. Clean-venv check with only `requirements.txt` (numpy 2.5.3, scipy 1.18.1, matplotlib 3.11.2, pytest 9.1.1): 229 passed |
| Optional solvers | ROSS not installed (own FE benchmarked instead); no native CAD application; no CFD/FEA |
| Budget input | `..\outputs\core-budget-20261002-fbef9859\CORE_Itemized_Budget.xlsx` (sha256 46364aee…), read-only; unchanged after the verification |
| Backup of the untracked work | `..\tmp\backups\github-core-worktree-20261004-144736.tar.gz` (taken before the verification edits; excludes `out/`) |

## Task status

Software status / engineering-evidence status.

| ID | Software | Engineering evidence | Where |
|---|---|---|---|
| T00 | implemented and checked | n/a | this file |
| T01 | implemented and checked | n/a | `docs/design/baseline/`; `baseline-250N` case reproduces the snapshot exactly |
| T02 | implemented and checked | n/a | `core/records.py`, `core/cases.py`, `run_case.py`, `config/cases/`, optional mode reads + module sets in `core/module.py` |
| T03 | implemented and checked | partially complete — proxy map | `data/maps/`, `core/compressor_map.py`, M10 fixed-wheel mode |
| T04 | implemented and checked | partially complete — throats/angles unmeasured; NGV hub web machining open | `data/components/turbine_*`, `ngv_*`; TW70 alternative in robustness |
| T05 | implemented and checked | partially complete | `core/diffuser.py`, M11 rewrite, station convention |
| T06 | implemented and checked | partially complete; liner-loss and penetration definitions questioned | M20 options, `core/postprocess.combustor_layout`, basis comparison |
| T07 | implemented and checked | partially complete | M40 fixed-nozzle mode, `postprocess.nozzle_contour`, trim table |
| T08 | implemented and checked | partially complete — rear-bearing path and fits unresolved | `core/assembly.py`, M29, `core/rotor_fe.py`, M30/M32/M34 assembly mode |
| T09 | implemented and checked | partially complete | `docs/design/limits-and-correlations-audit.md`, NIST-JANAF property audit |
| T10 | implemented and checked | requirements only | `core/systems.py`, `data/systems/signals.yaml`, `core/controls_sim.py` (hardware disabled) |
| T11 | implemented and checked | conditional | `core/turbine_rating.py`, `core/engine_match.py` |
| T12 | implemented and checked | conditional; most low-speed points unresolved (turbine correlation range) | `core/robustness.py` |
| T13 | implemented and checked | forecast only | `core/budget.py`, `data/budget/` |
| T14 | implemented and checked | no native CAD rebuild | `core/cad_export.py`, `core/exports.py`, `core/figures.py` |
| T15 | implemented and checked | reports and snapshots current; engineering evidence remains conditional | `docs/design/MORNING_REPORT.md` and companions |
| VER | independent verification done | see `independent-verification.md` | `docs/design/independent-verification.md`, `docs/design/checks/independent/` |

## Key decisions (reversible, with reasons in design-basis.md)

1. GT3076R map digitized as a related-wheel proxy (billet 11+0 wheel ≠ mapped 6+6 wheel).
2. DP-2's 0.30 kg/s / PR 1.63 at 66 krpm is not supported: proxy map needs ~84 krpm; blade work coefficient 0.837 > slip 0.820 (marginal; holds only while η_c < 0.735).
3. Purchased turbine route: JETMAX TW85 finished + NGV85 blank (primary); TW70 + NGV70 finished (alternative).
4. Fixed-geometry matching, zero starter torque; nozzle 54 mm chosen for ~850 K nominal T04 leaving margin for adverse cases.
5. Max continuous 68 krpm; soft damped bearing mounts; front bearing recessed 6 mm into the backplate hub.
6. Combustor sized at 2.5 % prescribed loss / 1.4 ms; 4–8 % in robustness.
7. Diffuser: 19 vanes, exit 126 mm, width growth 1.5; turn allowance 2 %.
8. 10 × 26 × 8 hybrid bearings both ends (9.99 mm turbine bore); shaft body 13 mm.
9. NGV flange to rear cover: 12 × M3 hot bolts on PCD 98; nozzle starts at the NGV casting rear face.
10. Candidate budget route SV1+SV5+SV4 ($5,822, under the ceiling); adding SV2+SV3 gives $5,487. None confirmed.
11. **Verification (2026-10-04):** model-validity rule — a point whose only problem is a model used outside its
    validity range is *unresolved* (robustness) / *unknown* (checks), never feasible and not a failure. Team
    decision; reversible in `core/robustness.status_of` and `run_case.candidate_extra_checks`.

## Commands

```
python -m pytest -q
python run_case.py pd1-jm85 --robustness        # ~20 min
python run_case.py dp2-prescribed
python run_case.py baseline-250N
python scripts/make_design_snapshot.py
python scripts/generate_dependencies.py --check
python docs/design/checks/gas_property_audit.py
python docs/design/checks/independent/<area>/<script>.py   # see the README there
```

## Last verified state

| Item | Value |
|---|---|
| Full test suite (final code) | **244 passed** (116 s); 229 at the start of the verification |
| Dependency doc check | current |
| Worksheets / legacy report | 14 worksheets OK; `run.py --report-only` output identical to the start of the verification (15/16, 35, 11) |
| Last complete runs (snapshotted, current) | pd1-jm85 `4a7560bfca63` (39 pass / 3 fail / 13 unknown), dp2-prescribed `d3cc73ced0c7`, baseline-250N `cda5fff53d3a` |
| Robustness | 93 fixed-geometry case-speed points: 10 feasible, 2 fail (combined adverse, T04 1317 K), 81 unresolved (79 turbine correlation out of range, 2 below the map) |
| Independent checks | every script in `docs/design/checks/independent/` exits 0 on the final snapshot |
| Snapshot validation | retained outputs hash-checked; missing listed outputs refused; `manifest.json` exempt because it stores the hashes |

## Current failures / open items

See `docs/design/MORNING_REPORT.md`, `docs/design/remaining-work.md` and
`docs/design/independent-verification.md`. The candidate is still PRELIMINARY - NOT FOR MANUFACTURE: physical
self-sustain, purchased-wheel map identity, turbine/NGV throat geometry and low-Re efficiency, the NGV hub
passage and rear-bearing path, low-speed starting, wheel fits, material allowables and the budget ceiling
remain open.

## Next action

The team decisions listed in the morning report (NGV hub path, validity rule, wheel identity, budget
confirmations, liner route). After any design-source edit, rerun all three cases and then
`python scripts/make_design_snapshot.py`; the snapshot script refuses stale runs and runs with missing outputs.
