"""Acces donnees pur sur les notifications in-app."""

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import NotificationType
from app.models.notification import Notification
from app.schemas.common import Pagination


async def create_many(
    db: AsyncSession,
    user_ids: set[uuid.UUID],
    *,
    type_: NotificationType,
    title: str,
    body: str | None,
    resource_type: str | None,
    resource_id: str | None,
) -> None:
    for user_id in user_ids:
        db.add(
            Notification(
                user_id=user_id,
                type=type_,
                title=title,
                body=body,
                resource_type=resource_type,
                resource_id=resource_id,
            )
        )
    await db.flush()


async def search(
    db: AsyncSession,
    user_id: uuid.UUID,
    pagination: Pagination,
    *,
    unread_only: bool = False,
) -> tuple[list[Notification], int]:
    query = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        query = query.where(Notification.read_at.is_(None))

    total = int(
        (
            await db.execute(select(func.count()).select_from(query.order_by(None).subquery()))
        ).scalar_one()
    )
    result = await db.execute(
        query.order_by(Notification.created_at.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    )
    return list(result.scalars().all()), total


async def count_unread(db: AsyncSession, user_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user_id, Notification.read_at.is_(None))
    )
    return int(result.scalar_one())


async def mark_read(
    db: AsyncSession, user_id: uuid.UUID, notification_ids: list[uuid.UUID] | None
) -> int:
    query = update(Notification).where(
        Notification.user_id == user_id, Notification.read_at.is_(None)
    )
    if notification_ids is not None:
        query = query.where(Notification.id.in_(notification_ids))
    result = await db.execute(query.values(read_at=func.now()))
    await db.flush()
    return result.rowcount or 0
