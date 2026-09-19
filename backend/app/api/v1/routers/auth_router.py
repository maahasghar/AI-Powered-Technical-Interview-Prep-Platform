from app.core.config import settings
from app.core.container import container
from app.core.rate_limit import RedisRateLimiter, client_identity
from app.domain.auth.exceptions import Unauthorized
from app.domain.auth.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    TokenResponse,
)
from app.domain.auth.service import AuthService
from app.infrastructure.db import get_db_session
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

router = APIRouter(prefix="/auth", tags=["Auth"])


# This is an instance implementation of the AuthService class that is created with a database session and the necessary repositories and services. This allows for better testability and separation of concerns.
# dependency injection to get the AuthService with a database session.
def get_auth_service(
    session: Session = Depends(get_db_session),
) -> AuthService:
    return container.get_auth_service(session)


def _limit(request, name, limit, window):
    RedisRateLimiter(container.redis.client).check(
        f"{name}:{client_identity(request)}", limit, window
    )


# using the dependency injection to get the AuthService instance to handle the authentication-related endpoints.
# Each endpoint uses the appropriate request and response schemas defined in the auth/schemas.py file.
# Each istance of dependency injection return the service instance, where the payload is passed to the service methods to handle the business logic of authentication, such as login, logout, registration, token refresh, and email verification.


@router.post(
    "/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED
)
def register(
    request: Request,
    payload: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    _limit(request, "register", settings.REGISTER_RATE_LIMIT, settings.REGISTER_RATE_WINDOW_SECONDS)
    return auth_service.register(payload)


COOKIE_NAME = "refresh_token"
COOKIE_PATH = "/api/v1/auth"


def require_session_request(request: Request):
    # Custom headers cannot be sent by cross-site HTML forms. CORS controls
    # browser preflights; additionally reject explicitly untrusted origins.
    allowed = {
        origin.strip().rstrip("/") for origin in settings.CORS_ORIGINS.split(",")
    }
    origin = request.headers.get("origin")
    if request.headers.get("X-Session-Request") != "1" or (
        origin and origin.rstrip("/") not in allowed
    ):
        raise HTTPException(status_code=403, detail="Invalid session request")


def clear_cookie(response: Response):
    response.delete_cookie(
        COOKIE_NAME,
        path=COOKIE_PATH,
        httponly=True,
        secure=settings.ENV != "dev",
        samesite="lax",
    )


def token_response(tokens, response: Response):
    response.set_cookie(
        COOKIE_NAME,
        tokens["refresh_token"],
        max_age=30 * 24 * 60 * 60,
        path=COOKIE_PATH,
        httponly=True,
        secure=settings.ENV != "dev",
        samesite="lax",
    )
    response.headers["Cache-Control"] = "no-store"
    return {"access_token": tokens["access_token"], "token_type": "bearer"}


@router.post(
    "/login",
    response_model=LoginResponse,
    dependencies=[Depends(require_session_request)],
)
def login(
    request: Request,
    payload: LoginRequest,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
):
    _limit(request, "login", settings.LOGIN_RATE_LIMIT, settings.LOGIN_RATE_WINDOW_SECONDS)
    return token_response(auth_service.login(payload), response)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    dependencies=[Depends(require_session_request)],
)
def refresh(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
):
    token = request.cookies.get(COOKIE_NAME)
    try:
        if not token:
            raise Unauthorized()
        return token_response(auth_service.refresh_access_token(token), response)
    except Unauthorized:
        failure = JSONResponse(
            status_code=401,
            content={"detail": "Unauthorized"},
            headers={"Cache-Control": "no-store"},
        )
        clear_cookie(failure)
        return failure


@router.post(
    "/logout",
    response_model=MessageResponse,
    dependencies=[Depends(require_session_request)],
)
def logout(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        try:
            auth_service.logout(token)
        except Unauthorized:
            pass
    clear_cookie(response)
    response.headers["Cache-Control"] = "no-store"
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
    request: Request,
    payload: ForgotPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    _limit(request, "resend-verification", settings.RESEND_VERIFICATION_RATE_LIMIT, settings.RESEND_VERIFICATION_RATE_WINDOW_SECONDS)
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
