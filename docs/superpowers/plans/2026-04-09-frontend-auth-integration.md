# Frontend Auth Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect the existing FastAPI auth backend in `PI2` to the sibling `frontend` Next.js app so login, logout, session restore, register, email confirmation, forgot password, and password reset all work end-to-end.

**Architecture:** Keep the backend and frontend as sibling repositories. Update the backend to expose frontend-facing auth links and browser CORS, then add a small client-side auth layer in the Next app that stores tokens, restores sessions with `/users/me` and `/auth/refresh`, and replaces the current demo login flow while leaving mocked post-login product data intact.

**Tech Stack:** FastAPI, Pydantic Settings, pytest, Next.js App Router, React 19, browser `fetch`, browser storage, ESLint

---

## File Structure

### Backend repository: `PI2/`

- Modify: `app/core/config.py`
  - Add frontend URL and CORS origin settings
- Modify: `app/main.py`
  - Install CORS middleware with configured frontend origins
- Modify: `app/api/routes/auth.py`
  - Generate frontend confirmation and reset links in auth emails
- Modify: `.env.example`
  - Document frontend URL and CORS origin variables
- Create: `tests/unit/test_frontend_integration_settings.py`
  - Cover new settings coercion and defaults
- Create: `tests/integration/test_auth_email_links.py`
  - Verify email-generated links target frontend routes
- Create: `tests/integration/test_cors.py`
  - Verify configured frontend origin receives CORS headers

### Frontend repository: `../frontend/`

- Create: `.env.local.example`
  - Document `NEXT_PUBLIC_API_BASE_URL`
- Create: `src/lib/api.js`
  - Minimal JSON fetch client for backend auth endpoints
- Create: `src/lib/auth-storage.js`
  - Token persistence helpers
- Create: `src/lib/auth-errors.js`
  - Normalize backend responses to UI-friendly messages
- Create: `src/context/AuthContext.jsx`
  - Own auth state, startup restore, refresh-and-retry, and auth actions
- Create: `src/components/auth/AuthShell.jsx`
  - Shared auth page wrapper to preserve current visual direction
- Create: `src/components/auth/LoginForm.jsx`
  - Real login form
- Create: `src/components/auth/RegisterForm.jsx`
  - Registration form and resend-verification entry point
- Create: `src/components/auth/ForgotPasswordForm.jsx`
  - Password reset request form
- Create: `src/components/auth/ResetPasswordForm.jsx`
  - New password form that uses URL token
- Create: `src/components/auth/AuthStatusCard.jsx`
  - Reusable success/error status presentation for confirm-email/reset flows
- Create: `src/app/auth/confirm-email/page.js`
  - Frontend email confirmation route
- Create: `src/app/auth/reset-password/page.js`
  - Frontend password reset route
- Modify: `src/app/layout.js`
  - Wrap app in auth provider
- Modify: `src/app/page.js`
  - Replace demo auth gate with provider-driven auth gate
- Modify: `src/components/views/LoginScreen.jsx`
  - Either retire or convert into a shell that delegates to auth forms
- Modify: `src/layouts/UserLayout.jsx`
  - Consume auth logout and optionally show real user profile data
- Modify: `src/components/layout/Sidebar.jsx`
  - Remove hard-coded demo role/email and show real authenticated user
- Delete or stop importing: `src/layouts/AdminLayout.jsx`
  - Remove demo admin routing from the main app flow

### Manual verification notes

- Backend test commands run from `PI2/`
- Frontend lint/build/manual verification commands run from `../frontend/`
- If the sibling repo is cloned somewhere else, update every `../frontend/...` path in this plan before implementation

### Task 1: Prepare The Sibling Frontend Repo And Environment Contract

**Files:**
- Create: `../frontend/`
- Create: `../frontend/.env.local.example`
- Modify: `.env.example`
- Test: `README manual setup notes in docs/superpowers/plans/2026-04-09-frontend-auth-integration.md`

- [ ] **Step 1: Clone the frontend repo next to the backend repo**

Run:

```bash
cd /Users/diegocarvajal/Documents/Programming
git clone https://github.com/DataDebt/frontend.git
```

Expected: a new sibling directory exists at `/Users/diegocarvajal/Documents/Programming/frontend`

- [ ] **Step 2: Verify the frontend repo structure before changing anything**

Run:

```bash
cd /Users/diegocarvajal/Documents/Programming/frontend
git status --short
find src -maxdepth 3 -type f | sort
```

Expected: clean working tree and files matching the current Next app structure including `src/app/page.js` and `src/components/views/LoginScreen.jsx`

- [ ] **Step 3: Add the frontend environment example file**

Create `../frontend/.env.local.example`:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

- [ ] **Step 4: Document the backend env additions in `.env.example`**

Update `.env.example`:

```env
APP_NAME=Auth Platform API
ENVIRONMENT=development
DEBUG=true
API_V1_PREFIX=/api/v1
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/auth_platform
SECRET_KEY=change-me
REFRESH_TOKEN_SECRET=change-me-too
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
VERIFICATION_TOKEN_EXPIRE_HOURS=24
PASSWORD_RESET_EXPIRE_HOURS=1
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
SMTP_FROM=noreply@example.com
SMTP_TLS=true
CAPTURE_EMAILS_TO_FILES=true
BASE_URL=http://localhost:8000
FRONTEND_BASE_URL=http://localhost:3000
BACKEND_CORS_ORIGINS=http://localhost:3000
```

- [ ] **Step 5: Sanity-check both env contracts**

Run:

```bash
cd /Users/diegocarvajal/Documents/Programming/PI2
rg -n "FRONTEND_BASE_URL|BACKEND_CORS_ORIGINS" .env.example
cd /Users/diegocarvajal/Documents/Programming/frontend
cat .env.local.example
```

Expected: backend env example contains both new variables and frontend env example contains `NEXT_PUBLIC_API_BASE_URL`

- [ ] **Step 6: Commit the environment scaffolding**

Run:

```bash
cd /Users/diegocarvajal/Documents/Programming/PI2
git add .env.example docs/superpowers/plans/2026-04-09-frontend-auth-integration.md
git commit -m "docs: document frontend auth integration env contract"
```

Expected: commit succeeds in `PI2`; commit frontend repo changes separately when they exist

### Task 2: Add Backend Settings Support For Frontend Links And CORS Origins

**Files:**
- Modify: `app/core/config.py`
- Create: `tests/unit/test_frontend_integration_settings.py`
- Test: `tests/unit/test_frontend_integration_settings.py`

- [ ] **Step 1: Write the failing settings test**

Create `tests/unit/test_frontend_integration_settings.py`:

```python
import importlib


def test_frontend_integration_settings_are_loaded(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/app")
    monkeypatch.setenv("SECRET_KEY", "secret")
    monkeypatch.setenv("REFRESH_TOKEN_SECRET", "refresh-secret")
    monkeypatch.setenv("FRONTEND_BASE_URL", "http://localhost:3000")
    monkeypatch.setenv("BACKEND_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")

    module = importlib.import_module("app.core.config")
    settings = module.Settings()

    assert settings.frontend_base_url == "http://localhost:3000"
    assert settings.backend_cors_origins == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
```

- [ ] **Step 2: Run the settings test to verify it fails**

Run:

```bash
cd /Users/diegocarvajal/Documents/Programming/PI2
pytest tests/unit/test_frontend_integration_settings.py -v
```

Expected: FAIL because `Settings` does not yet define `frontend_base_url` or `backend_cors_origins`

- [ ] **Step 3: Implement the minimal settings support**

Update `app/core/config.py`:

```python
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Auth Platform API"
    environment: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    database_url: str = Field(alias="DATABASE_URL")
    secret_key: str = Field(alias="SECRET_KEY")
    refresh_token_secret: str = Field(alias="REFRESH_TOKEN_SECRET")
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    verification_token_expire_hours: int = 24
    password_reset_expire_hours: int = 1
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    smtp_from: str = "noreply@example.com"
    smtp_tls: bool = True
    capture_emails_to_files: bool = True
    base_url: str = "http://localhost:8000"
    frontend_base_url: str = Field(default="http://localhost:3000", alias="FRONTEND_BASE_URL")
    backend_cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        alias="BACKEND_CORS_ORIGINS",
    )

    @field_validator("debug", mode="before")
    @classmethod
    def _coerce_debug(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on"}:
                return True
            if normalized in {"0", "false", "no", "off", "release"}:
                return False
        return value

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def _coerce_backend_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value
```

- [ ] **Step 4: Run the settings test to verify it passes**

Run:

```bash
cd /Users/diegocarvajal/Documents/Programming/PI2
pytest tests/unit/test_frontend_integration_settings.py -v
```

Expected: PASS

- [ ] **Step 5: Commit the settings support**

Run:

```bash
cd /Users/diegocarvajal/Documents/Programming/PI2
git add app/core/config.py tests/unit/test_frontend_integration_settings.py .env.example
git commit -m "feat: add frontend auth integration settings"
```

Expected: commit succeeds

### Task 3: Add Backend CORS Middleware For Browser Auth Calls

**Files:**
- Modify: `app/main.py`
- Create: `tests/integration/test_cors.py`
- Test: `tests/integration/test_cors.py`

- [ ] **Step 1: Write the failing CORS integration test**

Create `tests/integration/test_cors.py`:

```python
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_preflight_allows_configured_frontend_origin():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
```

- [ ] **Step 2: Run the CORS test to verify it fails**

Run:

```bash
cd /Users/diegocarvajal/Documents/Programming/PI2
pytest tests/integration/test_cors.py -v
```

Expected: FAIL because the app does not yet install CORS middleware

- [ ] **Step 3: Install CORS middleware using configured origins**

Update `app/main.py`:

```python
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings

app = FastAPI(title=settings.app_name, debug=settings.debug)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_v1_prefix)
```

- [ ] **Step 4: Run the CORS test to verify it passes**

Run:

```bash
cd /Users/diegocarvajal/Documents/Programming/PI2
pytest tests/integration/test_cors.py -v
```

Expected: PASS

- [ ] **Step 5: Commit the CORS middleware**

Run:

```bash
cd /Users/diegocarvajal/Documents/Programming/PI2
git add app/main.py tests/integration/test_cors.py
git commit -m "feat: allow frontend auth requests with CORS"
```

Expected: commit succeeds

### Task 4: Point Backend Auth Emails At Frontend Routes

**Files:**
- Modify: `app/api/routes/auth.py`
- Create: `tests/integration/test_auth_email_links.py`
- Test: `tests/integration/test_auth_email_links.py`

- [ ] **Step 1: Write the failing email-link integration test**

Create `tests/integration/test_auth_email_links.py`:

```python
import pytest

from app.api.routes import auth


@pytest.mark.asyncio
async def test_register_email_uses_frontend_confirmation_url(monkeypatch, db_session):
    captured: dict[str, str] = {}

    def fake_send_email(to_email, subject, html, text, metadata):
        captured["text"] = text

    monkeypatch.setattr(auth.settings, "frontend_base_url", "http://localhost:3000")
    monkeypatch.setattr(auth, "send_email", fake_send_email)

    await auth.register(
        payload=auth.RegisterRequest(
            username="alice",
            email="alice@example.com",
            password="password123!",
        ),
        background_tasks=type(
            "BG",
            (),
            {"add_task": lambda self, fn, *args: fn(*args)},
        )(),
        session=db_session,
    )

    assert "http://localhost:3000/auth/confirm-email?token=" in captured["text"]


@pytest.mark.asyncio
async def test_request_password_reset_email_uses_frontend_reset_url(monkeypatch, db_session):
    captured: dict[str, str] = {}

    service = auth.AuthService(db_session)
    _, raw_token = await service.register_user("bob", "bob@example.com", "password123!")
    await service.confirm_email(raw_token)

    def fake_send_email(to_email, subject, html, text, metadata):
        captured["text"] = text

    monkeypatch.setattr(auth.settings, "frontend_base_url", "http://localhost:3000")
    monkeypatch.setattr(auth, "send_email", fake_send_email)

    await auth.request_password_reset(
        payload=auth.RequestPasswordResetRequest(email="bob@example.com"),
        background_tasks=type(
            "BG",
            (),
            {"add_task": lambda self, fn, *args: fn(*args)},
        )(),
        session=db_session,
    )

    assert "http://localhost:3000/auth/reset-password?token=" in captured["text"]
```

- [ ] **Step 2: Run the email-link test to verify it fails**

Run:

```bash
cd /Users/diegocarvajal/Documents/Programming/PI2
pytest tests/integration/test_auth_email_links.py -v
```

Expected: FAIL because auth routes still build links from `settings.base_url`

- [ ] **Step 3: Update auth routes to generate frontend links**

Update the relevant parts of `app/api/routes/auth.py`:

```python
@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    service = AuthService(session)
    try:
        user, raw_token = await service.register_user(payload.username, payload.email, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    confirm_url = f"{settings.frontend_base_url}/auth/confirm-email?token={raw_token}"
    html = build_email_verification_html(user.username, confirm_url)
    background_tasks.add_task(
        send_email,
        user.email,
        "Confirm your email",
        html,
        f"Confirm your email: {confirm_url}",
        {"confirm_url": confirm_url, "username": user.username},
    )
    return MessageResponse(message="Registration successful. Please check your email.")


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(
    payload: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    service = AuthService(session)
    user, raw_token = await service.resend_verification(payload.email)

    if user and raw_token:
        confirm_url = f"{settings.frontend_base_url}/auth/confirm-email?token={raw_token}"
        html = build_email_verification_html(user.username, confirm_url)
        background_tasks.add_task(
            send_email,
            user.email,
            "Confirm your email",
            html,
            f"Confirm your email: {confirm_url}",
            {"confirm_url": confirm_url, "username": user.username},
        )
    return MessageResponse(message="If an unverified account with that email exists, a new verification email has been sent.")


@router.post("/request-password-reset", response_model=MessageResponse)
async def request_password_reset(
    payload: RequestPasswordResetRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    service = AuthService(session)
    raw_token, user = await service.request_password_reset(payload.email)
    if raw_token and user:
        reset_url = f"{settings.frontend_base_url}/auth/reset-password?token={raw_token}"
        html = build_password_reset_html(user.username, reset_url)
        background_tasks.add_task(
            send_email,
            user.email,
            "Reset your password",
            html,
            f"Reset your password: {reset_url}",
            {"reset_url": reset_url, "username": user.username},
        )
    return MessageResponse(message="If an account with that email exists, a password reset email has been sent.")
```

- [ ] **Step 4: Run the email-link test to verify it passes**

Run:

```bash
cd /Users/diegocarvajal/Documents/Programming/PI2
pytest tests/integration/test_auth_email_links.py -v
```

Expected: PASS

- [ ] **Step 5: Commit the email-link change**

Run:

```bash
cd /Users/diegocarvajal/Documents/Programming/PI2
git add app/api/routes/auth.py tests/integration/test_auth_email_links.py
git commit -m "feat: send frontend auth links in emails"
```

Expected: commit succeeds

### Task 5: Build The Frontend Auth API Client And Token Persistence

**Files:**
- Create: `../frontend/src/lib/api.js`
- Create: `../frontend/src/lib/auth-storage.js`
- Create: `../frontend/src/lib/auth-errors.js`
- Test: `../frontend npm run lint`

- [ ] **Step 1: Create the API base and JSON request helper**

Create `../frontend/src/lib/api.js`:

```javascript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

function buildHeaders(token, extraHeaders = {}) {
  const headers = { "Content-Type": "application/json", ...extraHeaders };
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

export async function apiRequest(path, { method = "GET", body, token, headers } = {}) {
  if (!API_BASE_URL) {
    throw new Error("Missing NEXT_PUBLIC_API_BASE_URL");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: buildHeaders(token, headers),
    body: body ? JSON.stringify(body) : undefined,
  });

  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json")
    ? await response.json()
    : { message: await response.text() };

  if (!response.ok) {
    const error = new Error(data.detail || data.message || "Request failed");
    error.status = response.status;
    error.data = data;
    throw error;
  }

  return data;
}
```

- [ ] **Step 2: Create token storage helpers**

Create `../frontend/src/lib/auth-storage.js`:

```javascript
const ACCESS_TOKEN_KEY = "datadebt.access_token";
const REFRESH_TOKEN_KEY = "datadebt.refresh_token";

function canUseStorage() {
  return typeof window !== "undefined" && !!window.localStorage;
}

export function readStoredTokens() {
  if (!canUseStorage()) {
    return { accessToken: null, refreshToken: null };
  }

  return {
    accessToken: window.localStorage.getItem(ACCESS_TOKEN_KEY),
    refreshToken: window.localStorage.getItem(REFRESH_TOKEN_KEY),
  };
}

export function storeTokens({ accessToken, refreshToken }) {
  if (!canUseStorage()) return;
  window.localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  window.localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function clearStoredTokens() {
  if (!canUseStorage()) return;
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
}
```

- [ ] **Step 3: Create auth error mapping helpers**

Create `../frontend/src/lib/auth-errors.js`:

```javascript
export function getAuthErrorMessage(error, fallbackMessage) {
  if (error?.status === 401) return "Correo o contraseña inválidos.";
  if (error?.status === 403) return "Debes confirmar tu correo antes de iniciar sesión.";
  if (error?.status === 409) return error.message || "El correo o nombre de usuario ya está en uso.";
  if (error?.status === 400) return error.message || fallbackMessage;
  return fallbackMessage || "Ocurrió un error inesperado.";
}
```

- [ ] **Step 4: Lint the new frontend utilities**

Run:

```bash
cd /Users/diegocarvajal/Documents/Programming/frontend
cp .env.local.example .env.local
npm install
npm run lint
```

Expected: PASS with no lint errors in `src/lib/*.js`

- [ ] **Step 5: Commit the frontend auth utility layer**

Run:

```bash
cd /Users/diegocarvajal/Documents/Programming/frontend
git add .env.local.example src/lib/api.js src/lib/auth-storage.js src/lib/auth-errors.js
git commit -m "feat: add frontend auth client utilities"
```

Expected: commit succeeds

### Task 6: Add The Frontend Auth Provider And Session Restore Gate

**Files:**
- Create: `../frontend/src/context/AuthContext.jsx`
- Modify: `../frontend/src/app/layout.js`
- Modify: `../frontend/src/app/page.js`
- Modify: `../frontend/src/layouts/UserLayout.jsx`
- Modify: `../frontend/src/components/layout/Sidebar.jsx`
- Test: `../frontend npm run lint`

- [ ] **Step 1: Create the auth provider**

Create `../frontend/src/context/AuthContext.jsx`:

```javascript
"use client";

import { createContext, useContext, useEffect, useState } from "react";

import { apiRequest } from "@/lib/api";
import { clearStoredTokens, readStoredTokens, storeTokens } from "@/lib/auth-storage";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [status, setStatus] = useState("loading");
  const [user, setUser] = useState(null);
  const [tokens, setTokens] = useState({ accessToken: null, refreshToken: null });

  async function loadUserWithAccessToken(accessToken) {
    return apiRequest("/users/me", { token: accessToken });
  }

  async function restoreSession() {
    const stored = readStoredTokens();
    if (!stored.accessToken || !stored.refreshToken) {
      setTokens({ accessToken: null, refreshToken: null });
      setUser(null);
      setStatus("unauthenticated");
      return;
    }

    try {
      const currentUser = await loadUserWithAccessToken(stored.accessToken);
      setTokens(stored);
      setUser(currentUser);
      setStatus("authenticated");
      return;
    } catch (error) {
      if (error.status !== 401) {
        clearStoredTokens();
        setTokens({ accessToken: null, refreshToken: null });
        setUser(null);
        setStatus("unauthenticated");
        return;
      }
    }

    try {
      const refreshed = await apiRequest("/auth/refresh", {
        method: "POST",
        body: { refresh_token: stored.refreshToken },
      });
      const nextTokens = {
        accessToken: refreshed.access_token,
        refreshToken: refreshed.refresh_token,
      };
      storeTokens(nextTokens);
      const currentUser = await loadUserWithAccessToken(nextTokens.accessToken);
      setTokens(nextTokens);
      setUser(currentUser);
      setStatus("authenticated");
    } catch {
      clearStoredTokens();
      setTokens({ accessToken: null, refreshToken: null });
      setUser(null);
      setStatus("unauthenticated");
    }
  }

  useEffect(() => {
    restoreSession();
  }, []);

  async function login(email, password) {
    const result = await apiRequest("/auth/login", {
      method: "POST",
      body: { email, password },
    });
    const nextTokens = {
      accessToken: result.access_token,
      refreshToken: result.refresh_token,
    };
    storeTokens(nextTokens);
    const currentUser = await loadUserWithAccessToken(nextTokens.accessToken);
    setTokens(nextTokens);
    setUser(currentUser);
    setStatus("authenticated");
    return currentUser;
  }

  function logout() {
    clearStoredTokens();
    setTokens({ accessToken: null, refreshToken: null });
    setUser(null);
    setStatus("unauthenticated");
  }

  const value = {
    status,
    user,
    accessToken: tokens.accessToken,
    refreshToken: tokens.refreshToken,
    login,
    logout,
    restoreSession,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within an AuthProvider");
  return context;
}
```

- [ ] **Step 2: Wrap the app in the provider**

Update `../frontend/src/app/layout.js`:

```javascript
import { Geist, Geist_Mono } from "next/font/google";

import { AuthProvider } from "@/context/AuthContext";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata = {
  title: "Data Debt",
  description: "Generated by create next app",
};

export default function RootLayout({ children }) {
  return (
    <html lang="es">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className={`${geistSans.variable} ${geistMono.variable}`}>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
```

- [ ] **Step 3: Replace the demo page gate with the provider state**

Update `../frontend/src/app/page.js`:

```javascript
"use client";

import LoginScreen from "@/components/views/LoginScreen";
import UserLayout from "@/layouts/UserLayout";
import { useAuth } from "@/context/AuthContext";

export default function Page() {
  const { status } = useAuth();

  if (status === "loading") {
    return <div style={{ minHeight: "100vh", display: "grid", placeItems: "center" }}>Cargando...</div>;
  }

  if (status === "unauthenticated") {
    return <LoginScreen />;
  }

  return <UserLayout />;
}
```

- [ ] **Step 4: Pass real logout and user data into the user shell**

Update `../frontend/src/layouts/UserLayout.jsx`:

```javascript
import { C } from "@/constants/colors";
import Sidebar from "@/components/layout/Sidebar";
import { MyEvaluationsView } from "@/components/views/MyEvaluationsView";
import { useAuth } from "@/context/AuthContext";

export default function UserLayout() {
  const { logout, user } = useAuth();

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: C.bg, fontFamily: "'Outfit', 'Segoe UI', sans-serif" }}>
      <Sidebar
        role="user"
        active="my-evaluations"
        onNav={() => {}}
        onLogout={logout}
        user={user}
      />
      <main style={{ flex: 1, overflowY: "auto" }}>
        <MyEvaluationsView />
      </main>
    </div>
  );
}
```

- [ ] **Step 5: Remove hard-coded demo identity from the sidebar**

Update the relevant parts of `../frontend/src/components/layout/Sidebar.jsx`:

```javascript
export default function Sidebar({ role, active, onNav, onLogout, user }) {
  const adminItems = [
    { key: "domains", icon: <MdDomain size={20} />, label: "Dominios" },
    { key: "reports", icon: <MdBarChart size={20} />, label: "Reportes" },
    { key: "evaluations", icon: <MdAssignment size={20} />, label: "Evaluaciones" },
  ];
  const userItems = [{ key: "my-evaluations", icon: <MdAssignment size={20} />, label: "Mis Evaluaciones" }];
  const items = role === "admin" ? adminItems : userItems;
  const initials = user?.username ? user.username.slice(0, 1).toUpperCase() : "U";
  const subtitle = user?.email || "Sin correo";

  return (
    <div style={{ width: 230, minHeight: "100vh", background: C.sidebar, display: "flex", flexDirection: "column", boxShadow: "4px 0 24px rgba(0,0,0,0.18)", position: "relative", zIndex: 10 }}>
      {/* ...existing logo and nav... */}
      <div style={{ padding: "16px 12px", borderTop: "1px solid rgba(255,255,255,0.08)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 14px", borderRadius: 10, background: "rgba(255,255,255,0.06)", marginBottom: 8 }}>
          <div style={{ width: 32, height: 32, borderRadius: "50%", background: `linear-gradient(135deg, ${C.accent}, #1a5c3a)`, display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontWeight: 700, fontSize: 13 }}>
            {initials}
          </div>
          <div>
            <div style={{ color: "#fff", fontSize: 13, fontWeight: 600 }}>{user?.username || "Usuario"}</div>
            <div style={{ color: "rgba(255,255,255,0.4)", fontSize: 10 }}>{subtitle}</div>
          </div>
        </div>
        <button onClick={onLogout} style={{ width: "100%", padding: "9px", background: "rgba(255,255,255,0.06)", border: "none", borderRadius: 8, color: "rgba(255,255,255,0.5)", fontSize: 13, cursor: "pointer", transition: "all .2s" }}>
          Cerrar sesión ⏻
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Lint the provider and gate changes**

Run:

```bash
cd /Users/diegocarvajal/Documents/Programming/frontend
npm run lint
```

Expected: PASS

- [ ] **Step 7: Commit the provider and session restore gate**

Run:

```bash
cd /Users/diegocarvajal/Documents/Programming/frontend
git add src/context/AuthContext.jsx src/app/layout.js src/app/page.js src/layouts/UserLayout.jsx src/components/layout/Sidebar.jsx
git commit -m "feat: add frontend auth provider and session restore"
```

Expected: commit succeeds

### Task 7: Replace The Demo Login Screen With Real Login, Register, And Forgot Password Flows

**Files:**
- Create: `../frontend/src/components/auth/AuthShell.jsx`
- Create: `../frontend/src/components/auth/LoginForm.jsx`
- Create: `../frontend/src/components/auth/RegisterForm.jsx`
- Create: `../frontend/src/components/auth/ForgotPasswordForm.jsx`
- Modify: `../frontend/src/components/views/LoginScreen.jsx`
- Modify: `../frontend/src/context/AuthContext.jsx`
- Test: `../frontend npm run lint`

- [ ] **Step 1: Extend the auth provider with register and reset-request actions**

Update the relevant parts of `../frontend/src/context/AuthContext.jsx`:

```javascript
import { apiRequest } from "@/lib/api";

// inside AuthProvider
async function register({ username, email, password }) {
  return apiRequest("/auth/register", {
    method: "POST",
    body: { username, email, password },
  });
}

async function resendVerification(email) {
  return apiRequest("/auth/resend-verification", {
    method: "POST",
    body: { email },
  });
}

async function requestPasswordReset(email) {
  return apiRequest("/auth/request-password-reset", {
    method: "POST",
    body: { email },
  });
}

const value = {
  status,
  user,
  accessToken: tokens.accessToken,
  refreshToken: tokens.refreshToken,
  login,
  logout,
  restoreSession,
  register,
  resendVerification,
  requestPasswordReset,
};
```

- [ ] **Step 2: Add a shared auth shell for the current look and feel**

Create `../frontend/src/components/auth/AuthShell.jsx`:

```javascript
"use client";

import GeoBg from "@/components/ui/GeoBg";
import { C } from "@/constants/colors";

export default function AuthShell({ title, subtitle, children, footer }) {
  return (
    <div style={{ minHeight: "100vh", background: "linear-gradient(135deg, #c8edd8 0%, #e8f7ef 50%, #d0eedf 100%)", display: "flex", alignItems: "center", position: "relative", overflow: "hidden", fontFamily: "'Outfit', 'Segoe UI', sans-serif" }}>
      <GeoBg />
      <div style={{ flex: 1, padding: "0 80px", zIndex: 1 }}>
        <h1 style={{ fontSize: 52, fontWeight: 800, color: "#0d3d26", letterSpacing: -1, marginBottom: 8 }}>Data Debt</h1>
        <p style={{ fontSize: 20, color: C.accent, fontWeight: 600, marginBottom: 28 }}>Your web tool to diagnosis data deb</p>
      </div>
      <div style={{ width: 420, marginRight: 80, zIndex: 1, background: "rgba(255,255,255,0.78)", backdropFilter: "blur(20px)", borderRadius: 20, boxShadow: "0 20px 60px rgba(0,80,40,0.18)", padding: "44px 40px" }}>
        <h2 style={{ textAlign: "center", fontSize: 26, fontWeight: 700, color: C.text, marginBottom: 6 }}>{title}</h2>
        <p style={{ textAlign: "center", color: C.textMuted, marginBottom: 32, fontSize: 14 }}>{subtitle}</p>
        {children}
        {footer}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Add the login form component**

Create `../frontend/src/components/auth/LoginForm.jsx`:

```javascript
"use client";

import { useState } from "react";

import { useAuth } from "@/context/AuthContext";
import { getAuthErrorMessage } from "@/lib/auth-errors";

export default function LoginForm({ onShowRegister, onShowForgotPassword }) {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      await login(email, password);
    } catch (submitError) {
      setError(getAuthErrorMessage(submitError, "No fue posible iniciar sesión."));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <input value={email} onChange={(event) => setEmail(event.target.value)} placeholder="Email" style={{ width: "100%", boxSizing: "border-box", padding: "12px 14px", border: "1.5px solid #d0e8dc", borderRadius: 10, fontSize: 15, outline: "none", background: "#fff", marginBottom: 16 }} />
      <input value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Password" type="password" style={{ width: "100%", boxSizing: "border-box", padding: "12px 14px", border: "1.5px solid #d0e8dc", borderRadius: 10, fontSize: 15, outline: "none", background: "#fff", marginBottom: 16 }} />
      {error ? <p style={{ color: "#d14343", fontSize: 13, marginBottom: 12 }}>{error}</p> : null}
      <button type="submit" disabled={isSubmitting} style={{ width: "100%", padding: "14px", background: "linear-gradient(135deg, #1a5c3a, #2d9f65)", color: "#fff", border: "none", borderRadius: 10, fontSize: 16, fontWeight: 700, cursor: "pointer" }}>
        {isSubmitting ? "Ingresando..." : "Login"}
      </button>
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 16, fontSize: 13 }}>
        <button type="button" onClick={onShowRegister} style={{ border: "none", background: "transparent", color: "#2d9f65", cursor: "pointer" }}>Crear cuenta</button>
        <button type="button" onClick={onShowForgotPassword} style={{ border: "none", background: "transparent", color: "#2d9f65", cursor: "pointer" }}>Forgot your password?</button>
      </div>
    </form>
  );
}
```

- [ ] **Step 4: Add the register and forgot-password forms**

Create `../frontend/src/components/auth/RegisterForm.jsx`:

```javascript
"use client";

import { useState } from "react";

import { useAuth } from "@/context/AuthContext";
import { getAuthErrorMessage } from "@/lib/auth-errors";

export default function RegisterForm({ onBackToLogin }) {
  const { register, resendVerification } = useAuth();
  const [form, setForm] = useState({ username: "", email: "", password: "" });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    setMessage("");
    setError("");
    try {
      const result = await register(form);
      setMessage(result.message);
    } catch (submitError) {
      setError(getAuthErrorMessage(submitError, "No fue posible registrarte."));
    }
  }

  async function handleResend() {
    const result = await resendVerification(form.email);
    setMessage(result.message);
  }

  return (
    <form onSubmit={handleSubmit}>
      <input value={form.username} onChange={(event) => setForm({ ...form, username: event.target.value })} placeholder="Username" style={{ width: "100%", boxSizing: "border-box", padding: "12px 14px", border: "1.5px solid #d0e8dc", borderRadius: 10, marginBottom: 12 }} />
      <input value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} placeholder="Email" style={{ width: "100%", boxSizing: "border-box", padding: "12px 14px", border: "1.5px solid #d0e8dc", borderRadius: 10, marginBottom: 12 }} />
      <input value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} placeholder="Password" type="password" style={{ width: "100%", boxSizing: "border-box", padding: "12px 14px", border: "1.5px solid #d0e8dc", borderRadius: 10, marginBottom: 12 }} />
      {message ? <p style={{ color: "#1a5c3a", fontSize: 13, marginBottom: 12 }}>{message}</p> : null}
      {error ? <p style={{ color: "#d14343", fontSize: 13, marginBottom: 12 }}>{error}</p> : null}
      <button type="submit" style={{ width: "100%", padding: "14px", background: "linear-gradient(135deg, #1a5c3a, #2d9f65)", color: "#fff", border: "none", borderRadius: 10, fontSize: 16, fontWeight: 700 }}>Crear cuenta</button>
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 16, fontSize: 13 }}>
        <button type="button" onClick={onBackToLogin} style={{ border: "none", background: "transparent", color: "#2d9f65", cursor: "pointer" }}>Volver</button>
        <button type="button" onClick={handleResend} style={{ border: "none", background: "transparent", color: "#2d9f65", cursor: "pointer" }}>Reenviar confirmación</button>
      </div>
    </form>
  );
}
```

Create `../frontend/src/components/auth/ForgotPasswordForm.jsx`:

```javascript
"use client";

import { useState } from "react";

import { useAuth } from "@/context/AuthContext";
import { getAuthErrorMessage } from "@/lib/auth-errors";

export default function ForgotPasswordForm({ onBackToLogin }) {
  const { requestPasswordReset } = useAuth();
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    setMessage("");
    setError("");
    try {
      const result = await requestPasswordReset(email);
      setMessage(result.message);
    } catch (submitError) {
      setError(getAuthErrorMessage(submitError, "No fue posible solicitar el cambio de contraseña."));
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <input value={email} onChange={(event) => setEmail(event.target.value)} placeholder="Email" style={{ width: "100%", boxSizing: "border-box", padding: "12px 14px", border: "1.5px solid #d0e8dc", borderRadius: 10, marginBottom: 12 }} />
      {message ? <p style={{ color: "#1a5c3a", fontSize: 13, marginBottom: 12 }}>{message}</p> : null}
      {error ? <p style={{ color: "#d14343", fontSize: 13, marginBottom: 12 }}>{error}</p> : null}
      <button type="submit" style={{ width: "100%", padding: "14px", background: "linear-gradient(135deg, #1a5c3a, #2d9f65)", color: "#fff", border: "none", borderRadius: 10, fontSize: 16, fontWeight: 700 }}>Enviar correo</button>
      <button type="button" onClick={onBackToLogin} style={{ marginTop: 16, border: "none", background: "transparent", color: "#2d9f65", cursor: "pointer" }}>Volver al login</button>
    </form>
  );
}
```

- [ ] **Step 5: Convert the current login screen into an auth switcher**

Replace `../frontend/src/components/views/LoginScreen.jsx` with:

```javascript
"use client";

import { useState } from "react";

import AuthShell from "@/components/auth/AuthShell";
import ForgotPasswordForm from "@/components/auth/ForgotPasswordForm";
import LoginForm from "@/components/auth/LoginForm";
import RegisterForm from "@/components/auth/RegisterForm";

export default function LoginScreen() {
  const [mode, setMode] = useState("login");

  if (mode === "register") {
    return (
      <AuthShell title="Create Account" subtitle="Regístrate para comenzar">
        <RegisterForm onBackToLogin={() => setMode("login")} />
      </AuthShell>
    );
  }

  if (mode === "forgot-password") {
    return (
      <AuthShell title="Reset Password" subtitle="Te enviaremos un enlace de recuperación">
        <ForgotPasswordForm onBackToLogin={() => setMode("login")} />
      </AuthShell>
    );
  }

  return (
    <AuthShell title="Welcome Back" subtitle="Sign in to your account">
      <LoginForm
        onShowRegister={() => setMode("register")}
        onShowForgotPassword={() => setMode("forgot-password")}
      />
    </AuthShell>
  );
}
```

- [ ] **Step 6: Lint the real auth entry flow**

Run:

```bash
cd /Users/diegocarvajal/Documents/Programming/frontend
npm run lint
```

Expected: PASS

- [ ] **Step 7: Commit the auth entry flow**

Run:

```bash
cd /Users/diegocarvajal/Documents/Programming/frontend
git add src/context/AuthContext.jsx src/components/auth/AuthShell.jsx src/components/auth/LoginForm.jsx src/components/auth/RegisterForm.jsx src/components/auth/ForgotPasswordForm.jsx src/components/views/LoginScreen.jsx
git commit -m "feat: wire frontend login register and password reset request"
```

Expected: commit succeeds

### Task 8: Add Frontend Email Confirmation And Password Reset Pages

**Files:**
- Create: `../frontend/src/components/auth/AuthStatusCard.jsx`
- Create: `../frontend/src/components/auth/ResetPasswordForm.jsx`
- Create: `../frontend/src/app/auth/confirm-email/page.js`
- Create: `../frontend/src/app/auth/reset-password/page.js`
- Modify: `../frontend/src/context/AuthContext.jsx`
- Test: `../frontend npm run lint`

- [ ] **Step 1: Extend the auth provider with confirm and reset actions**

Update the relevant parts of `../frontend/src/context/AuthContext.jsx`:

```javascript
async function confirmEmail(token) {
  return apiRequest(`/auth/confirm-email?token=${encodeURIComponent(token)}`);
}

async function resetPassword(token, newPassword) {
  return apiRequest("/auth/reset-password", {
    method: "POST",
    body: { token, new_password: newPassword },
  });
}

const value = {
  status,
  user,
  accessToken: tokens.accessToken,
  refreshToken: tokens.refreshToken,
  login,
  logout,
  restoreSession,
  register,
  resendVerification,
  requestPasswordReset,
  confirmEmail,
  resetPassword,
};
```

- [ ] **Step 2: Add shared status and reset-password components**

Create `../frontend/src/components/auth/AuthStatusCard.jsx`:

```javascript
"use client";

export default function AuthStatusCard({ title, message, error = false, action }) {
  return (
    <div>
      <p style={{ color: error ? "#d14343" : "#1a5c3a", fontSize: 14, lineHeight: 1.6, marginBottom: 16 }}>
        {message}
      </p>
      {action}
    </div>
  );
}
```

Create `../frontend/src/components/auth/ResetPasswordForm.jsx`:

```javascript
"use client";

import { useState } from "react";

import { useAuth } from "@/context/AuthContext";
import { getAuthErrorMessage } from "@/lib/auth-errors";

export default function ResetPasswordForm({ token }) {
  const { resetPassword } = useAuth();
  const [newPassword, setNewPassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    setMessage("");
    setError("");
    try {
      const result = await resetPassword(token, newPassword);
      setMessage(result.message);
    } catch (submitError) {
      setError(getAuthErrorMessage(submitError, "No fue posible restablecer la contraseña."));
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <input value={newPassword} onChange={(event) => setNewPassword(event.target.value)} placeholder="Nueva contraseña" type="password" style={{ width: "100%", boxSizing: "border-box", padding: "12px 14px", border: "1.5px solid #d0e8dc", borderRadius: 10, marginBottom: 12 }} />
      {message ? <p style={{ color: "#1a5c3a", fontSize: 13, marginBottom: 12 }}>{message}</p> : null}
      {error ? <p style={{ color: "#d14343", fontSize: 13, marginBottom: 12 }}>{error}</p> : null}
      <button type="submit" style={{ width: "100%", padding: "14px", background: "linear-gradient(135deg, #1a5c3a, #2d9f65)", color: "#fff", border: "none", borderRadius: 10, fontSize: 16, fontWeight: 700 }}>Guardar nueva contraseña</button>
    </form>
  );
}
```

- [ ] **Step 3: Add the confirm-email route**

Create `../frontend/src/app/auth/confirm-email/page.js`:

```javascript
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

import AuthShell from "@/components/auth/AuthShell";
import AuthStatusCard from "@/components/auth/AuthStatusCard";
import { useAuth } from "@/context/AuthContext";

export default function ConfirmEmailPage() {
  const searchParams = useSearchParams();
  const { confirmEmail } = useAuth();
  const [state, setState] = useState({ loading: true, message: "", error: false });

  useEffect(() => {
    const token = searchParams.get("token");
    if (!token) {
      setState({ loading: false, message: "El enlace de confirmación es inválido.", error: true });
      return;
    }

    confirmEmail(token)
      .then((result) => setState({ loading: false, message: result.message, error: false }))
      .catch((error) => setState({ loading: false, message: error.message || "No fue posible confirmar el correo.", error: true }));
  }, [confirmEmail, searchParams]);

  return (
    <AuthShell title="Confirm Email" subtitle="Estamos validando tu cuenta">
      <AuthStatusCard
        title="Confirm Email"
        message={state.loading ? "Procesando..." : state.message}
        error={state.error}
        action={<Link href="/">Volver al login</Link>}
      />
    </AuthShell>
  );
}
```

- [ ] **Step 4: Add the reset-password route**

Create `../frontend/src/app/auth/reset-password/page.js`:

```javascript
"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";

import AuthShell from "@/components/auth/AuthShell";
import AuthStatusCard from "@/components/auth/AuthStatusCard";
import ResetPasswordForm from "@/components/auth/ResetPasswordForm";

export default function ResetPasswordPage() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  return (
    <AuthShell title="Reset Password" subtitle="Ingresa una nueva contraseña">
      {token ? (
        <ResetPasswordForm token={token} />
      ) : (
        <AuthStatusCard
          title="Reset Password"
          message="El enlace de recuperación es inválido."
          error
          action={<Link href="/">Volver al login</Link>}
        />
      )}
    </AuthShell>
  );
}
```

- [ ] **Step 5: Lint the auth routes**

Run:

```bash
cd /Users/diegocarvajal/Documents/Programming/frontend
npm run lint
```

Expected: PASS

- [ ] **Step 6: Commit the confirm and reset pages**

Run:

```bash
cd /Users/diegocarvajal/Documents/Programming/frontend
git add src/context/AuthContext.jsx src/components/auth/AuthStatusCard.jsx src/components/auth/ResetPasswordForm.jsx src/app/auth/confirm-email/page.js src/app/auth/reset-password/page.js
git commit -m "feat: add frontend email confirmation and password reset pages"
```

Expected: commit succeeds

### Task 9: Remove The Demo Admin Path And Run End-To-End Verification

**Files:**
- Modify: `../frontend/src/app/page.js`
- Delete or stop importing: `../frontend/src/layouts/AdminLayout.jsx`
- Test: `tests/integration/test_auth_email_links.py`
- Test: `tests/integration/test_cors.py`
- Test: `tests/integration/test_auth_flow.py`
- Test: `tests/integration/test_users_me.py`
- Test: `tests/integration/test_password_reset.py`

- [ ] **Step 1: Ensure the app no longer imports the demo admin layout**

Update `../frontend/src/app/page.js` to match this final shape:

```javascript
"use client";

import LoginScreen from "@/components/views/LoginScreen";
import UserLayout from "@/layouts/UserLayout";
import { useAuth } from "@/context/AuthContext";

export default function Page() {
  const { status } = useAuth();

  if (status === "loading") {
    return <div style={{ minHeight: "100vh", display: "grid", placeItems: "center" }}>Cargando...</div>;
  }

  if (status === "unauthenticated") {
    return <LoginScreen />;
  }

  return <UserLayout />;
}
```

- [ ] **Step 2: Build the frontend production bundle**

Run:

```bash
cd /Users/diegocarvajal/Documents/Programming/frontend
npm run build
```

Expected: PASS and Next.js creates a production build without route or client-component errors

- [ ] **Step 3: Run the backend auth integration tests**

Run:

```bash
cd /Users/diegocarvajal/Documents/Programming/PI2
pytest \
  tests/integration/test_auth_email_links.py \
  tests/integration/test_cors.py \
  tests/integration/test_auth_flow.py \
  tests/integration/test_users_me.py \
  tests/integration/test_password_reset.py \
  -v
```

Expected: PASS

- [ ] **Step 4: Run the frontend lint one final time**

Run:

```bash
cd /Users/diegocarvajal/Documents/Programming/frontend
npm run lint
```

Expected: PASS

- [ ] **Step 5: Perform the manual browser verification**

Run:

```bash
cd /Users/diegocarvajal/Documents/Programming/PI2
uvicorn app.main:app --reload
```

In a second terminal:

```bash
cd /Users/diegocarvajal/Documents/Programming/frontend
npm run dev
```

Manual checklist:

```text
1. Register a new user from http://localhost:3000
2. Open the captured verification email and confirm it lands on /auth/confirm-email
3. Confirm the frontend page calls the backend and shows a success state
4. Log in with the confirmed user
5. Refresh the browser and confirm the session restores without returning to login
6. Log out and confirm the app returns to the auth screen
7. Request a password reset
8. Open the captured reset email and confirm it lands on /auth/reset-password
9. Submit a new password and confirm login works with the new password
10. Change the access token in localStorage to force a refresh path, then reload and confirm the session is restored using /auth/refresh
```

Expected: every auth flow works end-to-end while the post-login product data remains mocked

- [ ] **Step 6: Commit the final cleanup and verification-ready state**

Run:

```bash
cd /Users/diegocarvajal/Documents/Programming/frontend
git add src/app/page.js src/layouts/AdminLayout.jsx
git commit -m "refactor: remove demo admin auth path"
```

Expected: commit succeeds if `AdminLayout.jsx` was removed or retired from the main app flow

## Self-Review

### Spec coverage

- Backend email-link requirement is covered by Task 4
- Backend CORS requirement is covered by Task 3
- Frontend API base env contract is covered by Task 1
- Login, logout, and session restore are covered by Tasks 5, 6, and 7
- Register and resend-verification are covered by Task 7
- Forgot-password and reset-password are covered by Tasks 7 and 8
- Email confirmation route is covered by Task 8
- Removal of the demo admin path is covered by Task 9
- Verification across both repos is covered by Task 9

### Placeholder scan

- No `TBD`, `TODO`, or deferred implementation placeholders remain
- Each code-bearing step includes concrete code
- Each verification step includes exact commands and expected outcomes

### Type consistency

- Frontend tokens consistently use `accessToken` and `refreshToken` in local state
- Backend payloads consistently use API field names like `refresh_token` and `new_password`
- Frontend provider method names stay consistent across Tasks 6, 7, and 8
