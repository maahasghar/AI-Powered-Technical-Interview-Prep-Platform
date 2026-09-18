"""Run the fixed feedback regression suite before enabling AI broadly."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.core.config import settings
from app.feedback.evaluation import evaluate_fixture
from app.feedback.provider import OllamaFeedbackProvider, OpenAIFeedbackProvider


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, help="Write results to a JSON report")
    args = parser.parse_args()
    provider = (
        OllamaFeedbackProvider()
        if settings.FEEDBACK_PROVIDER == "ollama"
        else OpenAIFeedbackProvider()
    )
    report = {
        "provider": settings.FEEDBACK_PROVIDER,
        "model": settings.FEEDBACK_MODEL,
        "prompt_version": settings.FEEDBACK_PROMPT_VERSION,
        "schema_version": settings.FEEDBACK_SCHEMA_VERSION,
        **evaluate_fixture(provider),
    }
    rendered = json.dumps(report, indent=2) + "\n"
    print(rendered, end="")
    if args.report:
        args.report.write_text(rendered)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
