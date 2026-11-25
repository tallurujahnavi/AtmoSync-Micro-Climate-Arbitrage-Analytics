"""
esg_sustainability.py – Carbon emissions & food-waste avoidance engine.

Quantifies the Environmental, Social, and Governance (ESG) impact of
cold-chain spoilage arbitrage and reefer container diversion:
1. Food waste diverted from landfills (kg & tonnes)
2. Avoided anaerobic methane emissions (kg CO2e via IPCC factors)
3. Reefer diesel transit emissions (EPA SmartWay reefer factors)
4. Net Carbon Arbitrage & Voluntary Carbon Market (VCM) offset valuation
5. Fleet ESG Sustainability Index (0–100)
"""

from dataclasses import dataclass
from typing import Dict, List, Any
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Emission Factors & Benchmarks (IPCC & EPA SmartWay)
# ---------------------------------------------------------------------------
# FAO / IPCC: Average lifecycle CO2e emissions avoided per kg of fresh produce saved from landfill
FOOD_WASTE_CO2E_KG_PER_KG = 2.45

# Commodity-specific carbon footprints (kg CO2e per kg lost)
COMMODITY_CARBON_INTENSITY = {
    "Hass Avocados": 2.85,  # High water & fertilizer footprint
    "Atlantic Salmon": 5.40, # Aquaculture feed & refrigeration
    "Strawberries": 1.95,    # High vulnerability, quick rot
    "Vaccines": 12.50,       # High-value pharmaceutical cold chain
    "Artisan Cheeses": 4.10, # Dairy lifecycle emissions
    "Tomato": 2.10,
    "Mango": 2.30,
    "Potato": 1.20,
    "Onion": 1.40,
    "Banana": 1.70,
}

# EPA SmartWay freight emission factor: kg CO2e per tonne-km for refrigerated road freight
REEFER_DIESEL_EMISSIONS_KG_PER_TONNE_KM = 0.161

# Carbon Credit Offset Valuation (Voluntary Carbon Market USD per metric tonne CO2e)
CARBON_CREDIT_PRICE_USD_PER_TONNE = 20.00


@dataclass
class ContainerESGMetrics:
    container_id: str
    commodity: str
    food_saved_kg: float
    avoided_methane_co2e_kg: float
    haulage_emissions_co2e_kg: float
    net_carbon_saved_co2e_kg: float
    carbon_credit_value_usd: float
    esg_compliance_rating: str  # AAA, AA, A, B, C


@dataclass
class FleetESGSummary:
    total_containers_tracked: int
    rerouted_containers_count: int
    total_food_saved_tonnes: float
    total_avoided_methane_co2e_tonnes: float
    total_transit_emissions_co2e_tonnes: float
    net_carbon_saved_co2e_tonnes: float
    total_carbon_credit_value_usd: float
    fleet_esg_score: float  # 0 to 100
    esg_tier: str           # LEADER, ADVANCED, STANDARD, DEVELOPING
    details: List[ContainerESGMetrics]


def compute_container_esg(row: pd.Series) -> ContainerESGMetrics:
    """Computes carbon emissions and food waste savings for an individual container."""
    container_id = str(row.get("container_id", "UNKNOWN"))
    commodity = str(row.get("commodity", "Hass Avocados"))
    tonnage = float(row.get("cargo_tonnage", 15.0))
    dist_sec_km = float(row.get("dist_to_secondary_km", 120.0))
    action = str(row.get("action_decision", "MAINTAIN_ORIGINAL_ROUTE"))

    is_rerouted = "REROUTE" in action

    if is_rerouted:
        # Avoided loss: full cargo tonnage diverted from landfill
        food_saved_kg = tonnage * 1000.0
        intensity = COMMODITY_CARBON_INTENSITY.get(commodity, FOOD_WASTE_CO2E_KG_PER_KG)
        avoided_co2e = food_saved_kg * intensity

        # Additional transit haulage emissions for diversion
        haulage_co2e = dist_sec_km * tonnage * REEFER_DIESEL_EMISSIONS_KG_PER_TONNE_KM
        net_saved = max(0.0, avoided_co2e - haulage_co2e)
        carbon_usd = (net_saved / 1000.0) * CARBON_CREDIT_PRICE_USD_PER_TONNE
        rating = "AAA" if net_saved > 20000 else ("AA" if net_saved > 10000 else "A")
    else:
        food_saved_kg = 0.0
        avoided_co2e = 0.0
        haulage_co2e = 0.0
        net_saved = 0.0
        carbon_usd = 0.0
        # If healthy, rated A; if unmanaged drift, rated B or C
        rating = "AA" if "HEALTHY" in str(row.get("alert_level", "")) else "B"

    return ContainerESGMetrics(
        container_id=container_id,
        commodity=commodity,
        food_saved_kg=round(food_saved_kg, 1),
        avoided_methane_co2e_kg=round(avoided_co2e, 1),
        haulage_emissions_co2e_kg=round(haulage_co2e, 1),
        net_carbon_saved_co2e_kg=round(net_saved, 1),
        carbon_credit_value_usd=round(carbon_usd, 2),
        esg_compliance_rating=rating,
    )


def compute_fleet_esg_summary(fleet_df: pd.DataFrame) -> FleetESGSummary:
    """Aggregates ESG and carbon accounting metrics across the active reefer fleet."""
    if fleet_df.empty:
        return FleetESGSummary(
            total_containers_tracked=0,
            rerouted_containers_count=0,
            total_food_saved_tonnes=0.0,
            total_avoided_methane_co2e_tonnes=0.0,
            total_transit_emissions_co2e_tonnes=0.0,
            net_carbon_saved_co2e_tonnes=0.0,
            total_carbon_credit_value_usd=0.0,
            fleet_esg_score=100.0,
            esg_tier="LEADER",
            details=[],
        )

    records = [compute_container_esg(row) for _, row in fleet_df.iterrows()]

    total_containers = len(records)
    rerouted_count = sum(1 for r in records if r.food_saved_kg > 0)

    total_food_kg = sum(r.food_saved_kg for r in records)
    avoided_co2e_kg = sum(r.avoided_methane_co2e_kg for r in records)
    haulage_co2e_kg = sum(r.haulage_emissions_co2e_kg for r in records)
    net_co2e_kg = sum(r.net_carbon_saved_co2e_kg for r in records)
    total_credit_usd = sum(r.carbon_credit_value_usd for r in records)

    # Score calculation: base 70 + points for diverted food waste & zero unmitigated spoilage
    unmitigated_spoilage = sum(
        1 for _, row in fleet_df.iterrows()
        if "TOTAL_LOSS" in str(row.get("primary_status", "")) and "REROUTE" not in str(row.get("action_decision", ""))
    )
    score = 70.0 + (rerouted_count * 5.0) - (unmitigated_spoilage * 15.0)
    score = float(np.clip(score, 0.0, 100.0))

    if score >= 85:
        tier = "LEADER (AAA)"
    elif score >= 70:
        tier = "ADVANCED (AA)"
    elif score >= 50:
        tier = "STANDARD (A)"
    else:
        tier = "DEVELOPING (B)"

    return FleetESGSummary(
        total_containers_tracked=total_containers,
        rerouted_containers_count=rerouted_count,
        total_food_saved_tonnes=round(total_food_kg / 1000.0, 2),
        total_avoided_methane_co2e_tonnes=round(avoided_co2e_kg / 1000.0, 2),
        total_transit_emissions_co2e_tonnes=round(haulage_co2e_kg / 1000.0, 2),
        net_carbon_saved_co2e_tonnes=round(net_co2e_kg / 1000.0, 2),
        total_carbon_credit_value_usd=round(total_credit_usd, 2),
        fleet_esg_score=round(score, 1),
        esg_tier=tier,
        details=records,
    )


def generate_esg_executive_report(summary: FleetESGSummary) -> str:
    """Formats an executive ESG & Carbon Sustainability audit report in Markdown."""
    lines = [
        "# 🌿 AtmoSync Cold-Chain ESG & Carbon Abatement Audit",
        f"**Fleet ESG Rating**: `{summary.esg_tier}` | **Score**: `{summary.fleet_esg_score} / 100`",
        "",
        "---",
        "## 1. Key Sustainability Performance Indicators (KPIs)",
        f"- **Food Waste Diverted from Landfill**: `{summary.total_food_saved_tonnes:,.2f} Metric Tonnes`",
        f"- **Gross Methane Emissions Avoided**: `{summary.total_avoided_methane_co2e_tonnes:,.2f} t CO2e`",
        f"- **Reroute Transport Haulage Footprint**: `{summary.total_transit_emissions_co2e_tonnes:,.2f} t CO2e`",
        f"- **Net Carbon Abatement (Carbon Saved)**: `{summary.net_carbon_saved_co2e_tonnes:,.2f} t CO2e`",
        f"- **Voluntary Carbon Market Equivalence**: `${summary.total_carbon_credit_value_usd:,.2f} USD` (@ $20/t CO2e)",
        "",
        "---",
        "## 2. Container Abatement Breakdown",
        "| Container ID | Commodity | Food Saved (kg) | Avoided Landfill (kg CO2e) | Transit Haulage (kg CO2e) | Net Carbon Saved (kg CO2e) | ESG Rating |",
        "|---|---|---|---|---|---|---|",
    ]

    for item in summary.details:
        lines.append(
            f"| `{item.container_id}` | {item.commodity} | {item.food_saved_kg:,.1f} "
            f"| {item.avoided_methane_co2e_kg:,.1f} | {item.haulage_emissions_co2e_kg:,.1f} "
            f"| {item.net_carbon_saved_co2e_kg:,.1f} | `{item.esg_compliance_rating}` |"
        )

    lines.extend([
        "",
        "---",
        "## 3. Carbon Accounting Methodology",
        "- **Food Waste Landfill Factor**: IPCC Guidelines for National Greenhouse Gas Inventories (2.45 kg CO2e / kg food waste).",
        "- **Freight Reefer Factor**: EPA SmartWay Transport Partnership (0.161 kg CO2e / tonne-km for refrigerated road transit).",
        "- **Carbon Pricing**: S&P Global Platts Voluntary Carbon Credit Price Assessments ($20.00 / t CO2e).",
    ])

    return "\n".join(lines)
