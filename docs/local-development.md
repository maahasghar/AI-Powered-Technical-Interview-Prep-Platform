# Local development

The local environment requires the React frontend, FastAPI backend, PostgreSQL, Redis, a judge worker and a feedback worker. This guide contains the setup commands and environment variables for local development. Run commands from the repository root unless a different directory is specified. Shell examples use Bash or Zsh.

## Prerequisites

- Docker with Docker Compose v2, with the Docker engine running.
- For running application processes outside Docker: Python 3.11 and Node.js 20 with npm, matching the repository's Docker images and CI configuration.
- An E2B API key to evaluate submitted code. The current judge uses remote E2B sandboxes even during local development; starting Docker does not provide a local execution fallback. Browsing problems and using authentication do not require this key.

PostgreSQL 15 and Redis 7 are provided by [docker-compose.yml](../docker-compose.yml). The default ports are 3000 (frontend), 8000 (API), 5432 (PostgreSQL), 6379 (Redis) and, when enabled, 11434 (Ollama).

## Environment configuration

For a new checkout, copy the example files. Preserve any existing local configuration instead of overwriting it:

```bash
cp .env.example .env
cp frontend/.env.example frontend/.env
```

Edit the root `.env` using these settings:

| Variable | Local value or requirement |
|---|---|
| `DATABASE_URL` | `postgresql+psycopg2://app:app@localhost:5432/app` for host processes. Compose overrides this with the `postgres` service hostname. |
| `REDIS_URL` | `redis://localhost:6379/0` for host processes. Compose overrides this with the `redis` service hostname. |
| `JWT_SECRET` | Required. Replace the example placeholder with a random local secret, shared by the API and workers. Generate one with `openssl rand -hex 32`. |
| `ENV` | `dev` for local development. |
| `CORS_ORIGINS` | `http://localhost:3000`; multiple allowed origins are comma-separated. |
| `FRONTEND_URL` | `http://localhost:3000`, used in verification and password-reset links. |
| `E2B_API_KEY` | Required for real submission execution. |
| `E2B_REQUEST_TIMEOUT_SECONDS` | `10` in the example file. |
| `EMAIL_DELIVERY_MODE` | `console` skips delivery and logs only the subject; it does not print verification or reset links. See the account setup below. |
| `RESEND_API_KEY`, `EMAIL_FROM` | Required for real email delivery with `EMAIL_DELIVERY_MODE=resend`; use a sender accepted by your Resend account. |
| `EMAIL_TIMEOUT_SECONDS` | `10` in the example file. |
| `FEEDBACK_AI_ENABLED`, `FEEDBACK_EVALUATION_PASSED` | Keep both `false` for initial setup. Both must be `true` to enable AI generation. |
| `FEEDBACK_PROVIDER`, `FEEDBACK_MODEL` | The example selects `ollama` and `llama3.1`. See optional AI setup below. |
| `OLLAMA_BASE_URL` | `http://localhost:11434` for host processes. Compose overrides it to `http://ollama:11434` for the feedback worker. |
| `SENTRY_DSN` | Leave empty unless testing error reporting. |

Keep the login, registration, resend-verification and submission rate-limit settings from [.env.example](../.env.example) for the initial setup. Additional defaults, including feedback limits and retry settings, are defined in [Settings](../backend/app/core/config.py).

The frontend reads its own `frontend/.env`:

```dotenv
REACT_APP_API_URL=http://localhost:8000/api/v1
```

This URL is used by the browser, so it uses `localhost` even when the frontend runs in Docker. Keep backend secrets out of frontend environment variables.

Host Python processes load the root `.env` through the settings module; exported environment variables take precedence. Compose injects the root `.env` into the backend and workers. Restart host processes or recreate Compose containers after changing settings; restart the frontend after changing its environment file.

## Run with Docker Compose

Start the database and queue, build the application images, then migrate and seed before starting the API and workers:

```bash
docker compose up -d --wait postgres redis
docker compose build backend worker feedback-worker frontend
docker compose run --rm backend python -m alembic upgrade head
docker compose run --rm backend python -m app.scripts.seed_problems
docker compose up -d backend worker feedback-worker frontend
```

The seed command inserts missing sample problems and preserves existing seeds. API startup does not run migrations automatically. Ollama is optional while AI generation is disabled.

Open:

- Frontend: <http://localhost:3000>
- Interactive API documentation: <http://localhost:8000/docs>
- API readiness: <http://localhost:8000/readyz>

Check service state and logs:

```bash
docker compose ps
docker compose logs --tail=100 backend worker feedback-worker frontend
curl --fail http://localhost:8000/readyz
```

Readiness checks PostgreSQL and Redis connectivity. It does not confirm migrations, worker activity, E2B access or AI availability; use the submission workflow below to check those paths.

## Run application processes on the host

Use this option for backend live reload and direct debugging. If the full Compose application is already running, stop its application services first to avoid port conflicts and duplicate workers:

```bash
docker compose stop backend worker feedback-worker frontend
docker compose up -d --wait postgres redis
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements-dev.txt
```

Use a Python 3.11 virtual environment created on your machine. On Windows, activate it with `.venv\Scripts\Activate.ps1` in PowerShell.

Apply migrations and seed data from `backend/`:

```bash
cd backend
python -m alembic upgrade head
python -m app.scripts.seed_problems
```

Open three terminals, activate the same virtual environment in each, and run one command per terminal from `backend/`:

```bash
# Terminal 1: API
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

```bash
# Terminal 2: judge worker
python -m app.judge.worker
```

```bash
# Terminal 3: feedback worker
python -m app.feedback.worker
```

In a fourth terminal, install and start the frontend from `frontend/`:

```bash
npm ci
npm start
```

The API and frontend reload on source changes. Restart workers after changing their Python code. The Compose backend and worker services do not mount source code; rebuild and recreate affected services when using the Docker workflow.

## Create a local account and check submissions

Register through the frontend. Login requires a verified account. For actual verification and password-reset emails, configure Resend as described above and follow the emailed link.

For the default console mode, mark only your development account as verified in the local Compose database. Replace `developer@example.com` with the address you registered:

```bash
docker compose exec postgres psql -U app -d app
```

```sql
UPDATE users
SET is_verified = TRUE, verified_at = NOW()
WHERE email = 'developer@example.com';
\q
```

This local shortcut does not test email delivery or the verification-token flow. Console mode cannot complete password reset because it does not expose the reset link.

Log in, open a seeded problem and submit a Python solution using its expected function signature. With a valid `E2B_API_KEY` and the judge worker running, the submission should progress from queued/running to a final result. Review the submission history and result page. AI coaching remains disabled until the optional setup below is complete.

## Optional: enable AI coaching with Ollama

The example configuration uses `llama3.1`. Start Ollama and download that model from the repository root:

```bash
docker compose up -d ollama
docker compose exec ollama ollama pull llama3.1
```

If Ollama is still starting, retry the pull after its service is ready. Model download and inference require additional disk space and memory.

With the rollout flags still disabled, run the evaluation against the actual provider. For the Compose workflow:

```bash
docker compose run --rm feedback-worker python -m app.scripts.evaluate_feedback
```

For host processes, run from `backend/` with the virtual environment activated:

```bash
python -m app.scripts.evaluate_feedback --report /tmp/feedback-evaluation.json
```

The evaluation CLI invokes the provider even when rollout flags are off. After it passes and you review the results, set both flags in the root `.env`:

```dotenv
FEEDBACK_AI_ENABLED=true
FEEDBACK_EVALUATION_PASSED=true
```

Recreate the Compose API and workers to load the updated environment:

```bash
docker compose up -d --force-recreate backend worker feedback-worker
```

For the host workflow, restart the API and both workers. Submit a new solution to check coaching generation. Rerun evaluation when changing the model, prompt or generation settings. See [AI feedback](ai-feedback.md) for evaluation scope and provider configuration.

## Development checks

See [testing](testing.md) for test layers, coverage limits, CI behavior and real-provider evaluation. The commands below are the local quick reference.

Backend test fixtures drop and recreate database tables. Use a separate disposable `app_test` database and explicitly set `DATABASE_URL` for the test command so an exported development URL cannot override it.

Create the test database once, from the repository root:

```bash
docker compose exec postgres createdb -U app app_test
```

If it already exists, reuse it only if it contains disposable test data. With the host virtual environment and development dependencies installed, run from the repository root:

```bash
DATABASE_URL=postgresql+psycopg2://app:app@localhost:5432/app_test REDIS_URL=redis://localhost:6379/1 JWT_SECRET=local-test-secret RUN_REDIS_TESTS=1 python -m pytest backend/app/tests
PYTHONPATH=backend python -m unittest discover -s backend/tests -v
ruff check backend
black --check backend
isort --check-only backend
```

From `frontend/`:

```bash
npm run typecheck
npm test -- --watchAll=false
npm run build
```

For browser tests, install Chromium once, then run the suite. Playwright starts the frontend automatically or reuses an existing server on port 3000:

```bash
npx playwright install chromium
npm run test:e2e
```

## Common issues and shutdown

| Symptom | Check |
|---|---|
| API cannot start or readiness returns 503 | Confirm PostgreSQL and Redis are healthy. Host processes use `localhost`; containers use Compose service names. |
| Missing-table errors | Run `alembic upgrade head` using the matching workflow above. |
| Browser API or cookie requests fail | Use `http://localhost:3000` consistently and check the API URL, allowed CORS origin and `ENV=dev`. Mixing `localhost` and `127.0.0.1` changes the origin. |
| Login requires verification | Follow the local account instructions; console email mode does not print a verification link. |
| Submission stays queued | Check that the judge worker is running and uses the same database and Redis instance as the API. |
| Submission execution fails | Check the worker logs, `E2B_API_KEY` and outbound connectivity to E2B. |
| AI coaching is unavailable | Check both rollout flags, feedback-worker logs, Ollama availability and whether the configured model was downloaded. |
| HTTP 429 | A configured rate limit was reached; wait for its window to expire or adjust the relevant local limit and restart. |
| Code edits do not appear in containers | Rebuild and recreate the affected backend/worker services with `docker compose up -d --build backend worker feedback-worker`. |
| Port already in use | Stop the conflicting process or change the published port and its corresponding environment URLs. |

Stop host processes with `Ctrl+C`. Stop the Compose services with:

```bash
docker compose down
```

Named volumes retain the PostgreSQL data, Redis data and downloaded Ollama models. Adding `--volumes` deletes those volumes and their contents; use it only for an intentional local reset.
