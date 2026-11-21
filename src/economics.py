"""
AtmoSync: Micro-Climate Arbitrage Analytics
Module: economics.py
Description: Economic Arbitrage & Financial ROI Engine.
             Bridges meteorological suitability metrics and spoilage degradation curves
             into tangible financial gains:
             1. Crop yield estimation (quintals/hectare) & APMC mandi revenue differentials.
             2. Input cost savings (irrigation power, synthetic fertilizer, pesticide reduction).
             3. Transport Breakeven Haulage Distance (Haversine km vs. Arbitrage Margin).
             4. Commodity spot-pricing joins for cold-chain transit arbitrage.
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd


# 2025-2026 Indian Government Minimum Support Price (MSP) & APMC Mandi Wholesale Benchmarks (INR / Quintal)
# 1 Quintal = 100 kg
CROP_ECONOMIC_BENCHMARKS = {
    "Rice": {
        "base_yield_q_per_ha": 38.0,       # Base yield in quintals per hectare
        "msp_price_inr_per_q": 2300.0,     # MSP Grade A (approx INR/quintal)
        "csi_yield_elasticity": 0.45,      # 10 pt CSI gain yields 4.5% higher harvest
        "irrigation_cost_per_ha": 8500.0,  # Optimal rainfall reduces pumping diesel/electricity
        "fertilizer_cost_per_ha": 9200.0,  # Favorable micro-climate maximizes nutrient uptake
    },
    "Wheat": {
        "base_yield_q_per_ha": 35.0,
        "msp_price_inr_per_q": 2425.0,
        "csi_yield_elasticity": 0.50,
        "irrigation_cost_per_ha": 6500.0,
        "fertilizer_cost_per_ha": 7800.0,
    },
    "Cotton": {
        "base_yield_q_per_ha": 18.0,
        "msp_price_inr_per_q": 7120.0,     # Medium staple MSP
        "csi_yield_elasticity": 0.55,
        "irrigation_cost_per_ha": 7200.0,
        "fertilizer_cost_per_ha": 11500.0,
    },
    "Maize": {
        "base_yield_q_per_ha": 32.0,
        "msp_price_inr_per_q": 2225.0,
        "csi_yield_elasticity": 0.40,
        "irrigation_cost_per_ha": 5800.0,
        "fertilizer_cost_per_ha": 6900.0,
    },
    "Groundnut": {
        "base_yield_q_per_ha": 20.0,
        "msp_price_inr_per_q": 6780.0,
        "csi_yield_elasticity": 0.48,
        "irrigation_cost_per_ha": 6200.0,
        "fertilizer_cost_per_ha": 8100.0,
    },
    "Sugarcane": {
        "base_yield_q_per_ha": 780.0,      # High biomass tonnage
        "msp_price_inr_per_q": 340.0,      # Fair & Remunerative Price (FRP)
        "csi_yield_elasticity": 0.35,
        "irrigation_cost_per_ha": 14000.0,
        "fertilizer_cost_per_ha": 13500.0,
    },
}

# Agricultural Freight & Logistics rates in India
ROAD_FREIGHT_COST_INR_PER_TON_KM = 3.80  # Commercial rural truck rate per ton-km
COLD_CHAIN_FREIGHT_INR_PER_TON_KM = 6.20  # Reefer transport rate


def calculate_crop_economic_arbitrage(
    crop: str,
    baseline_csi: float,
    target_csi: float,
    farm_size_hectares: float = 5.0,
    transport_distance_km: float = 120.0
) -> Dict:
    """
    Computes economic ROI of cultivating in a superior micro-climate hub or procuring from it.
    
    Returns:
    - Yield differential (quintals)
    - Gross revenue boost (INR)
    - Input cost efficiency savings (INR)
    - Logistical haulage cost (INR)
    - Net Economic Arbitrage Profit (INR)
    - Breakeven Transport Distance (km)
    """
    if crop not in CROP_ECONOMIC_BENCHMARKS:
        raise ValueError(f"Crop '{crop}' not found in economic database.")

    bench = CROP_ECONOMIC_BENCHMARKS[crop]
    csi_delta = target_csi - baseline_csi

    # Percentage yield shift based on agro-climatic elasticity
    # e.g., +15 CSI pts * 0.45 elasticity = +6.75% yield gain
    yield_shift_pct = (csi_delta / 100.0) * bench["csi_yield_elasticity"]
    
    baseline_yield_total = bench["base_yield_q_per_ha"] * farm_size_hectares
    target_yield_total = baseline_yield_total * (1.0 + yield_shift_pct)
    yield_gain_quintals = round(target_yield_total - baseline_yield_total, 2)

    # Revenue shift at government MSP / wholesale mandi price
    baseline_revenue = baseline_yield_total * bench["msp_price_inr_per_q"]
    target_revenue = target_yield_total * bench["msp_price_inr_per_q"]
    gross_revenue_gain = round(target_revenue - baseline_revenue, 2)

    # Input savings (better rainfall and natural humidity reduce pumping diesel and fertilizer runoff)
    if csi_delta > 0:
        input_savings_pct = min(0.20, (csi_delta / 100.0) * 0.35)
    else:
        input_savings_pct = max(-0.25, (csi_delta / 100.0) * 0.40)

    total_input_baseline = (bench["irrigation_cost_per_ha"] + bench["fertilizer_cost_per_ha"]) * farm_size_hectares
    input_cost_savings = round(total_input_baseline * input_savings_pct, 2)

    # Logistical hauling cost to transport harvest between regions
    tonnage_to_move = target_yield_total / 10.0  # 10 quintals = 1 Metric Ton
    haulage_cost = round(tonnage_to_move * transport_distance_km * ROAD_FREIGHT_COST_INR_PER_TON_KM, 2)

    # Net Economic Arbitrage = (Revenue Gain + Input Savings) - Haulage Cost
    net_arbitrage_inr = round(gross_revenue_gain + input_cost_savings - haulage_cost, 2)

    # Maximum distance you can haul the harvest before freight costs eat all arbitrage profits
    gross_benefit = gross_revenue_gain + input_cost_savings
    cost_per_km = (tonnage_to_move * ROAD_FREIGHT_COST_INR_PER_TON_KM)
    breakeven_km = round(gross_benefit / max(cost_per_km, 1.0), 1) if gross_benefit > 0 else 0.0

    return {
        "crop": crop,
        "farm_size_ha": farm_size_hectares,
        "csi_baseline": round(baseline_csi, 1),
        "csi_target": round(target_csi, 1),
        "csi_gain": round(csi_delta, 1),
        "yield_gain_quintals": yield_gain_quintals,
        "gross_revenue_gain_inr": gross_revenue_gain,
        "input_cost_savings_inr": input_cost_savings,
        "transport_haulage_cost_inr": haulage_cost,
        "net_arbitrage_profit_inr": net_arbitrage_inr,
        "breakeven_distance_km": breakeven_km,
        "roi_multiple": round((gross_benefit / max(haulage_cost, 1.0)), 2) if haulage_cost > 0 else 0.0,
    }


def compute_location_economic_rankings(
    loc_df: pd.DataFrame,
    crop: str,
    base_loc_name: str,
    farm_size_ha: float = 5.0
) -> pd.DataFrame:
    """
    Ranks nearby alternative locations by Net Financial Arbitrage Profit (INR)
    relative to a farmer's or trader's home location.
    """
    if base_loc_name not in loc_df["location_name"].values:
        raise ValueError(f"Base location '{base_loc_name}' not in dataset.")

    base_row = loc_df[loc_df["location_name"] == base_loc_name].iloc[0]
    base_csi = base_row["csi"]

    econ_records = []
    for _, r in loc_df.iterrows():
        if r["location_name"] == base_loc_name:
            continue
        dist_km = r.get("distance_km", r.get("km", 100.0))
        econ = calculate_crop_economic_arbitrage(
            crop=crop,
            baseline_csi=base_csi,
            target_csi=r["csi"],
            farm_size_hectares=farm_size_ha,
            transport_distance_km=float(dist_km)
        )
        econ_records.append({
            "location_name": r["location_name"],
            "region": r.get("region", "General"),
            "distance_km": dist_km,
            "target_csi": r["csi"],
            "csi_gain": econ["csi_gain"],
            "yield_gain_q": econ["yield_gain_quintals"],
            "gross_revenue_inr": econ["gross_revenue_gain_inr"],
            "haulage_cost_inr": econ["transport_haulage_cost_inr"],
            "net_profit_inr": econ["net_arbitrage_profit_inr"],
            "breakeven_km": econ["breakeven_distance_km"],
        })

    econ_df = pd.DataFrame(econ_records).sort_values(by="net_profit_inr", ascending=False).reset_index(drop=True)
    return econ_df
