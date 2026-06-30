"""
Kafka consumer + publisher for the scheduler service.
On `solve.completed` → compute SM-2 → upsert review_queue in Postgres.
Daily APScheduler job → scan due reviews → publish `review.due` events to Kafka.
"""
import json
import logging
import threading
import asyncio
import uuid
from datetime import date
from confluent_kafka import Consumer, Producer, KafkaError, KafkaException
from app.core.config import settings
from app.core.sm2 import SMCard, sm2_update, quality_from_time
from app.db.session import AsyncSessionLocal
from sqlalchemy import text

logger = logging.getLogger(__name__)


def _make_consumer():
    return Consumer({
        "bootstrap.servers": settings.KAFKA_BROKERS,
        "group.id": "scheduler-service-group",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": True,
    })


def _make_producer():
    return Producer({"bootstrap.servers": settings.KAFKA_BROKERS, "acks": "all"})


_producer = None

def get_producer():
    global _producer
    if _producer is None:
        _producer = _make_producer()
    return _producer


async def _upsert_review_card(user_id: str, problem_slug: str, difficulty: str, time_seconds: int):
    """Fetch or create SM-2 card and update next review date in DB."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text("SELECT ef, interval_days, repetitions FROM review_queue WHERE user_id = :uid AND problem_slug = :slug"),
            {"uid": user_id, "slug": problem_slug}
        )
        row = result.fetchone()

        if row:
            card = SMCard(
                problem_slug=problem_slug,
                user_id=user_id,
                ef=float(row.ef),
                interval=row.interval_days,
                repetitions=row.repetitions,
            )
        else:
            card = SMCard(problem_slug=problem_slug, user_id=user_id)

        quality = quality_from_time(time_seconds, difficulty)
        updated = sm2_update(card, quality)

        await db.execute(text("""
            INSERT INTO review_queue (user_id, problem_slug, ef, interval_days, repetitions, next_review_date)
            VALUES (:uid, :slug, :ef, :iv, :rep, :nrd)
            ON CONFLICT (user_id, problem_slug) DO UPDATE SET
                ef = EXCLUDED.ef,
                interval_days = EXCLUDED.interval_days,
                repetitions = EXCLUDED.repetitions,
                next_review_date = EXCLUDED.next_review_date,
                updated_at = NOW()
        """), {
            "uid": user_id, "slug": problem_slug, "ef": updated.ef,
            "iv": updated.interval, "rep": updated.repetitions,
            "nrd": updated.next_review
        })
        await db.commit()
        logger.info(f"SM-2 updated: {user_id}:{problem_slug} → next review in {updated.interval}d (EF={updated.ef:.2f})")


async def _publish_due_reviews():
    """Scan for due reviews and publish to Kafka review.due."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(text("""
            SELECT user_id, problem_slug, ef, interval_days, repetitions
            FROM review_queue
            WHERE next_review_date <= :today
            ORDER BY next_review_date ASC
            LIMIT 500
        """), {"today": date.today()})
        due = result.fetchall()

    producer = get_producer()
    count = 0
    for row in due:
        payload = {
            "event_id": str(uuid.uuid4()),
            "user_id": str(row.user_id),
            "problem_slug": row.problem_slug,
            "ef": float(row.ef),
            "interval_days": row.interval_days,
            "repetitions": row.repetitions,
        }
        producer.produce(
            "review.due",
            key=str(row.user_id).encode(),
            value=json.dumps(payload).encode(),
        )
        count += 1
    producer.flush()
    logger.info(f"Published {count} review.due events")


def run_due_review_job():
    """Called by APScheduler — bridges sync to async."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_publish_due_reviews())
    loop.close()


def run_consumer_loop():
    consumer = _make_consumer()
    consumer.subscribe(["solve.completed"])
    logger.info("Scheduler service subscribed to solve.completed")
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
                uid = event.get("user_id")
                slug = event.get("problem_slug")
                diff = event.get("difficulty", "medium")
                time_s = event.get("time_taken_seconds", 0)
                if uid and slug:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(_upsert_review_card(uid, slug, diff, time_s))
                    loop.close()
            except Exception as e:
                logger.error(f"Scheduler consumer error: {e}")
    finally:
        consumer.close()


def start_consumer_thread():
    t = threading.Thread(target=run_consumer_loop, daemon=True, name="scheduler-consumer")
    t.start()
    logger.info("Scheduler Kafka consumer thread started")
    return t
