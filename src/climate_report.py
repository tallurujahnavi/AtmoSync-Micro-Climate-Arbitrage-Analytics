"""
AtmoSync: Micro-Climate Arbitrage Analytics
Module: climate_report.py
Description: Day 1 companion analytics module for Temperature & Humidity
             distribution binning, scatter/trend profiling, container-level
             climate summary tables, and Markdown analytical report export.
"""

from pathlib import Path
import statistics
import sys
from typing import Any, Dict, List, Optional, Sequence

try:
    from src.climate_telemetry import (
        COMMODITY_STORAGE_PROFILES,
        TelemetryRecord,
        analyze_temperature_humidity,
        parse_telemetry_records,
        summarize_by_container,
    )
    from src.iot_simulator import IoTSimulator, default_fleet_configs
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from climate_telemetry import (
        COMMODITY_STORAGE_PROFILES,
        TelemetryRecord,
        analyze_temperature_humidity,
        parse_telemetry_records,
        summarize_by_container,
    )
    from iot_simulator import IoTSimulator, default_fleet_configs


def compute_histogram_bins(values: Sequence[float], bins: int = 6) -> List[Dict[str, Any]]:
    """
    Computes equal-width histogram bins and percentages for distribution charts.
    """
    if not values:
        raise ValueError("values must be non-empty.")
    if bins <= 0:
        raise ValueError("bins must be > 0.")

    lo = min(values)
    hi = max(values)
    if lo == hi:
        return [
            {
                "bin_start": round(lo, 3),
                "bin_end": round(hi, 3),
                "count": len(values),
                "pct": 100.0,
            }
        ]

    width = (hi - lo) / bins
    counts = [0] * bins
    for val in values:
        idx = min(bins - 1, int((val - lo) / width))
        counts[idx] += 1

    total = len(values)
    result: List[Dict[str, Any]] = []
    for i, count in enumerate(counts):
        start = lo + i * width
        end = lo + (i + 1) * width
        result.append(
            {
                "bin_start": round(start, 3),
                "bin_end": round(end, 3),
                "count": count,
                "pct": round((count / total) * 100.0, 2),
            }
        )
    return result


def build_temp_humidity_scatter_summary(
    records: Sequence[TelemetryRecord],
) -> Dict[str, Any]:
    """
    Prepares Temperature vs. Humidity scatter points with linear regression
    slope/intercept and excursion flags for visualization layers.
    """
    if not records:
        raise ValueError("records must be non-empty.")

    temps = [r.temperature_c for r in records]
    hums = [r.humidity_pct for r in records]

    mean_t = statistics.fmean(temps)
    mean_h = statistics.fmean(hums)
    denom = sum((t - mean_t) ** 2 for t in temps)
    if denom > 0.0:
        slope = sum((t - mean_t) * (h - mean_h) for t, h in zip(temps, hums)) / denom
        intercept = mean_h - slope * mean_t
    else:
        slope = 0.0
        intercept = mean_h

    points: List[Dict[str, Any]] = []
    for rec in records:
        in_band = True
        if rec.commodity and rec.commodity in COMMODITY_STORAGE_PROFILES:
            prof = COMMODITY_STORAGE_PROFILES[rec.commodity]
            in_band = (
                prof["temp_min_c"] <= rec.temperature_c <= prof["temp_max_c"]
                and prof["hum_min_pct"] <= rec.humidity_pct <= prof["hum_max_pct"]
            )
        points.append(
            {
                "container_id": rec.container_id,
                "timestamp": rec.timestamp,
                "commodity": rec.commodity,
                "temperature_c": rec.temperature_c,
                "humidity_pct": rec.humidity_pct,
                "in_safe_band": in_band,
            }
        )

    return {
        "point_count": len(points),
        "linear_trend": {
            "slope_hum_per_c": round(slope, 4),
            "intercept_pct": round(intercept, 3),
        },
        "points": points,
    }


def generate_container_climate_matrix(
    records: Sequence[TelemetryRecord],
    bins: int = 6,
) -> Dict[str, Any]:
    """
    Builds a consolidated Week 2 Temperature & Humidity matrix across all containers.
    """
    if not records:
        raise ValueError("records must be non-empty.")

    record_list = list(records)
    overall = analyze_temperature_humidity(record_list)
    per_container = summarize_by_container(record_list)

    rows: List[Dict[str, Any]] = []
    for cid, stats_dict in per_container.items():
        comp = stats_dict.get("commodity_compliance", {})
        rows.append(
            {
                "container_id": cid,
                "commodity": comp.get("commodity", "Unspecified"),
                "records": stats_dict["record_count"],
                "temp_avg_c": stats_dict["temperature_c"]["avg"],
                "temp_min_c": stats_dict["temperature_c"]["min"],
                "temp_max_c": stats_dict["temperature_c"]["max"],
                "temp_std_c": stats_dict["temperature_c"]["std"],
                "hum_avg_pct": stats_dict["humidity_pct"]["avg"],
                "hum_min_pct": stats_dict["humidity_pct"]["min"],
                "hum_max_pct": stats_dict["humidity_pct"]["max"],
                "temp_hum_corr": stats_dict["temp_humidity_correlation"],
                "out_of_band_pct": comp.get("out_of_band_pct", 0.0),
                "status": comp.get("status", "UNSPECIFIED"),
            }
        )

    return {
        "overall": overall,
        "temperature_distribution": compute_histogram_bins(
            [r.temperature_c for r in record_list], bins=bins
        ),
        "humidity_distribution": compute_histogram_bins(
            [r.humidity_pct for r in record_list], bins=bins
        ),
        "scatter_summary": build_temp_humidity_scatter_summary(record_list),
        "container_rows": rows,
    }


def render_markdown_climate_report(matrix: Dict[str, Any]) -> str:
    """Formats a human-readable Markdown analytical report from `generate_container_climate_matrix`."""
    overall = matrix["overall"]
    lines = [
        "# AtmoSync Week 2 — Temperature & Humidity Analysis Report",
        "",
        f"- **Records Analyzed:** {overall['record_count']}",
        f"- **Observation Window:** {overall['start_timestamp']} to {overall['end_timestamp']}",
        f"- **Mean Temperature:** {overall['temperature_c']['avg']} °C "
        f"(min {overall['temperature_c']['min']} °C, max {overall['temperature_c']['max']} °C)",
        f"- **Mean Humidity:** {overall['humidity_pct']['avg']} % "
        f"(min {overall['humidity_pct']['min']} %, max {overall['humidity_pct']['max']} %)",
        f"- **Temp vs. Humidity Correlation (r):** {overall['temp_humidity_correlation']}",
        f"- **Linear Trend Slope:** {matrix['scatter_summary']['linear_trend']['slope_hum_per_c']} %/°C",
        "",
        "## Container Climate Summary",
        "",
        "| Container | Commodity | Avg Temp (°C) | Avg Hum (%) | Corr (r) | Out-of-Band % | Status |",
        "| :--- | :--- | ---: | ---: | ---: | ---: | :--- |",
    ]
    for row in matrix["container_rows"]:
        lines.append(
            f"| {row['container_id']} | {row['commodity']} | {row['temp_avg_c']:.2f} | "
            f"{row['hum_avg_pct']:.2f} | {row['temp_hum_corr']} | "
            f"{row['out_of_band_pct']:.2f}% | {row['status']} |"
        )
    return "\n".join(lines) + "\n"


def generate_day1_climate_report(
    output_path: Optional[str] = None,
    steps: int = 16,
    seed: int = 2026,
) -> str:
    """Runs Day 1 climate report generation over a simulated 4-container fleet."""
    sim = IoTSimulator(seed=seed)
    raw = sim.simulate_fleet(default_fleet_configs(), steps=steps, interval_minutes=15)
    valid, _ = parse_telemetry_records(raw)
    matrix = generate_container_climate_matrix(valid)
    report_md = render_markdown_climate_report(matrix)

    if output_path:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(report_md, encoding="utf-8")
    return report_md


if __name__ == "__main__":
    print(generate_day1_climate_report())
