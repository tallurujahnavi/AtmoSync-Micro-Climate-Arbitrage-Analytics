"""
AtmoSync: Micro-Climate Arbitrage Analytics
Module: iot_simulator.py
Description: High-throughput IoT sensor telemetry generator simulating container micro-climate
             measurements (temperature, humidity, vibration, GPS coordinates) and refrigeration
             failures for perishable agricultural commodities (e.g., Avocados, Berries, Mangoes).
             Follows Apache Kafka / Snowflake streaming event schema.
"""

import json
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import numpy as np
import pandas as pd


# Agronomic optimal storage bands & degradation parameters
COMMODITY_SPECS = {
    "Hass Avocados": {
        "ideal_temp_c": (4.0, 7.0),
        "ideal_hum_pct": (85.0, 95.0),
        "max_vibration_g": 0.8,
        "base_shelf_life_hours": 168.0,  # 7 days under optimal conditions
        "q10_temp_sensitivity": 2.2,     # Spoilage doubles every 10 deg C drift
        "wholesale_price_per_ton": 3200.0,
    },
    "Alphonso Mangoes": {
        "ideal_temp_c": (10.0, 13.0),
        "ideal_hum_pct": (85.0, 90.0),
        "max_vibration_g": 0.6,
        "base_shelf_life_hours": 120.0,  # 5 days
        "q10_temp_sensitivity": 2.5,
        "wholesale_price_per_ton": 4500.0,
    },
    "Strawberries": {
        "ideal_temp_c": (0.0, 2.0),
        "ideal_hum_pct": (90.0, 95.0),
        "max_vibration_g": 0.4,
        "base_shelf_life_hours": 72.0,   # 3 days
        "q10_temp_sensitivity": 3.0,
        "wholesale_price_per_ton": 5800.0,
    },
    "Cavendish Bananas": {
        "ideal_temp_c": (13.0, 15.0),
        "ideal_hum_pct": (90.0, 95.0),
        "max_vibration_g": 1.0,
        "base_shelf_life_hours": 216.0,  # 9 days
        "q10_temp_sensitivity": 2.0,
        "wholesale_price_per_ton": 1800.0,
    },
}

# Major logistical transit corridors with primary and secondary arbitrage markets
CORRIDORS = [
    {
        "corridor_id": "CORR-WEST-01",
        "origin": "Ratnagiri Farms, Maharashtra",
        "origin_coords": (16.99, 73.30),
        "primary_destination": "New Delhi Central Terminal",
        "primary_coords": (28.61, 77.20),
        "primary_dist_km": 1750.0,
        "secondary_destination": "Pune Wholesale Agro-Mandi",
        "secondary_coords": (18.52, 73.85),
        "secondary_dist_km": 310.0,
    },
    {
        "corridor_id": "CORR-SOUTH-02",
        "origin": "Kodaikanal Valley, Tamil Nadu",
        "origin_coords": (10.23, 77.48),
        "primary_destination": "Mumbai Cold Hub",
        "primary_coords": (19.07, 72.87),
        "primary_dist_km": 1320.0,
        "secondary_destination": "Bengaluru Electronic City Mandi",
        "secondary_coords": (12.97, 77.59),
        "secondary_dist_km": 460.0,
    },
    {
        "corridor_id": "CORR-CENTRAL-03",
        "origin": "Nashik Agro Cluster, Maharashtra",
        "origin_coords": (19.99, 73.78),
        "primary_destination": "Kolkata Port Terminal",
        "primary_coords": (22.57, 88.36),
        "primary_dist_km": 1820.0,
        "secondary_destination": "Nagpur Central Logistics Hub",
        "secondary_coords": (21.14, 79.08),
        "secondary_dist_km": 710.0,
    },
    {
        "corridor_id": "CORR-NORTH-04",
        "origin": "Shimla Cold Orchards, Himachal Pradesh",
        "origin_coords": (31.10, 77.17),
        "primary_destination": "Ahmedabad APMC Hub",
        "primary_coords": (23.02, 72.57),
        "primary_dist_km": 1150.0,
        "secondary_destination": "Chandigarh Mandi Complex",
        "secondary_coords": (30.73, 76.77),
        "secondary_dist_km": 115.0,
    },
]


def generate_fleet_telemetry(num_containers: int = 8, inject_anomalies: bool = True) -> pd.DataFrame:
    """
    Generates synthetic IoT telemetry for container shipments.
    Simulates real-time container health, coordinates, refrigeration status, and micro-climate drift.
    """
    random.seed(42)
    np.random.seed(42)

    records = []
    base_time = datetime.now()

    commodities = list(COMMODITY_SPECS.keys())

    for i in range(num_containers):
        container_id = f"CONT-ATMO-{1000 + i}"
        corridor = CORRIDORS[i % len(CORRIDORS)]
        commodity = commodities[i % len(commodities)]
        specs = COMMODITY_SPECS[commodity]

        cargo_tonnage = round(random.uniform(18.0, 24.0), 1)
        cargo_value = round(cargo_tonnage * specs["wholesale_price_per_ton"], 2)

        # Transit progression percentage (between 15% and 75% journey completed)
        progress = random.uniform(0.20, 0.65)
        current_lat = corridor["origin_coords"][0] + progress * (corridor["primary_coords"][0] - corridor["origin_coords"][0])
        current_lon = corridor["origin_coords"][1] + progress * (corridor["primary_coords"][1] - corridor["origin_coords"][1])

        dist_to_primary = round(corridor["primary_dist_km"] * (1.0 - progress), 1)
        dist_to_secondary = round(corridor["secondary_dist_km"] * random.uniform(0.3, 0.7), 1)

        speed_kmh = 55.0  # standard highway reefer truck speed
        hours_to_primary = round(dist_to_primary / speed_kmh, 1)
        hours_to_secondary = round(dist_to_secondary / speed_kmh, 1)

        # Baseline optimal container condition
        ideal_t_min, ideal_t_max = specs["ideal_temp_c"]
        ideal_h_min, ideal_h_max = specs["ideal_hum_pct"]

        # Anomaly injection for Container A (CONT-ATMO-1000) and Container C (CONT-ATMO-1002)
        is_anomalous = inject_anomalies and (i in [0, 2])
        if is_anomalous:
            # Compressor failure: Temperature spikes, humidity fluctuates
            temp_c = round(ideal_t_max + random.uniform(7.5, 12.0), 2)
            hum_pct = round(ideal_h_min - random.uniform(20.0, 35.0), 2)
            vibration_g = round(specs["max_vibration_g"] + random.uniform(0.3, 0.6), 2)
            reefer_status = "WARNING_COMPRESSOR_DRIFT"
        else:
            temp_c = round(random.uniform(ideal_t_min, ideal_t_max), 2)
            hum_pct = round(random.uniform(ideal_h_min, ideal_h_max), 2)
            vibration_g = round(random.uniform(0.1, specs["max_vibration_g"]), 2)
            reefer_status = "OPTIMAL_NORMAL"

        records.append({
            "container_id": container_id,
            "timestamp": (base_time - timedelta(minutes=random.randint(2, 15))).strftime("%Y-%m-%d %H:%M:%S"),
            "commodity": commodity,
            "cargo_tonnage": cargo_tonnage,
            "cargo_value_usd": cargo_value,
            "origin": corridor["origin"],
            "primary_destination": corridor["primary_destination"],
            "secondary_destination": corridor["secondary_destination"],
            "current_latitude": round(current_lat, 4),
            "current_longitude": round(current_lon, 4),
            "internal_temp_celsius": temp_c,
            "internal_humidity_percent": hum_pct,
            "vibration_g": vibration_g,
            "reefer_telemetry_status": reefer_status,
            "hours_to_primary_market": hours_to_primary,
            "hours_to_secondary_market": hours_to_secondary,
            "dist_to_primary_km": dist_to_primary,
            "dist_to_secondary_km": dist_to_secondary,
        })

    df = pd.DataFrame(records)
    return df
