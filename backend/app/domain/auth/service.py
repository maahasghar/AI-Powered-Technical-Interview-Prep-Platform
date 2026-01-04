from datetime import datetime
from datetime import datetime as now
from datetime import timedelta

from app.domain.auth.schemas import RegisterRequest
from exceptions import (
    EmailNotVerifiedError,
    InvalidCredentials,
    InvalidTokenError,
    TokenExpiredError,
    Unauthorized,
)
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer as oauth2_scheme
from jose import JWTError, jwt

from backend.app.core.config import Settings
from backend.app.core.security import (
    create_access_token,
    create_refresh_token,
    generate_verification_token,
    verify_password,
)

oauth2 = oauth2_scheme()


class AuthService:
    def login(self, email: str, password: str):
        user = self.user_repo.get_by_email(email)

        if not verify_password(password, user.password_hash):
            raise InvalidCredentials()

        # block user until email verified
        if not user.is_verified:
            raise EmailNotVerifiedError()

        access_token = create_access_token({"sub": user.id})
        refresh_token = create_refresh_token({"sub": user.id})

        self.token_repo.save(user_id=user.id, refresh_token=refresh_token)

        return {"access_token": access_token, "refresh_token": refresh_token}

    def logout(self, refresh_token: str):
        self.token_repo.revoke(refresh_token)

    def refresh_access_token(self, refresh_token: str):
        token = self.token_repo.get(refresh_token)

        if not token or token.revoked or token.expires_at < datetime.utcnow():
            raise Unauthorized()

        return create_access_token({"sub": token.user_id})

    @staticmethod
    def get_current_user(token: str = Depends(oauth2_scheme)):
        try:
            payload = jwt.decode(token, Settings.JWT_SECRET, algorithms=["HS256"])
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
            password_hash=self.hasher.hash(payload.password),
            is_verified=False,
        )

        token = generate_verification_token()

        self.verification_repo.create(
            user_id=user.id, token=token, expires_at=now() + timedelta(hours=24)
        )

        self.email_service.send_verification_email(email=user.email, token=token)

        return user

    def verify_email(self, token: str):
        record = self.verification_repo.get_by_token(token)

        if not record:
            raise InvalidTokenError()

        if record.used or record.expires_at < now():
            raise TokenExpiredError()

        self.user_repo.mark_verified(record.user_id)

        self.verification_repo.mark_used(record.id)
