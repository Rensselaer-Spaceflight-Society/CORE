# PD-1 manufacturing route and cash estimate

PRELIMINARY - NOT FOR MANUFACTURE. Sources: `data/budget/oct02_parts_budget.csv` (read-only extraction of
the October 2 workbook, every row ID kept), `data/budget/pd1_adjustments.yaml` (candidate changes with
reasons), `core/budget.py` (totals), and the generated tables in
[`results/pd1-jm85/SUMMARY.md`](results/pd1-jm85/SUMMARY.md) and `results/pd1-jm85/bom/candidate_bom.csv`.
Campus machining and welding labour are assumed in kind (workbook basis) — **not confirmed**; tool
availability, process suitability, schedule and quality still need the shop's answer.

## 1. Cash estimate versus the $5,500 target and $6,000 ceiling

The extraction reproduces the workbook exactly before any change: direct $5,402 + freight $200 + tax $450 +
reserve $550 = **$6,602** (test `test_budget_extraction_reproduces_workbook_total`). Tax (8 % planning rate on
direct excluding travel, plus freight) and reserve (10 % of direct) use the workbook formulas and rounding.

| Scenario (USD) | Direct | Freight | Tax | Reserve | **Total** | vs $5,500 | vs $6,000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| October 2 workbook baseline | 5,402 | 200 | 450 | 550 | **6,602** | +1,102 | +602 |
| PD-1 nominal (changes + missing scope) | 5,527 | 200 | 450 | 575 | **6,752** | +1,252 | +752 |
| PD-1 adverse (quote/price risk on flagged lines) | 6,532 | 270 | 550 | 675 | **8,027** | +2,527 | +2,027 |
| PD-1 nominal, tax-exempt only (conditional) | 5,527 | 200 | 0 | 575 | **6,302** | +802 | +302 |
| Route SV1+SV5+SV4 (conditional) | 5,097 | 200 | 0 | 525 | **5,822** | +322 | −178 |
| Route SV1+SV5+SV4+SV2+SV3 (conditional) | 4,787 | 200 | 0 | 500 | **5,487** | −13 | −513 |
| PD-1 nominal, every conditional option below | 4,747 | 200 | 0 | 475 | **5,422** | −78 | −578 |

**No unconditional full-scope total fits the $6,000 ceiling.** The nominal estimate is $752 over the ceiling;
the full set of conditional options brings it to $5,422 (below target), but every one of those options is
unconfirmed. Spend-to-date, committed purchases and inventory were not supplied, so all lines are forecast.

### What changed from the workbook, and why (nominal)

| Row | Change | Δ nominal | Reason (design link) |
|---|---|---:|---|
| R02 | JETMAX 85 mm finished wheel; list-price estimate | −150 | CHF 370 × assumed 1.25 USD/CHF × 1.08 fees ≈ $500; adverse keeps $650 |
| R03 | JETMAX NGV85 blank + CORE finishing | 0 | CHF 295 → ≈ $398; adverse $450 |
| R04 | 10 × 26 × 8 hybrid bearings both ends | 0 | 9.99 mm turbine bore forces a 10 mm rear journal (TR-01/SH-01) |
| R05 | 5/8 in 4140 bar | +5 | 13 mm shaft body > 1/2 in stock |
| C03 | 1/4 in × 0.035 in 316 tube | −10 | model vaporizer OD ~6.2 mm, not 8 mm (rerate at stock) |
| C05 | ~0.5 mm ID needle tube | −5 | laminar distribution restrictors (systems/fuel_budget.json) |
| E18/E19 | brushless starter + ESC | +55 | starter bound ~0.4–1.2 kW at 20–30 krpm (extrapolated) |
| N01–N06 | added scope | +230 | hot rear carrier stock, elastomer mount O-rings, A286 hot fasteners, pin-gauge set (throat measurement), small end mills (diffuser), dye penetrant |
| Tax/reserve | recomputed | +25 | reserve 10 % of the new direct total |

### Conditional savings (none confirmed)

| ID | Option | Saving | Consequence | Dependency |
|---|---|---:|---|---|
| SV1 | Tax-exempt purchasing | 450 | none on design | confirmed exemption/purchasing channel |
| SV2 | Borrow drills, end mills, extinguishers, glasses, pin gauges | 245 | tool condition not controlled | confirmed loan |
| SV3 | Nest exhaust nozzle on the C01 sheet remainder | 65 | uses the strip otherwise left for a spare liner set | shop nesting confirmation |
| SV4 | Ratiometric pressure sensors instead of transmitters | 230 | lower accuracy; adequate for trending/protection | signal-conditioning review |
| SV5 | Campus test at an approved site (no travel) | 200 | none if a reviewed site exists | site and containment approval |
| SV6 | Defer thrust measurement | 40 | no thrust evidence (secondary objective) | team decision |

**Candidate route to the budget (reversible):** SV1 + SV5 + SV4 brings the nominal to **$5,822**, under the
ceiling but above the target. It depends on two confirmations (tax status and test site) and a sensor
decision. Adding SV2 and SV3 gives **$5,487**, just under the target. Both routes are computed with the workbook
tax and reserve formulas (`data/budget/pd1_adjustments.yaml → routes`, `core/budget.apply_options`), not by
subtracting option amounts. Do not count any of these until confirmed.

### Largest unresolved price risks

Already inside the **adverse** total ($8,027), not the nominal:

1. Assembled-rotor balancing (S03/S04): custom rotor, possibly balanced in the engine core (JETMAX offers
   this, with international shipping): +$175.
2. Turbine/NGV landed cost (FX, payment fees, duties): +$200, plus freight +$70. The duty basis for
   Swiss-origin parts and whether the CHF list prices include Swiss VAT are not documented (open).
3. Fuel pump compatibility with an independent driver (F01): +$70; a different pump is possible.

In **no** total yet (nominal or adverse):

4. Shaft journal finishing: k5 journals (6 µm band) may need cylindrical grinding (+$100–200 if outsourced)
   — or a shop that can hold it by turning/lapping.
5. Liner fabrication route: if rolled-sheet liners cannot clear the weld seam (see component review), a
   4 in × 0.065 in 316 drawn tube for the outer liner adds ~$60–80.
6. Starter battery and starter capability (E18/E19): the requirement is not established below the map.
7. Stock rows that do not match the parts (independent check, 2026-10-04): R09 is ½ in (12.7 mm) bar but the
   front sleeve is Ø13.0 and the rear spacer Ø13.5 mm (needs ⅝ in; not re-priced); BC-01 has no linked stock
   row (R08 is 6061 bar and is linked to nothing; N01 covers BC-02 only); R04 still carries the old
   8 mm-bearing price ($150 each) because the record's price is unresolved.

## 2. Make/buy and process route per part

Tolerances marked critical below are the ones that set a running clearance, a fit or a flow area; everything
else is general tolerance (ISO 2768-m). The CAD bundle (`results/pd1-jm85/cad/cad_bundle.json`) carries the
proposed tolerance and its reason for every parameter.

| Part | Make/buy | Stock (budget row) | Operations and setups | Critical features | Special processes / inspection |
|---|---|---|---|---|---|
| CW-01 compressor wheel | buy | R01 | — | bore 5.99 mm | measure bore, weigh, scan blade-tip profile for the housing shroud |
| CH-01 compressor housing | make | 6061 block 2×6×6 in (R06) | lathe: 2 setups (inlet face, diffuser-cover face); soft jaws | shroud contour 0.30 mm from the measured wheel; register to casing | contour from wheel scan; CMM or template check |
| DF-01 diffuser/backplate | make | 6061-T651 ½ in plate (R07) | lathe: OD spigot, seal bore, bearing pocket, recess in ONE setup (concentricity ≤ 0.02 mm TIR); mill: 19 channels with rotary indexing; floor ramp for 6→9 mm width growth | throat width (≈ 2.6 mm), floor flush with wheel hub, pocket/spigot concentricity | small cutters (N05); deswirl vanes in the 90° bend are a separate fabricated ring (sheet vanes brazed/welded) — 3-D machining not assumed |
| BC-01 front bearing sleeve | make | 416/303 SS bar | lathe 1 setup + part-off | Ø26 J6 bore, O-ring grooves | anti-rotation pin |
| BC-02 rear carrier (hot) | make | 416/303 SS round (N01) | lathe 2 setups | Ø26 G6 floating bore, spring seat; the Ø48 g6 spigot is **envelope only** until the NGV hub decision (the 48 mm pocket in the blank is blind, with a centre web) | FKM O-ring temperature at the rear is a risk (air-cooled by tunnel leakage) |
| SH-01 shaft | make | 4140 prehard ⅝ in (R05) | between centres: rough, finish; threads M6×1 / M8×1 (hand to suit rotation); fillets ≤ 0.4 mm | journals k5, seats to measured bores, runout ≤ 0.005 mm | grinding or lapping likely; magnetic-particle or dye check of fillets |
| SL-01/02 sleeves/spacers | make | 316 bar (R09, needs ⅝ in) | lathe, lap faces | face parallelism ≤ 0.005 mm (clamp stack) | |
| TU-01 tunnel | make | 2 in × 0.065 in 316 tube (C02) | cut, face, spigot fits | rear end sliding fit | |
| CB-01..05 dome, liners, cones | make | 316 sheet 0.060 in (C01) | shear, roll, TIG seam, size on mandrel; drill rows on a rotary index fixture after welding; cones from flat patterns | hole Ø ±0.05, positions ±0.3, liner diameters ±0.3 | TIG distortion control, dye penetrant (N06); seam location constraint (see component review) |
| VP-01 vaporizers ×8 | make | ¼ in 316 tube (C03) | cut, mandrel J-bend (CLR ≈ 9.5 mm), crimp/swage exit, scoop inlet, weld to dome | crimp Ø, scoop Ø, bend position | flow-check each stick (air) before welding |
| NG-01 NGV | buy + finish | JETMAX NGV85 blank (R03) | measure throat FIRST; lathe: shroud bore Ø85.70 +0.02/0, flange faces; drill 12 × Ø3.4 on PCD 98 (M3 hot bolts on the 6 mm land between the Ø92 outer ring and the Ø104 flange OD). **Hub: the blank's Ø48 × 11 mm pocket is blind, with a centre web and a conical boss on the rear side; how much of the web is bored or removed is an open team decision** (see §2 assembly) | shroud bore (tip clearance), concentricity to the hub pocket | pin-gauge throat survey (N04); record vane count; remaining-web/hub strength check after machining |
| TR-01 turbine | buy | JETMAX TW85 finished (R02) | none (prebalanced) | bore 9.985–9.995 | dimensional + dye penetrant (S02); weigh; count blades; measure throat |
| CS-01/02 casing, rear cover | make | 316 sheet (C01) | roll + TIG seam; rear cover ring (ID = NGV outer ring + 1 mm) + TIG; drill flange holes matched to NG-01 | OD ±0.3, rear cover flatness, ID clears the NGV outer ring | leak check with shop air + soap |
| EX-01/02 nozzle, tailcone | make | 316 sheet (I03 or C01 remainder) | roll cones, TIG, 3 struts | exit Ø ±0.2 (area ±0.75 %) | make two nozzles (54 / 50 mm) for trimming |
| IN-01 bellmouth/screen | make | 6061 sheet (I01), mesh (I02) | spin/form or machine from block | lip radius | |
| Fuel manifold/needles | make | 1/8 in tube (C04), needle tube (C05) | bend ring, braze needles | needle length (restrictor) | flow-balance test with water/kerosene |
| Starter bracket | make | aluminium strut | mill | cone alignment | |
| Stand | make | steel tube (T01–T03) | saw, weld | load-cell alignment | |

**Assembly order — not established.** The earlier sequence (insert the shaft assembly from the rear so the
rear carrier seats in an "NGV hub bore Ø48") assumed an open bore. The supplier blank drawing shows the Ø48
pocket is **blind**: it opens on the front (vane-ring) face, 11 mm deep, then a centre web and a conical boss
that projects aft into the rotor's shroud section. In the current stack the rear bearing sits inside the
pocket, while the rear spacer, the Ø14 turbine boss and the carrier extend through the web zone, so the stack
implicitly assumes the web is removed. The finished passage, the carrier location and therefore the order are
a **team decision**:

1. bore the web for shaft/boss clearance and keep the pocket as the carrier seat (carrier and shaft go in from
   the front through the tunnel; turbine fitted from the rear);
2. remove the web completely (Ø48 through), as the stack drawing implies, after checking the 3.7 mm hub ring
   and vanes as the rear-bearing load path;
3. carry the rear bearing in a separate housing (tunnel/struts), the NGV hub only clearing the shaft;
4. flange the carrier to the machined rear face of the web.

Each option changes the rear support stiffness and temperature (rotordynamics), the axial growth path, the
balancing route and tool access. Unchanged by the choice: the turbine (Ø85) cannot pass any hub passage, so a
rotor balanced on a stand is disassembled at installation — balance in the assembled core (as JETMAX's service
describes) or prove repeatability with match marks and a re-check. Compressor nut from the inlet; turbine nut
from the exhaust before the nozzle; P03/T03/EGT bosses and igniter outside the casing.

## 3. Sheet nesting (C01, 610 × 610 mm)

`core/budget.sheet_nesting` shelf-packs the casing wrap, both liner wraps, dome blank, rear-cover blank and both
discharge cones from the solved geometry with 10 mm seam/kerf allowance: **fits**, leaving a 609.6 × 171.1 mm
strip. The run's nesting does not place the nozzle. An independent flat-pattern check shows the main nozzle
shell (262.8 × 116.7 mm) and tailcone (107.1 × 68.6 mm) fit that strip, but the strip is claimed three times —
SV3 (main nozzle), O02 (spare Ø50 nozzle, $0) and a spare liner set — and cannot serve all of them.
