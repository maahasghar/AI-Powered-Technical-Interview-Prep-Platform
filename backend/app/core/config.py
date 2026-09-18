from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    JWT_SECRET: str
    ENV: str = "dev"
    OPENAI_API_KEY: SecretStr = SecretStr("")
    FEEDBACK_MODEL: str = ""
    FEEDBACK_PROVIDER: str = "openai"
    FEEDBACK_AI_ENABLED: bool = False
    FEEDBACK_EVALUATION_PASSED: bool = False
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    FEEDBACK_PROMPT_VERSION: str = "2026-09-18-v1"
    FEEDBACK_SCHEMA_VERSION: str = "1"
    FEEDBACK_TIMEOUT_SECONDS: float = 120.0
    FEEDBACK_MAX_RETRIES: int = 1
    FEEDBACK_RETRY_BACKOFF_SECONDS: float = 2.0
    FEEDBACK_RATE_LIMIT: int = 10
    FEEDBACK_RATE_WINDOW_SECONDS: int = 3600
    FEEDBACK_OPENAI_INPUT_COST_PER_MILLION: float = 0.0
    FEEDBACK_OPENAI_OUTPUT_COST_PER_MILLION: float = 0.0
    SENTRY_DSN: str = ""
    CORS_ORIGINS: str = "http://localhost:3000"
    FRONTEND_URL: str = "http://localhost:3000"
    EMAIL_DELIVERY_MODE: str = "console"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "no-reply@example.com"
    SMTP_USE_TLS: bool = True

    class Config:
        env_file = str(Path(__file__).resolve().parents[3] / ".env")


settings = Settings()
