# Testing

The test strategy checks authentication, ownership, deterministic judging, asynchronous recovery and the separation between judge results and AI coaching. Automated suites use real databases/Redis where described below and controlled substitutes for external services. Passing them does not establish that production credentials, email delivery, remote sandboxes or a deployed model work.

Use [local development](local-development.md) for initial setup and [production deployment](production-deployment.md) for release smoke checks. Commands below run from the repository root unless stated otherwise.

## Test layers

| Layer | Location | Scope and dependencies |
|---|---|---|
| Backend unit/API/integration tests | `backend/app/tests/` | Pytest; database-backed cases use PostgreSQL and FastAPI TestClient. Queue integration includes real Redis. E2B, email and model calls use mocks/fakes in automated scenarios. |
| Worker/runtime regression tests | `backend/tests/` | Unittest; supervisor lifecycle, feedback leases, inference options and solution serialization. Feedback cases use temporary/in-memory SQLite; supervisor tests include local process shutdown. |
| Frontend component/client tests | `frontend/src/*.test.js` | React Testing Library/Jest through `react-scripts`; authentication races, routes, polling and feedback rendering with mocked API behavior. |
| Browser tests | `frontend/e2e/` | Playwright Chromium; practice journey and responsive landing/navigation. API routes are intercepted with fixture responses. |
| AI regression evaluation | `backend/app/scripts/evaluate_feedback.py` | Calls the selected real model/provider against fixed scenarios; separate from ordinary automated tests. |

## Backend setup and commands

Use Python 3.11 and a virtual environment. The [shared pytest fixtures](../backend/app/tests/conftest.py) drop and recreate database tables for database-backed tests. **Never run this suite against a production, restored business or valued development database.** Explicitly set `DATABASE_URL` on the test command: the fixtures preserve an already-exported value, even if `TEST_DATABASE_URL` is also set.

After preparing the root `.env` and virtual environment as described in the local guide:

```bash
source .venv/bin/activate
python -m pip install -r backend/requirements-dev.txt
docker compose up -d --wait postgres redis
docker compose exec postgres createdb -U app app_test
```

Create `app_test` only once; an existing database is suitable only if its contents are disposable. Run the full pytest suite with an explicit test database and a separate local Redis database:

```bash
DATABASE_URL=postgresql+psycopg2://app:app@localhost:5432/app_test REDIS_URL=redis://localhost:6379/1 JWT_SECRET=local-test-secret RUN_REDIS_TESTS=1 python -m pytest backend/app/tests
```

`RUN_REDIS_TESTS=1` enables the explicitly gated Redis test. Other integration cases also connect to Redis, so omitting this flag does not make the entire suite independent of Redis. Do not run application workers against the test database/queues, and do not run database-resetting tests concurrently against the same database.

For a focused deletion/progress check:

```bash
DATABASE_URL=postgresql+psycopg2://app:app@localhost:5432/app_test REDIS_URL=redis://localhost:6379/1 JWT_SECRET=local-test-secret python -m pytest backend/app/tests/test_progress.py
```

Run the separate worker/runtime suite:

```bash
DATABASE_URL=postgresql+psycopg2://app:app@localhost:5432/app_test REDIS_URL=redis://localhost:6379/1 JWT_SECRET=local-test-secret PYTHONPATH=backend python -m unittest discover -s backend/tests -v
```

### Migration and static checks

Pytest's table recreation does not replace checking Alembic migrations. CI applies migrations before pytest. To check migration application locally, run from `backend/` against the disposable test database:

```bash
DATABASE_URL=postgresql+psycopg2://app:app@localhost:5432/app_test REDIS_URL=redis://localhost:6379/1 JWT_SECRET=local-test-secret python -m alembic upgrade head
```

Use a fresh disposable database for a clean-install migration check; an `alembic_version` row can survive the fixture's application-table recreation. Neither a fresh upgrade nor pytest proves upgrade compatibility with every historical production dataset.

Run formatting and lint checks from the repository root:

```bash
ruff check backend
black --check backend
isort --check-only backend
pre-commit run --all-files
```

Pre-commit runs its pinned hooks and may modify files; review changes afterward. Its Black/Ruff pins are defined separately from the installed development dependencies, so check both configurations when investigating differences.

## Important backend scenarios

| Area | Representative test files and behavior |
|---|---|
| Authentication | `test_auth_routes.py`, `test_auth_cookie_contract.py`: login, refresh rotation/reuse, logout, cookie attributes, trusted-origin/CSRF requirements and safe user responses. |
| Email | `test_email_client.py`: Resend request contract, console mode, missing configuration and safe handling of provider/network failures. |
| Problem bank | `test_problem_workflow.py`: authentication/roles, filters, archiving, input validation and idempotent seeding. |
| Submission processing | `test_judge.py`, `test_submission_worker.py`: verdict mapping, sandbox cleanup/retry behavior, Redis integration, duplicate claims, stale-job recovery and ownership of final writes. |
| Public data | `test_public_submission_results.py`: allowlisted results, malformed/legacy data handling and exclusion of internal diagnostics. |
| Feedback | `test_feedback.py`, `test_feedback_workflow.py`: sanitized context, schema constraints, ordered stages, explicit solution requests, idempotency, retry limits and persistence after judging. |
| Progress/deletion | `test_progress.py`: user-scoped aggregates and removal of owned data while preserving shared problems. |
| Operational controls | `test_operational_controls.py`: rate limits, user scoping, sensitive metadata filtering and heartbeat TTL. |
| Integrated practice flow | `test_critical_journey_api.py`: API-level practice flow through result, coaching and history with controlled execution dependencies. |

These are representative coverage areas, not guarantees that every edge case is covered. In particular, deletion tests do not prove provider/backup erasure or all concurrent deletion races, and mock sandbox tests do not exercise the real E2B isolation boundary.

## Frontend and browser checks

Use Node.js 20. From `frontend/`:

```bash
npm ci
npm run typecheck
npm test -- --watchAll=false
npm run build
```

Client tests cover startup session restoration, shared refresh for concurrent unauthorized requests, bounded retries and login/logout races. Component tests cover protected routes, registration/reset flows, candidate-safe result rendering and staged feedback. Polling tests check terminal-state stopping, cancellation and bounded error behavior.

Install Chromium once, then run browser tests from `frontend/`:

```bash
npx playwright install chromium
npm run test:e2e
```

CI uses `npx playwright install --with-deps chromium` to install browser OS dependencies on its Linux runner. [Playwright configuration](../frontend/playwright.config.js) starts the frontend at `http://127.0.0.1:3000` or reuses an existing server. Ensure any reused server belongs to this checkout.

The critical journey signs in, submits Python, displays results/feedback and opens history using intercepted API responses. Landing tests cover widths of 360, 768 and 1440 pixels, keyboard skip navigation and horizontal overflow. Screenshots are written under `frontend/test-results/`; tracing is configured for a first retry, but retries are not enabled by default in the checked-in configuration.

These browser tests do not start FastAPI, PostgreSQL, Redis or workers and do not verify real cookies, email delivery, E2B or AI connectivity. Layout/keyboard checks are also not a complete accessibility audit.

## AI evaluation

Configure the chosen provider/model, then run from `backend/` with the virtual environment active:

```bash
python -m app.scripts.evaluate_feedback --report /tmp/feedback-evaluation.json
```

This calls the real provider even when AI rollout flags are disabled. The four fixed cases cover passed diagnosis, failed hint, runtime diagnosis and failed solution. Evaluation checks structured output and case-specific content rules; it does not execute suggested solutions or comprehensively grade educational quality and prompt-injection resistance.

The command exits nonzero on failure and does not set `FEEDBACK_EVALUATION_PASSED`. Review the report before changing rollout flags, and rerun after model/prompt/schema/generation-setting changes. Reports can include model output in validation details; review them before sharing. See [AI feedback](ai-feedback.md).

## CI and release validation

[CI](../.github/workflows/ci.yml) runs on pushes and pull requests to `main`. The backend job provisions PostgreSQL/Redis, applies migrations, runs lint/format checks, pytest and unittest, builds the API/worker images, performs a worker-image smoke check and runs pre-commit. The image smoke check mocks E2B and checks Ollama startup without downloading a model. The frontend job runs type checking, component tests, Chromium browser tests and a production build.

CI does not deploy the application or run the real-provider AI evaluation. Validate final HTTPS domains, email verification, session restoration, remote judging, worker completion and enabled coaching using the controlled release checks in [production deployment](production-deployment.md). Record which checks ran and their results; do not infer live-service health from mocked tests alone.
