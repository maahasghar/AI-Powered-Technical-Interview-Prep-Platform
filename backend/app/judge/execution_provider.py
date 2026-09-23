from __future__ import annotations

import json
import logging
import random
import time
from dataclasses import dataclass, field
from math import ceil
from typing import Any, Protocol

from e2b import CommandExitException, Sandbox, SandboxException, TimeoutException
from e2b.exceptions import AuthenticationException, RateLimitException

from app.core.config import settings
from app.domain.submissions.results import CaseResult

logger = logging.getLogger(__name__)
OUTPUT_LIMIT = 64 * 1024


class ExecutionProvider(Protocol):
    def execute(self, code: str, arguments: dict[str, Any], seconds: float = 6.0):
        ...

    def run_case(self, code: str, arguments: dict[str, Any], seconds: float = 6.0):
        ...


@dataclass
class ExecutionResult:
    stdout: str | None = None
    stderr: str | None = None
    exit_code: int | None = None
    execution_time: float | None = None
    timed_out: bool = False
    diagnostics: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class E2BProviderError(RuntimeError):
    pass


class E2BTransientError(E2BProviderError):
    pass


class E2BExecutionProvider:
    """Execute one isolated Python test case per E2B sandbox."""

    def __init__(
        self,
        api_key: str | None = None,
        request_timeout: float | None = None,
        max_attempts: int = 3,
        initial_backoff: float = 0.25,
        max_backoff: float = 2.0,
        sandbox_factory=Sandbox,
    ):
        self.api_key = (
            api_key if api_key is not None else settings.E2B_API_KEY.get_secret_value()
        )
        self.request_timeout = float(
            request_timeout
            if request_timeout is not None
            else settings.E2B_REQUEST_TIMEOUT_SECONDS
        )
        self.max_attempts = max(1, int(max_attempts))
        self.initial_backoff = float(initial_backoff)
        self.max_backoff = float(max_backoff)
        self.sandbox_factory = sandbox_factory

    @staticmethod
    def _runner_source():
        return """import importlib.util
import json

spec = importlib.util.spec_from_file_location('submission', '/tmp/submission.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with open('/tmp/input.json', encoding='utf-8') as input_file:
    arguments = json.load(input_file)
result = module.solve(**arguments)
print(json.dumps(result, allow_nan=False, separators=(',', ':')))
"""

    @staticmethod
    def _parse_json_value(stdout: str | None):
        if stdout is None:
            return None
        try:
            return json.loads(stdout.strip())
        except (TypeError, ValueError, RecursionError) as exc:
            raise ValueError("Sandbox stdout was not valid JSON") from exc

    def _sleep_with_backoff(self, delay: float):
        time.sleep(delay + random.uniform(0, min(delay, 0.25)))

    def _create_sandbox(self, seconds: float):
        if not self.api_key:
            raise E2BProviderError("E2B_API_KEY is not configured")
        try:
            return self.sandbox_factory.create(
                api_key=self.api_key,
                timeout=max(10, ceil(seconds) + 4),
                request_timeout=self.request_timeout,
                secure=True,
                allow_internet_access=False,
            )
        except RateLimitException as exc:
            raise E2BTransientError("E2B rate limit reached") from exc
        except AuthenticationException as exc:
            raise E2BProviderError("E2B authentication failed") from exc
        except SandboxException as exc:
            raise E2BTransientError("E2B sandbox creation failed") from exc

    def _execute_once(self, code: str, arguments: dict[str, Any], seconds: float):
        sandbox = self._create_sandbox(seconds)
        started = time.monotonic()
        try:
            sandbox.files.write(
                "/tmp/submission.py", code, request_timeout=self.request_timeout
            )
            sandbox.files.write(
                "/tmp/input.json",
                json.dumps(arguments, allow_nan=False, separators=(",", ":")),
                request_timeout=self.request_timeout,
            )
            sandbox.files.write(
                "/tmp/runner.py",
                self._runner_source(),
                request_timeout=self.request_timeout,
            )
            try:
                result = sandbox.commands.run(
                    "python /tmp/runner.py",
                    timeout=seconds,
                    request_timeout=self.request_timeout,
                )
            except CommandExitException as exc:
                return ExecutionResult(
                    stdout=exc.stdout,
                    stderr=exc.stderr,
                    exit_code=exc.exit_code,
                    execution_time=time.monotonic() - started,
                    diagnostics=exc.error or "Sandboxed code exited with an error",
                )
            except TimeoutException:
                return ExecutionResult(
                    timed_out=True,
                    execution_time=time.monotonic() - started,
                    diagnostics="Sandboxed code exceeded the execution timeout",
                )
            except SandboxException as exc:
                raise E2BTransientError("E2B command execution failed") from exc
            return ExecutionResult(
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.exit_code,
                execution_time=time.monotonic() - started,
                diagnostics=result.error,
            )
        except TimeoutException as exc:
            raise E2BTransientError("E2B sandbox request timed out") from exc
        except SandboxException as exc:
            raise E2BTransientError("E2B sandbox operation failed") from exc
        finally:
            try:
                sandbox.kill(request_timeout=self.request_timeout)
            except Exception:
                logger.warning("Unable to terminate E2B sandbox", exc_info=True)

    def execute(self, code: str, arguments: dict[str, Any], seconds: float = 6.0):
        delay = self.initial_backoff
        for attempt in range(self.max_attempts):
            try:
                return self._execute_once(code, arguments, seconds)
            except E2BTransientError:
                if attempt + 1 >= self.max_attempts:
                    raise
                self._sleep_with_backoff(delay)
                delay = min(self.max_backoff, delay * 2)
        raise E2BProviderError("E2B execution retries exhausted")

    def run_case(self, code: str, arguments: dict[str, Any], seconds: float = 6.0):
        try:
            result = self.execute(code, arguments, seconds)
        except E2BProviderError as exc:
            return CaseResult(
                status="RUNTIME_ERROR",
                verdict_code="UNAVAILABLE",
                diagnostics=str(exc),
            )

        runtime_ms = (
            round(result.execution_time * 1000, 3)
            if result.execution_time is not None
            else None
        )
        if result.timed_out:
            return CaseResult(
                status="TIME_LIMIT_EXCEEDED",
                verdict_code="TIME_LIMIT_EXCEEDED",
                runtime_ms=runtime_ms,
                diagnostics=result.diagnostics,
            )
        if result.exit_code != 0:
            return CaseResult(
                status="RUNTIME_ERROR",
                verdict_code="RUNTIME_ERROR",
                runtime_ms=runtime_ms,
                diagnostics=result.diagnostics or result.stderr or "Sandboxed code failed",
            )
        if result.stdout is None or len(result.stdout.encode()) > OUTPUT_LIMIT:
            return CaseResult(
                status="RUNTIME_ERROR",
                verdict_code="OUTPUT_LIMIT" if result.stdout is not None else "RUNTIME_ERROR",
                runtime_ms=runtime_ms,
                diagnostics=result.diagnostics or "Sandbox output was invalid",
            )
        try:
            actual = self._parse_json_value(result.stdout)
        except ValueError:
            return CaseResult(
                status="RUNTIME_ERROR",
                verdict_code="RUNTIME_ERROR",
                runtime_ms=runtime_ms,
                diagnostics=result.diagnostics or "Sandbox stdout was not valid JSON",
            )
        return CaseResult(
            status="PASSED",
            actual=actual,
            runtime_ms=runtime_ms,
            diagnostics=result.diagnostics,
        )
