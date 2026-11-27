"""
Unit tests for Day 1 temperature & humidity distribution, scatter trend,
container summary matrix, and Markdown report generation (`src/climate_report.py`).
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from climate_report import (
    build_temp_humidity_scatter_summary,
    compute_histogram_bins,
    generate_container_climate_matrix,
    generate_day1_climate_report,
    render_markdown_climate_report,
)
from climate_telemetry import parse_telemetry_records


class TestClimateReport(unittest.TestCase):
    def test_compute_histogram_bins_counts_and_percentages(self):
        bins = compute_histogram_bins([2.0, 4.0, 6.0, 8.0, 10.0, 12.0], bins=3)
        self.assertEqual(len(bins), 3)
        self.assertEqual(sum(b["count"] for b in bins), 6)
        self.assertAlmostEqual(sum(b["pct"] for b in bins), 100.0, places=1)

        flat_bins = compute_histogram_bins([5.0, 5.0, 5.0], bins=4)
        self.assertEqual(len(flat_bins), 1)
        self.assertEqual(flat_bins[0]["count"], 3)

    def test_scatter_summary_and_container_matrix(self):
        raw = [
            {"container_id": "C1", "timestamp": "2026-11-27T08:00:00", "temperature_c": 5.0, "humidity_pct": 92.0, "commodity": "Avocado"},
            {"container_id": "C1", "timestamp": "2026-11-27T08:15:00", "temperature_c": 6.0, "humidity_pct": 90.0, "commodity": "Avocado"},
            {"container_id": "C1", "timestamp": "2026-11-27T08:30:00", "temperature_c": 10.0, "humidity_pct": 82.0, "commodity": "Avocado"},
        ]
        valid, _ = parse_telemetry_records(raw)
        scatter = build_temp_humidity_scatter_summary(valid)
        self.assertEqual(scatter["point_count"], 3)
        self.assertLess(scatter["linear_trend"]["slope_hum_per_c"], 0.0)
        self.assertFalse(scatter["points"][-1]["in_safe_band"])

        matrix = generate_container_climate_matrix(valid, bins=3)
        self.assertEqual(len(matrix["container_rows"]), 1)
        self.assertEqual(matrix["container_rows"][0]["status"], "CRITICAL")

        md = render_markdown_climate_report(matrix)
        self.assertIn("Temperature & Humidity Analysis Report", md)
        self.assertIn("| C1 | Avocado |", md)

    def test_generate_day1_climate_report_writes_markdown_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "climate_report.md"
            md = generate_day1_climate_report(output_path=str(out_file), steps=8, seed=2026)
            self.assertTrue(out_file.exists())
            self.assertIn("CNT-AVO-01", md)
            self.assertIn("CNT-BAN-02", md)

    def test_validation_errors(self):
        with self.assertRaises(ValueError):
            compute_histogram_bins([])
        with self.assertRaises(ValueError):
            compute_histogram_bins([1.0], bins=0)
        with self.assertRaises(ValueError):
            build_temp_humidity_scatter_summary([])
        with self.assertRaises(ValueError):
            generate_container_climate_matrix([])


if __name__ == "__main__":
    unittest.main()
