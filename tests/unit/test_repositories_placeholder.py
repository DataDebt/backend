from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import app.repositories as repositories
from app.models.email_verification_token import EmailVerificationToken
from app.models.password_reset_token import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.email_verifications import EmailVerificationRepository
from app.repositories.password_resets import PasswordResetRepository
from app.repositories.refresh_tokens import RefreshTokenRepository
from app.repositories.users import UserRepository, normalize_email


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeSession:
    def __init__(self, result=None):
        self.result = result
        self.added = []
        self.flushed = 0
        self.refreshed = []
        self.executed = []

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flushed += 1

    async def refresh(self, obj):
        self.refreshed.append(obj)

    async def execute(self, statement):
        self.executed.append(statement)
        return _FakeResult(self.result)


def test_repository_exports_match_planned_contract() -> None:
    assert repositories.UserRepository is UserRepository
    assert repositories.EmailVerificationRepository is EmailVerificationRepository
    assert repositories.PasswordResetRepository is PasswordResetRepository
    assert repositories.RefreshTokenRepository is RefreshTokenRepository
    assert repositories.normalize_email is normalize_email
    assert repositories.EmailVerificationTokenRepository is EmailVerificationRepository
    assert repositories.PasswordResetTokenRepository is PasswordResetRepository


def test_normalize_email_trims_and_lowercases() -> None:
    assert normalize_email("  MiXeD@Example.Com  ") == "mixed@example.com"


async def test_user_repository_create_accepts_auth_service_fields() -> None:
    session = _FakeSession()
    repository = UserRepository(session)
    last_login_at = datetime(2026, 4, 9, tzinfo=timezone.utc)

    user = await repository.create(
        email="  MiXeD@Example.Com  ",
        username="CasePreserved",
        password_hash="hash",
        is_active=False,
        is_verified=True,
        last_login_at=last_login_at,
    )

    assert isinstance(user, User)
    assert user.email == "mixed@example.com"
    assert user.is_active is False
    assert user.is_verified is True
    assert user.last_login_at == last_login_at
    assert session.added == [user]
    assert session.flushed == 1
    assert session.refreshed == [user]


async def test_user_repository_get_by_email_returns_matching_user() -> None:
    expected = SimpleNamespace(email="mixed@example.com")
    session = _FakeSession(result=expected)
    repository = UserRepository(session)

    found = await repository.get_by_email("  MiXeD@Example.Com  ")

    assert found is expected
    assert session.executed


async def test_email_verification_repository_get_by_hash_eager_loads_user() -> None:
    expected = SimpleNamespace(
        token_hash="hash",
        user=SimpleNamespace(id=uuid4(), email="mixed@example.com"),
    )
    session = _FakeSession(result=expected)
    repository = EmailVerificationRepository(session)

    found = await repository.get_by_hash("hash")

    assert found is expected
    assert len(session.executed) == 1
    statement = session.executed[0]
    assert statement.column_descriptions[0]["entity"] is EmailVerificationToken
    assert statement._with_options, "expected eager-load options on the hash lookup"
    assert any("user" in str(option.path).lower() for option in statement._with_options)


async def test_email_verification_repository_consume_marks_token_consumed() -> None:
    token = EmailVerificationToken(
        token_hash="hash",
        user_id=uuid4(),
        expires_at=datetime(2026, 4, 10, tzinfo=timezone.utc),
    )
    session = _FakeSession()
    repository = EmailVerificationRepository(session)

    consumed = await repository.consume(token)

    assert consumed is token
    assert token.consumed_at is not None
    assert session.flushed == 1
    assert session.refreshed == [token]


async def test_email_verification_repository_consume_preserves_existing_timestamp() -> None:
    consumed_at = datetime(2026, 4, 9, 12, 0, tzinfo=timezone.utc)
    token = EmailVerificationToken(
        token_hash="hash",
        user_id=uuid4(),
        expires_at=datetime(2026, 4, 10, tzinfo=timezone.utc),
        consumed_at=consumed_at,
    )
    session = _FakeSession()
    repository = EmailVerificationRepository(session)

    consumed = await repository.consume(token)

    assert consumed is token
    assert token.consumed_at == consumed_at
    assert session.flushed == 0
    assert session.refreshed == []


async def test_refresh_token_repository_create_and_lookup_by_hash() -> None:
    expected = SimpleNamespace(token_hash="refresh-hash", user=SimpleNamespace(id=uuid4()))
    session = _FakeSession(result=expected)
    repository = RefreshTokenRepository(session)
    user_id = uuid4()
    expires_at = datetime(2026, 4, 10, tzinfo=timezone.utc)

    created = await repository.create(
        user_id=user_id,
        token_hash="refresh-hash",
        expires_at=expires_at,
    )
    found = await repository.get_by_hash("refresh-hash")

    assert isinstance(created, RefreshToken)
    assert created.user_id == user_id
    assert created.token_hash == "refresh-hash"
    assert created.expires_at == expires_at
    assert session.added == [created]
    assert session.flushed == 1
    assert session.refreshed == [created]
    assert found is expected
    assert len(session.executed) == 1


async def test_refresh_token_repository_get_by_hash_eager_loads_user() -> None:
    expected = SimpleNamespace(
        token_hash="refresh-hash",
        user=SimpleNamespace(id=uuid4(), email="mixed@example.com"),
    )
    session = _FakeSession(result=expected)
    repository = RefreshTokenRepository(session)

    found = await repository.get_by_hash("refresh-hash")

    assert found is expected
    assert len(session.executed) == 1
    statement = session.executed[0]
    assert statement.column_descriptions[0]["entity"] is RefreshToken
    assert statement._with_options, "expected eager-load options on the hash lookup"
    assert any("user" in str(option.path).lower() for option in statement._with_options)


async def test_refresh_token_repository_revoke_marks_token_revoked() -> None:
    token = RefreshToken(
        token_hash="refresh-hash",
        user_id=uuid4(),
        expires_at=datetime(2026, 4, 10, tzinfo=timezone.utc),
    )
    session = _FakeSession()
    repository = RefreshTokenRepository(session)

    revoked = await repository.revoke(token)

    assert revoked is token
    assert token.revoked_at is not None
    assert session.flushed == 1
    assert session.refreshed == [token]


async def test_refresh_token_repository_revoke_preserves_existing_timestamp() -> None:
    revoked_at = datetime(2026, 4, 9, 12, 0, tzinfo=timezone.utc)
    token = RefreshToken(
        token_hash="refresh-hash",
        user_id=uuid4(),
        expires_at=datetime(2026, 4, 10, tzinfo=timezone.utc),
        revoked_at=revoked_at,
    )
    session = _FakeSession()
    repository = RefreshTokenRepository(session)

    revoked = await repository.revoke(token)

    assert revoked is token
    assert token.revoked_at == revoked_at
    assert session.flushed == 0
    assert session.refreshed == []


async def test_password_reset_repository_create_and_lookup_by_hash() -> None:
    expected = SimpleNamespace(token_hash="reset-hash", user=SimpleNamespace(id=uuid4()))
    session = _FakeSession(result=expected)
    repository = PasswordResetRepository(session)
    user_id = uuid4()
    expires_at = datetime(2026, 4, 10, tzinfo=timezone.utc)

    created = await repository.create(
        user_id=user_id,
        token_hash="reset-hash",
        expires_at=expires_at,
    )
    found = await repository.get_by_hash("reset-hash")

    assert isinstance(created, PasswordResetToken)
    assert created.user_id == user_id
    assert created.token_hash == "reset-hash"
    assert created.expires_at == expires_at
    assert session.added == [created]
    assert session.flushed == 1
    assert session.refreshed == [created]
    assert found is expected
    assert len(session.executed) == 1


async def test_password_reset_repository_get_by_hash_eager_loads_user() -> None:
    expected = SimpleNamespace(
        token_hash="reset-hash",
        user=SimpleNamespace(id=uuid4(), email="mixed@example.com"),
    )
    session = _FakeSession(result=expected)
    repository = PasswordResetRepository(session)

    found = await repository.get_by_hash("reset-hash")

    assert found is expected
    assert len(session.executed) == 1
    statement = session.executed[0]
    assert statement.column_descriptions[0]["entity"] is PasswordResetToken
    assert statement._with_options, "expected eager-load options on the hash lookup"
    assert any("user" in str(option.path).lower() for option in statement._with_options)


async def test_password_reset_repository_consume_marks_token_consumed() -> None:
    token = PasswordResetToken(
        token_hash="reset-hash",
        user_id=uuid4(),
        expires_at=datetime(2026, 4, 10, tzinfo=timezone.utc),
    )
    session = _FakeSession()
    repository = PasswordResetRepository(session)

    consumed = await repository.consume(token)

    assert consumed is token
    assert token.consumed_at is not None
    assert session.flushed == 1
    assert session.refreshed == [token]


async def test_password_reset_repository_consume_preserves_existing_timestamp() -> None:
    consumed_at = datetime(2026, 4, 9, 12, 0, tzinfo=timezone.utc)
    token = PasswordResetToken(
        token_hash="reset-hash",
        user_id=uuid4(),
        expires_at=datetime(2026, 4, 10, tzinfo=timezone.utc),
        consumed_at=consumed_at,
    )
    session = _FakeSession()
    repository = PasswordResetRepository(session)

    consumed = await repository.consume(token)

    assert consumed is token
    assert token.consumed_at == consumed_at
    assert session.flushed == 0
    assert session.refreshed == []
