from app.core.security import hash_password, verify_password


def test_password_hash_round_trip() -> None:
    password = "correct horse battery staple"

    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong password", hashed) is False


def test_verify_password_returns_false_for_malformed_hash() -> None:
    assert verify_password("correct horse battery staple", "not-a-valid-hash") is False
