from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.container import container
from app.domain.auth.service import AuthService
from app.domain.submissions.schemas import (
	SubmissionCreate,
	SubmissionResponse,
	SubmissionUpdate,
)
from app.domain.submissions.service import SubmissionsService
from app.infrastructure.db import get_db_session


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
):
	return submissions_service.create_submission(
		user_id=current_user.id,
		problem_id=payload.problem_id,
		code=payload.code,
		language=payload.language,
		status="pending",
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
		return [submission for submission in submissions if submission.user_id == current_user.id]

	return submissions


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
