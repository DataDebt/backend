import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_load_frontend_base_url_and_comma_separated_cors_origins_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/app")
    monkeypatch.setenv("SECRET_KEY", "super-secret")
    monkeypatch.setenv("REFRESH_TOKEN_SECRET", "refresh-secret")
    monkeypatch.setenv("FRONTEND_BASE_URL", "https://frontend.example.com")
    monkeypatch.setenv(
        "BACKEND_CORS_ORIGINS",
        " https://frontend.example.com, , https://admin.example.com , http://localhost:3001, ",
    )

    settings = Settings()

    assert settings.frontend_base_url == "https://frontend.example.com"
    assert settings.backend_cors_origins == [
        "https://frontend.example.com",
        "https://admin.example.com",
        "http://localhost:3001",
    ]


def test_settings_load_json_array_cors_origins_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/app")
    monkeypatch.setenv("SECRET_KEY", "super-secret")
    monkeypatch.setenv("REFRESH_TOKEN_SECRET", "refresh-secret")
    monkeypatch.setenv(
        "BACKEND_CORS_ORIGINS",
        '["https://frontend.example.com", "https://admin.example.com"]',
    )

    settings = Settings()

    assert settings.backend_cors_origins == [
        "https://frontend.example.com",
        "https://admin.example.com",
    ]


@pytest.mark.parametrize(
    "cors_origins",
    [
        '[1, "https://frontend.example.com"]',
        '[null, "https://frontend.example.com"]',
    ],
)
def test_settings_rejects_non_string_json_array_cors_origins(monkeypatch, cors_origins):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/app")
    monkeypatch.setenv("SECRET_KEY", "super-secret")
    monkeypatch.setenv("REFRESH_TOKEN_SECRET", "refresh-secret")
    monkeypatch.setenv("BACKEND_CORS_ORIGINS", cors_origins)

    with pytest.raises(ValidationError):
        Settings()


def test_settings_uses_default_frontend_integration_values(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/app")
    monkeypatch.setenv("SECRET_KEY", "super-secret")
    monkeypatch.setenv("REFRESH_TOKEN_SECRET", "refresh-secret")
    monkeypatch.delenv("FRONTEND_BASE_URL", raising=False)
    monkeypatch.delenv("BACKEND_CORS_ORIGINS", raising=False)

    settings = Settings()

    assert settings.frontend_base_url == "http://localhost:3000"
    assert settings.backend_cors_origins == ["http://localhost:3000"]
