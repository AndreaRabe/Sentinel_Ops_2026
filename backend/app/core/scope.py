"""Scope multi-site - l'unique exception ABAC du modele d'autorisation.

Le RBAC (voir permissions.py) repond a "ce role a-t-il le droit de faire cette
action ?". Il ne repond pas a "sur QUELLE ressource ?" : un chef d'equipe a
bien la permission task:update, mais uniquement sur les taches des sites dont
il a la charge. C'est cette seconde question que traite ce module.

Ces fonctions sont volontairement pures (aucun acces DB) : le service appelant
recupere les sites de l'utilisateur via user_site_repository puis delegue la
decision ici. Elles doivent etre appelees explicitement dans chaque service
manipulant une ressource rattachee a un site - jamais supposees (CLAUDE.md).
"""

import uuid

from app.core.exceptions import ForbiddenError

# Roles dont la portee est l'organisation entiere : aucun filtrage par site.
# Voir cahier des charges section 3 (Super Admin = global, Responsable = tous
# les sites avec vue centrale obligatoire).
GLOBAL_SCOPE_ROLES: frozenset[str] = frozenset({"super_admin", "responsable"})


def has_global_scope(role_name: str) -> bool:
    return role_name in GLOBAL_SCOPE_ROLES


def is_site_in_scope(
    role_name: str,
    user_site_ids: set[uuid.UUID],
    target_site_id: uuid.UUID | None,
) -> bool:
    """Predicat sans effet de bord - utile pour filtrer une liste sans lever."""
    if has_global_scope(role_name):
        return True
    if target_site_id is None:
        # Une ressource sans site n'est visible que des roles a portee globale :
        # un utilisateur scope ne doit jamais voir de donnee non rattachee.
        return False
    return target_site_id in user_site_ids


def assert_site_in_scope(
    role_name: str,
    user_site_ids: set[uuid.UUID],
    target_site_id: uuid.UUID | None,
    message: str = "Cette ressource ne fait pas partie de vos sites.",
) -> None:
    if not is_site_in_scope(role_name, user_site_ids, target_site_id):
        raise ForbiddenError(message)


def visible_site_ids(role_name: str, user_site_ids: set[uuid.UUID]) -> set[uuid.UUID] | None:
    """Sites sur lesquels filtrer une requete de liste.

    Retourne None pour un role a portee globale : le service ne doit alors
    appliquer AUCUN filtre site (et non un filtre sur un ensemble vide, qui
    masquerait tout).
    """
    if has_global_scope(role_name):
        return None
    return user_site_ids
