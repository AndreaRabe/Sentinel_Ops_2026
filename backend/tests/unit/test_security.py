from app.core.security import (
    check_password_strength,
    create_access_token,
    decode_access_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


def test_password_hash_roundtrip():
    hashed = hash_password("Un-mot-de-passe-robuste-42!")
    assert verify_password("Un-mot-de-passe-robuste-42!", hashed)
    assert not verify_password("mauvais-mot-de-passe", hashed)


def test_check_password_strength_rejects_short_and_predictable():
    assert check_password_strength("short1") != []
    assert check_password_strength("password123456") != []


def test_check_password_strength_accepts_strong_password():
    assert check_password_strength("Xk9#vLp2!qRt7mZ") == []


def test_access_token_roundtrip_carries_permissions():
    token = create_access_token("user-123", "chef_equipe", {"task:create", "task:read"})
    payload = decode_access_token(token)
    assert payload["sub"] == "user-123"
    assert payload["role"] == "chef_equipe"
    assert set(payload["perms"]) == {"task:create", "task:read"}


def test_hash_refresh_token_is_deterministic_and_not_reversible():
    token = "opaque-secret-value"
    assert hash_refresh_token(token) == hash_refresh_token(token)
    assert hash_refresh_token(token) != token
