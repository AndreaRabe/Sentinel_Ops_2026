"""Acces donnees pur sur les roles et la matrice de permissions."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission


async def get_by_name(db: AsyncSession, name: str) -> Role | None:
    result = await db.execute(select(Role).where(Role.name == name))
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, role_id) -> Role | None:
    return await db.get(Role, role_id)


async def list_all(db: AsyncSession) -> list[Role]:
    result = await db.execute(select(Role).order_by(Role.name))
    return list(result.scalars().all())


async def list_permission_codes(db: AsyncSession) -> list[str]:
    result = await db.execute(select(Permission.code).order_by(Permission.code))
    return list(result.scalars().all())


async def get_permission_codes(db: AsyncSession, role_id) -> set[str]:
    result = await db.execute(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role_id)
    )
    return set(result.scalars().all())
