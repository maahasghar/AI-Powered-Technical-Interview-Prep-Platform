from typing import Optional

from pydantic import BaseModel


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None


class UserProfile(BaseModel):
    id: int
    user_id: int
    full_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    is_verified: bool

    class Config:
        from_attributes = True
