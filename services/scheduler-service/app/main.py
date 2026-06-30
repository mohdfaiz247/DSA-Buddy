from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import date
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.kafka.consumer import start_consumer_thread, run_due_review_job
from app.db.session import get_db
from app.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_consumer_thread()

    # Daily job at 9am to publish review.due events
    scheduler.add_job(run_due_review_job, "cron", hour=settings.REVIEW_NOTIFY_HOUR, minute=0)
    # Also run immediately on startup (to catch any from today)
    scheduler.add_job(run_due_review_job, "interval", minutes=60)
    scheduler.start()
    logger.info("APScheduler started for daily review.due publishing")
    yield
    scheduler.shutdown()


app = FastAPI(title="DSA Buddy — Scheduler Service", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health():
    return {"status": "ok", "service": "scheduler"}


@app.get("/due/{user_id}")
async def get_due_reviews(user_id: str, db: AsyncSession = Depends(get_db)):
    """Return problems due for review for a given user."""
    result = await db.execute(text("""
        SELECT rq.problem_slug, rq.next_review_date, rq.ef, rq.interval_days, rq.repetitions,
               p.title, p.difficulty
        FROM review_queue rq
        LEFT JOIN problems p ON rq.problem_slug = p.slug
        WHERE rq.user_id = :uid AND rq.next_review_date <= :today
        ORDER BY rq.next_review_date ASC
        LIMIT 20
    """), {"uid": user_id, "today": date.today()})

    return [
        {
            "problem_slug": r.problem_slug,
            "title": r.title or r.problem_slug.replace("-", " ").title(),
            "difficulty": r.difficulty or "medium",
            "next_review_date": str(r.next_review_date),
            "ef": float(r.ef),
            "interval_days": r.interval_days,
            "repetitions": r.repetitions,
        }
        for r in result
    ]


@app.get("/queue/{user_id}")
async def get_full_queue(user_id: str, db: AsyncSession = Depends(get_db)):
    """Return the full review queue (upcoming + due)."""
    result = await db.execute(text("""
        SELECT rq.problem_slug, rq.next_review_date, rq.ef, rq.interval_days, rq.repetitions,
               p.title, p.difficulty
        FROM review_queue rq
        LEFT JOIN problems p ON rq.problem_slug = p.slug
        WHERE rq.user_id = :uid
        ORDER BY rq.next_review_date ASC
        LIMIT 50
    """), {"uid": user_id})

    today = date.today()
    return [
        {
            "problem_slug": r.problem_slug,
            "title": r.title or r.problem_slug,
            "difficulty": r.difficulty or "medium",
            "next_review_date": str(r.next_review_date),
            "is_due": r.next_review_date <= today,
            "ef": float(r.ef),
            "interval_days": r.interval_days,
        }
        for r in result
    ]
