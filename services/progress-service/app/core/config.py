import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://dsabuddy:change_me_in_prod@localhost:5432/dsabuddy")
    KAFKA_BROKERS: str = os.getenv("KAFKA_BROKERS", "localhost:9092")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # XP Awards
    XP_EASY: int = 10
    XP_MEDIUM: int = 25
    XP_HARD: int = 60
    XP_STREAK_BONUS: int = 5       # bonus per problem when on streak >= 3 days
    XP_FIRST_SOLVE_BONUS: int = 15 # bonus for solving a problem for the first time

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
