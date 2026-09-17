"""Internal judge models. Never use these models as API response schemas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field

SubmissionStatus = Literal[
    "QUEUED", "RUNNING", "PASSED", "FAILED", "RUNTIME_ERROR", "TIME_LIMIT_EXCEEDED"
]
VerdictCode = Literal[
    "PASSED",
    "FAILED",
    "RUNTIME_ERROR",
    "TIME_LIMIT_EXCEEDED",
    "UNSUPPORTED_LANGUAGE",
    "UNAVAILABLE",
    "INVALID_TESTS",
    "OUTPUT_LIMIT",
]


@dataclass
class CaseResult:
    status: SubmissionStatus
    actual: Any = None
    runtime_ms: float | None = None
    memory_bytes: int | None = None
    diagnostics: str | None = None
    verdict_code: VerdictCode | None = None


class InternalJudgeResult(BaseModel):
    status: SubmissionStatus
    verdict_code: VerdictCode
    tests_passed: int | None = Field(default=None, ge=0)
    tests_total: int | None = Field(default=None, ge=0)
    runtime_ms: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    memory_bytes: int | None = Field(default=None, ge=0)
    # Diagnostics are logged by the worker, never persisted as public results.
    diagnostics: str | None = Field(default=None, exclude=True)
