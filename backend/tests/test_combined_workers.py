"""Process lifecycle checks without Redis, PostgreSQL, or a downloaded model."""

import io
import os
import signal
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import URLError

from app.scripts.run_workers import Supervisor


class CombinedWorkersTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.environment = patch.dict(
            os.environ,
            {
                "FEEDBACK_MODEL": "test-model",
                "FEEDBACK_PROVIDER": "ollama",
                "OLLAMA_MODELS": self.directory.name,
                "OLLAMA_BASE_URL": "http://ollama:11434",
            },
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.supervisor = Supervisor()

    def test_workers_start_only_after_server_and_model_are_ready(self):
        events = []

        def start(name, command):
            events.append(name)
            if name == "feedback worker":
                self.supervisor.stopping.set()

        with (
            patch.object(self.supervisor, "start", side_effect=start),
            patch.object(
                self.supervisor,
                "wait_for_ollama",
                side_effect=lambda _: events.append("ready") or [],
            ),
            patch.object(
                self.supervisor,
                "ensure_model",
                side_effect=lambda *_: events.append("model ready"),
            ),
            patch.object(self.supervisor, "shutdown") as shutdown,
        ):
            self.assertEqual(self.supervisor.run(), 0)
        self.assertEqual(
            events,
            ["Ollama", "ready", "model ready", "judge worker", "feedback worker"],
        )
        self.assertEqual(os.environ["OLLAMA_BASE_URL"], "http://127.0.0.1:11434")
        shutdown.assert_called_once()

    def test_existing_model_skips_download(self):
        with patch.object(self.supervisor, "start") as start:
            self.supervisor.ensure_model(
                "test-model", [{"name": "test-model:latest"}], 1
            )
        start.assert_not_called()

    def test_failed_model_download_prevents_workers_starting(self):
        server = Mock()
        server.poll.return_value = None
        download = Mock()
        download.poll.return_value = 1
        with (
            patch(
                "app.scripts.run_workers.subprocess.Popen",
                side_effect=[server, download],
            ) as spawn,
            patch.object(self.supervisor, "wait_for_ollama", return_value=[]),
            patch.object(self.supervisor, "shutdown") as shutdown,
        ):
            self.assertEqual(self.supervisor.run(), 1)
        self.assertEqual(spawn.call_count, 2)
        shutdown.assert_called_once()

    def test_successful_download_is_removed_from_supervised_processes(self):
        download = Mock()
        download.poll.return_value = 0
        with patch("app.scripts.run_workers.subprocess.Popen", return_value=download):
            self.supervisor.ensure_model("test-model", [], 1)
        self.assertEqual(self.supervisor.children, [])

    def test_readiness_retries_connection_failure(self):
        self.supervisor.http = Mock()
        self.supervisor.http.open.side_effect = [
            URLError("not ready"),
            io.BytesIO(b'{"models": []}'),
        ]
        with patch.object(self.supervisor.stopping, "wait"):
            self.assertEqual(self.supervisor.wait_for_ollama(5), [])
        self.assertEqual(self.supervisor.http.open.call_count, 2)

    def test_readiness_timeout(self):
        with self.assertRaisesRegex(RuntimeError, "startup timeout"):
            self.supervisor.wait_for_ollama(0)

    def test_download_timeout(self):
        download = Mock()
        download.poll.return_value = None
        with (
            patch("app.scripts.run_workers.subprocess.Popen", return_value=download),
            self.assertRaisesRegex(RuntimeError, "download timed out"),
        ):
            self.supervisor.ensure_model("test-model", [], 0)

    def test_missing_model_fails_before_starting_any_process(self):
        os.environ["FEEDBACK_MODEL"] = ""
        with patch.object(self.supervisor, "start") as start:
            self.assertEqual(self.supervisor.run(), 1)
        start.assert_not_called()

    def test_any_process_exit_stops_service_even_with_zero_exit_code(self):
        child = Mock()
        child.poll.return_value = 0
        for name in ("Ollama", "judge worker", "feedback worker"):
            self.supervisor.children = [(name, child)]
            with self.assertRaisesRegex(RuntimeError, "exited unexpectedly"):
                self.supervisor.check_children()

    def test_shutdown_terminates_and_reaps_real_processes(self):
        children = [
            self.supervisor.start(
                name, [sys.executable, "-c", "import time; time.sleep(60)"]
            )
            for name in ("Ollama", "judge worker", "feedback worker")
        ]
        try:
            self.supervisor.shutdown()
            for child in children:
                self.assertEqual(child.poll(), -signal.SIGTERM)
        finally:
            for child in children:
                if child.poll() is None:
                    child.kill()
                    child.wait()


if __name__ == "__main__":
    unittest.main()
