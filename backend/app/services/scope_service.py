"""Resolution du perimetre multi-site d'un utilisateur (ABAC).

Fait le pont entre les predicats purs de core/scope.py et les donnees
(`user_sites`). Tout service manipulant une ressource rattachee a un site doit
passer par ici - c'est le point unique ou l'on decide "cet utilisateur a-t-il
le droit de voir/toucher CETTE ressource ?".
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import scope
from app.models.user import User
from app.repositories import site_repository


async def get_user_site_ids(db: AsyncSession, user: User) -> set[uuid.UUID]:
    return await site_repository.get_site_ids_for_user(db, user.id)


async def visible_site_ids(db: AsyncSession, user: User) -> set[uuid.UUID] | None:
    """Filtre site a appliquer aux requetes de liste. None = aucun filtre (portee globale)."""
    if scope.has_global_scope(user.role.name):
        return None
    return await get_user_site_ids(db, user)


async def assert_site_allowed(
    db: AsyncSession,
    user: User,
    site_id: uuid.UUID | None,
    message: str = "Cette ressource ne fait pas partie de vos sites.",
) -> None:
    if scope.has_global_scope(user.role.name):
        return
    user_site_ids = await get_user_site_ids(db, user)
    scope.assert_site_in_scope(user.role.name, user_site_ids, site_id, message)


async def assert_sites_allowed(db: AsyncSession, user: User, site_ids: set[uuid.UUID]) -> None:
    if scope.has_global_scope(user.role.name):
        return
    user_site_ids = await get_user_site_ids(db, user)
    for site_id in site_ids:
        scope.assert_site_in_scope(user.role.name, user_site_ids, site_id)
