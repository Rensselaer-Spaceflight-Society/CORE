# September 2026 model corrections and remaining evidence

The reverse-flow architecture has engineering precedent; CORE's particular engine is **not yet validated**. Corrections below improve internal consistency. None substitutes for component tests, supplier limits, material/process qualification or independent review.

## Fix ledger

| Finding | Code change | Verification / remaining limit |
|---|---|---|
| Cycle used constant cp for work but integrated enthalpy for fuel | `core/thermo.py`, M01/M10/M13/M40 use the shared enthalpy and entropy model for work and local states | Work, energy, entropy, nozzle sonic/subsonic regression checks; product properties still a surrogate |
| Properties silently clamped or inversions returned unattainable values | Reject out-of-range/nonfinite properties, invalid efficiencies and unbracketed/unconverged solutions | Invalid-input and failure-path tests |
| Combustor reconstructed sea-level inlet and fuel state | M20 passes the cycle's actual T03, P03, FAR, fuel flow, efficiency and LHV | Shared-state consistency and round-trip energy checks |
| M24 reran sizing and mislabeled kW/m² as W/m² | Publish diagnostics from the one M20 geometry; convert to SI once | Test forbids another sizing call; heat flux is approximately 580,500 W/m², not 580.5 W/m² |
| Annulus “solved” velocity did not match geometry | Rate the frozen annuli and actual casing area | Continuity checks for both branches; annulus losses need not equal because separate hole heads close the paths |
| Hole/film/vaporizer branches did not close independently | Subtract vaporizer air from outer supply and allocate remaining branch demands consistently | Both branch mass residuals are checked |
| Global total loss used for every local hole pressure difference | Use local annulus static states, a uniform liner static state, and compressible orifice flux | Lumped local-reservoir approximation; axial withdrawal and actual Cd still need evidence |
| Vaporizer mixed stream borrowed fuel pump pressure | Allocate the available outer air-path head among scoop, tube and crimp; reject infeasible budgets | Bore/crimp fit and pressure-budget tests; heating, mixing and evaporation losses remain unvalidated |
| Total/static discharge states were reversed | Solve subsonic area continuity from total state; use the same convention in the RPM sweep | Mass/energy and total-static regression checks |
| Primary J mixed cold density with hot-zone density | Use primary-zone air plus fuel with the primary hot-gas density and area | J remains a diagnostic, not a demonstrated flame-stability boundary |
| Uncalibrated CLP curve changed combustion efficiency | Use explicit assumed efficiency; keep CLP only as a diagnostic | Tests ensure it cannot overwrite the chosen energy balance |
| Cold exports changed ODs but left IDs and lengths hot | Apply D_cold = D_hot / (1 + alpha ΔT) to liner surfaces, holes and lengths | Cold surface/wall round trips; wall thickness input is a hot-model dimension. Uniform metal temperature remains prescribed |
| NGV flagged subsonic but always used sonic area | Derive local state/Mach from required mean-line velocity; choose the matching area branch | Actual flow-regime continuity test; effective mean-line area is not a finished vane throat drawing |
| M13 and M33 used different blade masses | Share root section, linear tip/root area taper, mass and centroid; integrate mass/inertia consistently | M33 force/stress uses production geometry; historical KJ66 force check now exercises M33 |
| “Burst margin” suggested full rotor qualification | Add `blade_stress_speed_margin_ratio`; retain old name only as deprecated alias | Blade centrifugal screening only; disc/impeller strength, creep/fatigue and overspeed evidence remain open |
| Critical-speed check ignored operating range/startup crossing | Check distance to an explicit provisional 30,000–66,000 rpm continuous range and report startup crossing separately | Current separation fails; no limit relaxed |
| Missing turbine tip-speed check; missing data silently skipped | Cover every configured limit and reject missing/nonfinite inputs | Coverage and failure-path tests |
| State guard bypassed through dict methods; infinity accepted | Use a read-only Mapping of declared inputs; reject nonfinite outputs | Read/get/iteration/mutation tests |
| Self-loops skipped; tiny relaxation could fake convergence | Iterate self-dependencies and check unrelaxed fixed-point residuals | Self-loop/nonconvergence tests; counts are not numerically blended |
| Repeated cycle runs implied efficiency refinement | Remove the no-op outer refinement loop | No component-efficiency prediction is claimed |
| Pump pressure ambiguous and plumbing incomplete | Distinguish absolute outlet pressure from differential head; include provisional minor/filter budgets | Budget is not pump selection or a fuel-system qualification |
| Reports could look manufacturing-ready | Separate software CI, screening limits, evidence completeness and human part release | `--release-check` intentionally fails with missing current evidence |

## What the corrected baseline says

Run `python run.py --report-only` for current values; the generated report is authoritative for that revision.

- 250 N is the sizing target, approximately 0.484 kg/s is the sized airflow.
- Dome flux is roughly **580 kW/m²**, close to the existing 600 kW/m² placeholder ceiling; the wall temperature and heat-transfer correlations are not validated.
- The preliminary critical speed is roughly **23,400 rpm**. Startup crosses it, and separation from the proposed continuous range is roughly **10%**, below the existing 20% criterion.
- The baseline meets 15 of 16 numerical comparisons. It fails the evidence gate regardless of that count.
- The corrected vaporizer sizing no longer reproduces the historical KJ66 4 mm bore. The earlier claim of validation is withdrawn; do not tune the pressure budget to recover it.

## Assumptions the team must resolve

**Cycle and turbomachinery:** compressor/turbine maps at common corrected conditions, surge margin, off-design matching and startup acceleration. The products model `cp_air(T) × (1 + 0.75 FAR)` is unvalidated; fuel mass fraction is not a statement about reacted-gas composition. Compare mixture properties against independent thermochemistry, and recognize that equilibrium calculations cannot establish finite-rate stability.

**Combustor:** cold-flow air distribution and pressure losses, ignition/lean blowout, flame location, vaporizer startup/shutdown/coking, wall cooling, radiation, exit temperature pattern and hot streaks. Residence time is bulk transit bookkeeping. A penetration/mixing proxy is not measured pattern factor.

**Mechanical:** temperature-dependent material allowables, outer-liner external-pressure buckling, hot/cold fits, shaft bending and attachments, rotor/disc/impeller strength and life, balance, damped gyroscopic rotordynamics, bearing preload/lubrication/thrust and supplier speed capability. The current liner is modeled as 316SS while the existing temperature limit comment refers to Inconel 625; that mismatch is an explicit release blocker. No material limit was silently relaxed.

**Controls/test system:** selected pump and injector curves, line/filter/minor losses, startup sequence, flameout response, overspeed/overtemperature trips, emergency shutdown and approved containment/test site. The casing pressure estimate is not fragment-containment evidence.

## Release evidence

`config/readiness.yaml` contains ten required evidence categories. Every category starts `pending`. Each reviewed entry must reference an in-repository artifact, its SHA-256, reviewer and review date. The top-level fingerprint covers current core/module/config inputs, excluding the readiness record itself. Any covered change makes the evidence record stale.

Use `python run.py --report-only` to obtain the current fingerprint in `out/readiness.json`; populate the evidence record only after actual review. `python run.py --release-check` requires all numerical limits and complete current records. This checks completeness and identity, **not authenticity or technical adequacy**. Human engineering, Safety and shop approval still governs each released part. Fixtures/coupons can have a separately scoped review; they do not inherit an engine release.

## Sources and limits of transfer

- [NASA Brayton cycle overview](https://www.grc.nasa.gov/www/k-12/airplane/brayton.html): gas-turbine cycle context, not CORE performance evidence.
- [Yang et al., reverse-flow microcombustor evaporation-tube study (2025)](https://link.springer.com/article/10.1007/s44270-025-00023-9): configuration-dependent combustion behavior; not validation of this geometry.
- [NASA Chemical Equilibrium with Applications](https://www.nasa.gov/glenn/research/chemical-equilibrium-with-applications/): independent equilibrium-property comparison; does not model flame stability by itself.
- [FAA AC 33.27-1A](https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_33_27-1A.pdf): precedent for rotor analysis/test substantiation under adverse conditions; not a universal 1.5 margin or a claim that aircraft certification applies to CORE.
- [SKF high-speed bearing considerations](https://evolution.skf.com/us/bearings-for-high-speed-operations/): bearing design, preload and lubrication matter; obtain component-specific supplier guidance.
- [Sakurai et al., miniature kerosene combustor experiments (2020)](https://www.jstage.jst.go.jp/article/jgpp/11/3/11_1/_article/-char/en): adjacent vaporization/startup evidence, with different hardware and scale.

Historical documents `HANDOFF.md`, `PATCHES.md` and `RESEARCH.md` describe earlier assumptions. Their validation and baseline claims are superseded by this review.
