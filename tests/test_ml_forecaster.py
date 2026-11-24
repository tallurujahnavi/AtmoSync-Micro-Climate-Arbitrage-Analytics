"""
test_ml_forecaster.py – Unit tests for the ML Forecasting module.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import unittest
from ml_forecaster import (
    ClimateFeatures,
    ForecastResult,
    ModelReport,
    COMMODITIES,
    WARMING_SCENARIOS,
    OPTIMAL_TEMP,
    _generate_training_data,
    _spoilage_label,
    train_models,
    run_scenario_forecast,
    bulk_forecast,
)


class TestDataGeneration(unittest.TestCase):

    def test_shape(self):
        X, y = _generate_training_data("Tomato", n=50)
        self.assertEqual(X.shape, (50, 5))
        self.assertEqual(y.shape, (50,))

    def test_csi_range(self):
        _, y = _generate_training_data("Mango", n=100)
        self.assertTrue((y >= 0).all())
        self.assertTrue((y <= 100).all())


class TestSpoilageLabel(unittest.TestCase):

    def test_low(self):
        risk, rec = _spoilage_label(80)
        self.assertEqual(risk, "LOW")
        self.assertIn("No intervention", rec)

    def test_medium(self):
        risk, _ = _spoilage_label(60)
        self.assertEqual(risk, "MEDIUM")

    def test_high(self):
        risk, _ = _spoilage_label(35)
        self.assertEqual(risk, "HIGH")

    def test_critical(self):
        risk, rec = _spoilage_label(10)
        self.assertEqual(risk, "CRITICAL")
        self.assertIn("Immediate", rec)


class TestModelTraining(unittest.TestCase):

    def setUp(self):
        self.models, self.reports = train_models()

    def test_model_count(self):
        # Either all trained (sklearn present) or empty (fallback)
        self.assertIn(len(self.models), [0, len(COMMODITIES)])

    def test_report_metrics(self):
        for report in self.reports:
            self.assertIsInstance(report, ModelReport)
            self.assertGreaterEqual(report.r2, 0.0)
            self.assertLess(report.mae, 25.0)   # reasonable MAE on CSI 0-100

    def test_feature_importance_sums_to_one(self):
        for report in self.reports:
            total = sum(report.feature_importance.values())
            self.assertAlmostEqual(total, 1.0, places=5)


class TestScenarioForecast(unittest.TestCase):

    def setUp(self):
        self.models, _ = train_models()
        self.features = ClimateFeatures(
            ambient_temp=28.0,
            humidity_pct=65.0,
            transit_hours=24.0,
            precooling_done=True,
            warming_delta=0.0,
        )

    def test_returns_all_scenarios(self):
        results = run_scenario_forecast(self.models, "Tomato", self.features)
        scenario_names = {r.scenario for r in results}
        self.assertEqual(scenario_names, set(WARMING_SCENARIOS.keys()))

    def test_csi_in_range(self):
        results = run_scenario_forecast(self.models, "Potato", self.features)
        for r in results:
            self.assertGreaterEqual(r.predicted_csi, 0.0)
            self.assertLessEqual(r.predicted_csi, 100.0)

    def test_yield_loss_increases_with_warming(self):
        results = run_scenario_forecast(self.models, "Onion", self.features)
        # Sort by warming delta
        sorted_r = sorted(results, key=lambda r: WARMING_SCENARIOS[r.scenario])
        losses = [r.predicted_yield_loss_pct for r in sorted_r]
        self.assertEqual(losses, sorted(losses))   # monotonically non-decreasing

    def test_forecast_result_type(self):
        results = run_scenario_forecast(self.models, "Banana", self.features)
        for r in results:
            self.assertIsInstance(r, ForecastResult)
            self.assertIn(r.spoilage_risk, ["LOW", "MEDIUM", "HIGH", "CRITICAL"])


class TestBulkForecast(unittest.TestCase):

    def setUp(self):
        self.models, _ = train_models()
        self.features = ClimateFeatures(
            ambient_temp=35.0,
            humidity_pct=80.0,
            transit_hours=48.0,
            precooling_done=False,
        )

    def test_all_commodities_returned(self):
        output = bulk_forecast(self.models, self.features)
        self.assertEqual(set(output.keys()), set(COMMODITIES))

    def test_no_precooling_increases_risk(self):
        """High temp + no precooling should produce at least some non-LOW risks."""
        output = bulk_forecast(self.models, self.features)
        all_risks = [r.spoilage_risk for c in output.values() for r in c]
        non_low = [r for r in all_risks if r != "LOW"]
        self.assertGreater(len(non_low), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
