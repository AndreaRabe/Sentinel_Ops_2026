"""Module Incidents."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip, get_current_user
from app.core.exceptions import NotFoundError
from app.core.permissions import require_permission
from app.db.session import get_db
from app.models.enums import IncidentSeverity, IncidentStatus
from app.models.user import User
from app.repositories import incident_repository
from app.schemas.common import Page, Pagination, pagination_params
from app.schemas.incident import (
    IncidentActionCreate,
    IncidentActionRead,
    IncidentCreate,
    IncidentRead,
    IncidentResolve,
    IncidentUpdate,
)
from app.schemas.task import AttachmentRead
from app.services import attachment_service, incident_service

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get(
    "",
    response_model=Page[IncidentRead],
    dependencies=[Depends(require_permission("incident:read"))],
)
async def list_incidents(
    status: list[IncidentStatus] | None = Query(None),
    severity: list[IncidentSeverity] | None = Query(None),
    site_id: uuid.UUID | None = Query(None),
    mine: bool = Query(False, description="Restreindre aux incidents que j'ai declares."),
    occurred_after: datetime | None = Query(None),
    occurred_before: datetime | None = Query(None),
    q: str | None = Query(None),
    pagination: Pagination = Depends(pagination_params),
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Page[IncidentRead]:
    incidents, total = await incident_service.list_incidents(
        db,
        actor,
        pagination,
        statuses=status,
        severities=severity,
        site_id=site_id,
        mine_only=mine,
        occurred_after=occurred_after,
        occurred_before=occurred_before,
        query_text=q,
    )
    return Page.build(
        [IncidentRead.model_validate(incident) for incident in incidents], total, pagination
    )


@router.get(
    "/{incident_id}",
    response_model=IncidentRead,
    dependencies=[Depends(require_permission("incident:read"))],
)
async def get_incident(
    incident_id: uuid.UUID,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IncidentRead:
    incident = await incident_service.get_incident(db, actor, incident_id)
    return IncidentRead.model_validate(incident)


@router.post(
    "",
    response_model=IncidentRead,
    status_code=201,
    dependencies=[Depends(require_permission("incident:create"))],
)
async def create_incident(
    payload: IncidentCreate,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ip_address: str | None = Depends(get_client_ip),
) -> IncidentRead:
    incident = await incident_service.create_incident(
        db,
        actor,
        title=payload.title,
        description=payload.description,
        severity=payload.severity,
        site_id=payload.site_id,
        occurred_at=payload.occurred_at,
        ip_address=ip_address,
    )
    return IncidentRead.model_validate(incident)


@router.patch(
    "/{incident_id}",
    response_model=IncidentRead,
    dependencies=[Depends(require_permission("incident:update"))],
)
async def update_incident(
    incident_id: uuid.UUID,
    payload: IncidentUpdate,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ip_address: str | None = Depends(get_client_ip),
) -> IncidentRead:
    incident = await incident_service.update_incident(
        db,
        actor,
        incident_id,
        fields=payload.model_dump(exclude_unset=True),
        ip_address=ip_address,
    )
    return IncidentRead.model_validate(incident)


@router.post(
    "/{incident_id}/resolve",
    response_model=IncidentRead,
    dependencies=[Depends(require_permission("incident:resolve"))],
)
async def resolve_incident(
    incident_id: uuid.UUID,
    payload: IncidentResolve,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ip_address: str | None = Depends(get_client_ip),
) -> IncidentRead:
    incident = await incident_service.resolve_incident(
        db, actor, incident_id, payload.resolution_summary, ip_address
    )
    return IncidentRead.model_validate(incident)


@router.post(
    "/{incident_id}/close",
    response_model=IncidentRead,
    dependencies=[Depends(require_permission("incident:resolve"))],
)
async def close_incident(
    incident_id: uuid.UUID,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ip_address: str | None = Depends(get_client_ip),
) -> IncidentRead:
    incident = await incident_service.close_incident(db, actor, incident_id, ip_address)
    return IncidentRead.model_validate(incident)


@router.delete(
    "/{incident_id}",
    status_code=204,
    dependencies=[Depends(require_permission("incident:delete"))],
)
async def delete_incident(
    incident_id: uuid.UUID,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ip_address: str | None = Depends(get_client_ip),
) -> None:
    await incident_service.delete_incident(db, actor, incident_id, ip_address)


# ------------------------------------------------------------------ actions


@router.get(
    "/{incident_id}/actions",
    response_model=list[IncidentActionRead],
    dependencies=[Depends(require_permission("incident:read"))],
)
async def list_actions(
    incident_id: uuid.UUID,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[IncidentActionRead]:
    actions = await incident_service.list_actions(db, actor, incident_id)
    return [IncidentActionRead.model_validate(action) for action in actions]


@router.post(
    "/{incident_id}/actions",
    response_model=IncidentActionRead,
    status_code=201,
    dependencies=[Depends(require_permission("incident:update"))],
)
async def add_action(
    incident_id: uuid.UUID,
    payload: IncidentActionCreate,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ip_address: str | None = Depends(get_client_ip),
) -> IncidentActionRead:
    action = await incident_service.add_action(db, actor, incident_id, payload.body, ip_address)
    return IncidentActionRead.model_validate(action)


# ------------------------------------------------------------ pieces jointes


@router.get(
    "/{incident_id}/attachments",
    response_model=list[AttachmentRead],
    dependencies=[Depends(require_permission("incident:read"))],
)
async def list_attachments(
    incident_id: uuid.UUID,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AttachmentRead]:
    await incident_service.get_incident(db, actor, incident_id)
    attachments = await incident_repository.list_attachments(db, incident_id)
    return [AttachmentRead.model_validate(attachment) for attachment in attachments]


@router.post(
    "/{incident_id}/attachments",
    response_model=AttachmentRead,
    status_code=201,
    dependencies=[Depends(require_permission("incident:read"))],
)
async def upload_attachment(
    incident_id: uuid.UUID,
    file: UploadFile = File(...),
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ip_address: str | None = Depends(get_client_ip),
) -> AttachmentRead:
    attachment = await attachment_service.attach_to_incident(
        db, actor, incident_id, file, ip_address
    )
    return AttachmentRead.model_validate(attachment)


@router.get(
    "/{incident_id}/attachments/{attachment_id}/download",
    dependencies=[Depends(require_permission("incident:read"))],
)
async def download_attachment(
    incident_id: uuid.UUID,
    attachment_id: uuid.UUID,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    await incident_service.get_incident(db, actor, incident_id)
    attachment = await incident_repository.get_attachment(db, attachment_id)
    if attachment is None or attachment.incident_id != incident_id:
        raise NotFoundError("Piece jointe introuvable.")
    return FileResponse(
        attachment_service.file_path(attachment.stored_name),
        media_type=attachment.content_type,
        filename=attachment.filename,
    )


@router.delete(
    "/{incident_id}/attachments/{attachment_id}",
    status_code=204,
    dependencies=[Depends(require_permission("incident:update"))],
)
async def delete_attachment(
    incident_id: uuid.UUID,
    attachment_id: uuid.UUID,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ip_address: str | None = Depends(get_client_ip),
) -> None:
    await attachment_service.delete_incident_attachment(
        db, actor, incident_id, attachment_id, ip_address
    )
