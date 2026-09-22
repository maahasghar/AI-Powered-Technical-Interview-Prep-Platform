# Interview Prep frontend

From `frontend`, run `npm install` and `npm start`. The API defaults to
`http://localhost:8000/api/v1`. Copy `.env.example` to `.env` to configure
`REACT_APP_API_URL`; restart the development server after changing it.
The backend CORS configuration must allow the frontend origin.

Docker Compose keeps frontend dependencies in a separate `/app/node_modules`
volume. After dependency changes, synchronize the running container from the
repository root:

```sh
docker compose exec frontend npm ci
docker compose restart frontend
```

Installing packages on the host does not update this container volume.

| Route                                           | Purpose                                                                |
| ----------------------------------------------- | ---------------------------------------------------------------------- |
| `/login`, `/register`                           | Sign in and register                                                   |
| `/forgot-password`, `/reset-password?token=…`   | Password recovery                                                      |
| `/verify-email?token=…`, `/resend-verification` | Email verification                                                     |
| `/problems`                                     | Authenticated browsing with category/difficulty filters and pagination |
| `/problems/:problemId`                          | Problem brief and code editor                                          |
| `/problems/:problemId/editor`                   | Direct editor link                                                     |
| `/submissions/:submissionId`                    | Saved code, status, and available result                               |
| `/history`                                      | Paginated submission history                                           |
| `/progress`                                     | Attempted, solved, and recent activity summary                         |

Protected routes wait for `AuthProvider` to restore the session through
`POST /auth/refresh` and load `GET /users/me` before deciding whether to redirect.
The centralized TypeScript client (`src/api.ts`) keeps the 15-minute access token
in memory. Login and refresh return only the access token; the backend stores the
rotating 30-day refresh token in an HttpOnly cookie scoped to `/api/v1/auth`.
No new tokens are written to browser storage; legacy sessionStorage credentials
are removed on startup.

All backend requests use the client and include cookie credentials. Authenticated
requests attach the access token and, on a 401, share one refresh and retry once.
Refresh failure or a second 401 clears local authentication. Login, logout, and
refresh cookie mutations are serialized within the tab and, where Web Locks are
available, across tabs. Logout clears local state
immediately and asks the backend to revoke the refresh family and delete its cookie.
If the server cannot be reached, revocation and cookie deletion cannot be confirmed;
the UI reports the failure, and a later reload may restore the cookie session.

Cookie session endpoints require `X-Session-Request: 1` and reject untrusted Origin
headers. Set `CORS_ORIGINS` to explicit frontend origins (never `*` with credentials).
Cookies use `SameSite=Lax` and `Secure` whenever backend `ENV` is not `dev`.
Use HTTPS in production and deploy frontend and API on the same site (for example,
`app.example.com` and `api.example.com`). Unrelated frontend/API sites are not
supported by this cookie configuration. Local development uses `localhost` for
both services and `ENV=dev`. Cookies are shared by browser tabs; access tokens and
UI state are per tab. Web Locks coordinate cookie mutations across tabs on
supported browsers; without Web Locks, simultaneous refreshes in separate tabs
can invalidate a rotating refresh family. Login/logout UI notifications across
tabs are not implemented.

Registration requires email verification before login.

The editor accepts Python 3.11 solutions implementing `solve(...)`. Submissions
are queued for an isolated Docker judge and the result page polls automatically
until evaluation finishes. Sample tests are visible; hidden judge tests are never
returned by the API. See [submission execution](../docs/submission_execution.md)
for the solution contract, limits, and worker setup. Archived problems cannot
accept new submissions, while saved submission code remains readable.

Run `CI=true npm test -- --watchAll=false --runInBand` for route/API tests,
`npm run test:e2e` for the Chromium browser journey, `npm run typecheck` for
client contract checks, and `npm run build` for a production bundle. Install
the browser first with `npx playwright install chromium`. Production hosting must serve `index.html`
for non-API paths so direct links and browser refresh work with BrowserRouter.

For production, build `frontend/Dockerfile.production`; it serves the compiled
React app through Nginx and exposes `/healthz`. See the
[production deployment runbook](../docs/production-deployment.md).
Routing uses [React Router's declarative routes](https://reactrouter.com/docs/en/v6/start/concepts).

Submission results use a typed object containing a safe message, aggregate test
counts, runtime in milliseconds, and sampled memory in bytes. The result view
renders those fields explicitly; it does not dump arbitrary judge JSON. Missing
measurements are shown as Unavailable.
