"""
Unit tests for Day 3 Snowflake seed loader, storage profile CSV, and staging SQL.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from climate_telemetry import COMMODITY_STORAGE_PROFILES
from warehouse_loader import (
    export_snowflake_staging_bundle,
    load_commodity_pricing,
    load_storage_profiles,
)


class TestWarehouseLoader(unittest.TestCase):
    def test_storage_profiles_csv_matches_python_constants(self):
        profiles = load_storage_profiles()
        self.assertEqual(profiles, COMMODITY_STORAGE_PROFILES)

    def test_load_commodity_pricing_returns_typed_records(self):
        rows = load_commodity_pricing()
        self.assertGreaterEqual(len(rows), 15)
        first = rows[0]
        self.assertIsInstance(first["spot_price_usd_per_mt"], float)
        self.assertIsInstance(first["q10_factor"], float)
        self.assertIn(first["market_tier"], {"PRIMARY", "SECONDARY"})

    def test_snowflake_seed_load_sql_references_stages_and_raw_tables(self):
        sql = (ROOT_DIR / "sql" / "snowflake_seed_load.sql").read_text(encoding="utf-8")
        for token in (
            "USE ROLE ATMOSYNC_INGEST_ROLE",
            "RAW.CSV_SEED_FMT",
            "RAW.ATMOSYNC_TELEMETRY_STAGE",
            "RAW.ATMOSYNC_SEED_STAGE",
            "COPY INTO RAW.COMMODITY_PRICING_RAW",
            "COPY INTO RAW.COMMODITY_STORAGE_PROFILES_RAW",
            "COPY INTO RAW.CONTAINER_TELEMETRY_RAW",
        ):
            self.assertIn(token, sql)
        self.assertEqual(sql.count("("), sql.count(")"))

    def test_export_snowflake_staging_bundle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = export_snowflake_staging_bundle(tmpdir, steps=6, seed=7)
            self.assertEqual(manifest["telemetry_event_count"], 24)
            self.assertEqual(manifest["storage_profile_count"], len(COMMODITY_STORAGE_PROFILES))
            self.assertTrue(Path(manifest["telemetry_file"]).exists())
            saved = json.loads(Path(manifest["manifest_file"]).read_text(encoding="utf-8"))
            self.assertEqual(saved["target_database"], "ATMOSYNC_DWH")


if __name__ == "__main__":
    unittest.main()
