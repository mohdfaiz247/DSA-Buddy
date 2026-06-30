from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text
from contextlib import asynccontextmanager

from app.routes import problems, tags, journal
from app.db.session import AsyncSessionLocal
from app.services.trie_index import problem_trie

@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup: load all problems into the Trie
    async with AsyncSessionLocal() as session:
        query = text("SELECT title, slug FROM problems")
        result = await session.execute(query)
        for row in result:
            problem_trie.insert(row.title, row.slug)
    yield
    # On shutdown
    pass

app = FastAPI(title="DSA Buddy - Problem Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(problems.router, tags=["Problems"])
app.include_router(tags.router, prefix="/tags", tags=["Tags"])
app.include_router(journal.router, prefix="/journal", tags=["Journal"])

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "problems"}
