from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    JWT_SECRET: str
    ENV: str = "dev"
    SENTRY_DSN: str = ""
    CORS_ORIGINS: str = "http://localhost:3000"

    class Config:
        env_file = str(Path(__file__).resolve().parents[3] / ".env")


settings = Settings()
