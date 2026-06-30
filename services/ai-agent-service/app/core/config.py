import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Kafka
    KAFKA_BROKERS: str = os.getenv("KAFKA_BROKERS", "localhost:9092")
    KAFKA_GROUP_ID: str = "ai-agent-group"
    TOPIC_HINT_REQUESTED: str = "hint.requested"
    TOPIC_HINT_READY: str = "hint.ready"
    TOPIC_PATTERN_CLASSIFIED: str = "pattern.classified"
    TOPIC_SOLVE_COMPLETED: str = "solve.completed"

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # Neo4j
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "changeme")

    # Google Gemini / LLM
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    LLM_MODEL: str = "gemini-2.5-flash"
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 1024

    # Pinecone / Vector store
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_INDEX: str = os.getenv("PINECONE_INDEX", "dsa-editorials")

    # Hint settings
    MAX_HINTS_PER_PROBLEM: int = 5
    HINT_CACHE_TTL: int = 3600  # 1 hour in Redis

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore unknown env vars from the shared .env

settings = Settings()
