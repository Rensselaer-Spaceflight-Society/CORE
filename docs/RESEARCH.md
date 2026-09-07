> **Historical snapshot, superseded September 2026.** Numerical claims and validation statements below describe the pre-audit model. Use [current model review](model-review.md), [workflow](workflow.md) and [README](../README.md) for current guidance.

# Research notes

Two research passes back this repo. Both were done against primary sources with
explicit "could not verify" markers where nothing was found. Keep those markers
— an honest gap is more useful than a confident guess.

---

## Part 1 — KJ66 reference data

Machine-readable version with per-value confidence levels:
`config/kj66_baseline.yaml`. Used as the regression oracle in
`tests/test_kj66.py`.

### Performance

| Quantity | Value | Confidence | Note |
|---|---|---|---|
| Thrust | 75 N @ 117k rpm | medium | A U. Sydney paper says 92 N @ 128k. Not reconciled. |
| Max speed | 117,000 rpm | high | Two independent sources; one tested the compressor to exactly that. |
| Mass flow | 0.20–0.25 kg/s | low | 0.25 in a paper; CFD shows 0.20–0.21 at 120k. |
| Pressure ratio | 1.96 @ 117k | high | 1.54 at 80k rising to 1.96. |
| Compressor efficiency | 0.55 @ 117k | high | **Peaks at 0.73 near 80k then collapses** — a warning about running a turbo wheel past its map. |
| Turbine inlet temp | 983 K | medium | Mass-averaged, coupled CFD. NOT the ~2400 K local peak flame temperature quoted elsewhere. |
| EGT | 843 K (570 °C) | medium | CFD gives ~990 K at the combustor exit plane; different station. |
| Combustor loss | 12% of CDP | medium | **Roughly double** the 5–6% typical of a straight-through annular. That is the price of the reverse-flow turn. |
| Envelope | 240 × 110 mm, 0.93–1.2 kg | high | |

### Geometry

Compressor: 66 mm exducer, COTS KKK automotive turbocharger wheel, 6 full + 6
splitter blades, aluminium wedge-vane radial diffuser.

Turbine: 66 mm tip, cast Inconel 713C, ~6 mm disc, 23 blades, 55 mm mean
diameter, 11 mm blade height, 0.15–0.20 mm tip clearance. Schreckling's worked
blade root load is **4430 N** for a 1 g blade — the single best validation point
available for the structural side.

Combustor: annular reverse-flow, **six vaporizer tubes**, stainless 316/310
liner. Six independent sources agree on the six tubes; it is the
best-corroborated fact about this engine, which is why the model reproducing it
without tuning matters.

Bearings: ISO 608, 8 × 22 × 7 mm, C3, glass-fibre cage, rated to 120,000 rpm.
DN = 0.94e6. Lubricated by 5% turbine oil premixed into the kerosene.

### Not found anywhere

Inducer diameter, exducer blade width, backsweep angle, combustor liner
diameters and length, liner hole pattern (counts and diameters), NGV throat area
(count disputed between 11 and 18), nozzle exit dimensions, bearing span, shaft
diameter, and any published study scaling the KJ66 to another thrust class.
These almost certainly exist only in Schreckling's and Artés's own drawings.

### The cycle does not close

Feeding the model the KJ66's own published pressure ratio, compressor
efficiency, turbine inlet temperature and combustor loss produces about 23 N at
the published 0.23 kg/s, against a published 75 N. The turbine inlet temperature
that would reconcile it is ~1306 K, which implies an exhaust temperature near
1209 K against a published EGT of 843 K.

So at least two of {75 N, 0.23 kg/s, 983 K TIT, 843 K EGT} describe different
operating points or different engines, and no source says which. Most likely
suspect: the 0.55 compressor efficiency, measured far past where that
turbocharger wheel wants to run, combined with a TIT taken as a mass-average
from an entirely separate CFD study.

**Use the KJ66 to validate geometry and stress. Do not use it to validate the
cycle.** Two tests assert the gap is still there so nobody tunes it away.

---

## Part 2 — combustor correlations, verified against Lefebvre

Primary source: Lefebvre & Ballal, *Gas Turbine Combustion: Alternative Fuels
and Emissions*, 3rd ed., CRC Press, 2010. Equation, figure and page numbers
below were checked against the text, not against secondhand paraphrases.

| # | Item | Verdict |
|---|---|---|
| 1 | Loading parameter θ = P³·⁷⁵·A_ref·D_ref^0.75·exp(T/300)/ṁ (Eq. 5.6, p. 156) | **Exponents correct.** m = 0.75, b = 300 are Lefebvre & Halls' own fitted constants. Using plain volume instead of A_ref·D_ref^0.75 is Lefebvre's own Eq. 5.8 form, so a defensible variant. Note the code's CLP is the *reciprocal* of θ — fine, used consistently. |
| 2 | η vs loading | **Citation was wrong.** V21 cited Table 5.1; that table (p. 186) is the lean-blowout constants for Eqs. 5.27/5.29. The real relation is Figs. 5.2/5.4 and it is a chart. The assumed shape is defensible. |
| 3 | Pressure-loss factor K = 20 for annular (Table 4.1, p. 116) | **Exactly right.** Lefebvre's tabulated value: tubular 37, tuboannular 28, annular 20. Independently confirmed by Melconian & Modak 1985. No separate figure published for reverse-flow — COULD NOT VERIFY. |
| 4 | Jet penetration | **Right constant, wrong regime.** 1.15·√J is Eq. 4.19, for a *single* jet. Multi-hole rows need Eq. 4.20: 1.25·√J·[ṁ_g/(ṁ_g+ṁ_j)]. ~28% difference. Fixed in P6. |
| 5 | Primary zone φ = 1.6 | **Rich vs conventional guidance** (AFR ≈ 18, φ ≈ 0.82, p. 9), but defensible for a vaporizer combustor. Lefebvre notes RB199 vaporizer tubes run at AFR 2–6 internally (§6.12, pp. 252–253). At the top of the range where φ-dependent loading correlations are validated. |
| 6 | Nu = 0.037·Re^0.8·Pr^0.33 for dome flux | **Wrong correlation.** Neither Martin's impingement form (needs H/D and r/D) nor Lefebvre's own liner-convection method (§8.5, Eqs. 8.20–8.22, constant 0.017–0.020, liner hydraulic diameter). Three methods span 350–3900 kW/m² on the same geometry. Fixed in P7, but **not resolved**. |
| 7 | Typical liner heat flux | **COULD NOT VERIFY** a pinned benchmark. Lefebvre gives methods, not a tabulated typical range. The method-dependent envelope is itself the finding. |
| 8 | Residence time | Lefebvre quotes ~5 ms (§9.4.4.1.2, p. 374); Cranfield's worked example gives 3 ms for kerosene. **No codified minimum found.** The 1.4 ms this design runs at is below both, and is the KJ66's own value. |
| 9 | Cd = 0.60 | **Reasonable default, unverified in context.** Lefebvre Fig. 4.3 shows Cd is a function of K; 0.60 implies K ≈ 8–15, and he states K should not fall below 6. V21 never computed K. Fixed in P13 — and the check forced a design change. |
| 10 | Hole sizing A = ṁ/(Cd·√(2ρΔP)) | **Correct.** Lefebvre Eq. 4.14, standard form. The compressible correction V21 added beyond it is appropriately scoped. |

---

## Part 3 — the gas model

`core/gas.py` carries a least-squares quartic fit to standard air property
tables (Keenan & Kaye / Cengel–Boles Table A-17) over 300–1800 K:

- cp within **0.18%** of table
- enthalpy within **0.12%** of table
- `far_for_T4` and `T4_for_far` invert each other to better than 1e-9 K

Products of lean kerosene combustion are modelled as air with a linear
correction scaling with fuel-air ratio (~1.5% at f = 0.02), which is well inside
the fit accuracy for f < 0.03.

`tests/test_gas.py` asserts all of this against the table values directly.

**Do not reintroduce a constant cp.** The form `h = cp·T` with cp_cold = 1005
and cp_hot = 1150 and a zero-kelvin datum over-predicts the fuel-air ratio by
12–17%. There is a test that documents exactly this so nobody "simplifies" the
gas model back to it.

---

## Sources

- Lefebvre & Ballal, *Gas Turbine Combustion*, 3rd ed., CRC Press 2010
- Gas Turbine Builders Association, KJ66 engine page
- Trebunskikh, Ivanov & Dumnov (Mentor Graphics), *FloEFD simulation of micro-turbine engine*
- Xiang, Schlüter & Duan, *Study of KJ-66 micro gas turbine compressor*, Proc IMechE Part G, 2017
- Verstraete et al., *Micro propulsion activities at the University of Sydney*
- Wang & Luo (UCL), *Energies* 16(7), 2023 — reverse-flow combustor CFD
- Schreckling, *Home Built Model Turbines*
- Melconian & Modak 1985, via Conrado et al. 2004 (ENCIT)
- Martin, H., *Adv. Heat Transfer* 13, 1977; Zuckerman & Lior, *Adv. Heat Transfer* 39, 2006
- Keenan & Kaye air tables; Cengel & Boles Table A-17
