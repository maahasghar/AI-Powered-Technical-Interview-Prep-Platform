from app.core.container import container
from app.domain.auth.service import AuthService
from app.domain.user.schemas import UserProfileUpdate
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me")
def get_current_user(user_id: str = Depends(AuthService.get_current_user)):
    """Get current authenticated user's profile"""
    return container.user_service.get_user(int(user_id))


@router.get("/{user_id}/profile")
def get_user_profile(user_id: int):
    """Get user profile by user ID"""
    return container.user_service.get_user_profile(user_id)


@router.put("/{user_id}/profile")
def update_user_profile(
    user_id: int,
    payload: UserProfileUpdate,
    current_user_id: str = Depends(AuthService.get_current_user),
):
    """Update user profile (only own profile)"""
    if int(current_user_id) != user_id:
        raise Exception("Unauthorized")
    return container.user_service.update_user_profile(user_id, **payload.dict())


@router.post("/{user_id}/profile")
def create_user_profile(
    user_id: int,
    payload: UserProfileUpdate,
    current_user_id: str = Depends(AuthService.get_current_user),
):
    """Create user profile (only own profile)"""
    if int(current_user_id) != user_id:
        raise Exception("Unauthorized")
    return container.user_service.create_user_profile(user_id, **payload.dict())
