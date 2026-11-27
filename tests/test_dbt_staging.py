"""
Unit tests for Day 4 dbt Core staging configuration, SQL models, and source alignment.
"""

import re
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DBT_DIR = ROOT_DIR / "dbt"
STAGING_DIR = DBT_DIR / "models" / "staging"


class TestDbtStagingModels(unittest.TestCase):
    def test_dbt_project_and_yaml_configs_exist(self):
        project_yml = DBT_DIR / "dbt_project.yml"
        sources_yml = STAGING_DIR / "sources.yml"
        schema_yml = STAGING_DIR / "schema.yml"

        for path in (project_yml, sources_yml, schema_yml):
            self.assertTrue(path.exists(), f"Missing required dbt file: {path}")

        proj_text = project_yml.read_text(encoding="utf-8")
        self.assertIn("name: 'atmosync_analytics'", proj_text)
        self.assertIn("staging:", proj_text)
        self.assertIn("marts:", proj_text)

        sources_text = sources_yml.read_text(encoding="utf-8")
        for tbl in (
            "container_telemetry_raw",
            "commodity_pricing_raw",
            "commodity_storage_profiles_raw",
        ):
            self.assertIn(tbl, sources_text)

    def test_staging_sql_models_syntax_and_lineage(self):
        expected_models = {
            "stg_container_telemetry.sql": ("{{ source('atmosync_raw', 'container_telemetry_raw') }}",),
            "stg_commodity_pricing.sql": ("{{ source('atmosync_raw', 'commodity_pricing_raw') }}",),
            "stg_telemetry_enriched.sql": (
                "{{ ref('stg_container_telemetry') }}",
                "{{ ref('stg_commodity_pricing') }}",
                "{{ source('atmosync_raw', 'commodity_storage_profiles_raw') }}",
            ),
        }

        for filename, required_refs in expected_models.items():
            sql_path = STAGING_DIR / filename
            self.assertTrue(sql_path.exists(), f"Missing SQL model: {sql_path}")
            sql = sql_path.read_text(encoding="utf-8")
            self.assertEqual(sql.count("("), sql.count(")"), f"Unbalanced parens in {filename}")
            self.assertIn("SELECT", sql.upper())
            for ref in required_refs:
                self.assertIn(ref, sql, f"{filename} missing dependency {ref}")

    def test_schema_yml_covers_all_staging_models_and_statuses(self):
        schema_text = (STAGING_DIR / "schema.yml").read_text(encoding="utf-8")
        for model_name in ("stg_container_telemetry", "stg_commodity_pricing", "stg_telemetry_enriched"):
            self.assertIn(f"name: {model_name}", schema_text)
        for status in ("OK", "DEGRADED", "FAULT"):
            self.assertIn(status, schema_text)

    def test_stg_container_telemetry_aligns_with_snowflake_ddl(self):
        ddl_text = (ROOT_DIR / "sql" / "snowflake_schema.sql").read_text(encoding="utf-8")
        stg_sql = (STAGING_DIR / "stg_container_telemetry.sql").read_text(encoding="utf-8")
        ddl_fields = set(re.findall(r"raw_payload:([a-zA-Z0-9_]+)", ddl_text))
        stg_fields = set(re.findall(r"raw_payload:([a-zA-Z0-9_]+)", stg_sql))
        self.assertTrue(ddl_fields.issubset(stg_fields))


if __name__ == "__main__":
    unittest.main()
