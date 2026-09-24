# AI‑Powered Technical Interview Prep Platform

## Overview 

This project is a **production‑grade, full‑stack technical interview preparation platform** designed with real‑world engineering practices. Over the past month, the focus has been on building a **clean backend architecture**, **secure authentication**, and a **professional developer workflow** (Docker, pre‑commit, CI).

The goal is not just to build features, but to build them **the way real companies do**.

> **Current-state note:** this repository is an early backend foundation, not
> yet a production-ready full-stack application. See the
> [project guide and completion roadmap](docs/PROJECT_GUIDE.md) for the current
> architecture, known gaps, target architecture, and recommended build order.

---

## Tech Stack

### Backend

* **Python + FastAPI**
* **PostgreSQL** (planned / via Docker)
* **Redis** (planned – auth & caching)
* SQLAlchemy (ORM)
* Pydantic (request/response validation)

### Frontend (scaffolded)

* React (containerized)

### DevOps & Tooling

* Docker & Docker Compose
* Pre‑commit hooks (black, isort, ruff)
* GitHub Actions CI
* Virtual environments (venv)

---

## Backend Architecture

The backend follows a **clean architecture / DDD‑inspired structure**:

```
backend/app/
├── api/            # HTTP layer (FastAPI routes)
│   └── v1/
│       └── routers/
├── core/           # App wiring & configuration
│   ├── container.py
│   └── config.py
├── domain/         # Business logic
│   └── auth/
│       ├── service.py
│       ├── repository.py
│       └── models.py
├── infrastructure/ # DB, Redis, external integrations
└── main.py
```

### Layer Responsibilities

* **API**: Handles HTTP requests & responses only
* **Domain**: Pure business logic (no FastAPI, no DB specifics)
* **Infrastructure**: Database access, Redis, external services
* **Core**: Dependency injection & app wiring


Think of your backend like a company:

API = receptionist (talks to the outside world)

Domain = brain (business rules)

Infrastructure = tools & machines (databases, Redis, email, external services)

Core = shared policies & utilities (security, config, logging)

Each layer has one job.

This separation keeps the system:

* Testable
* Scalable
* Easy to reason about

---

## Authentication System

A **real‑world, production‑style auth flow** was designed.

### Password Security

* Password hashing & verification using a dedicated utility
* Plaintext passwords are never stored

### Token Strategy

* **Access tokens** → short‑lived
* **Refresh tokens** → long‑lived, stored in DB

### Refresh Token Lifecycle

* On login:

  * Generate access + refresh token
  * Save refresh token in DB

* On refresh:

  * Verify token exists
  * Ensure it’s not revoked
  * Ensure it’s not expired
  * Issue new access token

* On logout:

  * Mark refresh token as revoked

This mirrors how **real production systems** handle auth.

### Optional Email Verification (Designed)

* User signs up with `is_verified = false`
* Verification token generated
* Email link:

  ```
  https://yourapp.com/verify?token=abc123
  ```

---

## Dependency Injection

A lightweight container pattern is used:

* `core.container` stores **service instances**
* Routes call services through the container

This allows:

* Loose coupling
* Easier testing
* Clean separation between layers

---

## E2B execution provider

The judge worker uses E2B isolated sandboxes for submitted Python code. The Redis queue, SQLAlchemy submission lifecycle, test evaluation, and feedback pipeline remain independent of the sandbox provider through `ExecutionProvider`.

### Required environment variables

```env
E2B_API_KEY=
E2B_REQUEST_TIMEOUT_SECONDS=10
```

Create `E2B_API_KEY` in the E2B dashboard and store it in the local `.env` or the deployment secret manager. Never log the key. Each test case runs in a fresh sandbox with outbound network access disabled and is terminated after its command completes, fails, or times out.

### Local worker startup

```sh
cd backend
python -m app.judge.worker
```

### Railway startup

```sh
python -m app.judge.worker
```

This is a normal worker service; it does not require Docker socket access, a Docker daemon, or privileged mode.

The standalone feedback worker command is:

```sh
python -m app.feedback.worker
```

### Combined Railway workers and Ollama

Build `backend/Dockerfile.worker` with `backend` as the build context. Its default
command, `bash /app/start_workers.sh`, starts Ollama, waits for its API, downloads
`FEEDBACK_MODEL` if missing, then starts the judge and feedback workers. The
workers retain separate Redis queues. All three processes write to deployment
logs; a process exit stops the service so Railway can restart it. SIGTERM is
forwarded to all process groups, with forced cleanup after a 10-second grace period.

Set the combined service's variables:

```env
DATABASE_URL=
REDIS_URL=
JWT_SECRET=
E2B_API_KEY=
FEEDBACK_AI_ENABLED=true
FEEDBACK_EVALUATION_PASSED=true
FEEDBACK_PROVIDER=ollama
FEEDBACK_MODEL=<your-evaluated-Ollama-model-name>
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODELS=/data/ollama
```

Mount a persistent Railway volume at `/data` to retain downloaded models. The
supervisor sets `OLLAMA_HOST=127.0.0.1:11434` and
`OLLAMA_BASE_URL=http://127.0.0.1:11434` for its children, overriding stale external
hostnames. Ollama is internal to this container and needs no public domain.
The AI enablement/evaluation flags retain their existing meaning; enabling this
container does not bypass those checks.

Optional startup limits are `OLLAMA_STARTUP_TIMEOUT_SECONDS=60` and
`OLLAMA_PULL_TIMEOUT_SECONDS=900`. The first deployment can take longer while the
model downloads. Choose a model that fits the service's memory and CPU capacity.
See [Railway setup and verification](docs/production-deployment.md#combined-workers-with-ollama-on-railway).

The standalone judge command remains `python -m app.judge.worker`. Local Compose
explicitly uses that command and keeps its separate Ollama and feedback services.
For an external AI provider, run the standalone workers using the normal backend
image rather than the combined Ollama startup command.

## Docker & Docker Compose

### Purpose

* Ensure consistent environments
* Run backend, frontend, DB, Redis together
* Avoid "works on my machine" problems

### Dockerfile

* Defines how each service is built
* One Dockerfile per service

### docker-compose.yml

* Orchestrates all services
* Lives at the **project root**

---

## Pre‑commit Hooks

### Why

* Enforce code quality **before commit**
* Prevent bad formatting from entering the repo

### Tools Used

* **black** → code formatting
* **isort** → import ordering
* **ruff** → linting

### Behavior

* Hooks auto‑format code
* If files change → commit fails
* Developer re‑adds files and commits again

This enforces **discipline and consistency**.

---

## GitHub Actions CI

A CI pipeline was added to enforce quality at the repo level.

### Workflow

* Runs on:

  * Push to `main`
  * Pull requests

### What it does

* Sets up Python
* Installs pre‑commit
* Runs all hooks on the entire codebase

This ensures:

* No unformatted code reaches `main`
* Local mistakes don’t slip through

---

## Development Environment (Windows)

* Python virtual environment (venv)
* Explicit activation required before:

  * running pre‑commit
  * committing code

Significant work was done debugging:

* Python path issues
* Windows Store Python conflicts
* Pre‑commit permissions

Result: **stable, reproducible setup**.

---

## Engineering Mindset

Over this month, the project intentionally emphasized:

* Production‑grade architecture
* Real authentication flows
* Developer experience (DX)
* Tooling used by professional teams


## Problem bank workflow

Problem routes require an access token in `Authorization: Bearer <token>`.
Authenticated users can list active problems with `GET /api/v1/problems` and
read one with `GET /api/v1/problems/{id}`. Category and difficulty filters combine
with `skip`/`limit` pagination.

Only admins can create (`POST /api/v1/problems`), update
(`PATCH /api/v1/problems/{id}`), or archive (`DELETE /api/v1/problems/{id}`).
DELETE sets `is_active=false`; it preserves the problem and its submissions.
Admins can list archived entries with `?include_inactive=true`, read them by ID,
and restore them with PATCH `{"is_active": true}`. Regular users receive 404
for archived problem IDs. New submissions require an active problem; existing
submissions remain available under the existing ownership rules.

To migrate and seed, use a configured backend environment (Python 3.11 and the
backend requirements installed). From the repository root:

```sh
cd backend/app
python -m alembic upgrade head
cd ..
python -m app.scripts.seed_problems
```

The script inserts 15 problems spanning easy, medium, and hard difficulties,
with descriptions and JSON test cases (`input` arguments and `expected` output).
Stable unique seed keys make repeated and concurrent runs safe. Existing seed
rows, admin edits, and archive state are preserved; custom problems are untouched.
Seeding is an explicit maintenance command and does not run on server startup.

## Next Steps (Planned)

* Add pytest + coverage reporting
* Add Redis integration
* Add Docker‑based CI build step
* Add frontend → backend integration
* Deploy (Render / Fly.io / AWS)

---

## Python judge

Submissions run asynchronously through Redis and a separate Docker judge worker.
See [setup, limits, and test instructions](docs/submission_execution.md).
