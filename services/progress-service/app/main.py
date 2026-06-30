from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.kafka.consumer import start_consumer_thread
from app.routes import progress
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_consumer_thread()
    yield

app = FastAPI(title="DSA Buddy — Progress Service", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(progress.router, tags=["Progress"])

@app.get("/health")
def health():
    return {"status": "ok", "service": "progress"}
