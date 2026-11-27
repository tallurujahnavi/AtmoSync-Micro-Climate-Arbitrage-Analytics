"""
AtmoSync: Micro-Climate Arbitrage Analytics
Module: iot_simulator.py
Description: Week 2 Python IoT container telemetry simulator generating streaming
             JSON/NDJSON and CSV payloads (temperature, humidity, vibration,
             interpolated GPS route coordinates, and configurable fault modes)
             for Kafka/Snowflake ingestion and climate telemetry validation.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
import csv
import json
from pathlib import Path
import random
import sys
from typing import Any, Dict, Iterator, List, Optional, Sequence

try:
    from src.climate_telemetry import COMMODITY_STORAGE_PROFILES
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from climate_telemetry import COMMODITY_STORAGE_PROFILES


VALID_FAULT_MODES = ("none", "compressor_drift", "humidity_spike", "vibration_shock")


@dataclass(frozen=True)
class RouteSpec:
    """Origin-to-destination shipping corridor with GPS endpoints."""

    name: str
    origin: str
    destination: str
    origin_lat: float
    origin_lon: float
    dest_lat: float
    dest_lon: float


DEFAULT_ROUTES: Dict[str, RouteSpec] = {
    "Nashik-JNPT": RouteSpec(
        name="Nashik-JNPT",
        origin="Nashik",
        destination="JNPT Mumbai",
        origin_lat=19.9975,
        origin_lon=73.7898,
        dest_lat=18.9498,
        dest_lon=72.9508,
    ),
    "Bengaluru-Chennai": RouteSpec(
        name="Bengaluru-Chennai",
        origin="Bengaluru",
        destination="Chennai Port",
        origin_lat=12.9716,
        origin_lon=77.5946,
        dest_lat=13.0844,
        dest_lon=80.2899,
    ),
    "Hyderabad-Vizag": RouteSpec(
        name="Hyderabad-Vizag",
        origin="Hyderabad",
        destination="Visakhapatnam Port",
        origin_lat=17.3850,
        origin_lon=78.4867,
        dest_lat=17.6868,
        dest_lon=83.2185,
    ),
    "Pune-Mundra": RouteSpec(
        name="Pune-Mundra",
        origin="Pune",
        destination="Mundra Port",
        origin_lat=18.5204,
        origin_lon=73.8567,
        dest_lat=22.8395,
        dest_lon=69.7213,
    ),
}


@dataclass(frozen=True)
class ContainerConfig:
    """Simulation configuration for a single refrigerated shipping container."""

    container_id: str
    commodity: str
    route_name: str = "Bengaluru-Chennai"
    tonnage_mt: float = 20.0
    fault_mode: str = "none"
    fault_start_step: int = 8
    drift_rate_c_per_step: float = 0.65

    def __post_init__(self) -> None:
        if not self.container_id.strip():
            raise ValueError("container_id must be non-empty.")
        if self.commodity not in COMMODITY_STORAGE_PROFILES:
            raise ValueError(
                f"Unknown commodity '{self.commodity}'. Supported: {list(COMMODITY_STORAGE_PROFILES.keys())}"
            )
        if self.route_name not in DEFAULT_ROUTES:
            raise ValueError(
                f"Unknown route '{self.route_name}'. Supported: {list(DEFAULT_ROUTES.keys())}"
            )
        if self.fault_mode not in VALID_FAULT_MODES:
            raise ValueError(
                f"Invalid fault_mode '{self.fault_mode}'. Supported: {VALID_FAULT_MODES}"
            )
        if self.fault_start_step < 0:
            raise ValueError("fault_start_step must be >= 0.")


@dataclass(frozen=True)
class ContainerTelemetryEvent:
    """Single IoT sensor payload emitted by an in-transit reefer container."""

    event_id: str
    container_id: str
    timestamp: str
    commodity: str
    tonnage_mt: float
    route_name: str
    origin: str
    destination: str
    progress_pct: float
    latitude: float
    longitude: float
    temperature_c: float
    humidity_pct: float
    vibration_g: float
    compressor_status: str
    door_open: bool
    fault_injected: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


def _interpolate_gps(route: RouteSpec, fraction: float) -> tuple[float, float]:
    """Linearly interpolates latitude/longitude along a route for fraction in [0, 1]."""
    clamped = max(0.0, min(1.0, fraction))
    lat = route.origin_lat + (route.dest_lat - route.origin_lat) * clamped
    lon = route.origin_lon + (route.dest_lon - route.origin_lon) * clamped
    return round(lat, 5), round(lon, 5)


class IoTSimulator:
    """
    Deterministic streaming telemetry generator for refrigerated containers.

    Reuses commodity envelopes from `COMMODITY_STORAGE_PROFILES` so baseline
    readings stay within safe tolerances unless a fault scenario is triggered.
    """

    def __init__(self, seed: int = 42) -> None:
        self._rng = random.Random(seed)

    def stream_container(
        self,
        config: ContainerConfig,
        steps: int = 24,
        interval_minutes: int = 15,
        start_time: Optional[datetime] = None,
    ) -> Iterator[ContainerTelemetryEvent]:
        """Yields `steps` chronological IoT telemetry events for one container."""
        if steps <= 0:
            raise ValueError("steps must be > 0.")
        if interval_minutes <= 0:
            raise ValueError("interval_minutes must be > 0.")

        profile = COMMODITY_STORAGE_PROFILES[config.commodity]
        route = DEFAULT_ROUTES[config.route_name]
        base_temp = (profile["temp_min_c"] + profile["temp_max_c"]) / 2.0
        base_hum = (profile["hum_min_pct"] + profile["hum_max_pct"]) / 2.0
        t0 = start_time or datetime(2026, 11, 27, 8, 0, 0)

        for step in range(steps):
            ts = (t0 + timedelta(minutes=step * interval_minutes)).strftime("%Y-%m-%dT%H:%M:%S")
            fraction = step / max(1, steps - 1)
            lat, lon = _interpolate_gps(route, fraction)

            temp = base_temp + self._rng.gauss(0.0, 0.25)
            hum = base_hum + self._rng.gauss(0.0, 1.0)
            vib = max(0.02, 0.14 + abs(self._rng.gauss(0.0, 0.05)))
            compressor_status = "OK"
            door_open = False
            fault_active = config.fault_mode != "none" and step >= config.fault_start_step

            if fault_active:
                fault_steps = step - config.fault_start_step + 1
                if config.fault_mode == "compressor_drift":
                    temp += fault_steps * config.drift_rate_c_per_step
                    hum -= min(28.0, fault_steps * 1.8)
                    compressor_status = "FAULT" if fault_steps >= 4 else "DEGRADED"
                elif config.fault_mode == "humidity_spike":
                    hum += min(18.0, 7.5 + fault_steps * 1.2)
                    compressor_status = "DEGRADED"
                elif config.fault_mode == "vibration_shock":
                    vib += 0.75 + abs(self._rng.gauss(0.0, 0.15))
                    door_open = fault_steps % 5 == 0

            hum = max(5.0, min(100.0, hum))
            event_id = f"{config.container_id}-{step:04d}-{self._rng.randint(1000, 9999)}"

            yield ContainerTelemetryEvent(
                event_id=event_id,
                container_id=config.container_id,
                timestamp=ts,
                commodity=config.commodity,
                tonnage_mt=round(config.tonnage_mt, 2),
                route_name=route.name,
                origin=route.origin,
                destination=route.destination,
                progress_pct=round(fraction * 100.0, 2),
                latitude=lat,
                longitude=lon,
                temperature_c=round(temp, 3),
                humidity_pct=round(hum, 3),
                vibration_g=round(vib, 3),
                compressor_status=compressor_status,
                door_open=door_open,
                fault_injected=fault_active,
            )

    def simulate_fleet(
        self,
        configs: Sequence[ContainerConfig],
        steps: int = 24,
        interval_minutes: int = 15,
        start_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Generates interleaved chronological telemetry dicts for a container fleet."""
        if not configs:
            raise ValueError("configs must contain at least one ContainerConfig.")

        events: List[Dict[str, Any]] = []
        for cfg in configs:
            for event in self.stream_container(
                cfg,
                steps=steps,
                interval_minutes=interval_minutes,
                start_time=start_time,
            ):
                events.append(event.to_dict())

        events.sort(key=lambda item: (item["timestamp"], item["container_id"]))
        return events


def default_fleet_configs() -> List[ContainerConfig]:
    """Returns a representative 4-container fleet mixing healthy and drifting units."""
    return [
        ContainerConfig(
            container_id="CNT-AVO-01",
            commodity="Avocado",
            route_name="Bengaluru-Chennai",
            fault_mode="compressor_drift",
            fault_start_step=6,
            drift_rate_c_per_step=0.75,
        ),
        ContainerConfig(
            container_id="CNT-BAN-02",
            commodity="Banana",
            route_name="Nashik-JNPT",
            fault_mode="none",
        ),
        ContainerConfig(
            container_id="CNT-MAN-03",
            commodity="Mango",
            route_name="Hyderabad-Vizag",
            fault_mode="humidity_spike",
            fault_start_step=10,
        ),
        ContainerConfig(
            container_id="CNT-STR-04",
            commodity="Strawberry",
            route_name="Pune-Mundra",
            fault_mode="vibration_shock",
            fault_start_step=12,
        ),
    ]


def write_ndjson_stream(events: Sequence[Dict[str, Any]], output_path: str) -> str:
    """Writes telemetry events as newline-delimited JSON for Kafka/Snowflake ingestion."""
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as fh:
        for event in events:
            fh.write(json.dumps(event) + "\n")
    return str(target)


def write_csv_telemetry(events: Sequence[Dict[str, Any]], output_path: str) -> str:
    """Writes telemetry events to CSV compatible with `climate_telemetry.load_csv_telemetry`."""
    if not events:
        raise ValueError("Cannot write CSV from empty events list.")
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(events[0].keys())
    with target.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(events)
    return str(target)


if __name__ == "__main__":
    sim = IoTSimulator(seed=2026)
    fleet_events = sim.simulate_fleet(default_fleet_configs(), steps=16, interval_minutes=15)
    print(f"Generated {len(fleet_events)} IoT telemetry events across 4 containers.")
    print("Sample payload:", json.dumps(fleet_events[0], indent=2))
