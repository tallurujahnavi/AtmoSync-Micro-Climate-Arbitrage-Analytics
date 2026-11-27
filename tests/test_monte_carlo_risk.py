"""
test_monte_carlo_risk.py – Unit tests for Monte Carlo spoilage risk and VaR engine.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import unittest
import pandas as pd
from iot_simulator import generate_fleet_telemetry
from monte_carlo_risk import (
    MonteCarloConfig,
    RiskSimulationResult,
    simulate_spoilage_var,
    simulate_fleet_var,
)


class TestMonteCarloRisk(unittest.TestCase):

    def test_simulate_spoilage_var_structure_and_ordering(self):
        cfg = MonteCarloConfig(
            commodity="Hass Avocados",
            cargo_value_usd=40000.0,
            transit_hours=48.0,
            ambient_mean_c=11.0,
            ambient_volatility_c=3.0,
            heatwave_prob=0.15,
            n_simulations=500,
            seed=42,
        )
        res = simulate_spoilage_var(cfg)
        self.assertIsInstance(res, RiskSimulationResult)
        self.assertEqual(res.n_simulations, 500)
        self.assertEqual(len(res.simulated_losses_usd), 500)
        self.assertEqual(len(res.simulated_peak_temps_c), 500)
        # Tail risk ordering invariant: Expected Loss <= VaR 95 <= CVaR 95 and VaR 95 <= VaR 99
        self.assertLessEqual(res.expected_loss_usd, res.var_95_usd)
        self.assertLessEqual(res.var_95_usd, res.cvar_95_usd)
        self.assertLessEqual(res.var_95_usd, res.var_99_usd)

    def test_higher_heat_increases_spoilage_probability(self):
        cool_cfg = MonteCarloConfig("Strawberries", 30000.0, 48.0, ambient_mean_c=1.0, heatwave_prob=0.0, n_simulations=400, seed=7)
        hot_cfg = MonteCarloConfig("Strawberries", 30000.0, 48.0, ambient_mean_c=16.0, heatwave_prob=0.25, n_simulations=400, seed=7)

        cool_res = simulate_spoilage_var(cool_cfg)
        hot_res = simulate_spoilage_var(hot_cfg)

        self.assertGreater(hot_res.spoilage_probability_pct, cool_res.spoilage_probability_pct)
        self.assertGreater(hot_res.var_95_usd, cool_res.var_95_usd)

    def test_simulate_fleet_var(self):
        fleet = generate_fleet_telemetry(num_containers=5)
        summary = simulate_fleet_var(fleet, n_simulations=200, seed=10)
        self.assertEqual(summary["containers_simulated"], 5)
        self.assertGreater(summary["portfolio_value_usd"], 0.0)
        self.assertLessEqual(summary["portfolio_expected_loss_usd"], summary["portfolio_var_95_usd"])
        self.assertIsNotNone(summary["highest_risk_container"])
        self.assertEqual(len(summary["container_results"]), 5)

    def test_simulate_empty_fleet_var(self):
        summary = simulate_fleet_var(pd.DataFrame())
        self.assertEqual(summary["containers_simulated"], 0)
        self.assertEqual(summary["portfolio_var_95_usd"], 0.0)
        self.assertIsNone(summary["highest_risk_container"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
