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
