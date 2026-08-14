"""Acces donnees pur sur les refresh tokens (stockage hashe uniquement)."""

import uuid
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken


async def create(
    db: AsyncSession, user_id: uuid.UUID, token_hash: str, expires_at: datetime
) -> RefreshToken:
    token = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
    db.add(token)
    await db.flush()
    return token


async def get_valid_by_hash(db: AsyncSession, token_hash: str) -> RefreshToken | None:
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def revoke(db: AsyncSession, token: RefreshToken) -> None:
    token.revoked_at = func.now()
    await db.flush()


async def revoke_all_for_user(db: AsyncSession, user_id: uuid.UUID) -> int:
    """Coupe toutes les sessions actives d'un compte (desactivation, reset mot de passe)."""
    result = await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=func.now())
    )
    await db.flush()
    return result.rowcount or 0
