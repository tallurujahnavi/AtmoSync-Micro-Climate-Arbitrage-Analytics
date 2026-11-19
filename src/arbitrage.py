"""
AtmoSync: Micro-Climate Arbitrage Analytics
Module: arbitrage.py
Description: Core agronomic suitability modeling, spatial Haversine distance calculations,
             and micro-climate arbitrage differential analytics.
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy import stats


# ---------- Crop Agronomic Ideal Ranges & Tolerances ----------
# Format: variable: (ideal_low, ideal_high, tolerance_band)
# Inside [ideal_low, ideal_high], score = 1.0; decays linearly to 0 at ideal +- tolerance.
CROPS: Dict[str, Dict[str, Tuple[float, float, float]]] = {
    "Rice": {
        "temp": (22.0, 32.0, 10.0),
        "hum": (60.0, 90.0, 30.0),
        "rain": (0.0, 12.0, 10.0),
        "uv": (3.0, 9.0, 5.0),
    },
    "Wheat": {
        "temp": (12.0, 25.0, 10.0),
        "hum": (40.0, 70.0, 25.0),
        "rain": (0.0, 4.0, 6.0),
        "uv": (3.0, 8.0, 5.0),
    },
    "Cotton": {
        "temp": (21.0, 34.0, 10.0),
        "hum": (40.0, 75.0, 25.0),
        "rain": (0.0, 5.0, 8.0),
        "uv": (4.0, 10.0, 5.0),
    },
    "Maize": {
        "temp": (20.0, 30.0, 10.0),
        "hum": (50.0, 80.0, 25.0),
        "rain": (0.0, 8.0, 8.0),
        "uv": (3.0, 9.0, 5.0),
    },
    "Groundnut": {
        "temp": (22.0, 32.0, 10.0),
        "hum": (45.0, 75.0, 25.0),
        "rain": (0.0, 5.0, 8.0),
        "uv": (4.0, 10.0, 5.0),
    },
    "Sugarcane": {
        "temp": (24.0, 35.0, 10.0),
        "hum": (60.0, 85.0, 25.0),
        "rain": (0.0, 10.0, 10.0),
        "uv": (4.0, 10.0, 5.0),
    },
}

# Agro-climatic weighting schema for Crop Suitability Index
WEIGHTS: Dict[str, float] = {
    "temp": 0.40,  # Temperature is primary driver of metabolic rate
    "hum": 0.25,   # Relative humidity influences transpiration and fungal risk
    "rain": 0.20,  # Precipitation determines immediate moisture balance
    "uv": 0.15,    # Solar UV index correlates with photosynthetic radiation
}

COLS: Dict[str, str] = {
    "temp": "temperature_celsius",
    "hum": "humidity",
    "rain": "precip_mm",
    "uv": "uv_index",
}

# Indian agricultural crop season mapping by calendar month
SEASONS_MAPPING: Dict[int, str] = {
    1: "Rabi (Nov-Mar)",
    2: "Rabi (Nov-Mar)",
    3: "Rabi (Nov-Mar)",
    4: "Zaid (Apr-May)",
    5: "Zaid (Apr-May)",
    6: "Kharif (Jun-Oct)",
    7: "Kharif (Jun-Oct)",
    8: "Kharif (Jun-Oct)",
    9: "Kharif (Jun-Oct)",
    10: "Kharif (Jun-Oct)",
    11: "Rabi (Nov-Mar)",
    12: "Rabi (Nov-Mar)",
}


def band_score(x: np.ndarray, lo: float, hi: float, tol: float) -> np.ndarray:
    """
    Computes continuous agronomic suitability score:
    - Returns 1.0 inside ideal range [lo, hi].
    - Decays linearly to 0 outside the band up to [lo - tol] or [hi + tol].
    - Returns 0.0 beyond tolerance.
    """
    x_arr = np.asarray(x, dtype=float)
    dist = np.where(x_arr < lo, lo - x_arr, np.where(x_arr > hi, x_arr - hi, 0.0))
    score = np.clip(1.0 - (dist / tol), 0.0, 1.0)
    return score


def calculate_crop_suitability(df: pd.DataFrame, crop: str) -> pd.Series:
    """
    Calculates composite Crop Suitability Index (CSI) scaled from 0 to 100
    for a given crop across all observations in df.
    """
    if crop not in CROPS:
        raise ValueError(f"Crop '{crop}' not found in agronomic database. Available: {list(CROPS.keys())}")

    crop_specs = CROPS[crop]
    composite_score = np.zeros(len(df), dtype=float)

    for param, (lo, hi, tol) in crop_specs.items():
        col_name = COLS[param]
        if col_name not in df.columns:
            raise KeyError(f"Required meteorological column '{col_name}' missing from DataFrame.")
        sub_score = band_score(df[col_name].values, lo, hi, tol)
        composite_score += WEIGHTS[param] * sub_score

    return pd.Series((composite_score * 100.0).round(2), index=df.index, name="csi")


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates great-circle distance between two geographic points on Earth in kilometers
    using the Haversine formula.
    """
    p = np.pi / 180.0
    dlat = (lat2 - lat1) * p
    dlon = (lon2 - lon1) * p
    a = (np.sin(dlat / 2.0) ** 2) + np.cos(lat1 * p) * np.cos(lat2 * p) * (np.sin(dlon / 2.0) ** 2)
    c = 2.0 * np.arcsin(np.sqrt(a))
    return 6371.0 * c  # Earth mean radius in km


def find_microclimate_arbitrage(
    aggregated_loc_df: pd.DataFrame,
    origin_location: str,
    max_radius_km: float = 500.0
) -> Tuple[Optional[pd.Series], pd.DataFrame]:
    """
    Computes micro-climate arbitrage opportunities relative to a focal origin location.
    
    Returns:
    - origin_summary: pd.Series of origin metrics
    - candidate_df: Sorted DataFrame of nearby locations ranked by CSI gain
    """
    if origin_location not in aggregated_loc_df["location_name"].values:
        raise ValueError(f"Origin location '{origin_location}' not present in dataset.")

    origin_row = aggregated_loc_df[aggregated_loc_df["location_name"] == origin_location].iloc[0]
    origin_lat, origin_lon = origin_row["latitude"], origin_row["longitude"]

    candidates = aggregated_loc_df[aggregated_loc_df["location_name"] != origin_location].copy()
    candidates["distance_km"] = [
        round(haversine_distance(origin_lat, origin_lon, r.latitude, r.longitude), 1)
        for _, r in candidates.iterrows()
    ]

    in_radius = candidates[candidates["distance_km"] <= max_radius_km].copy()
    in_radius["csi_gain"] = (in_radius["csi"] - origin_row["csi"]).round(2)
    in_radius["temp_diff_c"] = (in_radius["temp"] - origin_row["temp"]).round(2)
    in_radius["humidity_diff"] = (in_radius["hum"] - origin_row["hum"]).round(2)
    in_radius["rain_diff_mm"] = (in_radius["rain"] - origin_row["rain"]).round(2)

    in_radius = in_radius.sort_values(by="csi_gain", ascending=False).reset_index(drop=True)
    return origin_row, in_radius


def run_regional_anova(df: pd.DataFrame, group_col: str = "region") -> Dict[str, float]:
    """
    Performs one-way ANOVA test to evaluate if crop suitability significantly differs across regions.
    """
    groups = [group["csi"].values for _, group in df.groupby(group_col) if len(group) > 1]
    if len(groups) < 2:
        return {"f_stat": 0.0, "p_val": 1.0, "significant": False}

    f_stat, p_val = stats.f_oneway(*groups)
    return {
        "f_stat": float(round(f_stat, 3)),
        "p_val": float(round(p_val, 5)),
        "significant": bool(p_val < 0.05)
    }


def run_location_ttest(
    df: pd.DataFrame,
    loc_a: str,
    loc_b: str
) -> Dict[str, float]:
    """
    Performs Welch's two-sample t-test between two distinct locations.
    """
    xa = df[df["location_name"] == loc_a]["csi"].dropna()
    xb = df[df["location_name"] == loc_b]["csi"].dropna()

    if len(xa) < 2 or len(xb) < 2:
        return {"t_stat": 0.0, "p_val": 1.0, "significant": False, "mean_diff": 0.0}

    t_stat, p_val = stats.ttest_ind(xa, xb, equal_var=False)
    return {
        "t_stat": float(round(t_stat, 3)),
        "p_val": float(round(p_val, 5)),
        "significant": bool(p_val < 0.05),
        "mean_diff": float(round(xa.mean() - xb.mean(), 2))
    }
