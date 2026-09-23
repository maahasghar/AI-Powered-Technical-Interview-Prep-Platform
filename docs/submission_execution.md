# Python submission execution

`POST /api/v1/submissions` accepts Python source, commits a `QUEUED` submission,
and enqueues its ID in Redis. A separate worker claims the row as `RUNNING`, loads
its problem and tests from PostgreSQL, and runs each test in a fresh Docker
container. The API and worker never execute submitted Python themselves.

Terminal states are `PASSED`, `FAILED`, `RUNTIME_ERROR`, and
`TIME_LIMIT_EXCEEDED`. The frontend polls every two seconds while queued/running,
stops on completion or a request error, and offers a manual retry after errors.
Navigation cancels the timer and outstanding fetch.

## Public results and private diagnostics

Every submission endpoint uses `SubmissionResponse` and a separate
`PublicSubmissionResult` schema. The API projects stored data onto an explicit
allowlist; it never returns the database result string directly. This also applies
to admin requests through these endpoints. No admin diagnostics endpoint exists.

Completed submissions return an object such as:

```json
{
  "message": "Your solution did not pass all tests.",
  "tests_passed": 2,
  "tests_total": 4,
  "runtime_ms": 123.5,
  "memory_bytes": 10485760
}
```

`result` is null for QUEUED/RUNNING submissions. Messages come from a fixed public
verdict catalog, never from exception text or a stored message. Counts are
aggregate only. Runtime is cumulative wall time measured by the worker around
container startup/attached execution, excluding container creation and cleanup;
it is not CPU time. Memory is the highest observed Docker CLI memory sample
across executed cases, not an exact peak. Docker's Linux CLI subtracts cache usage;
see [Docker stats semantics](https://docs.docker.com/reference/cli/docker/container/stats/).
Short runs can finish before a sample arrives. Unavailable or invalid metrics and
legacy records without measurements return null, and the UI displays Unavailable.

`CaseResult` and `InternalJudgeResult` are internal models and never response
schemas. Bounded runtime diagnostics and infrastructure exceptions stay in server
logs. Diagnostic fields are excluded from persisted model serialization. Hidden
test inputs, expected answers, per-test results, raw stdout, stack traces,
container identifiers, commands, and internal paths are excluded from public
results. User runtime exceptions currently receive a generic safe message; their
raw text is not forwarded or sanitized using fragile text replacement.

Legacy result strings are parsed defensively. Only valid numeric aggregates and
measurements survive projection; malformed data, arbitrary fields/messages, and
unknown statuses fail closed. Existing `passed`/`total` keys are recognized.
No database migration is needed for this result-schema change, but deploy the
frontend, API, and worker together: `result` changed from a JSON string to a typed
object. Existing source code and submission metadata remain available to their
authorized readers.

## Solution and test contract

Implement `solve(...)`, with arguments matching the input object's keys. Return a
JSON-compatible value. For example:

```python
def solve(nums, target):
    seen = {}
    for index, value in enumerate(nums):
        if target - value in seen:
            return [seen[target - value], index]
        seen[value] = index
```

Both `test_cases` (visible samples) and `hidden_test_cases` (judge-only) are JSON
strings containing entries such as `{"input":{"nums":[2,7],"target":9},"expected":[0,1]}`.
Admin create/patch endpoints accept both fields; problem responses expose only
`test_cases`, including for admins. Each field permits at most 20 tests, 128 KB
in total and 60 KB per test. Source is limited to 64 KB. Expected values are
compared in the worker using canonical JSON with sorted object keys; list order
and JSON number representations matter. Floating-point tolerance is not provided.
Ordinary print output is discarded inside the harness. No third-party packages
are installed in the judge image. Empty combined test suites cannot pass.

The seed catalog includes additional hidden tests. They are hidden from API
responses, not secrets from people who can read the seed repository. Existing
custom problems need hidden tests supplied by an administrator.

## Start locally

From the repository root:

```sh
docker compose build backend worker
docker compose up -d postgres redis
docker compose run --rm -w /app backend python -m alembic upgrade head
docker compose run --rm backend python -m app.scripts.seed_problems --backfill-hidden
docker compose up -d backend worker frontend
```

`--backfill-hidden` adds the catalog's hidden cases only to existing seeded rows
whose hidden field is exactly `[]`; it preserves titles, samples, archive flags,
and nonempty hidden cases. Omit it if empty hidden cases were intentional.
Migrations normalize legacy submission statuses; unfinished legacy submissions
are queued and evaluated, with unsupported languages receiving `RUNTIME_ERROR`.

For a host worker, install backend dependencies, set `E2B_API_KEY`, then run
`python -m app.judge.worker` from `backend` with DATABASE_URL, REDIS_URL and
JWT_SECRET configured. The worker is a normal non-privileged process and does
not require Docker or a Docker socket.

## Isolation and limits

Each test case uses a fresh E2B sandbox with outbound network access disabled.
The worker writes only submitted source, a current case's input, and its fixed
runner into that sandbox; expected answers remain in PostgreSQL/the worker. E2B
enforces the per-command timeout, and the worker also uses a bounded E2B API
request timeout and six-second case budget. Sandboxes are terminated in a
`finally` block after success, user-code error, timeout, or API failure. A fresh
sandbox per case preserves the existing test isolation semantics and prevents
state from leaking between sample and hidden tests, at the cost of one short-lived
sandbox per test case.

## Queue recovery

Redis uses a sorted set keyed by submission ID to deduplicate redispatch, with
`BZPOPMIN` claiming the oldest ID. PostgreSQL QUEUED rows form the durable dispatch
record: every ten seconds between jobs, workers redispatch up to 1,000 queued
rows. Consequently a Redis outage, restart, or a crash between database commit
and enqueue does not lose a saved submission. The API returns the saved QUEUED row
even if Redis is temporarily unavailable. Redis AOF persistence is also enabled.

A conditional database update prevents duplicate execution claims. RUNNING rows
older than three minutes are requeued, and a unique execution ID prevents an old
worker from overwriting a replacement result. This is at-least-once execution;
an interrupted job may be evaluated again. A deleted submission's eventual
result is discarded. Infrastructure failures become a safe RUNTIME_ERROR rather
than a wrong-answer verdict. Monitor queue age, worker logs and runtime health.

## Verification

```sh
# Requires a disposable PostgreSQL database: the suite recreates its tables.
RUN_REDIS_TESTS=1 pytest backend/app/tests
npm --prefix frontend run typecheck
CI=true npm --prefix frontend test -- --watchAll=false
npm --prefix frontend run build
```

CI mocks the E2B SDK and exercises provider outcome mapping, bounded retries,
sandbox cleanup, database worker state transitions, and Redis queue behavior.
No CI test makes a real E2B API call. Locally, Redis integration tests remain
opt-in through the flag above.
