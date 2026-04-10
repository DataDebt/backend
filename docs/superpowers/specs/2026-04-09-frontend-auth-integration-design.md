# Frontend Auth Integration Design

## Summary

Integrate the existing FastAPI authentication backend in this repository with the `DataDebt/frontend` Next.js application as a separate sibling repository. This first pass will wire up only real authentication flows and will leave the frontend's mocked post-login product data in place.

The integration will support:

- Login
- Session restore on reload
- Logout
- Register
- Email confirmation
- Forgot password
- Password reset

All authenticated users will be treated as normal users. The current frontend demo admin path will be removed or disabled because the backend does not expose role information in `/api/v1/users/me`.

## Scope

### In scope

- Clone the frontend as a sibling repository next to this backend repository
- Point the frontend to the backend API running locally
- Replace the frontend's demo auth state with real backend-backed auth state
- Add frontend views or routes for register, forgot password, confirm email, and reset password
- Persist auth tokens in the frontend to support session restore
- Load the current user from `GET /api/v1/users/me`
- Refresh tokens using `POST /api/v1/auth/refresh`
- Update backend email link generation so email confirmation and password reset links land on frontend routes instead of backend API routes
- Configure backend CORS for the local frontend origin

### Out of scope

- Replacing the frontend's mocked domain, evaluation, or report data
- Adding backend role or permission support
- Introducing server-side Next.js auth proxies or cookie-based sessions
- Redesigning the backend token model

## Repositories And Local Setup

The repositories will live as siblings on disk:

- `PI2/` for the FastAPI backend
- `frontend/` for the Next.js frontend

Local development assumptions:

- Frontend origin: `http://localhost:3000`
- Backend origin: `http://localhost:8000`
- Backend API base: `http://localhost:8000/api/v1`

The frontend will read its API base URL from an environment variable such as:

- `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1`

The backend will need a frontend-facing base URL for links sent in auth emails, separate from the backend's own base URL if necessary.

## Backend API Contract

The frontend integration will use the backend endpoints already present in this repository:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/confirm-email?token=...`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/resend-verification`
- `POST /api/v1/auth/request-password-reset`
- `POST /api/v1/auth/reset-password`
- `GET /api/v1/users/me`

Expected payloads and behavior come directly from the current backend schemas and routes:

- Login returns `access_token` and `refresh_token`
- Refresh returns rotated `access_token` and `refresh_token`
- Register returns a message and sends email confirmation
- Confirm email returns a success or invalid/expired token error
- Request password reset always returns a generic success message
- Reset password returns a success or invalid/expired token error
- `/users/me` returns the authenticated user's profile

## Recommended Frontend Architecture

Use a client-managed authentication layer inside the Next.js app.

### Components

- `auth API client`
  - Small wrapper around `fetch`
  - Knows the API base URL
  - Sends JSON requests and normalizes error responses

- `auth token storage`
  - Stores `access_token` and `refresh_token` in browser storage
  - Exposes read, write, clear helpers

- `auth provider/context`
  - Owns current auth state
  - Exposes `login`, `logout`, `register`, `requestPasswordReset`, `resetPassword`, `confirmEmail`, `resendVerification`, and `loadCurrentUser`
  - Handles startup session restore
  - Handles refresh-and-retry when an access token is expired

- `auth screens/pages`
  - Login
  - Register
  - Forgot password
  - Reset password
  - Confirm email

- `app gate`
  - Shows a loading screen while the frontend determines whether an existing session is valid
  - Renders the existing user layout when authenticated
  - Renders auth screens when unauthenticated

### Why this approach

- It matches the current frontend's client-rendered structure
- It minimizes moving parts for the first integration
- It uses the backend contract as-is with only a small email-link adjustment
- It avoids adding a Next.js backend-for-frontend layer before it is needed

## Auth State Model

The frontend auth state should track:

- `status`: `loading`, `authenticated`, or `unauthenticated`
- `user`: current user object from `/users/me` or `null`
- `accessToken`: current access token or `null`
- `refreshToken`: current refresh token or `null`
- `error`: optional user-facing auth error

Startup flow:

- Read stored tokens on app load
- If no tokens exist, mark the session unauthenticated
- If tokens exist, call `/users/me` with the access token
- If `/users/me` returns unauthorized and a refresh token exists, call `/auth/refresh`
- Store the rotated tokens, then retry `/users/me`
- If refresh fails, clear tokens and mark the session unauthenticated

## User Flows

### Login

- User submits email and password
- Frontend calls `POST /auth/login`
- On success, store `access_token` and `refresh_token`
- Call `GET /users/me`
- Enter authenticated app state and show the existing user layout

### Logout

- Clear stored tokens and in-memory auth state
- Return the user to the auth entry screen

### Register

- User submits username, email, and password
- Frontend calls `POST /auth/register`
- On success, show a confirmation state instructing the user to check email
- Offer resend verification from the frontend if needed

### Email Confirmation

- Auth email links to a frontend route such as `/auth/confirm-email?token=...`
- Frontend confirm-email page reads the token from the URL
- Frontend calls `GET /auth/confirm-email?token=...`
- Show success UI with a path back to sign-in
- Show error UI if the token is invalid or expired

### Forgot Password

- User submits email on the forgot-password screen
- Frontend calls `POST /auth/request-password-reset`
- Always show the backend's generic success message

### Reset Password

- Auth email links to a frontend route such as `/auth/reset-password?token=...`
- Frontend reset-password page reads the token from the URL
- User submits a new password
- Frontend calls `POST /auth/reset-password`
- On success, send the user back to sign-in
- On failure, show invalid or expired token guidance

### Session Restore

- On app load, run the startup auth flow
- If a valid session is restored, keep the user inside the app without returning to login

## Backend Changes Required

### Email Link Targets

The backend currently builds confirmation and password reset URLs using the backend base URL and API endpoints. For the frontend flow, those links should instead target frontend routes.

Needed change:

- Add a frontend base URL setting, for example `FRONTEND_BASE_URL`
- Build auth emails with frontend routes:
  - confirmation: `${FRONTEND_BASE_URL}/auth/confirm-email?token=...`
  - password reset: `${FRONTEND_BASE_URL}/auth/reset-password?token=...`

The frontend pages will then call the backend APIs after reading the token from the URL.

### CORS

The backend must allow the frontend local origin:

- `http://localhost:3000`

If CORS middleware is not already configured, add it with an allowlist setting so the frontend can call the API from the browser during development.

## Error Handling

Frontend error mapping should preserve backend behavior while keeping messages understandable.

Expected mappings:

- `401` on login: invalid credentials
- `403` on login: account exists but email is not confirmed
- `409` on register: email or username already taken
- `400` on confirm email: invalid or expired confirmation token
- `400` on reset password: invalid or expired reset token
- `401` on `/users/me` with failed refresh: session expired, sign in again

The UI should avoid exposing implementation details and should keep generic responses where the backend intentionally does so, especially for password reset requests.

## Frontend UI Changes

Keep the frontend's visual language and post-login screens mostly intact.

Auth-area changes:

- Replace the demo login submission logic with a real API call
- Add a registration screen or toggle
- Add a forgot-password screen or toggle
- Add standalone routes for confirm-email and reset-password
- Replace the admin-or-user demo routing with authenticated-or-unauthenticated routing
- Treat all authenticated users as normal users

This keeps scope narrow while producing a fully usable auth experience.

## Security And Tradeoffs

This design stores tokens in browser-managed storage for speed of integration. That is acceptable for this first pass because:

- It fits the current frontend architecture
- It avoids a larger backend auth redesign
- It minimizes integration complexity

Tradeoffs:

- Browser storage is less secure than HttpOnly cookies
- Refresh logic must be implemented carefully to avoid stale-session loops

A later iteration can move to cookie-based auth or a proxy-backed design if the product needs stricter browser-side protections.

## Testing Strategy

### Frontend verification

- Lint and build the frontend
- Manual local checks for:
  - register
  - resend verification
  - confirm email
  - login with confirmed user
  - logout
  - forgot password
  - reset password
  - reload with valid stored session
  - reload with expired access token and valid refresh token

### Backend verification

- Confirm email links now target the frontend routes
- Confirm the frontend routes correctly call backend endpoints
- Confirm CORS allows the frontend origin
- Confirm `/users/me` loads correctly after login and after token refresh

## Implementation Notes

Suggested execution order:

- Clone the frontend repository as a sibling repo
- Add frontend env configuration for API base URL
- Add backend frontend-base-url setting and update email link generation
- Add backend CORS configuration for the frontend origin
- Add frontend auth API layer and token storage helpers
- Add frontend auth provider and startup session restore
- Replace the demo login flow
- Add register and forgot-password flows
- Add confirm-email and reset-password routes
- Remove or disable the demo admin path
- Run verification across both repos

## Open Decisions Resolved

The following decisions are fixed for this implementation:

- Use sibling repositories
- Use `http://localhost:3000` for the frontend in local development
- Treat all authenticated users as normal users
- Include login, logout, session restore, register, forgot password, and email confirmation in the first pass
- Leave non-auth product data mocked for now
