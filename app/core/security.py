from passlib.context import CryptContext
from passlib.exc import UnknownHashError


_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return _pwd_context.verify(password, hashed_password)
    except (UnknownHashError, ValueError):
        return False


__all__ = ["hash_password", "verify_password"]
