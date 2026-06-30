import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    KAFKA_BROKERS: str = os.getenv("KAFKA_BROKERS", "localhost:9092")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    AI_AGENT_URL: str = os.getenv("AI_AGENT_URL", "http://ai-agent-service:8005")
    HINT_CACHE_POLL_INTERVAL: float = 0.5   # seconds between cache poll attempts
    HINT_CACHE_MAX_POLLS: int = 20           # max polls before returning pending

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
