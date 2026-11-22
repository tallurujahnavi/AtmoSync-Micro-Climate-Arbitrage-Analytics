"""
Unit tests for src/alerts.py
Validates Slack Block Kit payload structure, email message formatting,
and automated alert dispatch simulation.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from alerts import (
    format_slack_block_kit_payload,
    format_email_alert_payload,
    dispatch_arbitrage_alert,
    get_alert_history,
)


def test_slack_block_kit_payload():
    container = {
        "container_id": "CONT-TEST-777",
        "commodity": "Hass Avocados",
        "internal_temp_celsius": 16.8,
        "internal_humidity_percent": 65.0,
        "primary_destination": "New Delhi",
        "secondary_destination": "Pune Mandi",
        "hours_to_primary_market": 45.0,
        "hours_to_secondary_market": 4.0,
    }
    evaluation = {
        "spoilage_arbitrage_gain_usd": 48200.0,
        "hours_remaining_shelf_life": 28.5,
    }

    slack = format_slack_block_kit_payload(container, evaluation)
    assert slack["channel"] == "#commodities-arbitrage-alerts"
    assert "blocks" in slack
    assert len(slack["blocks"]) >= 3
    # Check that container ID is mentioned in header block
    assert "CONT-TEST-777" in slack["blocks"][0]["text"]["text"]


def test_email_alert_payload():
    container = {
        "container_id": "CONT-TEST-888",
        "commodity": "Strawberries",
        "secondary_destination": "Chandigarh",
    }
    evaluation = {
        "spoilage_arbitrage_gain_usd": 32000.0,
        "hours_remaining_shelf_life": 12.0,
    }

    email = format_email_alert_payload(container, evaluation, recipient="trader@infotact.in")
    assert email["recipient"] == "trader@infotact.in"
    assert "CONT-TEST-888" in email["subject"]
    assert "$32,000.00" in email["subject"]
    assert "Chandigarh" in email["body"]


def test_alert_dispatch_and_history():
    container = {
        "container_id": "CONT-TEST-999",
        "commodity": "Alphonso Mangoes",
        "secondary_destination": "Nagpur Hub",
    }
    evaluation = {
        "spoilage_arbitrage_gain_usd": 25500.0,
        "alert_level": "CRITICAL_SPOILAGE_RISK",
    }

    receipt = dispatch_arbitrage_alert(container, evaluation, channel="all")
    assert receipt["status"] == "DELIVERED_SUCCESSFULLY"
    assert receipt["container_id"] == "CONT-TEST-999"
    assert receipt["arbitrage_gain_usd"] == 25500.0

    history = get_alert_history(limit=5)
    assert len(history) >= 1
    assert history[0]["container_id"] == "CONT-TEST-999"


if __name__ == "__main__":
    test_slack_block_kit_payload()
    test_email_alert_payload()
    test_alert_dispatch_and_history()
    print("All Alert Notification unit tests passed successfully!")
