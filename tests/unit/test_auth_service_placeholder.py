from app.services.auth_service import AuthService


def test_auth_service_class_exists():
    service = AuthService(session=None)
    assert service is not None
