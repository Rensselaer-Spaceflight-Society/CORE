# Fork B: compressor map + whole-engine matching (independent audit scripts)

Run from the repository root (`C:\Users\andyc\OneDrive\Desktop\CORE\github-core`). Default inputs are the
snapshot folders `docs/design/results/pd1-jm85/` and `docs/design/results/dp2-prescribed/`; pass another
run folder as argv to re-check a new run. Each script prints `name indep repo diff% PASS/DIFF` lines and
exits 1 when a difference is not explained.

| Script | Independent of the code under test? | What it checks | Runtime |
|---|---|---|---|
| `indep_lib.py` | yes (imports only `core.gas` for cp/h) | own entropy (quadrature), inversions, map parser/interpolator, turbine mean line, nozzle, losses, nested matching solver | library |
| `map_checks.py` | yes | correction direction and reference state, station for theta/delta, beta-line interpolation at 68/56 krpm, domain limits, DP-2 off-map claim, work-coefficient argument, surge margins | ~40 s |
| `match_resolve.py` | yes | own anchoring + global re-solve at 68 krpm (design point, ~40 quantities), 56 krpm, three nozzle-trim points; NGV-throat window edges with own screens | ~5 min |
| `probe_matching.py` | NO - behaviour probe of `core.engine_match` | distant-start convergence, 41-point beta scans, T04 monotonicity, nozzle trend, what fails just beyond each threshold boundary, missed roots below the smallest-NGV boundary | ~7 min |
| `probe_inner_grid.py` | NO - behaviour probe | mechanism of the missed root (14-point inner T04 grid vs NGV choke) | ~1 min |

Outputs of the final runs (snapshot `4a7560bfca63`, after the verification fixes): `*.out` next to each script.
`indep_lib.py` now uses Sutherland's viscosity law and `map_checks.py` the blade-work convention
Δh0/(PIF·U2²), matching the corrected repository; `match_resolve.py` compares the threshold table's physical
screens (model validity is reported separately there). The first runs on `cf53eecfed2f` found the defects
recorded in `docs/design/independent-verification.md` (§4.2, §4.4).
