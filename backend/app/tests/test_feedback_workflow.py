from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from app.domain.submissions.models import Submission
from app.domain.submissions.results import CaseResult, InternalJudgeResult
from app.feedback.models import Feedback
from app.feedback.policy import StructuredFeedback
from app.feedback.service import initial_feedback
from app.feedback.worker import process_feedback, reconcile_feedback
from app.judge.worker import process_submission
from sqlalchemy.orm import sessionmaker

from .conftest import auth_headers


@pytest.fixture
def judged(db_session, user_factory, problem_factory):
    user, problem = user_factory(), problem_factory()
    problem.hidden_test_cases = '[{"input":{},"expected":"SECRET"}]'
    submission = Submission(
        user_id=user.id,
        problem_id=problem.id,
        code="def solve(): pass",
        language="python",
        status="FAILED",
        result=InternalJudgeResult(
            status="FAILED", verdict_code="FAILED", tests_passed=0, tests_total=1
        ).model_dump_json(),
    )
    db_session.add(submission)
    db_session.commit()
    return user, submission


def test_judge_commit_precedes_feedback_and_failure_cannot_change_verdict(
    db_session, judged
):
    _, submission = judged
    verdict = submission.result
    initial_feedback(db_session, submission)
    db_session.commit()
    row = db_session.query(Feedback).one()
    provider = Mock()

    def fail(stage, context):
        with sessionmaker(bind=db_session.get_bind())() as independent:
            assert independent.get(Submission, submission.id).result == verdict
        assert "SECRET" not in context.model_dump_json()
        raise RuntimeError("provider unavailable")

    provider.generate.side_effect = fail
    process_feedback(row.id, provider, sessionmaker(bind=db_session.get_bind()))
    db_session.refresh(row)
    db_session.refresh(submission)
    assert row.status == "READY"
    assert row.source == "fallback"
    assert row.payload is not None
    assert submission.status == "FAILED" and submission.result == verdict


def test_feedback_waits_for_committed_judge_result(db_session, judged):
    _, submission = judged
    submission.status = "QUEUED"
    submission.result = None
    row = Feedback(submission_id=submission.id, stage="DIAGNOSIS", status="QUEUED")
    db_session.add(row)
    db_session.commit()

    provider = Mock()
    process_feedback(row.id, provider, sessionmaker(bind=db_session.get_bind()))

    db_session.refresh(row)
    assert row.status == "QUEUED"
    provider.generate.assert_not_called()


def test_requests_enforce_order_explicit_solution_and_idempotency(
    client, judged, db_session
):
    user, submission = judged
    path = f"/api/v1/submissions/{submission.id}/feedback"
    headers = auth_headers(user)
    assert (
        client.post(path, headers=headers, json={"action": "hint"}).status_code == 409
    )
    first = client.post(path, headers=headers, json={"action": "diagnosis"})
    again = client.post(path, headers=headers, json={"action": "diagnosis"})
    assert first.status_code == 202 and first.json()["id"] == again.json()["id"]
    provider = Mock()
    provider.generate.return_value = StructuredFeedback(
        strengths=["The code is easy to read."],
        likely_issue="Review the loop boundary.",
        hint="Trace the first failing case.",
        complexity={"time": "O(n)", "space": "O(1)"},
        next_step="Add a boundary test.",
    ).model_dump_json()
    process_feedback(
        first.json()["id"], provider, sessionmaker(bind=db_session.get_bind())
    )
    hint = client.post(path, headers=headers, json={"action": "hint"})
    assert hint.status_code == 202 and hint.json()["stage"] == "HINT"
    assert db_session.query(Feedback).filter_by(stage="SOLUTION").count() == 0
    assert (
        client.post(
            path, headers=headers, json={"action": "hint", "stage": "SOLUTION"}
        ).status_code
        == 422
    )
    solution = client.post(path, headers=headers, json={"action": "show_solution"})
    assert solution.status_code == 202 and solution.json()["stage"] == "SOLUTION"
    assert "payload" not in first.json() and "execution_id" not in first.json()


def test_unauthorized_requests_and_unfinished_judge(
    client, judged, user_factory, db_session
):
    user, submission = judged
    path = f"/api/v1/submissions/{submission.id}/feedback"
    other = auth_headers(user_factory(email="other@example.com"))
    assert client.get(path, headers=other).status_code == 403
    assert (
        client.post(path, headers=other, json={"action": "show_solution"}).status_code
        == 403
    )
    submission.status = "RUNNING"
    db_session.commit()
    assert (
        client.post(
            path, headers=auth_headers(user), json={"action": "diagnosis"}
        ).status_code
        == 409
    )
    assert client.get(path, headers=auth_headers(user)).json() == {
        "eligible": False,
        "items": [],
    }


def test_duplicate_jobs_and_disallowed_output_are_isolated(db_session, judged):
    _, submission = judged
    initial_feedback(db_session, submission)
    db_session.commit()
    row = db_session.query(Feedback).one()
    provider = Mock()
    provider.generate.return_value = (
        '{"category":"arrays","focus":"logic","solution":"LEAK"}'
    )
    factory = sessionmaker(bind=db_session.get_bind())
    process_feedback(row.id, provider, factory)
    process_feedback(row.id, provider, factory)
    db_session.refresh(row)
    assert row.status == "READY" and row.source == "fallback" and row.payload is not None
    assert provider.generate.call_count == 2


def test_invalid_feedback_retries_once_before_saving(db_session, judged):
    _, submission = judged
    initial_feedback(db_session, submission)
    db_session.commit()
    row = db_session.query(Feedback).one()
    provider = Mock()
    provider.generate.side_effect = [
        '{"unexpected":"field"}',
        StructuredFeedback(
            strengths=["The code is readable."],
            likely_issue=None,
            hint=None,
            complexity={"time": "O(n)", "space": "O(1)"},
            next_step="Keep testing edge cases.",
        ).model_dump_json(),
    ]

    process_feedback(row.id, provider, sessionmaker(bind=db_session.get_bind()))

    db_session.refresh(row)
    assert row.status == "READY"
    assert provider.generate.call_count == 2
    assert '"strengths"' in row.payload


def test_recovery_creates_only_first_stage_and_preserves_judge(db_session, judged):
    _, submission = judged
    queue = Mock()
    factory = sessionmaker(bind=db_session.get_bind())
    reconcile_feedback(queue, factory)
    reconcile_feedback(queue, factory)
    row = db_session.query(Feedback).one()
    assert row.stage == "DIAGNOSIS"
    row.status = "RUNNING"
    row.updated_at = datetime.now(timezone.utc) - timedelta(minutes=4)
    db_session.commit()
    reconcile_feedback(queue, factory)
    db_session.refresh(row)
    assert row.status == "FAILED"
    db_session.refresh(submission)
    assert submission.status == "FAILED"


def test_actual_judge_schedules_first_feedback_after_persisting(db_session, judged):
    _, submission = judged
    submission.status = "QUEUED"
    db_session.commit()
    runner = Mock()
    runner.run_case.return_value = CaseResult("PASSED", "wrong answer")
    process_submission(submission.id, runner, sessionmaker(bind=db_session.get_bind()))
    db_session.refresh(submission)
    row = db_session.query(Feedback).one()
    assert submission.status == "FAILED" and submission.result is not None
    assert row.stage == "DIAGNOSIS" and row.status == "QUEUED"
