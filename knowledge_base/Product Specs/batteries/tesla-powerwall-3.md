---
title: "Tesla Powerwall 3 — home battery with integrated inverter"
category: battery
brand: "Tesla"
model: "Powerwall 3"
source_url: https://energylibrary.tesla.com/docs/Public/EnergyStorage/Powerwall/3/Datasheet/en-au/Powerwall-3-Datasheet-AU-EN.pdf
source_type: datasheet-pdf
source_name: "Tesla Powerwall 3 datasheet (AU/EN — applies to NZ 230 V / 50 Hz)"
publisher: "Tesla, Inc."
nz_availability: confirmed
source_date: 2025-01-01
source_date_basis: datasheet-revision   # "2025 Powerwall 3 Datasheet"; confirm latest revision
retrieved: 2026-09-04
secondary_sources:
  - https://cleanenergycouncil.org.au/industry-programs/products-program/batteries
  - https://www.stratfordenergy.co.uk/tesla-powerwall-3-specifications-key-features-benefits/
document_id: prod-battery-tesla-powerwall-3
specs:
  usable_kwh: 13.5
  chemistry: "LFP (reported) — see maintainer note"
  integrated_inverter: true
  coupling: "DC-coupled solar (integrated PV inputs) + AC"
  nominal_output_power_kw: [5, 10, 11.04]   # AU model variants at 230 VAC
  grid: "230 VAC single phase, 50 Hz"
  max_continuous_current_a: 48
  load_start_capability_lra: 185
  round_trip_efficiency_pct: 89             # solar-to-battery-to-grid; see note
  solar_to_home_efficiency_pct: 97.5
  max_continuous_charge_kw: 5
  scalable: "up to 4 units = 54 kWh / 44 kW"
  operating_temp_c: "-20 to 50"
  enclosure_rating: "IP55 (IP67 battery & power electronics)"
  dimensions_mm: "1099 x 609 x 193"
  weight_kg: 130
  warranty_yr: 10
---

# Tesla Powerwall 3

The Tesla Powerwall 3 is an all-in-one home battery that integrates a battery, a solar inverter and a system controller in one wall- or floor-mounted unit — a change from the Powerwall 2, which was an AC-coupled battery needing a separate solar inverter. Specifications here are from Tesla's Australian datasheet (230 VAC, 50 Hz single phase), which applies to the New Zealand grid; cross-checked against the Clean Energy Council approved-batteries list.

## Key specifications

A single Powerwall 3 stores 13.5 kWh of usable energy. In the AU/NZ market it is offered in 5 kW, 10 kW and 11.04 kW continuous AC output variants, with a 185 A locked-rotor-amp load-start capability able to start large motors (e.g. heat-pump and pool-pump compressors). The unit has integrated solar (DC) inputs plus AC coupling, an IP55 enclosure (IP67 for the battery and power electronics), an operating range of −20 °C to 50 °C, and a 10-year warranty. It measures 1099 × 609 × 193 mm and weighs about 130 kg. Up to four units can be combined for 54 kWh of storage and 44 kW of power.

## Efficiency (read carefully)

Two different efficiency figures are commonly quoted and mean different things. The **round-trip efficiency is about 89%** (solar → battery → grid, i.e. energy stored and later returned). The **97.5% figure is solar-to-home** — a one-way conversion of PV through the built-in inverter to the house, not a storage round trip. For modelling stored-energy losses, use ~89%.

## Note for corpus maintainers

*Battery chemistry is inconsistently reported: most 2026 sources state lithium iron phosphate (LFP), a change from the Powerwall 2's NMC; some sources still list NMC. Tesla does not print the chemistry on the datasheet, so this is flagged as "reported LFP". Do not conflate the 97.5% solar-to-home figure with round-trip efficiency (~89%). The source is the 2025 AU datasheet — check energylibrary.tesla.com for a newer revision, and confirm the exact model variant on the Clean Energy Council approved-batteries list for the authoritative NZ record.*
