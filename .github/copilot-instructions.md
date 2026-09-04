# Project Coding Instructions

## Architecture

- Keep API routes thin; place business logic in domain services.
- Keep database access in repositories.
- Use request-scoped SQLAlchemy sessions.
- Preserve the separation between API, domain, infrastructure, and core layers.
- Do not execute user-submitted code inside the FastAPI process.

## Backend

- Use FastAPI, SQLAlchemy, and Pydantic consistently.
- Version public routes under `/api/v1`.
- Add tests for new routes and services.
- Map domain exceptions to explicit HTTP responses.
- Never log passwords, JWTs, refresh tokens, or other secrets.
- Use existing repository and service patterns before creating new abstractions.

## Frontend

- Use React components with clear, focused responsibilities.
- Keep API calls in a shared client layer.
- Include loading, error, and empty states.
- Keep authentication state centralized.
- Make interfaces responsive and accessible.

## Editing

- Make the smallest change that solves the problem.
- Do not modify unrelated files.
- Do not commit changes unless explicitly requested.
- Run focused tests or validation after editing.
- Update documentation when behavior or architecture changes.

## Product Direction

The primary MVP journey is:

Register/login -> browse problems -> submit Python code -> receive a verdict -> view submission history.

Prioritize completing this vertical slice before adding advanced AI features.
Keep code execution separate from API Server to avoid security risks.