# Joulie training data corpus — Electricity Authority Te Mana Hiko (ea.govt.nz)

Generated markdown documents from the Electricity Authority website, for ingestion by the Joulie AI model.
Suggested corpus root: `C:\Joulie-data-ea`, with `your-power\`, `regulations\` and `data-insights\` subfolders. Keep this **separate** from the EECA and Rewiring corpora so provenance and licensing stay clear.

**Scope (as agreed):** Tiers 1–3 of the site scan — the consumer "Your power" hub, the rules/regulations that actually touch a home, and the home-relevant data dashboards. Code Parts are captured as **plain-language summaries**, not verbatim text. The deep wholesale-market machinery, MOSP manager pages, audits/certifications, transmission, and Code Parts 1–5/7/12–17 were deliberately excluded. **26 files.**

## Licensing — clean reuse (the key advantage of this source)

Unlike the EECA and Rewiring corpora (reuse approval pending), EA website content is licensed **CC BY 4.0**, and the **Electricity Industry Act 2010, the Electricity Industry Participation Code 2010, and the Electricity Industry (Enforcement) Regulations 2010 are not subject to copyright** at all. Every file records this in `licence:`. Exceptions on the site are only logos, imagery, and third-party submissions/agreements (none of which are used here).

## Conventions

Same YAML pattern as the other corpora, with EA-specific values:
- `publisher:` = "Electricity Authority Te Mana Hiko (New Zealand government regulator)".
- `content_stance:` = **authoritative** (government regulator). Every file also carries the site's own caveat: **general information, not legal advice; does not replace the Act or Code.** Joulie should present EA-derived rules as "how the rules work" and point to the Code for anything definitive.
- `licence:` = CC BY 4.0 (Code/Act/Enforcement Regs: not subject to copyright).
- `source_date_basis:` = retrieval-date (2026-07-10) for most pages, which are undated; where a rule has a known effective date it's noted in-line.
- Code Part files carry `corpus_note:` flagging that they are plain-language summaries, not the binding text.

## Documents — 26 files

### your-power\ (15) — consumer hub (Tier 1)
solar-power, time-of-use-plans, your-power-bill, compare-and-switch, meters, your-meter, how-electricity-works, new-zealands-electricity-sector, ways-to-save-energy, keeping-the-lights-on, power-outages, consumer-access-and-choice, and the Consumer Care set: consumer-care-obligations (hub), consumer-care-medical-dependence, consumer-care-hard-to-pay. (The hub also folds in the "signing up" and "if your company doesn't meet its obligations" sub-topics.)

### regulations\ (7) — rules that touch a home (Tier 2)
- code-part-6-distributed-generation — **the key rule for home solar/battery**: connection process, inverter standards, the 10kW default export limit, the >10 MW registration threshold.
- code-part-6b-distributor-pricing — network pricing methodologies + Distributed Generation Pricing Principles + the 1 April 2026 peak-export rebate.
- code-part-10-metering — metering standards, accuracy, data security, smart meters.
- code-part-11a-consumer-care — Schedule 11A.1, the binding backing for the consumer-care pages.
- industry-distribution — lines-company role, pricing, losses, distributed generation, obligations (consolidates the Industry > Distribution sub-pages).
- industry-retail — retailer role, obligations, metering, the registry and switching.
- about-act-regulations-code — the Act / Regulations / Code framework and the Authority's statutory objective.

### data-insights\ (4) — home-relevant dashboards (Tier 3)
- shift-to-10kw-export-limits — distributors' progress to a 10kW default residential export limit (in effect 11 May 2026).
- solar-installations-map — solar/battery uptake across NZ (~75,000 homes with solar, ~14,700 with batteries).
- regional-power-prices — average bill by region; low-user vs standard-user; Low Fixed Charge regulations.
- disconnections-for-non-payment — monthly disconnection data + the ~46,900 (2025) post-pay credit declines.

## Cross-source / figures to watch

- **10kW export limit dates:** rules "announced July 2025", the peak-export **rebate** effective **1 April 2026**, and the default-10kW **export limit** effective **11 May 2026** are distinct milestones — cite the specific one. The default replaces older blanket **5kW** residential limits. Across the **29 lines companies**, adoption varies (most at/near 10kW; a few not yet), and a limit below 10kW is allowed only via an industry assessment method.
- **Consumer Care Obligations dates:** two key protections from **1 Jan 2025** (no disconnection of known medically dependent consumers; reasonable fees), the rest from **1 April 2025**.
- **Billing reforms:** clearer plain-language bills, six-month back-bill cap, and annual best-plan checks take effect **30 October 2026**.
- **Prepay vs post-pay:** medically dependent protection applies to **post-pay**; on **prepay**, supply stops when credit runs out. This interacts with the ~46,900 post-pay credit declines (access/equity issue).
- **Who regulates what:** the **Electricity Authority** sets the Code and market rules; the **Commerce Commission** regulates lines-company (transmission + distribution) price-quality, which is ~½–⅔ of recent bill increases. Joulie should not conflate the two regulators.
- **Complements Rewiring's advocacy:** EA's Part 6B / distributed-generation pricing reform and the peak-export rebate are the regulatory counterpart to Rewiring's "symmetrical export tariff" position — one is the rule-maker's account, the other is advocacy. Keep the stances distinct.

## Deliberately excluded (per scope)

- Deep wholesale-market machinery (spot/hedge/FTR/WITS/clearing/settlement/reconciliation/prudential), MOSP manager pages, audits & certifications, participant registry mechanics, transmission (grid-scale), and Code Parts 1–5, 7, 12–17.
- Tier 4 "current reforms" project pages (Distribution connection pricing reform, Energy Competition Task Force, Network connections, Future security and resilience) — not generated, but noted here as the natural next add-on if Joulie needs to speak to in-flight rule changes. The key facts from these (10kW rule, peak rebate) are already captured above.

All items are safe to resume — existing files are skipped, so re-running only fills gaps.
