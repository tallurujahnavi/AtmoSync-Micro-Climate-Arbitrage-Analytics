"""
test_audit_logger.py – Unit tests for security audit ledger and RBAC event compliance.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import unittest
from audit_logger import (
    SecurityAuditLedger,
    SecurityAuditEvent,
    authorize_action,
    GLOBAL_AUDIT_LEDGER,
)


class TestSecurityAuditLogger(unittest.TestCase):

    def setUp(self):
        self.ledger = SecurityAuditLedger()

    def test_log_event_hash_chain(self):
        ev1 = self.ledger.log_event("trader@infotact.in", "Trader", "EXECUTE_REROUTE", "CONT-001", "ALLOWED")
        ev2 = self.ledger.log_event("trader@infotact.in", "Trader", "EXECUTE_REROUTE", "CONT-002", "ALLOWED")

        self.assertEqual(ev2.previous_hash, ev1.event_hash)
        self.assertTrue(self.ledger.verify_ledger_integrity())

    def test_ledger_tampering_detection(self):
        self.ledger.log_event("trader@infotact.in", "Trader", "EXECUTE_REROUTE", "CONT-001", "ALLOWED")
        self.ledger.log_event("trader@infotact.in", "Trader", "EXECUTE_REROUTE", "CONT-002", "ALLOWED")

        # Simulate tampering
        self.ledger._chain[0].user_role = "Hacker"
        self.assertFalse(self.ledger.verify_ledger_integrity())

    def test_authorize_action_success(self):
        allowed = authorize_action(
            user_email="trader@infotact.in",
            user_role="Commodities Trader",
            action="REROUTE_SHIPMENT",
            resource_id="CONT-005",
            required_role="Commodities Trader"
        )
        self.assertTrue(allowed)

    def test_authorize_action_denied(self):
        allowed = authorize_action(
            user_email="analyst@infotact.in",
            user_role="Supply Chain Analyst",
            action="EXECUTE_FINANCIAL_SETTLEMENT",
            resource_id="CONT-009",
            required_role="Commodities Trader"
        )
        self.assertFalse(allowed)

    def test_audit_summary_metrics(self):
        self.ledger.log_event("u1@infotact.in", "Trader", "VIEW", "R1", "ALLOWED")
        self.ledger.log_event("u2@infotact.in", "Guest", "DELETE", "R2", "DENIED_INSUFFICIENT_ROLE", "CRITICAL")

        summary = self.ledger.get_audit_summary()
        self.assertEqual(summary["total_events_logged"], 2)
        self.assertEqual(summary["incidents_blocked"], 1)
        self.assertTrue(summary["chain_integrity_verified"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
