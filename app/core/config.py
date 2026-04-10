import json
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", enable_decoding=False)

    app_name: str = "Auth Platform API"
    environment: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    frontend_base_url: str = Field(default="http://localhost:3000", alias="FRONTEND_BASE_URL")
    backend_cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        alias="BACKEND_CORS_ORIGINS",
    )
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
            normalized = value.strip()
            if not normalized:
                return []

            if normalized.startswith("["):
                try:
                    parsed = json.loads(normalized)
                except json.JSONDecodeError as exc:
                    raise ValueError("BACKEND_CORS_ORIGINS must be a valid JSON array or comma-separated string") from exc

                if not isinstance(parsed, list):
                    raise ValueError("BACKEND_CORS_ORIGINS JSON input must decode to a list")

                normalized_origins: list[str] = []
                for origin in parsed:
                    if not isinstance(origin, str):
                        raise ValueError("BACKEND_CORS_ORIGINS entries must be strings")

                    stripped_origin = origin.strip()
                    if stripped_origin:
                        normalized_origins.append(stripped_origin)

                return normalized_origins

            return [origin.strip() for origin in normalized.split(",") if origin.strip()]
        return value


class _LazySettings:
    def __init__(self) -> None:
        self._instance: Settings | None = None

    def _get_instance(self) -> Settings:
        if self._instance is None:
            self._instance = Settings()
        return self._instance

    def __getattr__(self, name: str) -> object:
        return getattr(self._get_instance(), name)

    def __repr__(self) -> str:
        if self._instance is None:
            return "<LazySettings pending initialization>"
        return repr(self._instance)


settings = _LazySettings()

__all__ = ["Settings", "settings"]
