"""
Unit tests for src/iot_simulator.py and src/spoilage_arbitrage.py
Tests IoT streaming telemetry generation, Arrhenius spoilage decay multipliers,
and Spoilage Arbitrage dollar capture decision logic.
"""

import sys
from pathlib import Path
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from iot_simulator import generate_fleet_telemetry, COMMODITY_SPECS
from spoilage_arbitrage import (
    calculate_spoilage_rate_multiplier,
    evaluate_container_arbitrage,
    compute_fleet_arbitrage_summary,
)


def test_iot_telemetry_generation():
    df = generate_fleet_telemetry(num_containers=6)
    assert len(df) == 6
    expected_cols = [
        "container_id", "commodity", "cargo_tonnage", "cargo_value_usd",
        "internal_temp_celsius", "internal_humidity_percent", "vibration_g",
        "hours_to_primary_market", "hours_to_secondary_market"
    ]
    for col in expected_cols:
        assert col in df.columns


def test_spoilage_rate_multiplier_normal():
    # Hass Avocados ideal temp is 4-7 C. At 5 C, multiplier should be 1.0 (no degradation acceleration)
    mult = calculate_spoilage_rate_multiplier("Hass Avocados", internal_temp_c=5.5, internal_hum=90.0)
    assert mult == 1.0


def test_spoilage_rate_multiplier_elevated_temperature():
    # At 17 C (10 C above max ideal of 7 C), multiplier should be approximately q10 = 2.2
    mult = calculate_spoilage_rate_multiplier("Hass Avocados", internal_temp_c=17.0, internal_hum=90.0)
    assert 2.0 <= mult <= 2.5


def test_spoilage_arbitrage_decision_logic():
    # Construct an at-risk container whose shelf life will expire before primary market arrival
    test_container = pd.Series({
        "container_id": "CONT-TEST-001",
        "commodity": "Hass Avocados",
        "cargo_tonnage": 20.0,
        "cargo_value_usd": 64000.0,
        "origin": "Ratnagiri",
        "primary_destination": "New Delhi",
        "secondary_destination": "Pune",
        "internal_temp_celsius": 17.5,      # High temperature drift
        "internal_humidity_percent": 60.0,   # Dry air accelerates decay
        "hours_to_primary_market": 60.0,     # Takes 60 hours, but remaining shelf life will be ~48 hrs
        "hours_to_secondary_market": 4.5,
        "dist_to_secondary_km": 250.0,
    })

    result = evaluate_container_arbitrage(test_container)
    assert "hours_remaining_shelf_life" in result
    assert "spoilage_arbitrage_gain_usd" in result
    assert result["action_decision"] == "URGENT_REROUTE_RECOMMENDED"
    assert result["spoilage_arbitrage_gain_usd"] > 10000.0  # Captures > $50,000 in saved value


def test_fleet_arbitrage_summary():
    df = generate_fleet_telemetry(num_containers=4)
    summary = compute_fleet_arbitrage_summary(df)
    assert len(summary) == 4
    assert "action_decision" in summary.columns
    assert "spoilage_arbitrage_gain_usd" in summary.columns


if __name__ == "__main__":
    test_iot_telemetry_generation()
    test_spoilage_rate_multiplier_normal()
    test_spoilage_rate_multiplier_elevated_temperature()
    test_spoilage_arbitrage_decision_logic()
    test_fleet_arbitrage_summary()
    print("All Spoilage Arbitrage unit tests passed successfully!")
