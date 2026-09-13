# Budget review: work within $5,000

September 13, 2026. Replaces the earlier $32,000 funding recommendation for planning. That estimate assumed a broader purchased-hardware/test-support route than the team can fund. **$5,000 is now the hard cash ceiling, not proof that every part of a running engine can be bought for that amount.**

## What the supplied DP-2 budget establishes

| Group | Low | High |
|---|---:|---:|
| Hot section and rotating | $1,350 | $2,670 |
| Fuel, start and control | $630 | $1,220 |
| Instrumentation | $345 | $840 |
| Stand, safety and ground support | $740 | $1,400 |
| Direct subtotal | $3,065 | $6,130 |
| With 15% contingency | $3,524.75 | $7,049.50 |

The arithmetic is correct. The midpoint with contingency is **$5,287.13**, which explains the document's approximate $5,300; it is not independently validated as the most likely cost. Only eight changed BOM lines and group totals were supplied. The full DP-1 BOM, supplier links for the claimed two hard anchors, shipping/tax assumptions and sponsor commitments were not supplied. This is insufficient to verify completeness or delivered cost.

## Initial spending envelopes

These are **caps to seek quotes against**, not revised estimates disguised as prices.

| Envelope | Maximum initial allocation |
|---|---:|
| Hot section, rotating parts, tooling and balancing | $1,700 |
| Fuel, start and controls | $750 |
| Minimum useful instrumentation and wiring | $500 |
| Stand, safety, approved ground support and consumables | $900 |
| Freight / tax / import reserve | $400 |
| Unallocated design and rework contingency | $750 |
| **Total ceiling** | **$5,000** |

Direct purchase envelopes total $3,850. Each fits within the supplied group range but their simultaneous feasibility is unproven. The $750 reserve is 15% of the cap (not 15% added afterward). Freight/tax is a separate allowance, not a tax determination. Include paid + committed + forecast remaining + reserves in the running total; pending invoices are not savings. If actual commitments already exist, enter them before approving new spending.

## In-kind support and cost efficiency

The team reports free machine-shop access, purchased stock/sensors, possibly free welding, likely paid balancing, and sponsorship by **Atlas Copco**. The sponsor relationship is confirmed by the team; the cash amount, stock, tooling, air supply or services committed are **NOT FOUND**. Count no additional sponsor credit until its scope and delivery date are confirmed. Existing free shop access must not be subtracted a second time as new sponsorship savings.

Prefer existing campus equipment, borrowed instruments with documented suitability, scrap for non-running mockups, shared tools and low-cost electronics for desk work. Seek in-kind certified stock, tooling, inspection and qualified balancing before spending on those items. Keep supplier correspondence private; record a publishable scope/quantity/date summary in the [quote log](../../workspaces/coordination/quotes.md).

## Items that can break the budget

- **Turbine material/process:** a $90 surplus IN718 blank is not an approved hot rotor. Confirm material identity, heat treatment, machining capability, inspection, final temperature/stress/life and tool wear. DP-2 mixes IN718 and 713C. A cheap blank can create expensive unusable machining work.
- **Bearings:** generic 608-C3 is not a verified low-cost solution at 66 krpm. Timken's listed example is limited to 39 krpm with oil. Get an exact approved part and lubrication/preload conditions. [Timken](https://cad.timken.com/item/deep-groove-ball-bearings/miniature-ball-bearings--600--610--620--630-/608-c3).
- **Pump compatibility:** Xicoy lists a pump at $156.47, but explicitly restricts that model to its own engines. Do not treat it as a proven generic $160 fuel system. Price the compatible pump, drive, valves, filter, fittings, power and delivered-flow verification together. [Xicoy](https://www.xicoy.com/catalog/product_info.php?currency=USD&products_id=771).
- **Cheap data collection is feasible for some channels:** an ADS1115 board is listed at $14.95. Its 860 conversions/s are shared among multiplexed channels, not 860/s per channel. It is not a complete thermocouple interface, an RPM pulse counter or an independent shutdown system. Budget the probe, cold-junction compensation, connectors, wiring, input protection and logging. Use a digital timer/counter for the proposed 1,100 Hz RPM signal, not sampled ADS1115 waveform reconstruction. [Adafruit](https://www.adafruit.com/product/1085), [TI](https://www.ti.com/product/ADS1115).
- **Balancing and containment:** the $100–250 service figure is unquoted and may not cover a custom shaft, fixtures, repeat runs or this rotor configuration. A teaching balance rig is not automatically an equivalent service. Retain an adequate review/inspection/containment route; do not trade it away to hit the cap.
- **Missing/unclear scope:** audit heat treatment, NDT, material certification, shipping, coolant/tooling, failed parts, fuel, extinguishers, spill provisions, power supplies, sensor mounting, load measurement, shop/test access and existing inventory before claiming a complete BOM.

Prices above were checked September 13, 2026 and are examples, not part selections or quotations. The earlier broad estimate remains historical; its purchased-service assumptions should not be added on top of this cap.

## Order of decisions

1. Chief engineer confirms spend-to-date, accessible cash, sponsor scope and inventory.
2. Leads obtain exact rotor-material/process, bearing, balancing, pump and test-support quotes; include delivery dates and compatibility evidence.
3. Reconcile the complete itemized BOM to the four direct envelopes. Record any exception before moving reserve money.
4. Buy reusable learning materials and approved first-part stock only when the related design and shop review are complete.
5. If the reviewed running-engine BOM exceeds $5,000, secure specific in-kind coverage or stage the project: December approved parts and desk/cold-flow evidence first; defer costly running-hardware work. Do not silently relax material, operating or containment requirements.

The first meeting requires **no spending**. Its budget deliverable is missing quote information and sensible priorities, not purchasing authorization.
