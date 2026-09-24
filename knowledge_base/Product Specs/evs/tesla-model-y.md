---
title: "Tesla Model Y — battery-electric midsize SUV"
category: ev
brand: "Tesla"
model: "Model Y"
source_url: https://www.tesla.com/en_nz/modely
source_type: webpage
source_name: "Tesla New Zealand (manufacturer)"
publisher: "Tesla, Inc."
nz_availability: confirmed
source_date: 2026-09-04
source_date_basis: retrieval-date   # manufacturer spec page undated; 2026 "Juniper" model year
retrieved: 2026-09-04
document_id: prod-ev-tesla-model-y
secondary_sources:
  - https://evdb.nz/v/tesla-model-y
  - https://evkx.net/models/tesla/model_y/model_y_premium_rwd/
specs:
  body_type: midsize SUV
  variants:
    - name: "RWD (Standard Range)"
      drivetrain: RWD
      motor_power_kw: 220
      battery_chemistry: LFP
      battery_kwh_nominal_approx: 62.5
      battery_kwh_usable_approx: 60.5
      range_km: 466
      dc_charge_kw_max: 175
      acceleration_0_100_s: 5.9
      warranty_battery: "8 years / 160,000 km"
    - name: "Long Range AWD"
      drivetrain: AWD (dual motor)
      battery_chemistry: NMC
      battery_kwh_approx: 80
      range_km: 600
      dc_charge_kw_max: 250
      acceleration_0_100_s: 4.8
      warranty_battery: "8 years / 192,000 km"
    - name: "Performance AWD"
      drivetrain: AWD (dual motor)
      range_km: 580
      acceleration_0_100_s: 3.5
  range_test_standard: WLTP
  efficiency_wh_per_km_approx: 149            # RWD (per evdb.nz)
  architecture_v: 400
  ac_charge_kw: 11
  charge_port: "Type 2 (AC) + CCS2 (DC / Supercharger in NZ)"
  v2l_supported: false
  length_mm: 4792
  width_mm: 1920
  height_mm: 1624
  wheelbase_mm: 2890
  seats: 5
  warranty_vehicle: "4 years / 80,000 km"
---

# Tesla Model Y

The Tesla Model Y is a midsize electric SUV and has been New Zealand's best-selling electric car in recent years. The 2026 line-up is the second-generation "Juniper" update. Figures here are from Tesla New Zealand, cross-checked against the independent EVDB NZ and EVKX databases; ranges are WLTP.

## Variants (2026 NZ line-up)

- **RWD (Standard Range)** — single 220 kW rear motor, LFP battery (~62.5 kWh nominal, ~60.5 kWh usable), 466 km WLTP range, 0–100 km/h in 5.9 s, DC fast charging up to 175 kW (about 28 minutes for 10–80%).
- **Long Range AWD** — dual-motor all-wheel drive, ~80 kWh NMC battery, 600 km WLTP range, 0–100 km/h in 4.8 s, DC up to 250 kW.
- **Performance AWD** — dual-motor, 580 km WLTP range, 0–100 km/h in 3.5 s.

A stretched six-seat "Model YL" variant is also offered (roughly 681 km WLTP on a larger NMC pack); treat it as a separate model if a dedicated record is needed.

## Battery and chemistry

The RWD uses a lithium iron phosphate (LFP) pack, which is well suited to daily charging to 100%; the Long Range and Performance use higher-energy-density nickel-manganese-cobalt (NMC) packs. Usable capacity on the RWD is around 60.5 kWh (per EVDB NZ).

## Charging

The onboard AC charger is 11 kW. DC fast charging peaks at 175 kW (RWD) or 250 kW (Long Range/Performance) — in New Zealand the Model Y charges via CCS2, including at Tesla's Superchargers. The Model Y does not support Vehicle-to-Load.

## Dimensions and warranty

The Model Y is 4,792 mm long, 1,920 mm wide and 1,624 mm tall on a ~2,890 mm wheelbase, seating five (kerb weight ~1,921 kg RWD). Tesla NZ covers the vehicle for 4 years / 80,000 km, and the battery and drive unit for 8 years / 160,000 km (RWD) or 8 years / 192,000 km (Long Range/Performance).

## Note for corpus maintainers

*Reported nominal battery capacity for the RWD varies slightly across sources (62.5 kWh from some NZ reviews, ~64 kWh nominal / 60.5 kWh usable per EVDB NZ). Tesla does not publish a headline kWh figure on its NZ configurator, so the usable figure is the more reliable one for modelling. Reconcile against RightCar's official NZ energy-economy rating for the authoritative record. Prices (RWD from ~$67,900; Long Range from ~$77,900) change frequently and are indicative only as at retrieval.*
