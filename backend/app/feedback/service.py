from __future__ import annotations

from typing import Literal

from app.domain.submissions.models import Submission
from app.feedback.models import Feedback
from app.feedback.policy import StructuredFeedback, judge_ready, validate_feedback
from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import insert

FEEDBACK_QUEUE = "coach:feedback"


class FeedbackRequest(BaseModel):
    action: Literal["diagnosis", "hint", "show_solution"]
    model_config = {"extra": "forbid"}


class FeedbackResponse(BaseModel):
    id: int
    stage: Literal["DIAGNOSIS", "HINT", "SOLUTION"]
    status: Literal["QUEUED", "RUNNING", "READY", "FAILED"]
    feedback: StructuredFeedback | None = None
    error: str | None = None


class FeedbackList(BaseModel):
    eligible: bool
    items: list[FeedbackResponse]


def public_feedback(row):
    feedback = None
    status = row.status
    if status == "READY":
        try:
            feedback = validate_feedback(row.stage, row.payload)
        except (ValueError, KeyError, TypeError):
            status = "FAILED"
    return FeedbackResponse(
        id=row.id,
        stage=row.stage,
        status=status,
        feedback=feedback,
        error=(
            "Coaching is unavailable. You can retry without changing your judge result."
            if status == "FAILED"
            else None
        ),
    )


def initial_feedback(session, submission):
    if not judge_ready(submission):
        return
    session.execute(
        insert(Feedback)
        .values(submission_id=submission.id, stage="DIAGNOSIS", status="QUEUED")
        .on_conflict_do_nothing(constraint="uq_feedback_stage")
    )


def request_feedback(session, submission_id, user_id, action):
    submission = (
        session.query(Submission)
        .filter(Submission.id == submission_id)
        .with_for_update()
        .first()
    )
    if submission is None:
        raise HTTPException(404, "Submission not found")
    if submission.user_id != user_id:
        raise HTTPException(403, "Forbidden")
    if not judge_ready(submission):
        raise HTTPException(409, "Feedback requires completed judge results.")
    stage = {"diagnosis": "DIAGNOSIS", "hint": "HINT", "show_solution": "SOLUTION"}[
        action
    ]
    if stage == "HINT":
        first = (
            session.query(Feedback)
            .filter_by(submission_id=submission.id, stage="DIAGNOSIS", status="READY")
            .first()
        )
        if first is None:
            raise HTTPException(
                409, "Read the first feedback before requesting a hint."
            )
    row = (
        session.query(Feedback)
        .filter_by(submission_id=submission.id, stage=stage)
        .first()
    )
    if row is None:
        row = Feedback(submission_id=submission.id, stage=stage, status="QUEUED")
        session.add(row)
    elif row.status == "FAILED":
        row.status, row.payload, row.execution_id = "QUEUED", None, None
    session.commit()
    session.refresh(row)
    return row
