"""
test_profiler.py – Unit tests for performance profiling, latency SLAs, and cache tracker.
"""

import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import unittest
from profiler import (
    timed_execution,
    LatencyRegistry,
    GLOBAL_LATENCY_REGISTRY,
    LRUCacheTracker,
    audit_pipeline_sla_benchmarks,
    ProfiledMetric,
)


class TestProfiler(unittest.TestCase):

    def setUp(self):
        GLOBAL_LATENCY_REGISTRY.clear()

    def test_timed_execution_decorator(self):
        @timed_execution(sla_threshold_ms=50.0, operation_name="fast_calc")
        def sample_fast():
            return 42 * 2

        val = sample_fast()
        self.assertEqual(val, 84)

        metrics = GLOBAL_LATENCY_REGISTRY.get_metrics()
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0].operation_name, "fast_calc")
        self.assertTrue(metrics[0].sla_compliant)
        self.assertLess(metrics[0].execution_time_ms, 50.0)

    def test_timed_execution_sla_breach(self):
        @timed_execution(sla_threshold_ms=1.0, operation_name="slow_op")
        def sample_slow():
            time.sleep(0.005)  # 5ms > 1ms SLA
            return "done"

        sample_slow()
        metrics = GLOBAL_LATENCY_REGISTRY.get_metrics()
        self.assertEqual(len(metrics), 1)
        self.assertFalse(metrics[0].sla_compliant)

    def test_latency_registry_summary(self):
        registry = LatencyRegistry()
        registry.record(ProfiledMetric("op1", 10.0, 0.0, 20.0, True))
        registry.record(ProfiledMetric("op2", 30.0, 0.0, 20.0, False))

        summary = registry.get_summary()
        self.assertEqual(summary["total_operations"], 2)
        self.assertEqual(summary["mean_latency_ms"], 20.0)
        self.assertEqual(summary["sla_compliance_rate_pct"], 50.0)

    def test_lru_cache_tracker(self):
        tracker = LRUCacheTracker("geospatial_cache")
        tracker.record_hit()
        tracker.record_hit()
        tracker.record_miss()

        self.assertEqual(tracker.hits, 2)
        self.assertEqual(tracker.misses, 1)
        self.assertEqual(tracker.total_requests, 3)
        self.assertAlmostEqual(tracker.hit_ratio_pct, 66.7, places=1)

    def test_audit_pipeline_sla_benchmarks(self):
        bench = audit_pipeline_sla_benchmarks(num_runs=10)
        self.assertIn("kinetics_avg_latency_ms", bench)
        self.assertIn("geospatial_avg_latency_ms", bench)
        self.assertTrue(bench["kinetics_sla_compliant"])
        self.assertTrue(bench["geospatial_sla_compliant"])
        self.assertEqual(bench["system_status"], "HIGH_THROUGHPUT_READY")


if __name__ == "__main__":
    unittest.main(verbosity=2)
