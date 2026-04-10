# FastAPI + Neon Auth Redesign

**Date:** 2026-04-09

## Goal

Redesign the current single-file Flask auth platform into a production-oriented FastAPI service backed by Neon PostgreSQL. The new system should preserve the existing core user journey while expanding the auth baseline to include refresh tokens, password reset, stronger structure, typed configuration, async database access, and cleaner boundaries between API, business logic, persistence, and infrastructure concerns.

## Current State Summary

The existing project is a small monolith centered in `app.py` with supporting modules for DB access, password hashing, config loading, and email sending. It currently:

- Uses Flask as the web framework.
- Connects to PostgreSQL directly through `psycopg2`.
- Stores most auth state directly on the `users` table.
- Sends email synchronously, with fallback to local file capture.
- Uses custom password hashing helpers and JWT issuance.
- Relies on a script-style integration test instead of a modern test suite.

This makes the project easy to understand, but it couples transport, business rules, persistence, and infrastructure tightly enough that extending auth features will become increasingly awkward.

## Design Principles

- Keep the project small enough to understand quickly.
- Move to an API-first service rather than a page-first app.
- Use async request handling end-to-end where I/O is involved.
- Model auth concerns as first-class records instead of overloading the `users` row.
- Prefer explicit structure over framework magic.
- Keep email delivery simple inside the app by using FastAPI background tasks rather than introducing a queue now.
- Make local development ergonomic while keeping the deployment path to Neon straightforward.

## Recommended Architecture

The redesigned project will use a layered modular service architecture:

- **API layer**: FastAPI routers define HTTP endpoints, dependency injection, status codes, and response contracts.
- **Schema layer**: Pydantic models validate requests and shape responses.
- **Service layer**: business logic for registration, email confirmation, login, refresh token rotation, password reset, and current-user retrieval.
- **Repository layer**: database operations grouped by aggregate concern (`users`, `tokens`, `sessions`).
- **Persistence layer**: SQLAlchemy ORM models and async session management against Neon PostgreSQL.
- **Infrastructure layer**: settings, security primitives, JWT utilities, password hashing, email providers, and background task wiring.

Request flow:

`client -> FastAPI router -> service -> repository -> SQLAlchemy async session -> Neon PostgreSQL`

Email flow:

`service schedules background task -> email provider sends SMTP or writes dev capture -> service returns response immediately`

This keeps controllers thin, keeps business rules reusable, and avoids embedding SQL and auth policy inside route functions.

## Proposed Project Structure

The target structure should look roughly like this:

```text
project/
├── app/
│   ├── api/
│   │   ├── deps.py
│   │   ├── router.py
│   │   └── routes/
│   │       ├── auth.py
│   │       ├── users.py
│   │       └── health.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── security.py
│   │   └── tokens.py
│   ├── models/
│   │   ├── base.py
│   │   ├── user.py
│   │   ├── email_verification_token.py
│   │   ├── refresh_token.py
│   │   └── password_reset_token.py
│   ├── repositories/
│   │   ├── users.py
│   │   ├── email_verifications.py
│   │   ├── refresh_tokens.py
│   │   └── password_resets.py
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── users.py
│   │   └── common.py
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── token_service.py
│   │   └── email_service.py
│   ├── main.py
│   └── __init__.py
├── alembic/
├── tests/
│   ├── integration/
│   └── unit/
├── emails/
├── .env.example
├── pyproject.toml
└── README.md
```

The current `app.py`, `db.py`, `config.py`, `password_utils.py`, and `email_service.py` responsibilities should be decomposed into the modules above rather than copied forward intact.

## Technology Stack

- **Framework:** FastAPI
- **ASGI server:** Uvicorn
- **Database platform:** Neon (hosted PostgreSQL)
- **ORM / data access:** SQLAlchemy ORM with async engine
- **PostgreSQL driver:** `asyncpg`
- **Migrations:** Alembic
- **Validation / serialization:** Pydantic
- **Typed settings:** `pydantic-settings`
- **JWT handling:** `python-jose` or `PyJWT` (prefer one consistently; `python-jose` is a common FastAPI pairing)
- **Password hashing:** `passlib` with `bcrypt` or `argon2` (prefer `argon2` if compatible with deployment environment)
- **Email transport:** standard SMTP integration with dev fallback capture
- **Testing:** `pytest`, `pytest-asyncio`, `httpx`

## Database Design

Neon remains PostgreSQL, so the domain can be modeled cleanly with normalized auth tables.

### `users`

Core identity record:

- `id` UUID primary key
- `email` unique, normalized
- `username` unique
- `password_hash`
- `is_active`
- `is_verified`
- `created_at`
- `updated_at`
- `last_login_at`

### `email_verification_tokens`

Verification records separated from the user:

- `id` UUID primary key
- `user_id` foreign key
- `token_hash`
- `expires_at`
- `consumed_at`
- `created_at`

### `refresh_tokens`

Session-oriented refresh token storage:

- `id` UUID primary key
- `user_id` foreign key
- `token_hash`
- `expires_at`
- `revoked_at`
- `created_at`
- optional `user_agent` and `ip_address` if session auditing becomes useful

### `password_reset_tokens`

Password reset workflow support:

- `id` UUID primary key
- `user_id` foreign key
- `token_hash`
- `expires_at`
- `consumed_at`
- `created_at`

## Token Strategy

The redesigned app should distinguish between token types:

- **Access token**: short-lived JWT for API authentication
- **Refresh token**: opaque random token stored hashed in the database
- **Email verification token**: opaque random token stored hashed in the database
- **Password reset token**: opaque random token stored hashed in the database

JWTs should carry only what the API needs, such as:

- `sub` user id
- `username`
- `type=access`
- expiration timestamp

Refresh, verification, and reset tokens should be opaque values generated with secure randomness and only stored as hashes in the database. This avoids treating the database as a source of reusable secret tokens and reduces damage if records are exposed.

## API Surface

The new API should include the following endpoints:

### Authentication

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/resend-verification`
- `GET /api/v1/auth/confirm-email`
- `POST /api/v1/auth/request-password-reset`
- `POST /api/v1/auth/reset-password`

### User

- `GET /api/v1/users/me`

### Operational

- `GET /api/v1/health`

### Optional / Dev-only

- `GET /api/v1/dev/emails`
- `GET /api/v1/dev/users`

The current `/api/users` and `/api/emails` endpoints should be reclassified as development or admin utilities rather than core public API.

## Auth and Security Behavior

### Registration

- Validate username, email, and password with typed schema validation.
- Hash the password before persistence.
- Create the user as unverified.
- Generate a verification token record.
- Schedule confirmation email delivery in a background task.
- Return a success response that does not expose raw token values.

### Email Confirmation

- Receive opaque token from the client.
- Hash and match against active verification token records.
- Fail cleanly on invalid, expired, or consumed tokens.
- Mark the user as verified.
- Mark the verification token as consumed.

### Login

- Validate credentials.
- Reject inactive accounts.
- Reject unverified accounts.
- Issue short-lived access token.
- Issue refresh token and persist only its hash.
- Update `last_login_at`.

### Refresh

- Accept refresh token.
- Validate hash match, expiry, and revocation.
- Rotate refresh token on success.
- Return new access token and refresh token pair.

### Password Reset

- Accept email address and respond generically whether or not the user exists.
- For existing users, generate a reset token record and send email in the background.
- On reset confirmation, validate token, hash new password, consume token, and revoke active refresh tokens if desired.

### Password Hashing

Replace the custom PBKDF2 helper with a mature password hashing library. `argon2` is preferred for a modern auth service unless there is a platform compatibility reason to choose `bcrypt`.

## FastAPI Design

### Routing

Routers should be grouped by concern and mounted under `/api/v1`.

### Dependencies

Use dependency injection for:

- async DB sessions
- current authenticated user
- settings access where needed

### Validation

Request and response contracts should be declared with Pydantic schemas instead of ad hoc JSON parsing and string cleanup.

### Error Handling

Define a consistent error strategy:

- 400 for invalid request shapes when semantically appropriate
- 401 for authentication failures
- 403 for valid identity lacking required state, such as unverified account
- 404 where a resource-oriented read genuinely does not exist
- 409 for uniqueness conflicts
- 422 for schema validation failures handled by FastAPI/Pydantic

Domain-specific exceptions from services should be translated into HTTP errors in one place rather than sprinkled throughout the codebase.

## Neon Integration

Neon should be used as the primary PostgreSQL backend via its standard connection string stored in environment configuration.

Design implications:

- Use SQLAlchemy async engine with connection pooling settings appropriate for server-based execution.
- Keep the connection string environment-driven and do not hardcode local database defaults that imply SQLite or local PostgreSQL.
- Make the app start even when the DB is unavailable only if operationally necessary; otherwise fail fast during startup checks.
- Use Alembic for all schema creation and evolution instead of `init_db()` schema execution at import time.

To keep the database layer from depending on unrelated auth secrets, the DB engine/session setup may resolve only `DATABASE_URL` and DB-relevant debug behavior lazily at first use, rather than importing a fully-instantiated application settings object at module import time.

The current pattern of creating schema on app import must be removed.

## Email Delivery Design

The user chose to keep email handling simple inside the app.

That means:

- business logic prepares email intent
- the API/service schedules a FastAPI background task
- the email provider sends through SMTP when configured
- development mode can save email payloads locally to the `emails/` directory for inspection

This preserves the current friendly dev workflow while decoupling email from request latency enough for a modern app.

## Configuration Design

Replace the handwritten `.env` loader with typed settings built on Pydantic settings.

Settings should cover:

- app name
- environment
- debug flag
- API prefix
- secret keys
- access token lifetime
- refresh token lifetime
- Neon database URL
- SMTP host, port, username, password, sender, TLS mode
- optional dev email capture toggle

Also add an `.env.example` to document required variables. The repo currently has an `env` file rather than `.env`; the redesign should standardize this.

To avoid import-time crashes in tests, migrations, and partial module imports, the public `settings` interface may be implemented lazily under the hood. Callers should still be able to import `settings` from the config module, but configuration resolution should happen on first access rather than at module import time.

## Testing Strategy

Testing should move from the current single script to a layered test suite.

### Unit Tests

Cover:

- password hashing helpers
- token generation and verification logic
- service-level auth rules
- repository query behavior where practical

### Integration Tests

Cover:

- register -> confirm email -> login
- duplicate email/username
- login blocked before verification
- refresh token rotation
- password reset request and completion
- current-user endpoint with valid and invalid JWTs

### Test Tooling

- `pytest`
- `pytest-asyncio`
- `httpx.AsyncClient`
- isolated test database configuration

## Migration Strategy

This redesign is large enough that it should be implemented as a controlled migration, not a line-by-line rewrite of `app.py`.

Recommended migration phases:

1. Scaffold FastAPI app structure and configuration.
2. Establish Neon connection, SQLAlchemy base, and Alembic.
3. Model and migrate the new auth tables.
4. Implement auth services and repositories.
5. Add FastAPI routes and schemas.
6. Port email capture behavior into the new service design.
7. Add tests around registration, verification, login, refresh, and reset flows.
8. Retire the old Flask entrypoint once feature parity and tests are in place.

## Out of Scope

To keep the redesign focused, the following are not part of the initial implementation unless later requested:

- external job queues
- OAuth / social login
- MFA / TOTP / WebAuthn
- RBAC beyond a role-ready user model
- frontend SPA or separate web client
- audit log subsystem

## Risks and Trade-offs

- Async SQLAlchemy introduces more complexity than sync SQLAlchemy, but it aligns better with the chosen modernized FastAPI architecture.
- Token tables increase schema complexity, but they make refresh and reset flows much cleaner and safer than embedding everything on the user row.
- Keeping email inside the app is operationally simpler now, but less robust than a dedicated queue for heavy production scale.
- Moving to a migration-driven database lifecycle adds setup cost, but it removes fragile runtime schema bootstrapping.

## Success Criteria

The redesign is successful when:

- the app runs as a FastAPI service rather than Flask
- Neon is the authoritative database backend
- database schema is managed by Alembic
- auth features include register, verify, login, refresh, password reset, current user, and health check
- email sending is non-blocking from the request path via background tasks
- tests cover the core auth flows
- responsibilities are split into focused modules rather than concentrated in one file

## Recommendation

Proceed with the layered FastAPI service redesign using Neon, SQLAlchemy async ORM, Alembic, typed settings, background email tasks, and a token-table-based auth model. This is the best fit for the requested “full modernized” scope without prematurely introducing queueing infrastructure or unrelated subsystems.
