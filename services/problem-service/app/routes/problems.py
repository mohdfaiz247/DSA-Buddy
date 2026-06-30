from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text
import random

from app.db.session import get_db
from app.services.trie_index import problem_trie

router = APIRouter()

@router.get("/search")
async def search_problems(q: str):
    if not q:
        return []
    return problem_trie.search(q)


@router.get("/recommend/{user_id}")
async def recommend_problems(user_id: str, db: AsyncSession = Depends(get_db)):
    """
    Return 5 randomly selected unsolved problems for a user: 1 easy, 3 medium, 1 hard.
    Problems the user already solved are excluded.
    """
    from datetime import date
    today_str = date.today().isoformat()

    async def _fetch(difficulty: str, limit: int) -> list:
        # We use MD5 of (slug + user_id + date) to generate a stable random shuffle
        # for this specific user on this specific day.
        # When a user solves a problem, it drops out of the NOT IN clause,
        # and the next problem in the stable sorted order slides up!
        result = await db.execute(text("""
            SELECT p.slug, p.title, p.difficulty, p.tags
            FROM problems p
            WHERE p.difficulty = :diff
              AND p.slug NOT IN (
                  SELECT s.problem_slug FROM solves s 
                  WHERE s.user_id = :uid 
                    AND CAST(s.solved_at AT TIME ZONE 'UTC' AS DATE) < CURRENT_DATE
              )
            ORDER BY MD5(p.slug || :uid || :today)
            LIMIT :limit
        """), {"diff": difficulty, "uid": user_id, "today": today_str, "limit": limit})
        return result.fetchall()

    easy_rows   = await _fetch("easy", 1)
    medium_rows = await _fetch("medium", 3)
    hard_rows   = await _fetch("hard", 1)

    picks = easy_rows + medium_rows + hard_rows
    # Sort them by difficulty visually or just leave them
    # the frontend renders them as they come.

    return [
        {
            "slug": r.slug,
            "title": r.title,
            "difficulty": r.difficulty,
            "tags": r.tags or [],
            "url": f"https://leetcode.com/problems/{r.slug}/",
        }
        for r in picks
    ]


@router.get("/{slug}")
async def get_problem(slug: str, db: AsyncSession = Depends(get_db)):
    query = text("SELECT slug, title, difficulty, tags, platform FROM problems WHERE slug = :slug")
    result = await db.execute(query, {"slug": slug})
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Problem not found")
        
    return {
        "slug": row.slug,
        "title": row.title,
        "difficulty": row.difficulty,
        "tags": row.tags,
        "platform": row.platform
    }
