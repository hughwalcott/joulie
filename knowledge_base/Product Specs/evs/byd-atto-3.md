---
title: "BYD Atto 3 — battery-electric compact SUV"
category: ev
brand: "BYD"
model: "Atto 3"
source_url: https://www.bydnz.nz/cars/atto-3/
source_type: webpage
source_name: "BYD New Zealand (manufacturer)"
publisher: "BYD New Zealand"
nz_availability: confirmed
source_date: 2026-09-04
source_date_basis: retrieval-date   # manufacturer spec page is undated; current model year 2026
retrieved: 2026-09-04
document_id: prod-ev-byd-atto-3
secondary_sources:
  - https://evdb.nz/v/byd-atto-3
  - https://evkx.net/models/byd/atto_3/atto_3/
  - https://www.bydauto.co.nz/news/atto-3-pricing-and-specs
specs:
  body_type: compact SUV
  drivetrain: FWD (single front motor)
  motor_type: permanent magnet synchronous
  motor_power_kw: 150
  motor_torque_nm: 310
  battery_chemistry: LFP (BYD Blade)
  battery_kwh_nominal: [49.92, 60.48]        # Essential / Superior
  battery_kwh_usable_approx: 58.0            # Superior (per EVKX); ~2.5 kWh buffer
  range_km: [345, 420]                        # Essential / Superior
  range_test_standard: WLTP (manufacturer estimate)
  efficiency_wh_per_km_approx: 138            # Superior (per EVKX, 13.8 kWh/100km)
  architecture_v: 400
  ac_charge_kw: 7
  dc_charge_kw_max: [70, 88]                  # Essential / Superior (per evdb.nz)
  charge_port: "Type 2 (AC) + CCS2 (DC)"
  v2l_supported: true
  v2l_power_kw: 3.3
  acceleration_0_100_s: [7.9, 7.3]           # Essential / Superior
  length_mm: 4455
  width_mm: 1875
  height_mm: 1615
  wheelbase_mm: 2720
  warranty_vehicle: "6 years / 150,000 km"
  warranty_battery: "8 years / 160,000 km"
---

# BYD Atto 3

The BYD Atto 3 is a front-wheel-drive compact electric SUV and BYD's first model sold in New Zealand (from 2022). Specifications here are for the currently available NZ model as published on BYD New Zealand's site; usable-capacity and DC-charging detail are cross-checked against the independent EVDB NZ and EVKX databases.

## Variants (current NZ model)

The Atto 3 is offered in two trims distinguished mainly by battery size:

- **Essential** — 49.92 kWh Blade battery, ~345 km WLTP (manufacturer estimate), 0–100 km/h in 7.9 s, DC fast charging up to ~70 kW.
- **Superior** (renamed from "Premium" in mid-2025) — 60.48 kWh Blade battery, ~420 km WLTP (estimate), 0–100 km/h in 7.3 s, DC up to ~88 kW, plus larger 18" wheels, sunroof, roof rails, heated front seats and a 15.6" touchscreen.

Both share a single 150 kW / 310 Nm front motor, a 400-volt architecture, a 7 kW onboard AC charger, and Vehicle-to-Load (V2L) output of up to 3.3 kW.

## Battery and chemistry

Both variants use BYD's Blade battery — a lithium iron phosphate (LFP) design. LFP trades some energy density for thermal stability, safety and cycle life. For the 60.48 kWh (Superior) pack, usable capacity is around 58 kWh after a protective buffer (per EVKX).

## Charging

AC charging is via the onboard 7 kW charger (a full charge takes roughly 8–11 hours on a suitable home charger). DC fast charging peaks near 70 kW (Essential) or 88 kW (Superior); BYD NZ describes a DC session as taking about an hour. The Atto 3 uses the Type 2 (AC) and CCS2 (DC) connectors standard on new EVs sold in New Zealand.

## Dimensions and warranty

The Atto 3 is 4,455 mm long, 1,875 mm wide and 1,615 mm tall, on a 2,720 mm wheelbase. BYD NZ covers the vehicle with a 6-year / 150,000 km warranty and the Blade battery with an 8-year / 160,000 km warranty (whichever comes first), transferable to later owners.

## Note for corpus maintainers

*An upgraded "Atto 3 Evo" (BYD e-Platform 3.0, 800-volt, 60.48/74.88 kWh, rear- or all-wheel drive, DC charging up to ~150–220 kW) has been announced and is confirmed for Australia, but as of retrieval (2026-09-04) its NZ release was not confirmed. Treat the Essential/Superior figures above as the current NZ model; revisit when the Evo's NZ status is settled. WLTP figures are BYD's own estimates and should be reconciled against RightCar's official NZ energy-economy rating when building the authoritative record.*
