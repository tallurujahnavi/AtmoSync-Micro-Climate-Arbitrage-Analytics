"""
Unit tests for src/climate_telemetry.py
Validates Week 2 temperature & humidity analysis, anomaly detection,
correlation calculation, and commodity safe-band compliance checks.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from climate_telemetry import (
    COMMODITY_STORAGE_PROFILES,
    analyze_temperature_humidity,
    export_telemetry_report,
    parse_telemetry_records,
    summarize_by_container,
)


class TestClimateTelemetry(unittest.TestCase):
    def test_parse_telemetry_records_filters_invalid_rows(self):
        raw = [
            {
                "container_id": "CNT-101",
                "timestamp": "2026-11-26 10:00",
                "temperature_c": "5.2",
                "humidity_pct": "90.0",
                "vibration_g": "0.2",
                "commodity": "Avocado",
            },
            {
                "container_id": "CNT-101",
                "timestamp": "2026-11-26 10:05",
                "temperature_c": "999.0",  # Invalid physical temp
                "humidity_pct": "88.0",
            },
            {
                "container_id": "",
                "timestamp": "2026-11-26 10:10",
                "temperature_c": "6.0",
                "humidity_pct": "88.0",
            },
        ]

        valid, rejected = parse_telemetry_records(raw)
        self.assertEqual(len(valid), 1)
        self.assertEqual(len(rejected), 2)
        self.assertEqual(valid[0].container_id, "CNT-101")
        self.assertEqual(rejected[0]["reason"], "invalid_temperature_c")
        self.assertEqual(rejected[1]["reason"], "missing_container_id")

    def test_analyze_temperature_humidity_stats_and_correlation(self):
        raw = [
            {"container_id": "CNT-A", "timestamp": "2026-11-26 08:00", "temperature_c": 5.0, "humidity_pct": 92.0},
            {"container_id": "CNT-A", "timestamp": "2026-11-26 09:00", "temperature_c": 6.0, "humidity_pct": 90.0},
            {"container_id": "CNT-A", "timestamp": "2026-11-26 10:00", "temperature_c": 7.0, "humidity_pct": 88.0},
        ]
        valid, _ = parse_telemetry_records(raw)
        report = analyze_temperature_humidity(valid, commodity="Avocado")

        self.assertEqual(report["temperature_c"]["avg"], 6.0)
        self.assertEqual(report["temperature_c"]["min"], 5.0)
        self.assertEqual(report["temperature_c"]["max"], 7.0)
        self.assertEqual(report["temperature_c"]["avg_step_delta"], 1.0)
        self.assertEqual(report["humidity_pct"]["avg"], 90.0)
        self.assertEqual(report["temp_humidity_correlation"], -1.0)
        self.assertEqual(report["commodity_compliance"]["status"], "NORMAL")

    def test_zscore_anomaly_and_critical_excursion_detection(self):
        raw = [
            {"container_id": "CNT-B", "timestamp": f"2026-11-26 0{i}:00", "temperature_c": 5.5, "humidity_pct": 90.0}
            for i in range(1, 7)
        ]
        # Inject sudden compressor failure spikes
        raw.append({"container_id": "CNT-B", "timestamp": "2026-11-26 07:00", "temperature_c": 14.5, "humidity_pct": 62.0})
        raw.append({"container_id": "CNT-B", "timestamp": "2026-11-26 08:00", "temperature_c": 15.0, "humidity_pct": 60.0})

        valid, _ = parse_telemetry_records(raw)
        report = analyze_temperature_humidity(valid, commodity="Avocado", z_threshold=1.5)

        self.assertGreaterEqual(report["anomalies"]["temperature_anomaly_count"], 1)
        self.assertGreaterEqual(report["anomalies"]["humidity_anomaly_count"], 1)
        self.assertEqual(report["commodity_compliance"]["status"], "CRITICAL")
        self.assertEqual(report["commodity_compliance"]["out_of_band_records"], 2)

    def test_summarize_by_container_and_export(self):
        raw = [
            {"container_id": "CNT-1", "timestamp": "2026-11-26 08:00", "temperature_c": 1.0, "humidity_pct": 92.0, "commodity": "Strawberry"},
            {"container_id": "CNT-2", "timestamp": "2026-11-26 08:00", "temperature_c": 13.5, "humidity_pct": 91.0, "commodity": "Banana"},
            {"container_id": "CNT-2", "timestamp": "2026-11-26 09:00", "temperature_c": 16.5, "humidity_pct": 85.0, "commodity": "Banana"},
        ]
        valid, _ = parse_telemetry_records(raw)
        summaries = summarize_by_container(valid)

        self.assertIn("CNT-1", summaries)
        self.assertIn("CNT-2", summaries)
        self.assertEqual(summaries["CNT-1"]["commodity_compliance"]["status"], "NORMAL")
        self.assertEqual(summaries["CNT-2"]["commodity_compliance"]["status"], "CRITICAL")

        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "telemetry_summary.json"
            written = export_telemetry_report(summaries, str(out_file))
            loaded = json.loads(Path(written).read_text(encoding="utf-8"))
            self.assertEqual(loaded["CNT-1"]["commodity_compliance"]["commodity"], "Strawberry")

    def test_validation_errors(self):
        with self.assertRaises(ValueError):
            analyze_temperature_humidity([])
        valid, _ = parse_telemetry_records([
            {"container_id": "CNT-X", "timestamp": "2026-11-26 08:00", "temperature_c": 5.0, "humidity_pct": 90.0}
        ])
        with self.assertRaises(ValueError):
            analyze_temperature_humidity(valid, commodity="UnknownFruit")
        self.assertIn("Avocado", COMMODITY_STORAGE_PROFILES)


if __name__ == "__main__":
    unittest.main()
