from fastapi import FastAPI
from app.core.container import container
from app.api.v1.routers.auth_router import router as auth_router
from app.api.v1.routers.user_router import router as user_router
from app.core.logging import RequestIDMiddleware

app = FastAPI()


app.add_middleware(RequestIDMiddleware)
app.include_router(auth_router)
app.include_router(user_router)
