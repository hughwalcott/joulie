---
title: "Enphase IQ Battery 5P — modular AC-coupled home battery"
category: battery
brand: "Enphase"
model: "IQ Battery 5P"
source_url: https://enphase.com/en-au/download/iq-battery-5p-anz
source_type: datasheet-pdf
source_name: "Enphase IQ Battery 5P datasheet (ANZ)"
publisher: "Enphase Energy, Inc."
nz_availability: confirmed
source_date: 2026-01-01
source_date_basis: datasheet-revision   # Rev. 2 updated January 2026 (per review sources); confirm on ANZ sheet
retrieved: 2026-09-04
secondary_sources:
  - https://cleanenergycouncil.org.au/industry-programs/products-program/batteries
  - https://enphase.com/store/storage/gen3/iq-battery-5p
document_id: prod-battery-enphase-iq-battery-5p
specs:
  usable_kwh: 5.0
  chemistry: "LFP (cobalt-free lithium iron phosphate)"
  integrated_inverter: true            # six embedded grid-forming microinverters
  coupling: "AC-coupled"
  modular: true
  continuous_power_kw: 3.84
  peak_power_kw: "7.68 (3 s) / 6.14 (10 s)"
  round_trip_efficiency_pct: 96        # AC-to-battery-to-AC at 50% rating, 25C
  depth_of_discharge_pct: 100
  nominal_dc_voltage_v: 76.8
  operating_temp_charge_c: "-20 to 50"
  operating_temp_discharge_c: "-20 to 55"
  optimum_temp_c: "0 to 30"
  enclosure_rating: "IP55 (microinverter IP67)"
  dimensions_mm: "980 x 550 x 188"
  weight_kg: 78.9
  warranty: "15 years / 6,000 cycles (ANZ) — see note"
  requires: "IQ System Controller 3/3G for grid-tied and backup operation"
---

# Enphase IQ Battery 5P

The Enphase IQ Battery 5P is a modular, AC-coupled home battery using cobalt-free lithium iron phosphate (LFP) cells, with six grid-forming microinverters built into each unit. Specifications here are from Enphase's ANZ datasheet, cross-checked against the Enphase store and the Clean Energy Council approved-batteries list.

## Key specifications

Each unit provides 5.0 kWh of usable energy (LFP supports 100% depth of discharge, so the 5.0 kWh is genuinely usable rather than a padded headline figure), with 3.84 kW continuous power and peaks of 7.68 kW for 3 seconds and 6.14 kW for 10 seconds. Round-trip efficiency is about 96% (AC-to-battery-to-AC at 50% rating, 25 °C). The nominal DC voltage is 76.8 V, the enclosure is IP55 (microinverters IP67), and each unit measures 980 × 550 × 188 mm at about 78.9 kg installed. Multiple units combine for larger systems, and an IQ System Controller 3/3G is required for grid-tied and backup operation.

## Temperature and warranty

The battery charges from −20 °C to 50 °C and discharges from −20 °C to 55 °C (optimum 0–30 °C). Enphase's ANZ datasheet lists a 15-year warranty; capacity-retention and cycle terms vary by region and datasheet revision (some markets quote 6,000 cycles / ≥60% retention, others 4,000 cycles / ≥70%).

## Note for corpus maintainers

*Usable capacity notes: it includes a 2% safety-critical reserve for long outages plus 3% held for battery electronics at night. Warranty terms (cycle count and retention percentage) differ across regional datasheets and revisions — record the ANZ sheet's figures for the NZ record and confirm on the current revision (reported Rev. 2, January 2026). The ANZ datasheet notes CEC listing / rebate readiness; confirm the exact model on the Clean Energy Council approved-batteries list. Being AC-coupled with built-in microinverters, the IQ Battery 5P pairs naturally with Enphase microinverter solar systems.*
