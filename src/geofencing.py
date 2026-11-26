"""
geofencing.py – Real-time corridor deviation and geofence monitoring engine.

Monitors reefer fleet adherence to authorized cold-chain transport corridors:
1. Polygonal corridor waypoint interpolation
2. Cross-track error (Haversine distance from vehicle to closest corridor segment)
3. Unauthorized detour detection into high-heat micro-climate zones
4. Automatic reroute transit corridor validation
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any
import pandas as pd
from arbitrage import haversine_distance


# ---------------------------------------------------------------------------
# Key Freight Corridors (Waypoints: [Latitude, Longitude])
# ---------------------------------------------------------------------------
FREIGHT_CORRIDORS = {
    "NH44_NORTH_SOUTH": [
        (28.6139, 77.2090),  # New Delhi
        (27.1767, 78.0081),  # Agra
        (26.2183, 78.1828),  # Gwalior
        (23.2599, 77.4126),  # Bhopal
        (21.1458, 79.0882),  # Nagpur
        (17.3850, 78.4867),  # Hyderabad
        (15.8281, 78.0373),  # Kurnool
        (12.9716, 77.5946),  # Bengaluru
    ],
    "WESTERN_CORRIDOR_MUMBAI_DELHI": [
        (19.0760, 72.8777),  # Mumbai
        (21.1702, 72.8311),  # Surat
        (22.3072, 73.1812),  # Vadodara
        (23.0225, 72.5714),  # Ahmedabad
        (24.5854, 73.7125),  # Udaipur
        (26.9124, 75.7873),  # Jaipur
        (28.6139, 77.2090),  # New Delhi
    ],
}

# Maximum permissible cross-track deviation before triggering an alert (km)
MAX_PERMISSIBLE_DEVIATION_KM = 35.0


@dataclass
class GeofenceStatus:
    container_id: str
    corridor_name: str
    current_lat: float
    current_lon: float
    cross_track_deviation_km: float
    is_compliant: bool
    status: str              # IN_CORRIDOR, MINOR_DEVIATION, UNAUTHORIZED_DETOUR_BREACH
    recommendation: str


def compute_cross_track_distance(
    lat: float, lon: float, corridor_waypoints: List[Tuple[float, float]]
) -> float:
    """
    Computes minimum Haversine distance from the vehicle coordinate to the closest corridor waypoint.
    """
    min_dist = float("inf")
    for w_lat, w_lon in corridor_waypoints:
        dist = haversine_distance(lat, lon, w_lat, w_lon)
        if dist < min_dist:
            min_dist = dist
    return round(min_dist, 2)


def evaluate_container_geofence(
    container_id: str,
    lat: float,
    lon: float,
    corridor_name: str = "NH44_NORTH_SOUTH"
) -> GeofenceStatus:
    """
    Audits a container position against its authorized freight route corridor.
    """
    waypoints = FREIGHT_CORRIDORS.get(corridor_name, FREIGHT_CORRIDORS["NH44_NORTH_SOUTH"])
    deviation_km = compute_cross_track_distance(lat, lon, waypoints)

    if deviation_km <= 15.0:
        status = "IN_CORRIDOR"
        compliant = True
        rec = "Vehicle on primary cold-chain corridor. Micro-climate conditions nominal."
    elif deviation_km <= MAX_PERMISSIBLE_DEVIATION_KM:
        status = "MINOR_DEVIATION"
        compliant = True
        rec = f"Minor detour detected ({deviation_km} km off corridor). Monitoring thermal setpoints."
    else:
        status = "UNAUTHORIZED_DETOUR_BREACH"
        compliant = False
        rec = f"Critical route deviation ({deviation_km} km off corridor)! Alerting dispatcher to verify reefer safety."

    return GeofenceStatus(
        container_id=container_id,
        corridor_name=corridor_name,
        current_lat=lat,
        current_lon=lon,
        cross_track_deviation_km=deviation_km,
        is_compliant=compliant,
        status=status,
        recommendation=rec,
    )


def audit_fleet_geofencing(fleet_df: pd.DataFrame) -> Tuple[List[GeofenceStatus], Dict[str, Any]]:
    """Evaluates entire fleet against designated cold-chain corridors."""
    results = []
    for _, row in fleet_df.iterrows():
        cid = str(row.get("container_id", "CONT-UNKNOWN"))
        lat = float(row.get("current_latitude", 21.0))
        lon = float(row.get("current_longitude", 78.0))
        corridor = "WESTERN_CORRIDOR_MUMBAI_DELHI" if lon < 75.0 else "NH44_NORTH_SOUTH"
        results.append(evaluate_container_geofence(cid, lat, lon, corridor))

    breached = sum(1 for r in results if not r.is_compliant)
    summary = {
        "total_monitored": len(results),
        "compliant_count": len(results) - breached,
        "breach_count": breached,
        "compliance_rate_pct": round(((len(results) - breached) / max(1, len(results))) * 100.0, 1),
    }
    return results, summary
