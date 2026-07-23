# Joulie training data corpus — Ministry of Business, Innovation & Employment (mbie.govt.nz)

Generated markdown documents from MBIE's energy statistics, modelling and policy pages, for ingestion by the Joulie AI model.
Suggested corpus root: `C:\Joulie-data-mbie`, with `energy-data\` and `policy\` subfolders. Plus a **cross-corpus** resources file at the root (see below). Keep separate from the other corpora so provenance stays clear.

**Why this exists:** MBIE is the **policy-and-statistics layer** above the two regulators. It's the authoritative primary source for NZ energy *numbers* (the figures that appear second-hand in the EECA, Rewiring, EA and ComCom material) and for the future-demand modelling and the official gas-supply picture. It fills the one genuine gap identified in the source review: official statistics + the authoritative counterpart to the advocacy "gas transition" story. **6 corpus files + 1 cross-corpus resources file.**

## Licensing — clean reuse (CC BY)

MBIE energy content is Crown copyright, licensed **CC BY 4.0** on current publications (verified on the *Energy in New Zealand* release), with a few older pages still carrying **CC BY 3.0 NZ**. Attribution: "Ministry of Business, Innovation & Employment". Each file records the applicable licence; where a page showed the 3.0 NZ notice, that's noted in-file. MBIE also attaches a standard **no-warranty** disclaimer to its statistics (accuracy/completeness not guaranteed) — reflected in the `content_stance`.

## Conventions

Same YAML pattern as the other corpora, with MBIE-specific values:
- `publisher:` = "Ministry of Business, Innovation & Employment Hīkina Whakatutuki (New Zealand government)".
- `content_stance:` = **authoritative official statistics/policy**; figures are point-in-time and revised; scenarios (EDGS) are conditional, not forecasts.
- `source_date_basis:` = document-date where a publication/edition date is known (Energy in NZ landing updated 5 Mar 2026; EDGS 2024 = July 2024), else retrieval-date.
- Statistics files carry a `corpus_note` telling Joulie to cite the edition/year and use the source Excel tables for the definitive series.

## Documents — 6 corpus files

### energy-data\ (4)
- **energy-in-new-zealand-overview** — the flagship annual statistics publication; latest headline figures (2024 data: renewables a record 45.5% of total primary energy supply; 85.5% of electricity renewable; gas consumption lowest since 2011; coal generation +118%); sub-topics; how to access the Excel data tables.
- **electricity-statistics** — generation mix and renewable share (88.1% in 2023, 85.5% in 2024); demand by sector (~⅓ households, ~⅓ industry, ~¼ commercial; Tiwai the largest user); first utility-scale solar farm (Kohirā); and the EV signal (transport electricity +42.4%; 76,506 BEVs end-2023 vs 29,292 end-2021).
- **renewables-statistics** — the renewable resource breakdown (hydro, geothermal, wind, solar, biomass/biogas/biofuels); the geothermal-efficiency point; renewables used for direct heat too.
- **gas-statistics** — the authoritative gas supply/demand picture (Taranaki fields, ongoing depletion, consumption lowest since 2011). The **factual counterpart** to Rewiring's advocacy explainer "A bad case of gas".

### policy\ (2)
- **edgs-scenarios** — official future electricity demand/generation scenarios to 2050; the link between MBIE modelling, the Commerce Commission's Transpower investment test, and grid charges; key insights (2,700 MW of coal/baseload-gas retired by 2050, rising renewables and BESS, energy emissions ~17 Mt CO₂-e by 2050 in Reference).
- **energy-hardship** — MBIE's official definition (June 2022), the five measures and annual reporting; the policy/measurement layer above the EA Consumer Care rules and ComCom affordability work.

## Cross-corpus resource — 1 file (at corpus root)

- **RESOURCES-FOR-FURTHER-INFORMATION.md** — the "Resources for further information" section requested: a signposting index of **verified, first-party interactive tools/calculators** across all processed sites (EECA/Gen Less home-energy-savings and appliance calculators + Warmer Kiwi Homes eligibility; Rewiring's electric calculator and Make a Plan; the EA's Billy, Your meter, solar map, regional-prices and 10kW dashboards; MBIE's Energy-in-NZ data tables, EDGS, and LCOE tool; ComCom's disclosure graphics). Every URL was checked live during the build. Non-government comparison sites (SEANZ, Consumer NZ, Powerswitch) are excluded per instruction; NIWA SolarView is listed once, clearly flagged as external. **This file is intended to live at the root of the combined Joulie dataset**, not just the MBIE folder, since it spans all sources. (Individual corpus files also cross-reference the relevant tool inline — e.g. the EA solar page links the solar map; the time-of-use page links Billy.)

## Figures / cautions to watch

- **Cite the year:** MBIE statistics are annual and revised. The renewable-electricity share moves with hydrology (88.1% in 2023, a strong hydro year; 85.5% in 2024, a dry year with more coal) — so a single "% renewable" figure is misleading without its year.
- **Two "renewable share" measures:** ~45.5% is the renewable share of **total primary energy** (all energy); ~85–88% is the renewable share of **electricity** only. Don't conflate them — this is the same distinction Rewiring makes ("only ~30% of total energy is renewable").
- **EDGS are scenarios, not forecasts** — present the numbers as conditional on assumptions.
- **Gas:** MBIE gives the factual declining-supply trend; keep any predictions about future gas prices or the pace of decline attributed to whoever makes them (e.g. Rewiring's advocacy vs MBIE's data).

## Deliberately excluded

Deep petroleum/reserves and fuel-logistics detail, oil/liquid-fuels series beyond the transition context, the New Zealand Energy Quarterly back-catalogue, consultation/submission pages, hydrogen roadmap, and all non-energy MBIE work. Non-government tool sites (SEANZ, Consumer NZ, Powerswitch) excluded per instruction.

Safe to resume — existing files are skipped, so re-running only fills gaps.
