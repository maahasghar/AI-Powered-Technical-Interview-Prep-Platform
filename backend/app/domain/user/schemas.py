from __future__ import annotations

from pydantic import BaseModel


class UserProfileUpdate(BaseModel):
    full_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None


class UserProfile(BaseModel):
    id: int
    user_id: int
    full_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    is_verified: bool

    class Config:
        from_attributes = True
