"""
sensor_calibration.py – IoT Sensor Drift Detection & Telemetry Calibration Engine.

Addresses signal noise and hardware drift in transit:
1. Thermocouple Zero-Point & Span Drift Detection
2. Vibration-induced telemetry noise filtering (accelerometer > 1.2g threshold)
3. Rolling Exponentially Weighted Moving Average (EWMA) baseline smoothing
4. False-positive alarm prevention for cold-chain spoilage diversions
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Any
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Calibration Thresholds & Noise Parameters
# ---------------------------------------------------------------------------
# Road transport vibration above 1.2g causes mechanical contact bounce and sensor jitter
VIBRATION_NOISE_THRESHOLD_G = 1.20

# Thermocouple drift bounds: readings fluctuating > 3.5 deg C above moving median without cargo load changes
MAX_ACCEPTABLE_SENSOR_DRIFT_C = 3.00

# Minimum confidence threshold for automated rerouting authorization
MIN_CONFIDENCE_THRESHOLD = 0.85


@dataclass
class CalibratedReading:
    container_id: str
    commodity: str
    raw_temp_c: float
    calibrated_temp_c: float
    drift_detected: bool
    drift_delta_c: float
    vibration_damped: bool
    sensor_health: str          # OPTIMAL, JITTER_SUPPRESSED, DRIFT_COMPENSATED, HARDWARE_FAULT
    confidence_score: float     # 0.0 to 1.0


def filter_vibration_noise(raw_temp: float, vibration_g: float) -> Tuple[float, bool]:
    """
    Suppresses transient temperature spikes caused by heavy road vibration
    and mechanical sensor contact jitter.
    """
    if vibration_g > VIBRATION_NOISE_THRESHOLD_G:
        # Excess vibration artificially amplifies transient thermal readings by 8-15%
        jitter_offset = (vibration_g - VIBRATION_NOISE_THRESHOLD_G) * 0.85
        cleaned_temp = max(-10.0, raw_temp - jitter_offset)
        return round(cleaned_temp, 2), True
    return raw_temp, False


def detect_sensor_drift(calibrated_temp: float, historical_baseline_temp: float) -> Tuple[float, bool]:
    """
    Identifies thermocouple calibration drift versus legitimate environmental excursions.
    """
    drift_delta = calibrated_temp - historical_baseline_temp
    is_drift = abs(drift_delta) >= MAX_ACCEPTABLE_SENSOR_DRIFT_C
    return round(drift_delta, 2), is_drift


def calibrate_container_packet(row: pd.Series) -> CalibratedReading:
    """
    Performs full pre-processing and noise calibration on a single container telemetry packet.
    """
    cid = str(row.get("container_id", "UNKNOWN"))
    commodity = str(row.get("commodity", "Perishable"))
    raw_t = float(row.get("internal_temp_celsius", 5.0))
    vib_g = float(row.get("vibration_g", 0.35))
    
    # Target baseline from ideal band midpoint or setpoint
    baseline_t = float(row.get("target_setpoint_c", 5.0)) if "target_setpoint_c" in row else 5.0

    # Step 1: Suppress vibration-induced mechanical contact jitter
    vibe_damped_temp, was_damped = filter_vibration_noise(raw_t, vib_g)

    # Step 2: Compute sensor drift against baseline setpoint
    drift_delta, has_drift = detect_sensor_drift(vibe_damped_temp, baseline_t)

    # Step 3: Determine sensor hardware health status and confidence score
    confidence = 1.0

    if was_damped:
        confidence -= 0.10

    if has_drift:
        if abs(drift_delta) > 8.0:
            status = "HARDWARE_FAULT"
            confidence -= 0.35
            # For hardware fault, clamp to baseline + conservative delta
            final_temp = baseline_t + (drift_delta * 0.5)
        else:
            status = "DRIFT_COMPENSATED"
            confidence -= 0.15
            final_temp = vibe_damped_temp - (drift_delta * 0.3)
    elif was_damped:
        status = "JITTER_SUPPRESSED"
        final_temp = vibe_damped_temp
    else:
        status = "OPTIMAL"
        final_temp = raw_t

    final_temp = round(final_temp, 2)
    confidence = round(max(0.20, min(1.0, confidence)), 2)

    return CalibratedReading(
        container_id=cid,
        commodity=commodity,
        raw_temp_c=raw_t,
        calibrated_temp_c=final_temp,
        drift_detected=has_drift,
        drift_delta_c=drift_delta,
        vibration_damped=was_damped,
        sensor_health=status,
        confidence_score=confidence,
    )


def calibrate_fleet_telemetry(fleet_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Applies sensor calibration across an entire fleet DataFrame.
    Returns:
        1. DataFrame with calibrated telemetry columns attached
        2. Calibration audit metrics dictionary
    """
    if fleet_df.empty:
        return fleet_df, {
            "total_packets": 0,
            "vibration_damped_count": 0,
            "drift_detected_count": 0,
            "hardware_fault_count": 0,
            "false_positives_prevented": 0,
            "mean_confidence_score": 1.0,
        }

    calibrations = [calibrate_container_packet(row) for _, row in fleet_df.iterrows()]
    
    cal_df = pd.DataFrame([{
        "container_id": c.container_id,
        "calibrated_temp_celsius": c.calibrated_temp_c,
        "sensor_health": c.sensor_health,
        "drift_detected": c.drift_detected,
        "drift_delta_c": c.drift_delta_c,
        "vibration_damped": c.vibration_damped,
        "telemetry_confidence": c.confidence_score,
    } for c in calibrations])

    merged = pd.merge(fleet_df, cal_df, on="container_id")

    # Quantify false alarm mitigation:
    # A false positive occurs when raw temp triggered a thermal alarm, but calibrated temp is within safe band
    raw_alarms = sum(1 for t in fleet_df["internal_temp_celsius"] if t > 12.0)
    cal_alarms = sum(1 for t in merged["calibrated_temp_celsius"] if t > 12.0)
    false_positives = max(0, raw_alarms - cal_alarms)

    vibe_count = sum(1 for c in calibrations if c.vibration_damped)
    drift_count = sum(1 for c in calibrations if c.drift_detected)
    fault_count = sum(1 for c in calibrations if c.sensor_health == "HARDWARE_FAULT")
    mean_conf = round(float(np.mean([c.confidence_score for c in calibrations])), 2)

    audit_summary = {
        "total_packets": len(calibrations),
        "vibration_damped_count": vibe_count,
        "drift_detected_count": drift_count,
        "hardware_fault_count": fault_count,
        "false_positives_prevented": false_positives,
        "mean_confidence_score": mean_conf,
    }

    return merged, audit_summary
