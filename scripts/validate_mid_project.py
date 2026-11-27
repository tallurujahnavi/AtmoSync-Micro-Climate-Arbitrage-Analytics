"""
AtmoSync: Micro-Climate Arbitrage Analytics
Script: scripts/validate_mid_project.py
Description: Mid-Project Review (Week 2 Day 4) end-to-end validation checking
             IoT telemetry generation, zero-loss parsing, commodity pricing
             referential integrity, Snowflake DDL readiness, and dbt staging checks.
"""

import csv
import json
from pathlib import Path
import sys
from typing import Any, Dict

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from climate_telemetry import parse_telemetry_records, summarize_by_container
from iot_simulator import IoTSimulator, default_fleet_configs


def run_mid_project_validation(steps: int = 24, seed: int = 2026) -> Dict[str, Any]:
    """
    Executes Week 2 Mid-Project Review pipeline & data integrity checks.

    Returns:
        Dictionary summarizing check outcomes and `overall_status` ('PASSED' or 'FAILED').
    """
    # 1. Simulate IoT container stream and validate zero-rejection parsing
    sim = IoTSimulator(seed=seed)
    fleet_configs = default_fleet_configs()
    raw_events = sim.simulate_fleet(fleet_configs, steps=steps, interval_minutes=15)
    valid_records, rejected_records = parse_telemetry_records(raw_events)
    container_summaries = summarize_by_container(valid_records)

    # 2. Verify commodity pricing reference covers every simulated commodity in both tiers
    pricing_path = ROOT_DIR / "data" / "commodity_pricing.csv"
    tiers_by_commodity: Dict[str, set] = {}
    with pricing_path.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            tiers_by_commodity.setdefault(row["commodity"].strip(), set()).add(
                row["market_tier"].strip()
            )

    missing_pricing = [
        cfg.commodity
        for cfg in fleet_configs
        if tiers_by_commodity.get(cfg.commodity) != {"PRIMARY", "SECONDARY"}
    ]

    # 3. Verify Snowflake DDL and dbt staging/test assets exist
    required_assets = [
        ROOT_DIR / "sql" / "snowflake_schema.sql",
        ROOT_DIR / "dbt" / "dbt_project.yml",
        ROOT_DIR / "dbt" / "models" / "staging" / "stg_container_telemetry.sql",
        ROOT_DIR / "dbt" / "models" / "staging" / "stg_commodity_pricing.sql",
        ROOT_DIR / "dbt" / "models" / "staging" / "stg_telemetry_enriched.sql",
        ROOT_DIR / "dbt" / "tests" / "assert_telemetry_bounds.sql",
        ROOT_DIR / "dbt" / "tests" / "assert_pricing_positive.sql",
    ]
    missing_assets = [str(p.relative_to(ROOT_DIR)) for p in required_assets if not p.exists()]

    # 4. Verify fault-injected drifting container is flagged as WARNING or CRITICAL
    drifting_status = container_summaries.get("CNT-AVO-01", {}).get(
        "commodity_compliance", {}
    ).get("status")
    healthy_status = container_summaries.get("CNT-BAN-02", {}).get(
        "commodity_compliance", {}
    ).get("status")

    checks = {
        "zero_rejected_events": len(rejected_records) == 0,
        "expected_event_count": len(valid_records) == len(fleet_configs) * steps,
        "pricing_referential_integrity": len(missing_pricing) == 0,
        "warehouse_and_dbt_assets_present": len(missing_assets) == 0,
        "drift_container_flagged": drifting_status in {"WARNING", "CRITICAL"},
        "healthy_container_normal": healthy_status == "NORMAL",
    }

    overall_status = "PASSED" if all(checks.values()) else "FAILED"
    return {
        "overall_status": overall_status,
        "events_generated": len(raw_events),
        "events_valid": len(valid_records),
        "events_rejected": len(rejected_records),
        "containers_validated": len(container_summaries),
        "missing_pricing_commodities": missing_pricing,
        "missing_assets": missing_assets,
        "checks": checks,
    }


if __name__ == "__main__":
    summary = run_mid_project_validation()
    print(json.dumps(summary, indent=2))
    if summary["overall_status"] != "PASSED":
        sys.exit(1)
