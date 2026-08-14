"""Notifications in-app de l'utilisateur connecte.

Toutes les routes sont implicitement limitees a l'appelant : aucune ne prend
d'identifiant d'utilisateur en parametre, il n'y a donc pas de fuite possible
vers les notifications d'un tiers.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permissions import require_permission
from app.db.session import get_db
from app.models.enums import NotificationType
from app.models.user import User
from app.schemas.common import Page, Pagination, pagination_params
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: NotificationType
    title: str
    body: str | None
    resource_type: str | None
    resource_id: str | None
    read_at: datetime | None
    created_at: datetime


class MarkReadRequest(BaseModel):
    notification_ids: list[uuid.UUID] | None = None


class UnreadCount(BaseModel):
    unread: int


@router.get(
    "",
    response_model=Page[NotificationRead],
    dependencies=[Depends(require_permission("notification:read"))],
)
async def list_notifications(
    unread_only: bool = Query(False),
    pagination: Pagination = Depends(pagination_params),
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Page[NotificationRead]:
    notifications, total = await notification_service.list_for_user(
        db, actor, pagination, unread_only=unread_only
    )
    return Page.build(
        [NotificationRead.model_validate(item) for item in notifications], total, pagination
    )


@router.get(
    "/unread-count",
    response_model=UnreadCount,
    dependencies=[Depends(require_permission("notification:read"))],
)
async def unread_count(
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UnreadCount:
    return UnreadCount(unread=await notification_service.count_unread(db, actor))


@router.post(
    "/mark-read",
    response_model=UnreadCount,
    dependencies=[Depends(require_permission("notification:read"))],
)
async def mark_read(
    payload: MarkReadRequest,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UnreadCount:
    """Marque comme lues les notifications citees, ou toutes si la liste est absente."""
    await notification_service.mark_read(db, actor, payload.notification_ids)
    return UnreadCount(unread=await notification_service.count_unread(db, actor))
