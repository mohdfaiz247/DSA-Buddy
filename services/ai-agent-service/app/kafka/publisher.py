"""
Kafka publisher helpers — sends hint.requested events to trigger the AI pipeline.
Used by the hint-service / API gateway when a user requests a hint.
"""
import json
import logging
import uuid
from confluent_kafka import Producer
from app.core.config import settings

logger = logging.getLogger(__name__)

_producer: Producer | None = None


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
    tags: list[str],
    hint_level: int = 3,
) -> str:
    """Publish a hint.requested event. Returns the event_id for correlation."""
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
    producer = get_producer()
    producer.produce(
        settings.TOPIC_HINT_REQUESTED,
        key=user_id.encode(),
        value=json.dumps(payload).encode(),
    )
    producer.poll(0)
    logger.info(f"Published hint.requested event {event_id} for {user_id}:{problem_slug}")
    return event_id


def publish_solve_completed(user_id: str, problem_slug: str, time_taken_seconds: int, language: str) -> None:
    """Publish a solve.completed event for XP/streak tracking."""
    payload = {
        "event_id": str(uuid.uuid4()),
        "user_id": user_id,
        "problem_slug": problem_slug,
        "time_taken_seconds": time_taken_seconds,
        "language": language,
    }
    producer = get_producer()
    producer.produce(
        "solve.completed",
        key=user_id.encode(),
        value=json.dumps(payload).encode(),
    )
    producer.poll(0)
    logger.info(f"Published solve.completed for {user_id}:{problem_slug}")
