from fastapi import APIRouter, Depends
from app.core.container import container
from app.domain.auth.schemas import LoginRequest, LoginResponse, MessageResponse, TokenResponse

router = APIRouter(prefix="/problems", tags=["Problem"])

@router.post("/question/{id}", dependencies=[Depends(require_role("admin"))])
def create_problem():
    ...
