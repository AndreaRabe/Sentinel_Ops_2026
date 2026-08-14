"""Notifications in-app.

Pas d'appel a audit_service ici : une notification n'est pas une mutation de
donnee sensible, c'est une consequence d'une mutation deja auditee par le
service appelant (assignation d'une tache, declaration d'incident...).

Ces fonctions ne committent pas : elles s'inscrivent dans la transaction du
service metier appelant, pour qu'une notification ne survive jamais a une
operation qui a echoue.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import NotificationType
from app.models.user import User
from app.repositories import notification_repository
from app.schemas.common import Pagination


async def notify(
    db: AsyncSession,
    user_ids: set[uuid.UUID],
    *,
    type_: NotificationType,
    title: str,
    body: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    exclude_user_id: uuid.UUID | None = None,
) -> None:
    # On ne notifie jamais l'auteur de sa propre action : il vient de la faire.
    targets = {uid for uid in user_ids if uid != exclude_user_id}
    if not targets:
        return
    await notification_repository.create_many(
        db,
        targets,
        type_=type_,
        title=title,
        body=body,
        resource_type=resource_type,
        resource_id=resource_id,
    )


async def list_for_user(
    db: AsyncSession, user: User, pagination: Pagination, *, unread_only: bool = False
):
    return await notification_repository.search(db, user.id, pagination, unread_only=unread_only)


async def count_unread(db: AsyncSession, user: User) -> int:
    return await notification_repository.count_unread(db, user.id)


async def mark_read(db: AsyncSession, user: User, notification_ids: list[uuid.UUID] | None) -> int:
    count = await notification_repository.mark_read(db, user.id, notification_ids)
    await db.commit()
    return count
