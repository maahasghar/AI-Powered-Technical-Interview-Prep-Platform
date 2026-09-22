# Production deployment

The production topology has four independently deployable services:

```text
web (Nginx static React app) -> api (FastAPI) -> managed PostgreSQL
                                      |          -> managed Redis
                                      +-> judge-worker -> isolated judge host
                                      +-> feedback-worker -> configured provider
```

The API and workers use the same image source but have separate processes and
scaling/restart policies. PostgreSQL and Redis are external managed services;
the production Compose file deliberately does not provision local database or
Redis containers.

## First deployment

1. Provision managed PostgreSQL with TLS, automated backups, and a restricted
   application role. Provision managed Redis with TLS and a restricted user.
2. Copy `.env.production.example` to `.env.production` and replace every
   placeholder using the deployment secret manager. Never commit that file.
3. Build the trusted judge image on the dedicated worker host:

   ```sh
   docker build -t interview-judge-python:local backend/judge
   ```

4. Apply migrations from a one-off API image before starting traffic:

   ```sh
   docker compose -f docker-compose.production.yml run --rm api \
     sh -lc 'cd /app && alembic upgrade head'
   ```

5. Deploy the web, API, judge-worker, and feedback-worker services:

   ```sh
   docker compose -f docker-compose.production.yml up -d --build
   ```

6. Verify `/health`, `/readyz`, web `/healthz`, worker heartbeat keys, login,
   problem reads, a test submission, and feedback polling before production
   traffic is enabled.

## Readiness and worker liveness

`/health` is a process liveness check. `/readyz` checks PostgreSQL and Redis and
returns `503` until both dependencies respond. The API healthcheck uses
`/readyz`; the web healthcheck uses `/healthz`.

Workers refresh these Redis keys with a 30-second TTL:

```text
health:worker:judge
health:worker:feedback
```

Alert when either key is missing for two consecutive evaluation periods.

## Dashboards

Create a managed-platform dashboard with API access logs, Redis metrics,
PostgreSQL metrics, and Sentry/application logs:

| Panel | Signal | Target |
| --- | --- | --- |
| API availability | successful `/readyz` requests | >= 99.9% |
| API latency | p50/p95/p99 by route | p95 < 500 ms for non-submit routes |
| HTTP errors | 4xx/5xx rate by route | investigate 5xx > 1% |
| Submission queue age | oldest `QUEUED` item | < 2 minutes |
| Judge throughput | completed submissions/minute | compare with traffic |
| Feedback queue age | oldest queued feedback | < 5 minutes |
| Worker liveness | heartbeat key age | < 30 seconds |
| Database/Redis | provider CPU, storage, connections, memory, latency | provider baseline |

Do not put source code, credentials, tokens, hidden tests, or authorization
headers into dashboard labels or log fields.

## Alerts

- API readiness failures for 2 minutes.
- Web/API healthcheck failure for 3 consecutive checks.
- API 5xx rate above 1% for 5 minutes or p95 latency above 1 second for 10 minutes.
- Oldest submission above 2 minutes for 5 minutes.
- Oldest feedback item above 5 minutes for 10 minutes.
- Missing judge or feedback heartbeat for 60 seconds.
- PostgreSQL connections/storage above 80% or failed backups.
- Redis memory above 80%, evictions above zero, or elevated command latency.

Each alert should link to the dashboard and identify the owning service. Avoid
alerting on ordinary rejected submissions.

## Rollback

1. Stop routing new traffic to the release while leaving the previous release
   available.
2. Inspect API/worker logs, Sentry, queue age, and `/readyz`.
3. Roll back web/API/worker images together to the last known-good image tag.
4. Prefer a forward fix for additive migrations. Restore a database snapshot
   only through an approved incident decision; never run an unreviewed
   destructive downgrade against production data.
5. Re-run readiness, login, problem read, submission, result, feedback, and
   history smoke checks.
6. Preserve the failed image and logs for investigation and record recovery time.

Use expand/migrate/contract releases for destructive schema changes.