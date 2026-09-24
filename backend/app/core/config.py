from pathlib import Path

from pydantic import Field, SecretStr
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
    OLLAMA_NUM_THREAD: int = Field(default=1, ge=1)
    OLLAMA_NUM_PREDICT: int = Field(default=1024, ge=1)
    FEEDBACK_PROMPT_VERSION: str = "2026-09-24-v2"
    FEEDBACK_SCHEMA_VERSION: str = "2"
    FEEDBACK_TIMEOUT_SECONDS: float = Field(default=120.0, gt=0, le=1800)
    FEEDBACK_MAX_RETRIES: int = 1
    FEEDBACK_RETRY_BACKOFF_SECONDS: float = 2.0
    FEEDBACK_RATE_LIMIT: int = 10
    FEEDBACK_RATE_WINDOW_SECONDS: int = 3600
    LOGIN_RATE_LIMIT: int = 10
    LOGIN_RATE_WINDOW_SECONDS: int = 300
    REGISTER_RATE_LIMIT: int = 5
    REGISTER_RATE_WINDOW_SECONDS: int = 3600
    RESEND_VERIFICATION_RATE_LIMIT: int = 5
    RESEND_VERIFICATION_RATE_WINDOW_SECONDS: int = 3600
    SUBMISSION_RATE_LIMIT: int = 30
    SUBMISSION_RATE_WINDOW_SECONDS: int = 3600
    E2B_API_KEY: SecretStr = SecretStr("")
    E2B_REQUEST_TIMEOUT_SECONDS: float = 10.0
    FEEDBACK_OPENAI_INPUT_COST_PER_MILLION: float = 0.0
    FEEDBACK_OPENAI_OUTPUT_COST_PER_MILLION: float = 0.0
    SENTRY_DSN: str = ""
    CORS_ORIGINS: str = "http://localhost:3000"
    FRONTEND_URL: str = "http://localhost:3000"
    EMAIL_DELIVERY_MODE: str = "console"
    RESEND_API_KEY: SecretStr = SecretStr("")
    EMAIL_TIMEOUT_SECONDS: float = Field(default=10.0, gt=0, le=60)
    # Accepted for old .env files only; SMTP delivery has been removed.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "no-reply@example.com"
    SMTP_USE_TLS: bool = True

    class Config:
        env_file = str(Path(__file__).resolve().parents[3] / ".env")


settings = Settings()
