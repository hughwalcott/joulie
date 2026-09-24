---
title: "BYD Dolphin — battery-electric hatchback"
category: ev
brand: "BYD"
model: "Dolphin"
source_url: https://www.bydnz.nz/cars/dolphin/
source_type: webpage
source_name: "BYD New Zealand (manufacturer) / BYD NZ dealers"
publisher: "BYD New Zealand"
nz_availability: used-only   # sold new in NZ 2023 to ~April 2026; used-only thereafter (per EVDB NZ) — see note
source_date: 2026-09-04
source_date_basis: retrieval-date
retrieved: 2026-09-04
document_id: prod-ev-byd-dolphin
secondary_sources:
  - https://evdb.nz/v/byd-dolphin
  - https://ateco.co.nz/media/arrival-of-the-byd-dolphin
  - https://www.bydauckland.co.nz/dolphin
specs:
  body_type: hatchback (C-segment)
  drivetrain: FWD (single front motor)
  battery_chemistry: LFP (BYD Blade)
  platform: BYD e-Platform 3.0
  heat_pump: true
  variants:
    - name: "Standard / Essential"
      battery_kwh_nominal_approx: 46
      battery_kwh_usable_approx: 44.9
      range_km: 340
      motor_power_kw: 70
      motor_torque_nm: 180
      acceleration_0_100_s: 12.3
    - name: "Extended / Premium"
      battery_kwh: 60
      range_km: 427
      motor_power_kw: 150
      motor_torque_nm: 310
      acceleration_0_100_s: 7.0
  range_test_standard: WLTP
  architecture_v: 400
  ac_charge_kw: 7          # manufacturer states 6.4 kW; EVDB NZ lists 7.4 kW — see note
  dc_charge_kw_max: "60 (Standard) / up to 80–100 (Extended)"   # sources conflict — see note
  charge_port: "Type 2 (AC) + CCS2 (DC)"
  v2l_supported: true
  v2l_power_kw: 3.3
  length_mm: 4290
  width_mm: 1770
  height_mm: 1570
  warranty_battery: "8 years / 160,000 km"
---

# BYD Dolphin

The BYD Dolphin is a front-wheel-drive C-segment electric hatchback — the first model in BYD's "Ocean" series — built on BYD's e-Platform 3.0 with a Blade (LFP) battery and a standard heat pump. It was sold new in New Zealand from 2023. Figures here are from BYD NZ and its dealers, cross-checked against EVDB NZ; ranges are WLTP.

## Variants (as sold new in NZ)

- **Standard / Essential** — ~45 kWh Blade battery (≈44.9 kWh usable), 340 km WLTP range, single 70 kW / 180 Nm front motor, 0–100 km/h in 12.3 s.
- **Extended / Premium** — 60 kWh Blade battery, 427 km WLTP range, 150 kW / 310 Nm front motor, 0–100 km/h in about 7 s.

Both have a 400-volt architecture, Vehicle-to-Load (up to 3.3 kW), a standard heat pump, and an 8-year / 160,000 km battery warranty. Dimensions are 4,290 × 1,770 × 1,570 mm.

## Charging and connectors

The Dolphin uses Type 2 (AC) and CCS2 (DC) connectors. DC fast charging is comparatively modest — around 60 kW on the Standard, with the Extended quoted at up to 80–100 kW depending on source (see note). A DC session of roughly 30 minutes covers a 30–80% top-up.

## Note for corpus maintainers

*Two currency/consistency issues. (1) Availability: EVDB NZ records the Dolphin as no longer sold new in NZ from around April 2026 (used-only thereafter), while some 2026 dealer pages and reviews still present it as on sale — `nz_availability` is set to `used-only` pending confirmation; verify current status before treating it as a new-sale model. (2) Charging figures conflict across sources: AC onboard charging is quoted as 6.4 kW (BYD NZ launch material) or 7.4 kW (EVDB NZ); Extended-range DC peak is quoted as 80 kW (Ateco/BYD launch) or 100 kW (some dealer pages). The most-common figures are recorded above with the conflict flagged; reconcile against BYD NZ's current spec sheet and RightCar for the authoritative record.*
