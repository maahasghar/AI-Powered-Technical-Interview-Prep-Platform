"""Small fixed regression suite for AI feedback behavior."""

from __future__ import annotations

from dataclasses import dataclass

from app.feedback.policy import FeedbackContext, validate_feedback


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    stage: str
    context: FeedbackContext
    forbidden: tuple[str, ...] = ()


EVALUATION_CASES = (
    EvaluationCase(
        case_id="passed-diagnosis",
        stage="DIAGNOSIS",
        context=FeedbackContext(
            problem_title="Two Sum",
            problem_description="Return indices of two values that add to target.",
            problem_categories=["arrays"],
            public_examples=[
                {"input": {"nums": [2, 7], "target": 9}, "expected": [0, 1]}
            ],
            language="python",
            submitted_code="def two_sum(nums, target): return [0, 1]",
            verdict="PASSED",
            tests_passed=3,
            tests_total=3,
            runtime_ms=1,
            memory_bytes=1024,
        ),
        forbidden=("hidden test", "judge internals"),
    ),
    EvaluationCase(
        case_id="failed-hint",
        stage="HINT",
        context=FeedbackContext(
            problem_title="First Missing Positive",
            problem_description="Return the smallest positive integer missing from a list.",
            problem_categories=["arrays", "optimization"],
            public_examples=[{"input": {"nums": [3, 4, -1, 1]}, "expected": 2}],
            language="python",
            submitted_code="def first_missing_positive(nums): return nums[0]",
            verdict="FAILED",
            tests_passed=1,
            tests_total=3,
            runtime_ms=1,
            memory_bytes=1024,
        ),
        forbidden=("```", "hidden test", "complete solution"),
    ),
    EvaluationCase(
        case_id="runtime-diagnosis",
        stage="DIAGNOSIS",
        context=FeedbackContext(
            problem_title="Valid Parentheses",
            problem_description="Determine whether brackets are balanced.",
            problem_categories=["strings"],
            public_examples=[{"input": {"s": "()"}, "expected": True}],
            language="python",
            submitted_code="def is_valid(s): return stack[-1]",
            verdict="RUNTIME_ERROR",
            tests_passed=0,
            tests_total=2,
            runtime_ms=1,
            memory_bytes=1024,
            error_message="Index access failed for an empty stack.",
        ),
        forbidden=("hidden test", "judge internals"),
    ),
    EvaluationCase(
        case_id="failed-solution",
        stage="SOLUTION",
        context=FeedbackContext(
            problem_title="Longest Substring Without Repeating Characters",
            problem_description="Return the longest substring length without repeated characters.",
            problem_categories=["strings", "optimization"],
            public_examples=[{"input": {"s": "abcabcbb"}, "expected": 3}],
            language="python",
            submitted_code="def longest(s): return len(set(s))",
            verdict="FAILED",
            tests_passed=1,
            tests_total=4,
            runtime_ms=1,
            memory_bytes=1024,
        ),
        forbidden=("hidden test", "judge internals"),
    ),
)


def evaluate_output(case: EvaluationCase, payload: str) -> list[str]:
    errors: list[str] = []
    try:
        feedback = validate_feedback(case.stage, payload)
    except ValueError as exc:
        return [f"schema validation failed: {exc}"]

    serialized = feedback.model_dump_json().lower()
    for forbidden in case.forbidden:
        if forbidden.lower() in serialized:
            errors.append(f"forbidden content: {forbidden}")
    if case.stage == "DIAGNOSIS" and feedback.hint is not None:
        errors.append("diagnosis must have a null hint")
    if case.stage == "HINT" and "```" in serialized:
        errors.append("hint must not contain a code block")
    if case.stage == "SOLUTION":
        solution = feedback.next_step.lower()
        if "```python" not in solution:
            errors.append("solution must contain a fenced Python code block")
        if feedback.next_step.rstrip().endswith("```"):
            errors.append("solution must include explanation after the code block")
    return errors


def evaluate_fixture(provider) -> dict:
    results = []
    for case in EVALUATION_CASES:
        try:
            payload = provider.generate(case.stage, case.context)
            errors = evaluate_output(case, payload)
        except Exception as exc:  # noqa: BLE001 - isolate each fixture result
            errors = [type(exc).__name__]
        results.append(
            {
                "id": case.case_id,
                "stage": case.stage,
                "passed": not errors,
                "errors": errors,
            }
        )
    return {
        "cases": len(results),
        "passed": all(result["passed"] for result in results),
        "results": results,
    }


__all__ = ["EVALUATION_CASES", "EvaluationCase", "evaluate_fixture", "evaluate_output"]
