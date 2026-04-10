from sqlalchemy import inspect

from app.models import (
    Base,
    EmailVerificationToken,
    PasswordResetToken,
    RefreshToken,
    User,
)


def test_user_email_is_canonicalized_and_metadata_is_explicit() -> None:
    user = User(email="MiXeD@Example.com", username="CasePreserved", password_hash="hash")

    assert Base.__name__ == "Base"
    assert user.email == "mixed@example.com"
    assert user.username == "CasePreserved"
    assert User.__tablename__ == "users"
    assert User.__table__.c.email.unique is None
    assert User.__table__.c.email.index is True
    assert User.__table__.c.username.unique is True
    assert User.__table__.c.username.index is True
    assert User.__table__.c.updated_at.onupdate is not None
    assert any(
        index.unique
        and getattr(expr := next(iter(index.expressions)), "name", None) == "lower"
        and list(expr.clauses)[0] is User.__table__.c.email
        for index in User.__table__.indexes
    )


def test_token_models_have_relationships_and_query_friendly_hashes() -> None:
    user_mapper = inspect(User)

    assert user_mapper.relationships["email_verification_tokens"].back_populates == "user"
    assert user_mapper.relationships["refresh_tokens"].back_populates == "user"
    assert user_mapper.relationships["password_reset_tokens"].back_populates == "user"

    for token_model, lifecycle_field in (
        (EmailVerificationToken, "consumed_at"),
        (RefreshToken, "revoked_at"),
        (PasswordResetToken, "consumed_at"),
    ):
        token_column = token_model.__table__.c.token_hash
        user_id_fk = next(iter(token_model.__table__.c.user_id.foreign_keys))

        assert token_model.__table__.c.id.primary_key is True
        assert token_column.unique is True
        assert token_column.index is True
        assert token_model.__table__.c.created_at.nullable is False
        assert token_model.__table__.c.expires_at.nullable is False
        assert token_model.__table__.c[user_id_fk.parent.name].nullable is False
        assert user_id_fk.ondelete == "CASCADE"
        assert token_model.__table__.c[lifecycle_field].nullable is True
