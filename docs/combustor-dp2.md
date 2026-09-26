# V22 at DP-2: inputs, corrections and remaining choices

The standalone `dp2`, `6in` and `6inch` presets now use PR 1.63, compressor
efficiency 0.72, inlet pressure recovery 0.99, air flow 0.30 kg/s, TIT 1150 K,
combustion efficiency 0.96 and fuel LHV 43 MJ/kg. This reproduces the archived
DP-2 cycle screen's **T03 = 348.10 K, P03 = 163.51 kPa and fuel = 23.72 kg/h**.
The [DP-2 review](project/dp2-review.md) and its
[cycle screen](project/checks/dp2_screen.py) document the inlet and fuel state.
The fuel difference from 22.9 kg/h comes from the
different FAR; the script has not been tuned to that earlier number.

Run from the repository directory:

```sh
python V22_CombustionChamberDesign.py dp2
python V22_CombustionChamberDesign.py dp2 --pressure-drop 0.025
python V22_CombustionChamberDesign.py kj66
python -m pytest tests -q
```

The standalone preset keeps V22's **4% prescribed total pressure loss**, a
**2-inch shaft tunnel**, 1.5 mm casing/liner walls and 2 ms bulk residence time.
The archived DP-2 full-cycle screen used **6% loss** and did not specify the
tunnel diameter or liner thickness. Those retained settings are assumptions,
not additional facts established by DP-2. The full-engine `config/seed.yaml`
remains the earlier design point; this change does not migrate the engine cycle.
The separate `core-engine` snapshot is not the edited working copy.

## What changed

- Inlet recovery multiplies ambient total pressure **before** the compressor
  pressure ratio. It does not change the compressor temperature rise at a fixed
  PR/efficiency. A supplied combustor inlet pressure/temperature pair takes
  precedence without another recovery correction. The RPM sweep carries the
  recovery in its design card so its DP-2 pressure matches the sizing run.
- `target_inner_hole_K=6.0` enables independent inner-feed area sizing. Starting
  with the legacy reference-area allocation, the model enlarges the inner
  annulus until local hole static head divided by annulus dynamic head meets
  the chosen minimum. The sizing and final rating use the same friction,
  entrance loss, actual diameters and discharge static pressure. Flame-tube
  flow area is preserved. Additional feed area increases the required casing;
  it does not consume the reacting volume or bypass the casing-fit check.
- `A_ref` remains the empirical sizing scale from the prescribed loss factor.
  Once the feed annulus is independently enlarged, it is not the sum of the
  packaged flow areas. Neither satisfying K nor fitting the casing predicts
  actual total pressure loss or validates the fixed hole Cd. Six is the
  inherited screening minimum and provides no additional design margin.
- DP-2 uses three dilution holes per vaporizer on the inner liner and four on
  the outer liner: **24 inner / 32 outer** for eight vaporizers. The inner holes
  grow to preserve the allocated flow. Each side can be set independently with
  `dil_holes_per_vap_inner` / `dil_holes_per_vap_outer`; the common legacy setting
  remains the fallback.
- The report checks all six main-hole rows in cold dimensions using the smaller
  face circumference of each liner. Minimum ligament is `max(2*t_cold, 1.5 mm)`.
  This is a circumferential, same-row screen; axial row placement, film-hole
  interference and drilling tolerances are not checked. The legacy
  `ligament_inner_mm` / `ligament_outer_mm` outputs keep their original hot,
  dilution-only convention for compatibility. The new `main_hole_ligaments`
  results are the checks printed in the report.
- `casing_wall_thickness_mm`, `liner_wall_thickness_mm` and optional
  `shaft_tunnel_wall_thickness_mm` separate the walls. Legacy
  `wall_thickness_mm` remains a fallback; the tunnel defaults to the casing
  thickness. The liner input retains the existing **hot-model** convention;
  cold CAD thickness is divided by the thermal expansion scale. Stress and
  ligament checks use the liner wall. No thinner stock was selected by default.
- The scoop report separates **approach velocity** in the outer annulus from
  **face velocity** through its pressure-sized opening. It reports both chosen
  targets and a streamtube capture-area estimate. The 35 m/s approach target
  and existing 22 m/s face target are advisory preferences. Suction can produce
  a face speed above approach speed; that discrepancy alone is not proof that
  the scoop cannot feed the vaporizer. The modeled air-path pressure allocation
  remains closed; scoop capture itself remains unvalidated.
- Primary-zone raw/capped temperature and vaporizer wall-temperature estimates
  are now visible beside the dome heat estimates. Thermal flags are explicitly
  described as uncalibrated advisory correlations. The warnings are not tuned
  away to make KJ66 pass, and the temperature cap is not treated as a prediction.
- Preset keys that correspond to `DESIGN_PARAMS` now take effect. Obsolete
  `target_tube_liq_vel` and `outer_loop_*` input controls are rejected with an
  explanatory error rather than silently ignored. Efficiency remains an input.

Omitting `target_inner_hole_K` preserves legacy annulus allocation, including
the KJ66 comparison and existing pipeline behavior. An explicit
`target_inner_annulus_vel` now sizes the actual area; specifying it together
with a K target is rejected. Neither option silently changes the feed split.

## Recomputed comparison

All rows use the same DP-2 inlet/fuel state, 152.4 mm casing, 50.8 mm tunnel and
1.5 mm walls. The old-geometry row disables K sizing and uses four dilution
holes per vaporizer on both liners. Other rows use K minimum 6 and inner/outer
hole multiples 3/4. Vaporizer count is still derived from circumference.

| Case | Casing required, mm | Outer / inner feed, m/s | Outer / inner hole K | Inner dilution ligament, cold mm | Length, hot mm |
|---|---:|---:|---:|---:|---:|
| Previous geometry, 4% | 126.8 | 14.9 / 58.8 | 48.82 / 1.62 | 1.48, fails | 133.2 |
| Corrected, 4% default | 130.3 | 16.5 / 38.6 | 39.60 / 6.00 | 4.24, passes | 133.2 |
| Corrected, 2.5% | 143.1 | 24.5 / 30.5 | 9.60 / 6.00 | 4.22, passes | 105.3 |
| Corrected, 2% | 149.8 | 33.8 / 27.3 | 2.79 / 6.00 | 1.95, fails | 94.2 |
| Corrected, 6% | 120.7 | 13.4 / 47.3 | 93.08 / 6.00 | 4.26, passes | 163.2 |

The cold ligament minimum is 2.97 mm because the retained 1.5 mm hot liner
corresponds to 1.485 mm cold in this prescribed-temperature model. The prior
1.79 mm ligament in the pasted review used the inner liner's larger, hot face;
the 1.48 mm above uses its smaller, cold face consistently with the new screen.

At 4%, casing fit margin is **11.03 mm per side**, L/D is **1.415**, residence
time is **2.00 ms**, and predicted dilution penetration is about **0.425 H** on
both sides. Fuel remains 23.72 kg/h. Main-hole and vaporizer branch budgets
close numerically. Scoop approach/face velocities are **16.5 / 37.4 m/s**,
requiring an estimated capture streamtube area **2.27 times** the opening area.
The scoop issue is exposed, not physically resolved by the software change.

At 2%, the larger circumference also changes the vaporizer count from eight to
twelve, so the hole count changes again. The outer K and cold inner ligament
both fail their screens despite the casing fit and near-35 m/s approach speed.
The 2.5% case is a useful comparison, not an adopted loss target. A larger
casing does not automatically lower loss in this prescribed-loss model.

## Verification and interpretation

`tests/test_combustor_dp2.py` exercises recovery and supplied-state precedence,
DP-2 thermodynamics, final-geometry K and mass/pressure budgets across feed
splits/tunnel sizes/loss targets, insufficient casing, velocity overrides,
separate walls through stress/CAD, asymmetric dilution flow conservation,
visible scoop/thermal diagnostics, invalid inputs and the RPM-sweep round trip.
The existing KJ66 and full pipeline regressions remain applicable.
Verification on September 26, 2026 after integrating the latest CORE main:
**163 tests passed**, including 31 new DP-2 regression cases. All 14 original
worksheets and the generated dependency check also passed.

The inlet convention follows [NASA's inlet performance description](https://www.grc.nasa.gov/www/k-12/airplane/inleth.html):
an adiabatic inlet preserves total temperature while losing total pressure.
For context, [NACA's air-entry-hole experiments](https://ntrs.nasa.gov/archive/nasa/casi.ntrs.nasa.gov/19930084890.pdf)
investigate discharge coefficients under parallel flow; they are not validation
of this reverse-flow geometry or the chosen K minimum. See
[model-review.md](model-review.md) for the broader model limitations.
