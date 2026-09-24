"""Inference configuration and lease checks without external services."""

import json
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import httpx
from app.core.config import settings
from app.feedback.models import Feedback
from app.feedback.policy import FeedbackContext
from app.feedback.provider import OllamaFeedbackProvider
from app.feedback.worker import _keep_feedback_alive, _renew_feedback_claim
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class FeedbackRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.engine = create_engine(f"sqlite:///{self.directory.name}/feedback.db")
        self.addCleanup(self.engine.dispose)
        Feedback.__table__.create(self.engine)
        self.sessions = sessionmaker(self.engine)
        with self.sessions.begin() as session:
            session.add(
                Feedback(
                    id=1,
                    submission_id=1,
                    stage="DIAGNOSIS",
                    status="RUNNING",
                    execution_id="owner",
                    updated_at=datetime.now(timezone.utc) - timedelta(minutes=10),
                )
            )

    def test_renewal_preserves_ownership_and_refreshes_stale_timestamp(self):
        self.assertTrue(_renew_feedback_claim(1, "owner", self.sessions))
        with self.sessions() as session:
            row = session.get(Feedback, 1)
            self.assertEqual(row.status, "RUNNING")
            self.assertGreater(
                row.updated_at,
                datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=5),
            )

    def test_old_worker_cannot_renew_reassigned_or_finished_job(self):
        self.assertFalse(_renew_feedback_claim(1, "old-owner", self.sessions))
        with self.sessions.begin() as session:
            session.get(Feedback, 1).status = "READY"
        self.assertFalse(_renew_feedback_claim(1, "owner", self.sessions))

    def test_lease_keeps_renewing_while_caller_blocks_and_stops_on_exit(self):
        renewed_twice = threading.Event()
        count = []

        def renew(*args):
            result = _renew_feedback_claim(*args)
            count.append(result)
            if len(count) >= 2:
                renewed_twice.set()
            return result

        with (
            patch("app.feedback.worker._renew_feedback_claim", side_effect=renew),
            _keep_feedback_alive(1, "owner", self.sessions, interval=0.01),
        ):
            self.assertTrue(renewed_twice.wait(2))
        self.assertGreaterEqual(len(count), 2)
        self.assertTrue(all(count))
        self.assertFalse(any(t.name == "feedback-lease" for t in threading.enumerate()))

    def test_lease_stops_when_generation_raises(self):
        with (
            self.assertRaises(httpx.ReadTimeout),
            _keep_feedback_alive(1, "owner", self.sessions),
        ):
            raise httpx.ReadTimeout("slow generation")
        self.assertFalse(any(t.name == "feedback-lease" for t in threading.enumerate()))

    def test_ollama_receives_limits_and_longer_timeout(self):
        payload = {
            "strengths": ["Readable code"],
            "likely_issue": None,
            "hint": None,
            "complexity": {"time": "O(1)", "space": "O(1)"},
            "next_step": "Review edge cases.",
        }
        response = httpx.Response(
            200,
            json={"message": {"content": json.dumps(payload)}},
            request=httpx.Request("POST", "http://ollama/api/chat"),
        )
        client = Mock()
        client.post.return_value = response
        context = FeedbackContext(
            problem_title="Example",
            problem_description="Return one",
            problem_categories=[],
            public_examples=[],
            language="python",
            submitted_code="def solve(): return 1",
            verdict="PASSED",
        )
        with (
            patch.object(settings, "FEEDBACK_MODEL", "test-model"),
            patch.object(settings, "FEEDBACK_TIMEOUT_SECONDS", 600),
            patch.object(settings, "OLLAMA_NUM_THREAD", 1),
            patch.object(settings, "OLLAMA_NUM_PREDICT", 1024),
            patch("app.feedback.provider.httpx.Client") as factory,
        ):
            factory.return_value.__enter__.return_value = client
            self.assertEqual(
                json.loads(OllamaFeedbackProvider().generate("DIAGNOSIS", context)),
                payload,
            )
        self.assertEqual(factory.call_args.kwargs["timeout"].read, 600)
        self.assertEqual(
            client.post.call_args.kwargs["json"]["options"],
            {
                "temperature": 0.2,
                "num_thread": 1,
                "num_predict": 1024,
            },
        )
