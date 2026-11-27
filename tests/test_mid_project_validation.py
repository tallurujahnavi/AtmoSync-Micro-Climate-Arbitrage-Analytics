"""
Unit tests for Day 4 Mid-Project Review validation and dbt singular SQL tests.
"""

import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "scripts"))

from validate_mid_project import run_mid_project_validation


class TestMidProjectValidation(unittest.TestCase):
    def test_dbt_singular_tests_exist_and_reference_staging_models(self):
        bounds_sql = (ROOT_DIR / "dbt" / "tests" / "assert_telemetry_bounds.sql").read_text(encoding="utf-8")
        pricing_sql = (ROOT_DIR / "dbt" / "tests" / "assert_pricing_positive.sql").read_text(encoding="utf-8")

        self.assertIn("{{ ref('stg_container_telemetry') }}", bounds_sql)
        self.assertIn("temperature_c", bounds_sql)
        self.assertIn("{{ ref('stg_commodity_pricing') }}", pricing_sql)
        self.assertIn("effective_price_usd_per_mt", pricing_sql)

    def test_mid_project_validation_passes_all_checks(self):
        result = run_mid_project_validation(steps=24, seed=2026)
        self.assertEqual(result["overall_status"], "PASSED")
        self.assertEqual(result["events_rejected"], 0)
        self.assertEqual(result["containers_validated"], 4)
        self.assertTrue(all(result["checks"].values()))


if __name__ == "__main__":
    unittest.main()
