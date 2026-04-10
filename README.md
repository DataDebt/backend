# 🔐 Auth Platform

A local user registration system with email confirmation, built with Flask + SQLite.

---

## Stack

| Layer    | Tech                              |
|----------|-----------------------------------|
| API      | Flask                             |
| Database | SQLite (via Python stdlib)        |
| Passwords| PBKDF2-HMAC-SHA256 (stdlib)       |
| Tokens   | JWT + `secrets.token_urlsafe(32)` |
| Email    | SMTP or local file fallback       |

---

## Quick Start

```bash
# Install Flask and JWT
pip install flask pyjwt

# Run the server
python app.py
```

Server starts at **http://localhost:5000**

---

## API Endpoints

### `POST /api/register`
Register a new user. Sends a confirmation email.

**Body:**
```json
{
  "username": "alice",
  "email": "alice@example.com",
  "password": "password123"
}
```

**Responses:**
- `201` – Registered, email sent
- `400` – Missing fields / password too short / bad email
- `409` – Email or username already taken

---

### `GET /api/confirm/<token>`
Confirm email address using the token from the confirmation email.

**Responses:**
- `200` – Account confirmed
- `404` – Invalid token
- `410` – Token expired (re-register)

---

### `POST /api/login`
Login after email is confirmed. Returns a JWT.

**Body:**
```json
{ "email": "alice@example.com", "password": "password123" }
```

**Responses:**
- `200` – `{ "token": "<jwt>", "username": "alice" }`
- `401` – Invalid credentials
- `403` – Email not confirmed

---

### `POST /api/resend-confirmation`
Resend the confirmation email.

**Body:**
```json
{ "email": "alice@example.com" }
```

---

### `GET /api/users`
List all registered users (no passwords exposed).

---

### `GET /api/emails`
View captured emails (dev tool). Each email is also saved as `.html` in `emails/`.

---

## Email Configuration

By default, emails are saved to `emails/` as `.json` + `.html` files — no SMTP needed.

To send real emails, edit `.env`:

```env
# Mailtrap (recommended for testing)
SMTP_HOST=sandbox.smtp.mailtrap.io
SMTP_PORT=2525
SMTP_USER=your-user
SMTP_PASS=your-pass
SMTP_FROM=noreply@yourdomain.com

# Gmail
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASS=your-app-password   # Use App Password, not account password
SMTP_TLS=true
```

---

## Database Schema

```sql
CREATE TABLE users (
    id                  TEXT PRIMARY KEY,     -- UUID
    username            TEXT NOT NULL UNIQUE,
    email               TEXT NOT NULL UNIQUE,
    password_hash       TEXT NOT NULL,        -- PBKDF2-SHA256
    confirmed           INTEGER DEFAULT 0,
    confirmation_token  TEXT,                 -- NULL after confirmation
    token_expires_at    TEXT,                 -- ISO datetime, 24hr window
    created_at          TEXT NOT NULL,
    last_login          TEXT
);
```

---

## File Structure

```
auth-platform/
├── app.py            # Flask routes
├── db.py             # SQLite setup & connection
├── email_service.py  # SMTP + file fallback
├── password_utils.py # PBKDF2 hashing
├── config.py         # Config from .env
├── test_api.py       # Integration tests
├── .env              # Your config (edit this)
├── db/
│   └── users.db      # SQLite database
└── emails/           # Captured emails (dev mode)
    ├── *.json        # Email metadata + confirm URL
    └── *.html        # Full HTML preview
```

---

## Running Tests

```bash
python test_api.py   # Runs against Flask test client — no server needed
```

---

## Security Notes

- Passwords hashed with **PBKDF2-HMAC-SHA256** at 260,000 iterations
- Confirmation tokens are **256-bit cryptographically random** (`secrets`)
- Tokens expire after **24 hours**
- JWT sessions expire after **12 hours**
- Confirmed tokens are **nulled out** in DB after use
- Timing-safe comparison via `hmac.compare_digest`
