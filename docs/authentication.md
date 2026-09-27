# Authentication and Sessions

Sources: [auth router](../backend/app/api/v1/routers/auth_router.py), [AuthService](../backend/app/domain/auth/service.py), [AuthRepository](../backend/app/domain/auth/repository.py), [security utilities](../backend/app/core/security.py), [typed API client](../frontend/src/api.ts) and [AuthProvider](../frontend/src/auth.js).

## Login

```mermaid
sequenceDiagram
    actor User
    participant Web as AuthProvider / api.ts
    participant API as AuthService
    participant DB as PostgreSQL
    User->>Web: Email and password
    Web->>Web: Clear previous in-memory session
    Web->>API: POST /api/v1/auth/login with X-Session-Request
    API->>DB: Load user and verify bcrypt hash
    Note over API: Reject unverified email
    API->>DB: Store hashed refresh token and family_id
    API-->>Web: Access JWT and HttpOnly refresh cookie
    Web->>Web: Store access token in memory
    Web->>API: GET /api/v1/users/me with Bearer token
    API-->>Web: Current user
    Web-->>User: Requested protected route or /problems
```

Access JWTs use HS256 and expire after 15 minutes by default. Refresh JWTs have a 30-day lifetime, `token_type`, `family_id` and `jti`; PostgreSQL `auth_tokens` stores SHA-256 hashes, not raw refresh credentials. Login requires email verification and removes expired/revoked token records before issuing a new family.

Registration creates an unverified account. Verification tokens are random, hashed in `account_tokens`, single-use and valid for 24 hours. Password-reset tokens use the same table with a 30-minute lifetime. Reset revokes the user's refresh sessions. Email delivery uses `EmailClient`; console mode does not print a usable verification link.

## Application Startup and Session Restoration

```mermaid
sequenceDiagram
    participant App as AuthProvider
    participant Client as api.ts
    participant API as FastAPI
    App->>Client: restoreSession
    Note over Client: Remove legacy sessionStorage entry
    Client->>API: POST /api/v1/auth/refresh with cookie
    alt Valid refresh session
        API-->>Client: Access JWT and rotated refresh cookie
        Client->>API: GET /api/v1/users/me
        API-->>Client: User
        Client-->>App: Publish authenticated user
    else Missing, expired or invalid session
        API-->>Client: 401 and delete refresh cookie
        Client-->>App: Clear in-memory authentication
    end
    Note over App: Finish loading and resolve protected routes
```

The public `/` landing page remains available during restoration. `ProtectedRoute` waits for loading to finish, then renders its outlet or redirects to `/login`, preserving pathname and query for return after login. Registration, login, verification and password routes are public. Problems, editor, submission results, history and progress are protected in the client and independently authorized by the API.

## Expired Access Token / Refresh Flow

```mermaid
sequenceDiagram
    participant Page as React page
    participant Client as api.ts
    participant API as FastAPI
    participant DB as auth_tokens
    Page->>Client: Authenticated request
    Client->>API: Request with access JWT
    API-->>Client: 401
    Client->>API: POST /api/v1/auth/refresh with cookie
    API->>DB: Validate hash, family, expiry and revocation
    alt Refresh valid
        API->>DB: Revoke old token and save replacement
        API-->>Client: New access JWT and refresh cookie
        Client->>API: Retry original request once
        API-->>Client: Response
        Client-->>Page: Result or error
    else Refresh fails
        API-->>Client: Failure
        Client->>Client: Clear authentication
        Client-->>Page: Error
    end
```

`api()` makes at most one refresh attempt and one retry for an authenticated request. If another request already refreshed the access token, it reuses that token. A repeated 401 clears state. Non-401 errors and explicitly unauthenticated requests do not initiate refresh.

Concurrent refreshes within a client share a promise. Login, logout and refresh cookie mutations are serialized; Web Locks coordinate tabs where supported, with a per-instance promise queue as fallback. A generation counter prevents late responses from reviving cleared sessions. These controls do not imply server-side atomic rotation: repository rotation is not a compare-and-swap/row-lock operation.

`AuthService` revokes a family on reuse of a revoked token that is still present. Login cleanup deletes revoked rows, so family-wide reuse detection cannot be claimed after that record has been removed.

## Logout and Revocation

```mermaid
sequenceDiagram
    actor User
    participant Web as api.ts
    participant API as FastAPI
    participant DB as auth_tokens
    User->>Web: Sign out
    Web->>Web: Clear user and access JWT immediately
    Web->>API: POST /api/v1/auth/logout with cookie
    API->>DB: Revoke matching refresh-token family if valid
    API-->>Web: Delete cookie and success response
```

Logout tolerates a missing/invalid refresh token. If the request cannot reach the server, local state is cleared but server revocation and cookie deletion are not confirmed; the UI surfaces the error. Revocation does not blacklist an already issued access JWT: it can remain valid until expiry while its user exists. Account deletion removes the user and dependent authentication records.

## Why Use an HttpOnly Refresh Cookie?

A reload should restore a session without persisting a long-lived credential in browser-accessible storage. The refresh credential is set by the API and unavailable through ordinary JavaScript cookie access; the short-lived access token and current user remain module variables in `api.ts`. Neither new token is placed in localStorage or sessionStorage.

Actual cookie configuration:

| Attribute | Implementation |
|---|---|
| Name/path | `refresh_token`, `/api/v1/auth` |
| HttpOnly | Always enabled |
| Secure | Enabled when `ENV != "dev"` |
| SameSite | `lax` |
| Lifetime | `max_age` of 30 days; refresh rotation resets lifetime |
| Domain | Not set explicitly (host-scoped) |

Login, refresh and logout require `X-Session-Request: 1` and reject a supplied Origin outside `CORS_ORIGINS`. Credentialed CORS and `fetch(..., credentials: "include")` support cookie transport. Missing Origin is accepted if the custom header is present. This is custom-header/origin CSRF protection, not a synchronizer-token implementation.

The trade-off is startup network traffic, rotation coordination and cookie/origin deployment constraints. `SameSite=lax` means arbitrary cross-site frontend/API deployments may not carry the cookie even when CORS permits them; verify the actual domains. HttpOnly limits credential extraction but does not prevent injected same-origin JavaScript from making authenticated requests or reading in-memory access tokens.

Centralizing this behavior keeps pages from duplicating retry loops and accidentally storing tokens. Reconsider the session design if cross-site embedding or concurrent-client requirements exceed the current cookie/rotation contract; preserve centralized ownership and explicit revocation semantics when doing so. See [security](security.md).
