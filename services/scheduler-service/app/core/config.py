import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://dsabuddy:change_me_in_prod@localhost:5432/dsabuddy")
    KAFKA_BROKERS: str = os.getenv("KAFKA_BROKERS", "localhost:9092")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    REVIEW_NOTIFY_HOUR: int = 9  # Push review.due events at 9am daily

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
