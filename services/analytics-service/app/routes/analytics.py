from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import date, timedelta
import redis as redis_lib
from app.core.config import settings
from app.core.db import get_db

router = APIRouter()

def get_redis():
    return redis_lib.from_url(settings.REDIS_URL, decode_responses=True)


@router.get("/overview")
async def global_overview(db: AsyncSession = Depends(get_db)):
    """Global platform stats — total users, solves, and breakdowns."""
    r = get_redis()

    total_solves = int(r.get("analytics:global:solves:total") or 0)
    easy = int(r.get("analytics:global:solves:easy") or 0)
    medium = int(r.get("analytics:global:solves:medium") or 0)
    hard = int(r.get("analytics:global:solves:hard") or 0)
    hints_total = int(r.get("analytics:global:hints_total") or 0)

    # Top tags from Redis ZSET
    top_tags = r.zrevrange("analytics:global:tag_freq", 0, 9, withscores=True)

    # DB user count
    result = await db.execute(text("SELECT COUNT(*) as cnt FROM users"))
    user_count = result.fetchone().cnt or 0

    return {
        "total_users": user_count,
        "total_solves": total_solves,
        "hints_requested": hints_total,
        "by_difficulty": {"easy": easy, "medium": medium, "hard": hard},
        "top_tags": [{"tag": t, "count": int(s)} for t, s in top_tags],
    }


@router.get("/leaderboard")
def leaderboard(limit: int = 10):
    """Top solvers sorted by total solve count."""
    r = get_redis()
    entries = r.zrevrange("analytics:leaderboard:solves", 0, limit - 1, withscores=True)
    return [
        {"user_id": uid, "rank": i + 1, "total_solves": int(score)}
        for i, (uid, score) in enumerate(entries)
    ]


@router.get("/heatmap/{user_id}")
async def heatmap(user_id: str, days: int = 90, db: AsyncSession = Depends(get_db)):
    """Activity heatmap data for the last N days."""
    start_date = date.today() - timedelta(days=days)
    result = await db.execute(text("""
        SELECT date, problems_solved, xp_earned
        FROM daily_activity
        WHERE user_id = :uid AND date >= :start
        ORDER BY date ASC
    """), {"uid": user_id, "start": start_date})

    return [
        {"date": str(r.date), "count": r.problems_solved, "xp": r.xp_earned}
        for r in result
    ]


@router.get("/patterns/{user_id}")
async def user_patterns(user_id: str, db: AsyncSession = Depends(get_db)):
    """Which DSA patterns has this user solved most? Based on problem tags."""
    result = await db.execute(text("""
        SELECT unnest(p.tags) AS tag, COUNT(*) AS cnt
        FROM solves s
        JOIN problems p ON s.problem_slug = p.slug
        WHERE s.user_id = :uid
        GROUP BY tag
        ORDER BY cnt DESC
        LIMIT 10
    """), {"uid": user_id})

    return [{"tag": r.tag, "count": int(r.cnt)} for r in result]


@router.get("/velocity/{user_id}")
async def solve_velocity(user_id: str, db: AsyncSession = Depends(get_db)):
    """Weekly solve counts for the last 8 weeks — shows momentum."""
    result = await db.execute(text("""
        SELECT
            DATE_TRUNC('week', date) AS week_start,
            SUM(problems_solved) AS solves,
            SUM(xp_earned) AS xp
        FROM daily_activity
        WHERE user_id = :uid
          AND date >= CURRENT_DATE - INTERVAL '56 days'
        GROUP BY week_start
        ORDER BY week_start ASC
    """), {"uid": user_id})

    return [
        {"week": str(r.week_start)[:10], "solves": int(r.solves or 0), "xp": int(r.xp or 0)}
        for r in result
    ]
