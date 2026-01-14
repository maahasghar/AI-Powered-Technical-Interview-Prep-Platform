from app.api.v1.routers.auth_router import router as auth_router
from app.api.v1.routers.user_router import router as user_router
from app.core.config import settings
from app.core.logging import RequestIDMiddleware
from app.core.sentry import init_sentry
from fastapi import FastAPI

app = FastAPI()


app.add_middleware(RequestIDMiddleware)
app.include_router(auth_router)
app.include_router(user_router)
init_sentry(settings.SENTRY_DSN)
