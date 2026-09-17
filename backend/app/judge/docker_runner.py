"""Docker is the execution boundary. Never execute submitted Python in this process."""

import json
import re
import selectors
import subprocess
import time
from uuid import uuid4

from app.domain.submissions.results import CaseResult, InternalJudgeResult

OUTPUT_LIMIT = 64 * 1024
CASE_SECONDS = 6
JOB_SECONDS = 90
CONTAINER_LABEL = "interview-judge"


class JudgeUnavailable(Exception):
    pass


class DockerRunner:
    def __init__(self, image="interview-judge-python:local"):
        self.image = image

    def command(self, name, code, arguments):
        return [
            "docker",
            "create",
            "--name",
            name,
            "--label",
            f"{CONTAINER_LABEL}=true",
            "--label",
            f"judge.expires={int(time.time()) + JOB_SECONDS}",
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges=true",
            "--user",
            "65534:65534",
            "--cpus",
            "1",
            "--memory",
            "128m",
            "--memory-swap",
            "128m",
            "--pids-limit",
            "32",
            "--ulimit",
            "cpu=3:3",
            "--ulimit",
            "fsize=65536:65536",
            "--ulimit",
            "nofile=64:64",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,nodev,size=16m,mode=1777",
            "--shm-size",
            "8m",
            "--log-driver",
            "none",
            self.image,
            code,
            json.dumps(arguments, allow_nan=False),
        ]

    @staticmethod
    def control(args):
        try:
            return subprocess.run(
                ["docker", *args], capture_output=True, check=True, timeout=10
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise JudgeUnavailable("Docker control operation failed") from exc

    def run_case(self, code, arguments, seconds=CASE_SECONDS):
        name = f"interview-judge-{uuid4().hex}"
        process = None
        stats = None
        started = None
        peak_memory = None
        output = bytearray()

        def finish(status, actual=None, verdict_code=None):
            return CaseResult(
                status=status,
                actual=actual,
                verdict_code=verdict_code or status,
                runtime_ms=(
                    round((time.monotonic() - started) * 1000, 3) if started else None
                ),
                memory_bytes=peak_memory,
                diagnostics=(
                    f"container={name}; output={bytes(output)!r}"
                    if status != "PASSED"
                    else None
                ),
            )

        try:
            try:
                subprocess.run(
                    self.command(name, code, arguments),
                    capture_output=True,
                    check=True,
                    timeout=10,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                raise JudgeUnavailable(
                    "Could not create judge container; build the judge image first"
                ) from exc
            started = time.monotonic()
            process = subprocess.Popen(
                ["docker", "start", "--attach", name],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            # Best-effort host-side sampling. Short runs may finish before the
            # first sample; report unknown rather than inventing zero usage.
            try:
                stats = subprocess.Popen(
                    ["docker", "stats", "--format", "{{.MemUsage}}", name],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                )
            except OSError:
                stats = None
            deadline = time.monotonic() + seconds
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ, "output")
                if stats:
                    selector.register(stats.stdout, selectors.EVENT_READ, "stats")
                reading_output = True
                stats_buffer = b""
                while reading_output:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        return finish("TIME_LIMIT_EXCEEDED")
                    for key, _ in selector.select(min(remaining, 0.1)):
                        chunk = key.fileobj.read1(8192)
                        if not chunk:
                            selector.unregister(key.fileobj)
                            if key.data == "output":
                                reading_output = False
                            continue
                        if key.data == "stats":
                            stats_buffer += chunk
                            while b"\n" in stats_buffer:
                                line, stats_buffer = stats_buffer.split(b"\n", 1)
                                sample = memory_sample(line.decode(errors="replace"))
                                if sample is not None:
                                    peak_memory = max(peak_memory or 0, sample)
                            stats_buffer = stats_buffer[-4096:]
                        else:
                            output.extend(chunk)
                            if len(output) > OUTPUT_LIMIT:
                                return finish(
                                    "RUNTIME_ERROR", verdict_code="OUTPUT_LIMIT"
                                )
                process.wait(timeout=max(0.1, deadline - time.monotonic()))
            state = json.loads(
                self.control(["inspect", "--format", "{{json .State}}", name]).stdout
            )
            if state["OOMKilled"]:
                return finish("RUNTIME_ERROR")
            if state["ExitCode"] in (124, 137, 152):
                return finish("TIME_LIMIT_EXCEEDED")
            if state["ExitCode"] != 0:
                return finish("RUNTIME_ERROR")
            try:
                value = json.loads(output, parse_constant=self.invalid_constant)
            except (ValueError, UnicodeError, RecursionError):
                return finish("RUNTIME_ERROR")
            return finish("PASSED", value)
        except subprocess.TimeoutExpired:
            return finish("TIME_LIMIT_EXCEEDED")
        except OSError as exc:
            raise JudgeUnavailable("Docker CLI unavailable") from exc
        finally:
            # Close attached streams before removal so output flooding cannot
            # block the daemon while it shuts down the container.
            for client in (stats, process):
                if client:
                    if client.poll() is None:
                        client.kill()
                    client.wait(timeout=5)
                    client.stdout.close()
            # Killing the CLI alone does not kill the container.
            self.control(["rm", "--force", name])

    @staticmethod
    def invalid_constant(value):
        raise ValueError("Non-finite JSON value")

    def reap_expired(self):
        names = (
            self.control(["ps", "-aq", "--filter", f"label={CONTAINER_LABEL}=true"])
            .stdout.decode()
            .split()
        )
        for name in names:
            try:
                expires = self.control(
                    [
                        "inspect",
                        "--format",
                        '{{index .Config.Labels "judge.expires"}}',
                        name,
                    ]
                ).stdout
                if int(expires) < time.time():
                    self.control(["rm", "--force", name])
            except (JudgeUnavailable, ValueError):
                # Another worker may have removed it already.
                continue


def memory_sample(line):
    line = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", line)
    match = re.match(r"^([0-9.]+)(B|KiB|MiB|GiB|kB|MB|GB) /", line.strip())
    if not match:
        return None
    scales = {
        "B": 1,
        "KiB": 1024,
        "MiB": 1024**2,
        "GiB": 1024**3,
        "kB": 1000,
        "MB": 1000**2,
        "GB": 1000**3,
    }
    try:
        value = int(float(match[1]) * scales[match[2]])
    except (ValueError, OverflowError):
        return None
    return value if 0 < value <= 128 * 1024 * 1024 else None


def evaluate(code, cases, runner):
    if not cases:
        return InternalJudgeResult(status="RUNTIME_ERROR", verdict_code="INVALID_TESTS")
    started = time.monotonic()
    passed = 0
    runtime_ms = None
    memory_bytes = None
    for case in cases:
        remaining = JOB_SECONDS - 20 - (time.monotonic() - started)
        if remaining <= 0:
            outcome = CaseResult(status="TIME_LIMIT_EXCEEDED")
        else:
            outcome = runner.run_case(code, case["input"], min(CASE_SECONDS, remaining))
            if outcome.runtime_ms is not None:
                runtime_ms = (runtime_ms or 0) + outcome.runtime_ms
            if outcome.memory_bytes is not None:
                memory_bytes = max(memory_bytes or 0, outcome.memory_bytes)
            if outcome.status == "PASSED":
                if json.dumps(outcome.actual, sort_keys=True) != json.dumps(
                    case["expected"], sort_keys=True
                ):
                    outcome.status = "FAILED"
                    outcome.verdict_code = "FAILED"
                else:
                    passed += 1
        if outcome.status != "PASSED":
            return InternalJudgeResult(
                status=outcome.status,
                verdict_code=outcome.verdict_code or outcome.status,
                tests_passed=passed,
                tests_total=len(cases),
                runtime_ms=runtime_ms,
                memory_bytes=memory_bytes,
                diagnostics=outcome.diagnostics,
            )
    return InternalJudgeResult(
        status="PASSED",
        verdict_code="PASSED",
        tests_passed=passed,
        tests_total=len(cases),
        runtime_ms=runtime_ms,
        memory_bytes=memory_bytes,
    )
