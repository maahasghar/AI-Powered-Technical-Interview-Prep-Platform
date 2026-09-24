# Production deployment

The production topology has four independently deployable services:

```text
web (Nginx static React app) -> api (FastAPI) -> managed PostgreSQL
                                      |          -> managed Redis
                                      +-> judge-worker -> E2B sandbox API over HTTPS
                                      +-> feedback-worker -> configured provider
```

The API and workers use the same image source but have separate processes and
scaling/restart policies. PostgreSQL and Redis are external managed services;
the production Compose file deliberately does not provision local database or
Redis containers. The judge worker is a normal process and does not require a
Docker socket, Docker daemon, or privileged container access.

## Combined workers with Ollama on Railway

To run judge, feedback, and Ollama in one service:

1. Set the worker service's Root Directory to `/backend` and
   `RAILWAY_DOCKERFILE_PATH=Dockerfile.worker`. The build context must contain
   `requirements.txt`, `start_workers.sh`, and `app/`.
2. Set the Start Command to `bash /app/start_workers.sh` (or clear the override
   to use the image's default). Do not use the API Dockerfile or the previous
   judge-only start command for this combined service.
3. Attach a persistent volume mounted at `/data`. Set `OLLAMA_MODELS=/data/ollama`.
4. Configure `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, and `E2B_API_KEY` as for
   the existing workers, pointing at the same database and Redis as the backend.
   Set `FEEDBACK_PROVIDER=ollama`, `FEEDBACK_MODEL` to the exact Ollama model name
   you evaluated, and `FEEDBACK_AI_ENABLED=true` / `FEEDBACK_EVALUATION_PASSED=true`
   once that evaluation has passed. Set `OLLAMA_BASE_URL=http://127.0.0.1:11434`.
5. Deploy. Logs should show Ollama starting, the model download (or an already
   installed message), then `Ollama and both workers are running.` The model is
   downloaded on container startup, not during the build or pre-deploy phase,
   so it can be stored on the mounted volume.
6. Through SSH into this worker, check the installed models:

   ```sh
   python -c 'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=5).read().decode())'
   ```

   Submit a new solution and request feedback. Confirm feedback has `source=ai`
   and that Show solution includes code. Existing saved fallback feedback does
   not regenerate just by refreshing the page.

The supervisor starts `ollama serve`, waits for its API, installs the configured
model if missing, then starts both queue workers. It forces loopback addresses
for Ollama and the feedback client, including when an old `http://ollama:11434`
variable remains configured. No public Ollama port or domain is required.

The server readiness timeout defaults to 60 seconds (`OLLAMA_STARTUP_TIMEOUT_SECONDS`)
and model download timeout to 900 seconds (`OLLAMA_PULL_TIMEOUT_SECONDS`). Missing
model configuration, download failure, or any process exiting produces a nonzero
service exit. Configure Railway to restart on failure. Shutdown signals reach all
three process groups; remaining processes are killed after a 10-second grace period.

All three share the service's CPU, memory, and restart lifecycle. Size the service
for the selected model plus both workers; CPU inference may exceed the feedback
request timeout. A mounted volume avoids repeated model downloads. The Docker
build argument `OLLAMA_IMAGE` defaults to `ollama/ollama:latest`; override it with
an evaluated tag or digest for reproducible releases.

The existing production Compose setup still runs standalone workers. Local
Compose retains its separate Ollama container. To use an external provider, run
the standalone worker commands in the normal backend image.

### Slow CPU inference and feedback timeouts

If the logs show `ReadTimeout` after 120 seconds while Ollama remains running,
deploy the updated feedback worker and try these variables on the worker service:

```env
FEEDBACK_TIMEOUT_SECONDS=600
FEEDBACK_MAX_RETRIES=0
OLLAMA_NUM_THREAD=1
OLLAMA_NUM_PREDICT=1024
```

The timeout default remains 120 seconds; 600 gives CPU inference more time to
finish. Disabling automatic retries avoids immediately repeating a slow request.
The Ollama request explicitly sets CPU threads (default 1) and maximum output
tokens (default 1024). Tune thread count to the CPU actually allocated to this
container. The token cap bounds generation; an incomplete JSON response still
fails validation and falls back rather than being shown as a complete solution.

Active feedback jobs now renew their database timestamp every 30 seconds during
inference and retry waits. The three-minute recovery threshold applies to jobs
whose heartbeat stopped, so another worker won't reclaim a healthy long request.
Deploy this change to every feedback worker before increasing timeouts.

These settings do not guarantee enough CPU or memory for the model. Check service
metrics during a request; increase the constrained resource if usage reaches the
service limit. Verify with a new submission because existing fallback feedback
is saved and will not regenerate on refresh.

### Deploying the solution code response

Deploy the API, feedback worker, and frontend together for feedback schema v2.
Show solution now requires `solution_code` containing Python source with a `solve`
function; `next_step` contains the explanation. The frontend renders the code
directly in a code block. Syntax checking does not execute or prove the code correct.
If prompt/schema version variables are overridden, update them to
`FEEDBACK_PROMPT_VERSION=2026-09-24-v2` and `FEEDBACK_SCHEMA_VERSION=2`.

Previously saved fenced solutions remain readable. Old text-only solution records
are shown as unavailable and can be regenerated with **Retry show solution**.
New solution generation failures remain retryable instead of saving generic review
text as a completed solution. Diagnosis and hint fallback behavior is unchanged.

## First deployment

1. Provision managed PostgreSQL with TLS, automated backups, and a restricted
   application role. Provision managed Redis with TLS and a restricted user.
2. Copy `.env.production.example` to `.env.production` and replace every
   placeholder using the deployment secret manager. Never commit that file.
3. Create an E2B API key and store it as `E2B_API_KEY` in the deployment secret manager. Set `E2B_REQUEST_TIMEOUT_SECONDS=10` unless an approved operational change requires a different bounded value.

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

## Email delivery with Resend

Verification and password-reset messages use the
[Resend HTTPS API](https://resend.com/docs/api-reference/emails/send-email).
On the Railway **backend** service, configure:

```env
EMAIL_DELIVERY_MODE=resend
RESEND_API_KEY=re_your_api_key
EMAIL_FROM=Interview Prep <no-reply@your-verified-domain.com>
EMAIL_TIMEOUT_SECONDS=10
FRONTEND_URL=https://frontend-production-ef78.up.railway.app
```

Create an API key with sending permission and verify your sending domain in
Resend. Replace `EMAIL_FROM` with an address on that domain. Resend's
`onboarding@resend.dev` test sender only sends to your own account email;
[verify a domain to send to other users](https://resend.com/docs/knowledge-base/403-error-resend-dev-domain).
Keep the API key in backend secrets, never frontend variables. Deploy the updated
backend after saving the variables. SMTP variables are no longer used and can be
removed. HTTPS delivery does not require Railway's outbound SMTP support.

Local development defaults to `EMAIL_DELIVERY_MODE=console`, which logs that
delivery was skipped and does not send a message or expose verification tokens.
Use `resend` mode to test actual delivery. Verify registration and password-reset
messages using an inbox you control, and check delivery status in Resend.
Provider failures return HTTP 503 with a safe message; backend logs contain the
provider HTTP status without the API key or email contents. Check the API key,
verified sender, and provider limits if Resend rejects a request. Requests have
a configurable timeout and are not automatically retried.
Registration currently saves the account before sending email. If delivery fails
and registering again reports that the email is already registered, fix delivery
and use the frontend's resend-verification page for that account.

## Readiness and worker liveness

`/health` is a process liveness check. `/readyz` checks PostgreSQL and Redis and
returns `503` until both dependencies respond. The API healthcheck uses
`/readyz`; the web healthcheck uses `/healthz`. The judge-worker healthcheck is
Redis/queue liveness. E2B sandbox requests use bounded API and execution timeouts; infrastructure errors are recorded as unavailable execution results rather than user-code failures.

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
