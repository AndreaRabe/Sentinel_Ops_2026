"""Regles metier des sites + audit explicite de chaque mutation."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models.site import Site
from app.models.user import User
from app.repositories import site_repository
from app.services import audit_service, scope_service


async def list_sites(db: AsyncSession, actor: User, include_inactive: bool = False) -> list[Site]:
    site_ids = await scope_service.visible_site_ids(db, actor)
    return await site_repository.list_all(db, site_ids=site_ids, include_inactive=include_inactive)


async def get_site(db: AsyncSession, actor: User, site_id: uuid.UUID) -> Site:
    site = await site_repository.get_by_id(db, site_id)
    if site is None:
        raise NotFoundError("Site introuvable.")
    await scope_service.assert_site_allowed(db, actor, site.id)
    return site


async def create_site(db: AsyncSession, actor: User, name: str, ip_address: str | None) -> Site:
    if await site_repository.get_by_name(db, name) is not None:
        raise ConflictError("Un site portant ce nom existe deja.")

    site = await site_repository.create(db, name)
    await audit_service.log_action(
        db,
        actor_user_id=actor.id,
        action="site.created",
        resource_type="site",
        resource_id=str(site.id),
        details={"name": name},
        ip_address=ip_address,
    )
    await db.commit()
    return site


async def update_site(
    db: AsyncSession,
    actor: User,
    site_id: uuid.UUID,
    *,
    name: str | None,
    is_active: bool | None,
    ip_address: str | None,
) -> Site:
    site = await get_site(db, actor, site_id)

    if name and name != site.name and await site_repository.get_by_name(db, name) is not None:
        raise ConflictError("Un site portant ce nom existe deja.")

    changes = {
        key: value
        for key, value in {"name": name, "is_active": is_active}.items()
        if value is not None and value != getattr(site, key)
    }
    if not changes:
        return site

    await site_repository.update(db, site, **changes)
    await audit_service.log_action(
        db,
        actor_user_id=actor.id,
        action="site.updated",
        resource_type="site",
        resource_id=str(site.id),
        details=changes,
        ip_address=ip_address,
    )
    await db.commit()
    return site


async def delete_site(
    db: AsyncSession, actor: User, site_id: uuid.UUID, ip_address: str | None
) -> None:
    site = await get_site(db, actor, site_id)

    # Un site encore rattache a des utilisateurs ne peut pas disparaitre : les
    # taches et incidents qui le referencent perdraient leur perimetre de scope.
    if await site_repository.count_active_users(db, site.id) > 0:
        raise BusinessRuleError(
            "Ce site est encore affecte a des utilisateurs - reaffectez-les avant suppression."
        )

    await site_repository.soft_delete(db, site)
    await audit_service.log_action(
        db,
        actor_user_id=actor.id,
        action="site.deleted",
        resource_type="site",
        resource_id=str(site.id),
        details={"name": site.name},
        ip_address=ip_address,
    )
    await db.commit()
