"""Acces donnees sur le journal d'audit : INSERT et SELECT uniquement.

Aucune fonction d'UPDATE ou de DELETE ne doit jamais etre ajoutee ici : la
table est append-only et protegee par un trigger PostgreSQL (migration 0001).
"""

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.schemas.common import Pagination


async def create(
    db: AsyncSession,
    *,
    actor_user_id: uuid.UUID | None,
    action: str,
    resource_type: str,
    resource_id: str | None,
    details: dict | None,
    ip_address: str | None,
) -> AuditLog:
    entry = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
    )
    db.add(entry)
    await db.flush()
    return entry


async def search(
    db: AsyncSession,
    pagination: Pagination,
    *,
    actor_user_id: uuid.UUID | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
) -> tuple[list[AuditLog], int]:
    query = select(AuditLog)
    if actor_user_id:
        query = query.where(AuditLog.actor_user_id == actor_user_id)
    if action:
        query = query.where(AuditLog.action.like(f"{action}%"))
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    if resource_id:
        query = query.where(AuditLog.resource_id == resource_id)
    if created_after:
        query = query.where(AuditLog.created_at >= created_after)
    if created_before:
        query = query.where(AuditLog.created_at < created_before)

    total = int(
        (
            await db.execute(select(func.count()).select_from(query.order_by(None).subquery()))
        ).scalar_one()
    )
    result = await db.execute(
        query.order_by(AuditLog.created_at.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    )
    return list(result.scalars().all()), total


async def count_failed_logins(db: AsyncSession, email: str, since: datetime) -> int:
    """Tentatives de connexion echouees sur un email depuis `since`.

    Lecture seule sur le journal : c'est lui qui sert de compteur pour le
    verrouillage brute-force, ce qui evite d'introduire Redis ou une table
    dediee pour une information que l'on journalise deja.
    """
    result = await db.execute(
        select(func.count())
        .select_from(AuditLog)
        .where(
            AuditLog.action == "auth.login_failed",
            AuditLog.resource_id == email,
            AuditLog.created_at >= since,
        )
    )
    return int(result.scalar_one())


async def distinct_actions(db: AsyncSession) -> list[str]:
    """Alimente le filtre "action" de l'ecran d'audit."""
    result = await db.execute(select(AuditLog.action).distinct().order_by(AuditLog.action))
    return list(result.scalars().all())
