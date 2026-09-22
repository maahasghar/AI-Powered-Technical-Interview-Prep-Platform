from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

from app.core.config import settings
from app.domain.submissions.models import Submission
from app.feedback.models import Feedback
from app.feedback.policy import StructuredFeedback, judge_ready, validate_feedback
from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import func
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
    provider: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    schema_version: str | None = None
    source: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: str | None = None
    generation_ms: int | None = None
    attempts: int | None = None
    generated_at: datetime | None = None


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
        provider=row.provider,
        model=row.model,
        prompt_version=row.prompt_version,
        schema_version=row.schema_version,
        source=row.source,
        input_tokens=row.input_tokens,
        output_tokens=row.output_tokens,
        estimated_cost_usd=row.estimated_cost_usd,
        generation_ms=row.generation_ms,
        attempts=row.attempts,
        generated_at=row.generated_at,
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
        recent = (
            session.query(func.count(Feedback.id))
            .join(Submission, Submission.id == Feedback.submission_id)
            .filter(
                Submission.user_id == user_id,
                Feedback.created_at
                >= datetime.now(timezone.utc)
                - timedelta(seconds=settings.FEEDBACK_RATE_WINDOW_SECONDS),
            )
            .scalar()
        )
        if recent >= settings.FEEDBACK_RATE_LIMIT:
            raise HTTPException(429, "Feedback request limit reached. Try again later.")
        row = Feedback(submission_id=submission.id, stage=stage, status="QUEUED")
        session.add(row)
    elif row.status in {"QUEUED", "RUNNING", "READY"}:
        session.commit()
        session.refresh(row)
        return row, False
    elif row.status == "FAILED":
        recent = (
            session.query(func.count(Feedback.id))
            .join(Submission, Submission.id == Feedback.submission_id)
            .filter(
                Submission.user_id == user_id,
                Feedback.created_at
                >= datetime.now(timezone.utc)
                - timedelta(seconds=settings.FEEDBACK_RATE_WINDOW_SECONDS),
            )
            .scalar()
        )
        if recent >= settings.FEEDBACK_RATE_LIMIT:
            raise HTTPException(429, "Feedback request limit reached. Try again later.")
        row.status, row.payload, row.execution_id = "QUEUED", None, None
    else:
        recent = (
            session.query(func.count(Feedback.id))
            .join(Submission, Submission.id == Feedback.submission_id)
            .filter(
                Submission.user_id == user_id,
                Feedback.created_at
                >= datetime.now(timezone.utc)
                - timedelta(seconds=settings.FEEDBACK_RATE_WINDOW_SECONDS),
            )
            .scalar()
        )
        if recent >= settings.FEEDBACK_RATE_LIMIT:
            raise HTTPException(429, "Feedback request limit reached. Try again later.")
    session.commit()
    session.refresh(row)
    return row, True
