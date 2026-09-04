from app.domain.auth.schemas import (
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    RegisterRequest,
    RegisterResponse,
    MessageResponse,
    RefreshRequest,
    TokenResponse,
)
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.container import container
from app.domain.auth.service import AuthService
from app.infrastructure.db import get_db_session


router = APIRouter(prefix="/auth", tags=["Auth"])

#This is an instance implementation of the AuthService class that is created with a database session and the necessary repositories and services. This allows for better testability and separation of concerns.
#dependency injection to get the AuthService with a database session.
def get_auth_service(session: Session = Depends(get_db_session),) -> AuthService:
    return container.get_auth_service(session)

#using the dependency injection to get the AuthService instance to handle the authentication-related endpoints. 
#Each endpoint uses the appropriate request and response schemas defined in the auth/schemas.py file.
#Each istance of dependency injection return the service instance, where the payload is passed to the service methods to handle the business logic of authentication, such as login, logout, registration, token refresh, and email verification.

@router.post("/register", response_model=RegisterResponse)
def register(
    payload: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    return auth_service.register(payload)

@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    return auth_service.login(payload)

@router.post("/refresh", response_model=TokenResponse)
def refresh(
    payload: RefreshRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    return auth_service.refresh_access_token(payload.refresh_token)

@router.post("/logout", response_model=MessageResponse)
def logout(
    payload: LogoutRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    auth_service.logout(payload.refresh_token)
    return MessageResponse(message="Logged out successfully")

@router.get("/verify")
def verify_email(token: str, auth_service: AuthService = Depends(get_auth_service)):
    auth_service.verify_email(token)
    return {"message": "Email verified successfully"}

@router.get("/password-reset")
def reset_password(token: str, auth_service: AuthService = Depends(get_auth_service)):
    auth_service.reset_password(token)
    return {"message": "Password reset successfully"}
