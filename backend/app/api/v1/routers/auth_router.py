from app.core.container import container
from app.domain.auth.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    TokenResponse,
)
from app.domain.auth.service import AuthService
from app.infrastructure.db import get_db_session
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

router = APIRouter(prefix="/auth", tags=["Auth"])


# This is an instance implementation of the AuthService class that is created with a database session and the necessary repositories and services. This allows for better testability and separation of concerns.
# dependency injection to get the AuthService with a database session.
def get_auth_service(
    session: Session = Depends(get_db_session),
) -> AuthService:
    return container.get_auth_service(session)


# using the dependency injection to get the AuthService instance to handle the authentication-related endpoints.
# Each endpoint uses the appropriate request and response schemas defined in the auth/schemas.py file.
# Each istance of dependency injection return the service instance, where the payload is passed to the service methods to handle the business logic of authentication, such as login, logout, registration, token refresh, and email verification.


@router.post(
    "/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED
)
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


@router.get("/verify-email", response_model=MessageResponse)
def verify_email(
    token: str = Query(min_length=1),
    auth_service: AuthService = Depends(get_auth_service),
):
    auth_service.verify_email(token)
    return MessageResponse(message="Email verified successfully")


@router.post("/resend-verification", response_model=MessageResponse)
def resend_verification(
    payload: ForgotPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    auth_service.resend_verification(payload.email)
    return MessageResponse(
        message="If the account exists, a verification email was sent."
    )


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def forgot_password(
    payload: ForgotPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    auth_service.forgot_password(payload.email)
    return MessageResponse(
        message="If an account exists, a password reset email has been sent."
    )


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    payload: ResetPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    auth_service.reset_password(payload)
    return MessageResponse(message="Password reset successfully")
