"""
Unit tests for src/economics.py
Validates crop economic arbitrage, yield differentials, input cost savings,
transportation freight costs, and breakeven haulage distance.
"""

import sys
from pathlib import Path
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from economics import (
    calculate_crop_economic_arbitrage,
    compute_location_economic_rankings,
    CROP_ECONOMIC_BENCHMARKS,
)


def test_positive_csi_economic_arbitrage():
    # If target location has higher CSI (e.g. 85 vs 65, +20 pts), yield and revenue must be positive
    res = calculate_crop_economic_arbitrage(
        crop="Rice",
        baseline_csi=65.0,
        target_csi=85.0,
        farm_size_hectares=10.0,
        transport_distance_km=80.0
    )
    assert res["csi_gain"] == 20.0
    assert res["yield_gain_quintals"] > 0
    assert res["gross_revenue_gain_inr"] > 0
    assert res["input_cost_savings_inr"] > 0
    assert res["net_arbitrage_profit_inr"] > 0
    assert res["breakeven_distance_km"] > res["transport_haulage_cost_inr"] / 100.0


def test_negative_csi_economic_penalty():
    # If target has worse CSI (e.g. 50 vs 75, -25 pts), yield gain should be negative
    res = calculate_crop_economic_arbitrage(
        crop="Wheat",
        baseline_csi=75.0,
        target_csi=50.0,
        farm_size_hectares=5.0,
        transport_distance_km=50.0
    )
    assert res["csi_gain"] == -25.0
    assert res["yield_gain_quintals"] < 0
    assert res["gross_revenue_gain_inr"] < 0
    assert res["net_arbitrage_profit_inr"] < 0


def test_location_economic_rankings():
    mock_locs = pd.DataFrame([
        {"location_name": "Hub_Base", "csi": 60.0, "distance_km": 0.0, "region": "Region_A"},
        {"location_name": "Hub_Superior", "csi": 82.0, "distance_km": 110.0, "region": "Region_A"},
        {"location_name": "Hub_Inferior", "csi": 45.0, "distance_km": 90.0, "region": "Region_B"},
    ])
    ranked = compute_location_economic_rankings(
        loc_df=mock_locs,
        crop="Cotton",
        base_loc_name="Hub_Base",
        farm_size_ha=5.0
    )
    assert len(ranked) == 2
    # Hub_Superior should rank #1 with positive net profit
    assert ranked.iloc[0]["location_name"] == "Hub_Superior"
    assert ranked.iloc[0]["net_profit_inr"] > 0


if __name__ == "__main__":
    test_positive_csi_economic_arbitrage()
    test_negative_csi_economic_penalty()
    test_location_economic_rankings()
    print("All Economic Arbitrage unit tests passed successfully!")
