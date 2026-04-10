import importlib
import sys

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _import_fresh_config_module():
    sys.modules.pop("app.core.config", None)
    return importlib.import_module("app.core.config")


def test_importing_config_is_safe_without_required_env(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("REFRESH_TOKEN_SECRET", raising=False)

    module = _import_fresh_config_module()

    with pytest.raises(ValidationError):
        _ = module.settings.database_url


def test_lazy_settings_resolves_when_env_present_before_first_access(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/app")
    monkeypatch.setenv("SECRET_KEY", "super-secret")
    monkeypatch.setenv("REFRESH_TOKEN_SECRET", "refresh-secret")

    module = _import_fresh_config_module()

    assert module.settings.database_url == "postgresql+asyncpg://user:pass@localhost:5432/app"
    assert module.settings.secret_key == "super-secret"
    assert module.settings.refresh_token_secret == "refresh-secret"


def test_settings_reads_required_env_values_and_keeps_defaults(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/app")
    monkeypatch.setenv("SECRET_KEY", "super-secret")
    monkeypatch.setenv("REFRESH_TOKEN_SECRET", "refresh-secret")
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("DEBUG", raising=False)
    monkeypatch.delenv("API_V1_PREFIX", raising=False)
    monkeypatch.delenv("ACCESS_TOKEN_EXPIRE_MINUTES", raising=False)
    monkeypatch.delenv("REFRESH_TOKEN_EXPIRE_DAYS", raising=False)
    monkeypatch.delenv("VERIFICATION_TOKEN_EXPIRE_HOURS", raising=False)
    monkeypatch.delenv("PASSWORD_RESET_EXPIRE_HOURS", raising=False)
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_PORT", raising=False)
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_PASS", raising=False)
    monkeypatch.delenv("SMTP_FROM", raising=False)
    monkeypatch.delenv("SMTP_TLS", raising=False)
    monkeypatch.delenv("CAPTURE_EMAILS_TO_FILES", raising=False)

    settings = Settings()

    assert settings.database_url == "postgresql+asyncpg://user:pass@localhost:5432/app"
    assert settings.secret_key == "super-secret"
    assert settings.refresh_token_secret == "refresh-secret"
    assert settings.environment == "development"
    assert settings.debug is True
    assert settings.api_v1_prefix == "/api/v1"
    assert settings.app_name == "Auth Platform API"
    assert settings.access_token_expire_minutes == 15
    assert settings.refresh_token_expire_days == 7
    assert settings.verification_token_expire_hours == 24
    assert settings.password_reset_expire_hours == 1
    assert settings.smtp_host == ""
    assert settings.smtp_port == 587
    assert settings.smtp_user == ""
    assert settings.smtp_pass == ""
    assert settings.smtp_from == "noreply@example.com"
    assert settings.smtp_tls is True
    assert settings.capture_emails_to_files is True
