import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from app.api.v1.routers.problems_router import get_problems_service
from app.api.v1.routers.submissions_router import get_submissions_service, router
from app.domain.auth.service import AuthService
from app.domain.submissions.results import CaseResult, InternalJudgeResult
from app.domain.submissions.schemas import SubmissionResponse, public_result
from app.judge.docker_runner import evaluate, memory_sample
from fastapi import FastAPI
from fastapi.testclient import TestClient

SECRET = "HIDDEN_SENTINEL /opt/judge/runner.py container=abc Traceback docker run"


def row(result, status="RUNTIME_ERROR"):
    return SimpleNamespace(
        id=1,
        user_id=1,
        problem_id=1,
        code="def solve(): pass",
        language="python",
        status=status,
        result=result,
        execution_id=SECRET,
        created_at=None,
        updated_at=None,
    )


@pytest.mark.parametrize("role", ["user", "admin"])
@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/submissions/1"),
        ("GET", "/submissions/me"),
        ("GET", "/submissions/problem/1"),
        ("POST", "/submissions"),
        ("DELETE", "/submissions/1"),
    ],
)
def test_all_submission_routes_allowlist_results(role, method, path):
    raw = json.dumps(
        {
            "message": SECRET,
            "error": SECRET,
            "diagnostics": SECRET,
            "hidden_tests": [{"input": SECRET, "expected": SECRET}],
            "container": SECRET,
            "command": SECRET,
            "stdout": SECRET,
            "verdict_code": SECRET,
            "tests_passed": 2,
            "tests_total": 4,
            "runtime_ms": 12.5,
            "memory_bytes": 4096,
        }
    )
    submission = row(raw)
    service = Mock()
    service.get_submission.return_value = submission
    service.create_submission.return_value = submission
    service.delete_submission.return_value = submission
    for method_name in [
        "get_user_submissions",
        "get_all_submissions",
        "get_problem_submissions",
    ]:
        getattr(service, method_name).return_value = [submission]
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[AuthService.get_current_user] = lambda: SimpleNamespace(
        id=1, role=role
    )
    app.dependency_overrides[get_submissions_service] = lambda: service
    problems = Mock()
    problems.get_problem.return_value = SimpleNamespace(is_active=True)
    app.dependency_overrides[get_problems_service] = lambda: problems
    with TestClient(app) as client:
        response = client.request(
            method,
            path,
            json={"problem_id": 1, "code": "pass"} if method == "POST" else None,
        )
    assert response.status_code in (200, 201)
    assert SECRET not in response.text
    payload = response.json()
    if isinstance(payload, list):
        payload = payload[0]
    assert payload["result"] == {
        "message": "Your code could not complete successfully.",
        "tests_passed": 2,
        "tests_total": 4,
        "runtime_ms": 12.5,
        "memory_bytes": 4096,
    }
    assert "execution_id" not in payload


@pytest.mark.parametrize(
    "raw",
    [
        SECRET,
        '{"bad":',
        "[]",
        None,
        json.dumps({"message": SECRET, "passed": 1, "total": 2}),
    ],
)
def test_legacy_and_malformed_storage_fails_closed(raw):
    value = SubmissionResponse.model_validate(row(raw)).model_dump_json()
    assert SECRET not in value
    assert "Your code could not complete successfully." in value


@pytest.mark.parametrize(
    "field,value",
    [
        ("tests_passed", SECRET),
        ("tests_passed", True),
        ("tests_total", -1),
        ("runtime_ms", float("nan")),
        ("runtime_ms", float("inf")),
        ("runtime_ms", SECRET),
        ("memory_bytes", {"path": SECRET}),
        ("memory_bytes", -1),
        ("memory_bytes", 10**1000),
    ],
)
def test_invalid_metrics_are_not_coerced_or_exposed(field, value):
    data = {"tests_passed": 1, "tests_total": 2, field: value}
    result = public_result(data, "FAILED")
    assert getattr(result, field) is None
    assert SECRET not in result.model_dump_json()


def test_inconsistent_counts_are_discarded():
    result = public_result({"passed": 9, "total": 2}, "FAILED")
    assert result.tests_passed is None and result.tests_total is None


@pytest.mark.parametrize("status", ["QUEUED", "RUNNING"])
def test_pending_results_are_not_exposed(status):
    assert SubmissionResponse.model_validate(row(SECRET, status)).result is None


def test_unknown_status_and_verdict_cannot_leak_text():
    response = SubmissionResponse.model_validate(
        row(json.dumps({"verdict_code": SECRET}), SECRET)
    )
    assert response.status == "RUNTIME_ERROR"
    assert SECRET not in response.model_dump_json()


def test_internal_model_does_not_serialize_diagnostics():
    internal = InternalJudgeResult(
        status="RUNTIME_ERROR", verdict_code="RUNTIME_ERROR", diagnostics=SECRET
    )
    assert internal.diagnostics == SECRET
    assert SECRET not in internal.model_dump_json()


def test_metrics_aggregate_without_returning_actual_outputs():
    runner = Mock()
    runner.run_case.side_effect = [
        CaseResult("PASSED", 1, 10, 1000),
        CaseResult("PASSED", 2, 20, 2000),
    ]
    result = evaluate(
        "code", [{"input": {}, "expected": 1}, {"input": {}, "expected": 2}], runner
    )
    assert result.runtime_ms == 30
    assert result.memory_bytes == 2000
    assert result.tests_passed == 2
    assert "actual" not in result.model_dump()


@pytest.mark.parametrize(
    "sample,expected",
    [
        ("1.5MiB / 128MiB", 1572864),
        ("\x1b[2J\x1b[H1.5MiB / 128MiB", 1572864),
        ("0B / 128MiB", None),
        ("-- / --", None),
    ],
)
def test_memory_samples(sample, expected):
    assert memory_sample(sample) == expected
