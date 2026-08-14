"""Acces donnees pur sur les utilisateurs - aucune regle metier ici."""

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.role import Role
from app.models.user import User
from app.models.user_site import UserSite
from app.schemas.common import Pagination


async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await db.get(User, user_id)


async def get_alive_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    """Comme get_by_id mais exclut les comptes soft-deletes (usage administration)."""
    result = await db.execute(select(User).where(User.id == user_id, User.deleted_at.is_(None)))
    return result.scalar_one_or_none()


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email, User.deleted_at.is_(None)))
    return result.scalar_one_or_none()


async def update_password(db: AsyncSession, user: User, password_hash: str) -> None:
    user.password_hash = password_hash
    user.must_change_password = False
    await db.flush()


async def update_last_login(db: AsyncSession, user: User) -> None:
    user.last_login_at = func.now()
    await db.flush()


async def force_password_reset(db: AsyncSession, user: User, password_hash: str) -> None:
    """Pose un mot de passe temporaire : la prochaine connexion imposera un changement."""
    user.password_hash = password_hash
    user.must_change_password = True
    await db.flush()


# ------------------------------------------------------------ administration


async def create(
    db: AsyncSession,
    *,
    first_name: str,
    last_name: str,
    email: str,
    password_hash: str,
    role_id: uuid.UUID,
) -> User:
    user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password_hash=password_hash,
        role_id=role_id,
        must_change_password=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user, ["role"])
    return user


async def update_fields(db: AsyncSession, user: User, **fields) -> User:
    for key, value in fields.items():
        if value is not None:
            setattr(user, key, value)
    await db.flush()
    return user


async def set_active(db: AsyncSession, user: User, is_active: bool) -> User:
    user.is_active = is_active
    await db.flush()
    return user


async def soft_delete(db: AsyncSession, user: User) -> None:
    user.deleted_at = func.now()
    user.is_active = False
    await db.flush()


async def search(
    db: AsyncSession,
    pagination: Pagination,
    *,
    site_ids: set[uuid.UUID] | None = None,
    role_name: str | None = None,
    query_text: str | None = None,
    include_inactive: bool = True,
) -> tuple[list[User], int]:
    query = select(User).options(joinedload(User.role)).where(User.deleted_at.is_(None))
    if site_ids is not None:
        query = query.where(
            User.id.in_(select(UserSite.user_id).where(UserSite.site_id.in_(site_ids)))
        )
    if role_name:
        query = query.where(User.role_id.in_(select(Role.id).where(Role.name == role_name)))
    if query_text:
        pattern = f"%{query_text.lower()}%"
        query = query.where(
            or_(
                func.lower(User.first_name).like(pattern),
                func.lower(User.last_name).like(pattern),
                func.lower(User.email).like(pattern),
            )
        )
    if not include_inactive:
        query = query.where(User.is_active.is_(True))

    total = int(
        (
            await db.execute(select(func.count()).select_from(query.order_by(None).subquery()))
        ).scalar_one()
    )
    result = await db.execute(
        query.order_by(User.last_name, User.first_name)
        .offset(pagination.offset)
        .limit(pagination.page_size)
    )
    return list(result.scalars().unique().all()), total


async def get_many_by_ids(db: AsyncSession, user_ids: set[uuid.UUID]) -> list[User]:
    if not user_ids:
        return []
    result = await db.execute(select(User).where(User.id.in_(user_ids), User.deleted_at.is_(None)))
    return list(result.scalars().all())
