"""
test_esg_sustainability.py – Unit tests for ESG carbon & food waste avoidance module.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import unittest
import pandas as pd
from iot_simulator import generate_fleet_telemetry
from spoilage_arbitrage import compute_fleet_arbitrage_summary
from esg_sustainability import (
    compute_container_esg,
    compute_fleet_esg_summary,
    generate_esg_executive_report,
    ContainerESGMetrics,
    FleetESGSummary,
)


class TestESGSustainability(unittest.TestCase):

    def setUp(self):
        telemetry = generate_fleet_telemetry(num_containers=6)
        self.fleet_df = compute_fleet_arbitrage_summary(telemetry)

    def test_compute_container_esg_rerouted(self):
        mock_rerouted = pd.Series({
            "container_id": "CONT-TEST-001",
            "commodity": "Hass Avocados",
            "cargo_tonnage": 18.0,
            "dist_to_secondary_km": 150.0,
            "action_decision": "URGENT_REROUTE_RECOMMENDED",
            "alert_level": "CRITICAL_SPOILAGE_RISK",
        })
        res = compute_container_esg(mock_rerouted)
        self.assertIsInstance(res, ContainerESGMetrics)
        self.assertEqual(res.food_saved_kg, 18000.0)
        self.assertGreater(res.avoided_methane_co2e_kg, 0.0)
        self.assertGreater(res.haulage_emissions_co2e_kg, 0.0)
        self.assertGreater(res.net_carbon_saved_co2e_kg, 0.0)
        self.assertGreater(res.carbon_credit_value_usd, 0.0)
        self.assertIn(res.esg_compliance_rating, ["AAA", "AA", "A"])

    def test_compute_container_esg_healthy(self):
        mock_healthy = pd.Series({
            "container_id": "CONT-TEST-002",
            "commodity": "Vaccines",
            "cargo_tonnage": 5.0,
            "dist_to_secondary_km": 80.0,
            "action_decision": "MAINTAIN_ORIGINAL_ROUTE",
            "alert_level": "HEALTHY",
        })
        res = compute_container_esg(mock_healthy)
        self.assertEqual(res.food_saved_kg, 0.0)
        self.assertEqual(res.avoided_methane_co2e_kg, 0.0)
        self.assertEqual(res.net_carbon_saved_co2e_kg, 0.0)
        self.assertEqual(res.esg_compliance_rating, "AA")

    def test_compute_fleet_esg_summary(self):
        summary = compute_fleet_esg_summary(self.fleet_df)
        self.assertIsInstance(summary, FleetESGSummary)
        self.assertEqual(summary.total_containers_tracked, len(self.fleet_df))
        self.assertGreaterEqual(summary.fleet_esg_score, 0.0)
        self.assertLessEqual(summary.fleet_esg_score, 100.0)
        self.assertTrue(any(t in summary.esg_tier for t in ["LEADER", "ADVANCED", "STANDARD", "DEVELOPING"]))
        self.assertEqual(len(summary.details), len(self.fleet_df))

    def test_empty_fleet_esg_summary(self):
        empty_df = pd.DataFrame()
        summary = compute_fleet_esg_summary(empty_df)
        self.assertEqual(summary.total_containers_tracked, 0)
        self.assertEqual(summary.total_food_saved_tonnes, 0.0)
        self.assertEqual(summary.fleet_esg_score, 100.0)

    def test_generate_esg_executive_report(self):
        summary = compute_fleet_esg_summary(self.fleet_df)
        report_md = generate_esg_executive_report(summary)
        self.assertIn("# 🌿 AtmoSync Cold-Chain ESG & Carbon Abatement Audit", report_md)
        self.assertIn("Food Waste Diverted", report_md)
        self.assertIn("Carbon Credit", report_md)


if __name__ == "__main__":
    unittest.main(verbosity=2)
