"""
test_websocket_gateway.py – Unit tests for real-time WebSocket streaming gateway.
"""

import sys
import os
import json
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import unittest
from websocket_gateway import WebSocketGateway, WSMessage


class TestWebSocketGateway(unittest.TestCase):

    def setUp(self):
        self.gateway = WebSocketGateway(heartbeat_timeout_sec=0.5)

    def test_client_registration_and_disconnect(self):
        session = self.gateway.register_client("trader_desk_1")
        self.assertEqual(session.client_id, "trader_desk_1")
        self.assertTrue(session.is_active)
        self.assertIn("trader_desk_1", self.gateway.clients)

        self.gateway.disconnect_client("trader_desk_1")
        self.assertNotIn("trader_desk_1", self.gateway.clients)

    def test_subscriptions_and_fanout(self):
        self.gateway.register_client("client_a")
        self.gateway.register_client("client_b")

        self.gateway.subscribe("client_a", "spoilage_alerts")
        self.gateway.subscribe("client_b", "macro_weather")

        # Broadcast to spoilage_alerts: only client_a should receive
        delivered = self.gateway.broadcast(
            channel="spoilage_alerts",
            event_type="THERMAL_DRIFT",
            payload={"container_id": "CONT-001", "temp": 16.5}
        )
        self.assertEqual(delivered, 1)
        self.assertEqual(len(self.gateway.clients["client_a"].inbox), 1)
        self.assertEqual(len(self.gateway.clients["client_b"].inbox), 0)

        # Verify parsed message frame
        frame = json.loads(self.gateway.clients["client_a"].inbox[0])
        self.assertEqual(frame["channel"], "spoilage_alerts")
        self.assertEqual(frame["event"], "THERMAL_DRIFT")
        self.assertEqual(frame["data"]["container_id"], "CONT-001")

    def test_wildcard_subscription(self):
        self.gateway.register_client("admin_monitor")
        self.gateway.subscribe("admin_monitor", "*")

        delivered = self.gateway.broadcast("any_channel", "STATUS_PING", {"ok": True})
        self.assertEqual(delivered, 1)
        self.assertEqual(len(self.gateway.clients["admin_monitor"].inbox), 1)

    def test_heartbeat_and_stale_reap(self):
        self.gateway.register_client("stale_client")
        # Artificially set last_ping back
        self.gateway.clients["stale_client"].last_ping = time.time() - 1.0

        reaped = self.gateway.reap_stale_connections()
        self.assertEqual(reaped, 1)
        self.assertNotIn("stale_client", self.gateway.clients)

    def test_stats(self):
        self.gateway.register_client("c1")
        self.gateway.subscribe("c1", "ch1")
        self.gateway.subscribe("c1", "ch2")

        stats = self.gateway.get_stats()
        self.assertEqual(stats["connected_clients"], 1)
        self.assertEqual(stats["active_subscriptions"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
