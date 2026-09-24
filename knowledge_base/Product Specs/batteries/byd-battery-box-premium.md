---
title: "BYD Battery-Box Premium HVS / HVM — modular home battery"
category: battery
brand: "BYD"
model: "Battery-Box Premium HVS / HVM"
source_url: https://bydbatterybox.com/uploads/downloads/BYD%20Battery-Box%20Premium_Datasheet_HV-AU%20V1.2%20EN-5eec6422498ad.pdf
source_type: datasheet-pdf
source_name: "BYD Battery-Box Premium datasheet (HV-AU — applies to NZ)"
publisher: "BYD Company Ltd. (BYD Battery-Box)"
nz_availability: confirmed
source_date: 2023-05-30
source_date_basis: datasheet-revision   # datasheet V1.7 dated 2023-05-30; AU V1.2 also referenced — confirm latest
retrieved: 2026-09-04
secondary_sources:
  - https://cleanenergycouncil.org.au/industry-programs/products-program/batteries
  - https://www.windandsun.co.uk/products/byd-battery-box-premium-hvs-hvm
document_id: prod-battery-byd-battery-box-premium
specs:
  chemistry: "LFP (cobalt-free lithium iron phosphate)"
  integrated_inverter: false
  coupling: "DC (high-voltage; requires compatible external hybrid inverter)"
  modular: true
  hvs:
    module_kwh: 2.56
    modules: "2 to 5"
    usable_kwh_range: "5.12 to 12.8"
    max_parallel_kwh: 38.4
    nominal_voltage_v: "204 to 512"
    max_output_current_a: 25
    peak_output_current_a: "50 (5 s)"
  hvm:
    module_kwh: 2.76
    modules: "3 to 8"
    usable_kwh_range: "8.28 to 22.08"
    max_parallel_kwh: 66.2
  round_trip_efficiency_pct: 96
  depth_of_discharge_pct: 100
  operating_temp_c: "-10 to +50"
  enclosure_rating: "IP55"
  warranty_yr: 10
  compatible_inverters: "Fronius, GoodWe, Kostal, SMA, SolarEdge and other approved HV battery inverters"
  standards: "VDE 2510-50"
---

# BYD Battery-Box Premium HVS / HVM

The BYD Battery-Box Premium is a modular high-voltage home/commercial battery using BYD's cobalt-free lithium iron phosphate (LFP) cells. Unlike the all-in-one Tesla Powerwall, it has no built-in inverter and must be paired with a compatible external high-voltage hybrid inverter. Specifications here are from BYD's AU datasheet (which applies to NZ) and the HVS/HVM datasheet V1.7, cross-checked against the Clean Energy Council approved-batteries list.

## Modular capacity

The system uses stackable battery modules connected in series, in two families:

- **HVS** — 2.56 kWh modules, 2 to 5 per stack, for 5.12 to 12.8 kWh usable; up to three stacks in parallel gives a maximum of 38.4 kWh.
- **HVM** — 2.76 kWh modules, 3 to 8 per stack, for about 8.3 to 22.1 kWh usable; up to three stacks in parallel gives a maximum of 66.2 kWh.

This modularity lets a system be sized to the household and expanded later by adding modules or stacks.

## Performance and durability

The LFP chemistry supports 100% depth of discharge with a charge/discharge (round-trip) efficiency of about 96%. The system operates from −10 °C to +50 °C, carries an IP55 rating, meets the VDE 2510-50 safety standard, and has a 10-year product warranty. It is compatible with leading single- and three-phase high-voltage battery inverters (Fronius, GoodWe, Kostal, SMA, SolarEdge and others).

## Note for corpus maintainers

*Usable energy is quoted at 100% DoD, 0.2C, 25 °C, and "system usable energy may vary with different inverter brands." Multiple datasheet revisions exist (HVS/HVM V1.7 dated 2023-05-30; AU V1.2 also in circulation) plus separate HVE, HVL and LVS families and newer generations — confirm the exact model/family and revision, and cross-check the Clean Energy Council approved-batteries list for the authoritative NZ record. Because this battery needs a matched external inverter, the delivered performance depends on the paired inverter.*
