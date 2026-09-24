import json
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from app.core.container import container
from app.domain.submissions.models import Submission
from app.domain.submissions.results import CaseResult
from app.judge.worker import process_submission, reconcile
from sqlalchemy.orm import sessionmaker

from .conftest import auth_headers


def test_api_enqueues_and_hides_judge_tests(
    client, user_factory, problem_factory, db_session
):
    user, problem = user_factory(), problem_factory()
    problem.hidden_test_cases = '[{"input":{"x":1},"expected":2}]'
    db_session.commit()
    headers = auth_headers(user)
    response = client.post(
        "/api/v1/submissions",
        headers=headers,
        json={"problem_id": problem.id, "code": "def solve(x): return x+1"},
    )
    assert response.status_code == 201
    assert response.json()["status"] == "QUEUED"
    container.redis.client.zadd.assert_called_once_with(
        "judge:submissions", {str(response.json()["id"]): response.json()["id"]}
    )
    public = client.get(f"/api/v1/problems/{problem.id}", headers=headers).json()
    assert "hidden_test_cases" not in public


def test_worker_claims_once_and_persists_result(
    db_session, user_factory, problem_factory
):
    user, problem = user_factory(), problem_factory()
    problem.test_cases = '[{"input":{"x":1},"expected":2}]'
    problem.hidden_test_cases = '[{"input":{"x":8},"expected":9}]'
    row = Submission(
        user_id=user.id,
        problem_id=problem.id,
        code="code",
        language="python",
        status="QUEUED",
    )
    db_session.add(row)
    db_session.commit()
    runner = Mock()
    runner.run_case.side_effect = [CaseResult("PASSED", 2), CaseResult("PASSED", 9)]
    factory = sessionmaker(bind=db_session.get_bind())
    process_submission(row.id, runner, factory)
    process_submission(row.id, runner, factory)
    db_session.refresh(row)
    assert row.status == "PASSED"
    assert json.loads(row.result)["tests_passed"] == 2
    assert json.loads(row.result)["tests_total"] == 2
    assert runner.run_case.call_count == 2


def test_reconcile_recovers_queued_and_abandoned_jobs(
    db_session, user_factory, problem_factory
):
    user, problem = user_factory(), problem_factory()
    rows = [
        Submission(
            user_id=user.id,
            problem_id=problem.id,
            code="code",
            language="python",
            status=status,
            updated_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        )
        for status in ["QUEUED", "RUNNING", "PASSED"]
    ]
    db_session.add_all(rows)
    db_session.commit()
    queue = Mock()
    reconcile(queue, sessionmaker(bind=db_session.get_bind()))
    assert [call.args[0] for call in queue.enqueue.call_args_list] == [
        rows[0].id,
        rows[1].id,
    ]
    db_session.refresh(rows[1])
    assert rows[1].status == "QUEUED"


def test_old_worker_cannot_overwrite_reclaimed_submission(
    db_session, user_factory, problem_factory
):
    user, problem = user_factory(), problem_factory()
    problem.test_cases = '[{"input":{},"expected":1}]'
    row = Submission(
        user_id=user.id,
        problem_id=problem.id,
        code="code",
        language="python",
        status="QUEUED",
    )
    db_session.add(row)
    db_session.commit()
    factory = sessionmaker(bind=db_session.get_bind())

    def replacement_finishes(*args):
        with factory.begin() as session:
            current = session.get(Submission, row.id)
            assert current.status == "RUNNING"
            current.execution_id = "replacement"
            current.status = "FAILED"
        return CaseResult("PASSED", 1)

    runner = Mock()
    runner.run_case.side_effect = replacement_finishes
    process_submission(row.id, runner, factory)
    db_session.refresh(row)
    assert row.status == "FAILED"


def test_api_to_redis_to_e2b_provider_to_result(
    client, user_factory, problem_factory, db_session, monkeypatch
):
    from uuid import uuid4

    import redis
    from app.core.config import settings
    from app.infrastructure import submission_queue
    from app.judge.execution_provider import E2BExecutionProvider

    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    key = f"judge-test:{uuid4().hex}"
    monkeypatch.setattr(submission_queue, "QUEUE_KEY", key)
    monkeypatch.setattr(container.redis, "client", redis_client)
    queue = submission_queue.SubmissionQueue(redis_client)
    user, problem = user_factory(), problem_factory()
    problem.test_cases = '[{"input":{"x":1},"expected":2}]'
    problem.hidden_test_cases = '[{"input":{"x":4},"expected":5}]'
    db_session.commit()
    headers = auth_headers(user)
    try:
        created = client.post(
            "/api/v1/submissions",
            headers=headers,
            json={"problem_id": problem.id, "code": "def solve(x): return x + 1"},
        )
        assert created.status_code == 201
        assert created.json()["status"] == "QUEUED"
        submission_id = queue.take()
        assert submission_id == created.json()["id"]
        sandbox = Mock()
        sandbox.commands.run.side_effect = [
            Mock(stdout="2", stderr="", exit_code=0, error=None),
            Mock(stdout="5", stderr="", exit_code=0, error=None),
        ]
        sandbox_factory = Mock()
        sandbox_factory.create.return_value = sandbox
        process_submission(
            submission_id,
            E2BExecutionProvider(api_key="test-key", sandbox_factory=sandbox_factory),
            sessionmaker(bind=db_session.get_bind()),
        )
        db_session.expire_all()
        result = client.get(
            f"/api/v1/submissions/{submission_id}", headers=headers
        ).json()
        assert result["status"] == "PASSED"
        assert result["result"]["tests_passed"] == 2
        assert result["result"]["tests_total"] == 2
        assert result["result"]["runtime_ms"] > 0
        assert sandbox_factory.create.call_count == 2
        assert sandbox.kill.call_count == 2
    finally:
        redis_client.delete(key)
        redis_client.close()


def test_runtime_diagnostics_stay_in_logs(
    db_session, user_factory, problem_factory, caplog
):
    from app.domain.submissions.schemas import SubmissionResponse

    user, problem = user_factory(), problem_factory()
    problem.test_cases = '[{"input":{},"expected":1}]'
    row = Submission(
        user_id=user.id,
        problem_id=problem.id,
        code="code",
        language="python",
        status="QUEUED",
    )
    db_session.add(row)
    db_session.commit()
    runner = Mock()
    runner.run_case.return_value = CaseResult(
        "RUNTIME_ERROR", diagnostics="PRIVATE_TRACE /opt/judge/runner.py"
    )
    process_submission(row.id, runner, sessionmaker(bind=db_session.get_bind()))
    db_session.refresh(row)
    assert "PRIVATE_TRACE" in caplog.text
    assert "PRIVATE_TRACE" not in row.result
    assert (
        "PRIVATE_TRACE" not in SubmissionResponse.model_validate(row).model_dump_json()
    )
