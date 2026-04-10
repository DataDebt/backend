import os

# Set required environment variables before any app modules are imported.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/testdb")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-tests")
os.environ.setdefault("REFRESH_TOKEN_SECRET", "test-refresh-secret-for-tests")
os.environ.setdefault("CAPTURE_EMAILS_TO_FILES", "false")
