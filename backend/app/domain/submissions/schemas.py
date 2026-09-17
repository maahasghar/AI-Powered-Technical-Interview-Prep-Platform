from __future__ import annotations

import json
import math
from datetime import datetime
from typing import Literal

from app.domain.submissions.results import SubmissionStatus
from pydantic import BaseModel, Field, field_validator, model_validator


class SubmissionCreate(BaseModel):
    problem_id: int
    code: str = Field(min_length=1, max_length=64000)
    language: Literal["python"] = "python"

    @field_validator("code")
    @classmethod
    def validate_code(cls, value):
        if len(value.encode()) > 64000 or "\x00" in value:
            raise ValueError("Code must be at most 64 KB and contain no null bytes")
        return value


class SubmissionUpdate(BaseModel):
    code: str | None = None
    language: str | None = None
    status: str | None = None
    result: str | None = None


PUBLIC_MESSAGES = {
    "QUEUED": "Your submission is queued.",
    "RUNNING": "Your submission is being evaluated.",
    "PASSED": "All tests passed.",
    "FAILED": "Your solution did not pass all tests.",
    "RUNTIME_ERROR": "Your code could not complete successfully.",
    "TIME_LIMIT_EXCEEDED": "Your solution exceeded the time limit.",
}
ERROR_MESSAGES = {
    "UNSUPPORTED_LANGUAGE": "Only Python submissions are supported.",
    "UNAVAILABLE": "Evaluation is temporarily unavailable. Please try again later.",
    "INVALID_TESTS": "Evaluation is temporarily unavailable. Please try again later.",
    "OUTPUT_LIMIT": "Your solution produced too much output.",
}


class PublicSubmissionResult(BaseModel):
    message: str
    tests_passed: int | None = None
    tests_total: int | None = None
    runtime_ms: float | None = None
    memory_bytes: int | None = None

    model_config = {"extra": "forbid"}


def public_result(raw, status):
    if status in {"QUEUED", "RUNNING"}:
        return None
    # Treat stored data as untrusted, including historical JSON strings. Never
    # echo a message, diagnostic, extra field, or nested object from storage.
    if isinstance(raw, str):
        try:
            raw = json.loads(raw) if len(raw) <= 1_000_000 else {}
        except (ValueError, RecursionError):
            raw = {}
    if isinstance(raw, PublicSubmissionResult):
        raw = raw.model_dump()
    if not isinstance(raw, dict):
        raw = {}

    def number(key, maximum, integer=False):
        value = raw.get(key)
        if type(value) not in ((int,) if integer else (int, float)):
            return None
        if not 0 <= value <= maximum or not math.isfinite(value):
            return None
        return value

    # Support the previous aggregate names without returning the old blob.
    raw = {
        **raw,
        "tests_passed": raw.get("tests_passed", raw.get("passed")),
        "tests_total": raw.get("tests_total", raw.get("total")),
    }
    passed = number("tests_passed", 40, True)
    total = number("tests_total", 40, True)
    if passed is None or total is None or passed > total:
        passed = total = None
    code = raw.get("verdict_code")
    message = PUBLIC_MESSAGES[status]
    if status == "RUNTIME_ERROR" and isinstance(code, str):
        message = ERROR_MESSAGES.get(code, message)
    return PublicSubmissionResult(
        message=message,
        tests_passed=passed,
        tests_total=total,
        runtime_ms=number("runtime_ms", 180_000),
        memory_bytes=number("memory_bytes", 128 * 1024 * 1024, True),
    )


class SubmissionResponse(BaseModel):
    id: int
    user_id: int
    problem_id: int
    code: str
    language: str
    status: SubmissionStatus
    result: PublicSubmissionResult | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @model_validator(mode="before")
    @classmethod
    def project_public_result(cls, value):
        # Apply to every route using this response model: creation, detail,
        # history, problem history and deletion. Admins get the same projection.
        fields = cls.model_fields
        data = {
            name: (
                value.get(name)
                if isinstance(value, dict)
                else getattr(value, name, None)
            )
            for name in fields
        }
        if not isinstance(data["status"], str) or data["status"] not in PUBLIC_MESSAGES:
            data["status"] = "RUNTIME_ERROR"
        data["result"] = public_result(data["result"], data["status"])
        return data

    model_config = {"from_attributes": True}
