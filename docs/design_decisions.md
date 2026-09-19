Phase 2 — deliver the practice loop without AI
Add a typed API client and one centralized authentication/session mechanism.

Use a centralized TypeScript API client for all backend communication. Store the short-lived access token in memory and the refresh token in an HttpOnly cookie. Maintain authentication state through a single React AuthProvider. On application startup, attempt session restoration using the refresh endpoint and load the authenticated user. Automatically attach the access token to authenticated API requests. On a 401 response, attempt one token refresh and retry the original request once; if refresh fails, clear authentication state. Provide centralized login, logout, refresh, and current-user behavior and use protected route components for authenticated pages.

Queue submissions and integrate an isolated judge for one language first (Python is the simplest starting point).

Submission Execution Design
Submissions will be processed asynchronously rather than during the API request.
POST /submissions creates a submission with QUEUED status and enqueues its ID.
Redis-backed worker queue will process submissions.
Workers retrieve the submission and test cases from PostgreSQL.
Only Python will be supported initially.
User code will execute inside an isolated, temporary Docker container rather than inside the FastAPI or worker process.
Containers will have CPU, memory, execution-time, process, filesystem, and network restrictions.
Problems will contain visible sample tests and hidden judge tests.
Submission states will include QUEUED, RUNNING, PASSED, FAILED, RUNTIME_ERROR, and TIME_LIMIT_EXCEEDED.
The frontend will initially poll GET /submissions/{id} until execution completes.
Multi-language support and real-time WebSocket updates will be deferred until after the Python MVP.

Do not expose hidden test cases or arbitrary judge internals in API responses.

Submission APIs will expose only candidate-relevant results: submission status, sanitized verdict/error message, aggregate tests passed/total, runtime, and memory usage. Hidden test inputs, expected outputs, detailed hidden-test results, execution infrastructure details, stack traces, container information, commands, internal paths, and raw judge errors will never be included in candidate-facing responses. User-generated compilation/runtime errors may be returned after sanitization. Internal judge results and public API response schemas will be modeled separately to prevent accidental leakage. Detailed diagnostics will remain in server-side logs, with any future admin diagnostics protected by server-side authorization.

Phase 3 — add one focused AI feature
Generate feedback only after deterministic judge results exist.
The deterministic judge is the sole source of truth for submission correctness. AI feedback will only be generated after the judge has completed and its results have been persisted. The feedback generator will receive the problem, submitted code, and a sanitized representation of the judge result without exposing hidden test cases or judge internals. Judge and feedback statuses will be tracked separately so AI failure cannot invalidate a completed judge result. Feedback generation should eventually run asynchronously, allowing judge results to be returned immediately while feedback is generated separately. AI feedback will provide coaching and explanations but will never determine or modify the submission verdict. Ai coaching should follow these policies: First feedback:
diagnose category of problem
→ no solution

Second hint:
point toward approach

Explicit "Show solution":
allow detailed solution

Send the problem, user code, and sanitized test summary to the model; do not send secrets or hidden expected outputs.

Create a dedicated FeedbackContext as an allowlisted data contract for AI feedback generation. It will contain only the problem statement/constraints/public examples, programming language, submitted code, verdict, aggregate test results, and safe performance/error information. Hidden test inputs, hidden expected outputs, raw judge results, infrastructure details, user identity/session information, credentials, environment variables, API keys, tokens, and other secrets will never be included. Hidden tests will be represented only through sanitized aggregate results. The context will be explicitly constructed from approved fields rather than passing internal objects to the model and attempting to remove sensitive fields afterward.


Require structured output with strengths, likely issue, hint, complexity, and next step. Validate it before saving.

AI feedback will use a predefined structured schema containing strengths, likely_issue, hint, complexity (time and space), and next_step. likely_issue and hint may be null when no meaningful issue exists, such as for an accepted solution. The model response will be validated against a Pydantic schema before persistence, with reasonable field lengths and list limits. Invalid responses will not be stored; the system may retry generation once before marking feedback as failed. Feedback failure will remain independent from the deterministic judge result. Valid feedback will be stored as structured data rather than pre-rendered Markdown/text so presentation remains the responsibility of the frontend.

Add prompt/version/model metadata, timeouts, retries, rate limits, cost tracking, and a non-AI fallback

AI feedback will be treated as an external, fallible dependency. Each generated feedback record will include model, prompt version, schema version, and generation metadata for traceability. AI calls will have an explicit timeout and bounded retries with backoff only for transient failures; permanent errors will not be retried. Application-level rate limits and duplicate-generation protection will prevent abuse and uncontrolled API spending. Token usage and estimated cost will be recorded for monitoring and budgeting. If AI generation remains unavailable, the system will fall back to deterministic guidance derived from the judge verdict rather than failing the submission. AI-specific configuration and reliability logic will be centralized in a feedback service rather than scattered across API routes.

Evaluate feedback on a small fixed dataset before enabling it broadly.

LLM behavior is nondeterministic and can change when the prompt, model, parameters, or surrounding pipeline changes. The fixed feedback regression suite in `backend/app/feedback/evaluation.py` covers diagnosis, hint, and solution stages across passed, failed, and runtime-error submissions. It validates the structured schema, stage-specific restrictions, and forbidden-content rules.

Run it before rollout:

	PYTHONPATH=backend python -m app.scripts.evaluate_feedback --report feedback-evaluation-report.json

Review the report and enable AI only when every case passes by setting `FEEDBACK_AI_ENABLED=true` and `FEEDBACK_EVALUATION_PASSED=true`. Rerun the suite whenever the model, prompt version, parameters, or feedback pipeline changes; keep AI disabled when the suite fails so deterministic fallback guidance remains active.



Implement the following production-readiness improvements for the AI Technical Interview Prep Platform.

IMPORTANT:
Before changing any code:
1. Inspect the existing repository structure, backend architecture, frontend architecture, database models, authentication/session implementation, submission lifecycle, Docker configuration, and existing tests.
2. Reuse existing abstractions and conventions wherever possible.
3. Do not rewrite working architecture simply to fit these requirements.
4. Do not introduce infrastructure unless it solves an actual requirement.
5. If an implementation choice conflicts with the existing architecture, explain the conflict and choose the least disruptive solution.
6. Keep changes modular and production-oriented.
7. Add/update tests for important behavior.
8. Update documentation for new configuration/environment variables.
9. Do not put secrets, passwords, JWTs, refresh tokens, API keys, or other sensitive values into logs/audit records.

Implement the following.

==================================================
1. USER PROGRESS SUMMARIES
==================================================

Add a progress-summary capability based on persisted submission data.

Expose an authenticated endpoint similar to:

GET /api/v1/users/me/progress

Return useful metrics where supported by the current schema, including:
- total problems attempted
- total problems solved
- overall success/solve rate
- breakdown by difficulty
- breakdown by problem category/pattern if categories exist
- recent activity/progress if timestamps support it

Design requirements:
- Calculate statistics from PostgreSQL on demand for the MVP.
- Do NOT introduce materialized views, background aggregation jobs, or Redis caching unless the existing architecture clearly requires them.
- Avoid N+1 queries.
- Keep aggregation/query logic out of the API router and in the appropriate service/repository layer.
- Ensure users can access only their own statistics.
- Handle users with no submissions cleanly.
- Add tests for aggregation logic and authorization.

Add a simple frontend progress/dashboard view if an appropriate dashboard/profile surface already exists.

==================================================
2. ACCESSIBILITY + RESPONSIVE UI
==================================================

Review the React frontend and improve accessibility and responsive behavior.

Requirements:
- Use semantic HTML wherever practical.
- All form controls must have accessible labels.
- Interactive elements must be keyboard accessible.
- Provide visible focus states.
- Do not communicate submission success/failure solely through color.
- Provide text such as "Passed" and "Failed".
- Add appropriate ARIA attributes only where semantic HTML is insufficient.
- Loading/error/status changes should be understandable to assistive technology.
- Images/icons that convey information need accessible text.
- Decorative images/icons should not create unnecessary screen-reader noise.

Responsive behavior:
- Desktop layouts may use multi-column layouts.
- On smaller screens, problem description, editor, results, and feedback should stack/reflow appropriately.
- Avoid horizontal page overflow.
- Ensure navigation, authentication forms, problem lists, editor controls, and result displays remain usable on smaller screens.

Do not claim formal WCAG compliance. Implement strong accessibility fundamentals.

==================================================
3. EXPLICIT LOADING + ERROR STATES
==================================================

Review asynchronous frontend/backend workflows, especially submissions.

Model submission lifecycle explicitly using the existing architecture. Use states equivalent to:

QUEUED
RUNNING
JUDGING
GENERATING_FEEDBACK
COMPLETED
FAILED

Only add states that actually correspond to the current workflow.

Frontend requirements:
- Show meaningful loading/progress states.
- Prevent accidental duplicate submission while an identical submission request is already being initiated where appropriate.
- Handle network errors.
- Handle authentication expiration.
- Handle 429 responses.
- Handle judge failures.
- Handle AI-feedback failures separately from deterministic judge failures.
- Handle generic server failures.

IMPORTANT:
AI feedback must not be required for deterministic judge results.

If judging succeeds but AI feedback fails, still return/display the deterministic result and show a message such as:

"AI feedback is temporarily unavailable."

Do not expose stack traces, internal exception details, secrets, hidden test cases, or judge internals to the frontend.

Use existing global error-handling/API-client mechanisms rather than duplicating error handling throughout components.

==================================================
4. RATE LIMITING
==================================================

Add rate limiting to abuse-sensitive and/or expensive endpoints.

At minimum evaluate:
- login
- registration if appropriate
- email verification resend
- submission creation
- AI feedback generation

Do NOT necessarily apply the same limit to every endpoint.

Choose reasonable development/MVP defaults and make important limits configurable through environment/config settings.

Identity strategy:
- authenticated expensive operations: primarily user ID
- unauthenticated auth endpoints: IP-based or an appropriate combination
- avoid trusting arbitrary client-supplied identity headers

Use Redis-backed rate limiting if Redis is already part of or being integrated into the architecture. If Redis is unavailable in the current implementation and adding it would significantly expand scope, implement the cleanest abstraction that allows Redis-backed limiting later and document the tradeoff.

Return:

HTTP 429 Too Many Requests

Provide a safe client-facing error response.

If practical, include appropriate retry information.

Add tests proving:
- requests under the limit succeed
- requests exceeding the limit return 429
- one user's limit does not incorrectly affect another authenticated user

==================================================
5. AUDIT EVENTS
==================================================

Introduce structured audit events for security-sensitive and privileged actions.

Audit events should be distinct from ordinary application/debug logs.

Support events where applicable such as:

USER_REGISTERED
LOGIN_SUCCESS
LOGIN_FAILED
EMAIL_VERIFIED
PASSWORD_CHANGED
REFRESH_TOKEN_ROTATED
SESSION_REVOKED
SUBMISSION_CREATED
PROBLEM_CREATED
PROBLEM_UPDATED
PROBLEM_DELETED
ADMIN_ROLE_GRANTED

Do not invent workflows that don't exist yet.

Audit record fields should include only useful metadata, for example:
- event type
- timestamp
- actor/user ID when available
- target resource ID when relevant
- request/correlation ID if the application already supports one
- limited request metadata such as IP only if justified

NEVER record:
- plaintext passwords
- password hashes
- JWTs
- refresh tokens
- verification tokens
- API keys
- authorization headers
- secrets
- hidden test contents
- unnecessary user code

Design audit events so they can later be queried/investigated.

Prefer an append-oriented audit model.

Add tests confirming important events are created and sensitive values are not stored.

==================================================
6. DATABASE BACKUP + RECOVERY DOCUMENTATION
==================================================

Do NOT build a custom backup service unless absolutely necessary.

The production PostgreSQL deployment should rely on managed-provider backup functionality where available.

Add operational documentation covering:
- what data must be backed up
- expected backup frequency
- retention period
- restore procedure
- how restore verification should be performed
- RPO
- RTO

For the MVP, recommend/document sensible targets rather than pretending stronger guarantees exist.

Redis should NOT require backup if it contains only disposable cache/rate-limit state. If Redis currently stores durable business-critical state, identify that architectural problem.

Create documentation such as:

docs/backup-and-recovery.md

Do not include production credentials or secrets.

==================================================
7. DATA RETENTION + ACCOUNT DELETION
==================================================

Review all persisted user-related data.

Document and implement a basic retention strategy for:
- user accounts
- submissions
- AI feedback
- refresh/session tokens
- verification/reset tokens if present
- audit events

Implement or improve account deletion if appropriate.

Account deletion must:
- require authentication
- revoke active sessions/tokens
- handle dependent database records intentionally
- delete or anonymize personal data according to clearly documented rules
- avoid leaving broken foreign-key references
- not accidentally delete shared/global problem data

Decide explicitly whether submission history is deleted or anonymized.

Expired/revoked temporary authentication records should not be retained forever. Implement a cleanup strategy appropriate to the existing architecture.

Document that deleted information may remain temporarily in backup snapshots until those backups expire according to the backup-retention policy.

Do not implement arbitrary retention periods without documenting them centrally/configurably where appropriate.

==================================================
8. TESTING
==================================================

Add tests for the important behavior introduced above.

Prioritize:
- progress aggregation
- authorization
- rate limiting
- audit event creation
- account deletion/data handling
- submission state transitions
- graceful handling of AI failure
- sensitive-data exclusion

Use the project's existing testing conventions.

Do not write meaningless tests purely to increase coverage.

==================================================
9. OBSERVABILITY / ERROR HANDLING
==================================================

Where these changes introduce new failure modes:

- use structured logging consistent with the existing project
- avoid logging secrets
- distinguish expected operational failures from unexpected exceptions
- preserve useful server-side diagnostic context
- expose only sanitized errors to clients

If correlation/request IDs already exist, propagate them.
If they do not exist, do not introduce a large observability subsystem solely for this task.

==================================================
10. DOCUMENTATION
==================================================

Update the README and/or docs to accurately describe what is ACTUALLY implemented.

Do not describe planned features as completed.

Document:
- progress-summary endpoint
- submission states
- rate-limiting behavior
- audit-event strategy
- backup/recovery strategy
- data-retention/account-deletion behavior
- new environment variables
- relevant architectural decisions

==================================================
IMPLEMENTATION PROCESS
==================================================

Work incrementally.

First:
1. Inspect the repository.
2. Give me a concise implementation plan showing:
   - existing components you found
   - files/modules likely to change
   - database migrations required
   - new dependencies, if any
   - important architectural decisions
   - anything already implemented that should be reused
   - anything from these requirements that does NOT make sense for the current application

Then implement the work in logical phases.

Suggested phases:

Phase 1:
Progress summaries + submission/loading/error states

Phase 2:
Rate limiting

Phase 3:
Audit events

Phase 4:
Account deletion + retention controls

Phase 5:
Accessibility/responsive improvements

Phase 6:
Backup/recovery documentation + final docs

After each phase:
- run relevant tests
- fix failures caused by the changes
- summarize what changed

Do not silently change unrelated application behavior.

==================================================
FINAL ACCEPTANCE CRITERIA
==================================================

The work is complete when:

1. Authenticated users can retrieve meaningful progress statistics.
2. The frontend handles loading, success, partial failure, and error states clearly.
3. AI-feedback failure does not destroy a successful deterministic judge result.
4. Abuse-sensitive endpoints are rate limited.
5. Security-sensitive/privileged actions generate safe audit events.
6. No secrets/tokens/passwords are stored in audit events or exposed to clients.
7. Core UI works reasonably across desktop and smaller screens.
8. Basic keyboard/accessibility behavior is supported.
9. Account deletion and data-retention behavior are explicitly defined and implemented.
10. PostgreSQL backup/recovery procedures are documented.
11. Important new behavior has meaningful tests.
12. Existing tests still pass.
13. Documentation reflects the actual implementation.
14. The application remains runnable through the project's existing local/Docker workflow.

Most importantly: favor simple, defensible MVP implementations over unnecessary enterprise complexity. If a requirement would substantially overengineer the current application, explain why and implement the smallest architecture that leaves a clean upgrade path.