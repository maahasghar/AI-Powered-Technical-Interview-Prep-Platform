# Backup and recovery

PostgreSQL is the system of record. Back up users, profiles, authentication
records, problems, submissions, feedback, and audit events with the managed
PostgreSQL provider's native backups or a scheduled encrypted dump. Redis holds
queue, rate-limit, and other recoverable operational state; it does not need a
business-data backup in this architecture.

For the MVP, use daily backups with at least 30 days of retention. The target
is an RPO of 24 hours and an RTO of 4 hours; these are targets, not guarantees
until the deployment provider and restore drills support them.

## Restore procedure

1. Provision an isolated PostgreSQL instance at the target version.
2. Restore the selected managed snapshot or encrypted dump.
3. Set `DATABASE_URL` for a maintenance deployment and run `alembic upgrade head`.
4. Verify `/health`, authentication, problem reads, submission history, and
   progress aggregation against a sanitized smoke-test account.
5. Reconnect the application only after row counts, migration revision, and
   representative feedback/submission records have been checked.

Run a restore verification at least quarterly. Deleted records can remain in
backup snapshots until the configured backup-retention period expires.