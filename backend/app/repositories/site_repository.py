"""Acces donnees pur sur les sites et l'affectation des utilisateurs aux sites."""

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.site import Site
from app.models.user_site import UserSite


async def get_by_id(db: AsyncSession, site_id: uuid.UUID) -> Site | None:
    result = await db.execute(select(Site).where(Site.id == site_id, Site.deleted_at.is_(None)))
    return result.scalar_one_or_none()


async def get_by_name(db: AsyncSession, name: str) -> Site | None:
    result = await db.execute(select(Site).where(Site.name == name, Site.deleted_at.is_(None)))
    return result.scalar_one_or_none()


async def list_all(
    db: AsyncSession,
    *,
    site_ids: set[uuid.UUID] | None = None,
    include_inactive: bool = False,
) -> list[Site]:
    query = select(Site).where(Site.deleted_at.is_(None))
    if site_ids is not None:
        query = query.where(Site.id.in_(site_ids))
    if not include_inactive:
        query = query.where(Site.is_active.is_(True))
    result = await db.execute(query.order_by(Site.name))
    return list(result.scalars().all())


async def create(db: AsyncSession, name: str) -> Site:
    site = Site(name=name)
    db.add(site)
    await db.flush()
    return site


async def update(db: AsyncSession, site: Site, **fields) -> Site:
    for key, value in fields.items():
        if value is not None:
            setattr(site, key, value)
    await db.flush()
    return site


async def soft_delete(db: AsyncSession, site: Site) -> None:
    site.deleted_at = func.now()
    site.is_active = False
    await db.flush()


async def count_active_users(db: AsyncSession, site_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count()).select_from(UserSite).where(UserSite.site_id == site_id)
    )
    return int(result.scalar_one())


# --------------------------------------------------------------- user_sites


async def get_site_ids_for_user(db: AsyncSession, user_id: uuid.UUID) -> set[uuid.UUID]:
    result = await db.execute(select(UserSite.site_id).where(UserSite.user_id == user_id))
    return set(result.scalars().all())


async def set_sites_for_user(
    db: AsyncSession, user_id: uuid.UUID, site_ids: set[uuid.UUID]
) -> None:
    await db.execute(delete(UserSite).where(UserSite.user_id == user_id))
    for site_id in site_ids:
        db.add(UserSite(user_id=user_id, site_id=site_id))
    await db.flush()


async def get_user_ids_for_sites(db: AsyncSession, site_ids: set[uuid.UUID]) -> set[uuid.UUID]:
    result = await db.execute(select(UserSite.user_id).where(UserSite.site_id.in_(site_ids)))
    return set(result.scalars().all())
