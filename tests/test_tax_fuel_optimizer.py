"""
test_tax_fuel_optimizer.py – Unit tests for haulage fuel, tolls, and APMC cess optimizer.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import unittest
from tax_fuel_optimizer import (
    compute_fiscal_arbitrage_breakdown,
    NetArbitrageFiscalBreakdown,
    STATE_APMC_CESS_RATES,
)


class TestTaxFuelOptimizer(unittest.TestCase):

    def test_compute_fiscal_arbitrage_breakdown_nominal(self):
        res = compute_fiscal_arbitrage_breakdown(
            container_id="CONT-001",
            target_market="Pune Wholesale Mandi",
            target_state="Maharashtra",
            distance_km=140.0,
            gross_salvage_usd=35000.0,
            fuel_surcharge_multiplier=1.0
        )
        self.assertIsInstance(res, NetArbitrageFiscalBreakdown)
        self.assertEqual(res.container_id, "CONT-001")
        self.assertGreater(res.fuel_cost_usd, 0.0)
        self.assertGreater(res.toll_fees_usd, 0.0)
        self.assertGreater(res.apmc_mandi_cess_usd, 0.0)
        self.assertGreater(res.carbon_tax_levy_usd, 0.0)
        self.assertGreater(res.net_realized_arbitrage_usd, 0.0)
        self.assertLess(res.net_realized_arbitrage_usd, res.gross_salvage_value_usd)
        self.assertGreater(res.margin_retention_pct, 90.0)

    def test_state_cess_differentiation(self):
        res_mh = compute_fiscal_arbitrage_breakdown("C1", "Mandi", "Maharashtra", 100, 10000)
        res_ka = compute_fiscal_arbitrage_breakdown("C1", "Mandi", "Karnataka", 100, 10000)

        # Karnataka cess (1.5%) > Maharashtra cess (1.05%)
        self.assertGreater(res_ka.apmc_mandi_cess_usd, res_mh.apmc_mandi_cess_usd)

    def test_zero_distance_edge_case(self):
        res = compute_fiscal_arbitrage_breakdown("C0", "Local", "Delhi", 0.0, 10000.0)
        self.assertEqual(res.fuel_cost_usd, 0.0)
        self.assertEqual(res.toll_fees_usd, 0.0)
        self.assertEqual(res.carbon_tax_levy_usd, 0.0)
        self.assertGreater(res.net_realized_arbitrage_usd, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
