"""Scope multi-site (ABAC) - la seule exception au RBAC pur.

Ces regles decident quelles ressources un utilisateur peut voir et toucher :
une erreur ici est une fuite de donnees entre sites.
"""

import uuid

import pytest

from app.core.exceptions import ForbiddenError
from app.core.scope import (
    GLOBAL_SCOPE_ROLES,
    assert_site_in_scope,
    has_global_scope,
    is_site_in_scope,
    visible_site_ids,
)

SITE_A = uuid.uuid4()
SITE_B = uuid.uuid4()


def test_global_scope_roles_match_the_specification():
    # Super Admin (global) et Responsable (vue centrale tous sites),
    # cahier des charges section 3.
    assert GLOBAL_SCOPE_ROLES == frozenset({"super_admin", "responsable"})


@pytest.mark.parametrize("role", ["super_admin", "responsable"])
def test_global_roles_see_every_site(role):
    assert has_global_scope(role)
    assert is_site_in_scope(role, set(), SITE_A)
    # None = aucun filtre applique, et surtout PAS un filtre sur un ensemble vide.
    assert visible_site_ids(role, set()) is None


@pytest.mark.parametrize("role", ["chef_equipe", "agent"])
def test_scoped_roles_only_see_their_own_sites(role):
    assert not has_global_scope(role)
    assert is_site_in_scope(role, {SITE_A}, SITE_A)
    assert not is_site_in_scope(role, {SITE_A}, SITE_B)
    assert visible_site_ids(role, {SITE_A}) == {SITE_A}


def test_chef_equipe_can_cover_several_sites():
    assert is_site_in_scope("chef_equipe", {SITE_A, SITE_B}, SITE_B)


def test_scoped_role_with_no_site_sees_nothing():
    assert not is_site_in_scope("agent", set(), SITE_A)
    assert visible_site_ids("agent", set()) == set()


def test_resource_without_site_is_hidden_from_scoped_roles():
    """Une ressource non rattachee ne doit pas fuiter vers un role scope."""
    assert not is_site_in_scope("chef_equipe", {SITE_A}, None)
    assert is_site_in_scope("responsable", set(), None)


def test_assert_raises_forbidden_out_of_scope():
    with pytest.raises(ForbiddenError):
        assert_site_in_scope("agent", {SITE_A}, SITE_B)


def test_assert_passes_in_scope():
    assert_site_in_scope("agent", {SITE_A}, SITE_A)
