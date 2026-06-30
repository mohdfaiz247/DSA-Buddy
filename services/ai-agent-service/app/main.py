"""
AI Agent Service entry point.

Starts:
  1. A background Kafka consumer thread that processes hint.requested events
     through the LangGraph pipeline and publishes results to hint.ready.
  2. A lightweight FastAPI health + manual trigger endpoint for testing.
"""
import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.kafka.consumer import start_consumer_thread
from app.kafka.publisher import publish_hint_request
from app.tools.redis_cache import redis_cache
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI Agent Service…")
    logger.info(f"  Kafka:   {settings.KAFKA_BROKERS}")
    logger.info(f"  Redis:   {settings.REDIS_URL}")
    logger.info(f"  Neo4j:   {settings.NEO4J_URI}")
    logger.info(f"  LLM:     {settings.LLM_MODEL} (key={'set' if settings.GEMINI_API_KEY else 'NOT SET - fallback mode'})")

    # Start background Kafka consumer
    start_consumer_thread()

    yield

    logger.info("AI Agent Service shutting down…")


app = FastAPI(title="DSA Buddy — AI Agent Service", lifespan=lifespan)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "ai-agent",
        "llm_model": settings.LLM_MODEL,
        "gemini_configured": bool(settings.GEMINI_API_KEY),
    }


class HintTriggerRequest(BaseModel):
    user_id: str
    problem_slug: str
    problem_title: str
    difficulty: str = "medium"
    tags: list[str] = []
    hint_level: int = 3


@app.post("/trigger-hint")
async def trigger_hint(body: HintTriggerRequest):
    """
    Manually trigger the hint generation pipeline by publishing to Kafka.
    Useful for testing without a running extension.
    """
    event_id = publish_hint_request(
        user_id=body.user_id,
        problem_slug=body.problem_slug,
        problem_title=body.problem_title,
        difficulty=body.difficulty,
        tags=body.tags,
        hint_level=body.hint_level,
    )
    return {"event_id": event_id, "status": "queued"}


@app.get("/cached-hints/{user_id}/{problem_slug}")
def get_cached_hints(user_id: str, problem_slug: str):
    """Retrieve cached hints from Redis for a user+problem."""
    hints = redis_cache.get_hints(user_id, problem_slug)
    if hints is None:
        raise HTTPException(status_code=404, detail="No cached hints found")
    return {"hints": hints, "cached": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8005, log_level="info")
