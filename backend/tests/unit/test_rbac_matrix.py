"""Matrice RBAC : ce que chaque role peut et - surtout - ne peut PAS faire.

Ces tests figent les decisions du cahier des charges (section 3). Une
modification volontaire de la matrice doit casser ces tests : c'est le signal
qu'une migration versionnee doit accompagner le changement.
"""

import pytest
from fastapi import HTTPException

from app.core.permissions import require_permission
from app.core.rbac_matrix import (
    PERMISSION_DESCRIPTIONS,
    ROLE_DESCRIPTIONS,
    ROLE_PERMISSIONS,
    SUPER_ADMIN_ONLY_PERMISSIONS,
    all_permission_codes,
)

ROLES = ("super_admin", "responsable", "chef_equipe", "agent")


def _payload_for(role: str) -> dict:
    return {"sub": "u1", "role": role, "perms": sorted(ROLE_PERMISSIONS[role])}


def _allows(role: str, permission: str) -> bool:
    try:
        require_permission(permission)(_payload_for(role))
        return True
    except HTTPException:
        return False


def test_all_roles_are_described():
    assert set(ROLE_PERMISSIONS) == set(ROLES)
    assert set(ROLE_DESCRIPTIONS) == set(ROLES)


def test_every_permission_has_a_description():
    missing = all_permission_codes() - set(PERMISSION_DESCRIPTIONS)
    assert missing == set(), f"Permissions sans description : {sorted(missing)}"


def test_wildcard_is_not_a_real_permission_code():
    """Le joker "*" est un mecanisme d'evaluation, pas une permission a decrire."""
    assert "*" not in all_permission_codes()


def test_super_admin_can_do_everything():
    for permission in sorted(all_permission_codes()):
        assert _allows("super_admin", permission), permission


@pytest.mark.parametrize("role", ["responsable", "chef_equipe", "agent"])
@pytest.mark.parametrize("permission", sorted(SUPER_ADMIN_ONLY_PERMISSIONS))
def test_reserved_permissions_are_super_admin_only(role, permission):
    assert not _allows(role, permission)


@pytest.mark.parametrize(
    ("role", "permission"),
    [
        # Responsable : vue centrale, gestion des comptes, rapports et audits.
        ("responsable", "audit:read"),
        ("responsable", "report:export"),
        ("responsable", "user:create"),
        ("responsable", "task:delete"),
        # Chef d'equipe : taches, planning et incidents de ses sites.
        ("chef_equipe", "task:create"),
        ("chef_equipe", "task:assign"),
        ("chef_equipe", "incident:resolve"),
        ("chef_equipe", "planning:read"),
        # Agent : execution et declaration.
        ("agent", "task:read"),
        ("agent", "task:update_own_status"),
        ("agent", "incident:create"),
    ],
)
def test_role_has_expected_permission(role, permission):
    assert _allows(role, permission)


@pytest.mark.parametrize(
    ("role", "permission"),
    [
        # Le Responsable ne touche ni aux roles ni aux parametres systeme.
        ("responsable", "role:update"),
        ("responsable", "settings:update"),
        # Le chef d'equipe ne gere pas les comptes et ne lit pas l'audit.
        ("chef_equipe", "user:create"),
        ("chef_equipe", "user:deactivate"),
        ("chef_equipe", "audit:read"),
        ("chef_equipe", "report:export"),
        ("chef_equipe", "site:create"),
        # L'agent execute : il ne cree, n'assigne ni ne supprime de tache.
        ("agent", "task:create"),
        ("agent", "task:assign"),
        ("agent", "task:update"),
        ("agent", "task:delete"),
        ("agent", "incident:resolve"),
        ("agent", "audit:read"),
        ("agent", "report:read"),
        ("agent", "user:read"),
    ],
)
def test_role_lacks_permission(role, permission):
    assert not _allows(role, permission)


def test_only_agents_hold_the_restricted_status_permission():
    """task:update_own_status est le pendant restreint de task:update."""
    for role in ROLES:
        if role == "agent":
            continue
        assert "task:update_own_status" not in ROLE_PERMISSIONS[role]


def test_no_role_can_write_the_audit_log():
    """audit_logs est append-only : aucune permission d'ecriture ne doit exister."""
    forbidden = {code for code in all_permission_codes() if code.startswith("audit:")}
    assert forbidden == {"audit:read"}
