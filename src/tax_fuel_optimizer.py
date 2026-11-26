"""
tax_fuel_optimizer.py – Haulage fuel surcharge, APMC mandi cess, and carbon tax optimizer.

Calculates realistic secondary market financial net returns after factoring in:
1. Diesel fuel consumption indices & dynamic fuel surcharges
2. State-level APMC agricultural market entry cess & mandi fees
3. National highway toll plaza cost models
4. Regulatory Scope 3 carbon tax deductions ($25.00/t CO2e)
"""

from dataclasses import dataclass
from typing import Dict, List, Any


# State-level APMC Agricultural Produce Market Committee cess rates (% of wholesale transaction)
STATE_APMC_CESS_RATES = {
    "Maharashtra": 0.0105,  # 1.05%
    "Karnataka": 0.0150,    # 1.50%
    "Delhi": 0.0100,        # 1.00%
    "Gujarat": 0.0080,      # 0.80%
    "Madhya Pradesh": 0.0150, # 1.50%
    "Tamil Nadu": 0.0100,   # 1.00%
    "Default": 0.0120,      # 1.20%
}

# Highway toll cost per kilometer for heavy commercial reefer trucks (USD / km)
HIGHWAY_TOLL_RATE_USD_PER_KM = 0.045

# Reefer fuel burn rate: liters of diesel per kilometer (propulsion + auxiliary generator)
REEFER_DIESEL_LITERS_PER_KM = 0.38
BASE_DIESEL_PRICE_USD_PER_LITER = 1.15

# Carbon Tax Rate (USD per metric tonne of CO2e emitted)
CARBON_TAX_USD_PER_TONNE = 25.00
DIESEL_EMISSION_KG_CO2_PER_LITER = 2.68


@dataclass
class NetArbitrageFiscalBreakdown:
    container_id: str
    target_market: str
    target_state: str
    gross_salvage_value_usd: float
    fuel_cost_usd: float
    toll_fees_usd: float
    apmc_mandi_cess_usd: float
    carbon_tax_levy_usd: float
    total_transit_deductions_usd: float
    net_realized_arbitrage_usd: float
    margin_retention_pct: float


def compute_fiscal_arbitrage_breakdown(
    container_id: str,
    target_market: str,
    target_state: str,
    distance_km: float,
    gross_salvage_usd: float,
    fuel_surcharge_multiplier: float = 1.0
) -> NetArbitrageFiscalBreakdown:
    """
    Computes fine-grained fiscal deductions for a secondary market reefer diversion.
    """
    # 1. Fuel cost
    liters_consumed = distance_km * REEFER_DIESEL_LITERS_PER_KM
    effective_fuel_price = BASE_DIESEL_PRICE_USD_PER_LITER * fuel_surcharge_multiplier
    fuel_cost = liters_consumed * effective_fuel_price

    # 2. Highway tolls
    tolls = distance_km * HIGHWAY_TOLL_RATE_USD_PER_KM

    # 3. APMC Mandi Entry Cess
    cess_rate = STATE_APMC_CESS_RATES.get(target_state, STATE_APMC_CESS_RATES["Default"])
    apmc_cess = gross_salvage_usd * cess_rate

    # 4. Carbon Tax
    carbon_tonnes = (liters_consumed * DIESEL_EMISSION_KG_CO2_PER_LITER) / 1000.0
    carbon_tax = carbon_tonnes * CARBON_TAX_USD_PER_TONNE

    # Total transit overhead
    total_deductions = fuel_cost + tolls + apmc_cess + carbon_tax
    net_realized = max(0.0, gross_salvage_usd - total_deductions)
    retention_pct = round((net_realized / max(1.0, gross_salvage_usd)) * 100.0, 1)

    return NetArbitrageFiscalBreakdown(
        container_id=container_id,
        target_market=target_market,
        target_state=target_state,
        gross_salvage_value_usd=round(gross_salvage_usd, 2),
        fuel_cost_usd=round(fuel_cost, 2),
        toll_fees_usd=round(tolls, 2),
        apmc_mandi_cess_usd=round(apmc_cess, 2),
        carbon_tax_levy_usd=round(carbon_tax, 2),
        total_transit_deductions_usd=round(total_deductions, 2),
        net_realized_arbitrage_usd=round(net_realized, 2),
        margin_retention_pct=retention_pct,
    )
