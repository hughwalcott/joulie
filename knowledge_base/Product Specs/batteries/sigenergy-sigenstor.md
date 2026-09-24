---
title: "Sigenergy SigenStor — modular all-in-one home battery / energy hub"
category: battery
brand: "Sigenergy"
model: "SigenStor"
source_url: https://www.gridly.com.au/home-batteries/sigenergy-specs/
source_type: webpage
source_name: "Sigenergy SigenStor spec references (AU) — verify against manufacturer datasheet"
publisher: "Sigenergy"
nz_availability: likely   # dominant in AU; sold in NZ via distributors — confirm NZ distributor / CEC listing
source_date: 2026-09-04
source_date_basis: retrieval-date
retrieved: 2026-09-04
secondary_sources:
  - https://cleanenergycouncil.org.au/industry-programs/products-program/batteries
  - https://ecoaspireenergy.com.au/sigenergy-review/
  - https://connectenergy.com.au/guides/sigenergy-battery-review-australia/
document_id: prod-battery-sigenergy-sigenstor
specs:
  architecture: "5-in-1 all-in-one: hybrid inverter (energy controller) + stackable LFP battery modules + BMS + EMS + optional DC EV charger"
  coupling: "DC-coupled"
  chemistry: "LFP (LiFePO4, prismatic cells)"
  phase_options: "single-phase (SP) and three-phase (TP)"
  module_classes_kwh: [5.0, 6.0, 8.0]        # AU commonly 6 kWh and 8 kWh; usable ~5.2 / 5.84 / 7.8
  module_usable_kwh_examples: "5.0-class ~5.2; 6.0-class ~5.84; 8.0-class ~7.8"
  modules_supported: "1 to 6 per controller"
  max_capacity_kwh_approx: 48.36              # 6 x 8-kWh-class; smaller with smaller modules
  round_trip_efficiency_pct: "94-95 (independent) / up to 98.4 (manufacturer) — see note"
  depth_of_discharge_pct: 100
  operating_temp_c: "-20 to 60"
  enclosure_rating: "IP66 (SigenStor) — EC variant reported IP55; see note"
  ev_charging_option: "bidirectional DC EV charger 12.5 or 25 kW; V2H / V2G ready"
  backup: "0 ms UPS-grade with optional Sigen Gateway"
  warranty: "10 years, >=70% usable capacity, or module throughput (e.g. 15.85 MWh for 5 kWh module / 23.77 MWh for 8 kWh module)"
  cec_listed: true
---

# Sigenergy SigenStor

The Sigenergy SigenStor is a modular "5-in-1" home energy system that combines a hybrid inverter (the energy controller), stackable LFP battery modules, a battery management system, an energy management system, and an optional DC EV charger in a single tower. Sigenergy was founded in 2022 by former Huawei inverter engineers and has rapidly become one of the best-selling residential battery brands in Australia. Specifications here are drawn from Australian spec references and reviews; they should be reconciled against Sigenergy's official datasheet and the NZ distributor before being treated as authoritative for New Zealand.

## Architecture and capacity

The SigenStor is a DC-coupled system available in single-phase (SP) and three-phase (TP) variants. It uses stackable prismatic LFP modules — commonly 6 kWh and 8 kWh classes in Australia (with 5 kWh and 10 kWh classes also referenced) — giving roughly 5.2 kWh (5.0 class), 5.84 kWh (6.0 class) or 7.8 kWh (8.0 class) usable per module. One controller supports 1 to 6 modules, scaling to roughly 48 kWh, with LFP's 100% depth of discharge. A distinguishing feature is genuinely integrated EV charging: an optional bidirectional DC EV charger (12.5 kW or 25 kW) with V2H/V2G readiness, rather than bolt-on AC charging.

## Performance and durability

LFP chemistry gives strong thermal stability across a −20 °C to 60 °C operating range, with an IP66 outdoor rating and 0 ms UPS-grade backup when the Sigen Gateway is added. Round-trip efficiency is quoted by the manufacturer as up to 98.4%, while independent Australian reviews report about 94–95% DC round-trip — use the lower, independent figure for conservative modelling. Sigenergy provides a 10-year product and performance warranty guaranteeing at least 70% of usable capacity, or a module energy-throughput figure (e.g. 15.85 MWh for a 5 kWh module, 23.77 MWh for an 8 kWh module), whichever comes first.

## Note for corpus maintainers

*Several caveats. (1) NZ availability: the sourced specs are Australia-centric; confirm the current NZ distributor and the exact model on the Clean Energy Council approved-batteries list (Sigenergy is CEC-listed) before treating figures as NZ-authoritative — hence `nz_availability: likely`. (2) Efficiency: the manufacturer's "up to 98.4%" and independent "94–95%" figures differ; both are recorded, prefer the independent figure. (3) Variants and generations: module sizing and naming vary across markets and revisions (AU SigenStor with 2026 "Neo" modules; a "SigenStor EC" line in Europe with a reported IP55 rating and 95.5% efficiency) — confirm the exact variant. (4) A November 2025 recall was referenced by one Australian source; verify any affected models/batch and current safety status before relying on this record. This file uses a retrieval date pending a dated manufacturer datasheet.*
