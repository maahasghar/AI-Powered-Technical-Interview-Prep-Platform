from app.core.container import container
from app.domain.auth.service import AuthService
from app.domain.user.schemas import UserProfileUpdate, UserResponse
from app.domain.user.progress_schemas import ProgressResponse
from app.infrastructure.db import get_db_session
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

router = APIRouter(prefix="/users", tags=["Users"])


def get_user_service(session: Session = Depends(get_db_session)):
    return container.get_user_service(session)


def get_progress_service(session: Session = Depends(get_db_session)):
    return container.get_progress_service(session)


@router.get("/me", response_model=UserResponse)
def get_current_user(
    current_user=Depends(AuthService.get_current_user),
    user_service=Depends(get_user_service),
):
    """Get current authenticated user's profile"""
    return user_service.get_user(current_user.id)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_current_user(
    response: Response,
    current_user=Depends(AuthService.get_current_user),
    user_service=Depends(get_user_service),
):
    if not user_service.delete_account(current_user.id):
        raise HTTPException(status_code=404, detail="User not found")
    response.delete_cookie("refresh_token", path="/api/v1/auth", httponly=True, samesite="lax")


@router.get("/me/progress", response_model=ProgressResponse)
def get_progress(
    current_user=Depends(AuthService.get_current_user),
    progress_service=Depends(get_progress_service),
):
    return progress_service.get_progress(current_user.id)


@router.get("/{user_id}/profile")
def get_user_profile(user_id: int, user_service=Depends(get_user_service)):
    """Get user profile by user ID"""
    return user_service.get_user_profile(user_id)


@router.put("/{user_id}/profile")
def update_user_profile(
    user_id: int,
    payload: UserProfileUpdate,
    current_user=Depends(AuthService.get_current_user),
    user_service=Depends(get_user_service),
):
    """Update user profile (only own profile)"""
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return user_service.update_user_profile(user_id, **payload.dict())


@router.post("/{user_id}/profile")
def create_user_profile(
    user_id: int,
    payload: UserProfileUpdate,
    current_user=Depends(AuthService.get_current_user),
    user_service=Depends(get_user_service),
):
    """Create user profile (only own profile)"""
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return user_service.create_user_profile(user_id, **payload.dict())
