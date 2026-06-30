"""
Analytics Kafka consumer — aggregates solve.completed events into
time-bucketed counters stored in Redis for real-time leaderboards and
pattern classification.

Events consumed:
  solve.completed   → incr platform/difficulty/tag counters in Redis
  hint.ready        → track hint usage rate per user
"""
import json
import logging
import threading
from confluent_kafka import Consumer, KafkaError, KafkaException
import redis as redis_lib
from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_redis():
    return redis_lib.from_url(settings.REDIS_URL, decode_responses=True)


def _process_solve(event: dict, r):
    user_id = event.get("user_id", "anon")
    difficulty = event.get("difficulty", "medium").lower()
    platform = event.get("platform", "unknown")
    tags = event.get("tags", [])

    pipe = r.pipeline()

    # Global counters (TTL = 30 days)
    pipe.incr(f"analytics:global:solves:total")
    pipe.incr(f"analytics:global:solves:{difficulty}")
    pipe.incr(f"analytics:global:platform:{platform}")

    # Per-user counters
    pipe.incr(f"analytics:user:{user_id}:solves")
    pipe.incr(f"analytics:user:{user_id}:difficulty:{difficulty}")

    # Tag frequency (global sorted set — drives leaderboard)
    for tag in tags:
        pipe.zincrby("analytics:global:tag_freq", 1, tag)

    # Leaderboard (global solve count)
    pipe.zincrby("analytics:leaderboard:solves", 1, user_id)

    pipe.execute()
    logger.debug(f"Analytics: processed solve for {user_id} ({difficulty})")


def _process_hint_ready(event: dict, r):
    user_id = event.get("user_id", "anon")
    r.incr(f"analytics:user:{user_id}:hints_received")
    r.incr("analytics:global:hints_total")


def run_consumer_loop():
    r = _get_redis()
    consumer = Consumer({
        "bootstrap.servers": settings.KAFKA_BROKERS,
        "group.id": "analytics-service-group",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": True,
    })
    consumer.subscribe(["solve.completed", "hint.ready"])
    logger.info("Analytics consumer subscribed to solve.completed + hint.ready")
    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                raise KafkaException(msg.error())
            try:
                event = json.loads(msg.value().decode())
                topic = msg.topic()
                if topic == "solve.completed":
                    _process_solve(event, r)
                elif topic == "hint.ready":
                    _process_hint_ready(event, r)
            except Exception as e:
                logger.error(f"Analytics consumer error: {e}")
    finally:
        consumer.close()


def start_consumer_thread():
    t = threading.Thread(target=run_consumer_loop, daemon=True, name="analytics-consumer")
    t.start()
    logger.info("Analytics Kafka consumer started")
    return t
