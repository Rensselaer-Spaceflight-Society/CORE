# PD-1 component reviews

PRELIMINARY - NOT FOR MANUFACTURE. One record per component or purchased assembly, in the order of the
contract (identity → disposition). Machine-readable parameters with units, basis, source, tolerance and status:
`results/pd1-jm85/cad/cad_bundle.json` (186 parameters, 23 interfaces). Run values: `results/pd1-jm85/SUMMARY.md`.
"Ready for preliminary CAD" means the team can model it now without inventing a mating dimension; it does
not mean released.

---

## IN-01 Inlet bellmouth, screen and starter bracket
- **Identity:** make; 6061 sheet bellmouth (I01) + 304 mesh (I02); owner: assembly record / M29.
- **Inputs:** compressor inducer 57.04 mm; corrected flow 25 lb/min at design.
- **Design:** 25 mm long bellmouth, 8 mm lip radius, ahead of an 8 mm inlet duct in the housing; starter on a 3-strut bracket in the inlet. Inlet loss allowance 1 % at 0.20 kg/s corrected, ∝ flow² (assumption; includes screen and strut blockage).
- **Interfaces:** CH-01 inlet face (spigot); IF-STARTER (cone on compressor nut, one-way clutch).
- **Manufacture:** spun/formed or machined; screen clamped. **Verification:** loss not measured. **Cost:** I01 $25, I02 $15, I04 clamps.
- **Disposition:** envelope ready for CAD; strut count/size and screen open area need a team choice (affects the 1 % allowance; 2 % evaluated: +15 K T04).

## CW-01 Compressor wheel (purchased) and characteristic
- **Identity:** buy, R01; record `data/components/compressor_gt3076r_56trim.yaml`; map `data/maps/gt3076r_compressor.yaml`; software M10 (fixed-wheel mode), `core/compressor_map.py`.
- **Inputs:** ISA SLS inlet; N 56–68 krpm.
- **Design (fixed):** inducer 57.04, exducer 76.13 (extended tip 79.22), exit blade height 5.75, super-back 2.36, bore 5.99 mm, 11 + 0 blades (supplied). Hub diameter 19 mm, axial length 32 mm, mass 0.075 kg, Ip 3.2e-5 kg m² are **assumptions**.
- **Characteristic:** Garrett GT3076R map (stock 6+6 cast wheel, Garrett housing). Digitized speed lines 55,864–144,956 corrected rpm; efficiency anchors from contour crossings; Garrett's 58 % choke convention; reference 545 °R / 28.4 inHg (secondary source). Medium-confidence efficiency domain ≤ 100,452 rpm. No extrapolation. At design: PR 1.486, η 0.763, β 0.662, SM_flow 0.58, blade work coefficient 0.60, inducer relative Mach 0.65.
- **Interfaces:** IF-CW-SH (bore on the 6 mm seat, clamped by M6 nut against the seal sleeve; the 6 mm seat is an envelope — the finished seat diameter and fit are **unresolved** until the 5.99 mm bore is measured), IF-CW-DF (0.40 mm backface clearance), shroud contour to CH-01 (0.30 mm), IF-ROT (rotation direction must match the turbine).
- **Materials:** forged aluminium, grade unconfirmed. **Verification:** map digitization checks; substitution offsets in robustness (η −0.04: +35 K; flow ±5 %: ≤ 8 K).
- **Cost:** R01 $150 nominal / $250 adverse; billet listing showed sold out.
- **Disposition:** dimensions ready for CAD except shroud contour (scan the wheel). **Decision needed:** billet 11+0 vs stock 452708-0001 (map applies to the stock wheel).

## CH-01 Compressor housing (shroud + diffuser cover)
- **Identity:** make; 6061 block 2×6×6 in (R06).
- **Design:** inlet duct Ø57.64 mm (inducer + 2×0.30), shroud following the measured blade-tip profile, diffuser cover face at x = −8.11 mm, OD = casing OD 152.4 mm. Envelope only until the wheel is scanned.
- **Interfaces:** IN-01; DF-01 (cover over the vane channels, axial stack x −8.11 → −2.36 mm); CS-01 register.
- **Manufacture:** lathe 2 setups; shroud from wheel scan; soft jaws. **Disposition:** envelope ready; contour blocked by wheel scan.

## DF-01 Vaned diffuser / backplate (with front bearing pocket)
- **Identity:** make; 6061-T651 ½ in plate (R07); `core/diffuser.py`, M11.
- **Design:** vaneless ratio 1.08 (LE Ø82.2 mm, free-vortex LE flow angle 57.9° from radial — 1.5° less than before the blade-work correction of 2026-10-04), 19 straight-centreline channels (coprime with 11 blades), throat Mach 0.70 → throat width 5.84 mm (81 % of the 7.2 mm the LE pitch allows), exit Ø126 mm, axial width 6 → 9 mm, area ratio 3.17, in-plane divergence 10.4°, exit Mach 0.17. Floor flush with the wheel hub disc (x = −2.36 mm). Seal bore Ø13.2 mm; front bearing pocket recessed 6 mm; OD 149 mm spigot.
- **Loss accounting:** none subtracted (the map covers wheel + a diffuser). Turn/deswirl estimate 1.0 % (K 0.5 × exit head, with axial deswirl vanes in the bend — assumption) vs 2.0 % ledger allowance.
- **Interfaces:** CW-01, CH-01, BC-01 (pocket), TU-01 (rear spigot), CS-01 (rim, 12 × M4).
- **Manufacture:** one-setup turning of spigot/seal/pocket (concentricity ≤ 0.02 mm), rotary-indexed milling of channels with ⅛ in cutters (N05), floor ramp for width growth; deswirl vanes as a fabricated ring. **Disposition:** ready for preliminary CAD; recovery/turn loss needs CFD or a rig survey.

## CB Combustor (dome CB-01, liners CB-02/03, discharge cones CB-04/05, vaporizers VP-01, igniter IG-01)
- **Identity:** make; 316/316L 0.060 in sheet (C01), ¼ in tube (C03), needle tube (C05); M20 + `core/combustor.py`; layout `core/postprocess.combustor_layout`.
- **Inputs:** combustor air 0.1969 kg/s (compressor air less 2 % tunnel leakage), P031 146.3 kPa, T03 333.4 K, T04 848.0 K, fuel 9.53 kg/h (FAR 0.0134), η_b 0.96 (assumed).
- **Basis comparison (same inlet state):** at PD-1 flow every loss from 3 % to 6 % fails the dilution-penetration screen; 6 %/2 ms is infeasible (L/D > 2). Both 2.5 %/1.4 ms and 2.5 %/2.0 ms pass every existing screen. **Chosen:** 2.5 % / 1.4 ms, because the shorter liner shortens the bearing span. Prescribed loss is a sizing basis, not a prediction; actual 4–8 % evaluated in robustness. **Independent check (2026-10-04):** with the code's uniform-liner-static assumption every hole discharges to the liner exit static, but the liner's own exit dynamic head (ρ4u4² ≈ 4.9 kPa) is comparable to the 6.0 kPa hole drop; a 1-D momentum balance makes the sized holes consistent with about 5 % total-pressure loss, not 2.5 % (`core/combustor.py` liner model; team-owned, not changed). The 4 % and 6 % robustness cases cover the cycle effect.
- **Geometry (cold, 293 K):** outer liner OD 102.95 / ID 99.90 mm; inner liner OD 72.64 / ID 69.59 mm; length 85.8 mm (L/D ≈ 1.0); wall 1.524 mm stock (rated at stock, hot-model conversion inside M20); required casing OD 122.4 mm (15 mm/side margin in the 152.4 mm casing); tunnel 50.8 × 1.651 mm stock.
- **Holes (cold):** primary 16 out Ø3.54 / 16 in Ø3.04; secondary 16 / 16 (Ø4.87 out); dilution **32 outer Ø5.64 / 24 inner Ø5.59**; film 4 rows. Rows: primary 0.55 L_pz, secondary L_pz + 0.5 L_sz, dilution L_pz + L_sz + 0.4 L_dz; film rows at 4 mm, zone boundaries and 0.85 L_dz. Clocking: vaporizer k at 45 k°, primary/secondary ±¼ pitch, dilution half-step offset; inner/outer dilution counts differ (staggered jets). Coordinates in `cad_bundle.json → patterns.combustor_rows`.
- **Screens (existing):** hole K outer 108 / inner 8.5 (≥ 6), J primary 21, dilution penetration 0.67 (≤ 0.75), residence 1.4 ms, dome flux 377 kW/m² (placeholder limit), liner wall 693 K (prescribed 0.72 T04 rule, uncalibrated). **Independent check:** the penetration pass depends on two offsetting definitions in `core/combustor.py` (geometric hole diameter with the area-mean jet velocity, and a fixed 1200 K mainstream). With Lefebvre's effective jet diameter d·√Cd and U_j = √(2ΔP/ρ3) at 1200 K the ratio is ≈ 0.89 (fails 0.75); with an energy-balance mainstream (~1717 K) it is 0.56–0.74. Treat the screen as open until the combustor owner fixes the definitions.
- **Layout checks:** all-row (axial + diagonal + circumferential) ligaments ≥ max(2t, 1.5 mm); bend exclusions pass; **weld seam:** see run checks — with a 3 mm seam band the dense dilution rows on rolled sheet cannot be cleared (remedy: drawn tube for the outer liner, narrower seam, or a clocked gap; film holes in the seam band are omitted with film area preserved).
- **Vaporizers:** 8 J-sticks, model OD 6.17 / ID 4.97 mm (stock ¼ in needs rerating), crimp and scoop from the air-path allocation; J-bend (CLR 1.5 OD) too tall for the 13.4 mm combustion gap radially → bend plane circumferential (fits between sticks). Scoop capture ratio 3.7 and inner-wall temperature estimate ~1400 K are advisory warnings (coking/structural risk) from uncalibrated correlations.
- **Igniter:** M10 boss through casing + outer liner, primary zone, midway between vaporizers 0 and 1.
- **Supports/expansion:** liners slip onto the NGV outer ring/hub ring (located at the rear); dome on 3 radial pins in casing slots (axial growth ~1 mm taken at the front); fuel needles enter sticks with clearance.
- **Verification:** branch mass residuals ~0; pressure budgets close; layout tests. **Not established:** ignition, lean blowout, vaporizer behaviour, coking, exit pattern factor, liner temperature, creep.
- **Cost:** C01 $110 (adverse $130), C03, C05, C06–C11.
- **Disposition:** ready for preliminary CAD (envelopes, rows, clocking, stick rule). Before release: cold-flow split test, ignition/stability tests, thermal analysis, seam route decision, stock rerating of sticks.

## NG-01 Nozzle guide vanes (purchased casting, CORE-finished)
- **Identity:** buy + finish, R03; record `ngv_jetmax_ngv85.yaml`.
- **Design (supplied envelope):** hub ring OD 55.4 / bore 48, outer ring OD 92, flange OD 104, vane ring height 20 mm then 14 mm shroud/flange section around the rotor. **Assumed:** vane tip Ø87, chord 12 mm, ~20 vanes, exit angle 65° → throat 1494 mm².
- **Rating at design:** throat Mach 0.46, flow 74 % of choke; not choked across 56–68 krpm in any single-parameter robustness case (max 0.84 of choke, at the 72° exit angle); the smallest NGV throat the model accepts at 68 krpm is ≈ 700 mm² (below it the NGV comes within 5 % of choke).
- **Finishing:** measure throat first; shroud bore Ø85.70 +0.02/0 concentric with hub bore; flange faces; 12 × M3 on PCD 98 (hot fasteners N03; holes on the 6 mm land between the Ø92 outer ring and the Ø104 flange OD, checked in the stack).
- **Interfaces:** CB-04/05 slip fits; CS-02 rear cover on the flange front face; TR-01 tip clearance 0.35 mm cold, NGV-rotor gap 2 mm. **Hub (IF-BC2-NG): unresolved.** The blank's Ø48 pocket is blind (11 mm deep from the front face, then a centre web and a conical boss reaching aft into the rotor's shroud section). The stack's rear bearing sits in the pocket but the spacer, the Ø14 turbine boss and BC-02 pass through the web zone, so the finished passage and the rear-bearing support path are a team decision (options in manufacturing-and-budget.md §2).
- **Materials:** "high-temperature alloy steel, to 1000 °C" (supplier words); grade unknown.
- **Disposition:** envelope ready for CAD; **vane geometry must not be modelled from guesses** — measure or obtain supplier CAD.

## TR-01 Turbine wheel (purchased, finished)
- **Identity:** buy, R02; record `turbine_jetmax_tw85.yaml`; `core/turbine_rating.py`; M13 fixed mode; M33.
- **Design (supplied):** tip 85, hub 55, bore 9.99 ±0.005, boss Ø14 × 19 (8 mm one side), rim width 7.5. **Assumed:** ~30 blades, rotor exit angle −58°, blade sections (root area 9 mm², mass 0.86 g), wheel mass 0.17 kg, Ip 8.4e-5 kg m².
- **Rating:** Soderberg + aspect/Re corrections + tip leakage (K_tip 2) + incidence model; η_tt 0.846 at 68 krpm with the rotor Reynolds number 2.0e4 — at 56–66 krpm it is 1.6–1.9e4, below the code's (unsourced) 2e4 validity flag, and Soderberg's basis is 1e5. The value is probably optimistic; the model still matches at 68 krpm with losses ×5.8 (η_tt ≈ 0.51, T04 1150 K). Tip speed 303 m/s at 68 krpm; AN² 1.5e7; blade-root centrifugal speed margin 1.93 vs an assumed 620 MPa allowable (blade only — not a disc/burst/life assessment).
- **Interfaces:** IF-SH-TR (the nominal 9.99 ±0.005 mm bore on the 10.000 mm seat is a 5–15 µm interference; M8 nut clamp proposed; **fit, assembly method and hub stress unresolved**), tip/axial clearances, IF-ROT.
- **Disposition:** ready for CAD as an envelope; blade profiles, alloy and speed rating are supplier items.

## EX-01/02 Exhaust nozzle and tailcone
- **Design:** conical outer wall from Ø85.7 (shroud) to Ø54.0 over 80 mm (half-angle 11.2°), tailcone Ø55 → point over 40 mm; annular area falls monotonically to the exit (throat at exit — checked); unchoked at all rated speeds.
- **Interfaces:** flange to the NGV flange rear face (shared hot bolts); EGT boss at nozzle entry.
- **Sensitivity:** ±3 % area → ∓11 K T04; make 54 mm and 50 mm nozzles for trimming after the throat is measured (trim table in SUMMARY).
- **Disposition:** ready for CAD (`sections.nozzle_contour`).

## SH-01, SL-01/02 Shaft and rotating stack
- **Design:** stepped 4140: M6 front thread, Ø6 compressor seat, Ø6 seal-sleeve seat (sleeve OD 13), Ø10 k5 front journal, Ø13 body, Ø10 k5 rear journal, rear spacer (OD 13.5, 4 mm), Ø10 turbine seat, M8 rear thread; fillets ≤ 0.4 mm; total length and stations in `assembly_stack.json`. Clamp chains: front nut → wheel → sleeve → front inner ring → body shoulder; rear nut → turbine → spacer → rear inner ring → body shoulder.
- **Checks:** torque 1.29 N·m at 68 krpm; peak von Mises at the 6 mm seat ~85 MPa (Kt 2.0/1.6, consistent with the R0.4 fillet at r/d 0.067, D/d 1.67) vs 0.5 × 655 MPa; alternating bending ≪ corrected endurance; body shoulder 13 ≥ typical 12.5 mm abutment (verify supplier). **Not covered:** the M6/M8 threaded ends (minor diameter ~5.1/6.8 mm) may carry part of the wheel torque through the clamped nut (49.6 MPa nominal on the M6 minor diameter if all of it did) plus the clamp preload — an `unknown` check now says so.
- **Disposition:** stepped profile ready for preliminary CAD; the compressor and turbine **finished seat diameters are unresolved** (measured bores and approved fits). Thread hands follow rotation (IF-ROT). Grinding/lapping capability needed.

## BR-01/02, BC-01/02 Bearings, sleeve, carrier, preload, lubrication
- **Design:** 10 × 26 × 8 hybrid angular contact both ends; front locating (J6 in a steel sleeve on two O-rings in the backplate pocket); rear floating (G6 in a stainless carrier with a ~40 N wave spring and an O-ring soft mount). **The carrier's location in the NGV hub is unresolved** (blind Ø48 pocket with a centre web; `BC02_SPIGOT_OD` is envelope only). DN 0.68e6 at 68 krpm. Lubrication: fuel + 5 % oil mist (model-jet practice) — supplier acceptance required. Friction model (SKF/Palmgren, f0 1.7, ν 8 cSt): 98 W for both at 68 krpm (×3 evaluated: +16 K).
- **Axial load:** M31 estimate ~41 N net forward at design (crude; sign and magnitude need a pressure-cavity analysis); the locating front bearing must carry it; spring preload 40 N.
- **Disposition:** BR-01/BC-01 ready for preliminary CAD; **BC-02 waits for the NGV hub decision**. Supplier speed/preload data and measured mount stiffness/damping are release items.

## Rotordynamics (whole rotor)
- **Model:** `core/rotor_fe.py` (benchmarked), stack from M29, soft supports k = 2 N/µm, c = 1000 N·s/m per bearing (assumed), G2.5 unbalance.
- **Result** (`rotordynamics.json`): crossings 18,264 rpm (damping ratio 0.87) and 19,918 rpm (0.58) are rigid-body modes on the soft supports, crossed during starting and heavily damped (not resonances: the forced response has no peak there); the first bending crossing is at 88,024 rpm (0.04), 29.4 % above 68 krpm with the recessed front bearing (20 % required for all criticals). Mesh-converged to < 1 rpm (12/6/3 mm elements); reproduced to ≤ 0.05 % by an independent lumped-beam model; turbine orbit at G2.5 ≈ 0.34 µm against 1/3 of the cold tip clearance.
- **Sensitivity:** at 1 N/µm the crossings are 8.7k / 87.6k rpm; at 5 N/µm they are 35.1k / 49.7k / 89.3k rpm — the 49.7k mode is inside the 20 % band below 56 krpm. Independent sweeps: separation falls below 20 % above ≈ 3.98 N/µm (3.86 undamped), and — at 2 N/µm — above ≈ 2.6 kN·s/m damping (bending crossing 80.8k rpm at 3 kN·s/m, toward the 77.8k rigid-bearing limit). **Mount stiffness and damping must both be measured** before committing the O-ring design.
- **Not established:** support coefficients, clamped-joint stiffness, gyroscopic effects of the real wheel inertias, damping — rotor modal test and supplier data required.

## TU-01, CS-01/02 Tunnel, casing and rear cover
- **Design:** tunnel 2 in × 0.065 in 316 tube from the backplate spigot to a slip joint in BC-02 (does not fight the casing load path); casing 152.4 × 1.524 mm rolled 316 with seam weld from the backplate rim to the rear cover; rear cover (ID = outer ring + 1 mm) bolted to the NGV flange front face (12 × M3 + gasket).
- **Checks:** casing hoop stress ~2.4 MPa (pressure vessel only — **not fragment containment**); outer liner elastic buckling margin ~1300 (knockdown 0.5; creep buckling open); differential growth: NGV–rotor gap opens by ~0.05 mm hot (≈ 0.08 mm with the stack-faithful path; sign checked by hand), rear bearing float ≪ spring travel (≈ 0.12 mm if the carrier is held at the NGV and grows forward; still < 0.5 mm, but the carrier path is open).
- **Disposition:** TU-01, CS-01 and CS-02 ready for preliminary CAD; the tunnel's rear slip joint into BC-02 waits for the NGV hub decision.

## FU Fuel system
- **Requirement:** max 9.5 kg/h in range → pump 16.2 L/h including 30 % margin and 5 % lube flow; differential 1.57 bar (combustor 0.45 bar(g) + needles 0.6 + line/filter/fittings/check/solenoid); liquid budget separate from vaporizer air budget. 8 laminar needle restrictors ~0.5 mm ID (length from `systems/fuel_budget.json`).
- **Hardware:** JetCat-class pump (F01, compatibility unproven), NC solenoid (F02), manual valve, filter, check valve, Tygon line ~2 mm bore.
- **Disposition:** requirements defined; pump curve and distribution test needed.

## ST Starter, electrical, instrumentation, controls
- **Starter:** bound 0.4–1.2 kW at 20–30 krpm (compressor power ∝ N³ from the lowest matched point — extrapolation), rotor Ip 1.2e-4 kg m²; brushless 500–800 W class + ESC; cone on the compressor nut through a one-way clutch. Light-off and cut-out speeds unknown.
- **Electrical:** 12 V continuous ~3.6 A (pump + solenoid) within the 5 A buck; starter peak from the 3S LiPo.
- **Instrumentation:** `data/systems/signals.yaml` — N (timer capture, 1 pulse/rev), EGT (K 3 mm at nozzle entry; EGT ≠ TIT; model T04 − T5 ≈ 50 K), P03 (0–30 psig recommended), PF, T03, thrust, fuel mass; ranges, latency and invalid-data actions defined.
- **Controls:** `core/controls_sim.py` synthetic state machine with hardware outputs disabled; thresholds illustrative only.
- **Disposition:** requirements and interfaces defined; firmware and hardware selection remain team work.
