from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    JWT_SECRET: str
    ENV: str = "dev"

    class Config:
        env_file = ".env"

settings = Settings()
