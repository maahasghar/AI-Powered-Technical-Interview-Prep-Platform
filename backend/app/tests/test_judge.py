import os
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from app.domain.problems.judge_cases import parse_cases
from app.domain.problems.schemas import ProblemCreate, ProblemResponse
from app.domain.submissions.results import CaseResult
from app.domain.submissions.schemas import SubmissionCreate
from app.domain.submissions.service import SubmissionsService
from app.infrastructure.submission_queue import SubmissionQueue
from app.judge.execution_provider import E2BExecutionProvider
from app.judge.worker import evaluate
from e2b import CommandExitException, TimeoutException
from e2b.exceptions import RateLimitException
from redis.exceptions import ConnectionError


def test_queue_outage_preserves_committed_submission():
    client = Mock()
    client.zadd.side_effect = ConnectionError()
    repo = Mock()
    repo.create.return_value = SimpleNamespace(id=17, status="QUEUED")
    service = SubmissionsService(repo, SubmissionQueue(client))
    assert (
        service.create_submission(1, 2, "def solve(): return 1", "python").status
        == "QUEUED"
    )
    repo.create.assert_called_once_with(
        1, 2, "def solve(): return 1", "python", "QUEUED"
    )
    client.zadd.assert_called_once_with("judge:submissions", {"17": 17})


def test_queue_extracts_only_submission_id():
    client = Mock()
    client.bzpopmin.return_value = ("judge:submissions", "42", 42)
    assert SubmissionQueue(client).take() == 42


@pytest.mark.parametrize("language", ["javascript", "java", "cpp", "shell"])
def test_only_python_is_accepted(language):
    with pytest.raises(ValueError):
        SubmissionCreate(problem_id=1, code="pass", language=language)


@pytest.mark.parametrize(
    "cases", ["{}", '[{"input":[],"expected":1}]', '[{"input":{},"expected":NaN}]']
)
def test_invalid_cases_rejected(cases):
    with pytest.raises(ValueError):
        parse_cases(cases)


def test_hidden_cases_never_appear_in_public_problem():
    problem = ProblemCreate(
        title="Example",
        difficulty=1,
        description="Example",
        test_cases="[]",
        hidden_test_cases='[{"input":{"secret":3},"expected":4}]',
    )
    public = ProblemResponse.model_validate(
        {**problem.model_dump(), "id": 1, "is_active": True}
    )
    assert "hidden_test_cases" not in public.model_dump()
    assert "secret" not in public.model_dump_json()


@pytest.mark.parametrize(
    "runner_result,expected",
    [
        (("PASSED", 2), "PASSED"),
        (("PASSED", 9), "FAILED"),
        (("RUNTIME_ERROR", None), "RUNTIME_ERROR"),
        (("TIME_LIMIT_EXCEEDED", None), "TIME_LIMIT_EXCEEDED"),
        (("PASSED", True), "FAILED"),
    ],
)
def test_judge_verdicts_and_hidden_answer_privacy(runner_result, expected):
    runner = Mock()
    runner.run_case.return_value = CaseResult(*runner_result)
    result = evaluate("code", [{"input": {"x": 1}, "expected": 2}], runner)
    assert result.status == expected
    assert result.tests_passed == int(expected == "PASSED")
    assert result.tests_total == 1
    assert runner.run_case.call_args.args[:2] == ("code", {"x": 1})
    assert "expected" not in result.model_dump_json()


def test_empty_test_suite_cannot_pass():
    assert evaluate("code", [], Mock()).status == "RUNTIME_ERROR"


def e2b_provider(sandbox):
    factory = Mock()
    factory.create.return_value = sandbox
    provider = E2BExecutionProvider(
        api_key="test-key", request_timeout=3, sandbox_factory=factory
    )
    provider._sleep_with_backoff = Mock()
    return provider, factory


def test_e2b_provider_captures_stdout_and_cleans_up_sandbox():
    sandbox = Mock()
    sandbox.commands.run.return_value = SimpleNamespace(
        stdout="2\n", stderr="", exit_code=0, error=None
    )
    provider, factory = e2b_provider(sandbox)

    result = provider.run_case("def solve(x): return x + 1", {"x": 1}, seconds=2)

    assert result.status == "PASSED"
    assert result.actual == 2
    factory.create.assert_called_once_with(
        api_key="test-key",
        timeout=10,
        request_timeout=3.0,
        secure=True,
        allow_internet_access=False,
    )
    assert sandbox.files.write.call_count == 3
    sandbox.commands.run.assert_called_once_with(
        "python /tmp/runner.py", timeout=2, request_timeout=3.0
    )
    sandbox.kill.assert_called_once_with(request_timeout=3.0)


def test_e2b_provider_preserves_wrong_answer_for_worker_evaluation():
    sandbox = Mock()
    sandbox.commands.run.return_value = SimpleNamespace(
        stdout="1", stderr="", exit_code=0, error=None
    )
    provider, _ = e2b_provider(sandbox)

    outcome = provider.run_case("def solve(x): return x", {"x": 1}, seconds=2)
    runner = Mock()
    runner.run_case.return_value = outcome
    result = evaluate("code", [{"input": {"x": 1}, "expected": 2}], runner)

    assert outcome.status == "PASSED"
    assert result.status == "FAILED"


def test_e2b_provider_maps_user_runtime_exception_and_cleans_up():
    sandbox = Mock()
    sandbox.commands.run.side_effect = CommandExitException(
        "Traceback", "", 1, "command exited"
    )
    provider, _ = e2b_provider(sandbox)

    result = provider.run_case("def solve(): raise RuntimeError", {}, seconds=2)

    assert result.status == "RUNTIME_ERROR"
    assert result.verdict_code == "RUNTIME_ERROR"
    sandbox.kill.assert_called_once_with(request_timeout=3.0)


def test_e2b_provider_maps_execution_timeout_and_cleans_up():
    sandbox = Mock()
    sandbox.commands.run.side_effect = TimeoutException("execution timed out")
    provider, _ = e2b_provider(sandbox)

    result = provider.run_case("def solve():\n while True: pass", {}, seconds=2)

    assert result.status == "TIME_LIMIT_EXCEEDED"
    sandbox.kill.assert_called_once_with(request_timeout=3.0)


def test_e2b_provider_retries_transient_api_failures_with_cleanup():
    sandbox = Mock()
    sandbox.commands.run.return_value = SimpleNamespace(
        stdout="7", stderr="", exit_code=0, error=None
    )
    factory = Mock()
    factory.create.side_effect = [RateLimitException("retry"), sandbox]
    provider = E2BExecutionProvider(
        api_key="test-key", request_timeout=3, sandbox_factory=factory
    )
    provider._sleep_with_backoff = Mock()

    result = provider.run_case("def solve(): return 7", {}, seconds=2)

    assert result.status == "PASSED"
    assert factory.create.call_count == 2
    provider._sleep_with_backoff.assert_called_once()
    sandbox.kill.assert_called_once_with(request_timeout=3.0)


def test_e2b_provider_returns_unavailable_after_api_failure():
    factory = Mock()
    factory.create.side_effect = RateLimitException("over quota")
    provider = E2BExecutionProvider(
        api_key="test-key", request_timeout=3, max_attempts=1, sandbox_factory=factory
    )

    result = provider.run_case("def solve(): return 1", {}, seconds=2)

    assert result.status == "RUNTIME_ERROR"
    assert result.verdict_code == "UNAVAILABLE"


def test_e2b_provider_rejects_malformed_stdout_and_cleans_up():
    sandbox = Mock()
    sandbox.commands.run.return_value = SimpleNamespace(
        stdout="not-json", stderr="", exit_code=0, error=None
    )
    provider, _ = e2b_provider(sandbox)

    result = provider.run_case("def solve(): return object()", {}, seconds=2)

    assert result.status == "RUNTIME_ERROR"
    assert result.verdict_code == "RUNTIME_ERROR"
    sandbox.kill.assert_called_once_with(request_timeout=3.0)


def test_e2b_provider_cleans_up_after_write_failure():
    sandbox = Mock()
    sandbox.files.write.side_effect = TimeoutException("request timeout")
    provider, _ = e2b_provider(sandbox)

    result = provider.run_case("def solve(): return 1", {}, seconds=2)

    assert result.verdict_code == "UNAVAILABLE"
    assert sandbox.kill.call_count == provider.max_attempts
    sandbox.kill.assert_called_with(request_timeout=3.0)


@pytest.mark.skipif(os.getenv("RUN_REDIS_TESTS") != "1", reason="Requires Redis")
def test_real_redis_deduplication_and_dequeue(monkeypatch):
    from uuid import uuid4

    import redis
    from app.core.config import settings
    from app.infrastructure import submission_queue

    client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    key = f"judge-test:{uuid4().hex}"
    monkeypatch.setattr(submission_queue, "QUEUE_KEY", key)
    queue = SubmissionQueue(client)
    try:
        assert queue.enqueue(2)
        assert queue.enqueue(1)
        assert queue.enqueue(1)
        assert queue.take() == 1
        assert queue.take() == 2
        assert client.zcard(key) == 0
    finally:
        client.delete(key)
        client.close()


