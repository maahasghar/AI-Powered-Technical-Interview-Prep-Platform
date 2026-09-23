"""Run with python -m app.judge.worker. PostgreSQL is the durable job ledger."""

import logging
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.domain.auth.models import User  # noqa: F401 - register referenced table
from app.domain.problems.judge_cases import parse_cases
from app.domain.problems.models import Problem
from app.domain.submissions.models import Submission
from app.domain.submissions.results import InternalJudgeResult
from app.infrastructure.db import SessionLocal
from app.infrastructure.redis import RedisClient
from app.infrastructure.submission_queue import SubmissionQueue
from app.infrastructure.worker_health import heartbeat
from app.judge.execution_provider import E2BExecutionProvider
from sqlalchemy import update

logger = logging.getLogger(__name__)
LEASE_SECONDS = 180


def reconcile(queue, session_factory=SessionLocal):
    now = datetime.now(timezone.utc)
    with session_factory.begin() as session:
        session.execute(
            update(Submission)
            .where(
                Submission.status == "RUNNING",
                Submission.updated_at < now - timedelta(seconds=LEASE_SECONDS),
            )
            .values(status="QUEUED", execution_id=None, updated_at=now)
        )
        ids = (
            session.query(Submission.id)
            .filter(Submission.status == "QUEUED")
            .order_by(Submission.id)
            .limit(1000)
            .all()
        )
    for (submission_id,) in ids:
        if not queue.enqueue(submission_id):
            break


def evaluate(code, cases, runner):
    if not cases:
        return InternalJudgeResult(status="RUNTIME_ERROR", verdict_code="INVALID_TESTS")
    started = time.monotonic()
    passed = 0
    runtime_ms = None
    memory_bytes = None
    for case in cases:
        remaining = 90 - 20 - (time.monotonic() - started)
        if remaining <= 0:
            outcome = InternalJudgeResult(
                status="TIME_LIMIT_EXCEEDED",
                verdict_code="TIME_LIMIT_EXCEEDED",
            )
            return outcome
        outcome = runner.run_case(code, case["input"], min(6, remaining))
        if outcome.runtime_ms is not None:
            runtime_ms = (runtime_ms or 0) + outcome.runtime_ms
        if outcome.memory_bytes is not None:
            memory_bytes = max(memory_bytes or 0, outcome.memory_bytes)
        if outcome.status == "PASSED":
            if outcome.actual != case["expected"]:
                return InternalJudgeResult(
                    status="FAILED",
                    verdict_code="FAILED",
                    tests_passed=passed,
                    tests_total=len(cases),
                    runtime_ms=runtime_ms,
                    memory_bytes=memory_bytes,
                    diagnostics=outcome.diagnostics,
                )
            passed += 1
        else:
            return InternalJudgeResult(
                status=outcome.status,
                verdict_code=outcome.verdict_code or outcome.status,
                tests_passed=passed,
                tests_total=len(cases),
                runtime_ms=runtime_ms,
                memory_bytes=memory_bytes,
                diagnostics=outcome.diagnostics,
            )
    return InternalJudgeResult(
        status="PASSED",
        verdict_code="PASSED",
        tests_passed=passed,
        tests_total=len(cases),
        runtime_ms=runtime_ms,
        memory_bytes=memory_bytes,
    )


def process_submission(submission_id, runner, session_factory=SessionLocal):
    execution_id = uuid4().hex
    with session_factory.begin() as session:
        claimed = session.execute(
            update(Submission)
            .where(
                Submission.id == submission_id,
                Submission.status == "QUEUED",
            )
            .values(
                status="RUNNING",
                execution_id=execution_id,
                updated_at=datetime.now(timezone.utc),
            )
        )
        if not claimed.rowcount:
            return
        submission = session.get(Submission, submission_id)
        problem = session.get(Problem, submission.problem_id)
        code, language = submission.code, submission.language
        sample_tests = problem.test_cases if problem else "[]"
        hidden_tests = problem.hidden_test_cases if problem else "[]"
    try:
        if language != "python":
            result = InternalJudgeResult(
                status="RUNTIME_ERROR", verdict_code="UNSUPPORTED_LANGUAGE"
            )
        else:
            cases = parse_cases(sample_tests) + parse_cases(hidden_tests)
            result = evaluate(code, cases, runner)
    except Exception:
        logger.exception("Judging failed for submission %s", submission_id)
        result = InternalJudgeResult(
            status="RUNTIME_ERROR", verdict_code="UNAVAILABLE"
        )
    if result.diagnostics:
        logger.warning(
            "Submission %s diagnostics: %r", submission_id, result.diagnostics
        )
    with session_factory.begin() as session:
        persisted = session.execute(
            update(Submission)
            .where(
                Submission.id == submission_id,
                Submission.status == "RUNNING",
                Submission.execution_id == execution_id,
            )
            .values(
                status=result.status,
                result=result.model_dump_json(),
                updated_at=datetime.now(timezone.utc),
            )
        )

    if persisted.rowcount:
        try:
            from app.feedback.service import initial_feedback

            with session_factory.begin() as session:
                saved = session.get(Submission, submission_id)
                if saved is not None:
                    initial_feedback(session, saved)
        except Exception:
            logger.exception(
                "Feedback scheduling failed for submission %s", submission_id
            )


def main():
    logging.basicConfig(level=logging.INFO)
    redis = RedisClient()
    queue = SubmissionQueue(redis.client)
    runner = E2BExecutionProvider()
    last_reconcile = 0
    try:
        while True:
            try:
                if time.monotonic() - last_reconcile > 10:
                    reconcile(queue)
                    last_reconcile = time.monotonic()
                heartbeat(redis.client, "judge")
                submission_id = queue.take()
                if submission_id is not None:
                    process_submission(submission_id, runner)
            except Exception:
                logger.exception("Worker iteration failed; retrying")
                time.sleep(2)
    finally:
        redis.close()


if __name__ == "__main__":
    main()
