"""
Unit tests for src/arbitrage.py
Tests band scoring, suitability index calculation, and Haversine distance.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from arbitrage import (
    band_score,
    calculate_crop_suitability,
    haversine_distance,
    find_microclimate_arbitrage,
    CROPS,
)


def test_band_score_inside_ideal():
    # Value inside ideal range [22, 32] should yield 1.0
    scores = band_score(np.array([22.0, 25.0, 32.0]), lo=22.0, hi=32.0, tol=10.0)
    assert np.allclose(scores, [1.0, 1.0, 1.0])


def test_band_score_outside_tolerance():
    # Value beyond ideal + tol (32 + 10 = 42) or ideal - tol (22 - 10 = 12) should yield 0.0
    scores = band_score(np.array([10.0, 45.0]), lo=22.0, hi=32.0, tol=10.0)
    assert np.allclose(scores, [0.0, 0.0])


def test_band_score_partial_linear_decay():
    # Value at midpoint of tolerance band (e.g., 37 with hi=32, tol=10) should yield 0.5
    score = band_score(np.array([37.0]), lo=22.0, hi=32.0, tol=10.0)
    assert np.isclose(score[0], 0.5)


def test_calculate_crop_suitability():
    sample_data = pd.DataFrame({
        "temperature_celsius": [25.0, 38.0],
        "humidity": [75.0, 30.0],
        "precip_mm": [5.0, 20.0],
        "uv_index": [6.0, 11.0],
    })
    csi = calculate_crop_suitability(sample_data, crop="Rice")
    assert len(csi) == 2
    # First row is ideal across all 4 parameters -> should be close to 100
    assert csi.iloc[0] == 100.0
    # Second row is outside ideal -> lower CSI
    assert csi.iloc[1] < csi.iloc[0]


def test_haversine_distance():
    # Distance between Bengaluru (12.97, 77.59) and Mysore (12.30, 76.64) ~ 128 km
    dist = haversine_distance(12.97, 77.59, 12.30, 76.64)
    assert 120.0 < dist < 140.0


def test_find_microclimate_arbitrage():
    loc_summary = pd.DataFrame([
        {"location_name": "Bengaluru", "latitude": 12.97, "longitude": 77.59, "csi": 72.0, "temp": 24.0, "hum": 65.0, "rain": 2.0},
        {"location_name": "Mysore", "latitude": 12.30, "longitude": 76.64, "csi": 85.0, "temp": 26.0, "hum": 70.0, "rain": 4.0},
        {"location_name": "Delhi", "latitude": 28.61, "longitude": 77.20, "csi": 50.0, "temp": 35.0, "hum": 40.0, "rain": 1.0},
    ])
    origin, candidates = find_microclimate_arbitrage(loc_summary, origin_location="Bengaluru", max_radius_km=300.0)
    assert origin["location_name"] == "Bengaluru"
    # Delhi is >1500 km away, so only Mysore should be in radius
    assert len(candidates) == 1
    assert candidates.iloc[0]["location_name"] == "Mysore"
    assert candidates.iloc[0]["csi_gain"] == 13.0


if __name__ == "__main__":
    test_band_score_inside_ideal()
    test_band_score_outside_tolerance()
    test_band_score_partial_linear_decay()
    test_calculate_crop_suitability()
    test_haversine_distance()
    test_find_microclimate_arbitrage()
    print("All unit tests passed successfully!")
