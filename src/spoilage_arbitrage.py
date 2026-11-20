"""
AtmoSync: Micro-Climate Arbitrage Analytics
Module: spoilage_arbitrage.py
Description: Mathematical engine for perishable commodity spoilage degradation curves
             and real-time "Spoilage Arbitrage" decision logic (as specified in Infotact Project 1).
"""

from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
from iot_simulator import COMMODITY_SPECS


# Transportation & market penalty parameters
REROUTE_HAULAGE_COST_PER_TON_KM = 0.08  # USD per ton-km for refrigerated diversion
PRIMARY_MARKET_DISCOUNT_PER_HOUR_DELAY = 15.0  # USD price decay per hour of post-harvest delay
SECONDARY_MARKET_PRICE_DISCOUNT = 0.90  # Secondary wholesale mandi offers 90% of metro price


def calculate_spoilage_rate_multiplier(commodity: str, internal_temp_c: float, internal_hum: float) -> float:
    """
    Calculates accelerated spoilage rate multiplier based on Arrhenius-type Q10 thermal degradation.
    When container temperature exceeds ideal band, biological respiration accelerates exponentially.
    """
    specs = COMMODITY_SPECS.get(commodity, COMMODITY_SPECS["Hass Avocados"])
    ideal_t_min, ideal_t_max = specs["ideal_temp_c"]
    q10 = specs["q10_temp_sensitivity"]

    if internal_temp_c <= ideal_t_max:
        temp_factor = 1.0
    else:
        temp_excess = internal_temp_c - ideal_t_max
        temp_factor = float(q10 ** (temp_excess / 10.0))

    # Humidity penalty: Dry air causes dehydration/shrivel; saturated air induces mold/fungal rot
    ideal_h_min, ideal_h_max = specs["ideal_hum_pct"]
    if internal_hum < ideal_h_min:
        hum_factor = 1.0 + ((ideal_h_min - internal_hum) / 100.0) * 1.5
    elif internal_hum > ideal_h_max:
        hum_factor = 1.0 + ((internal_hum - ideal_h_max) / 100.0) * 1.2
    else:
        hum_factor = 1.0

    return round(temp_factor * hum_factor, 2)


def evaluate_container_arbitrage(container_row: pd.Series) -> Dict:
    """
    Evaluates a single container telemetry event to determine:
    1. Hours of remaining shelf-life under current micro-climate conditions.
    2. Primary market outcome (Fresh vs. Spoiled total loss).
    3. Secondary market diversion outcome.
    4. Net Spoilage Arbitrage Dollar Gain ($).
    """
    commodity = container_row["commodity"]
    specs = COMMODITY_SPECS.get(commodity, COMMODITY_SPECS["Hass Avocados"])
    base_shelf_life = specs["base_shelf_life_hours"]

    multiplier = calculate_spoilage_rate_multiplier(
        commodity,
        container_row["internal_temp_celsius"],
        container_row["internal_humidity_percent"]
    )

    # Effective remaining shelf life (hours)
    # Higher degradation multiplier drastically shortens the decay clock
    hours_remaining = round(base_shelf_life / max(multiplier, 1.0), 1)

    hours_to_primary = container_row["hours_to_primary_market"]
    hours_to_secondary = container_row["hours_to_secondary_market"]
    cargo_tonnage = container_row["cargo_tonnage"]
    base_value = container_row["cargo_value_usd"]

    # --- Scenario A: Maintain Route to Primary Market ---
    if hours_remaining >= hours_to_primary:
        # Arrives before complete spoilage
        spoilage_pct_primary = round((hours_to_primary / hours_remaining) * 100.0, 1)
        primary_realized_value = round(base_value * (1.0 - (spoilage_pct_primary / 200.0)), 2)
        primary_status = "DELIVERABLE_FRESH"
    else:
        # Spoilage occurs in transit! Severe commercial loss / rejection
        spoilage_pct_primary = 100.0
        primary_realized_value = round(base_value * 0.05, 2)  # 5% salvage / landfill value
        primary_status = "TOTAL_LOSS_SPOILED_IN_TRANSIT"

    # --- Scenario B: Reroute to Nearby Secondary Market ---
    if hours_remaining >= hours_to_secondary:
        spoilage_pct_sec = round((hours_to_secondary / hours_remaining) * 100.0, 1)
        gross_secondary_value = base_value * SECONDARY_MARKET_PRICE_DISCOUNT * (1.0 - (spoilage_pct_sec / 300.0))
        reroute_haulage_cost = container_row["dist_to_secondary_km"] * cargo_tonnage * REROUTE_HAULAGE_COST_PER_TON_KM
        secondary_net_value = round(gross_secondary_value - reroute_haulage_cost, 2)
        secondary_status = "FEASIBLE_PREMIUM_SALVAGE"
    else:
        secondary_net_value = 0.0
        secondary_status = "INFEASIBLE_SPOILS_BEFORE_SECONDARY"

    # Spoilage Arbitrage Net Gain = Value Saved by Rerouting minus Value if Maintained
    spoilage_arbitrage_gain = round(secondary_net_value - primary_realized_value, 2)

    # Decision Matrix
    if primary_status == "TOTAL_LOSS_SPOILED_IN_TRANSIT" and secondary_net_value > 0:
        action = "URGENT_REROUTE_RECOMMENDED"
        alert_level = "CRITICAL_SPOILAGE_RISK"
        recommendation = f"Reroute immediately to {container_row['secondary_destination']} to capture ${spoilage_arbitrage_gain:,.2f} Spoilage Arbitrage and avoid complete transit loss."
    elif spoilage_arbitrage_gain > 2000.0 and multiplier > 1.8:
        # Commercial Arbitrage: Closer secondary market yields significantly higher net profit due to freshness premium
        action = "URGENT_REROUTE_RECOMMENDED"
        alert_level = "ARBITRAGE_OPPORTUNITY"
        recommendation = f"Arbitrage trigger: Rerouting to {container_row['secondary_destination']} captures ${spoilage_arbitrage_gain:,.2f} premium over degraded primary shipment."
    elif multiplier > 1.6:
        action = "MONITOR_ELEVATED_RISK"
        alert_level = "WARNING"
        recommendation = "Reefer temperature drifting. Monitor next telemetry interval for reroute trigger."
    else:
        action = "MAINTAIN_ORIGINAL_ROUTE"
        alert_level = "HEALTHY"
        recommendation = f"Container micro-climate optimal. On schedule for {container_row['primary_destination']}."

    return {
        "container_id": container_row["container_id"],
        "commodity": commodity,
        "spoilage_rate_multiplier": multiplier,
        "hours_remaining_shelf_life": hours_remaining,
        "primary_status": primary_status,
        "primary_realized_value_usd": primary_realized_value,
        "secondary_net_value_usd": secondary_net_value,
        "spoilage_arbitrage_gain_usd": max(0.0, spoilage_arbitrage_gain) if "REROUTE" in action else 0.0,
        "action_decision": action,
        "alert_level": alert_level,
        "recommendation": recommendation,
    }


def compute_fleet_arbitrage_summary(telemetry_df: pd.DataFrame) -> pd.DataFrame:
    """Processes entire fleet DataFrame and attaches spoilage arbitrage analytics."""
    evaluations = [evaluate_container_arbitrage(row) for _, row in telemetry_df.iterrows()]
    eval_df = pd.DataFrame(evaluations)
    merged = pd.merge(telemetry_df, eval_df, on=["container_id", "commodity"])
    return merged
