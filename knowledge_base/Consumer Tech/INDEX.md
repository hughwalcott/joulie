# Joulie EECA consumer/technology corpus (gap-fill batch)

Fills the technology and household-cost gaps identified in the coverage check. Merge into the EECA
website corpus (e.g. C:\Joulie-data): the for-homes/, insights/, co-funding-and-support/ and about/
folders slot alongside the existing EECA docs. The technology/ explainers use the non-government
sources the test bank itself cites (US DOE, SolarReviews, Enphase, Trane, Lennox, Explain that Stuff,
KitchenAid, EV Power) — attributed as supplier/explanatory documentation, not government data.
electricity-authority/smart-meters.md is an EA source — it can instead live in the policy corpus.

Conventions match the other corpora (YAML front matter + ⚠ currency notes).

## Documents (16) and the test-bank questions they close

| File | Source | Closes |
| --- | --- | --- |
| for-homes/hot-water-heat-pumps.md | EECA | 1.1, 1.2, 1.3, 1.9 |
| insights/hot-water-heat-pump-technology.md | EECA + Rinnai | 7.1, 7.2, 7.3, 7.4 |
| for-homes/induction-cooktops.md | EECA | 1.6, 1.7, 1.8, 1.9, 2.7 |
| technology/induction-cooktop-technology.md | Explain that Stuff, KitchenAid | 9.1, 9.2, 9.3, 9.4 |
| for-homes/heat-pumps.md | EECA + Trane + Lennox | 8.1, 8.2, 8.3, 8.4, 8.5, 8.6 |
| for-homes/compare-home-heating.md | EECA | 1.10, 1.11 |
| co-funding-and-support/warmer-kiwi-homes.md | EECA | 1.4, 1.5 |
| insights/solar-energy-in-nz.md | EECA | 1.14 |
| insights/plugging-into-the-future-evs.md | EECA | 3.8, 3.11 |
| for-homes/plan-your-solar-system.md | EECA | 6.5, 6.6, 6.7, 6.8, 6.9 |
| technology/how-solar-panels-work.md | US DOE, SolarReviews, Enphase | 6.1, 6.2, 6.3, 6.4 |
| for-homes/charging-your-ev.md | EECA + EV Power | 11.1, 11.4, 11.5, 11.6, 11.7 |
| for-homes/smart-ev-chargers.md | EECA | 11.2, 11.3 |
| co-funding-and-support/gidi-fund.md | EECA | 5.9, 5.10 |
| about/about-eeca.md | EECA | 5.11 |
| electricity-authority/smart-meters.md | Electricity Authority | 12.1, 12.2 |

## Currency updates captured
- Warmer Kiwi Homes: 50/80/90% insulation tiers, 90% heating up to $3,450; the 50% grant now extends to
  middle-income households (Jan 2026); wood/pellet burners NO LONGER funded for new applications from 9 Jan 2026.
- HWHP figures ($284/yr, ~$7,000, 60-75%, 7,000kg) confirmed against the live EECA page.
- Solar share cross-referenced to MBIE (1.4% of generation, 2024) alongside EECA's "up to 6% by 2035" outlook.
- EV fleet ">100,000 by end-2023" framed as a dated milestone; 2026 registrations +96.4% YoY cross-referenced.

## Effect on coverage
Takes topics 1, 6, 9, 12 from weak to solid and completes the "how it works" explainers in 7, 8, 11.
Combined with the EECA batches 1-3, product-specs corpus and policy corpus, this backs essentially all 107 test questions.
