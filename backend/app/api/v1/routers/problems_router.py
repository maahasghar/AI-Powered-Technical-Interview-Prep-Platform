from fastapi import APIRouter, Depends

from backend.app.domain.auth.service import AuthService

router = APIRouter(prefix="/problems", tags=["Problem"])


@router.post(
    "/question/{id}", dependencies=[Depends(AuthService.require_role("admin"))]
)
def create_problem():
    ...
