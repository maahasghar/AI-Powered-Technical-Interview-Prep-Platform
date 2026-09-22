"""The first two stages render only approved coaching, never model-authored solutions."""

from __future__ import annotations

import json
from typing import Literal

from app.domain.submissions.results import InternalJudgeResult
from app.domain.submissions.schemas import public_result
from pydantic import BaseModel, ConfigDict, Field

CATEGORIES = {
    "arrays": "arrays and sequences",
    "strings": "string processing",
    "graphs": "graphs and dependencies",
    "trees": "tree traversal",
    "optimization": "optimization",
    "search": "search",
    "general": "general problem solving",
}
FOCUSES = {
    "edge_cases": "Review how your code handles boundary cases.",
    "logic": "Review whether your code matches each part of the problem contract.",
    "performance": "Review the amount of work your code performs as input size grows.",
    "return_value": "Review the type and shape of the value your function returns.",
    "runtime": "Review operations that could raise exceptions.",
    "reflection": "Reflect on your reasoning and the limits of the approach you used.",
}
APPROACHES = {
    "lookup": "Consider whether keeping previously seen information would avoid repeated searches.",
    "two_pointers": "Consider tracking two positions in the input instead of examining every pair.",
    "window": "Consider maintaining information about a moving section of the input.",
    "stack": "Consider whether the most recently encountered unfinished item should be handled first.",
    "traversal": "Consider exploring connected elements while tracking which ones you have visited.",
    "dynamic_programming": "Consider whether smaller subproblems repeat and their results could be reused.",
    "binary_search": "Consider whether a decision can eliminate half of the remaining search space.",
    "sorting": "Consider whether ordering the data would make its relationships easier to inspect.",
    "invariant": "Identify a property that should remain true as your algorithm progresses.",
    "contract": "Compare your function inputs and return value with the stated contract.",
}


class Complexity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    time: str = Field(min_length=1, max_length=200)
    space: str = Field(min_length=1, max_length=200)


class StructuredFeedback(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strengths: list[str] = Field(min_length=1, max_length=5)
    likely_issue: str | None = Field(default=None, max_length=2000)
    hint: str | None = Field(default=None, max_length=2000)
    complexity: Complexity
    next_step: str = Field(min_length=1, max_length=2000)


OUTPUT_MODELS = {
    stage: StructuredFeedback for stage in ("DIAGNOSIS", "HINT", "SOLUTION")
}


class FeedbackContext(BaseModel):
    """Allowlisted, candidate-relevant data that may be sent to the model."""

    model_config = ConfigDict(extra="forbid")

    problem_title: str = Field(max_length=500)
    problem_description: str = Field(max_length=100_000)
    problem_categories: list[str] = Field(max_length=20)
    public_examples: list[dict[str, object]] = Field(max_length=20)
    language: Literal["python"]
    submitted_code: str = Field(max_length=64_000)
    verdict: Literal["PASSED", "FAILED", "RUNTIME_ERROR", "TIME_LIMIT_EXCEEDED"]
    tests_passed: int | None = Field(default=None, ge=0)
    tests_total: int | None = Field(default=None, ge=1)
    runtime_ms: float | None = Field(default=None, ge=0)
    memory_bytes: int | None = Field(default=None, ge=0)
    error_message: str | None = Field(default=None, max_length=500)


def deterministic_feedback(stage, context: FeedbackContext):
    if context.verdict == "PASSED":
        strengths = ["The submission passed the deterministic judge tests."]
        issue = None
        next_step = "Review the passing solution for clarity and consider whether its complexity can be improved."
    elif context.verdict == "RUNTIME_ERROR":
        strengths = ["The submission was accepted by the judge as valid Python input."]
        issue = (
            context.error_message
            or "The submission raised an exception during evaluation."
        )
        next_step = "Trace the failing operation with the smallest input and add a guard for that case."
    elif context.verdict == "TIME_LIMIT_EXCEEDED":
        strengths = ["The submission was accepted by the judge and began execution."]
        issue = "The submission did not finish within the judge time limit."
        next_step = "Identify the innermost repeated work and look for a way to avoid recomputing it."
    else:
        strengths = [
            "The submission was accepted by the judge and produced an evaluable result."
        ]
        issue = "The implementation does not yet produce the expected result for every judge case."
        next_step = "Compare the first failing case with the problem contract and trace the state change that leads to the wrong result."
    return StructuredFeedback(
        strengths=strengths,
        likely_issue=issue,
        hint=(next_step if stage == "HINT" else None),
        complexity=Complexity(time="Not available", space="Not available"),
        next_step=next_step,
    )


def validate_feedback(stage, payload):
    return OUTPUT_MODELS[stage].model_validate_json(payload)


def judge_ready(submission):
    if (
        submission.status
        not in {"PASSED", "FAILED", "RUNTIME_ERROR", "TIME_LIMIT_EXCEEDED"}
        or not submission.result
    ):
        return False
    try:
        result = InternalJudgeResult.model_validate_json(submission.result)
    except ValueError:
        return False
    return (
        result.status == submission.status
        and result.verdict_code
        in {"PASSED", "FAILED", "RUNTIME_ERROR", "TIME_LIMIT_EXCEEDED", "OUTPUT_LIMIT"}
        and result.tests_total is not None
        and result.tests_total > 0
        and result.tests_passed is not None
        and 0 <= result.tests_passed <= result.tests_total
    )


def build_feedback_context(submission, problem):
    if not judge_ready(submission):
        raise ValueError("Completed, persisted judge results are required")
    try:
        examples = json.loads(problem.test_cases or "[]")
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError("Public examples are invalid") from exc
    if not isinstance(examples, list) or not all(
        isinstance(example, dict) for example in examples
    ):
        raise ValueError("Public examples are invalid")

    result = public_result(submission.result, submission.status)
    return FeedbackContext(
        problem_title=problem.title,
        problem_description=problem.description,
        problem_categories=problem.categories or [],
        public_examples=examples,
        language=submission.language,
        submitted_code=submission.code,
        verdict=submission.status,
        tests_passed=result.tests_passed,
        tests_total=result.tests_total,
        runtime_ms=result.runtime_ms,
        memory_bytes=result.memory_bytes,
        error_message=(
            result.message if submission.status == "RUNTIME_ERROR" else None
        ),
    )


feedback_input = build_feedback_context
