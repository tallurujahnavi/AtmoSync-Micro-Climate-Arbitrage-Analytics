"""
data_quality.py – Automated data contracts, schema drift, and telemetry quality validator.

Enforces production DataOps & MDS quality constraints before landing in Snowflake:
1. Physical boundary assertions (temperature, humidity, vibration limits)
2. Schema contract drift detection (unannounced upstream Kafka schema mutations)
3. Anomaly isolation & Dead-Letter Queue (DLQ) routing
4. Automated fleet data quality scorecard (0-100%)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Any, Optional
import pandas as pd


# Mandatory schema contract for incoming IoT telemetry packets
EXPECTED_TELEMETRY_SCHEMA = {
    "container_id": str,
    "commodity": str,
    "internal_temp_celsius": (float, int),
    "internal_humidity_percent": (float, int),
    "vibration_g": (float, int),
    "cargo_tonnage": (float, int),
    "cargo_value_usd": (float, int),
}

# Physical boundary constraints
TEMP_MIN_CELSIUS = -40.0
TEMP_MAX_CELSIUS = 60.0
HUMIDITY_MIN_PCT = 0.0
HUMIDITY_MAX_PCT = 100.0
MAX_VIBRATION_G = 15.0


@dataclass
class PacketValidationResult:
    container_id: str
    is_valid: bool
    violations: List[str] = field(default_factory=list)
    quarantine_to_dlq: bool = False


@dataclass
class FleetQualityScorecard:
    total_records_checked: int
    clean_records_count: int
    quarantined_records_count: int
    data_quality_score_pct: float
    schema_drift_detected: bool
    drift_keys: List[str]
    violation_summary: Dict[str, int]


def validate_telemetry_packet(payload: Dict[str, Any]) -> PacketValidationResult:
    """
    Validates a single telemetry payload against data contract assertions.
    """
    violations = []
    cid = str(payload.get("container_id", "MISSING_ID"))

    if not payload.get("container_id"):
        violations.append("NULL_OR_EMPTY_CONTAINER_ID")

    # Physical range assertions
    temp = payload.get("internal_temp_celsius")
    if temp is None or not (TEMP_MIN_CELSIUS <= float(temp) <= TEMP_MAX_CELSIUS):
        violations.append(f"TEMPERATURE_OUT_OF_BOUNDS: {temp}°C")

    hum = payload.get("internal_humidity_percent")
    if hum is None or not (HUMIDITY_MIN_PCT <= float(hum) <= HUMIDITY_MAX_PCT):
        violations.append(f"HUMIDITY_OUT_OF_BOUNDS: {hum}%")

    vib = payload.get("vibration_g")
    if vib is None or float(vib) < 0.0 or float(vib) > MAX_VIBRATION_G:
        violations.append(f"VIBRATION_OUT_OF_BOUNDS: {vib}g")

    tonnage = payload.get("cargo_tonnage")
    if tonnage is None or float(tonnage) <= 0.0:
        violations.append(f"INVALID_CARGO_TONNAGE: {tonnage}")

    val = payload.get("cargo_value_usd")
    if val is None or float(val) <= 0.0:
        violations.append(f"INVALID_CARGO_VALUE: {val}")

    is_valid = len(violations) == 0
    return PacketValidationResult(
        container_id=cid,
        is_valid=is_valid,
        violations=violations,
        quarantine_to_dlq=not is_valid,
    )


def audit_dataset_quality(df: pd.DataFrame) -> FleetQualityScorecard:
    """
    Evaluates schema drift and data quality across a batch DataFrame.
    """
    if df.empty:
        return FleetQualityScorecard(
            total_records_checked=0,
            clean_records_count=0,
            quarantined_records_count=0,
            data_quality_score_pct=100.0,
            schema_drift_detected=False,
            drift_keys=[],
            violation_summary={},
        )

    # 1. Schema drift detection
    payload_cols = set(df.columns)
    contract_cols = set(EXPECTED_TELEMETRY_SCHEMA.keys())
    missing_mandatory = contract_cols - payload_cols
    unexpected_cols = payload_cols - contract_cols
    drift_keys = list(unexpected_cols)
    schema_drift = len(missing_mandatory) > 0 or len(unexpected_cols) > 0

    # 2. Record validation
    violation_counts: Dict[str, int] = {}
    clean_count = 0
    quarantine_count = 0

    for _, row in df.iterrows():
        res = validate_telemetry_packet(row.to_dict())
        if res.is_valid:
            clean_count += 1
        else:
            quarantine_count += 1
            for v in res.violations:
                base_v = v.split(":")[0]
                violation_counts[base_v] = violation_counts.get(base_v, 0) + 1

    total = len(df)
    score_pct = round((clean_count / total) * 100.0, 1)

    return FleetQualityScorecard(
        total_records_checked=total,
        clean_records_count=clean_count,
        quarantined_records_count=quarantine_count,
        data_quality_score_pct=score_pct,
        schema_drift_detected=schema_drift,
        drift_keys=drift_keys,
        violation_summary=violation_counts,
    )
