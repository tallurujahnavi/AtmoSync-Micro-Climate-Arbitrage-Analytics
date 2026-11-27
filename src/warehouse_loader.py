"""
AtmoSync: Micro-Climate Arbitrage Analytics
Module: warehouse_loader.py
Description: Day 3 Snowflake staging helper for loading commodity pricing and
             storage profile seed CSVs and preparing Snowflake-ready NDJSON
             ingestion manifests from simulated container telemetry.
"""

import csv
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent

try:
    from src.iot_simulator import IoTSimulator, default_fleet_configs, write_ndjson_stream
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from iot_simulator import IoTSimulator, default_fleet_configs, write_ndjson_stream


def load_commodity_pricing(csv_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Loads commodity spot market pricing rows with typed numeric fields."""
    path = Path(csv_path) if csv_path else ROOT_DIR / "data" / "commodity_pricing.csv"
    if not path.exists():
        raise FileNotFoundError(f"Commodity pricing CSV not found: {path}")

    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as fh:
        for raw in csv.DictReader(fh):
            rows.append(
                {
                    "commodity": raw["commodity"].strip(),
                    "market_name": raw["market_name"].strip(),
                    "market_tier": raw["market_tier"].strip().upper(),
                    "latitude": float(raw["latitude"]),
                    "longitude": float(raw["longitude"]),
                    "spot_price_usd_per_mt": float(raw["spot_price_usd_per_mt"]),
                    "secondary_price_factor": float(raw["secondary_price_factor"]),
                    "base_shelf_life_hours": float(raw["base_shelf_life_hours"]),
                    "q10_factor": float(raw["q10_factor"]),
                    "humidity_sensitivity_alpha": float(raw["humidity_sensitivity_alpha"]),
                    "haulage_cost_usd_per_mt_km": float(raw["haulage_cost_usd_per_mt_km"]),
                    "effective_date": raw["effective_date"].strip(),
                }
            )
    return rows


def load_storage_profiles(csv_path: Optional[str] = None) -> Dict[str, Dict[str, float]]:
    """Loads commodity cold-chain safe threshold profiles keyed by commodity."""
    path = Path(csv_path) if csv_path else ROOT_DIR / "data" / "commodity_storage_profiles.csv"
    if not path.exists():
        raise FileNotFoundError(f"Storage profiles CSV not found: {path}")

    profiles: Dict[str, Dict[str, float]] = {}
    with path.open("r", encoding="utf-8", newline="") as fh:
        for raw in csv.DictReader(fh):
            profiles[raw["commodity"].strip()] = {
                "temp_min_c": float(raw["temp_min_c"]),
                "temp_max_c": float(raw["temp_max_c"]),
                "hum_min_pct": float(raw["hum_min_pct"]),
                "hum_max_pct": float(raw["hum_max_pct"]),
                "max_vibration_g": float(raw["max_vibration_g"]),
            }
    return profiles


def export_snowflake_staging_bundle(
    output_dir: str,
    steps: int = 12,
    seed: int = 2026,
) -> Dict[str, Any]:
    """
    Exports an NDJSON telemetry batch and manifest summary ready for
    `sql/snowflake_seed_load.sql` stage upload.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    pricing_rows = load_commodity_pricing()
    storage_profiles = load_storage_profiles()

    sim = IoTSimulator(seed=seed)
    events = sim.simulate_fleet(default_fleet_configs(), steps=steps, interval_minutes=15)

    ndjson_file = out_path / "telemetry_batch.ndjson"
    write_ndjson_stream(events, str(ndjson_file))

    manifest = {
        "telemetry_file": str(ndjson_file),
        "telemetry_event_count": len(events),
        "pricing_row_count": len(pricing_rows),
        "storage_profile_count": len(storage_profiles),
        "target_database": "ATMOSYNC_DWH",
        "target_schema": "RAW",
    }
    manifest_file = out_path / "ingest_manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    manifest["manifest_file"] = str(manifest_file)
    return manifest
