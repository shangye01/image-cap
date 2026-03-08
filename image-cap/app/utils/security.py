from passlib.context import CryptContext


def _build_password_context() -> CryptContext:
    """Build a password context that works even when optional backends are missing."""
    try:
        import argon2  # noqa: F401

        schemes = ["argon2", "pbkdf2_sha256"]
    except ImportError:
        schemes = ["pbkdf2_sha256"]

    return CryptContext(schemes=schemes, deprecated="auto")


pwd_context = _build_password_context()

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, hash_value: str) -> bool:
    return pwd_context.verify(password, hash_value)

