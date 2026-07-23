---
title: "Home Energy Savings Calculator (methodology)"
source_url: https://www.eeca.govt.nz/for-homes/energy-saving-technology/plan-your-home-energy-upgrades/home-energy-savings-calculator/
source_type: webpage
publisher: "EECA (Energy Efficiency & Conservation Authority), New Zealand Government"
section: "For homes > Energy saving technology > Plan your home energy upgrades"
source_date: 2026-07-10
source_date_basis: retrieval-date  # page displays no publication/updated date (data model last updated March 2025)
retrieved: 2026-07-10
document_id: eeca-for-homes-home-energy-savings-calculator
linked_from: https://www.eeca.govt.nz/for-homes/energy-saving-technology/plan-your-home-energy-upgrades/
# Discovered during crawl (not in original URL list); substantive methodology page.
---

# Home Energy Savings Calculator (methodology)

The Home Energy Savings Calculator estimates how much a household could save by upgrading heating, hot water, the cooktop, the car, or by adding solar. The underlying data model was last updated **March 2025** (adding a solar-savings module and refreshing the electricity pricing plans), and the full model source code is published openly. The notes below document the modelling assumptions, which are useful context for interpreting EECA's savings figures elsewhere in the corpus.

## Inputs

- **Household size** informs hot water and cooking energy use.
- **Postcode** estimates localised electricity prices, how much energy goes to heating and hot water, and how efficient heat pumps are in different climates. (Hot water energy depends partly on incoming cold-water temperature, which varies by region.)

## Pricing basis

Electricity and piped gas costs are based on the **lowest-cost plan** offered in each region by the four major electricity retailers. "Lowest cost" is judged on the annual cost for a fully electric house (for electricity plans) and a mixed-energy house (for piped gas plans).

## Hot water assumptions

Average per-person hot water use draws on data from BRANZ and the University of Auckland; low/high variations are based on showering only, with other hot water uses held at average. Modelled appliance efficiencies:

| Appliance | Efficiency |
| --- | --- |
| Gas instantaneous water heater | 83% |
| Gas storage water heater | 88% |
| Electric hot water cylinder | 100% |
| Hot water heat pump | 276%–415% |

Hot water heat pump performance varies with climate across the 18 NIWA climate zones. Storage losses are modelled for gas cylinders, electric cylinders and hot water heat pumps, varying by appliance type and storage volume (which depends on household size). Gas and electric cylinders are assumed indoors; hot water heat pumps outdoors.

## Cooktop

Cooktop energy use is based on the number of people in the household.

## Solar assumptions

Self-use of solar-generated electricity is treated as zero cost. Electricity sold to the grid is valued at **12 c/kWh**; because grid electricity almost always costs more than 12 c/kWh, the model favours maximising self-use. To allocate solar to self-use, the calculator assumes appliance-usage timing: heating on in the morning (7–9am) and evening (5–11pm) in all cases, and during the day (9am–5pm) for the number of days per week specified in the heating module, with heating energy based on regional climate data (colder months only).
