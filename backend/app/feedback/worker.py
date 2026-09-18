"""Independent coaching worker; never updates submission verdicts or judge results."""

import logging
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx
from app.domain.auth.models import User  # noqa: F401
from app.domain.problems.models import Problem
from app.domain.submissions.models import Submission
from app.core.config import settings
from app.feedback.models import Feedback
from app.feedback.policy import (
    build_feedback_context,
    deterministic_feedback,
    judge_ready,
    validate_feedback,
)
from app.feedback.provider import build_feedback_provider
from app.feedback.service import FEEDBACK_QUEUE, initial_feedback
from app.infrastructure.db import SessionLocal
from app.infrastructure.redis import RedisClient
from app.infrastructure.submission_queue import SubmissionQueue
from sqlalchemy import exists, update

logger = logging.getLogger(__name__)


def _retry_delay(exc: Exception, attempt: int) -> float:
    """Backoff before retrying a failed provider call, honoring Retry-After on 429s."""
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429:
        retry_after = exc.response.headers.get("retry-after")
        if retry_after is not None:
            try:
                return max(float(retry_after), 1.0)
            except ValueError:
                pass
        return max(settings.FEEDBACK_RETRY_BACKOFF_SECONDS, 5.0)
    return settings.FEEDBACK_RETRY_BACKOFF_SECONDS * (attempt + 1)


def _is_transient(exc: Exception) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)):
        return True
    return isinstance(exc, httpx.HTTPStatusError) and (
        exc.response.status_code == 429 or exc.response.status_code >= 500
    )


def reconcile_feedback(queue, session_factory=SessionLocal):
    with session_factory.begin() as session:
        # Recover a judge crash between committing the result and scheduling feedback.
        completed = (
            session.query(Submission)
            .filter(
                Submission.status.in_(
                    ["PASSED", "FAILED", "RUNTIME_ERROR", "TIME_LIMIT_EXCEEDED"]
                ),
                Submission.result.isnot(None),
                ~exists().where(
                    Feedback.submission_id == Submission.id,
                    Feedback.stage == "DIAGNOSIS",
                ),
            )
            .order_by(Submission.id)
            .yield_per(100)
        )
        for submission in completed:
            initial_feedback(session, submission)
        # Interrupted generations require an explicit retry to bound provider charges.
        session.execute(
            update(Feedback)
            .where(
                Feedback.status == "RUNNING",
                Feedback.updated_at < datetime.now(timezone.utc) - timedelta(minutes=3),
            )
            .values(status="FAILED", execution_id=None)
        )
        ids = (
            session.query(Feedback.id)
            .filter_by(status="QUEUED")
            .order_by(Feedback.id)
            .limit(1000)
            .all()
        )
    for (feedback_id,) in ids:
        if not queue.enqueue(feedback_id):
            break


def process_feedback(feedback_id, provider, session_factory=SessionLocal):
    token = uuid4().hex
    retry_after_judge_commit = False
    with session_factory.begin() as session:
        claimed = session.execute(
            update(Feedback)
            .where(Feedback.id == feedback_id, Feedback.status == "QUEUED")
            .values(
                status="RUNNING",
                execution_id=token,
                updated_at=datetime.now(timezone.utc),
            )
        )
        if not claimed.rowcount:
            return
        row = session.get(Feedback, feedback_id)
        submission = session.get(Submission, row.submission_id)
        problem = session.get(Problem, submission.problem_id) if submission else None
        stage = row.stage
        # Build context from a committed judge result; no provider call on missing results.
        if submission and problem and not judge_ready(submission):
            retry_after_judge_commit = True
            context = None
        else:
            context = (
                build_feedback_context(submission, problem)
                if submission and problem
                else None
            )
    if retry_after_judge_commit:
        with session_factory.begin() as session:
            session.execute(
                update(Feedback)
                .where(
                    Feedback.id == feedback_id,
                    Feedback.status == "RUNNING",
                    Feedback.execution_id == token,
                )
                .values(
                    status="QUEUED",
                    execution_id=None,
                    updated_at=datetime.now(timezone.utc),
                )
            )
        return
    status, payload = "READY", None
    metadata = {
        "provider": settings.FEEDBACK_PROVIDER,
        "model": settings.FEEDBACK_MODEL or None,
        "prompt_version": settings.FEEDBACK_PROMPT_VERSION,
        "schema_version": settings.FEEDBACK_SCHEMA_VERSION,
        "source": "fallback",
        "input_tokens": None,
        "output_tokens": None,
        "estimated_cost_usd": "0",
        "generation_ms": None,
        "attempts": 0,
        "error_type": None,
        "generated_at": datetime.now(timezone.utc),
    }
    attempts = settings.FEEDBACK_MAX_RETRIES + 1
    if context is not None:
        for attempt in range(attempts):
            try:
                candidate = provider.generate(stage, context)
                payload = validate_feedback(stage, candidate).model_dump_json()
                provider_metadata = getattr(provider, "last_metadata", {})
                if isinstance(provider_metadata, dict):
                    metadata.update(provider_metadata)
                metadata.update(
                    source="ai",
                    prompt_version=settings.FEEDBACK_PROMPT_VERSION,
                    schema_version=settings.FEEDBACK_SCHEMA_VERSION,
                    attempts=attempt + 1,
                    generated_at=datetime.now(timezone.utc),
                )
                break
            except Exception as exc:  # noqa: BLE001 - isolate AI failures
                # Do not log request bodies, source code, keys, or provider responses.
                logger.warning(
                    "Feedback %s attempt %s failed (%s)",
                    feedback_id,
                    attempt + 1,
                    type(exc).__name__,
                )
                metadata["error_type"] = type(exc).__name__
                metadata["attempts"] = attempt + 1
                if not _is_transient(exc):
                    break
                if attempt + 1 < attempts:
                    time.sleep(_retry_delay(exc, attempt))
        if payload is None:
            payload = deterministic_feedback(stage, context).model_dump_json()
    else:
        status = "FAILED"
    with session_factory.begin() as session:
        session.execute(
            update(Feedback)
            .where(
                Feedback.id == feedback_id,
                Feedback.status == "RUNNING",
                Feedback.execution_id == token,
            )
            .values(
                status=status,
                payload=payload if status == "READY" else None,
                provider=metadata["provider"],
                model=metadata["model"],
                prompt_version=metadata["prompt_version"],
                schema_version=metadata["schema_version"],
                source=metadata["source"],
                input_tokens=metadata["input_tokens"],
                output_tokens=metadata["output_tokens"],
                estimated_cost_usd=metadata["estimated_cost_usd"],
                generation_ms=metadata["generation_ms"],
                attempts=metadata["attempts"],
                error_type=metadata["error_type"],
                generated_at=metadata["generated_at"],
                updated_at=datetime.now(timezone.utc),
            )
        )


def main():
    logging.basicConfig(level=logging.INFO)
    redis = RedisClient()
    queue = SubmissionQueue(redis.client, FEEDBACK_QUEUE)
    provider = build_feedback_provider()
    last_scan = 0
    try:
        while True:
            try:
                if time.monotonic() - last_scan > 5:
                    reconcile_feedback(queue)
                    last_scan = time.monotonic()
                feedback_id = queue.take()
                if feedback_id is not None:
                    process_feedback(feedback_id, provider)
            except Exception as exc:  # noqa: BLE001 - isolate AI failures
                logger.warning(
                    "Feedback worker iteration failed (%s)", type(exc).__name__
                )
                time.sleep(2)
    finally:
        redis.close()


if __name__ == "__main__":
    main()
