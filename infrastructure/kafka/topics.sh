#!/bin/sh

echo "Waiting for Kafka to be ready..."
sleep 15

echo "Creating topics..."
kafka-topics --create --if-not-exists --bootstrap-server localhost:9092 --topic solve.completed --partitions 3 --replication-factor 1
kafka-topics --create --if-not-exists --bootstrap-server localhost:9092 --topic hint.requested --partitions 3 --replication-factor 1
kafka-topics --create --if-not-exists --bootstrap-server localhost:9092 --topic hint.ready --partitions 3 --replication-factor 1
kafka-topics --create --if-not-exists --bootstrap-server localhost:9092 --topic timer.tick --partitions 1 --replication-factor 1
kafka-topics --create --if-not-exists --bootstrap-server localhost:9092 --topic review.due --partitions 1 --replication-factor 1
kafka-topics --create --if-not-exists --bootstrap-server localhost:9092 --topic pattern.classified --partitions 3 --replication-factor 1

echo "Topics created successfully."
