"""
Unit tests for Day 3 deliverables:
- sql/snowflake_schema.sql structure, VARIANT staging extraction, and RBAC roles
- data/commodity_pricing.csv completeness and referential alignment with COMMODITY_STORAGE_PROFILES
"""

import csv
import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from climate_telemetry import COMMODITY_STORAGE_PROFILES


class TestSnowflakeSchemaAndPricing(unittest.TestCase):
    def test_snowflake_ddl_contains_required_layers_and_rbac(self):
        ddl_path = ROOT_DIR / "sql" / "snowflake_schema.sql"
        self.assertTrue(ddl_path.exists(), "sql/snowflake_schema.sql must exist")
        ddl = ddl_path.read_text(encoding="utf-8")

        for token in (
            "CREATE WAREHOUSE IF NOT EXISTS ATMOSYNC_WH",
            "CREATE DATABASE IF NOT EXISTS ATMOSYNC_DWH",
            "CREATE SCHEMA IF NOT EXISTS RAW",
            "CREATE SCHEMA IF NOT EXISTS STAGING",
            "CREATE SCHEMA IF NOT EXISTS MARTS",
            "RAW.CONTAINER_TELEMETRY_RAW",
            "raw_payload      VARIANT",
            "STAGING.STG_CONTAINER_TELEMETRY",
            "STAGING.STG_COMMODITY_PRICING",
            "MARTS.FCT_CONTAINER_CLIMATE_HEALTH",
            "MARTS.FCT_SPOILAGE_ARBITRAGE",
            "ATMOSYNC_INGEST_ROLE",
            "ATMOSYNC_TRANSFORM_ROLE",
            "ATMOSYNC_BI_READER",
        ):
            self.assertIn(token, ddl)

        # Ensure VARIANT extraction matches IoT simulator fields
        for field in ("event_id", "container_id", "temperature_c", "humidity_pct", "vibration_g", "compressor_status"):
            self.assertIn(f"raw_payload:{field}", ddl)

        # Basic balanced parentheses sanity check
        self.assertEqual(ddl.count("("), ddl.count(")"))

    def test_commodity_pricing_csv_covers_all_commodities_and_tiers(self):
        csv_path = ROOT_DIR / "data" / "commodity_pricing.csv"
        self.assertTrue(csv_path.exists(), "data/commodity_pricing.csv must exist")

        with csv_path.open("r", encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))

        self.assertGreaterEqual(len(rows), 10)
        tiers_by_commodity = {}
        for row in rows:
            commodity = row["commodity"].strip()
            tier = row["market_tier"].strip()
            self.assertIn(tier, {"PRIMARY", "SECONDARY"})
            self.assertGreater(float(row["spot_price_usd_per_mt"]), 0.0)
            self.assertGreater(float(row["base_shelf_life_hours"]), 0.0)
            self.assertGreater(float(row["q10_factor"]), 1.0)
            self.assertGreater(float(row["haulage_cost_usd_per_mt_km"]), 0.0)
            self.assertTrue(-90.0 <= float(row["latitude"]) <= 90.0)
            self.assertTrue(-180.0 <= float(row["longitude"]) <= 180.0)
            tiers_by_commodity.setdefault(commodity, set()).add(tier)

        for commodity in COMMODITY_STORAGE_PROFILES:
            self.assertIn(commodity, tiers_by_commodity)
            self.assertEqual(tiers_by_commodity[commodity], {"PRIMARY", "SECONDARY"})


if __name__ == "__main__":
    unittest.main()
