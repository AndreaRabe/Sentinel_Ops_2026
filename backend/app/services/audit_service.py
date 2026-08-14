"""Service d'audit - point d'entree unique pour ecrire dans audit_logs (append-only).

Chaque service metier declenchant une mutation sensible doit appeler
log_action(...) explicitement (voir CLAUDE.md - Conventions de code).
"""

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.repositories import audit_repository
from app.schemas.common import Pagination


async def log_action(
    db: AsyncSession,
    *,
    actor_user_id: uuid.UUID | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
) -> None:
    await audit_repository.create(
        db,
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
    )


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
    """Consultation du journal.

    Volontairement sans filtrage par site : l'audit n'est accessible qu'aux
    porteurs de audit:read (Super Admin et Responsable), qui ont tous les deux
    une portee globale. Y ajouter un scope donnerait une vue partielle de la
    conformite, ce qui irait contre l'engagement de retention.
    """
    return await audit_repository.search(
        db,
        pagination,
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        created_after=created_after,
        created_before=created_before,
    )


async def list_actions(db: AsyncSession) -> list[str]:
    return await audit_repository.distinct_actions(db)


async def count_failed_logins(db: AsyncSession, email: str, since: datetime) -> int:
    return await audit_repository.count_failed_logins(db, email, since)
