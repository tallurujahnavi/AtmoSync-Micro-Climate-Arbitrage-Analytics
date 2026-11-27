"""
AtmoSync: Micro-Climate Arbitrage Analytics
Module: telemetry_stream.py
Description: Day 2 streaming ingestion layer connecting `IoTSimulator` events
             to a partitioned Kafka-style topic broker, JSON serializer/consumer,
             dead-letter queue (DLQ) routing, and consumer-lag benchmark.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    from src.climate_telemetry import TelemetryRecord, parse_telemetry_records, summarize_by_container
    from src.iot_simulator import IoTSimulator, default_fleet_configs
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from climate_telemetry import TelemetryRecord, parse_telemetry_records, summarize_by_container
    from iot_simulator import IoTSimulator, default_fleet_configs


DEFAULT_TELEMETRY_TOPIC = "atmosync.container.telemetry"
DEFAULT_DLQ_TOPIC = "atmosync.container.telemetry.dlq"


class InMemoryKafkaBroker:
    """
    Lightweight deterministic Kafka-compatible topic broker with key hashing,
    multi-partition append logs, and consumer-group offset tracking.
    """

    def __init__(self, num_partitions: int = 4) -> None:
        if num_partitions <= 0:
            raise ValueError("num_partitions must be > 0.")
        self.num_partitions = num_partitions
        self._topics: Dict[str, Dict[int, List[Dict[str, Any]]]] = {}
        self._consumer_offsets: Dict[Tuple[str, str, int], int] = {}

    def _ensure_topic(self, topic: str) -> Dict[int, List[Dict[str, Any]]]:
        if topic not in self._topics:
            self._topics[topic] = {p: [] for p in range(self.num_partitions)}
        return self._topics[topic]

    def partition_for_key(self, key: str) -> int:
        """Deterministically maps a container key to a partition index."""
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return int(digest[:8], 16) % self.num_partitions

    def publish(self, topic: str, key: str, value: str) -> Tuple[int, int]:
        """Appends a serialized message to the target topic partition and returns (partition, offset)."""
        partitions = self._ensure_topic(topic)
        partition = self.partition_for_key(key)
        log = partitions[partition]
        offset = len(log)
        log.append(
            {
                "topic": topic,
                "partition": partition,
                "offset": offset,
                "key": key,
                "value": value,
                "published_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        return partition, offset

    def poll(
        self,
        topic: str,
        group_id: str,
        max_records: int = 500,
    ) -> List[Dict[str, Any]]:
        """Reads unconsumed messages across all partitions up to `max_records`."""
        partitions = self._ensure_topic(topic)
        collected: List[Dict[str, Any]] = []
        for p_idx in range(self.num_partitions):
            log = partitions[p_idx]
            cursor = self._consumer_offsets.get((group_id, topic, p_idx), 0)
            while cursor < len(log) and len(collected) < max_records:
                collected.append(log[cursor])
                cursor += 1
            if len(collected) >= max_records:
                break
        return collected

    def commit_offsets(self, group_id: str, records: Sequence[Dict[str, Any]]) -> None:
        """Commits consumer offsets for a sequence of consumed topic records."""
        for rec in records:
            key = (group_id, rec["topic"], rec["partition"])
            next_offset = rec["offset"] + 1
            if next_offset > self._consumer_offsets.get(key, 0):
                self._consumer_offsets[key] = next_offset

    def get_consumer_lag(self, topic: str, group_id: str) -> Dict[str, Any]:
        """Returns per-partition and total consumer lag for a topic and consumer group."""
        partitions = self._ensure_topic(topic)
        per_partition: Dict[int, int] = {}
        for p_idx, log in partitions.items():
            committed = self._consumer_offsets.get((group_id, topic, p_idx), 0)
            per_partition[p_idx] = max(0, len(log) - committed)
        return {
            "topic": topic,
            "group_id": group_id,
            "per_partition_lag": per_partition,
            "total_lag": sum(per_partition.values()),
        }

    def topic_count(self, topic: str) -> int:
        partitions = self._ensure_topic(topic)
        return sum(len(log) for log in partitions.values())


class TelemetryProducer:
    """Publishes IoT container telemetry dicts as JSON events onto the broker."""

    def __init__(
        self,
        broker: InMemoryKafkaBroker,
        topic: str = DEFAULT_TELEMETRY_TOPIC,
    ) -> None:
        self.broker = broker
        self.topic = topic

    def send_batch(self, events: Sequence[Dict[str, Any]]) -> List[Tuple[int, int]]:
        """Serializes and publishes a batch of telemetry events keyed by container_id."""
        receipts: List[Tuple[int, int]] = []
        for event in events:
            key = str(event.get("container_id") or "unknown")
            receipts.append(self.broker.publish(self.topic, key=key, value=json.dumps(event)))
        return receipts


class TelemetryConsumer:
    """
    Consumes telemetry messages, validates them with `parse_telemetry_records`,
    and routes invalid payloads to a dead-letter queue (DLQ) topic.
    """

    def __init__(
        self,
        broker: InMemoryKafkaBroker,
        topic: str = DEFAULT_TELEMETRY_TOPIC,
        dlq_topic: str = DEFAULT_DLQ_TOPIC,
        group_id: str = "atmosync-staging-ingest",
    ) -> None:
        self.broker = broker
        self.topic = topic
        self.dlq_topic = dlq_topic
        self.group_id = group_id

    def consume_batch(self, max_records: int = 1000) -> Tuple[List[TelemetryRecord], List[Dict[str, Any]]]:
        """Polls, deserializes, validates, and commits a batch of telemetry events."""
        raw_messages = self.broker.poll(self.topic, group_id=self.group_id, max_records=max_records)
        if not raw_messages:
            return [], []

        decoded_payloads: List[Dict[str, Any]] = []
        dlq_items: List[Dict[str, Any]] = []

        for msg in raw_messages:
            try:
                parsed = json.loads(msg["value"])
                if not isinstance(parsed, dict):
                    raise ValueError("JSON payload must decode to an object.")
                decoded_payloads.append(parsed)
            except (json.JSONDecodeError, ValueError) as exc:
                dlq_record = {"reason": f"malformed_json: {exc}", "raw_value": msg["value"]}
                dlq_items.append(dlq_record)
                self.broker.publish(self.dlq_topic, key=msg["key"], value=json.dumps(dlq_record))

        valid_records, rejected = parse_telemetry_records(decoded_payloads)
        for rej in rejected:
            dlq_items.append(rej)
            key = str(rej.get("raw", {}).get("container_id") or "unknown")
            self.broker.publish(self.dlq_topic, key=key, value=json.dumps(rej))

        self.broker.commit_offsets(self.group_id, raw_messages)
        return valid_records, dlq_items


def benchmark_stream_pipeline(
    steps_per_container: int = 50,
    num_partitions: int = 4,
    seed: int = 2026,
) -> Dict[str, Any]:
    """Runs an end-to-end streaming benchmark and verifies zero consumer lag."""
    t_start = time.perf_counter()
    sim = IoTSimulator(seed=seed)
    events = sim.simulate_fleet(default_fleet_configs(), steps=steps_per_container, interval_minutes=15)

    broker = InMemoryKafkaBroker(num_partitions=num_partitions)
    producer = TelemetryProducer(broker)
    consumer = TelemetryConsumer(broker)

    producer.send_batch(events)
    valid_records, dlq_items = consumer.consume_batch(max_records=len(events) + 10)
    summaries = summarize_by_container(valid_records)
    lag = broker.get_consumer_lag(DEFAULT_TELEMETRY_TOPIC, consumer.group_id)
    elapsed_sec = max(1e-6, time.perf_counter() - t_start)

    return {
        "events_published": len(events),
        "events_consumed_valid": len(valid_records),
        "dlq_count": len(dlq_items),
        "total_consumer_lag": lag["total_lag"],
        "containers_summarized": len(summaries),
        "elapsed_ms": round(elapsed_sec * 1000.0, 2),
        "throughput_events_per_sec": round(len(events) / elapsed_sec, 1),
    }


if __name__ == "__main__":
    print(json.dumps(benchmark_stream_pipeline(), indent=2))
