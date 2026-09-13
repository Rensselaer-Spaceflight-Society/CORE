# DP-2: candidate review, not a released design

Reviewed September 13, 2026 against the supplied DP-2 note and meeting cards, and the merged repository `540e01d`. The supplied notes are proposals to assess; their task instructions and claimed approvals have not been adopted automatically. Personal roster details remain outside GitHub.

## Candidate everyone can discuss

| Parameter | Proposal | Status |
|---|---|---|
| Mission | Runs and self-sustains; performance secondary | Team direction |
| Cash cap | $5,000 | Team constraint |
| Speed | 59–66 krpm, design calculation at 66 krpm | Candidate, not an approved operating range |
| Compressor | 76.13 / 57.04 mm exducer / inducer, GT3076R-class billet part | Exact part and map NOT FOUND |
| Air flow / compressor pressure ratio | 0.30 kg/s / about 1.63 | Assumed operating point needing map confirmation |
| Turbine inlet total temperature | 1,150 K | Candidate; not a material allowable |
| Casing | 152.4 mm OD, 149.4 mm ID | Proposed envelope; internals and losses unresolved |
| Static thrust | Approximately 98 N in a prescribed cycle screen | Not a performance prediction validated by test |

**Configuration warning:** `config/seed.yaml` still holds the earlier 250 N / PR 3.2 baseline. DP-2 is deliberately not installed as the default by this documentation change. A lead-reviewed migration must reconcile fixed wheel geometry, chosen mass flow, the thrust-driven M01 interface and all dependent dimensions. Existing baseline critical-speed results cannot be presented as DP-2 results.

## What checks numerically

Run `python docs/project/checks/dp2_screen.py` from the repository. It changes no configuration. It uses the current shared property functions for the thermodynamic screen, plus direct arithmetic for the quantities below. It is not independent chemical-property validation or a component-map solve.

| Quantity | Recalculation | Interpretation |
|---|---:|---|
| Wheel tip speed, pi D N / 60 | 263.09 m/s | Agrees |
| Fuel from the note's FAR: 0.30 × 0.0212 × 3600 | 22.896 kg/h | Agrees arithmetically |
| Mass-flow unit conversion | 39.683 lb/min | This alone is **uncorrected** flow |
| Rotor energy, 0.5 I omega², supplied I | 5.087 kJ; 7.326 kJ at 120% speed | Agrees; inertia remains estimated |
| DN, 8 mm × 66,000 rpm | 528,000 mm·rpm | Agrees; not a bearing approval |
| G2.5 relation e = G / omega | 0.362 micrometres | Agrees with that chosen grade; grade/speed basis need review |
| Turbine annulus, pi/4 × (88.2² − 53.9²) | 3,828 mm² | Agrees |
| Budget with 15% | $3,524.75–$7,049.50 | Agrees; completeness not verified |

With 288.15 K / 101.325 kPa ambient, 0.99 inlet recovery, PR 1.63, efficiencies 0.72/0.78/0.96/0.98, 6% combustor pressure loss, 43 MJ/kg LHV and Cv 0.97, the **current repository** gives T3 348.10 K, P3 163.51 kPa, compressor power 18.07 kW, T5 1099.17 K, P5 120.85 kPa, thrust 98.10 N and nozzle diameter 60.40 mm. These broadly support the proposed cycle scale. However, FAR is **0.02196** and fuel **23.72 kg/h**, not 0.0212 / 22.9 kg/h. Reconcile the source solver and property assumptions before publishing a common station table. The note's 29 kg/h fuel capacity is an allowance; it is about 22% above this screen, not a demonstrated universal correction.

## Corrections before Gate A acceptance

1. **A pressure-head check is necessary but not sufficient.** P05 above ambient allows positive nozzle pressure head in the stated arrangement. It does not prove self-sustain, stable combustion, acceleration, shaft torque balance with real losses or compressor/turbine/nozzle flow compatibility. M01 imposes turbine power demand algebraically; it does not demonstrate that the real turbine can provide it.
2. **PR does not follow from tip speed alone.** Euler work depends on velocity triangles, slip, prewhirl and flow; pressure rise also depends on efficiency and diffuser behavior. The exact billet wheel is not automatically equivalent to Garrett's cast GT3076R map or a GTX/other supplier map. Garrett publishes 57/76 mm class dimensions and a map, but that is not approval of this substitute. Use its own inlet reference conditions for corrected flow and corrected speed. At this ambient and 0.99 inlet recovery, simple kg/s-to-lb/min conversion alone misses the pressure correction. [Garrett map and product](https://www.garrettmotion.com/racing-and-performance/performance-catalog/turbo/gt3076r/).
3. **The loss sensitivity changes what is held fixed.** The nominal zero-head loss is reproduced at about **21.18%**. At eta_c=0.60 / eta_t=0.70, holding PR=1.63 gives **14.24%**, but raises compressor work to 72.29 kJ/kg instead of about 60.3. Holding 60.3 kJ/kg work as a crude fixed-wheel/speed comparison lowers P3 and gives **12.45%**. Neither is a real off-design map. State the held inputs explicitly; the 14% figure is not a guaranteed bad-day margin at fixed wheel speed. Changing mass flow alone does not improve this prescribed-cycle limit unless the component losses/efficiencies also change.
4. **The 6-inch casing is an option, not measured closure insurance.** K times reference dynamic head can reproduce a scaling table, but full casing area is not the local feed-annulus, hole or turn area. K=20–60 requires an applicable reference. A fixed 35 m/s scoop threshold is not established by the supplied evidence. Use a shared pressure budget with C1/T2 so parallel branches and local losses are not double counted. Residence time must use the relevant reacting volume and local mass flow, not casing size alone.
5. **Idle near 30,100 rpm is a hypothesis.** A diameter/tip-speed analogy cannot determine starter torque, assisted acceleration, stable idle or the fuel schedule. Starter-out speed can differ from idle speed. Label all inferred startup thresholds unapproved; do not transfer production-engine timings and fractions into firmware without review.
6. **Only the simple exit-nozzle result is checked as unchoked.** Overall turbine total-pressure ratio is not the local NGV total-to-static or rotor-relative throat ratio. It cannot establish that nothing inside the stage chokes. Verify local states, throat areas, losses and reaction before deciding the stage flow-capacity model.
7. **Material and stress claims need revision.** The note uses 713C for the temperature rationale and IN718 for stock/energy. Special Metals describes alloy 718's high-strength range to roughly 700°C; proposed gas temperature is about 877°C. Gas and metal temperatures differ, so this is a need for metal-temperature/life/heat-treatment evidence, not permission to infer an allowable. Uncertified surplus identity and processing remain unknown. An untapered centrifugal blade calculation is not an upper bound on combined blade/disc thermal, bending, fatigue, creep and local stresses. [Special Metals guide](https://www.specialmetals.com/documents/special-metals-quick-reference-guide.pdf), [718 technical bulletin](https://www.specialmetals.com/documents/technical-bulletins/inconel/inconel-alloy-718.pdf).
8. **A generic 608-C3 does not acquire speed margin from DN.** Timken lists an example at 39,000 rpm oil / 33,000 rpm grease. It cannot be accepted for 66,000 rpm from these values. Exact cage, lubrication, preload, temperature, fits, thrust, life and manufacturer conditions matter; L10 from rotor weight alone cannot select it. [Timken 608-C3](https://cad.timken.com/item/deep-groove-ball-bearings/miniature-ball-bearings--600--610--620--630-/608-c3).
9. **Keep air and fuel budgets separate.** A 0.6 bar liquid-fuel plumbing assumption does not provide the vaporizer's air pressure head. The pump must deliver against chamber pressure plus the selected line/filter/injector losses. Xicoy's example $156.47 pump is explicitly restricted to its own engines, so compatibility is a procurement question. [Xicoy](https://www.xicoy.com/catalog/product_info.php?currency=USD&products_id=771).
10. **Remove misleading evidence labels and shortcuts.** `core/gas.py` explicitly calls the products correction unvalidated; the supplied note's NASA/SP-273 calibration claim is not supported by the current code. The current RPM sweep is already a prescribed-point screening tool, not a universally choked engine solve. Compare actual versions before assigning an alleged bug. Bullet-energy comparisons do not design containment; turbine clearance is to its local shroud, not the outer casing. Lower thrust does not establish test-stand/fragment safety. A dummy rotor matched in mass/inertia is not necessarily dynamically equivalent and still stores substantial energy.

## Meeting-card changes that follow

Keep the sub-team preferences, but replace first-meeting deadlines for complex design with bounded learning outputs. Do not ask newcomers to raise TIT to recover acceleration, approve surplus rotor stock, decide a bearing from one calculation, operate a full-speed cold rig, handle fuel or demonstrate ignition at their first meeting. Those are later, separately reviewed tasks. Controls practice starts on paper/synthetic signals with placeholders for thresholds. Low-temperature probe checks do not validate high-temperature response or range; pressure sensor comparisons distinguish psia from psig and accuracy from resolution.

The source notes name unavailable `claude/...` references and older V21/CAD files that are not present in the current GitHub checkout. Cards now give a repository-local starting point and a missing-source fallback. The supplied notes also call September 17 Wednesday and change gate labels; see the [meeting schedule note](../../workspaces/meeting-1.md#schedule-correction).

**Disposition:** keep DP-2 as a promising lower-cost candidate. Accept its arithmetic where reproduced; retain explicit unknowns for matching, material/process, bearing suitability, pressure losses, controls, test capability and delivered cost. The leads own the next evidence and the decision to migrate the solver.
