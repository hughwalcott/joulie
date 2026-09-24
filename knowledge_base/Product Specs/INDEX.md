# Product-specs corpus index

Generated data files (real, sourced specifications). Save this tree into C:\Joulie\Product-data.

**Coverage: all six categories now have a first batch — 27 product files total (8 EVs, 3 solar panels, 4 batteries, 3 hot water heat pumps, 3 space heating heat pumps, 3 induction cooktops).**

## Electric vehicles (8)

| File | Brand | Model | Primary source | NZ availability |
| --- | --- | --- | --- | --- |
| evs/byd-atto-3.md | BYD | Atto 3 | BYD New Zealand | confirmed |
| evs/tesla-model-y.md | Tesla | Model Y | Tesla New Zealand | confirmed |
| evs/mg-mg4.md | MG | MG4 | MG Motor New Zealand | confirmed |
| evs/byd-dolphin.md | BYD | Dolphin | BYD New Zealand / dealers | used-only (from ~Apr 2026) |
| evs/hyundai-ioniq-5.md | Hyundai | Ioniq 5 (Series II) | Hyundai New Zealand | confirmed |
| evs/kia-ev6.md | Kia | EV6 | Kia New Zealand | confirmed |
| evs/tesla-model-3.md | Tesla | Model 3 | Tesla New Zealand | confirmed |
| evs/nissan-leaf.md | Nissan | Leaf (3rd-gen + prior) | Nissan New Zealand | incoming / used |

## Solar panels (3)

| File | Brand | Series | Cell tech | Primary source |
| --- | --- | --- | --- | --- |
| solar-panels/jinko-tiger-neo-54hl4r.md | JinkoSolar | Tiger Neo 54HL4R | N-type TOPCon | Jinko datasheet |
| solar-panels/trina-vertex-s-plus-neg9r.md | Trina Solar | Vertex S+ NEG9R | N-type i-TOPCon (dual glass) | Trina datasheet (APAC) |
| solar-panels/longi-hi-mo-6-lr5-54ht.md | LONGi | Hi-MO 6 LR5-54HT | HPBC back-contact | LONGi datasheet |

## Home batteries (3)

| File | Brand | Model | Usable kWh | Chemistry | Primary source |
| --- | --- | --- | --- | --- | --- |
| batteries/tesla-powerwall-3.md | Tesla | Powerwall 3 | 13.5 (to 54) | LFP (reported) | Tesla AU datasheet |
| batteries/byd-battery-box-premium.md | BYD | Battery-Box Premium HVS/HVM | 5.1–66.2 (modular) | LFP | BYD AU datasheet |
| batteries/enphase-iq-battery-5p.md | Enphase | IQ Battery 5P | 5.0/unit (modular) | LFP | Enphase ANZ datasheet |
| batteries/sigenergy-sigenstor.md | Sigenergy | SigenStor | ~5.2–48 (modular) | LFP | Sigenergy AU spec refs |

## Hot water heat pumps (3)

| File | Brand | Model | Config | Refrigerant | COP (test std) | Primary source |
| --- | --- | --- | --- | --- | --- | --- |
| hot-water-heat-pumps/reclaim-energy-co2.md | Reclaim Energy | CO2 (EHPE-4540P) | split | R744 (CO2) | 5.24 (AS/NZS 5125) | Reclaim NZ design guide |
| hot-water-heat-pumps/mitsubishi-ecodan-quhz.md | Mitsubishi Electric | Ecodan QUHZ-W40VA | monobloc + 200L cylinder | R744 (CO2) | ~4.0 (see note) | Mitsubishi Electric NZ |
| hot-water-heat-pumps/rinnai-hydraheat-integrated.md | Rinnai | HydraHeat Integrated 275/340L | integrated all-in-one | R290 (propane) | 4.7 (AS/NZS 5125) | Rinnai NZ |

## Space heating heat pumps (3)

| File | Brand | Model | Type | Refrigerant | Notes | Primary source |
| --- | --- | --- | --- | --- | --- | --- |
| space-heating-heat-pumps/mitsubishi-gs-series.md | Mitsubishi Electric | GS Standard Series | single-split high wall | R32 | 6 sizes 3.1-9.0 kW heat; COP 3.5-4.0 | Mitsubishi Electric NZ |
| space-heating-heat-pumps/fujitsu-e3-series.md | Fujitsu | e3 Series | single-split high wall | R32 | ASTG09 up to 5 star, COP 4.92 | Fujitsu NZ datasheet |
| space-heating-heat-pumps/mitsubishi-hypercore-cold-climate.md | Mitsubishi Electric | HyperCore (MSZ-LN) | single-split high wall, cold-climate | R32 | full rated heat to -15 C | Mitsubishi Electric NZ |

## Induction cooktops (3)

| File | Brand | Model | Zones | Total load | Note | Primary source |
| --- | --- | --- | --- | --- | --- | --- |
| induction-cooktops/fisher-paykel-ci604.md | Fisher & Paykel | 60cm CI604 (SmartZone) | 4 | 4.4 kW / 19.1 A | NZ brand | F&P spec sheet |
| induction-cooktops/bosch-60cm.md | Bosch | 60cm Series 4/6 (CombiZone) | 4 | ~6.9 kW | 17 power levels | Bosch NZ spec sheet |
| induction-cooktops/haier-hci604-low-current.md | Haier | 60cm HCI604 Low Current (Flexi Zone) | 4 | 4.5 kW / 19.7 A | reuses existing wiring | Haier NZ |

## Status

- EVs: substantially complete (8 top NZ sellers). Optional: Polestar 2, BYD Seal, GWM Ora, MG ZS EV.
- Solar panels: 3 done. Could add Canadian Solar, JA Solar, Aiko, REC, Q Cells.
- Home batteries: 4 done (Tesla Powerwall 3, BYD Battery-Box, Enphase IQ 5P, Sigenergy SigenStor). Could add sonnen, Fronius/GoodWe, Pylontech, Huawei LUNA, FranklinWH.
- Hot water heat pumps: 3 done (CO2 split, CO2 monobloc+cylinder, R290 integrated). Could add Stiebel Eltron, Bosch, iStore, Midea.
- Space heating heat pumps: 3 done (standard single-split, high-efficiency single-split, cold-climate). Could add multi-split, ducted, and other brands (Daikin, Panasonic).
- Induction cooktops: 3 done (NZ-brand SmartZone, European 17-level, budget low-current). Could add Electrolux/Westinghouse, Samsung, Miele, 80/90 cm and full-flex models.

## Conventions

Full front-matter schema, the ranked source register per category, and the licensing posture are in COWORK-TASK-products.md. Performance figures are tagged with their basis (WLTP for EVs; STC 1000 W/m2 / 25 C / AM1.5 for PV modules; usable kWh at stated DoD and round-trip efficiency at stated conditions for batteries). Region-appropriate datasheets (AU/ANZ) are used for batteries since NZ shares the 230 V / 50 Hz grid. Cross-source discrepancies (e.g. Powerwall 3 chemistry; round-trip vs solar-to-home efficiency) are flagged per file rather than silently resolved. For hot water heat pumps, COP is only comparable between products tested to the SAME standard/conditions (AS/NZS 5125 vs BS EN 14511 differ) — each file keeps the test basis attached. Authoritative NZ checks: RightCar for EVs; Clean Energy Council approved-products lists for solar panels and batteries; the trans-Tasman Energy Rating registration database for heat pumps (air conditioners are MEPS-regulated; use registered star/ZERL and seasonal COP/EER, not just single-point rated COP). For space heating, star ratings vary by NZ climate zone (cold/average/hot) and cold-climate models are rated on full-capacity-to-low-temperature, not just +7 C COP. Induction cooktops are NOT MEPS-regulated, so there is no government registry or star rating for them - manufacturer spec sheets are the only authoritative source, and total connected load (which is power-managed and lower than the sum of zone maxima) is the key installation figure.
