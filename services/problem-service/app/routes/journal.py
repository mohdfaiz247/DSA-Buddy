from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

router = APIRouter()

# Dependency for DB session
async def get_db():
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        yield session

class JournalCreate(BaseModel):
    user_id: UUID
    problem_slug: str
    reflection: str

class JournalResponse(BaseModel):
    id: UUID
    user_id: UUID
    problem_slug: str
    reflection: str
    created_at: datetime

@router.post("/", response_model=JournalResponse)
async def create_journal_entry(entry: JournalCreate, db: AsyncSession = Depends(get_db)):
    query = text("""
        INSERT INTO journal_entries (user_id, problem_slug, reflection)
        VALUES (:user_id, :problem_slug, :reflection)
        RETURNING id, user_id, problem_slug, reflection, created_at
    """)
    result = await db.execute(query, {
        "user_id": entry.user_id,
        "problem_slug": entry.problem_slug,
        "reflection": entry.reflection
    })
    await db.commit()
    row = result.fetchone()
    return dict(row._mapping)

@router.get("/{user_id}", response_model=List[JournalResponse])
async def get_user_journals(user_id: UUID, db: AsyncSession = Depends(get_db)):
    query = text("""
        SELECT id, user_id, problem_slug, reflection, created_at
        FROM journal_entries
        WHERE user_id = :user_id
        ORDER BY created_at DESC
    """)
    result = await db.execute(query, {"user_id": user_id})
    return [dict(row._mapping) for row in result.fetchall()]
