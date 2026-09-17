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
