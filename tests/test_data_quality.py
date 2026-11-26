"""
test_data_quality.py – Unit tests for data contract validation and schema drift detection.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import unittest
import pandas as pd
from iot_simulator import generate_fleet_telemetry
from data_quality import (
    validate_telemetry_packet,
    audit_dataset_quality,
    PacketValidationResult,
    FleetQualityScorecard,
)


class TestDataQuality(unittest.TestCase):

    def test_validate_clean_packet(self):
        clean_payload = {
            "container_id": "CONT-TEST-001",
            "commodity": "Hass Avocados",
            "internal_temp_celsius": 6.5,
            "internal_humidity_percent": 85.0,
            "vibration_g": 0.45,
            "cargo_tonnage": 18.0,
            "cargo_value_usd": 45000.0,
        }
        res = validate_telemetry_packet(clean_payload)
        self.assertIsInstance(res, PacketValidationResult)
        self.assertTrue(res.is_valid)
        self.assertEqual(len(res.violations), 0)
        self.assertFalse(res.quarantine_to_dlq)

    def test_validate_corrupt_packet_temperature(self):
        corrupt_payload = {
            "container_id": "CONT-CORRUPT-002",
            "commodity": "Hass Avocados",
            "internal_temp_celsius": 999.0,  # Physically impossible reefer temp
            "internal_humidity_percent": 85.0,
            "vibration_g": 0.45,
            "cargo_tonnage": 18.0,
            "cargo_value_usd": 45000.0,
        }
        res = validate_telemetry_packet(corrupt_payload)
        self.assertFalse(res.is_valid)
        self.assertTrue(res.quarantine_to_dlq)
        self.assertTrue(any("TEMPERATURE_OUT_OF_BOUNDS" in v for v in res.violations))

    def test_validate_corrupt_packet_negative_cargo(self):
        corrupt_payload = {
            "container_id": "CONT-CORRUPT-003",
            "commodity": "Vaccines",
            "internal_temp_celsius": 4.0,
            "internal_humidity_percent": 50.0,
            "vibration_g": 0.20,
            "cargo_tonnage": -5.0,  # Negative tonnage
            "cargo_value_usd": -100.0,
        }
        res = validate_telemetry_packet(corrupt_payload)
        self.assertFalse(res.is_valid)
        self.assertTrue(res.quarantine_to_dlq)

    def test_audit_dataset_quality_on_simulator(self):
        fleet = generate_fleet_telemetry(num_containers=10)
        scorecard = audit_dataset_quality(fleet)
        self.assertIsInstance(scorecard, FleetQualityScorecard)
        self.assertEqual(scorecard.total_records_checked, 10)
        self.assertEqual(scorecard.data_quality_score_pct, 100.0)
        self.assertEqual(scorecard.quarantined_records_count, 0)

    def test_empty_dataset_quality(self):
        empty_df = pd.DataFrame()
        scorecard = audit_dataset_quality(empty_df)
        self.assertEqual(scorecard.total_records_checked, 0)
        self.assertEqual(scorecard.data_quality_score_pct, 100.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
