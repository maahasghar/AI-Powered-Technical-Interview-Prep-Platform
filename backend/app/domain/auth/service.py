import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.core.config import settings
from app.core.security import (  # generate_verification_token,
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.domain.auth.exceptions import (  # InvalidTokenError,; TokenExpiredError,
    DuplicateEmail,
    EmailNotVerifiedError,
    InvalidCredentials,
    Unauthorized,
)
from app.domain.auth.schemas import LoginRequest, RegisterRequest, ResetPasswordRequest
from app.domain.user.repository import UserRepository
from app.infrastructure.db import Database, get_db_session
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

# from datetime import datetime as now
# from datetime import timedelta


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


class AuthService:
    def __init__(self, token_repo, user_repo, account_token_repo, email_service):
        self.token_repo = token_repo
        self.user_repo = user_repo
        self.account_token_repo = account_token_repo
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
        refresh_token = self._issue_refresh_token(user.id)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    def logout(self, refresh_token: str):
        payload = self._decode_refresh_token(refresh_token)
        token = self.token_repo.get(self._hash_refresh_token(refresh_token))
        if token is not None and token.family_id == payload["family_id"]:
            self.token_repo.revoke_family(token.family_id)

    def refresh_access_token(self, refresh_token: str):
        payload = self._decode_refresh_token(refresh_token)
        token = self.token_repo.get(self._hash_refresh_token(refresh_token))

        if token is None or token.family_id != payload["family_id"]:
            raise Unauthorized()

        if token.revoked:
            self.token_repo.revoke_family(token.family_id)
            raise Unauthorized()

        if token.expires_at < datetime.now(timezone.utc):
            raise Unauthorized()

        replacement = self._issue_refresh_token(
            token.user_id,
            family_id=token.family_id,
            rotate_from=token,
        )

        return {
            "access_token": create_access_token({"sub": token.user_id}),
            "refresh_token": replacement,
            "token_type": "bearer",
        }

    @staticmethod
    def get_current_user(
        token: str = Depends(oauth2_scheme),
        session: Session = Depends(get_db_session),
    ):
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
            if payload.get("token_type") != "access":
                raise HTTPException(status_code=401, detail="Invalid token")
            user_id = int(payload["sub"])
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

        user_repo = UserRepository(Database(session))
        user = user_repo.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user

    @staticmethod
    def require_role(required_role: str):
        def checker(user=Depends(AuthService.get_current_user)):
            if user.role != required_role:
                raise HTTPException(status_code=403, detail="Forbidden")
            return user

        return checker

    def register(self, payload: RegisterRequest):
        email = payload.email.strip().lower()
        if self.user_repo.get_by_email(email):
            raise HTTPException(status_code=409, detail="Email is already registered")

        try:
            user = self.user_repo.create_user(
                email=email,
                password_hash=hash_password(payload.password),
                is_verified=False,
            )
        except DuplicateEmail:
            raise HTTPException(
                status_code=409, detail="Email is already registered"
            ) from None

        if any((payload.full_name, payload.bio, payload.avatar_url)):
            self.user_repo.create_profile(
                user_id=user.id,
                full_name=payload.full_name,
                bio=payload.bio,
                avatar_url=payload.avatar_url,
            )

        self._send_verification_token(user)
        return user

    def verify_email(self, token: str):
        record = self._get_account_token(token, "email_verification")
        user = self.user_repo.get_by_id(record.user_id)
        if user is None:
            raise HTTPException(status_code=400, detail="Invalid verification token")
        self.user_repo.update_user(
            user.id,
            is_verified=True,
            verified_at=datetime.now(timezone.utc),
        )
        self.account_token_repo.mark_used(record)

    def resend_verification(self, email: str):
        user = self.user_repo.get_by_email(email.strip().lower())
        if user and not user.is_verified:
            self._send_verification_token(user)

    def forgot_password(self, email: str):
        user = self.user_repo.get_by_email(email.strip().lower())
        if user:
            self.account_token_repo.invalidate_unused(user.id, "password_reset")
            raw_token = self._create_account_token(
                user.id, "password_reset", timedelta(minutes=30)
            )
            self.email_service.send_password_reset_email(user.email, raw_token)

    def reset_password(self, payload: ResetPasswordRequest):
        record = self._get_account_token(payload.token, "password_reset")
        user = self.user_repo.get_by_id(record.user_id)
        if user is None:
            raise HTTPException(status_code=400, detail="Invalid reset token")
        self.user_repo.update_user(
            user.id,
            password_hash=hash_password(payload.new_password),
        )
        self.token_repo.revoke_all_for_user(user.id)
        self.account_token_repo.mark_used(record)

    def _send_verification_token(self, user):
        self.account_token_repo.invalidate_unused(user.id, "email_verification")
        raw_token = self._create_account_token(
            user.id, "email_verification", timedelta(hours=24)
        )
        self.email_service.send_verification_email(user.email, raw_token)

    def _create_account_token(self, user_id, token_type, lifetime):
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        self.account_token_repo.create(
            user_id,
            token_hash,
            token_type,
            datetime.now(timezone.utc) + lifetime,
        )
        return raw_token

    def _get_account_token(self, raw_token, token_type):
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        record = self.account_token_repo.get_active(token_hash, token_type)
        if record is None or record.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Invalid or expired token")
        return record

    def _issue_refresh_token(self, user_id, family_id=None, rotate_from=None):
        family_id = family_id or str(uuid4())
        token_id = str(uuid4())
        raw_token = create_refresh_token(
            {"sub": user_id, "family_id": family_id, "jti": token_id}
        )
        token_hash = self._hash_refresh_token(raw_token)
        if rotate_from is None:
            self.token_repo.save(
                user_id=user_id,
                token_hash=token_hash,
                family_id=family_id,
                expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            )
        else:
            self.token_repo.revoke_and_rotate(rotate_from, token_hash)
        return raw_token

    @staticmethod
    def _hash_refresh_token(refresh_token: str) -> str:
        return hashlib.sha256(refresh_token.encode()).hexdigest()

    @staticmethod
    def _decode_refresh_token(refresh_token: str):
        try:
            payload = jwt.decode(
                refresh_token,
                settings.JWT_SECRET,
                algorithms=["HS256"],
            )
            if (
                payload.get("token_type") != "refresh"
                or not payload.get("sub")
                or not payload.get("family_id")
                or not payload.get("jti")
            ):
                raise JWTError()
            int(payload["sub"])
            return payload
        except (JWTError, ValueError, TypeError):
            raise Unauthorized() from None
