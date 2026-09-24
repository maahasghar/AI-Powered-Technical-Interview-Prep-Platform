"""Supervise a local Ollama server and both queue workers in one container."""

import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener


class Supervisor:
    def __init__(self):
        self.stopping = threading.Event()
        self.children = []
        # Local service calls must not go through a deployment's HTTP proxy.
        self.http = build_opener(ProxyHandler({}))

    def start(self, name, command):
        print(f"Starting {name}.", flush=True)
        child = subprocess.Popen(command, start_new_session=True)
        self.children.append((name, child))
        return child

    def check_children(self):
        for name, child in self.children:
            code = child.poll()
            if code is not None:
                raise RuntimeError(f"{name} exited unexpectedly (status {code}).")

    def wait_for_ollama(self, timeout):
        deadline = time.monotonic() + timeout
        while not self.stopping.is_set():
            self.check_children()
            if time.monotonic() >= deadline:
                raise RuntimeError(
                    "Ollama did not become ready before startup timeout."
                )
            try:
                with self.http.open(
                    "http://127.0.0.1:11434/api/tags", timeout=2
                ) as response:
                    return json.load(response)["models"]
            except (URLError, OSError, ValueError, KeyError):
                self.stopping.wait(0.5)
        return []

    def ensure_model(self, model, available, timeout):
        # Ollama expands untagged model names to :latest.
        normalized = model if ":" in model.rsplit("/", 1)[-1] else f"{model}:latest"
        if any(item.get("name") in {model, normalized} for item in available):
            print("Configured Ollama model is already installed.", flush=True)
            return
        pull = self.start("Ollama model download", ["ollama", "pull", model])
        deadline = time.monotonic() + timeout
        while not self.stopping.is_set():
            code = pull.poll()
            if code is not None:
                if code != 0:
                    raise RuntimeError(f"Ollama model download failed (status {code}).")
                self.children.remove(("Ollama model download", pull))
                return
            # The download is allowed to finish; the server is not.
            for name, child in self.children:
                if child is not pull and child.poll() is not None:
                    raise RuntimeError(f"{name} exited during model download.")
            if time.monotonic() >= deadline:
                raise RuntimeError("Ollama model download timed out.")
            self.stopping.wait(0.5)

    def shutdown(self):
        print("Stopping Ollama and workers.", flush=True)
        # Signal process groups too: Ollama can have model runner children.
        for _, child in reversed(self.children):
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        deadline = time.monotonic() + 10
        for _, child in self.children:
            try:
                child.wait(timeout=max(0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                pass
        for _, child in self.children:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.wait()

    def run(self):
        try:
            model = os.environ.get("FEEDBACK_MODEL", "").strip()
            if not model or model.startswith("-"):
                raise ValueError("Set FEEDBACK_MODEL to the Ollama model to install.")
            if os.environ.get("FEEDBACK_PROVIDER", "ollama") != "ollama":
                raise ValueError(
                    "The combined service requires FEEDBACK_PROVIDER=ollama."
                )
            startup_timeout = positive_seconds("OLLAMA_STARTUP_TIMEOUT_SECONDS", 60)
            pull_timeout = positive_seconds("OLLAMA_PULL_TIMEOUT_SECONDS", 900)
            # Override stale Docker Compose hostnames inherited from Railway variables.
            os.environ["FEEDBACK_PROVIDER"] = "ollama"
            os.environ["OLLAMA_HOST"] = "127.0.0.1:11434"
            os.environ["OLLAMA_BASE_URL"] = "http://127.0.0.1:11434"
            models = os.environ.setdefault("OLLAMA_MODELS", "/data/ollama")
            Path(models).mkdir(parents=True, exist_ok=True)
            self.start("Ollama", ["ollama", "serve"])
            available = self.wait_for_ollama(startup_timeout)
            if self.stopping.is_set():
                return 0
            self.ensure_model(model, available, pull_timeout)
            if self.stopping.is_set():
                return 0
            self.check_children()
            self.start("judge worker", [sys.executable, "-m", "app.judge.worker"])
            self.start("feedback worker", [sys.executable, "-m", "app.feedback.worker"])
            print("Ollama and both workers are running.", flush=True)
            while not self.stopping.wait(0.5):
                self.check_children()
            return 0
        except (OSError, RuntimeError, ValueError) as exc:
            print(f"Combined worker startup/runtime failure: {exc}", file=sys.stderr)
            return 1
        finally:
            self.shutdown()


def positive_seconds(name, default):
    value = int(os.environ.get(name, default))
    if value <= 0:
        raise ValueError(f"{name} must be a positive number of seconds.")
    return value


def main():
    supervisor = Supervisor()
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_: supervisor.stopping.set())
    return supervisor.run()


if __name__ == "__main__":
    sys.exit(main())
