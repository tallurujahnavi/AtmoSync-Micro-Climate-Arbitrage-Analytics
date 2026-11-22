"""
AtmoSync: Micro-Climate Arbitrage Analytics
Module: alerts.py
Description: Automated Slack and Email alerting notification engine.
             Triggered by real-time micro-climate thermal drift and Spoilage Arbitrage
             opportunities (as specified in Week 4 of the Infotact Project Document).
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


ALERT_LOG_FILE = Path(__file__).resolve().parent.parent / "data" / "alert_history.json"


def format_slack_block_kit_payload(container_data: Dict, evaluation_data: Dict) -> Dict:
    """
    Constructs an interactive Slack Block Kit JSON payload
    notifying commodities traders of an actionable Spoilage Arbitrage opportunity.
    """
    cid = container_data.get("container_id", "CONT-UNKNOWN")
    commodity = container_data.get("commodity", "Perishable Agro Goods")
    temp = container_data.get("internal_temp_celsius", 0.0)
    hum = container_data.get("internal_humidity_percent", 0.0)
    primary = container_data.get("primary_destination", "Primary Terminal")
    secondary = container_data.get("secondary_destination", "Secondary Mandi")
    gain = evaluation_data.get("spoilage_arbitrage_gain_usd", 0.0)
    hours_left = evaluation_data.get("hours_remaining_shelf_life", 0.0)
    hours_primary = container_data.get("hours_to_primary_market", 0.0)
    hours_secondary = container_data.get("hours_to_secondary_market", 0.0)

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🚨 CRITICAL ARBITRAGE TRIGGER: {cid} ({commodity})",
                "emoji": True
            }
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Container ID:*\n`{cid}`"},
                {"type": "mrkdwn", "text": f"*Commodity:*\n*{commodity}*"},
                {"type": "mrkdwn", "text": f"*Internal Temperature:*\n⚠️ `{temp:.1f}°C` (Drift Detected)"},
                {"type": "mrkdwn", "text": f"*Relative Humidity:*\n`{hum:.1f}%`"},
            ]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*Micro-Climate Transit Risk Analysis:*\n"
                    f"• *Remaining Shelf Life:* `{hours_left:.1f} hours`\n"
                    f"• *Transit to {primary}:* `{hours_primary:.1f} hours` → *WILL ARRIVE SPOILED!* (95% value loss)\n"
                    f"• *Recommended Diversion:* Reroute to *{secondary}* (`{hours_secondary:.1f} hours` transit)\n"
                    f"• *Net Spoilage Arbitrage Capture:* `+${gain:,.2f} USD`"
                )
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": f"⚡ Authorize Reroute to {secondary}"},
                    "style": "primary",
                    "value": f"reroute_{cid}"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Acknowledge & Monitor"},
                    "value": f"ack_{cid}"
                }
            ]
        }
    ]

    return {
        "channel": "#commodities-arbitrage-alerts",
        "username": "AtmoSync Cold-Chain Bot",
        "icon_emoji": ":avocado:",
        "blocks": blocks,
    }


def format_email_alert_payload(container_data: Dict, evaluation_data: Dict, recipient: str = "trader@infotact.in") -> Dict:
    """
    Constructs an executive email alert notification for the Infotact Commodities Desk.
    """
    cid = container_data.get("container_id", "CONT-UNKNOWN")
    commodity = container_data.get("commodity", "Perishable Agro Goods")
    gain = evaluation_data.get("spoilage_arbitrage_gain_usd", 0.0)
    secondary = container_data.get("secondary_destination", "Secondary Mandi")

    subject = f"[URGENT ARBITRAGE ALERT] Reroute Order Recommended for {cid} (+${gain:,.2f})"

    body = f"""
Dear Infotact Commodities Trader,

AtmoSync has detected a critical micro-climate thermal excursion in reefer container {cid} carrying {commodity}.

Key Telemetry & Arbitrage Parameters:
--------------------------------------------------------------------------------
- Container ID:                 {cid}
- Commodity Cargo:              {commodity}
- Current Internal Temperature: {container_data.get('internal_temp_celsius', 0.0):.1f} °C
- Remaining Usable Shelf Life:  {evaluation_data.get('hours_remaining_shelf_life', 0.0):.1f} hours
- Time to Primary Destination:  {container_data.get('hours_to_primary_market', 0.0):.1f} hours [TOTAL SPOILAGE RISK]
- Time to Secondary Diversion:  {container_data.get('hours_to_secondary_market', 0.0):.1f} hours ({secondary})
--------------------------------------------------------------------------------
FINANCIAL ARBITRAGE GAIN:       +${gain:,.2f} USD saved vs. terminal spoilage loss.

Action Required:
Log in to the AtmoSync Executive BI Portal (http://localhost:8501) and authorize the carrier diversion waypoint to {secondary}.

Best Regards,
AtmoSync Cold-Chain Surveillance Network
Infotact Solutions Global Logistics Desk
"""
    return {
        "recipient": recipient,
        "subject": subject,
        "body": body.strip(),
        "dispatched_at": datetime.now().isoformat(),
    }


def dispatch_arbitrage_alert(
    container_data: Dict,
    evaluation_data: Dict,
    channel: str = "all"
) -> Dict:
    """
    Simulates automated webhook dispatch to Slack and Email recipients.
    Records delivery receipt to persistent alert history log.
    """
    slack_payload = format_slack_block_kit_payload(container_data, evaluation_data)
    email_payload = format_email_alert_payload(container_data, evaluation_data)

    receipt = {
        "alert_id": f"ALT-{int(datetime.now().timestamp() * 1000) % 1000000}",
        "container_id": container_data.get("container_id", "CONT-UNKNOWN"),
        "commodity": container_data.get("commodity", "Goods"),
        "alert_level": evaluation_data.get("alert_level", "WARNING"),
        "arbitrage_gain_usd": evaluation_data.get("spoilage_arbitrage_gain_usd", 0.0),
        "target_diversion": container_data.get("secondary_destination", "Mandi"),
        "dispatched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "channels": ["slack", "email"] if channel == "all" else [channel],
        "status": "DELIVERED_SUCCESSFULLY",
        "slack_preview": slack_payload,
        "email_preview": email_payload,
    }

    # Persist receipt
    ALERT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing_alerts = []
    if ALERT_LOG_FILE.exists():
        try:
            with open(ALERT_LOG_FILE, "r", encoding="utf-8") as f:
                existing_alerts = json.load(f)
        except Exception:
            existing_alerts = []

    existing_alerts.insert(0, receipt)
    # Retain latest 50 alerts
    existing_alerts = existing_alerts[:50]

    with open(ALERT_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(existing_alerts, f, indent=2)

    return receipt


def get_alert_history(limit: int = 10) -> List[Dict]:
    """Retrieves list of recently dispatched alert receipts."""
    if not ALERT_LOG_FILE.exists():
        return []
    try:
        with open(ALERT_LOG_FILE, "r", encoding="utf-8") as f:
            alerts = json.load(f)
            return alerts[:limit]
    except Exception:
        return []
