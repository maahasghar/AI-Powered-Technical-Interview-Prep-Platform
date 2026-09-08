from app.infrastructure.db import Base
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    role = Column(String, default="user")  # user | admin
    is_verified = Column(Boolean, default=False)
    verified_at = Column(DateTime(timezone=True))
    email_verification_token = Column(String, nullable=True)


class AuthToken(Base):
    __tablename__ = "auth_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    token_hash = Column(String, nullable=False, unique=True, index=True)
    family_id = Column(String, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True))
    revoked = Column(Boolean, default=False)
    replaced_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
