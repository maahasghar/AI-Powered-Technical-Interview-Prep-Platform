from __future__ import annotations

from app.api.v1.routers.problems_router import get_problems_service
from app.core.config import settings
from app.core.container import container
from app.core.rate_limit import RedisRateLimiter
from app.domain.auth.service import AuthService
from app.domain.problems.service import ProblemsService
from app.domain.submissions.models import Submission
from app.domain.submissions.schemas import SubmissionCreate, SubmissionResponse
from app.domain.submissions.service import SubmissionsService
from app.feedback.models import Feedback
from app.feedback.policy import judge_ready
from app.feedback.service import (
    FEEDBACK_QUEUE,
    FeedbackList,
    FeedbackRequest,
    FeedbackResponse,
    public_feedback,
    request_feedback,
)
from app.infrastructure.db import get_db_session
from app.infrastructure.submission_queue import SubmissionQueue
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

router = APIRouter(prefix="/submissions", tags=["Submissions"])


def get_submissions_service(
    session: Session = Depends(get_db_session),
) -> SubmissionsService:
    return container.get_submissions_service(session)


@router.post("", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED)
def create_submission(
    payload: SubmissionCreate,
    current_user=Depends(AuthService.get_current_user),
    submissions_service: SubmissionsService = Depends(get_submissions_service),
    problems_service: ProblemsService = Depends(get_problems_service),
):
    RedisRateLimiter(container.redis.client).check(
        f"submission:user:{current_user.id}",
        settings.SUBMISSION_RATE_LIMIT,
        settings.SUBMISSION_RATE_WINDOW_SECONDS,
    )
    problem = problems_service.get_problem(payload.problem_id)
    if problem is None or not problem.is_active:
        raise HTTPException(status_code=404, detail="Problem not found")
    return submissions_service.create_submission(
        user_id=current_user.id,
        problem_id=payload.problem_id,
        code=payload.code,
        language=payload.language,
        status="QUEUED",
    )


@router.get("/me", response_model=list[SubmissionResponse])
def list_my_submissions(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    current_user=Depends(AuthService.get_current_user),
    submissions_service: SubmissionsService = Depends(get_submissions_service),
):
    if current_user.role == "admin":
        return submissions_service.get_all_submissions(skip=skip, limit=limit)

    return submissions_service.get_user_submissions(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )


@router.get("/problem/{problem_id}", response_model=list[SubmissionResponse])
def list_problem_submissions(
    problem_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    current_user=Depends(AuthService.get_current_user),
    submissions_service: SubmissionsService = Depends(get_submissions_service),
):
    submissions = submissions_service.get_problem_submissions(
        problem_id=problem_id,
        skip=skip,
        limit=limit,
    )

    if current_user.role != "admin":
        return [
            submission
            for submission in submissions
            if submission.user_id == current_user.id
        ]

    return submissions


@router.get("/{submission_id}", response_model=SubmissionResponse)
def get_submission(
    submission_id: int,
    current_user=Depends(AuthService.get_current_user),
    submissions_service: SubmissionsService = Depends(get_submissions_service),
):
    submission = submissions_service.get_submission(submission_id)
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found",
        )

    if submission.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )

    return submission


@router.delete("/{submission_id}", response_model=SubmissionResponse)
def delete_submission(
    submission_id: int,
    current_user=Depends(AuthService.get_current_user),
    submissions_service: SubmissionsService = Depends(get_submissions_service),
):
    submission = submissions_service.get_submission(submission_id)
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found",
        )

    if submission.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )

    deleted_submission = submissions_service.delete_submission(submission_id)
    return deleted_submission


@router.get("/{submission_id}/feedback", response_model=FeedbackList)
def get_feedback(
    submission_id: int,
    current_user=Depends(AuthService.get_current_user),
    session: Session = Depends(get_db_session),
):
    submission = session.get(Submission, submission_id)
    if submission is None:
        raise HTTPException(404, "Submission not found")
    if submission.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(403, "Forbidden")
    eligible = judge_ready(submission)
    rows = (
        session.query(Feedback)
        .filter_by(submission_id=submission_id)
        .order_by(Feedback.id)
        .all()
        if eligible
        else []
    )
    return FeedbackList(eligible=eligible, items=[public_feedback(row) for row in rows])


@router.post(
    "/{submission_id}/feedback", response_model=FeedbackResponse, status_code=202
)
def create_feedback(
    submission_id: int,
    payload: FeedbackRequest,
    current_user=Depends(AuthService.get_current_user),
    session: Session = Depends(get_db_session),
):
    RedisRateLimiter(container.redis.client).check(
        f"feedback:user:{current_user.id}",
        settings.FEEDBACK_RATE_LIMIT,
        settings.FEEDBACK_RATE_WINDOW_SECONDS,
    )
    row, should_enqueue = request_feedback(
        session, submission_id, current_user.id, payload.action
    )
    if should_enqueue:
        SubmissionQueue(container.redis.client, FEEDBACK_QUEUE).enqueue(row.id)
    return public_feedback(row)
