"""Modeles de taches reutilisables et recurrences RRULE."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip, get_current_user
from app.core.permissions import require_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.task import (
    TaskRead,
    TaskTemplateCreate,
    TaskTemplateRead,
    TaskTemplateUpdate,
)
from app.services import task_service, task_template_service

router = APIRouter(prefix="/task-templates", tags=["taches"])


@router.get(
    "",
    response_model=list[TaskTemplateRead],
    dependencies=[Depends(require_permission("task:read"))],
)
async def list_templates(
    include_inactive: bool = Query(False),
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TaskTemplateRead]:
    templates = await task_template_service.list_templates(
        db, actor, active_only=not include_inactive
    )
    return [TaskTemplateRead.model_validate(template) for template in templates]


@router.post(
    "",
    response_model=TaskTemplateRead,
    status_code=201,
    dependencies=[Depends(require_permission("task:template_manage"))],
)
async def create_template(
    payload: TaskTemplateCreate,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ip_address: str | None = Depends(get_client_ip),
) -> TaskTemplateRead:
    template = await task_template_service.create_template(
        db, actor, payload=payload.model_dump(), ip_address=ip_address
    )
    return TaskTemplateRead.model_validate(template)


@router.patch(
    "/{template_id}",
    response_model=TaskTemplateRead,
    dependencies=[Depends(require_permission("task:template_manage"))],
)
async def update_template(
    template_id: uuid.UUID,
    payload: TaskTemplateUpdate,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ip_address: str | None = Depends(get_client_ip),
) -> TaskTemplateRead:
    template = await task_template_service.update_template(
        db,
        actor,
        template_id,
        payload=payload.model_dump(exclude_unset=True),
        ip_address=ip_address,
    )
    return TaskTemplateRead.model_validate(template)


@router.delete(
    "/{template_id}",
    status_code=204,
    dependencies=[Depends(require_permission("task:template_delete"))],
)
async def delete_template(
    template_id: uuid.UUID,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ip_address: str | None = Depends(get_client_ip),
) -> None:
    await task_template_service.delete_template(db, actor, template_id, ip_address)


@router.post(
    "/{template_id}/instantiate",
    response_model=TaskRead,
    status_code=201,
    dependencies=[Depends(require_permission("task:create"))],
)
async def instantiate_template(
    template_id: uuid.UUID,
    due_at: datetime | None = Query(None),
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ip_address: str | None = Depends(get_client_ip),
) -> TaskRead:
    """Cree immediatement une tache a partir du modele (independant de la RRULE)."""
    task = await task_template_service.instantiate(
        db, actor, template_id, due_at=due_at, ip_address=ip_address
    )
    return TaskRead.from_task(task, is_overdue=task_service.is_overdue(task))
