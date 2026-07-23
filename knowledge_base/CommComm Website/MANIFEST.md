# Joulie training data corpus — Commerce Commission Te Komihana Tauhokohoko (comcom.govt.nz)

Generated markdown documents from the Commerce Commission website, for ingestion by the Joulie AI model.
Suggested corpus root: `C:\Joulie-data-comcom` (or a `commerce-commission\` folder alongside the EA set). Keep the two regulators **cleanly distinguished** — this is deliberately a small, focused add-on to the EA corpus, not a full regulatory corpus.

**Why this exists:** the EA corpus repeatedly references the Commerce Commission because the two are New Zealand's **two primary economic regulators** of electricity — the EA does the wholesale/retail markets and pricing principles; the Commission regulates the **lines (network) monopolies** and therefore the **lines charges** that drive most recent bill increases. Without this, Joulie only had half the answer to "why is my power bill going up?"

**Scope:** the consumer-facing "lines charges & network regulation" slice only — **4 files**. The deep regulatory economics (input methodologies, WACC, asset valuation, individual determinations, reasons/companion papers, reopener mechanics) is deliberately excluded as out of scope for a home-electrification assistant.

## Licensing — clean reuse (CC BY 4.0)

comcom.govt.nz content is Crown copyright, **licensed CC BY 4.0 International** (attribute to the Commerce Commission), verified on the site's copyright page. Exceptions are only logos/emblems/trade marks, the site's design elements, photography/imagery, and any third-party-owned material — none of which are used here. Every file records this in `licence:`.

## Conventions

Same YAML pattern as the EA corpus, with ComCom-specific values:
- `publisher:` = "Commerce Commission Te Komihana Tauhokohoko (New Zealand economic regulator)".
- `content_stance:` = **authoritative** (government economic regulator); general information, not legal advice.
- `licence:` = CC BY 4.0 (Crown copyright).
- `source_date_basis:` = retrieval-date for the standing pages; **document-date (20 Nov 2024)** for the DPP4/RCP4 reset figures.

## Documents — 4 files (lines-charges\)

- **our-role-in-electricity-lines** — the ComCom/EA split; Part 4 of the Commerce Act; the two tools (price-quality paths + information disclosure); which businesses each applies to (price-quality: Transpower + 16 non-consumer-owned distributors; info disclosure: Transpower + all 29); the 12-of-29 consumer-owned exemption; Fair Trading Act; complaints via Utilities Disputes.
- **why-lines-charges-are-changing** — the plain-language "why is my bill going up" explainer (inflation; 5-yearly interest-rate resets vs 2019; higher investment) and how the Commission limits the increases. **The most consumer-useful page**; it's what the EA bill page points toward.
- **price-quality-paths** — default vs customised paths; the DPP components (starting prices, CPI-X rate of change, quality standards); ~5-year resets; Aurora Energy's CPP returning to default in 2026.
- **dpp4-rcp4-bill-impacts** — the current reset (from 1 April 2025): Transpower revenue +43% (smoothed, capped 15%/yr then 5%), ~$10–25/month household impact, distribution ≈ 30% of the bill.

## The anchor fact Joulie should always get right

The Commission **caps the revenue** lines companies can recover and sets **quality standards** — it does **not set the price on your bill**. Retailers set final prices, factoring in lines charges determined in line with the **Electricity Authority's pricing principles**. So: **ComCom = lines revenue + quality; EA = market rules + pricing principles; retailer = the price you actually pay.** Don't attribute one regulator's role to the other.

## Cross-source notes

- **Consistent with the EA corpus:** the EA "Your power bill" and "Regional power prices" files state lines charges are ~½–⅔ of recent increases and regulated by the Commerce Commission; this set explains *why*. The ~$10–25/month regional figure appears in both corpora (EA quotes it from ComCom).
- **Distinct from Rewiring's advocacy:** ComCom's investment-vs-affordability balancing is authoritative regulation, not advocacy; keep it separate from Rewiring's positions on network pricing and "symmetrical export tariffs".
- **Dates to cite carefully:** DPP4/RCP4 both took effect **1 April 2025** (final decisions 20 Nov 2024); the Transpower +43% figure is smoothed via the 15%/15%/5%/5%/5% caps.

## Deliberately excluded

Input methodologies; individual DPP/CPP/IPP determinations, reasons and companion papers; WACC/asset-valuation detail; information-disclosure mechanics; reopener/reconsideration processes; and all non-electricity Commission work (mergers, Fair Trading enforcement generally, telco/fibre, etc.).

Safe to resume — existing files are skipped, so re-running only fills gaps.
