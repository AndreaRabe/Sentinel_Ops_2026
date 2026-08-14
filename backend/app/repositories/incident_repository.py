"""Acces donnees pur sur les incidents."""

import uuid
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import IncidentSeverity, IncidentStatus
from app.models.incident import Incident, IncidentAction, IncidentAttachment
from app.schemas.common import Pagination


async def get_by_id(db: AsyncSession, incident_id: uuid.UUID) -> Incident | None:
    result = await db.execute(
        select(Incident).where(Incident.id == incident_id, Incident.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def next_reference(db: AsyncSession, year: int) -> str:
    """Reference lisible INC-<annee>-<sequence>, unique par annee.

    Le compteur est derive du nombre de references existantes pour l'annee ;
    la contrainte d'unicite en base reste le garde-fou en cas de course, et
    l'echelle du projet (quelques incidents par jour, un seul worker) rend le
    conflit improbable.
    """
    prefix = f"INC-{year}-"
    result = await db.execute(
        select(func.count()).select_from(Incident).where(Incident.reference.like(f"{prefix}%"))
    )
    return f"{prefix}{int(result.scalar_one()) + 1:04d}"


async def search(
    db: AsyncSession,
    pagination: Pagination,
    *,
    site_ids: set[uuid.UUID] | None = None,
    statuses: list[IncidentStatus] | None = None,
    severities: list[IncidentSeverity] | None = None,
    reported_by_id: uuid.UUID | None = None,
    occurred_after: datetime | None = None,
    occurred_before: datetime | None = None,
    query_text: str | None = None,
) -> tuple[list[Incident], int]:
    query = select(Incident).where(Incident.deleted_at.is_(None))
    if site_ids is not None:
        query = query.where(Incident.site_id.in_(site_ids))
    if statuses:
        query = query.where(Incident.status.in_(statuses))
    if severities:
        query = query.where(Incident.severity.in_(severities))
    if reported_by_id:
        query = query.where(Incident.reported_by_id == reported_by_id)
    if occurred_after:
        query = query.where(Incident.occurred_at >= occurred_after)
    if occurred_before:
        query = query.where(Incident.occurred_at < occurred_before)
    if query_text:
        pattern = f"%{query_text.lower()}%"
        query = query.where(
            or_(
                func.lower(Incident.title).like(pattern),
                func.lower(Incident.description).like(pattern),
                func.lower(Incident.reference).like(pattern),
            )
        )

    total = int(
        (
            await db.execute(select(func.count()).select_from(query.order_by(None).subquery()))
        ).scalar_one()
    )
    result = await db.execute(
        query.order_by(Incident.occurred_at.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    )
    return list(result.scalars().all()), total


async def create(db: AsyncSession, **fields) -> Incident:
    incident = Incident(**fields)
    db.add(incident)
    await db.flush()
    return incident


async def update_fields(db: AsyncSession, incident: Incident, **fields) -> Incident:
    for key, value in fields.items():
        setattr(incident, key, value)
    await db.flush()
    return incident


async def soft_delete(db: AsyncSession, incident: Incident) -> None:
    incident.deleted_at = func.now()
    await db.flush()


async def add_action(
    db: AsyncSession,
    incident_id: uuid.UUID,
    author_id: uuid.UUID | None,
    action_type,
    body: str,
) -> IncidentAction:
    action = IncidentAction(
        incident_id=incident_id, author_id=author_id, action_type=action_type, body=body
    )
    db.add(action)
    await db.flush()
    return action


async def list_actions(db: AsyncSession, incident_id: uuid.UUID) -> list[IncidentAction]:
    result = await db.execute(
        select(IncidentAction)
        .where(IncidentAction.incident_id == incident_id)
        .order_by(IncidentAction.created_at)
    )
    return list(result.scalars().all())


async def count_by_severity(
    db: AsyncSession, site_ids: set[uuid.UUID] | None, *, open_only: bool = True
) -> dict[str, int]:
    query = select(Incident.severity, func.count()).where(Incident.deleted_at.is_(None))
    if site_ids is not None:
        query = query.where(Incident.site_id.in_(site_ids))
    if open_only:
        query = query.where(Incident.status.in_([IncidentStatus.OPEN, IncidentStatus.IN_PROGRESS]))
    result = await db.execute(query.group_by(Incident.severity))
    return {str(severity): int(count) for severity, count in result.all()}


async def list_for_period(
    db: AsyncSession,
    start: datetime,
    end: datetime,
    site_ids: set[uuid.UUID] | None,
) -> list[Incident]:
    query = select(Incident).where(
        Incident.deleted_at.is_(None),
        Incident.occurred_at >= start,
        Incident.occurred_at < end,
    )
    if site_ids is not None:
        query = query.where(Incident.site_id.in_(site_ids))
    result = await db.execute(query.order_by(Incident.occurred_at))
    return list(result.scalars().all())


# ------------------------------------------------------------ pieces jointes


async def add_attachment(db: AsyncSession, **fields) -> IncidentAttachment:
    attachment = IncidentAttachment(**fields)
    db.add(attachment)
    await db.flush()
    return attachment


async def get_attachment(db: AsyncSession, attachment_id: uuid.UUID) -> IncidentAttachment | None:
    return await db.get(IncidentAttachment, attachment_id)


async def list_attachments(db: AsyncSession, incident_id: uuid.UUID) -> list[IncidentAttachment]:
    result = await db.execute(
        select(IncidentAttachment)
        .where(IncidentAttachment.incident_id == incident_id)
        .order_by(IncidentAttachment.created_at)
    )
    return list(result.scalars().all())


async def delete_attachment(db: AsyncSession, attachment: IncidentAttachment) -> None:
    await db.delete(attachment)
    await db.flush()
