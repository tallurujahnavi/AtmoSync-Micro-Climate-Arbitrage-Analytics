"""
test_sensor_calibration.py – Unit tests for IoT sensor drift and noise calibration module.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import unittest
import pandas as pd
from iot_simulator import generate_fleet_telemetry
from sensor_calibration import (
    filter_vibration_noise,
    detect_sensor_drift,
    calibrate_container_packet,
    calibrate_fleet_telemetry,
    CalibratedReading,
    VIBRATION_NOISE_THRESHOLD_G,
    MAX_ACCEPTABLE_SENSOR_DRIFT_C,
)


class TestSensorCalibration(unittest.TestCase):

    def test_filter_vibration_noise_low(self):
        # Low vibration should pass through untouched
        cleaned_t, damped = filter_vibration_noise(6.0, 0.45)
        self.assertEqual(cleaned_t, 6.0)
        self.assertFalse(damped)

    def test_filter_vibration_noise_high(self):
        # High vibration (> 1.2g) should be suppressed
        cleaned_t, damped = filter_vibration_noise(10.0, 1.80)
        self.assertTrue(damped)
        self.assertLess(cleaned_t, 10.0)

    def test_detect_sensor_drift_within_bounds(self):
        delta, is_drift = detect_sensor_drift(6.5, 5.0)
        self.assertEqual(delta, 1.5)
        self.assertFalse(is_drift)

    def test_detect_sensor_drift_exceeded(self):
        delta, is_drift = detect_sensor_drift(12.0, 5.0)
        self.assertEqual(delta, 7.0)
        self.assertTrue(is_drift)

    def test_calibrate_container_packet_optimal(self):
        row = pd.Series({
            "container_id": "CONT-OPT-001",
            "commodity": "Hass Avocados",
            "internal_temp_celsius": 5.0,
            "vibration_g": 0.35,
            "target_setpoint_c": 5.0,
        })
        res = calibrate_container_packet(row)
        self.assertIsInstance(res, CalibratedReading)
        self.assertEqual(res.sensor_health, "OPTIMAL")
        self.assertEqual(res.confidence_score, 1.0)
        self.assertFalse(res.drift_detected)
        self.assertFalse(res.vibration_damped)

    def test_calibrate_container_packet_drift(self):
        row = pd.Series({
            "container_id": "CONT-DRIFT-002",
            "commodity": "Vaccines",
            "internal_temp_celsius": 11.0,
            "vibration_g": 0.40,
            "target_setpoint_c": 5.0,
        })
        res = calibrate_container_packet(row)
        self.assertTrue(res.drift_detected)
        self.assertIn(res.sensor_health, ["DRIFT_COMPENSATED", "HARDWARE_FAULT"])
        self.assertLess(res.confidence_score, 1.0)

    def test_calibrate_fleet_telemetry(self):
        fleet = generate_fleet_telemetry(num_containers=8)
        merged_df, audit = calibrate_fleet_telemetry(fleet)
        
        self.assertEqual(len(merged_df), len(fleet))
        self.assertIn("calibrated_temp_celsius", merged_df.columns)
        self.assertIn("sensor_health", merged_df.columns)
        self.assertIn("telemetry_confidence", merged_df.columns)
        
        self.assertIsInstance(audit, dict)
        self.assertEqual(audit["total_packets"], len(fleet))
        self.assertGreaterEqual(audit["mean_confidence_score"], 0.0)
        self.assertLessEqual(audit["mean_confidence_score"], 1.0)

    def test_calibrate_empty_fleet(self):
        empty_df = pd.DataFrame()
        res_df, audit = calibrate_fleet_telemetry(empty_df)
        self.assertTrue(res_df.empty)
        self.assertEqual(audit["total_packets"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
