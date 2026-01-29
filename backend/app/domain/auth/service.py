from datetime import datetime

from app.core.config import settings
from app.core.security import (  # generate_verification_token,
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.domain.auth.exceptions import (  # InvalidTokenError,; TokenExpiredError,
    EmailNotVerifiedError,
    InvalidCredentials,
    Unauthorized,
)
from app.domain.auth.schemas import LoginRequest, RegisterRequest
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

# from datetime import datetime as now
# from datetime import timedelta


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


class AuthService:
    def __init__(self, token_repo, user_repo, email_service):
        self.token_repo = token_repo
        self.user_repo = user_repo
        self.email_service = email_service

    def login(self, payload: LoginRequest):
        user = self.user_repo.get_by_email(payload.email)

        if not user:
            raise InvalidCredentials()

        if not verify_password(payload.password, user.password_hash):
            raise InvalidCredentials()

        # block user until email verified
        if not user.is_verified:
            raise EmailNotVerifiedError()

        access_token = create_access_token({"sub": user.id})
        refresh_token = create_refresh_token({"sub": user.id})

        self.token_repo.save(user_id=user.id, refresh_token=refresh_token)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    def logout(self, refresh_token: str):
        self.token_repo.revoke(refresh_token)

    def refresh_access_token(self, refresh_token: str):
        token = self.token_repo.get(refresh_token)

        if not token or token.revoked or token.expires_at < datetime.utcnow():
            raise Unauthorized()

        return {
            "access_token": create_access_token({"sub": token.user_id}),
            "token_type": "bearer",
        }

    @staticmethod
    def get_current_user(token: str = Depends(oauth2_scheme)):
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
            return payload["sub"]
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

    @staticmethod
    def require_role(required_role: str):
        def checker(user=Depends(AuthService.get_current_user)):
            if user.role != required_role:
                raise HTTPException(status_code=403, detail="Forbidden")
            return user

        return checker

    def register(self, payload: RegisterRequest):
        user = self.user_repo.create_user(
            email=payload.email,
            password_hash=hash_password(payload.password),
            is_verified=False,
        )

        # token = generate_verification_token()

        # Note: verification_repo is not in the current container, skipping for now
        # self.verification_repo.create(
        #     user_id=user.id, token=token, expires_at=now() + timedelta(hours=24)
        # )

        # self.email_service.send_verification_email(email=user.email, token=token)

        return user

    def verify_email(self, token: str):
        # Note: verification_repo is not in the current container
        # record = self.verification_repo.get_by_token(token)
        # if not record:
        #     raise InvalidTokenError()
        # if record.used or record.expires_at < now():
        #     raise TokenExpiredError()
        # self.user_repo.mark_verified(record.user_id)
        # self.verification_repo.mark_used(record.id)
        pass
