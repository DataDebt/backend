# 🔐 Auth Platform

A modern user authentication system with email verification and password reset, built with FastAPI, PostgreSQL (Neon), and async SQLAlchemy.

---

## Stack

| Layer      | Tech                              |
|------------|-----------------------------------|
| API        | FastAPI + Uvicorn                 |
| Database   | PostgreSQL (Neon) via asyncpg     |
| ORM        | SQLAlchemy (async)                |
| Migrations | Alembic                           |
| Passwords  | argon2 (via passlib)              |
| Tokens     | JWT (python-jose)                 |
| Validation | Pydantic v2                       |
| Email      | SMTP or local file capture        |

---

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL database (e.g., Neon)
- `.env` file with required environment variables

### Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Configure environment variables (copy from .env.example)
cp .env.example .env
# Edit .env with your database URL and secrets
```

### Run Migrations

```bash
# Create initial migration (if needed)
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head
```

### Run the Server

```bash
# Start Uvicorn server
uvicorn app.main:app --reload

# Server runs at http://localhost:8000
# Interactive docs available at http://localhost:8000/docs
```

---

## API Endpoints

All endpoints use the `/api/v1` prefix. Use the interactive docs at `/docs` for live testing.

### Authentication

#### `POST /api/v1/auth/register`
Register a new user. Returns 201 and sends a confirmation email.

**Request Body:**
```json
{
  "username": "alice",
  "email": "alice@example.com",
  "password": "password123"
}
```

**Responses:**
- `201` – Registered successfully, confirmation email sent
- `409` – Email or username already taken

---

#### `POST /api/v1/auth/login`
Login after email is confirmed. Returns access and refresh tokens.

**Request Body:**
```json
{
  "email": "alice@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "access_token": "<jwt>",
  "refresh_token": "<jwt>"
}
```

**Responses:**
- `200` – Login successful, tokens returned
- `401` – Invalid credentials
- `403` – Email not confirmed

---

#### `GET /api/v1/auth/confirm-email`
Confirm email address using the token from the confirmation email.

**Query Parameters:**
- `token` (required) – Token from confirmation link

**Responses:**
- `200` – Email confirmed successfully
- `400` – Invalid or expired token

---

#### `POST /api/v1/auth/refresh`
Refresh the access token using a valid refresh token.

**Request Body:**
```json
{
  "refresh_token": "<jwt>"
}
```

**Response:**
```json
{
  "access_token": "<jwt>",
  "refresh_token": "<jwt>"
}
```

**Responses:**
- `200` – Tokens refreshed
- `401` – Invalid refresh token

---

#### `POST /api/v1/auth/resend-verification`
Resend the email verification link.

**Request Body:**
```json
{
  "email": "alice@example.com"
}
```

**Responses:**
- `200` – If an unverified account exists, a new verification email is sent

---

#### `POST /api/v1/auth/request-password-reset`
Request a password reset email.

**Request Body:**
```json
{
  "email": "alice@example.com"
}
```

**Responses:**
- `200` – If an account with that email exists, a password reset email is sent

---

#### `POST /api/v1/auth/reset-password`
Reset password using a valid reset token.

**Request Body:**
```json
{
  "token": "<reset-token>",
  "new_password": "newpassword123"
}
```

**Responses:**
- `200` – Password reset successfully
- `400` – Invalid or expired token

### Users

#### `GET /api/v1/users/me`
Get the current authenticated user profile. Requires a valid access token.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "id": "uuid",
  "username": "alice",
  "email": "alice@example.com",
  "is_active": true,
  "created_at": "2026-04-09T12:34:56Z"
}
```

**Responses:**
- `200` – Current user data
- `401` – Missing or invalid token

### Health

#### `GET /api/v1/health`
Health check endpoint (no authentication required).

**Response:**
```json
{
  "status": "ok"
}
```

---

## Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# Database (Neon PostgreSQL)
DATABASE_URL=postgresql+asyncpg://user:password@host/database?ssl=require

# JWT Secrets (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
SECRET_KEY=your-secret-key-here
REFRESH_TOKEN_SECRET=your-refresh-secret-here

# Base URL (for confirmation and reset links)
BASE_URL=http://localhost:8000

# Email Configuration (SMTP)
SMTP_HOST=smtp.mailtrap.io        # or smtp.gmail.com, etc.
SMTP_PORT=587
SMTP_USER=your-username
SMTP_PASS=your-password
SMTP_FROM=noreply@example.com
SMTP_TLS=true

# Development: Set to false to send real emails, true to capture to files
CAPTURE_EMAILS_TO_FILES=true
```

### Database Setup (Neon PostgreSQL)

1. Create a Neon PostgreSQL database at [neon.tech](https://neon.tech)
2. Copy the connection string to `DATABASE_URL` in `.env` (ensure `ssl=require` is included)
3. Run migrations: `alembic upgrade head`

---

## Database Models

The application uses SQLAlchemy async ORM with these core models:

- **User** – Username, email, password_hash, is_active, created_at
- **EmailVerificationToken** – For email confirmation (expires after 24 hours)
- **RefreshToken** – For refresh token rotation (expires after 7 days)
- **PasswordResetToken** – For password reset (expires after 1 hour)

---

## Project Structure

```
pi2-auth-platform/
├── app/                      # FastAPI application package
│   ├── main.py              # FastAPI app factory
│   ├── api/                 # API routes
│   │   ├── routes/          # Route modules (auth, users, health)
│   │   └── deps.py          # Dependency injection
│   ├── core/                # Core utilities
│   │   ├── config.py        # Pydantic settings
│   │   ├── database.py      # SQLAlchemy async engine/session
│   │   ├── security.py      # Password hashing
│   │   └── tokens.py        # JWT token generation/validation
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/             # Pydantic request/response schemas
│   ├── services/            # Business logic (auth, email)
│   └── repositories/        # Data access layer
├── alembic/                 # Database migrations
├── tests/                   # Test suite
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   └── conftest.py         # Pytest fixtures
├── .env                     # Environment variables (create from .env.example)
├── .env.example             # Example environment template
├── alembic.ini             # Alembic configuration
├── pyproject.toml          # Project metadata and dependencies
└── README.md               # This file
```

---

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/unit/test_auth_service.py

# Run with verbose output
pytest -v

# Run tests matching a pattern
pytest -k "test_register"
```

Currently **47 passing tests** covering:
- User registration and email verification
- Login and token refresh
- Password reset flow
- Authorization and authentication
- Input validation
- Error handling

---

## Security Notes

- **Passwords** hashed with **Argon2** (via passlib) with automatic salt generation
- **Email verification tokens** are **256-bit cryptographically random** (URL-safe base64)
- **Email verification** expires after **24 hours**
- **Password reset tokens** expire after **1 hour**
- **Access tokens** expire after **15 minutes**
- **Refresh tokens** expire after **7 days** (with rotation on use)
- **Database connection** requires SSL/TLS (`ssl=require` in connection string for Neon)
- **JWT tokens** signed with `SECRET_KEY` and `REFRESH_TOKEN_SECRET` (keep these secure!)
- All sensitive endpoints require Bearer token authentication
- Email addresses are validated and unique per user
- Usernames are validated and unique per user

---

## Development Notes

- **Email capture** for development: Set `CAPTURE_EMAILS_TO_FILES=true` in `.env` to save emails locally instead of sending via SMTP
- **Interactive API docs**: Available at `/docs` (Swagger UI) and `/redoc` (ReDoc) when the server is running
- **Database migrations**: Use `alembic` to manage schema changes safely
- **Async throughout**: All database operations are async for better performance and scalability
- **Environment-based configuration**: All settings come from environment variables (no hardcoding)
