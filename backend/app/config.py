import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Autonomous Agent Platform"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/agent_platform"
    DATABASE_SYNC_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/agent_platform"

    # OpenAI / LLM
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: Optional[str] = None
    DEFAULT_MODEL: str = "gpt-4o-mini"
    SUPPORTED_MODELS: List[str] = ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]

    # Agent Limits
    MAX_STEPS_LIMIT: int = 12
    MAX_TOOL_CALLS_PER_STEP: int = 4
    DEFAULT_TOKEN_BUDGET: int = 50000
    DEFAULT_WALL_CLOCK_TIMEOUT: float = 180.0
    MAX_CONSECUTIVE_FAILURES: int = 3
    MAX_TOOL_RETRIES: int = 2

    # Cost calculation (rates per 1M tokens)
    # gpt-4o-mini: $0.15 / 1M prompt, $0.60 / 1M completion
    # gpt-4o: $2.50 / 1M prompt, $10.00 / 1M completion
    TOKEN_PRICING: dict = {
        "gpt-4o-mini": {"prompt": 0.00000015, "completion": 0.0000006},
        "gpt-4o": {"prompt": 0.0000025, "completion": 0.00001},
        "gpt-3.5-turbo": {"prompt": 0.0000005, "completion": 0.0000015},
        "default": {"prompt": 0.000001, "completion": 0.000003},
    }

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*"
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
