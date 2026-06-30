"""
Kafka consumer for the progress service.
Listens on `solve.completed` events and calls the XP engine.
Then publishes to `pattern.classified` for the analytics service.
"""
import json
import logging
import threading
from confluent_kafka import Consumer, Producer, KafkaError, KafkaException
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.core.xp_engine import record_solve
import asyncio

logger = logging.getLogger(__name__)


def _make_consumer():
    return Consumer({
        "bootstrap.servers": settings.KAFKA_BROKERS,
        "group.id": "progress-service-group",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": True,
    })


def _make_producer():
    return Producer({
        "bootstrap.servers": settings.KAFKA_BROKERS,
        "acks": "all",
    })


def _sync_process_event(event: dict):
    """Bridge sync Kafka handler to async XP engine."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_process_event(event))
    finally:
        loop.close()


async def _process_event(event: dict):
    user_id = event.get("user_id")
    problem_slug = event.get("problem_slug")
    difficulty = event.get("difficulty", "medium")
    time_taken = event.get("time_taken_seconds", 0)
    language = event.get("language", "unknown")

    if not user_id or not problem_slug:
        logger.warning(f"Malformed solve.completed event: {event}")
        return

    async with AsyncSessionLocal() as db:
        result = await record_solve(db, user_id, problem_slug, difficulty, time_taken, language)
        logger.info(f"Processed solve for {user_id}: {result}")


def run_consumer_loop():
    consumer = _make_consumer()
    consumer.subscribe(["solve.completed"])
    logger.info("Progress service subscribed to solve.completed")
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
                event = json.loads(msg.value().decode("utf-8"))
                _sync_process_event(event)
            except Exception as e:
                logger.error(f"Error processing solve.completed: {e}")
    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()


def start_consumer_thread():
    t = threading.Thread(target=run_consumer_loop, daemon=True, name="progress-consumer")
    t.start()
    logger.info("Progress Kafka consumer thread started")
    return t
