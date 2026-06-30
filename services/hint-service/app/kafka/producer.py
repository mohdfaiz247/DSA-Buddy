"""
Hint Service Kafka helpers — publishes hint.requested events and
subscribes to hint.ready to cache results back for HTTP polling.
"""
import json
import logging
import threading
import uuid
from confluent_kafka import Consumer, Producer, KafkaError, KafkaException
import redis as redis_lib
from app.core.config import settings

logger = logging.getLogger(__name__)

_producer = None


def get_producer() -> Producer:
    global _producer
    if _producer is None:
        _producer = Producer({
            "bootstrap.servers": settings.KAFKA_BROKERS,
            "acks": "all",
            "retries": 5,
        })
    return _producer


def publish_hint_request(
    user_id: str,
    problem_slug: str,
    problem_title: str,
    difficulty: str,
    tags: list,
    hint_level: int,
) -> str:
    """Returns event_id for correlation."""
    event_id = str(uuid.uuid4())
    payload = {
        "event_id": event_id,
        "user_id": user_id,
        "problem_slug": problem_slug,
        "problem_title": problem_title,
        "difficulty": difficulty,
        "tags": tags,
        "hint_level": hint_level,
    }
    get_producer().produce(
        settings.KAFKA_BROKERS.split(",")[0],  # not needed — topic below
        topic="hint.requested",
        key=user_id.encode(),
        value=json.dumps(payload).encode(),
    )
    get_producer().poll(0)
    logger.info(f"Published hint.requested: {event_id}")
    return event_id


def publish_hint_request_v2(
    user_id: str,
    problem_slug: str,
    problem_title: str,
    difficulty: str,
    tags: list,
    hint_level: int,
    user_code: str = "",
) -> str:
    event_id = str(uuid.uuid4())
    payload = {
        "event_id": event_id,
        "user_id": user_id,
        "problem_slug": problem_slug,
        "problem_title": problem_title,
        "difficulty": difficulty,
        "tags": tags,
        "hint_level": hint_level,
        "user_code": user_code,
    }
    p = get_producer()
    p.produce(
        "hint.requested",
        key=user_id.encode(),
        value=json.dumps(payload).encode(),
    )
    p.poll(0)
    logger.info(f"Published hint.requested event_id={event_id} for {user_id}:{problem_slug}")
    return event_id


def run_hint_ready_consumer():
    """
    Subscribes to hint.ready and caches results in Redis so the HTTP
    polling endpoint can return them without waiting on Kafka directly.
    """
    r = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
    consumer = Consumer({
        "bootstrap.servers": settings.KAFKA_BROKERS,
        "group.id": "hint-service-ready-group",
        "auto.offset.reset": "latest",
        "enable.auto.commit": True,
    })
    consumer.subscribe(["hint.ready"])
    logger.info("Hint service subscribed to hint.ready")
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
                event_id = event.get("event_id")
                hints = event.get("hints", [])
                if event_id and hints:
                    # Cache by event_id for 5 minutes
                    r.setex(f"hint_ready:{event_id}", 300, json.dumps(hints))
                    logger.info(f"Cached hint.ready for event_id={event_id}")
            except Exception as e:
                logger.error(f"hint.ready consumer error: {e}")
    finally:
        consumer.close()


def start_hint_ready_thread():
    t = threading.Thread(target=run_hint_ready_consumer, daemon=True, name="hint-ready-consumer")
    t.start()
    return t
