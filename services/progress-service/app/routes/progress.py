from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter()

@router.get("/stats/{user_id}")
async def get_user_stats(user_id: str, db: AsyncSession = Depends(get_db)):
    user_result = await db.execute(
        text("SELECT username, xp, level, streak_days, last_active FROM users WHERE id = :uid"),
        {"uid": user_id}
    )
    user = user_result.fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Solve counts by difficulty
    counts = await db.execute(text("""
        SELECT p.difficulty, COUNT(*) as cnt
        FROM solves s
        JOIN problems p ON s.problem_slug = p.slug
        WHERE s.user_id = :uid
        GROUP BY p.difficulty
    """), {"uid": user_id})
    difficulty_counts = {row.difficulty: row.cnt for row in counts}

    # Weekly activity (last 7 days)
    activity = await db.execute(text("""
        SELECT date, problems_solved, xp_earned
        FROM daily_activity
        WHERE user_id = :uid
        ORDER BY date DESC
        LIMIT 7
    """), {"uid": user_id})
    weekly = [{"date": str(r.date), "solved": r.problems_solved, "xp": r.xp_earned} for r in activity]

    # Total solves
    total = await db.execute(
        text("SELECT COUNT(*) as cnt FROM solves WHERE user_id = :uid"), {"uid": user_id}
    )
    total_solves = total.fetchone().cnt or 0

    return {
        "username": user.username,
        "xp": user.xp,
        "level": user.level,
        "streak_days": user.streak_days,
        "last_active": str(user.last_active) if user.last_active else None,
        "total_solves": total_solves,
        "by_difficulty": difficulty_counts,
        "weekly_activity": weekly,
    }

@router.get("/solves/{user_id}")
async def get_recent_solves(user_id: str, limit: int = 20, db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("""
        SELECT s.problem_slug, s.solved_at, s.time_taken_seconds, s.language, s.earned_xp
        FROM solves s
        WHERE s.user_id = :uid
        ORDER BY s.solved_at DESC
        LIMIT :limit
    """), {"uid": user_id, "limit": limit})
    return [
        {
            "problem_slug": r.problem_slug,
            "solved_at": str(r.solved_at),
            "time_taken_seconds": r.time_taken_seconds,
            "language": r.language,
            "earned_xp": r.earned_xp,
        }
        for r in result
    ]

from pydantic import BaseModel
from typing import List

class SyncRequest(BaseModel):
    user_id: str
    solved_slugs: List[str]

@router.post("/sync")
async def sync_leetcode_solves(payload: SyncRequest, db: AsyncSession = Depends(get_db)):
    if not payload.solved_slugs:
        return {"synced": 0}

    # Fetch existing solves so we don't insert duplicates
    existing = await db.execute(
        text("SELECT problem_slug FROM solves WHERE user_id = :uid"),
        {"uid": payload.user_id}
    )
    existing_slugs = {row.problem_slug for row in existing.fetchall()}

    new_slugs = [s for s in payload.solved_slugs if s not in existing_slugs]
    if not new_slugs:
        return {"synced": 0}

    # We also need to make sure the problem actually exists in our problems table
    # to avoid Foreign Key constraint violations.
    valid_problems = await db.execute(
        text("SELECT slug FROM problems WHERE slug = ANY(:slugs)"),
        {"slugs": new_slugs}
    )
    valid_slugs = {row.slug for row in valid_problems.fetchall()}
    
    to_insert = [s for s in new_slugs if s in valid_slugs]
    if not to_insert:
        return {"synced": 0}

    # Insert with a very old solved_at date so they don't count towards
    # today's streak or daily xp.
    insert_query = text("""
        INSERT INTO solves (user_id, problem_slug, solved_at, language, earned_xp)
        VALUES (:uid, :slug, '2000-01-01 00:00:00+00', 'unknown', 0)
    """)
    
    # Executemany equivalent in async SQLAlchemy
    await db.execute(
        text("""
        INSERT INTO solves (user_id, problem_slug, solved_at, language, earned_xp)
        SELECT :uid, slug, '2000-01-01 00:00:00+00', 'unknown', 0
        FROM UNNEST(CAST(:slugs AS text[])) AS slug
        """),
        {"uid": payload.user_id, "slugs": to_insert}
    )
    await db.commit()

    return {"synced": len(to_insert)}

