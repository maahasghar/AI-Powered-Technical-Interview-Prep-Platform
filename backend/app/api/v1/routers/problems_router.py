from __future__ import annotations

from app.core.container import container
from app.domain.auth.service import AuthService
from app.domain.problems.schemas import ProblemCreate, ProblemResponse, ProblemUpdate
from app.domain.problems.service import ProblemsService
from app.infrastructure.db import get_db_session
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

router = APIRouter(prefix="/problems", tags=["Problems"])


def get_problems_service(
    session: Session = Depends(get_db_session),
) -> ProblemsService:
    return container.get_problems_service(session)


@router.get("", response_model=list[ProblemResponse])
def list_problems(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    difficulty: int | None = Query(default=None, ge=1, le=3),
    category: str | None = Query(default=None, min_length=1),
    include_inactive: bool = False,
    current_user=Depends(AuthService.get_current_user),
    problems_service: ProblemsService = Depends(get_problems_service),
):
    if include_inactive and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    return problems_service.get_all_problems(
        skip=skip,
        limit=limit,
        difficulty=difficulty,
        category=category,
        include_inactive=include_inactive,
    )


@router.get("/{problem_id}", response_model=ProblemResponse)
def get_problem(
    problem_id: int,
    current_user=Depends(AuthService.get_current_user),
    problems_service: ProblemsService = Depends(get_problems_service),
):
    problem = problems_service.get_problem(problem_id)
    if problem is None or (not problem.is_active and current_user.role != "admin"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found"
        )
    return problem


@router.post(
    "",
    response_model=ProblemResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(AuthService.require_role("admin"))],
)
def create_problem(
    payload: ProblemCreate,
    problems_service: ProblemsService = Depends(get_problems_service),
):
    return problems_service.create_problem(**payload.model_dump())


@router.patch(
    "/{problem_id}",
    response_model=ProblemResponse,
    dependencies=[Depends(AuthService.require_role("admin"))],
)
def update_problem(
    problem_id: int,
    payload: ProblemUpdate,
    problems_service: ProblemsService = Depends(get_problems_service),
):
    problem = problems_service.update_problem(
        problem_id,
        **payload.model_dump(exclude_unset=True),
    )
    if problem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found"
        )
    return problem


@router.delete(
    "/{problem_id}",
    response_model=ProblemResponse,
    dependencies=[Depends(AuthService.require_role("admin"))],
    summary="Archive a problem without deleting its submissions",
)
def archive_problem(
    problem_id: int,
    problems_service: ProblemsService = Depends(get_problems_service),
):
    problem = problems_service.archive_problem(problem_id)
    if problem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found"
        )
    return problem
