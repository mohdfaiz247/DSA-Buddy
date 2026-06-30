"""
XP Engine — computes XP earned from a solve event including difficulty,
streak bonuses, and first-solve bonuses.
"""
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

DIFFICULTY_XP = {
    "easy": settings.XP_EASY,
    "medium": settings.XP_MEDIUM,
    "hard": settings.XP_HARD,
}


async def compute_xp(
    db: AsyncSession,
    user_id: str,
    problem_slug: str,
    difficulty: str,
    streak_days: int,
    is_first_solve: bool
) -> int:
    base_xp = DIFFICULTY_XP.get(difficulty.lower(), settings.XP_MEDIUM)
    bonus = 0

    if is_first_solve:
        bonus += settings.XP_FIRST_SOLVE_BONUS

    if streak_days >= 3:
        bonus += settings.XP_STREAK_BONUS

    total = base_xp + bonus
    logger.info(f"XP computed for {user_id}: base={base_xp}, bonus={bonus}, total={total}")
    return total


async def compute_level(xp: int) -> int:
    """Level formula: level = floor(sqrt(xp / 10)) + 1 (capped at 100)."""
    import math
    return min(100, int(math.sqrt(xp / 10)) + 1)


async def update_streak(db: AsyncSession, user_id: str) -> int:
    """
    Update the user's streak:
    - If last_active was yesterday → increment streak
    - If last_active was today → no change
    - Otherwise → reset to 1
    Returns the new streak value.
    """
    today = date.today()
    result = await db.execute(
        text("SELECT streak_days, last_active FROM users WHERE id = :uid"),
        {"uid": user_id}
    )
    row = result.fetchone()
    if not row:
        return 1

    streak = row.streak_days or 0
    last_active = row.last_active

    if last_active is None:
        new_streak = 1
    elif last_active == today:
        new_streak = streak  # already solved today
    elif (today - last_active).days == 1:
        new_streak = streak + 1  # consecutive day
    else:
        new_streak = 1  # streak broken

    await db.execute(
        text("UPDATE users SET streak_days = :s, last_active = :d WHERE id = :uid"),
        {"s": new_streak, "d": today, "uid": user_id}
    )
    return new_streak


async def record_solve(
    db: AsyncSession,
    user_id: str,
    problem_slug: str,
    difficulty: str,
    time_taken_seconds: int,
    language: str,
) -> dict:
    """
    Full solve pipeline:
    1. Check if first solve (from solves table)
    2. Update streak
    3. Compute XP
    4. Insert into solves table
    5. Update user XP and level
    6. Upsert daily_activity
    Returns a dict with earned XP, new total XP, level, streak.
    """
    # 1. First solve check
    existing = await db.execute(
        text("SELECT id FROM solves WHERE user_id = :uid AND problem_slug = :slug LIMIT 1"),
        {"uid": user_id, "slug": problem_slug}
    )
    is_first_solve = existing.fetchone() is None

    # 2. Streak update
    streak = await update_streak(db, user_id)

    # 3. XP calc
    earned_xp = await compute_xp(db, user_id, problem_slug, difficulty, streak, is_first_solve)

    # 4. Insert solve record
    await db.execute(
        text("""
            INSERT INTO solves (user_id, problem_slug, time_taken_seconds, language, earned_xp)
            VALUES (:uid, :slug, :time, :lang, :xp)
        """),
        {"uid": user_id, "slug": problem_slug, "time": time_taken_seconds, "lang": language, "xp": earned_xp}
    )

    # 5. Update user XP + level
    user_result = await db.execute(
        text("SELECT xp FROM users WHERE id = :uid"), {"uid": user_id}
    )
    user_row = user_result.fetchone()
    current_xp = (user_row.xp if user_row else 0) or 0
    new_xp = current_xp + earned_xp
    new_level = await compute_level(new_xp)

    await db.execute(
        text("UPDATE users SET xp = :xp, level = :lvl WHERE id = :uid"),
        {"xp": new_xp, "lvl": new_level, "uid": user_id}
    )

    # 6. Upsert daily_activity
    today = date.today()
    await db.execute(
        text("""
            INSERT INTO daily_activity (user_id, date, problems_solved, xp_earned)
            VALUES (:uid, :d, 1, :xp)
            ON CONFLICT (user_id, date) DO UPDATE SET
                problems_solved = daily_activity.problems_solved + 1,
                xp_earned = daily_activity.xp_earned + EXCLUDED.xp_earned
        """),
        {"uid": user_id, "d": today, "xp": earned_xp}
    )

    await db.commit()
    logger.info(f"Solve recorded: user={user_id}, problem={problem_slug}, xp={earned_xp}, total={new_xp}, lvl={new_level}")

    return {
        "earned_xp": earned_xp,
        "total_xp": new_xp,
        "level": new_level,
        "streak_days": streak,
        "is_first_solve": is_first_solve,
    }
