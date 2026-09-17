"""Shared validation for JSON sample and hidden tests."""

import json

MAX_CASES = 20
MAX_TEST_BYTES = 128_000


def parse_cases(value: str) -> list[dict]:
    if len(value.encode()) > MAX_TEST_BYTES:
        raise ValueError("Test cases exceed 128 KB")
    try:
        cases = json.loads(value, parse_constant=reject_constant)
    except (ValueError, TypeError) as exc:
        raise ValueError("Test cases must be JSON") from exc
    if not isinstance(cases, list) or len(cases) > MAX_CASES:
        raise ValueError("Test cases must be a list with at most 20 entries")
    for case in cases:
        if len(json.dumps(case).encode()) > 60_000:
            raise ValueError("Each test must be at most 60 KB")
        if not isinstance(case, dict) or set(case) != {"input", "expected"}:
            raise ValueError("Each test needs input and expected fields")
        if not isinstance(case["input"], dict) or any(
            not key.isidentifier() for key in case["input"]
        ):
            raise ValueError("Test input must map Python argument names to JSON values")
    return cases


def reject_constant(value):
    raise ValueError("Non-finite JSON values are not supported")
