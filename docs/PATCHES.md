> **Historical snapshot, superseded September 2026.** Numerical claims and validation statements below describe the pre-audit model. Use [current model review](model-review.md), [workflow](workflow.md) and [README](../README.md) for current guidance.

# Combustor patches: V21 → core/combustor.py

Fourteen changes to the team's `V21_CombustionChamberDesign.py`. Every one is
marked `# ===== PATCH Pn =====` at its site in `core/combustor.py`, and
`self.res['patches_applied']` carries the list at run time.

Numbers below are for the KJ66 preset unless noted. Reference is Lefebvre &
Ballal, *Gas Turbine Combustion*, 3rd ed. (2010); equation and section numbers
were checked against the text.

---

## Changes that move a dimension

### P2 — thermal growth was a factor of two out

V21 computed `alpha * (OD/2) * dT` — a change in **radius** — and subtracted it
from a **diameter**. It also used turbine inlet temperature for the metal
temperature, but a liner film-cooled on both faces runs far cooler. Two errors
in opposite directions that happened to look plausible together.

| | V21 | patched |
|---|---|---|
| thermal offset, outer liner | 0.691 mm | 0.839 mm |
| basis | Δradius at TIT | Δdiameter at 0.72·TIT |

Cold build dimensions changed. Anything already cut to V21 numbers is wrong.

### P5 — the feed-split solve was degenerate

V21 solved for the outer/inner flow split that equalises path pressure loss.
But the annuli were *sized* to hit target velocities, so both velocities were
pinned regardless of the split. The residual was flat across the entire search
range and the solver slid to whichever rail it started nearest:

```
f_outer   0.20   0.30   0.40   0.50   0.60   0.70   0.80   0.90
residual  4084   1077     14     -2     11      0      7     11   Pa
```

That is why it reported 0.516 for the 6-inch case and 0.371 for the KJ66 from
what is essentially numerical noise — and neither was ever fed back into the
geometry those splits were supposed to size.

Reformulated: the flow split is a design choice; what the pressure balance
actually determines is the inner annulus **area**, equivalently its velocity.
`dP_inner` is strictly monotonic in `v_inner`, so there is exactly one solution.

**Consequence worth noting:** the KJ66 preset asserted
`target_inner_annulus_vel = 20.0` as an explicit empirical calibration. With
that input removed, the reformulated balance **predicts 23 m/s**. A hand-tuned
constant became a model output.

### P14 — the combustor had no intrinsic size

V21 sized the liner by subtracting the feed annuli from a **given** casing bore,
so the combustor expanded to fill whatever casing it was handed. Invisible while
the casing OD was a fixed input. Fatal once the casing became computed: the
liner grew to fill the casing, the casing grew to contain the liner, and the
pair diverged monotonically (183 → 187 → 192 → … → 225 mm and climbing).

Reformulated to Lefebvre's actual method (Sec. 4.3, Eqs. 4.1–4.6): the reference
area comes from the pressure loss the combustor is allowed, which is an absolute
size set by mass flow and inlet state. Geometry then stacks outward from the
shaft tunnel and the required casing bore falls out as an **output**.

```
A_ref = mdot / (rho3 * V_ref),   V_ref = sqrt(2 * (dP/K) / rho3),   K = 20
```

KJ66: needs a 90.8 mm casing, given 110 mm, 9.6 mm/side margin.

---

## Quantities computed and then discarded

### P1 — fuel energy balance

V21: `m_fuel = m_air * cp(T_mean) * (TIT - T2) / (LHV * eta * hlf)`. A single
mean cp, and the fuel mass left out of the product stream.

Replaced with a real enthalpy balance carrying the fuel mass, solved by
`core.gas.far_for_T4` and verified by round trip.

| method | FAR | vs air tables |
|---|---|---|
| V21 as written | 0.01580 | −3.2% |
| V21 cp fit, enthalpy form | 0.01609 | −1.4% |
| **air tables (correct)** | **0.01631** | — |
| constant cp with 0 K datum | 0.01904 | **+16.7%** |

**Correction to the first review of this code:** it claimed V21 was 21% low.
That was wrong. It compared V21 against the last row — a constant-cp cycle model
that was itself 17% high. V21 was the better of the two, and the real bug was in
the reviewing code. `core/gas.py` now serves both.

### P3 — residence time

V21 sized the chamber length from combustion air only but reported residence
time from air plus fuel. Same nominal quantity, two mass flows. You asked for
2.00 ms and got 1.73. Both now use the total flow through the chamber.

### P4 — combustion efficiency

V21 hard-coded `comb_eff = 0.96` in the fuel balance while `combustion_loading()`
separately computed 0.999 from the loading parameter and discarded it. Now
iterated to a fixed point in an outer loop. This is also why the off-design
script disagreed with V21 by 3.9% at the point its docstring promised would
"reproduce V21 exactly" — and it now agrees to 0.01%.

### P10 — pressure drop verified against the holes it produced

`target_pressure_drop` was an assertion nothing checked. The holes are sized
*from* it, so re-deriving it from the resulting hole areas closes the loop. If
they disagree, the orifice model and the assumed drop are inconsistent and every
hole diameter is wrong. Currently closes to within 1.3%.

---

## Wrong member of the right correlation family

### P6 — jet penetration used the single-jet form

`1.15·√J·(d/H)` is exactly Lefebvre Eq. 4.19, correctly attributed — but Eq.
4.19 is for a **single** jet. Every row here has 12–24 holes, which is Eq. 4.20:

```
Y_max = 1.25 * d_j * sqrt(J) * [mdot_g / (mdot_g + mdot_j)]
```

The mass-flow term is the blockage effect of the jets accelerating the
mainstream. KJ66: penetration moves from 0.854·H to 0.552·H — enough to flip the
over-penetration flag. Both forms are reported so the change is auditable.

### P7 — dome heat flux used a flat-plate correlation

`Nu = 0.037·Re^0.8·Pr^0.33` with the hole diameter as length scale is a flat
plate correlation, not an impingement one — no standoff ratio H/D, no radial
position r/D, both first-order for an impinging jet.

The evidence it was wrong: it returned 1240–1655 kW/m² across the *entire*
design space and never once cleared its own 600 kW/m² "critical" threshold —
including 1240 kW/m² for the real KJ66, an engine thousands of people have flown
for twenty-five years. **A check that always fails is a constant, not a check.**

Three methods now computed, all three reported:

| method | KJ66 convective flux |
|---|---|
| Lefebvre Sec. 8.5 liner convection (reported default) | 219 kW/m² |
| Martin 1977 single-jet impingement | 1005 kW/m² |
| V21 original flat plate | 1114 kW/m² |

**This is not resolved.** Lefebvre's is reported because it is what the cited
reference recommends for this geometry, but nobody has defended a choice in
writing. `m24_combustor_checks` is `status="stub"` for this reason alone.

---

## Labelling and bounds

### P8 — the efficiency citation was wrong
V21 cited "Lefebvre GTC 3rd Ed. Table 5.1" for the η-vs-loading fit. Table 5.1
(p. 186) is the **lean-blowout** constants A and B for Eqs. 5.27/5.29. The real
relation is Figs. 5.2 and 5.4 and it is a chart, not a table. The fit shape is
defensible; the source was not there.

### P9 — chamber length had no ceiling
At 0.9 kg/s in a 6-inch casing V21 silently returned a **372 mm** combustor —
longer than the whole engine. `L_D_max = 2.0` now raises.

### P11 — `phi_primary_actual` is not actual
Primary air is *defined* as `m_fuel·stoich/phi_target`, so this can only echo
its input. It read exactly 1.600 at every turbine inlet temperature, which is
the tell. Renamed honestly and flagged.

### P12 — the "turbine inlet" plane was the combustor discharge
V21 labelled `exit_conditions` as turbine inlet and derived an available turbine
enthalpy from it. It is the combustor discharge, upstream of the nozzle guide
vanes — whose throat is 3.5× smaller and is what actually sets turbine inlet
Mach. The NGV throat area is now reported alongside so the difference is visible.

### P13 — the discharge coefficient was never checked
Lefebvre Fig. 4.3 shows Cd is a function of K, the ratio of hole dynamic
pressure to annulus dynamic pressure, and states K should not fall below 6
upstream of the primary holes. Cd = 0.60 corresponds to K ≈ 8–15. V21 never
computed K, so it could not know whether its own Cd was appropriate.

It now does — and the check **forced a design change**: at the textbook
`liner_area_frac = 0.66` the annuli run at 62 m/s and K comes out at 2.3. The
seed value is now 0.45, which is where K just clears 6. See the trade table in
`config/seed.yaml`.
