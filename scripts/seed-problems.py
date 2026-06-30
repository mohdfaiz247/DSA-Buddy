import os
import asyncio
import sys
import logging

# Add services dir to path to import problem_scraper
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'services', 'problem-service'))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text
from app.services.problem_scraper import fetch_leetcode_problems

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://dsabuddy:change_me_in_prod@localhost:5432/dsabuddy")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(bind=engine, autoflush=False, autocommit=False)

async def seed_problems():
    logger.info("Fetching 500 problems from LeetCode GraphQL API...")
    problems = await fetch_leetcode_problems(500)
    logger.info(f"Fetched {len(problems)} problems.")
    
    async with AsyncSessionLocal() as session:
        # We use PostgreSQL specific ON CONFLICT DO NOTHING to avoid duplicate errors
        query = text("""
            INSERT INTO problems (slug, title, difficulty, tags, platform)
            VALUES (:slug, :title, :difficulty, :tags, :platform)
            ON CONFLICT (slug) DO UPDATE SET 
                title = EXCLUDED.title,
                difficulty = EXCLUDED.difficulty,
                tags = EXCLUDED.tags,
                platform = EXCLUDED.platform
        """)
        
        for p in problems:
            await session.execute(query, p)
            
        await session.commit()
        logger.info("Successfully seeded database with problems.")

if __name__ == "__main__":
    asyncio.run(seed_problems())
