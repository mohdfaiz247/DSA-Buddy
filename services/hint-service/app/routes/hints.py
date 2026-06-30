"""
Hint Service REST routes.

POST /request    — publish hint.requested to Kafka, return event_id
GET  /poll/{id}  — poll Redis for hint.ready result by event_id
GET  /cached     — get cached hints from Redis by user+slug (from AI agent cache)
"""
import asyncio
import json
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import redis.asyncio as aioredis

from app.core.config import settings
from app.kafka.producer import publish_hint_request_v2

logger = logging.getLogger(__name__)
router = APIRouter()


class HintRequest(BaseModel):
    user_id: str
    problem_slug: str
    problem_title: str
    difficulty: str = "medium"
    tags: list[str] = []
    hint_level: int = 3
    user_code: str = ""  # current code from the editor (optional)


@router.post("/request")
async def request_hints(body: HintRequest):
    """
    Publish hint.requested event to Kafka.
    Returns event_id for the client to poll with.
    """
    event_id = publish_hint_request_v2(
        user_id=body.user_id,
        problem_slug=body.problem_slug,
        problem_title=body.problem_title,
        difficulty=body.difficulty,
        tags=body.tags,
        hint_level=body.hint_level,
        user_code=body.user_code,
    )
    return {
        "event_id": event_id,
        "status": "queued",
        "poll_url": f"/hints/poll/{event_id}",
    }


@router.get("/poll/{event_id}")
async def poll_hints(event_id: str):
    """
    Long-poll for hint.ready result by event_id.
    Returns hints if available, or {status: pending} if still processing.
    """
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        # Poll with exponential backoff for up to 10 seconds
        for attempt in range(settings.HINT_CACHE_MAX_POLLS):
            raw = await r.get(f"hint_ready:{event_id}")
            if raw:
                hints = json.loads(raw)
                return {"status": "ready", "hints": hints, "event_id": event_id}
            await asyncio.sleep(settings.HINT_CACHE_POLL_INTERVAL)
        return {"status": "pending", "hints": [], "event_id": event_id}
    finally:
        await r.aclose()


@router.get("/cached/{user_id}/{problem_slug}")
async def get_cached_hints(user_id: str, problem_slug: str):
    """
    Return cached hints from the AI agent's Redis cache (keyed by user+slug).
    This is the fast path — no Kafka roundtrip needed if hints are cached.
    """
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        raw = await r.get(f"hints:{user_id}:{problem_slug}")
        if not raw:
            raise HTTPException(status_code=404, detail="No cached hints")
        hints = json.loads(raw)
        return {"hints": hints, "cached": True, "user_id": user_id, "problem_slug": problem_slug}
    finally:
        await r.aclose()


@router.post("/solve-complete")
async def mark_solved(body: dict):
    """
    Record a solve completion — publishes to solve.completed Kafka topic.
    Progress service and scheduler service both consume this event.
    """
    import uuid
    from confluent_kafka import Producer
    p = Producer({"bootstrap.servers": settings.KAFKA_BROKERS})
    payload = {
        "event_id": str(uuid.uuid4()),
        "user_id": body.get("user_id"),
        "problem_slug": body.get("problem_slug"),
        "difficulty": body.get("difficulty", "medium"),
        "time_taken_seconds": body.get("time_taken_seconds", 0),
        "language": body.get("language", "unknown"),
        "platform": body.get("platform", "leetcode"),
        "tags": body.get("tags", []),
        "user_code": body.get("user_code", ""),
    }
    p.produce("solve.completed", key=payload["user_id"].encode(), value=json.dumps(payload).encode())
    p.flush()
    return {"status": "recorded", "event_id": payload["event_id"]}

@router.get("/review/{user_id}/{problem_slug}")
async def get_review(user_id: str, problem_slug: str):
    """
    Polls Redis for the AI-generated Post-Solve Code Review.
    """
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        raw = await r.get(f"review:{user_id}:{problem_slug}")
        if raw:
            review = json.loads(raw)
            return {"status": "ready", "review": review}
        return {"status": "pending"}
    finally:
        await r.aclose()
