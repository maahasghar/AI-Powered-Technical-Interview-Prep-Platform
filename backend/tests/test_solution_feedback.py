import json
import unittest
from unittest.mock import Mock, patch

from app.domain.submissions.models import Submission
from app.domain.submissions.results import InternalJudgeResult
from app.feedback.evaluation import EVALUATION_CASES, evaluate_output
from app.feedback.models import Feedback
from app.feedback.policy import FeedbackContext, validate_feedback
from app.feedback.service import public_feedback, request_feedback
from app.feedback.worker import process_feedback
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def payload(**extra):
    return json.dumps(
        dict(
            strengths=["Passed tests"],
            likely_issue=None,
            hint=None,
            complexity={"time": "O(1)", "space": "O(1)"},
            next_step="Return the constant.",
            **extra,
        )
    )


class SolutionFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        self.addCleanup(self.engine.dispose)
        Submission.__table__.create(self.engine)
        Feedback.__table__.create(self.engine)
        self.sessions = sessionmaker(self.engine)
        with self.sessions.begin() as session:
            session.add(
                Submission(
                    id=1,
                    user_id=1,
                    problem_id=1,
                    code="def solve(): return 1",
                    language="python",
                    status="PASSED",
                    result=InternalJudgeResult(
                        status="PASSED",
                        verdict_code="PASSED",
                        tests_passed=1,
                        tests_total=1,
                    ).model_dump_json(),
                )
            )
            session.add(
                Feedback(
                    id=1,
                    submission_id=1,
                    stage="SOLUTION",
                    status="READY",
                    payload=payload(),
                )
            )

    def test_text_only_solution_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_feedback("SOLUTION", payload())
        for code in ("", "Please review the solution.", "def solve(:", "x = 1"):
            with self.assertRaises(ValueError):
                validate_feedback("SOLUTION", payload(solution_code=code))

    def test_code_survives_api_serialization_and_evaluation(self):
        with self.sessions() as session:
            row = session.get(Feedback, 1)
            row.payload = payload(solution_code="def solve(): return 1")
            result = public_feedback(row).model_dump()
            self.assertEqual(
                result["feedback"]["solution_code"], "def solve(): return 1"
            )
            case = next(case for case in EVALUATION_CASES if case.stage == "SOLUTION")
            self.assertEqual(evaluate_output(case, row.payload), [])

    def test_legacy_fenced_code_is_preserved(self):
        data = json.loads(payload())
        data["next_step"] = (
            "```python\ndef solve(): return 1\n```\nReturn the constant."
        )
        feedback = validate_feedback("SOLUTION", json.dumps(data))
        self.assertEqual(feedback.solution_code, "def solve(): return 1")
        self.assertEqual(feedback.next_step, "Return the constant.")

    def test_old_text_only_solution_can_be_retried(self):
        with self.sessions() as session:
            self.assertEqual(public_feedback(session.get(Feedback, 1)).status, "FAILED")
            row, enqueue = request_feedback(session, 1, 1, "show_solution")
            self.assertTrue(enqueue)
            self.assertEqual(row.status, "QUEUED")
            self.assertIsNone(row.payload)

    def test_valid_solution_is_not_regenerated_on_duplicate_request(self):
        with self.sessions.begin() as session:
            session.get(Feedback, 1).payload = payload(
                solution_code="def solve(): return 1"
            )
        with self.sessions() as session:
            row, enqueue = request_feedback(session, 1, 1, "show_solution")
            self.assertFalse(enqueue)
            self.assertEqual(row.status, "READY")

    def test_generation_failure_does_not_save_review_text_as_solution(self):
        with self.sessions.begin() as session:
            session.get(Feedback, 1).status = "QUEUED"
        context = FeedbackContext(
            problem_title="Return one",
            problem_description="Return one",
            problem_categories=[],
            public_examples=[],
            language="python",
            submitted_code="def solve(): return 1",
            verdict="PASSED",
        )
        provider = Mock()
        provider.generate.side_effect = RuntimeError("unavailable")
        # This test needs only the feedback/submission tables, not the problem bank.
        with (
            patch("app.feedback.worker.Problem", Submission),
            patch("app.feedback.worker.build_feedback_context", return_value=context),
        ):
            process_feedback(1, provider, self.sessions)
        with self.sessions() as session:
            row = session.get(Feedback, 1)
            self.assertEqual(row.status, "FAILED")
            self.assertIsNone(row.payload)
            self.assertEqual(session.get(Submission, 1).status, "PASSED")
