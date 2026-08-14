"""Consultation du journal d'audit - LECTURE SEULE STRICTE.

Aucune route d'ecriture, de modification ou de suppression n'existe ici et il
ne doit jamais en exister : `audit_logs` est append-only (retention legale de
3 ans, exigence contractuelle client - cahier des charges section 1). Une
tentative d'UPDATE/DELETE echouerait de toute facon au niveau PostgreSQL grace
au trigger pose par la migration 0001.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_permission
from app.db.session import get_db
from app.schemas.common import Page, Pagination, pagination_params
from app.services import audit_service

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_user_id: uuid.UUID | None
    action: str
    resource_type: str
    resource_id: str | None
    details: dict | None
    ip_address: str | None
    created_at: datetime


@router.get(
    "",
    response_model=Page[AuditLogRead],
    dependencies=[Depends(require_permission("audit:read"))],
)
async def list_audit_logs(
    actor_user_id: uuid.UUID | None = Query(None),
    action: str | None = Query(None, description="Prefixe d'action, ex: 'task.' ou 'auth.login'."),
    resource_type: str | None = Query(None),
    resource_id: str | None = Query(None),
    created_after: datetime | None = Query(None),
    created_before: datetime | None = Query(None),
    pagination: Pagination = Depends(pagination_params),
    db: AsyncSession = Depends(get_db),
) -> Page[AuditLogRead]:
    entries, total = await audit_service.search(
        db,
        pagination,
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        created_after=created_after,
        created_before=created_before,
    )
    return Page.build([AuditLogRead.model_validate(entry) for entry in entries], total, pagination)


@router.get(
    "/actions",
    response_model=list[str],
    dependencies=[Depends(require_permission("audit:read"))],
)
async def list_actions(db: AsyncSession = Depends(get_db)) -> list[str]:
    return await audit_service.list_actions(db)
