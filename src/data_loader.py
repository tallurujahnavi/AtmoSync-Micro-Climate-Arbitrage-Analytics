"""
AtmoSync: Micro-Climate Arbitrage Analytics
Module: data_loader.py
Description: Beginner-friendly, robust data loading and structural inspection
             for Phase 1 data understanding.
"""

import os
from pathlib import Path
from typing import Dict, Tuple, Optional
import pandas as pd
import numpy as np


# Standard column dictionary for Kaggle Global Weather Repository & AtmoSync project
DATA_DICTIONARY_DEFINITIONS = {
    "country": ("object", "Name of the country", "Categorical"),
    "location_name": ("object", "Name of the monitored city/location", "Categorical"),
    "region": ("object", "State/Administrative region or province", "Categorical"),
    "latitude": ("float64", "Geographical latitude coordinate", "Degrees (-90 to +90)"),
    "longitude": ("float64", "Geographical longitude coordinate", "Degrees (-180 to +180)"),
    "timezone": ("object", "Local IANA timezone", "Timezone string"),
    "last_updated_epoch": ("int64", "Unix timestamp of weather measurement", "Epoch seconds"),
    "last_updated": ("object", "Local observation timestamp (YYYY-MM-DD HH:MM)", "Datetime string"),
    "temperature_celsius": ("float64", "Ambient air temperature in Celsius", "°C"),
    "temperature_fahrenheit": ("float64", "Ambient air temperature in Fahrenheit", "°F"),
    "condition_text": ("object", "Text description of weather condition", "Text"),
    "wind_mph": ("float64", "Sustained wind speed in miles per hour", "mph"),
    "wind_kph": ("float64", "Sustained wind speed in kilometers per hour", "km/h"),
    "wind_degree": ("int64", "Wind direction clockwise from North", "Degrees (0-360)"),
    "wind_direction": ("object", "Wind direction compass point (e.g., N, ENE)", "Compass string"),
    "pressure_mb": ("float64", "Barometric atmospheric pressure", "Millibars (hPa)"),
    "pressure_in": ("float64", "Barometric atmospheric pressure", "Inches of Hg"),
    "precip_mm": ("float64", "Precipitation/rainfall accumulation", "Millimeters (mm)"),
    "precip_in": ("float64", "Precipitation/rainfall accumulation", "Inches"),
    "humidity": ("int64", "Relative atmospheric humidity percentage", "%"),
    "cloud": ("int64", "Cloud cover percentage", "%"),
    "feels_like_celsius": ("float64", "Apparent perceived temperature in Celsius", "°C"),
    "feelslike_celsius": ("float64", "Apparent perceived temperature in Celsius", "°C"),
    "visibility_km": ("float64", "Horizontal visibility distance", "Kilometers (km)"),
    "uv_index": ("float64", "Solar ultraviolet radiation index", "Index (0-12+)"),
    "gust_kph": ("float64", "Peak instantaneous wind gust speed", "km/h"),
    "air_quality_PM2.5": ("float64", "Fine particulate matter <= 2.5 micrometers", "µg/m³"),
    "air_quality_PM10": ("float64", "Coarse particulate matter <= 10 micrometers", "µg/m³"),
    "air_quality_Carbon_Monoxide": ("float64", "Carbon monoxide concentration", "µg/m³"),
    "air_quality_Ozone": ("float64", "Tropospheric ozone concentration", "µg/m³"),
}


def find_dataset_path(preferred_path: str = "data/raw/GlobalWeatherRepository.csv") -> Tuple[str, bool]:
    """
    Locates the dataset, checking for real Kaggle CSV first, then falling back to synthetic.
    Returns: (resolved_path, is_synthetic)
    """
    base_dir = Path(__file__).resolve().parent.parent
    kaggle_csv = base_dir / preferred_path
    synthetic_csv = base_dir / "data/raw/sample_SYNTHETIC.csv"

    if kaggle_csv.exists():
        return str(kaggle_csv), False
    elif synthetic_csv.exists():
        return str(synthetic_csv), True
    else:
        raise FileNotFoundError(
            f"No dataset found at {kaggle_csv} or {synthetic_csv}. "
            f"Please place 'GlobalWeatherRepository.csv' into 'data/raw/'."
        )


def load_dataset(file_path: Optional[str] = None) -> Tuple[pd.DataFrame, bool]:
    """
    Loads raw CSV dataset into a pandas DataFrame with validation.
    """
    if file_path is None:
        path, is_synthetic = find_dataset_path()
    else:
        path = str(file_path)
        is_synthetic = "SYNTHETIC" in os.path.basename(path).upper()

    if not os.path.exists(path):
        raise FileNotFoundError(f"Dataset file not found: {path}")

    if not path.lower().endswith(".csv"):
        raise ValueError("Only CSV dataset files are supported.")

    if os.path.getsize(path) == 0:
        raise ValueError("Dataset file is empty.")

    print(f"[AtmoSync Data Loader] Loading data from: {path}")

    if is_synthetic:
        print(
            "[WARNING] Active dataset is SYNTHETIC test data. "
            "Place the real Kaggle CSV in 'data/raw/' for final grading."
        )

    df = pd.read_csv(path)

    if df.empty:
        raise ValueError("CSV file contains no data rows.")

    if len(df.columns) == 0:
        raise ValueError("CSV file contains no columns.")

    return df, is_synthetic


def inspect_dataset_structure(df: pd.DataFrame) -> Dict:
    """
    Performs structural inspection of the dataset.
    Extracts shape, column count, dtypes, date range,
    location count, and country list.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input must be a pandas DataFrame.")

    if df.empty:
        raise ValueError("Dataset is empty. Cannot inspect structure.")

    inspection = {}
    inspection["rows"], inspection["columns"] = df.shape

    date_cols = [
        c for c in ["last_updated", "date", "last_updated_epoch"]
        if c in df.columns
    ]

    if "last_updated" in df.columns:
        parsed_dates = pd.to_datetime(
            df["last_updated"], errors="coerce"
        )
    elif "date" in df.columns:
        parsed_dates = pd.to_datetime(
            df["date"], errors="coerce"
        )
    elif "last_updated_epoch" in df.columns:
        parsed_dates = pd.to_datetime(
            df["last_updated_epoch"], unit="s", errors="coerce"
        )
    else:
        parsed_dates = pd.Series(dtype="datetime64[ns]")

    valid_dates = parsed_dates.dropna()

    inspection["date_range"] = (
        (str(valid_dates.min()), str(valid_dates.max()))
        if not valid_dates.empty
        else ("Unavailable", "Unavailable")
    )

    inspection["locations"] = (
        int(df["location_name"].nunique())
        if "location_name" in df.columns
        else 0
    )

    inspection["countries"] = (
        sorted(df["country"].dropna().unique().tolist())
        if "country" in df.columns
        else []
    )

    inspection["missing_values"] = int(df.isna().sum().sum())
    inspection["duplicate_rows"] = int(df.duplicated().sum())
    inspection["date_columns_found"] = date_cols

    return inspection


def generate_data_dictionary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Constructs a professional Data Dictionary Table for documentation and deliverables.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input must be a pandas DataFrame.")

    if df.empty:
        raise ValueError("Input dataset is empty.")

    records = []

    for col in df.columns:
        dtype = str(df[col].dtype)
        null_count = int(df[col].isna().sum())
        non_null_count = int(df[col].notna().sum())
        null_pct = round((null_count / len(df)) * 100, 2)

        sample_val = (
            str(df[col].dropna().iloc[0])
            if non_null_count > 0
            else "None"
        )

        meta = DATA_DICTIONARY_DEFINITIONS.get(
            col,
            (dtype, "Observed atmospheric/geographical feature", "Standard")
        )

        desc = meta[1]
        units = meta[2]

        records.append({
            "Column Name": col,
            "Pandas Dtype": dtype,
            "Non-Null Count": non_null_count,
            "Null Count": null_count,
            "Null %": null_pct,
            "Sample Value": sample_val,
            "Physical Units": units,
            "Description": desc
        })

    return pd.DataFrame(records)


if __name__ == "__main__":
    df, is_syn = load_dataset()
    info = inspect_dataset_structure(df)
    print("\n--- DATASET INSPECTION SUMMARY ---")
    for k, v in info.items():
        print(f"  {k}: {v}")

    print("\n--- DATA DICTIONARY PREVIEW (FIRST 5 COLS) ---")
    dict_df = generate_data_dictionary(df)
    print(dict_df.head(5).to_string(index=False))
