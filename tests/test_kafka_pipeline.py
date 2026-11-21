"""
Unit tests for src/kafka_pipeline.py
Validates Apache Kafka mock topic buffer, producer batch generation,
consumer drain speed, consumer lag monitoring, and pipeline benchmark SLA.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kafka_pipeline import (
    MockKafkaTopic,
    KafkaContainerProducer,
    KafkaStreamConsumer,
    run_pipeline_benchmark,
)


def test_kafka_topic_publish_consume():
    topic = MockKafkaTopic("test-topic")
    assert topic.lag == 0

    # Publish 10 messages
    for i in range(10):
        topic.publish({"test_id": i})

    assert topic.lag == 10
    batch = topic.consume(batch_size=4)
    assert len(batch) == 4
    assert topic.lag == 6

    # Consume remaining
    remaining = topic.consume(batch_size=10)
    assert len(remaining) == 6
    assert topic.lag == 0


def test_producer_consumer_pipeline():
    topic = MockKafkaTopic("container-telemetry-stream")
    producer = KafkaContainerProducer(topic)
    consumer = KafkaStreamConsumer(topic)

    offsets = producer.produce_batch(num_containers=8)
    assert len(offsets) == 8
    assert topic.lag == 8

    stat = consumer.poll_and_land(batch_size=100)
    assert stat["batch_size"] == 8
    assert stat["consumer_lag"] == 0
    assert consumer.total_processed == 8


def test_pipeline_benchmark_zero_lag():
    benchmark_result = run_pipeline_benchmark(events_to_stream=200)
    assert benchmark_result["status"] == "PASSED_ZERO_LAG"
    assert benchmark_result["events_streamed"] == 200
    assert benchmark_result["events_landed_in_dwh"] == 200
    assert benchmark_result["final_consumer_lag"] == 0
    assert benchmark_result["overall_throughput_events_per_sec"] > 500.0


if __name__ == "__main__":
    test_kafka_topic_publish_consume()
    test_producer_consumer_pipeline()
    test_pipeline_benchmark_zero_lag()
    print("All Kafka Streaming Pipeline tests passed successfully!")
