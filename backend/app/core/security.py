"""Hash des mots de passe (Argon2id), JWT (access token) et refresh token opaque."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from zxcvbn import zxcvbn

from app.core.config import settings

_hasher = PasswordHasher()

PASSWORD_MIN_LENGTH = 12
PASSWORD_MIN_SCORE = 3  # zxcvbn : 0 (trivial) a 4 (tres robuste)


def hash_password(plain_password: str) -> str:
    return _hasher.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return _hasher.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False


def check_password_strength(password: str, user_inputs: list[str] | None = None) -> list[str]:
    """Retourne la liste des raisons de rejet, vide si le mot de passe est acceptable."""
    errors = []
    if len(password) < PASSWORD_MIN_LENGTH:
        errors.append(f"Le mot de passe doit contenir au moins {PASSWORD_MIN_LENGTH} caracteres.")
    result = zxcvbn(password, user_inputs=user_inputs or [])
    if result["score"] < PASSWORD_MIN_SCORE:
        errors.append("Le mot de passe est trop predictible.")
    return errors


def create_access_token(user_id: str, role: str, permissions: set[str]) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    payload = {
        "sub": user_id,
        "role": role,
        "perms": sorted(permissions),
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
