> **Historical snapshot, superseded September 2026.** Numerical claims and validation statements below describe the pre-audit model. Use [current model review](model-review.md), [workflow](workflow.md) and [README](../README.md) for current guidance.

# CORE microjet — agent handoff

**Read this first.** You are picking up a reverse-flow micro gas turbine design
project at Rensselaer Polytechnic Institute. This document tells you what
exists, what is trustworthy, what is not, and what to do next.

Repo: `core-engine/`. Run `python run.py` and `python -m pytest tests/` before
changing anything — both should be green, and if they are not, that is your
first job.

---

## 1. What this is

A student team (~20 people, Fall 2026) is designing a reverse-flow microjet
scaled up from the KJ66 — the best-documented hobbyist micro turbojet in
existence. The goal for the semester is a frozen design and parts on order, not
a running engine.

The repo is a **declarative design pipeline**. Every component is a Python
function that declares what state variables it reads and writes. A solver reads
those declarations, builds the dependency graph, topologically sorts it, finds
the genuine circular dependencies, and iterates those to a fixed point. Nobody
maintains an execution order by hand and nobody passes dictionaries down a
chain.

```
python run.py            solve the design point, write out/
python run.py --graph    execution order and the coupled groups
python run.py --status   module maturity board: owner, second, stub/draft/verified
python run.py --trace    watch the solver work, including loop passes
python -m pytest tests/  74 tests
```

Current state: **14 modules, 74 tests passing, 15/15 safety limits satisfied.**

---

## 2. The three kinds of number

Knowing which is which resolves most arguments.

| Kind | Lives in | Decided by |
|---|---|---|
| **Seed** | `config/seed.yaml` | a human, frozen at Gate A |
| **Limit** | `config/limits.yaml` | the Safety Director; a violation fails CI |
| **Computed** | exactly one module | that module, and no other |

`config/variables.yaml` is the Interface Control Document — every number that
crosses a boundary between two people's work, with its unit, meaning, owner and
freeze gate. **Exactly one module may write any given variable.** The solver
refuses to run otherwise. This is the single most important rule in the repo.

Variable names carry their SI unit as a suffix (`D2_m`, `mdot_kg_s`, `T04_K`,
`P03_Pa`). A test enforces it.

---

## 3. What you can trust, and what you cannot

### Trust

- **`core/gas.py`.** Validated against published air property tables to 0.18%
  on cp and 0.12% on enthalpy over 300–1800 K, with an exact round-trip between
  `far_for_T4` and `T4_for_far`. `tests/test_gas.py` proves it.
- **The solver.** It found two real bugs during construction that no human
  review had caught: a combustor/casing pair that diverged without bound, and a
  pressure-balance solve that was degenerate. See §5.
- **The mass and energy balances.** The air budget closes to machine precision;
  the fuel flow round-trips to the target turbine inlet temperature to 1e-10 K.
- **Blade root stress.** Reproduces Schreckling's own worked KJ66 example to
  within 7%.
- **Vaporizer count and bore.** Predicted, not fitted — see §4.

### Do not trust

- **The dome heat flux.** Three published methods disagree by roughly 10× on
  the same geometry. `m24_combustor_checks` is marked `status="stub"` for this
  reason alone; everything else in it is sound. Details in `PATCHES.md` P7.
- **The KJ66 cycle numbers.** They do not close. Feed the model the KJ66's own
  published pressure ratio, compressor efficiency, turbine inlet temperature
  and combustor loss and it makes about a third of the published thrust.
  `tests/test_kj66.py` asserts the gap is *still there* on purpose, so that
  nobody "fixes" the cycle by tuning it until the KJ66 closes.
- **Any module marked `stub`.** `python run.py --status` lists them.
- **The seed design point.** It is a placeholder scale-up (250 N, roughly
  3.3× the KJ66), not a decision the team has made.

---

## 4. The KJ66 baseline: fits versus predictions

`config/kj66_baseline.yaml` holds published KJ66 numbers with a source and a
confidence level on each. This distinction matters and the original combustor
code did not draw it:

**Fitted — not evidence.** The chamber length agreement. The KJ66 preset
overrode `tau_min_s` and `target_inner_annulus_vel` with comments explicitly
saying they were calibrated to reproduce the historical ~65 mm length. Two free
parameters tuned to hit one number is a curve fit.

**Predicted — this is the evidence.**

| Quantity | Model | KJ66 | Note |
|---|---|---|---|
| Vaporizer count | 6 | 6 | falls out of dome circumference ÷ pitch |
| Vaporizer bore | 4.26 mm | ~4.0 mm | from a target mixture velocity |
| Inner annulus velocity | 23 m/s | 20 m/s (was hand-tuned) | now a solver output |
| Blade root force | 4128 N | 4430 N | Schreckling's own worked example |

The inner annulus velocity is the interesting one: it *was* an empirical
calibration constant and is now something the model predicts, because the
pressure balance was reformulated (PATCH P5).

---

## 5. Two bugs the solver found that review did not

Worth reading, because they say something about the architecture.

**The combustor and casing diverged without bound.** The combustor sized its
liner by subtracting feed annuli from a given casing bore — so it expanded to
fill whatever casing it was handed. The casing sized itself around the liner.
Positive feedback with gain above one: 183 mm → 224 mm → onward, monotonically.

This was invisible while the casing OD was a fixed human input, which is how
the original script ran. It appeared the moment the casing became a computed
quantity. The fix (PATCH P14) was to give the combustor an intrinsic size via
Lefebvre's reference-area method, so it *publishes the casing it requires*
instead of consuming one.

**The feed-split solve was degenerate.** The original code solved for the
outer/inner flow split that equalises path pressure loss. But the annuli were
*sized* to hit target velocities, so both velocities were pinned regardless of
the split, so the losses were pinned, so the residual was flat to within a few
pascals across the whole search range:

```
f_outer   0.20   0.30   0.40   0.50   0.60   0.70   0.80   0.90
residual  4084   1077     14     -2     11      0      7     11   Pa
```

The solver had nothing to solve and slid to whichever rail it started nearest —
which is why it reported 0.516 for one case and 0.371 for another from
numerical noise. Reformulated to solve for the inner annulus *area* instead,
which is monotonic and has exactly one solution.

---

## 6. Open questions — where a reviewer should push

1. **The dome heat flux correlation is unresolved.** Lefebvre's own §8.5 liner
   convection gives ~300 kW/m², Martin's impingement correlation ~1100, and the
   original flat-plate form ~1300. We report Lefebvre's because that is what the
   cited reference recommends for this geometry, but nobody has defended a
   choice in writing. Until someone does, the limit in `limits.yaml` is a
   placeholder and the Safety Director should not sign against it.

2. **Residence time is the constraint the whole combustor stands on.** At 2.0 ms
   there is *no* feasible combustor at the current design point — not at any
   casing size, not at any pressure loss, not at any area split. The design runs
   at 1.4 ms, which is the KJ66's own value, against Lefebvre's 3–5 ms guidance
   for full-size combustors. If part-throttle blowout appears on the test stand,
   this is the first number to revisit. The `tau_res_min_s` limit had to be
   lowered from 1.5 ms to 1.2 ms because the real KJ66 violates 1.5.

3. **`liner_area_frac` is 0.45, not the textbook 0.66.** Forced by the hole
   discharge-coefficient check: at 0.66 the feed annuli run at 62 m/s, putting
   the hole coefficient K at 2.3 against Lefebvre's stated minimum of 6, which
   makes the assumed Cd of 0.60 unsupportable. The trade table is in
   `config/seed.yaml`. This sits *at* a constraint boundary, which is a good
   argument for revisiting the 4% pressure-loss target — the KJ66 measures 12%.

4. **The combustor pressure loss is optimistic.** 4% is below Lefebvre's 6% for
   a *straight-through* annular can, and this is a reverse-flow can with a 180°
   turn on top. The KJ66 measures 12%. Nothing has been done about this yet.

5. **`m01_cycle` uses constant γ for the hot section** even though cp is now
   properly temperature-dependent. Inconsistent; probably worth fixing.

6. **The primary zone equivalence ratio of 1.6 is rich** against Lefebvre's
   conventional guidance (AFR ≈ 18, φ ≈ 0.82). Defensible for a vaporizer
   combustor, which prepares fuel rich by nature, but it is at the top of the
   range where the φ-dependent loading correlations are validated.

7. **Off-design is unbuilt.** `RPM_Sweep_OffDesign.py` is a good design-card /
   rating-model split and works, but it is not wired into the pipeline. It
   should become `m60_offdesign`, reading frozen geometry from state rather
   than round-tripping JSON. Deliberately deferred — nothing you need to order
   a part depends on it.

---

## 7. Repo map

```
core/
  gas.py         validated thermodynamics. Do not add a second gas model.
  combustor.py   patched port of the team's V21 combustor. 14 patches.
  module.py      the @module contract and its validation
  solver.py      graph build, topological sort, loop detection, relaxation
  registry.py    variable registry, unit rules, config loading
config/
  variables.yaml     THE ICD. Every shared number.
  seed.yaml          human choices. Frozen at Gate A. Read the inline notes.
  limits.yaml        Safety-owned. A violation fails CI.
  kj66_baseline.yaml published KJ66 data with sources and confidence levels
  initial_guess.yaml first guesses for the coupled loops
  cad_map.yaml       state variable -> CAD parameter name
modules/       one file per component. 14 of them.
tests/         74 tests: gas model, KJ66 regression, combustor, pipeline health
docs/          this file, PATCHES.md, the research notes
out/           generated. Never commit it.
V22_CombustionChamberDesign.py   standalone entry point, same interface as V21
RPM_Sweep_OffDesign.py           off-design rating model, patched to share the gas model
```

---

## 8. If you change something

- Run `python run.py` and `pytest` first, so you know what green looks like.
- Every new shared variable goes in `config/variables.yaml` with a unit and an
  owner, or the run fails.
- Every module needs a `second` owner — there is a test for it. This team has
  uneven attendance and bus factor 1 is how a module goes dark for three weeks.
- Editing `config/limits.yaml` is the Safety Director's call, not yours.
- If you make a module more accurate, move its `status` from `stub` toward
  `verified` and say in the docstring what you validated it against.
- If you find the source that reconciles the KJ66 cycle numbers, update
  `kj66_baseline.yaml` and delete the two tests that assert the gap, with a note
  saying what you found.

**A note on the review that produced this.** The first audit of the team's
combustor claimed its fuel balance was 21% low. That was wrong: it compared the
combustor against a cycle model that was itself 17% high, and the combustor was
the better of the two. The actual error was about 3%, and the real bug was in
the reviewing code. Check claims against published data, not against another
piece of code that has not itself been validated.
