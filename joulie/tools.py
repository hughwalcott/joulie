"""Registry of external tools Joulie can point visitors to via QR code.

Every tool is a household-oriented, first-party (government or Rewiring)
resource sourced from knowledge_base/ADDITIONAL_RESOURCES.md. The kiosk shows
the pre-rendered QR from assets/qrcodes/ when Joulie's reply mentions the
tool by name — no URL is ever spoken aloud.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class Tool:
    id: str
    name: str
    publisher: str
    description: str
    url: str
    short_url: str
    keywords: tuple[str, ...]


_QR_DIR = Path(__file__).parent.parent / "assets" / "qrcodes"


REGISTRY: dict[str, Tool] = {
    "billy": Tool(
        id="billy",
        name="Billy",
        publisher="Electricity Authority",
        description="Free, independent power-plan comparison.",
        url="https://www.billy.govt.nz/",
        short_url="billy.govt.nz",
        keywords=(
            "billy", "compare power plans", "compare plans", "compare power",
            "plan comparison", "compare your plan", "switch plan", "switch power",
            "switching plans", "compare retailers", "plan compare",
        ),
    ),
    "eeca_home_savings": Tool(
        id="eeca_home_savings",
        name="Home energy savings calculator",
        publisher="EECA",
        description="Estimate savings on heating, hot water, cooking, EVs and solar.",
        url="https://www.eeca.govt.nz/for-homes/energy-saving-technology/plan-your-home-energy-upgrades/home-energy-savings-calculator/",
        short_url="eeca.govt.nz — home energy savings calculator",
        keywords=(
            "home energy savings calculator", "home energy calculator",
            "energy savings calculator", "eeca calculator", "energy calculator",
            "eeca home", "home savings calculator",
        ),
    ),
    "rewiring_calc": Tool(
        id="rewiring_calc",
        name="Rewiring electric calculator",
        publisher="Rewiring Aotearoa",
        description="Personalised savings and emissions from electrifying your home.",
        url="https://www.rewiring.nz/calculator",
        short_url="rewiring.nz/calculator",
        keywords=(
            "electric calculator", "rewiring calculator", "rewiring electric",
            "electrification calculator", "rewiring's calculator",
        ),
    ),
    "rewiring_plan": Tool(
        id="rewiring_plan",
        name="Rewiring Make a Plan",
        publisher="Rewiring Aotearoa",
        description="Staged, downloadable electrification plan timed to each machine's end of life.",
        url="https://www.rewiring.nz/plan",
        short_url="rewiring.nz/plan",
        keywords=(
            "make a plan", "rewiring plan", "electrification plan",
            "electrification to-do", "electrification to do", "make-a-plan",
        ),
    ),
    "eeca_solar_calc": Tool(
        id="eeca_solar_calc",
        name="EECA solar power calculator",
        publisher="EECA",
        description="Model a solar system for your home.",
        url="https://www.eeca.govt.nz/for-homes/solar-for-homes/solar-power-calculator/",
        short_url="eeca.govt.nz — solar power calculator",
        keywords=(
            "solar power calculator", "solar calculator", "eeca solar",
            "size a solar", "sizing solar", "size your solar", "solar sizing",
        ),
    ),
    "niwa_solarview": Tool(
        id="niwa_solarview",
        name="NIWA SolarView",
        publisher="NIWA",
        description="Estimate the sunlight hours and solar potential of a specific roof.",
        url="https://solarview.niwa.co.nz/",
        short_url="solarview.niwa.co.nz",
        keywords=(
            "solarview", "solar view", "niwa solar", "niwa",
            "sunlight hours", "solar potential", "roof sunlight",
        ),
    ),
    "eeca_appliance": Tool(
        id="eeca_appliance",
        name="Efficient appliance calculator",
        publisher="EECA",
        description="Compare running costs of common appliances.",
        url="https://www.eeca.govt.nz/for-homes/energy-saving-technology/efficient-appliance-calculator/",
        short_url="eeca.govt.nz — efficient appliance calculator",
        keywords=(
            "efficient appliance calculator", "appliance calculator",
            "compare appliance", "appliance running cost", "appliance efficiency",
            "compare appliances",
        ),
    ),
    "ea_meter": Tool(
        id="ea_meter",
        name="EA Your meter (ICP lookup)",
        publisher="Electricity Authority",
        description="Look up your ICP number, retailer and meter type by address.",
        url="https://www.ea.govt.nz/your-power/your-meter/",
        short_url="ea.govt.nz — your meter",
        keywords=(
            "your meter", "icp lookup", "icp number", "meter type",
            "look up your meter", "find your meter", "ea meter", "your-meter",
        ),
    ),
    "warmer_kiwi_homes": Tool(
        id="warmer_kiwi_homes",
        name="Warmer Kiwi Homes eligibility check",
        publisher="EECA",
        description="Check eligibility for 50–90% off insulation and up to 90% off heating.",
        url="https://www.eeca.govt.nz/co-funding-and-support/products/warmer-kiwi-homes-programme/check-eligibility/",
        short_url="eeca.govt.nz — Warmer Kiwi Homes",
        keywords=(
            "warmer kiwi homes", "insulation grant", "heating grant",
            "warmer homes", "insulation subsidy", "kiwi homes programme",
        ),
    ),
}


def qr_path(tool_id: str) -> Path:
    return _QR_DIR / f"{tool_id}.png"


def detect_tool(reply_text: str) -> Optional[Tool]:
    """Fuzzy-match Joulie's reply against tool keywords. Returns the highest-
    priority hit (longest matching keyword wins); None if nothing matches.

    We match against keywords rather than expecting the LLM to emit structured
    tags — small models (1B --lite) don't reliably follow tag protocols but
    they will name tools verbally as the system prompt instructs."""
    if not reply_text:
        return None
    text = reply_text.lower()
    # Score by length of matched keyword — longer matches are more specific.
    best: Optional[tuple[int, Tool]] = None
    for tool in REGISTRY.values():
        for kw in tool.keywords:
            if kw in text:
                score = len(kw)
                if best is None or score > best[0]:
                    best = (score, tool)
    return best[1] if best else None
