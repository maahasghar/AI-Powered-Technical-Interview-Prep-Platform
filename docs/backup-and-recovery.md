# Backup and Recovery

PostgreSQL is the durable system of record. The repository contains no backup scheduler, snapshot policy, restore automation or checked-in managed-provider backup configuration. The existing project targets below are retained as recommendations, not evidence that a live environment meets them.

## Why Use Managed PostgreSQL Backups?

The application must recover users, problem definitions and historical attempts consistently, not just restart its containers. SQLAlchemy/Alembic manage application data and schema, but do not implement a backup subsystem. Database-native snapshots or provider-managed backups avoid building custom snapshot/retention machinery into FastAPI workers.

This delegates storage consistency and backup operations to infrastructure at the cost of provider dependence and operational verification. Confirm backup enablement, restore/export options, retention, encryption and access controls with the operator. No Railway frequency, PITR capability, SLA or recovery guarantee is established by this repository. Reconsider an additional encrypted export strategy if provider portability or verified retention requirements demand it; no such scheduled export is currently implemented.

## Data Requiring Backup

Back up the complete application database with transactionally consistent tooling, including schema and sequences.

| Table / entity | Durable information |
|---|---|
| `users` / `User` | Identity, password hashes, role and verification state. |
| `user_profiles` / `UserProfile` | Candidate profile fields. |
| `auth_tokens` / `AuthToken` | Hashed refresh sessions, families, expiration and revocation. |
| `account_tokens` / `AccountToken` | Hashed verification/reset credentials, expiry and consumption state. |
| `problem_bank` / `Problem` | Public problem content, hidden tests, archive state and seed keys. |
| `submissions` / `Submission` | Source, ownership, exact lifecycle status, execution claim and serialized judge result. |
| `submission_feedback` / `Feedback` | Staged structured coaching, lifecycle claims and traceability metadata. |
| `audit_events` / `AuditEvent` | Security-relevant event history. |
| `alembic_version` | Migration revision needed to select compatible application code. |

Sources: [auth models](../backend/app/domain/auth/models.py), [account tokens](../backend/app/domain/auth/token_models.py), [profiles](../backend/app/domain/user/models.py), [problems](../backend/app/domain/problems/models.py), [submissions](../backend/app/domain/submissions/models.py), [feedback](../backend/app/feedback/models.py), and [audit](../backend/app/audit.py).

Progress is computed from submissions and problems; there is no separate progress table to restore. Provider credentials and `JWT_SECRET` are not restored by a database backup: recover them through the deployment's protected configuration process. Ollama model downloads can be recreated, although losing their volume extends startup time. Transient E2B sandboxes are not business-data backups.

## Redis Recovery

Redis contains sorted-set work queues, rate-limit counters and expiring heartbeat keys. Local Compose enables AOF and a volume, but PostgreSQL remains the recovery source. Redis loss can reset rate-limit windows and discard heartbeat observations; it does not erase committed submissions or feedback.

With Redis restored or replaced, workers redispatch `QUEUED` database rows. Judge reconciliation also requeues `RUNNING` rows stale for more than 180 seconds. Feedback reconciliation renews missing initial diagnoses and marks stale `RUNNING` feedback `FAILED` for explicit retry, rather than automatically repeating potentially paid inference. Recovery occurs between jobs and is not instantaneous.

Use empty, isolated queues for a database restore to avoid old queue IDs referring to different restored records. Do not blindly copy queues from a newer database timeline. This is at-least-once work recovery, not replay of every past infrastructure operation. See [submission lifecycle](submission-lifecycle.md).

## Recovery Procedure

This is an operator runbook, not a previously demonstrated restore. No restore is performed by these documentation changes.

1. **Choose a recovery point.** Identify the incident, last trustworthy snapshot/export, database version and matching application revision. Verify the backup exists and is restorable. Record the expected data-loss window. Stop writes and both workers before production cutover; preserve the old environment for investigation.
2. **Restore in isolation.** Provision a compatible PostgreSQL instance and restore the selected provider snapshot or protected database dump using the provider/database tooling. Do not overwrite the only live copy as a first test. Restrict access: backups contain password hashes, user source and hidden cases.
3. **Reconnect compatible code.** Set `DATABASE_URL`, `REDIS_URL` and other required settings through the secret/configuration mechanism, without printing their values. Use the explicit `postgresql+psycopg2` driver prefix matching installed dependencies. Connect a separate Redis instance/database for the drill. Keep worker and public traffic disabled until database checks pass.
4. **Inspect migration state.** From `backend/`, with dependencies installed and the intended environment loaded, run the commands below. Compare the restored revision with the application release. Inspect intervening migrations before upgrading a restored copy; do not stamp or downgrade to conceal a mismatch.
5. **Review restored identities and deletions.** A backup can revive revoked sessions, consumed reset tokens or deleted users. Before public access, reconcile known deletions and decide whether to invalidate restored authentication records or rotate signing credentials. The repository has no automated post-restore invalidation/reconciliation command.
6. **Verify API and workers.** Start the API and the selected worker topology against the isolated restored database. Complete the verification below before switching public traffic. Use approved test accounts and provider settings; new sandbox or AI calls can incur costs.
7. **Cut over and observe.** Update all API and worker connections together, reopen writes, monitor queue ages/errors and record actual recovery time. Keep the rollback copy and incident record according to the operator's retention policy.

```sh
# Run from backend/ with the restored database configured.
python -m alembic current
python -m alembic heads
# After reviewing migration compatibility on the restored copy:
python -m alembic upgrade head
```

The production-deployment guide referenced by older docs is absent, so no broken link to it is added here. Use [architecture deployment notes](architecture.md#deployment-topologies-and-health), [production Compose](../docker-compose.production.yml), [worker image](../backend/Dockerfile.worker) and [Supervisor](../backend/app/scripts/run_workers.py) as the available configuration evidence. Actual Railway backup controls and volume attachments must be verified in the deployment account.

## Restore Verification

| Check | Evidence required before cutover |
|---|---|
| Database/schema | Alembic current revision agrees with reviewed migrations; row counts, relationships and representative records agree with the selected recovery point. |
| API reachability | `/health` responds; `/ready` or `/readyz` also succeeds against PostgreSQL and Redis. Readiness does not test E2B or AI. |
| Authentication | Approved verified account can log in, reload/refresh, and log out; cookie flags/origins work at the intended hostnames. |
| Problems | Authenticated list/detail return expected active problems; archived problems and admin restrictions behave correctly. |
| History/progress | Owner can read representative old submissions and feedback; other users cannot; progress reflects restored attempts. |
| New work | Submit a known Python solution and observe `QUEUED`/`RUNNING` reaching a valid terminal state. Verify expected wrong-answer behavior separately. |
| Background recovery | Workers consume new work and reconcile restored pending rows without overwriting newer claims. Check stale feedback is retryable. |
| Coaching | Eligible results produce the configured AI or deterministic fallback behavior; solution-generation failure leaves judge results intact. |
| Data hygiene | Restored deleted accounts/session credentials were reviewed; logs and exports are access-restricted. |

Do not run the backend test suite against a restored business database: its fixtures recreate tables. Use smoke checks with controlled records instead. Record the selected backup timestamp, restore duration, schema revision and verification outcome without credentials or raw candidate data.

## RPO and RTO

The previous project guide proposed **daily backups, at least 30 days of retention, RPO 24 hours, and RTO four hours**. These remain MVP operational targets, not provider guarantees or measured achievements.

- **RPO** is the acceptable data-loss window between the last recoverable point and the incident. Daily successful backups can support a 24-hour target only when backup completion and restore validity are verified.
- **RTO** is the acceptable time to recover service, including database restore, configuration, validation, worker recovery and cutover. Four hours must be demonstrated through drills, not inferred from container startup time.

Run a restore drill at least quarterly as a project recommendation and after material storage/deployment changes. Revisit targets when data-loss tolerance, restore duration or account-deletion retention requirements change. Deleted data can remain in retained snapshots; the application has no automatic backup erasure mechanism.
