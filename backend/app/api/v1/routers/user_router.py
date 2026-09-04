from app.core.container import container
from app.domain.auth.service import AuthService
from app.domain.user.schemas import UserProfileUpdate
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.infrastructure.db import get_db_session

router = APIRouter(prefix="/users", tags=["Users"])


def get_user_service(session: Session = Depends(get_db_session)):
    return container.get_user_service(session)


@router.get("/me")
def get_current_user(
    user_id: str = Depends(AuthService.get_current_user),
    user_service=Depends(get_user_service),
):
    """Get current authenticated user's profile"""
    return user_service.get_user(int(user_id))


@router.get("/{user_id}/profile")
def get_user_profile(user_id: int, user_service=Depends(get_user_service)):
    """Get user profile by user ID"""
    return user_service.get_user_profile(user_id)


@router.put("/{user_id}/profile")
def update_user_profile(
    user_id: int,
    payload: UserProfileUpdate,
    current_user_id: str = Depends(AuthService.get_current_user),
    user_service=Depends(get_user_service),
):
    """Update user profile (only own profile)"""
    if int(current_user_id) != user_id:
        raise Exception("Unauthorized")
    return user_service.update_user_profile(user_id, **payload.dict())


@router.post("/{user_id}/profile")
def create_user_profile(
    user_id: int,
    payload: UserProfileUpdate,
    current_user_id: str = Depends(AuthService.get_current_user),
    user_service=Depends(get_user_service),
):
    """Create user profile (only own profile)"""
    if int(current_user_id) != user_id:
        raise Exception("Unauthorized")
    return user_service.create_user_profile(user_id, **payload.dict())
