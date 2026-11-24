"""
test_reports.py – Unit tests for the Compliance Audit & Reporting module.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import unittest
import pandas as pd
from iot_simulator import generate_fleet_telemetry
from spoilage_arbitrage import compute_fleet_arbitrage_summary
from reports import generate_fleet_csv, generate_audit_report


class TestReports(unittest.TestCase):

    def setUp(self):
        telemetry = generate_fleet_telemetry(num_containers=5)
        self.fleet_df = compute_fleet_arbitrage_summary(telemetry)

    def test_generate_fleet_csv_output(self):
        csv_str = generate_fleet_csv(self.fleet_df)
        self.assertIsInstance(csv_str, str)
        self.assertIn("container_id", csv_str)
        self.assertIn("commodity", csv_str)
        # Verify lines count matches fleet length + header
        lines = [line for line in csv_str.strip().split("\n") if line]
        self.assertEqual(len(lines), len(self.fleet_df) + 1)

    def test_generate_audit_report_structure(self):
        report = generate_audit_report(self.fleet_df, auditor_name="Test Auditor")
        self.assertIn("report_id", report)
        self.assertTrue(report["report_id"].startswith("RPT-"))
        self.assertEqual(report["total_containers"], len(self.fleet_df))
        self.assertGreaterEqual(report["compliance_rate_pct"], 0.0)
        self.assertLessEqual(report["compliance_rate_pct"], 100.0)
        self.assertIn("integrity_hash", report)
        self.assertEqual(len(report["integrity_hash"]), 64)  # SHA-256 length
        self.assertIn("markdown_content", report)
        self.assertIn("# 📋 AtmoSync Cold-Chain Telemetry & Compliance Audit", report["markdown_content"])
        self.assertIn("Test Auditor", report["markdown_content"])

    def test_audit_report_empty_fleet(self):
        empty_df = pd.DataFrame(columns=["action_decision", "cargo_value_usd", "spoilage_arbitrage_gain_usd"])
        report = generate_audit_report(empty_df)
        self.assertEqual(report["total_containers"], 0)
        self.assertEqual(report["at_risk_count"], 0)
        self.assertEqual(report["compliance_rate_pct"], 100.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
