from fastapi import APIRouter, Depends
from app.core.container import container
from app.domain.auth.schemas import LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    return container.auth_service.login(payload)