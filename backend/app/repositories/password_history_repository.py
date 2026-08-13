"""Acces donnees pur sur l'historique des mots de passe (anti-reutilisation)."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.password_history import PasswordHistory

RECENT_HISTORY_SIZE = 5


async def add(db: AsyncSession, user_id: uuid.UUID, password_hash: str) -> None:
    db.add(PasswordHistory(user_id=user_id, password_hash=password_hash))
    await db.flush()


async def get_recent_hashes(db: AsyncSession, user_id: uuid.UUID) -> list[str]:
    result = await db.execute(
        select(PasswordHistory.password_hash)
        .where(PasswordHistory.user_id == user_id)
        .order_by(PasswordHistory.created_at.desc())
        .limit(RECENT_HISTORY_SIZE)
    )
    return list(result.scalars().all())
