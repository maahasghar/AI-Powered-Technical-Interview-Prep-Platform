from fastapi import APIRouter, Depends
from app.core.container import container
from app.domain.auth.schemas import LoginRequest, LoginResponse, MessageResponse, TokenResponse

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/login", response_model=LoginResponse )
def login(payload: LoginRequest):
    return container.auth_service.login(payload)

@router.post("/logout", response_model=MessageResponse)
def logout(payload: LogoutRequest):
    container.auth_service.logout(payload)
    return MessageResponse(message="Logged out successfully")

@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest):
    return container.auth_service.refresh_access_token(payload)

@router.get("/verify")
def verify_email(token: str):
    container.auth_service.verify_email(token)
    return {"message": "Email verified successfully"}