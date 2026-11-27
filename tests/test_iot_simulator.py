"""
Unit tests for src/iot_simulator.py
Validates deterministic container telemetry streaming, fault injection modes,
GPS route interpolation, NDJSON/CSV export, and compatibility with
src/climate_telemetry.py.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from climate_telemetry import load_csv_telemetry, parse_telemetry_records, summarize_by_container
from iot_simulator import (
    ContainerConfig,
    IoTSimulator,
    default_fleet_configs,
    write_csv_telemetry,
    write_ndjson_stream,
)


class TestIoTSimulator(unittest.TestCase):
    def test_deterministic_stream_and_gps_interpolation(self):
        cfg = ContainerConfig(
            container_id="CNT-TEST-1",
            commodity="Avocado",
            route_name="Bengaluru-Chennai",
            fault_mode="none",
        )
        events_a = [e.to_dict() for e in IoTSimulator(seed=7).stream_container(cfg, steps=5)]
        events_b = [e.to_dict() for e in IoTSimulator(seed=7).stream_container(cfg, steps=5)]

        self.assertEqual(events_a, events_b)
        self.assertEqual(len(events_a), 5)
        self.assertEqual(events_a[0]["progress_pct"], 0.0)
        self.assertEqual(events_a[-1]["progress_pct"], 100.0)
        self.assertNotEqual(events_a[0]["latitude"], events_a[-1]["latitude"])
        self.assertTrue(all(e["compressor_status"] == "OK" for e in events_a))

    def test_compressor_drift_fault_triggers_critical_telemetry(self):
        cfg = ContainerConfig(
            container_id="CNT-DRIFT",
            commodity="Avocado",
            route_name="Nashik-JNPT",
            fault_mode="compressor_drift",
            fault_start_step=3,
            drift_rate_c_per_step=0.9,
        )
        events = [e.to_dict() for e in IoTSimulator(seed=11).stream_container(cfg, steps=12)]
        self.assertFalse(events[0]["fault_injected"])
        self.assertTrue(events[-1]["fault_injected"])
        self.assertEqual(events[-1]["compressor_status"], "FAULT")
        self.assertGreater(events[-1]["temperature_c"], events[0]["temperature_c"] + 4.0)

        valid, rejected = parse_telemetry_records(events)
        self.assertEqual(len(rejected), 0)
        summaries = summarize_by_container(valid)
        self.assertEqual(summaries["CNT-DRIFT"]["commodity_compliance"]["status"], "CRITICAL")

    def test_humidity_spike_and_vibration_shock_modes(self):
        hum_cfg = ContainerConfig(
            container_id="CNT-HUM",
            commodity="Mango",
            fault_mode="humidity_spike",
            fault_start_step=2,
        )
        vib_cfg = ContainerConfig(
            container_id="CNT-VIB",
            commodity="Strawberry",
            fault_mode="vibration_shock",
            fault_start_step=2,
        )
        sim = IoTSimulator(seed=21)
        hum_events = [e.to_dict() for e in sim.stream_container(hum_cfg, steps=8)]
        vib_events = [e.to_dict() for e in sim.stream_container(vib_cfg, steps=8)]

        self.assertEqual(hum_events[-1]["compressor_status"], "DEGRADED")
        self.assertGreater(hum_events[-1]["humidity_pct"], 94.0)
        self.assertGreater(vib_events[-1]["vibration_g"], 0.7)

    def test_fleet_simulation_ndjson_and_csv_roundtrip(self):
        sim = IoTSimulator(seed=99)
        events = sim.simulate_fleet(default_fleet_configs(), steps=10)
        self.assertEqual(len(events), 40)

        timestamps = [e["timestamp"] for e in events]
        self.assertEqual(timestamps, sorted(timestamps))

        with tempfile.TemporaryDirectory() as tmpdir:
            ndjson_path = Path(tmpdir) / "telemetry.ndjson"
            csv_path = Path(tmpdir) / "telemetry.csv"

            write_ndjson_stream(events, str(ndjson_path))
            write_csv_telemetry(events, str(csv_path))

            lines = ndjson_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 40)
            self.assertEqual(json.loads(lines[0])["container_id"], events[0]["container_id"])

            valid, rejected = load_csv_telemetry(str(csv_path))
            self.assertEqual(len(valid), 40)
            self.assertEqual(len(rejected), 0)

    def test_config_validation_errors(self):
        with self.assertRaises(ValueError):
            ContainerConfig(container_id="", commodity="Avocado")
        with self.assertRaises(ValueError):
            ContainerConfig(container_id="CNT-1", commodity="Papaya")
        with self.assertRaises(ValueError):
            ContainerConfig(container_id="CNT-1", commodity="Avocado", route_name="Unknown-Route")
        with self.assertRaises(ValueError):
            ContainerConfig(container_id="CNT-1", commodity="Avocado", fault_mode="bad_mode")


if __name__ == "__main__":
    unittest.main()
