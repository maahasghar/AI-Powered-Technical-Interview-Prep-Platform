# AI‑Powered Technical Interview Prep Platform

## Overview

This project is a **production‑grade, full‑stack technical interview preparation platform** designed with real‑world engineering practices. Over the past month, the focus has been on building a **clean backend architecture**, **secure authentication**, and a **professional developer workflow** (Docker, pre‑commit, CI).

The goal is not just to build features, but to build them **the way real companies do**.

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


## Next Steps (Planned)

* Add pytest + coverage reporting
* Add Redis integration
* Add Docker‑based CI build step
* Add frontend → backend integration
* Deploy (Render / Fly.io / AWS)

---


