# Joulie product-specs corpus — gaps & consistency review

**Reviewer:** Claude (Opus 4.8) · **Date:** 2026-09-04
**Scope:** the 24 product data files under `product-specs/` (EVs, solar panels, home batteries, hot water heat pumps, space heating heat pumps, induction cooktops). Excludes `INDEX.md` and `COWORK-TASK-products.md`.
**Method:** front matter of every file parsed and audited programmatically (schema completeness, `document_id` uniqueness, date basis, source region, and per-category `specs` key consistency), plus manual reading.

---

## 1. What's solid

- **Provenance layer is complete and uniform.** All 24 files carry the full 14-field schema (`title, category, brand, model, source_url, source_type, source_name, publisher, nz_availability, source_date, source_date_basis, retrieved, secondary_sources, document_id`) plus a `specs` block. No required field is missing anywhere.
- **`document_id` values are all unique; none null.**
- **Test-basis discipline held across the corpus.** Performance figures are tagged with the standard/conditions they were measured under: WLTP (EVs), STC 1000 W/m²/25 °C/AM1.5 (PV modules), AS/NZS 5125 vs BS EN 14511 (hot water heat pumps), ZERL star ratings (space heating). This is the single most important property for trustworthy training data and it is consistent.
- **Discrepancies are flagged, not silently resolved.** Where sources disagree, each file records the conflict in a maintainer note rather than guessing.

## 2. Consistency issues to fix (schema drift, not factual errors)

The `specs` blocks were designed per-product, so their structure diverges. Three issues would trip up structured ingestion:

1. **Three different shapes for "this model has multiple variants."**
   - 6 of 8 EVs use a `variants:` list.
   - BYD Atto 3 uses flat fields with list values (e.g. `battery_kwh_nominal: [49.92, 60.48]`).
   - Nissan Leaf uses named nested blocks (`third_gen_2026:` / `prior_gen_2019_2024:`).
   - Same pattern in batteries: modular units (BYD `hvs`/`hvm`, Sigenergy `module_classes_kwh`) nest capacity, so a query for `usable_kwh` matches only 2 of 4 battery files even though all four have a usable capacity.
   - **Fix:** adopt one canonical representation for multi-variant/modular products (recommend a `variants:` list of objects, each with the same key set).

2. **`dimensions_mm` — inconsistent axis order, often unlabelled.**
   - W×H×D: Fisher & Paykel, Mitsubishi (space heating). H×W×D: Reclaim, Bosch. Bare numbers, no axes: all batteries and all panels (e.g. `1099 x 609 x 193`).
   - **Fix:** pick one order (recommend `W x H x D`) and always label it; for PV modules state length×width×thickness explicitly.

3. **Same concept under different keys.**
   - COP: `cop` (Reclaim, Rinnai) vs `cop_approx` + `cop_note` (Mitsubishi QUHZ).
   - Weight: `weight_kg` vs `hp_unit_weight_kg` vs `full_system_weight_kg`.
   - EV range test standard is top-level in 7 files but nested inside the Leaf's generation block.
   - **Fix:** normalise to a shared key vocabulary per category; keep the value's test basis attached to the value.

*These are cheap to correct with a one-pass normalisation and do not require re-researching any facts.*

## 3. Coverage gaps

Every category has a representative first batch (EVs 8; batteries 4; solar panels, hot water heat pumps, space heating heat pumps, induction cooktops 3 each), but depth is uneven and some structural holes stand out:

| Gap | Detail | Priority |
| --- | --- | --- |
| **No solar inverters** | Panels and batteries covered, but the inverter (string / micro / hybrid) is a core system component and its own class — the most significant single omission. | High |
| **Space heating too narrow** | All 3 are single-split high-wall from 2 brands (Mitsubishi ×2, Fujitsu ×1). Daikin and Panasonic (both major in NZ) absent; no multi-split or ducted. | High |
| **Batteries all LFP** | No NMC example for contrast; sonnen / Fronius / Pylontech missing. | Medium |
| **EVs: 2 not on sale new** | Nissan Leaf (`incoming`), BYD Dolphin (`used-only`) — honestly flagged, but weight accordingly. No ute/commercial (BYD Shark, LDV) or premium marque. | Medium |
| **Induction: form factors** | No 80/90 cm or full-flex models; brands Miele/Electrolux/Samsung not covered. | Low |

## 4. Currency / provenance risks

- **20 of 24 files use `source_date_basis: retrieval-date`** (manufacturer pages are undated). This weakens the update-detection purpose of dating: a retrieval date records when the page was read, not when its content last changed, so the "has the source moved on?" re-ingestion trigger is unreliable for ~83% of the corpus. Only the 4 files anchored on dated datasheets (Trina, Tesla Powerwall 3, BYD Battery-Box, Enphase) support this well.
  - **Mitigation:** prefer dated PDF datasheets over undated web pages where both exist; lean on the authoritative registries (RightCar, CEC lists, Energy Rating database) which carry revision/approval dates.
- **Region mismatch on batteries:** all 4 battery files are sourced from AU/ANZ datasheets — valid for NZ's shared 230 V / 50 Hz grid, but the exact NZ-supplied variant is unverified. 2 of 3 solar-panel files use global manufacturer pages (no NZ/AU-specific source); solar relies on the (Australian) CEC list.
- **Open, deliberately-unresolved discrepancies** (flagged in-file, still to be settled against authoritative sources): MG4 battery chemistry (NCM vs LFP); Tesla Powerwall 3 chemistry (LFP vs NMC); Sigenergy SigenStor — `nz_availability: likely` and an unverified Nov-2025 recall mention; BYD Dolphin new-sale status.

## 5. Cross-corpus note

Reviewed against the EECA website corpus: **no contradictions found.** Both corpora reference the same E3 / Energy Rating (GEMS) framework, which is consistent. Opportunity: cross-reference product files to the EECA explainer docs (e.g. link induction-cooktop files to EECA's efficiency page; link heat-pump files to EECA's selection guidance) so Joulie can connect "how it works" to "specific product."

## 6. Recommended next actions (priority order)

1. **Normalisation pass on `specs` blocks** — one canonical variant/modular structure; labelled, consistently-ordered dimensions; unified COP/weight/test-standard keys. (No re-research required.)
2. **Fill the solar-inverter gap** and add **Daikin + Panasonic** space heating; add multi-split/ducted configs.
3. **Re-anchor files onto dated datasheets** where available, to make re-ingestion triggers reliable.
4. **Resolve the open discrepancies** in §4 against authoritative registries (RightCar, CEC approved-products lists, Energy Rating database).
5. Optionally, **expand thin categories** (NMC battery, premium/ute EVs, extra induction form factors) toward a target count per category.
