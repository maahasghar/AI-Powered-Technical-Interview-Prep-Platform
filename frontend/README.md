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

Protected links return to their destination after sign-in. Access and refresh tokens
are stored in sessionStorage for the current tab, with one shared refresh request
when API calls encounter an expired access token. Signing out revokes the refresh
session through the backend. Registration requires email verification before login.

The editor submits code to the existing API; it does not execute code in the browser.
The backend currently saves attempts as pending. The result page displays the actual
backend status and offers manual refresh. Admin history follows the existing API's
behavior and includes all users' submissions. Archived problem links may return 404
for regular users, while their saved submission code remains readable.

Run `CI=true npm test -- --watchAll=false --runInBand` for route/API tests and
`npm run build` for a production bundle. Production hosting must serve `index.html`
for non-API paths so direct links and browser refresh work with BrowserRouter.
Routing uses [React Router's declarative routes](https://reactrouter.com/docs/en/v6/start/concepts).
