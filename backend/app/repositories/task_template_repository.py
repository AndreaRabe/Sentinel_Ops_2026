"""Acces donnees pur sur les modeles de taches."""

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import TaskTemplate


async def get_by_id(db: AsyncSession, template_id: uuid.UUID) -> TaskTemplate | None:
    result = await db.execute(
        select(TaskTemplate).where(
            TaskTemplate.id == template_id, TaskTemplate.deleted_at.is_(None)
        )
    )
    return result.scalar_one_or_none()


async def list_all(
    db: AsyncSession,
    *,
    site_ids: set[uuid.UUID] | None = None,
    recurring_only: bool = False,
    active_only: bool = True,
) -> list[TaskTemplate]:
    query = select(TaskTemplate).where(TaskTemplate.deleted_at.is_(None))
    if site_ids is not None:
        query = query.where(TaskTemplate.site_id.in_(site_ids))
    if recurring_only:
        query = query.where(TaskTemplate.rrule.isnot(None))
    if active_only:
        query = query.where(TaskTemplate.is_active.is_(True))
    result = await db.execute(query.order_by(TaskTemplate.name))
    return list(result.scalars().all())


async def create(db: AsyncSession, **fields) -> TaskTemplate:
    template = TaskTemplate(**fields)
    db.add(template)
    await db.flush()
    return template


async def update_fields(db: AsyncSession, template: TaskTemplate, **fields) -> TaskTemplate:
    for key, value in fields.items():
        setattr(template, key, value)
    await db.flush()
    return template


async def mark_generated(db: AsyncSession, template: TaskTemplate, generated_at: datetime) -> None:
    template.last_generated_at = generated_at
    await db.flush()


async def soft_delete(db: AsyncSession, template: TaskTemplate) -> None:
    template.deleted_at = func.now()
    template.is_active = False
    await db.flush()
