# Joulie training data corpus — EECA (eeca.govt.nz)

Generated markdown documents for ingestion by the Joulie AI model.
Save this folder's contents into C:\Joulie-data (merge into `for-homes\` and `regulations\`; nothing existing is overwritten).

**Status:** the entire original COWORK-TASK.md URL list is complete, plus the consumer-facing and mid-level regulatory *discovered* pages. Corpus now stands at **76 documents** (10 pre-existing + 66 generated). The only outstanding items are the deepest, most granular B2B regulatory pages and a few linked PDFs (listed at the end).

## Conventions

YAML front matter on every file: `source_url`, `source_type` (webpage/pdf), `source_date` + `source_date_basis` (document-date where the source shows one, else retrieval-date 2026-07-10), `retrieved`, `document_id`. Discovered pages also carry `linked_from`. Content is a faithful, reworded restructuring with navigation/footers/promos removed; EECA statistics keep their attribution and methodology; cross-page discrepancies are flagged.

## Naming decisions (deviations from strict "last path segment")

- `for-homes/warmer-kiwi-homes-information.md` — segment `information` was ambiguous.
- `regulations/e3-compliance-and-monitoring.md` / `veeel-compliance-and-monitoring.md` — the two sections share a `compliance-and-monitoring` segment; prefixed to avoid collision.
- E3 compliance children prefixed `e3-` (retailers, manufacturers-and-importers, registering-your-product, providing-sales-data, minimal-quantities-exemption) to be unambiguous in the flat folder.
- VEEEL seller pages shortened to `veeel-compliance-{role}.md` from very long URL segments.
- `best-practice-residential-solar-pv-and-battery.md` shortened from a long URL segment.
- Energy Rating Label product pages sit in `regulations/` (e.g. `regulations/fridges-and-freezers.md`, `regulations/heat-pumps.md`); the consumer versions of some sit in `for-homes/` — same last segment, different folder, so no file collision.

## Licensing note

eeca.govt.nz footer states "©2026 EECA — All rights reserved"; reuse approval being sought. Exception: the three E3 Strategy PDFs (Strategic Plan, Implementation Plan, Workplan) are Commonwealth of Australia publications under CC BY 4.0 (attribution in each file).

## Completed documents

### Pre-existing (10)
for-homes: insulate-your-home, window-insulation, reduce-draughts, reduce-dampness, design-for-energy-efficiency, do-a-healthy-home-check, easy-ways-to-save-on-your-energy-bills, understand-your-energy-bills · regulations: about-the-e3-programme, e3-strategic-plan-pdf

### Batch 4 — For-homes non-vehicle content (22)
Save on energy bills, Improve your home, Energy saving technology (water heating, heating/cooling, appliances), Solar — including 4 discovered pages (home-energy-savings-calculator, home-water-heating-options, use-your-heat-pump-efficiently, buy-an-efficient-heater).

### Batch 5 — Vehicles + all Regulations + E3 PDFs (20)
Vehicles (6); E3 pages (how-to-comply, about-energy-rating-labels, e3-compliance-and-monitoring); VEEEL pages (about, how-to-comply, veeel-compliance-and-monitoring); other regs (regulatory-requirements-under-review, emissions-plan-guidance, ev-smart-charger-approved-list, solar-products-approved-list, best-practice-guidance-documents, demand-flexibility-in-end-use-products); PDFs (e3-implementation-plan, e3-workplan).

### Batch 6 — Discovered pages: appliances, tools, compliance sub-pages, ERL product pages (24)
for-homes (6): washing-machines, dishwashers, fridges-and-freezers, tvs-monitors-and-home-entertainment, efficient-appliance-calculator, solar-power-calculator
regulations — E3 compliance children (6): e3-compliance-retailers, e3-compliance-manufacturers-and-importers, e3-registering-your-product, e3-providing-sales-data, e3-minimal-quantities-exemption, products-under-e3
regulations — VEEEL seller pages (3): veeel-compliance-private-sellers, veeel-compliance-new-vehicle-distributors, veeel-compliance-motor-vehicle-traders
regulations — Energy Rating Label product pages (6): energy-rating-label, heat-pumps (Zoned label), clothes-dryers, clothes-washers, fridges-and-freezers, televisions-and-computer-monitors
regulations — voluntary guidance / review (3): solar-product-technical-specification, best-practice-residential-solar-pv-and-battery, heat-pump-water-heaters (review)

## Cross-page discrepancies logged

- **Warmer Kiwi Homes heating grant:** 80% (get-winter-ready, funding) vs 90% (home page, easy-ways, WKH information $3,450 = 90%). Authoritative = WKH information page (up to 90%, highest-need; excluded in middle-income areas).
- **Power-plan comparison tool:** Billy (Electricity Authority) vs Powerswitch (Consumer NZ); both legitimate.
- **Hot water heat pump figures:** vary by scenario/baseline across product page, Insights, and compare-options — not contradictions.
- **National average electricity price:** ~30c/kWh (choose-good-appliances) vs ~25c/kWh MBIE (Consumer NZ).
- **Per-star energy reduction differs by product** (as stated on each ERL page): clothes dryers ~15%/star (1–10★); fridges/freezers ~18%/star (1–6★); TVs ~20%/star (1–8★), monitors (1–9★). A third-party page's "10%/star" generalisation is not EECA's per-product figure.

## Remaining — deepest regulatory tree + PDFs (optional; highly technical / B2B)

**products-under-e3/{product} detail pages** (Standards citations, MEPS thresholds, Determinations, 1 May 2026 amendments) — one per regulated product, e.g. household-refrigerating-appliances, gas-water-heaters, electric-storage-water-heaters, computers-and-laptops, monitors, televisions, set-top-boxes, refrigerated-cabinets, air-conditioners, chillers, distribution-transformers, three-phase-electric-motors, ballasts, compact/linear-fluorescent-lamps, external-power-supplies, commercial-ice-makers. (The clothes-dryers and clothes-washers regulatory detail is already folded into their ERL pages.)
**regulatory-requirements-under-review detail pages:** distribution-transformers, electronic-displays, chillers, air-conditioners-and-heat-pumps-above-65kw, household-refrigerating-appliances, three-phase-electric-motors, commercial-ice-makers
**Best-practice guidance sub-pages:** smart homes; residential EV chargers; commercial EV chargers; procuring energy-efficient biomass boilers
**Consultation:** demand-flexibility green paper (unlocking the potential of demand flexibility in homes)
**Linked PDFs to capture on a PDF pass:** NDIGHG Emissions Plan Guidance (March 2024), Residential Solar PV Purchasing Checklist, "Your guide to labelling" (MEPL guide), SNZ PAS 6011:2023 (residential EV charging), DZ PAS 6014 (residential solar PV & battery), sales/efficiency data XLSX files.

All remaining items are safe to resume — existing files are skipped, so re-running only fills gaps. These are increasingly granular; recommend prioritising by which product regulations Joulie most needs to answer on.
