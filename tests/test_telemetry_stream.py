"""
Unit tests for Day 2 partitioned telemetry stream producer, consumer, DLQ,
and consumer-lag benchmark (`src/telemetry_stream.py`).
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from telemetry_stream import (
    DEFAULT_DLQ_TOPIC,
    DEFAULT_TELEMETRY_TOPIC,
    InMemoryKafkaBroker,
    TelemetryConsumer,
    TelemetryProducer,
    benchmark_stream_pipeline,
)


class TestTelemetryStream(unittest.TestCase):
    def test_key_partitioning_is_deterministic(self):
        broker = InMemoryKafkaBroker(num_partitions=4)
        p1 = broker.partition_for_key("CNT-AVO-01")
        p2 = broker.partition_for_key("CNT-AVO-01")
        self.assertEqual(p1, p2)
        self.assertTrue(0 <= p1 < 4)

    def test_producer_consumer_roundtrip_and_zero_lag(self):
        broker = InMemoryKafkaBroker(num_partitions=3)
        producer = TelemetryProducer(broker)
        consumer = TelemetryConsumer(broker)

        events = [
            {
                "event_id": "E-1",
                "container_id": "CNT-10",
                "timestamp": "2026-11-27T10:00:00",
                "temperature_c": 5.5,
                "humidity_pct": 90.0,
                "commodity": "Avocado",
            },
            {
                "event_id": "E-2",
                "container_id": "CNT-20",
                "timestamp": "2026-11-27T10:15:00",
                "temperature_c": 13.5,
                "humidity_pct": 92.0,
                "commodity": "Banana",
            },
        ]
        producer.send_batch(events)
        self.assertEqual(broker.get_consumer_lag(DEFAULT_TELEMETRY_TOPIC, consumer.group_id)["total_lag"], 2)

        valid, dlq = consumer.consume_batch()
        self.assertEqual(len(valid), 2)
        self.assertEqual(len(dlq), 0)
        self.assertEqual(broker.get_consumer_lag(DEFAULT_TELEMETRY_TOPIC, consumer.group_id)["total_lag"], 0)

    def test_invalid_json_and_out_of_bounds_route_to_dlq(self):
        broker = InMemoryKafkaBroker(num_partitions=2)
        consumer = TelemetryConsumer(broker)

        broker.publish(DEFAULT_TELEMETRY_TOPIC, key="CNT-BAD", value="{not-valid-json")
        broker.publish(
            DEFAULT_TELEMETRY_TOPIC,
            key="CNT-BAD",
            value=json.dumps({
                "container_id": "CNT-BAD",
                "timestamp": "2026-11-27T10:00:00",
                "temperature_c": 250.0,
                "humidity_pct": 85.0,
            }),
        )
        broker.publish(
            DEFAULT_TELEMETRY_TOPIC,
            key="CNT-GOOD",
            value=json.dumps({
                "container_id": "CNT-GOOD",
                "timestamp": "2026-11-27T10:00:00",
                "temperature_c": 6.0,
                "humidity_pct": 89.0,
                "commodity": "Avocado",
            }),
        )

        valid, dlq = consumer.consume_batch()
        self.assertEqual(len(valid), 1)
        self.assertEqual(valid[0].container_id, "CNT-GOOD")
        self.assertEqual(len(dlq), 2)
        self.assertEqual(broker.topic_count(DEFAULT_DLQ_TOPIC), 2)

    def test_stream_benchmark_completes_with_zero_lag(self):
        metrics = benchmark_stream_pipeline(steps_per_container=25, num_partitions=4, seed=2026)
        self.assertEqual(metrics["events_published"], 100)
        self.assertEqual(metrics["events_consumed_valid"], 100)
        self.assertEqual(metrics["dlq_count"], 0)
        self.assertEqual(metrics["total_consumer_lag"], 0)
        self.assertEqual(metrics["containers_summarized"], 4)
        self.assertGreater(metrics["throughput_events_per_sec"], 0.0)


if __name__ == "__main__":
    unittest.main()
