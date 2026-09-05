from app.api.v1.routers.auth_router import router as auth_router
from app.api.v1.routers.user_router import router as user_router
from app.api.v1.routers.problems_router import router as problem_router
from app.api.v1.routers.submissions_router import router as submission_router

from app.core.config import settings
from app.core.logging import RequestIDMiddleware
from app.core.sentry import init_sentry
from app.core.container import container
from app.core.logging import setup_logging
from app.infrastructure.db import engine
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi import status
from sqlalchemy import text

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()

    # Confirm the database is reachable.
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    # Confirm Redis is reachable.
    container.redis.client.ping()

    yield

    # Shutdown
    container.redis.close()
    engine.dispose()

app = FastAPI(lifespan=lifespan)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", status_code=status.HTTP_200_OK)
def hello_world():
	return {"message": "Hello, World!"}

@app.get("/health")
def health():
    return {"status": "ok"}

app.add_middleware(RequestIDMiddleware)
app.include_router(auth_router, prefix="/api/v1", tags=["Auth"])
app.include_router(user_router, prefix="/api/v1")
app.include_router(problem_router, prefix="/api/v1")
app.include_router(submission_router, prefix="/api/v1")
init_sentry(settings.SENTRY_DSN)
