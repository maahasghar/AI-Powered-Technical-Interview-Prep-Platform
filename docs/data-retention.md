# Data retention

This document describes implemented retention, account deletion and session cleanup. The application has no general age-based data purge or scheduled retention worker. Token expiration limits credential validity; it does not guarantee immediate removal of the corresponding database row.

## Retention by data type

| Data | Implemented lifecycle |
|---|---|
| Users and profiles | Retained until account deletion; no automatic inactive/unverified-account purge. |
| Submissions, submitted source and judge results | Retained for history and progress until the owner deletes their account; no age-based purge. |
| Feedback and generation metadata | Retained with the submission and deleted during owner account deletion. |
| Shared problems and tests | Preserved during account deletion. Problem archiving hides a problem from active practice without deleting historical submissions. |
| Refresh-session records (`auth_tokens`) | Store token hashes, family IDs, expiration and revocation state. Expired or revoked rows are deleted opportunistically at the start of login. |
| Verification/reset records (`account_tokens`) | Store token hashes, type, expiry and consumption state. Expired rows are deleted when a new account token is created. |
| Audit events | Preserved after account deletion; no automatic expiration or anonymization job. |
| Redis rate-limit counters | Expire after the configured rate-limit window, set when the counter is first created. |
| Redis worker heartbeats | Default expiry is 30 seconds, renewed by workers. |
| Redis queue entries | Contain record IDs and are removed when popped by workers; no age-based queue TTL. |
| Application/provider logs and backups | Retention is controlled outside the application; no checked-in policy enforces a duration. |

Progress is calculated from submission history rather than retained as a separate analytics dataset. Source: [user service](../backend/app/domain/user/service.py), [authentication repositories](../backend/app/domain/auth/repository.py), [account-token repository](../backend/app/domain/auth/token_repository.py), [rate limiter](../backend/app/core/rate_limit.py) and [queue](../backend/app/infrastructure/submission_queue.py).

## Account deletion

An authenticated user can call `DELETE /api/v1/users/me`. The endpoint derives the account from the access token and returns `204 No Content` after successful deletion. It clears the refresh cookie at `/api/v1/auth`.

[UserService.delete_account](../backend/app/domain/user/service.py) performs the following database work in one transaction:

1. Record an `ACCOUNT_DELETED` audit event.
2. Delete feedback attached to the user's submissions, then delete those submissions.
3. Delete refresh-session and verification/reset-token records.
4. Delete the profile and user record, then commit.

Shared problems and other users' records are outside this deletion scope. Audit events, including prior events and the deletion event, remain. Audit records can retain the numeric actor ID, target ID, IP address if supplied, timestamps and metadata. Deletion is therefore not complete anonymization of every stored record.

Deleted refresh records cannot establish new sessions. Existing access JWTs are not individually erased or added to a denylist, but protected requests look up the user and reject the token once that user no longer exists.

### Queue and external-work boundaries

Account deletion does not explicitly remove Redis queue IDs or cancel a running E2B/AI request. A judge job for a missing submission cannot claim that row, and result persistence is conditional on the claimed row still existing. Work already sent to an external provider may continue after database deletion. The endpoint does not promise cancellation of every in-flight request or erase provider-side copies.

The deletion path does not purge logs, audit events, backups, email-provider records or AI/execution-provider data. Any required external erasure or log cleanup is an operator responsibility; no automated cross-provider deletion workflow is implemented.

## Session and account-token cleanup

The lifetimes below come from [security helpers](../backend/app/core/security.py) and [AuthService](../backend/app/domain/auth/service.py):

| Credential | Lifetime and invalidation |
|---|---|
| Access JWT | 15 minutes by default. Validated on each protected request, including lookup of the user. |
| Refresh JWT and database session | 30 days per issuance. Refresh rotates the token and issues a replacement with a new 30-day expiry. |
| Email-verification token | 24 hours. Successful verification marks it used; resending invalidates earlier unused verification tokens for that user. |
| Password-reset token | 30 minutes. A new request invalidates earlier unused reset tokens; successful reset marks the token used and revokes the user's refresh sessions. |

Logout revokes the presented refresh-token family. Reuse of a revoked refresh token revokes its family when that record is still available. Password reset revokes all refresh sessions for the user. Neither logout nor password reset immediately invalidates already-issued access JWTs for an existing user; they can remain valid until expiry.

Cleanup is triggered by activity:

- Every login attempt first deletes expired **or revoked** refresh rows, across users.
- Creating a verification or reset token first deletes expired account-token rows, across users.
- Used account tokens remain until expiration and a later cleanup trigger, unless the account is deleted first.

There is no timer, cron job or retention CLI guaranteeing that cleanup runs during inactivity. Expired credentials are rejected even if their rows remain. Deleting revoked refresh rows also removes the evidence needed to associate a later replay with its token family: an unknown token is rejected, but its family cannot be revoked through that missing record. Preserve this distinction when changing cleanup behavior.

## Backups, logs and provider data

Deleted information can remain in backups until those backups expire under the operator's policy. Restoring an older snapshot can revive deleted accounts and previously valid session records. Follow [backup and recovery](backup-and-recovery.md), including deletion/session reconciliation before reopening the restored application.

Judge diagnostics can appear in internal logs. Audit metadata filtering removes a known set of top-level sensitive keys; it is not a recursive sanitizer for arbitrary nested data. Restrict access to logs and audit storage, and define their retention at the deployment layer. See [security](security.md).

The AI adapter's request options, including OpenAI `store=false`, are not a provider retention guarantee. E2B sandbox cleanup and database deletion likewise do not establish the retention policy of external services. Verify those policies in the relevant accounts and agreements.

## Operational follow-up and verification

The operator must define any required retention periods for user history, audit records, logs, backups and provider-held data. No duration beyond credential/Redis expiry should be presented as automatically enforced by this code. Adding a scheduled purge requires a separate implementation and review of historical data, session replay detection and backup recovery behavior.

The account-deletion regression in [test_progress.py](../backend/app/tests/test_progress.py) creates dependent records and checks the deletion response, user/submission/feedback removal and preservation of the shared problem. It does not establish complete audit, provider, backup or concurrent-worker erasure coverage. See [testing](testing.md) for safe test execution and coverage limits.
