import pytest
from fastapi import HTTPException

from app.core.permissions import require_permission


def test_require_permission_allows_matching_permission():
    dependency = require_permission("task:create")
    payload = {"sub": "u1", "role": "chef_equipe", "perms": ["task:create", "task:read"]}
    assert dependency(payload) == payload


def test_require_permission_allows_super_admin_wildcard():
    dependency = require_permission("audit:read")
    payload = {"sub": "u1", "role": "super_admin", "perms": ["*"]}
    assert dependency(payload) == payload


def test_require_permission_rejects_missing_permission():
    dependency = require_permission("user:deactivate")
    payload = {"sub": "u1", "role": "agent", "perms": ["task:read"]}
    with pytest.raises(HTTPException) as exc_info:
        dependency(payload)
    assert exc_info.value.status_code == 403
