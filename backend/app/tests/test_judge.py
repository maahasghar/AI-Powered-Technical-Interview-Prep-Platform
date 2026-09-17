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
from app.judge.docker_runner import DockerRunner, evaluate
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


def test_container_restrictions_are_explicit():
    command = DockerRunner().command("example", "code", {"x": 1})
    for option, value in {
        "--network": "none",
        "--cap-drop": "ALL",
        "--user": "65534:65534",
        "--memory": "128m",
        "--memory-swap": "128m",
        "--pids-limit": "32",
        "--cpus": "1",
        "--log-driver": "none",
    }.items():
        assert command[command.index(option) + 1] == value
    assert "--read-only" in command
    assert "no-new-privileges=true" in command
    assert not any(
        option in command for option in ["--privileged", "--volume", "--env", "--mount"]
    )


@pytest.mark.skipif(
    os.getenv("RUN_DOCKER_TESTS") != "1", reason="Requires built judge image and Docker"
)
@pytest.mark.parametrize(
    "code,expected",
    [
        ("def solve(x): return x + 1", "PASSED"),
        ("def solve(x): return 0", "FAILED"),
        ("def solve(x): raise ValueError('secret')", "RUNTIME_ERROR"),
        ("def solve(x):\n while True: pass", "TIME_LIMIT_EXCEEDED"),
        ("def solve(x):\n import time\n time.sleep(60)", "TIME_LIMIT_EXCEEDED"),
        ("def solve(x): return bytearray(512 * 1024 * 1024)", "RUNTIME_ERROR"),
        (
            "def solve(x):\n import os\n while True: os.write(1, b'x' * 8192)",
            "RUNTIME_ERROR",
        ),
    ],
)
def test_real_docker_verdicts(code, expected):
    assert (
        evaluate(code, [{"input": {"x": 1}, "expected": 2}], DockerRunner()).status
        == expected
    )


@pytest.mark.skipif(
    os.getenv("RUN_DOCKER_TESTS") != "1", reason="Requires built judge image and Docker"
)
def test_real_container_isolation():
    code = """def solve():
 import os, socket
 checks = [os.getuid() == 65534, os.getenv("JWT_SECRET") is None, not os.path.exists("/var/run/docker.sock")]
 try:
  open("/root-write", "w").write("bad")
  checks.append(False)
 except OSError:
  checks.append(True)
 try:
  socket.create_connection(("1.1.1.1", 53), timeout=0.5)
  checks.append(False)
 except OSError:
  checks.append(True)
 return all(checks)
"""
    outcome = DockerRunner().run_case(code, {})
    assert outcome.status == "PASSED"
    assert outcome.actual is True
    assert outcome.runtime_ms > 0


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


@pytest.mark.skipif(os.getenv("RUN_DOCKER_TESTS") != "1", reason="Requires Docker")
def test_real_runtime_and_sampled_memory():
    outcome = DockerRunner().run_case(
        "def solve():\n import time\n memory = bytearray(16 * 1024 * 1024)\n time.sleep(3)\n return len(memory)",
        {},
    )
    assert outcome.status == "PASSED"
    assert outcome.actual == 16 * 1024 * 1024
    assert outcome.runtime_ms >= 3000
    assert outcome.memory_bytes is not None and outcome.memory_bytes >= 16 * 1024 * 1024
