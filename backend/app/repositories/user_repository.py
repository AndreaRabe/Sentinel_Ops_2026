"""Acces donnees pur sur les utilisateurs - aucune regle metier ici."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await db.get(User, user_id)


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
