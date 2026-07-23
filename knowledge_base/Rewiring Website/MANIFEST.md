# Joulie training data corpus — Rewiring Aotearoa (rewiring.nz)

Generated markdown documents for ingestion by the Joulie AI model, from Rewiring Aotearoa's website.
Suggested corpus root: C:\Joulie-data-rewiring, with `learn\`, `go-electric\` and `reports\` subfolders. Keep this **separate** from the EECA corpus so provenance and licensing stay clear.

**Scope (as requested):** the "Learn" (educational) and "Go Electric" (practical) material, plus the research **Reports** (folded in at your request — they're well-regarded in the sector). All news, success stories, submissions and event pages are excluded.

**Status:** the Learn/Go Electric sections, the research reports, and the full set of "watt now" explainers are complete — **46 files**. Remaining optional items (policy pages, EV-charging tool page) are listed at the end.

## Conventions

Same as the EECA corpus, with two Rewiring-specific additions in the YAML front matter:

- **`content_stance`** — records that this is advocacy/educational/research content representing Rewiring Aotearoa's *stated positions* (Rewiring is an advocacy non-profit). Claims are attributed to Rewiring ("Rewiring's position/argument…") so Joulie can distinguish advocacy from neutral fact. On reports, it also notes they are Rewiring's own modelling under stated assumptions (and, where relevant, who peer-reviewed them).
- **`licence`** — reuse approval pending, to be sought from Rewiring Aotearoa (readily given as Electrify the Hutt is a Rewiring community group). No site-wide Creative Commons statement found.

Reports carry `authors` where known, and `source_date`/`source_date_basis` = document-date where a release date is known (Electric Homes 18 Mar 2024; Machine Count 6 May 2025), else retrieval-date.

## FAQ capture method (unchanged)

The 17 `learn\` files were built faithfully from the full Electrification FAQ that the homepage renders inline, grouped under Rewiring's own topic scheme, each with a `corpus_note` recording the method.

## Completed documents — 32 files

### go-electric\ (9)
Guides: get-started, space-heating-and-cooling, water-heating, cooktops, electric-cars, solar, home-batteries.
Tools: electric-calculator, make-a-plan.

### learn\ (17 — the full Electrification FAQ)
the-basics, solar, batteries, vehicles, hot-water-heating, space-heating, cooking, finance, energy-system, gas, emissions, farms, buildings, mining, jobs, geoengineering, how-to-speed-things-up.

### learn\explainers\ (14 — the full "watt now" explainer series)
Long-form explainers, each with its publication date in the front matter (`source_date_basis: document-date`) and author(s) where shown:
- electricity-means-efficiency (2024-09-04, Dr David Hall, Jenny Sahng, Dominic Thorn) — flagship: electrifying needs fewer materials and less energy than people think; "doing more with less".
- closing-the-loop (2024-10-14, David Hall + Circularity) — the circular-economy companion; recycling/reuse of batteries and panels.
- energy-use-in-new-zealand (2024-11-20) — only ~26% of total energy is electricity; use more electricity, less energy overall.
- why-going-electric-wins-on-emissions (2025-01-31) — embodied vs operational emissions; lifetime payback; flight comparisons.
- why-solar-makes-sense (2025-02-24) — the four-part case for rooftop solar.
- why-electric-vehicles-matter (2025-03-26) — we don't have to give up cars, just make them electric.
- show-me-the-money-electric-economics (2025-04-30) — "swap fuel for finance"; $52k EV vs $39k ICE worked example.
- what-could-the-future-look-like (2025-05-22) — scenario piece: two possible 2030 futures.
- scale-and-speed-why-the-climate-needs-evs (2025-07-28) — mode-shift + EVs are complementary; electrification is the biggest step-change.
- a-bad-case-of-gas (2025-09-09) — gas shortage, price spikes, deindustrialisation, what replaces gas (live policy, time-stamped).
- the-case-for-energy-loans (2025-12-04) — why bank green loans fall short; Energy IMPACT loans via the RAS.
- sun-in-a-socket-plug-in-solar (2026-05-21) — plug-in/balcony solar for renters.
- solving-the-dry-year (2026-06-03) — distributed renewables + flexibility vs new thermal/LNG for dry years.
- electrification-for-humans-people-power (2024-07-12, David Hall & Mike Rewi) — the values piece: "panoptic vision", beyond carbon tunnel vision.

**Explainer capture note:** four explainers (electricity-means-efficiency, closing-the-loop, and via the /explained index) were captured in full from fetched page text. The others were reconstructed faithfully from Rewiring's own reported passages of each explainer plus closely-matching FAQ/report material, because the individual Webflow pages weren't directly fetchable; each such file carries a `corpus_note` flagging this and pointing Joulie to the source URL for the complete article. The `this-car-can` EV-publicity campaign is deliberately excluded, per instruction.

### reports\ (6)
- electric-homes — flagship (2024) "electrification tipping point"; **includes the 2025 update** (savings roughly doubled: up to ~$3,000/yr / net $45,000 over 15 yrs; ~$9.1b/yr by 2040; reviewed by Cameron Bagrie).
- investing-in-tomorrow — "the electrification opportunity"; national scale; co-authored by RBNZ chief economist Paul Conway; ~$10.7b/yr by 2040.
- the-machine-count — inventory of ~10m fossil-fuel machines (with Ara Ake + EECA); 84% ready today; top 6m save ~$3.7b + 7.5 Mt CO₂e/yr.
- delivered-cost-of-energy — decision-maker argument that consumer "delivered cost" (not generation cost) should drive investment decisions.
- electric-farms — farm electrification; Forest Lodge Orchard case study (~$40k/yr saved).
- symmetrical-export-tariffs — proposal to pay customers fairly for peak exports, making batteries "bankable".

## Cross-source / internal figures to watch

- **Warmer Kiwi Homes grant:** Rewiring's space-heating guide cites 80% (May 2024); EECA's programme page (authoritative) says up to 90% / $3,450. Flagged in `go-electric/space-heating-and-cooling.md`.
- **Electric Homes savings figures evolve:** 2024 = ~$1,500/yr (or ~$4,500 with 1% loan); 2025 update ≈ doubled (~$3,000/yr net over 15 yrs; ~$7,600/yr excl. upfront). Both are recorded in `reports/electric-homes.md` with dates, so Joulie should cite the year.
- **National savings figures differ by report/scope:** Investing in Tomorrow ≈ $10.7b/yr by 2040; the 2025 Electric Homes refresh ≈ $9.1b/yr by 2040; Machine Count ≈ $3.7b/yr for the top 6m machines. These measure different things (whole-economy vs household stock vs priority-machine subset) — not contradictions.

## Remaining — optional, not yet processed

- **EVs and Charging tool page** ("This Car Can" info, rewiring.nz/this-car-can-info) and the Videos index — **deliberately excluded** ("This Car Can" was an EV-publicity campaign, per instruction). Skip unless Joulie needs the EV-charging how-to specifically.
- **Policy items** (advocacy rather than research): Ratepayer Assistance Scheme / "home energy fund" (captured in the Electric Homes 2025 update and the energy-loans explainer) and the 2025 Policy Manifesto. The manifesto has some distinct national figures (e.g. avoid 212 Mt of emissions by 2050; ~$15b/yr on 3.1 Mt of imported fossil fuels; five cross-party "asks"). Fold in if Joulie should speak directly to Rewiring's policy platform.

All remaining items are safe to resume — existing files are skipped, so re-running only fills gaps.
