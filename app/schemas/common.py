"""Common schemas and utilities."""
from pydantic import field_validator


def normalize_email(value: str) -> str:
    """Normalize email by stripping whitespace and converting to lowercase."""
    return value.strip().lower()
