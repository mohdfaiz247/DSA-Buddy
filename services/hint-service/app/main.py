from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.kafka.producer import start_hint_ready_thread
from app.routes import hints
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_hint_ready_thread()
    yield

app = FastAPI(title="DSA Buddy — Hint Service", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# No prefix — Nginx strips /api/hints/ so service receives /request, /poll/*, etc.
app.include_router(hints.router, tags=["Hints"])

@app.get("/health")
def health():
    return {"status": "ok", "service": "hints"}
