from app.schemas.auth import RegisterRequest


def test_register_schema_normalizes_email():
    model = RegisterRequest(username="alice", email=" Alice@Example.com ", password="secret123!")
    assert model.email == "alice@example.com"
