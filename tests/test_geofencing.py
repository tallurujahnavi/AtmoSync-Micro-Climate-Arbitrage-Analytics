"""
test_geofencing.py – Unit tests for cold-chain route corridor geofencing.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import unittest
import pandas as pd
from iot_simulator import generate_fleet_telemetry
from geofencing import (
    compute_cross_track_distance,
    evaluate_container_geofence,
    audit_fleet_geofencing,
    FREIGHT_CORRIDORS,
    GeofenceStatus,
)


class TestGeofencing(unittest.TestCase):

    def test_compute_cross_track_exact_match(self):
        # Point directly on corridor (Nagpur)
        dist = compute_cross_track_distance(21.1458, 79.0882, FREIGHT_CORRIDORS["NH44_NORTH_SOUTH"])
        self.assertAlmostEqual(dist, 0.0, places=1)

    def test_evaluate_container_geofence_in_corridor(self):
        res = evaluate_container_geofence("CONT-001", 21.1458, 79.0882, "NH44_NORTH_SOUTH")
        self.assertIsInstance(res, GeofenceStatus)
        self.assertEqual(res.status, "IN_CORRIDOR")
        self.assertTrue(res.is_compliant)

    def test_evaluate_container_geofence_breach(self):
        # Point far out in eastern India (Kolkata) against NH-44 corridor
        res = evaluate_container_geofence("CONT-BREACH-002", 22.5726, 88.3639, "NH44_NORTH_SOUTH")
        self.assertEqual(res.status, "UNAUTHORIZED_DETOUR_BREACH")
        self.assertFalse(res.is_compliant)
        self.assertGreater(res.cross_track_deviation_km, 100.0)

    def test_audit_fleet_geofencing(self):
        fleet = generate_fleet_telemetry(num_containers=6)
        results, summary = audit_fleet_geofencing(fleet)
        self.assertEqual(len(results), len(fleet))
        self.assertEqual(summary["total_monitored"], len(fleet))
        self.assertGreaterEqual(summary["compliance_rate_pct"], 0.0)
        self.assertLessEqual(summary["compliance_rate_pct"], 100.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
