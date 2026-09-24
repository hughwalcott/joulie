---
title: "Nissan Leaf — battery-electric (3rd generation) and prior generations"
category: ev
brand: "Nissan"
model: "Leaf"
source_url: https://www.jimwright.co.nz/nissan/leaf
source_type: webpage
source_name: "Nissan New Zealand (via NZ dealer) + global reveal specs"
publisher: "Nissan New Zealand"
nz_availability: incoming   # 3rd-gen arriving NZ from FY2026; prior gen sold new until ~2024, used widely available
source_date: 2026-09-04
source_date_basis: retrieval-date
retrieved: 2026-09-04
document_id: prod-ev-nissan-leaf
secondary_sources:
  - https://paultan.org/2025/06/18/2026-nissan-leaf-full-details-3rd-gen-ev-now-an-suv-with-up-to-218-ps-604-km-range-ccs2-charge-port/
  - https://www.tarmaclife.co.nz/news/all-new-nissan-leaf-boasts-a-mind-blowing-621km-range/
  - https://evdb.nz/v/nissan-leaf
specs:
  body_type: crossover / hatchback
  drivetrain: FWD (single motor)
  third_gen_2026:
    battery_kwh: [52, 75]
    battery_cooling: liquid-cooled
    range_km: [436, 604]          # 52 kWh / 75 kWh; see note (some sources quote 621 km)
    range_test_standard: WLTP (pending NZ homologation)
    dc_charge_kw_max: 150
    dc_10_80_min: 35
    charge_port: "CCS2 (NZ/global) — see note on US NACS"
    v2l_supported: true
    v2l_power_kw: 3.6
    v2g_supported: true
    heat_pump: true
  prior_gen_2019_2024:
    battery_kwh: [40, 62]         # 62 kWh = e+
    battery_cooling: air-cooled
    range_km: [270, 385]          # 40 kWh / e+ (WLTP)
    motor_power_kw: [110, 160]
    ac_charge_kw: 6.6
    charge_port: "Type 1 (AC) + CHAdeMO (DC)"
---

# Nissan Leaf

The Nissan Leaf was one of the first mass-market EVs and remains extremely common in New Zealand — both as a former new model and as a very large used-import fleet. An all-new third generation launched globally in 2025–2026, switching to a crossover body, liquid-cooled battery and the CCS2 charging standard. Because the NZ fleet spans two very different generations, both are recorded here.

## Third generation (2026-, arriving in NZ from FY2026)

Built on Nissan's new EV platform as a crossover-styled SUV with a single front motor and, for the first time, a liquid-cooled battery. Two battery options:

- **52 kWh** — about 436 km WLTP range (pending NZ homologation).
- **75 kWh** — up to roughly 604 km WLTP range (some NZ sources quote 621 km — see note).

DC fast charging rises to up to 150 kW (10–80% in about 35 minutes), a large jump over the previous generation. It adds a heat pump, Vehicle-to-Load (~3.6 kW) and Vehicle-to-Grid support, and — critically for New Zealand — uses the CCS2 fast-charging port, retiring the old CHAdeMO plug.

## Previous generations (2019–2024 new in NZ; large used fleet)

The previous Leaf used an air-cooled battery in 40 kWh and 62 kWh (e+) forms, giving roughly 270 km and 385 km WLTP range respectively, with 110 kW or 160 kW motors, 6.6 kW AC charging, and the Type 1 (AC) / CHAdeMO (DC) connectors. Many older Japanese-import Leafs (24/30/40 kWh) are also on NZ roads; for these, battery State of Health (SoH) matters more than odometer reading, and real range scales with SoH (e.g. a 40 kWh Leaf at 86% SoH ≈ 234 km).

## Note for corpus maintainers

*Significant market/source divergence on the 3rd-gen Leaf. (1) Charge port: NZ/global cars use CCS2 (per Nissan's global reveal); US-market coverage describes a NACS port with a J1772 companion — do not apply US charging specs to the NZ car. (2) Battery/range: NZ/global sources quote 52 kWh (436 km) and 75 kWh (604–621 km) WLTP, while some US-oriented databases list a 60 kWh pack (~480 km) and up to 200 kW DC — these appear to be different-market interpretations. NZ WLTP figures were still pending homologation at retrieval. Set `nz_availability` to `incoming` until NZ deliveries and RightCar figures are confirmed. The previous-generation CHAdeMO Leaf remains the dominant Leaf on NZ roads and should be treated as a distinct record.*
