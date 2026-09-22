# Production-readiness MVP behavior

## Progress

Authenticated users can query `GET /api/v1/users/me/progress`. It calculates
attempted submissions, passed submissions, solve rate, difficulty/category
breakdowns, and the ten most recent activities from PostgreSQL. No aggregate
cache or background job is required.

## Submission and feedback states

The deterministic judge remains authoritative. `QUEUED` and `RUNNING` are
shown as evaluation progress; `PASSED`, `FAILED`, `RUNTIME_ERROR`, and
`TIME_LIMIT_EXCEEDED` are terminal judge outcomes. Feedback is independent:
provider failures retain the judge result and use deterministic fallback
guidance, while a failed feedback record can be retried from the UI.

## Rate limits

Redis fixed-window limits protect login, registration, verification resend,
submission creation, and feedback generation. Defaults and windows are
configurable with the `*_RATE_LIMIT` and `*_RATE_WINDOW_SECONDS` settings in
`.env`. Unauthenticated limits use a hashed client IP; authenticated expensive
operations use the user ID. Exceeded requests return `429` with `Retry-After`.

## Audit events

Append-only PostgreSQL audit events record registration, login success/failure,
email verification, session revocation/rotation, submission creation, problem
changes, and account deletion. Audit metadata is filtered for credential,
token, source-code, hidden-test, and secret-like keys. Audit events never store
request bodies or authorization headers.

## Account deletion and retention

`DELETE /api/v1/users/me` requires authentication. It removes the account,
profile, submissions, feedback, authentication tokens, and temporary account
tokens. Shared problem records are preserved. Expired account tokens and
expired/revoked refresh tokens are cleaned during authentication operations.
Audit records are append-oriented and may retain the deleted user ID for
security investigation. PostgreSQL backup snapshots may retain deleted data
until their documented retention period expires.

Production service topology, readiness checks, worker heartbeats, dashboards,
alerts, and rollback steps are documented in
[production deployment](production-deployment.md).