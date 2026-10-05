# Limits and correlations audit (T09)

October 4, 2026. `config/limits.yaml` was **not changed**. This page records whether each existing
screen and each consequential correlation applies to the PD-1 candidate, and proposes criteria for
team review where it does not. A proposal here is not an adopted limit.

## 1. Applicability of the existing limits to PD-1

| Limit (limits.yaml) | Value | Comment's stated basis | PD-1 applicability | Proposal for team review |
|---|---:|---|---|---|
| `T04_max_K` | 1200 K | Uncooled Inconel 713C | JETMAX wheel alloy is **not published**; NGV is "high-temperature alloy steel, to 1000 °C" (supplier wording). The 713C basis may not apply. | Keep 1200 K as a screen only. Obtain alloy/heat treatment; set the limit from blade/NGV metal temperature and life, not gas temperature. PD-1 also screens at the DP-2 1150 K. |
| `U2_max_m_s` | 520 m/s | 7075-T6 radial impellers | Billet wheel alloy unconfirmed (commonly 2618-class forged). PD-1 runs 271 m/s, far below. | Replace by the supplier's speed rating for the actual wheel. |
| `M1s_rel_max_ratio` | 0.90 | Inducer shock losses | Applies. Inducer hub diameter is an assumption. | Keep; measure hub. |
| `burst_margin_min_ratio` | 1.50 | "Burst speed over design speed" | M33 computes a **blade root centrifugal** speed margin only, from assumed blade sections; it is not disc burst. | Rename the screen in reports as blade-stress speed margin (already done in code); add disc/hub analysis requirement. |
| `AN2_max_m2_rpm2` | 6e7 | Traditional blade-stress index | Applies as an index. PD-1 1.4e7. | Keep. |
| `DN_max_mm_rpm` | 1.6e6 | Hybrid ceramic, preload, **oil mist** | PD-1 lubrication is fuel + 5 % oil mist (model-jet practice), not a dedicated oil-mist system. The applicable DN is lower and supplier-specific. | Replace by the supplier limiting speed for the chosen lubrication (requested). PD-1 DN 6.8e5. |
| `T_liner_wall_max_K` | 1150 K | **Inconel 625** liner with film cooling | PD-1 liner is **316/316L**. The comment's material does not match. | Propose ≤ 950 K for 316 at the steady point pending oxidation/creep review; PD-1 model value ~685–705 K (prescribed 0.72 × T04 rule, uncalibrated). |
| `N_crit_margin_min_frac` | 0.20 | "API-style" rule | Screening rule; supports are assumed. Applied to all FE criticals found. | Keep as screen; require a measured rotor modal test before release. |
| `q_dome_max_W_m2` | 600 kW/m² | Placeholder (methods differ ~10×) | Placeholder, as its comment says. | Do not sign against it; see thermal analysis request. |
| `J_primary_*` | 5–80 | Lefebvre band, widened | Diagnostic, not a stability proof. | Keep as diagnostic. |
| `dil_pen_max_ratio` | 0.75 | Lefebvre multi-jet | Applies as a mixing proxy. | Keep. |
| `tau_res_min_s` | 1.2 ms | KJ66 practice | PD-1 sizes at 1.4 ms (seed basis). Bulk transit only. | Keep; low-pressure (1.5 bar) operation makes this more doubtful than at KJ66 pressure. |
| `hole_K_min_ratio` | 6 | Lefebvre §4.6.1 | Applies to inner and outer branches. | Keep. |
| `casing_fit_margin_min_m` | 2 mm | Assembly clearance | Applies. | Keep. |

## 2. Correlations that control consequential dimensions or conclusions

| Correlation / model | Where | Controls | Source and validity | Status |
|---|---|---|---|---|
| Air cp(T) quartic | `core/gas.py` | every enthalpy | Fit to air tables 300–1800 K | **Independently checked:** within ±0.2 % of a NIST-JANAF species mixture, 300–1500 K (`docs/design/checks/gas_property_audit.py`) |
| Products cp = cp_air (1 + 0.75 FAR) | `core/gas.py` | fuel, turbine ΔT | Unvalidated surrogate | **Independently checked:** 1.2 % low at FAR 0.0139, 1.8–2.0 % low at FAR 0.022 vs frozen complete-combustion NIST-JANAF mixture; turbine Δh over PD-1 expansion −1.2 %. Keep with this stated bias; equilibrium (CEA) comparison still open. |
| GT3076R map (digitized) | `data/maps` | compressor PR, η, flow | Garrett image; reference conditions from a secondary source | Related-wheel proxy; ±0.3 lb/min, ±0.01 PR, η ±0.01–0.03 digitization; substitution offsets in robustness |
| Soderberg loss + aspect-ratio + Reynolds corrections | `core/turbine_rating.py` | turbine work/efficiency | Dixon & Hall presentation; basis Re 1e5, AR ~3 | **Rotor Re 1.6–2.0e4 over 56–68 krpm** after the viscosity fix (0.16–0.20 of the basis). The code's validity flag at Re < 2e4 has **no cited source**; it now trips at 56–66 krpm and the 68 krpm design point sits 0.1 % inside it. The (1e5/Re)^¼ correction cannot represent laminar separation; low-Re loss data for this stage do not exist. Loss ×1.5/×2 cases and the loss-multiplier threshold bound the effect within the model only |
| Hot-gas viscosity for the turbine Reynolds number | `core/turbine_rating.py` `mu_hot` | Soderberg Re correction and validity flag | **Corrected 2026-10-04**: Sutherland's law for air (1.458e-6 T^1.5/(T+110.4)), within ~2 % of tabulated air at 300–1000 K | The earlier law 3.5e-5 (T/1000)^0.7 was ~18 % low and overstated Re by ~20 %. The same old law remains in `core/combustor.py` (dome heat-flux estimate, where it errs on the conservative side); left for the combustor owner |
| Cosine rule (throat ↔ exit angle) | `core/turbine_rating.py` | NGV/rotor capacity and swirl | Standard subsonic approximation | Angles assumed; throat measurement resolves it |
| Tip leakage (1 − K_tip c/H), incidence 0.5 k (W sin i)² | `core/turbine_rating.py` | work debit | Provisional engineering models | Bounded in robustness (K_tip 3, 0.5 mm, ±10° incidence) |
| Stanitz slip | `core/gas.py`, M10 | diagnostic of feasible work | NACA TN 2654 | Diagnostic for DP-2. **Corrected 2026-10-04:** the fixed-wheel diagnostic multiplied the air's enthalpy rise by the power-input factor instead of dividing; the blade work coefficient for PR 1.63 at 66 krpm (η 0.72) is **0.837**, not 0.905, against σ = 0.820 — still above slip, but only if η_c < 0.735. The legacy sizing branch of M10 keeps the old convention (inflates the baseline D2 by ~4 %); left for the team because it moves the baseline |
| Power input factor convention | M10 (legacy sizing) | baseline impeller diameter | Saravanamuttoo-type definition Δh0 = PIF × σU² | Legacy branch applies PIF × Δh0 as blade work; team decision (baseline regression) |
| Nozzle Cd and Cv | `core/engine_match.py`, M40, `core/thermo.nozzle` | nozzle capacity, T04 | Values 0.97/0.97 are assumptions | Capacity uses Cd·A·ρ8·(Cv·V_is): relative to ideal flow the effective coefficient is ≈ Cd·Cv ≈ 0.94. If Cd is meant as the overall discharge coefficient this double counts ~3 % of capacity (≈ +12 K T04). Convention needs a team decision and, ideally, a measured nozzle |
| Combustor liner static pressure | `core/combustor.py` | hole ΔP, loss basis | Uniform liner static at the exit value (stated approximation) | At PD-1's liner exit Mach (~0.16) the exit dynamic head (≈ 4.9 kPa) is comparable to the hole drop (6.0 kPa); a 1-D momentum balance makes the sized holes consistent with ≈ 5 % loss, not the 2.5 % basis. Team-owned; robustness 4/6 % covers the cycle effect |
| Dilution-jet definitions | `core/combustor.py` | penetration screen | Lefebvre Eq. 4.20 | Code uses the geometric diameter with the area-mean jet velocity and a fixed 1200 K mainstream; with Lefebvre's effective-diameter definitions the PD-1 ratio is ≈ 0.89 (fails 0.75). Open for the combustor owner |
| Lefebvre A_ref from loss factor K = 20 | `core/combustor.py` | liner and annulus sizes | Lefebvre Table 4.1 (annular) | Prescribed loss is a sizing basis, not a prediction |
| Lefebvre multi-jet penetration | `core/combustor.py` | dilution hole sizing check | Lefebvre Eq. 4.20 | Diagnostic |
| Combustor loss ∝ FF² off-design | `core/engine_match.py` | off-design pressure ledger | Fixed-geometry scaling (cold-loss form); hot loss neglected | 4/6/8 % cases bound the level |
| Diffuser turn K q_exit | `core/diffuser.py` | duct-loss allowance | K = 0.5 with deswirl vanes is an assumption | Allowance 2 % ≥ estimate 1.6 %; 3 % case in robustness |
| SKF/Palmgren friction moment | `core/engine_match.py` | mechanical loss | Classic SKF form; f0, ν assumed | ×3 case: +16 K T04 |
| Windenburg–Trilling external-pressure buckling | `core/assembly.py` | outer liner wall | US EMB short-cylinder formula | Elastic only; creep buckling open |
| Solid-disc centrifugal growth | `core/assembly.py` | tip clearance | Thin solid disc | Rim/bore geometry simplified |
| Euler–Bernoulli/Rayleigh beam FE | `core/rotor_fe.py` | criticals | Benchmarked (Rayleigh beam, Jeffcott, gyroscopic cantilever) | No shear deformation; supports assumed |

Equilibrium-property results (e.g. CEA) would not establish flame stability, vaporizer behaviour or
exit pattern factor; those remain experimental/analysis items.
