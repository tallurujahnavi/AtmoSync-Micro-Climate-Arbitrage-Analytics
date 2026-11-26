"""
AtmoSync: Micro-Climate Arbitrage Analytics
Module: climate_telemetry.py
Description: Week 2 temperature and humidity telemetry analysis for refrigerated
             shipping containers, including fluctuation profiling, z-score
             anomaly detection, correlation analysis, and commodity safe-band
             excursion reporting.
"""

from dataclasses import dataclass
from datetime import datetime
import csv
import json
import math
from pathlib import Path
import statistics
from typing import Any, Dict, Iterable, List, Optional, Tuple


# Ideal cold-chain storage profiles for high-value perishable commodities
# Tuple fields: temp_min_c, temp_max_c, hum_min_pct, hum_max_pct, max_vibration_g
COMMODITY_STORAGE_PROFILES: Dict[str, Dict[str, float]] = {
    "Avocado": {
        "temp_min_c": 4.5,
        "temp_max_c": 7.5,
        "hum_min_pct": 85.0,
        "hum_max_pct": 95.0,
        "max_vibration_g": 0.6,
    },
    "Banana": {
        "temp_min_c": 13.0,
        "temp_max_c": 14.5,
        "hum_min_pct": 90.0,
        "hum_max_pct": 95.0,
        "max_vibration_g": 0.5,
    },
    "Mango": {
        "temp_min_c": 10.0,
        "temp_max_c": 13.0,
        "hum_min_pct": 85.0,
        "hum_max_pct": 90.0,
        "max_vibration_g": 0.6,
    },
    "Strawberry": {
        "temp_min_c": 0.0,
        "temp_max_c": 2.0,
        "hum_min_pct": 90.0,
        "hum_max_pct": 95.0,
        "max_vibration_g": 0.4,
    },
    "Tomato": {
        "temp_min_c": 10.0,
        "temp_max_c": 13.5,
        "hum_min_pct": 85.0,
        "hum_max_pct": 92.0,
        "max_vibration_g": 0.5,
    },
}


@dataclass(frozen=True)
class TelemetryRecord:
    """Validated micro-climate sensor observation for a shipping container."""

    container_id: str
    timestamp: str
    temperature_c: float
    humidity_pct: float
    vibration_g: float = 0.0
    commodity: Optional[str] = None


def _to_float(value: Any) -> Optional[float]:
    """Converts raw sensor values to finite float, returning None if invalid."""
    if value is None or value == "":
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    return num if math.isfinite(num) else None


def parse_telemetry_records(
    raw_records: Iterable[Dict[str, Any]],
) -> Tuple[List[TelemetryRecord], List[Dict[str, Any]]]:
    """
    Validates and normalizes raw IoT JSON/CSV telemetry payloads.

    Supports both container-native field names (`temperature_c`, `humidity_pct`)
    and weather-repository field names (`temperature_celsius`, `humidity`).

    Returns:
        (valid_records, rejected_records)
    """
    valid: List[TelemetryRecord] = []
    rejected: List[Dict[str, Any]] = []

    for idx, row in enumerate(raw_records):
        container_id = str(
            row.get("container_id") or row.get("location_name") or ""
        ).strip()
        timestamp = str(
            row.get("timestamp") or row.get("last_updated") or ""
        ).strip()
        temp = _to_float(
            row.get("temperature_c")
            if "temperature_c" in row
            else row.get("temperature_celsius")
        )
        hum = _to_float(
            row.get("humidity_pct")
            if "humidity_pct" in row
            else row.get("humidity")
        )
        vib = _to_float(row.get("vibration_g", 0.0))
        commodity = row.get("commodity")

        reason = None
        if not container_id:
            reason = "missing_container_id"
        elif not timestamp:
            reason = "missing_timestamp"
        elif temp is None or not (-40.0 <= temp <= 60.0):
            reason = "invalid_temperature_c"
        elif hum is None or not (0.0 <= hum <= 100.0):
            reason = "invalid_humidity_pct"
        elif vib is None or vib < 0.0:
            reason = "invalid_vibration_g"

        if reason:
            rejected.append({"index": idx, "reason": reason, "raw": row})
            continue

        valid.append(
            TelemetryRecord(
                container_id=container_id,
                timestamp=timestamp,
                temperature_c=round(temp, 3),
                humidity_pct=round(hum, 3),
                vibration_g=round(vib, 3),
                commodity=str(commodity).strip() if commodity else None,
            )
        )

    valid.sort(key=lambda r: _sort_key_timestamp(r.timestamp))
    return valid, rejected


def _sort_key_timestamp(ts: str) -> Tuple[int, str]:
    """Parses ISO or standard datetime strings for chronological ordering."""
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return (0, datetime.strptime(ts[:19], fmt).isoformat())
        except ValueError:
            continue
    return (1, ts)


def _compute_series_stats(values: List[float]) -> Dict[str, float]:
    """Computes descriptive statistics and step-to-step fluctuation metrics."""
    mean_val = statistics.fmean(values)
    min_val = min(values)
    max_val = max(values)
    std_val = statistics.stdev(values) if len(values) > 1 else 0.0

    deltas = [abs(values[i] - values[i - 1]) for i in range(1, len(values))]
    avg_delta = statistics.fmean(deltas) if deltas else 0.0
    max_spike = max(deltas) if deltas else 0.0

    return {
        "avg": round(mean_val, 3),
        "min": round(min_val, 3),
        "max": round(max_val, 3),
        "range": round(max_val - min_val, 3),
        "std": round(std_val, 3),
        "avg_step_delta": round(avg_delta, 3),
        "max_step_spike": round(max_spike, 3),
    }


def _pearson_correlation(xs: List[float], ys: List[float]) -> Optional[float]:
    """Computes Pearson correlation coefficient between two equal-length series."""
    if len(xs) < 2 or len(xs) != len(ys):
        return None
    mx = statistics.fmean(xs)
    my = statistics.fmean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den_x = sum((x - mx) ** 2 for x in xs)
    den_y = sum((y - my) ** 2 for y in ys)
    denom = math.sqrt(den_x * den_y)
    if denom == 0.0:
        return 0.0
    return round(num / denom, 4)


def _zscore_anomaly_indices(values: List[float], threshold: float = 2.0) -> List[int]:
    """Returns indices whose absolute z-score meets or exceeds `threshold`."""
    if len(values) < 3:
        return []
    mean_val = statistics.fmean(values)
    std_val = statistics.stdev(values)
    if std_val == 0.0:
        return []
    return [
        idx
        for idx, val in enumerate(values)
        if abs((val - mean_val) / std_val) >= threshold
    ]


def analyze_temperature_humidity(
    records: List[TelemetryRecord],
    commodity: Optional[str] = None,
    z_threshold: float = 2.0,
) -> Dict[str, Any]:
    """
    Performs Week 2 temperature and humidity statistical & excursion analysis.

    Args:
        records: Non-empty list of validated TelemetryRecord items.
        commodity: Optional commodity name from COMMODITY_STORAGE_PROFILES.
        z_threshold: Z-score cutoff for flagging unusual sensor spikes.

    Returns:
        Structured dictionary with temperature stats, humidity stats,
        Pearson correlation, anomaly timestamps, and safe-band status.
    """
    if not records:
        raise ValueError("Cannot analyze an empty telemetry record list.")
    if commodity is not None and commodity not in COMMODITY_STORAGE_PROFILES:
        raise ValueError(
            f"Unknown commodity '{commodity}'. Supported: {list(COMMODITY_STORAGE_PROFILES.keys())}"
        )

    ordered = sorted(records, key=lambda r: _sort_key_timestamp(r.timestamp))
    temps = [r.temperature_c for r in ordered]
    hums = [r.humidity_pct for r in ordered]

    temp_stats = _compute_series_stats(temps)
    hum_stats = _compute_series_stats(hums)

    temp_anom_idx = _zscore_anomaly_indices(temps, threshold=z_threshold)
    hum_anom_idx = _zscore_anomaly_indices(hums, threshold=z_threshold)

    result: Dict[str, Any] = {
        "record_count": len(ordered),
        "start_timestamp": ordered[0].timestamp,
        "end_timestamp": ordered[-1].timestamp,
        "temperature_c": temp_stats,
        "humidity_pct": hum_stats,
        "temp_humidity_correlation": _pearson_correlation(temps, hums),
        "anomalies": {
            "z_threshold": z_threshold,
            "temperature_anomaly_count": len(temp_anom_idx),
            "humidity_anomaly_count": len(hum_anom_idx),
            "temperature_anomaly_timestamps": [ordered[i].timestamp for i in temp_anom_idx],
            "humidity_anomaly_timestamps": [ordered[i].timestamp for i in hum_anom_idx],
        },
    }

    if commodity is not None:
        profile = COMMODITY_STORAGE_PROFILES[commodity]
        temp_excursions = sum(
            1
            for t in temps
            if t < profile["temp_min_c"] or t > profile["temp_max_c"]
        )
        hum_excursions = sum(
            1
            for h in hums
            if h < profile["hum_min_pct"] or h > profile["hum_max_pct"]
        )
        any_excursion = sum(
            1
            for r in ordered
            if (
                r.temperature_c < profile["temp_min_c"]
                or r.temperature_c > profile["temp_max_c"]
                or r.humidity_pct < profile["hum_min_pct"]
                or r.humidity_pct > profile["hum_max_pct"]
            )
        )
        out_of_band_pct = round((any_excursion / len(ordered)) * 100.0, 2)

        if out_of_band_pct >= 25.0:
            status = "CRITICAL"
        elif any_excursion > 0:
            status = "WARNING"
        else:
            status = "NORMAL"

        result["commodity_compliance"] = {
            "commodity": commodity,
            "safe_band": profile,
            "temperature_excursions": temp_excursions,
            "humidity_excursions": hum_excursions,
            "out_of_band_records": any_excursion,
            "out_of_band_pct": out_of_band_pct,
            "status": status,
        }

    return result


def summarize_by_container(
    records: List[TelemetryRecord],
    commodity_map: Optional[Dict[str, str]] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Groups telemetry records by `container_id` and runs temperature/humidity
    analysis for each container independently.
    """
    grouped: Dict[str, List[TelemetryRecord]] = {}
    for rec in records:
        grouped.setdefault(rec.container_id, []).append(rec)

    summaries: Dict[str, Dict[str, Any]] = {}
    for container_id, group in sorted(grouped.items()):
        inferred_commodity = None
        if commodity_map and container_id in commodity_map:
            inferred_commodity = commodity_map[container_id]
        else:
            inferred_commodity = next((r.commodity for r in group if r.commodity), None)

        if inferred_commodity not in COMMODITY_STORAGE_PROFILES:
            inferred_commodity = None

        summaries[container_id] = analyze_temperature_humidity(
            group, commodity=inferred_commodity
        )

    return summaries


def load_csv_telemetry(csv_path: str) -> Tuple[List[TelemetryRecord], List[Dict[str, Any]]]:
    """Loads and validates telemetry records from a CSV file."""
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Telemetry CSV not found: {csv_path}")

    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        return parse_telemetry_records(reader)


def export_telemetry_report(summary: Dict[str, Any], output_path: str) -> str:
    """Writes a temperature/humidity analysis report to JSON and returns its path."""
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    return str(target)
