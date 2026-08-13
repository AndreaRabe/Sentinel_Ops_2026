"""Service d'audit - point d'entree unique pour ecrire dans audit_logs (append-only).

Chaque service metier declenchant une mutation sensible doit appeler
log_action(...) explicitement (voir CLAUDE.md - Conventions de code).
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import audit_repository


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
