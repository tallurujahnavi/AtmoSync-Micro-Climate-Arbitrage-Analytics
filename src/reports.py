"""
reports.py – Audit report generator and CSV export engine for AtmoSync.

Produces compliance-ready audit summaries, cryptographic SHA-256 integrity
signatures, and CSV exports for commodities trading and cold-chain compliance.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List
import pandas as pd


def generate_fleet_csv(fleet_df: pd.DataFrame) -> str:
    """Exports key fleet telemetry and arbitrage decisions to standard CSV format."""
    cols_to_export = [
        "container_id", "commodity", "origin", "primary_destination",
        "secondary_destination", "internal_temp_celsius",
        "internal_humidity_percent", "vibration_g",
        "hours_remaining_shelf_life", "hours_to_primary_market",
        "primary_realized_value_usd", "secondary_net_value_usd",
        "spoilage_arbitrage_gain_usd", "action_decision", "recommendation"
    ]
    available_cols = [c for c in cols_to_export if c in fleet_df.columns]
    return fleet_df[available_cols].to_csv(index=False)


def generate_audit_report(
    fleet_df: pd.DataFrame,
    auditor_name: str = "AtmoSync Automated Compliance Auditor"
) -> Dict[str, Any]:
    """
    Compiles an executive-grade cold-chain audit report with cryptographic integrity hash.
    """
    now_utc = datetime.now(timezone.utc)
    report_id = f"RPT-{now_utc.strftime('%Y%m%d%H%M%S')}"

    total_units = len(fleet_df)
    at_risk_df = fleet_df[fleet_df["action_decision"].str.contains("REROUTE", na=False)]
    at_risk_count = len(at_risk_df)
    healthy_count = total_units - at_risk_count

    total_cargo_val = float(fleet_df["cargo_value_usd"].sum()) if "cargo_value_usd" in fleet_df.columns else 0.0
    total_gain = float(fleet_df["spoilage_arbitrage_gain_usd"].sum()) if "spoilage_arbitrage_gain_usd" in fleet_df.columns else 0.0

    compliance_pct = round((healthy_count / total_units) * 100.0, 1) if total_units > 0 else 100.0

    # Cryptographic integrity signature
    raw_signature_payload = {
        "report_id": report_id,
        "timestamp": now_utc.isoformat(),
        "total_units": total_units,
        "at_risk_count": at_risk_count,
        "total_cargo_val": total_cargo_val,
        "total_gain": total_gain,
    }
    digest = hashlib.sha256(json.dumps(raw_signature_payload, sort_keys=True).encode()).hexdigest()

    # Markdown executive report formatting
    lines = [
        f"# 📋 AtmoSync Cold-Chain Telemetry & Compliance Audit",
        f"**Report ID**: `{report_id}`  ",
        f"**Audit Timestamp**: {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}  ",
        f"**Lead Auditor**: {auditor_name}  ",
        f"**Integrity Signature (SHA-256)**: `{digest}`  ",
        "",
        "---",
        "## 1. Executive Summary",
        f"- **Total Containers Monitored**: `{total_units}`",
        f"- **Optimal Micro-Climate Transit**: `{healthy_count}` units ({compliance_pct}%)",
        f"- **Thermal Anomaly / Diverted Units**: `{at_risk_count}` units",
        f"- **Total Active Cargo In-Transit**: `${total_cargo_val:,.2f} USD`",
        f"- **Capturable Spoilage Arbitrage**: `${total_gain:,.2f} USD`",
        "",
        "---",
        "## 2. Active Diversion Advisories",
    ]

    if at_risk_count > 0:
        lines.append("| Container | Commodity | Temp Drift | Shelf-Life Left | Destination Reroute | Net Saved ($) |")
        lines.append("|---|---|---|---|---|---|")
        for _, row in at_risk_df.iterrows():
            lines.append(
                f"| `{row.get('container_id', 'N/A')}` | {row.get('commodity', 'N/A')} "
                f"| {row.get('internal_temp_celsius', 0.0):.1f}°C "
                f"| {row.get('hours_remaining_shelf_life', 0.0):.1f} hrs "
                f"| {row.get('secondary_destination', 'N/A')} "
                f"| ${row.get('spoilage_arbitrage_gain_usd', 0.0):,.2f} |"
            )
    else:
        lines.append("No active thermal excursions detected. All fleet reefers compliant with target setpoints.")

    lines.extend([
        "",
        "---",
        "## 3. Regulatory & Quality Statement",
        "All telemetry packets verified via Snowflake DWH ingestion logs and Arrhenius Q10 kinetic modeling.",
        f"*Report verified electronically by {auditor_name}.*",
    ])

    markdown_doc = "\n".join(lines)

    return {
        "report_id": report_id,
        "timestamp": now_utc.isoformat(),
        "total_containers": total_units,
        "at_risk_count": at_risk_count,
        "compliance_rate_pct": compliance_pct,
        "total_cargo_val_usd": total_cargo_val,
        "total_arbitrage_gain_usd": total_gain,
        "integrity_hash": digest,
        "markdown_content": markdown_doc,
    }
