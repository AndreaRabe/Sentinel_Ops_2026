"""Module Taches : CRUD, machine a etats, assignations, checklist, dependances.

Les vues Kanban et Backlog du frontend consomment toutes les deux `GET /tasks`
avec des filtres differents : ce sont deux lectures des memes donnees, pas deux
modeles (cahier des charges section 2).
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip, get_current_user
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.permissions import get_current_user_payload, require_permission
from app.db.session import get_db
from app.models.enums import TaskPriority, TaskStatus
from app.models.task import Task
from app.models.user import User
from app.repositories import task_repository
from app.schemas.common import Page, Pagination, pagination_params
from app.schemas.task import (
    AttachmentRead,
    ChecklistItemToggle,
    TaskAssignmentUpdate,
    TaskCommentCreate,
    TaskCommentRead,
    TaskCreate,
    TaskDependencyCreate,
    TaskRead,
    TaskStatusHistoryRead,
    TaskStatusUpdate,
    TaskUpdate,
)
from app.services import attachment_service, task_service

router = APIRouter(prefix="/tasks", tags=["taches"])


def _to_read(task: Task) -> TaskRead:
    return TaskRead.from_task(task, is_overdue=task_service.is_overdue(task))


@router.get(
    "", response_model=Page[TaskRead], dependencies=[Depends(require_permission("task:read"))]
)
async def list_tasks(
    status: list[TaskStatus] | None = Query(None),
    priority: list[TaskPriority] | None = Query(None),
    assignee_id: uuid.UUID | None = Query(None),
    mine: bool = Query(False, description="Restreindre a mes propres taches assignees."),
    site_id: uuid.UUID | None = Query(None),
    due_before: datetime | None = Query(None),
    due_after: datetime | None = Query(None),
    q: str | None = Query(None),
    pagination: Pagination = Depends(pagination_params),
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Page[TaskRead]:
    tasks, total = await task_service.list_tasks(
        db,
        actor,
        pagination,
        statuses=status,
        priorities=priority,
        assignee_id=assignee_id,
        mine_only=mine,
        site_id=site_id,
        due_before=due_before,
        due_after=due_after,
        query_text=q,
    )
    return Page.build([_to_read(task) for task in tasks], total, pagination)


@router.get(
    "/{task_id}", response_model=TaskRead, dependencies=[Depends(require_permission("task:read"))]
)
async def get_task(
    task_id: uuid.UUID,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskRead:
    return _to_read(await task_service.get_task(db, actor, task_id))


@router.post(
    "",
    response_model=TaskRead,
    status_code=201,
    dependencies=[Depends(require_permission("task:create"))],
)
async def create_task(
    payload: TaskCreate,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ip_address: str | None = Depends(get_client_ip),
) -> TaskRead:
    task = await task_service.create_task(
        db,
        actor,
        title=payload.title,
        description=payload.description,
        site_id=payload.site_id,
        priority=payload.priority,
        due_at=payload.due_at,
        estimated_minutes=payload.estimated_minutes,
        assignee_ids=payload.assignee_ids,
        checklist_labels=payload.checklist_labels,
        template_id=payload.template_id,
        ip_address=ip_address,
    )
    return _to_read(task)


@router.patch(
    "/{task_id}",
    response_model=TaskRead,
    dependencies=[Depends(require_permission("task:update"))],
)
async def update_task(
    task_id: uuid.UUID,
    payload: TaskUpdate,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ip_address: str | None = Depends(get_client_ip),
) -> TaskRead:
    task = await task_service.update_task(
        db,
        actor,
        task_id,
        fields=payload.model_dump(exclude={"checklist_labels"}, exclude_unset=True),
        checklist_labels=payload.checklist_labels,
        ip_address=ip_address,
    )
    return _to_read(task)


@router.put("/{task_id}/status", response_model=TaskRead)
async def change_status(
    task_id: uuid.UUID,
    payload: TaskStatusUpdate,
    actor: User = Depends(get_current_user),
    token_payload: dict = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_db),
    ip_address: str | None = Depends(get_client_ip),
) -> TaskRead:
    """Transition de statut.

    Pas de `require_permission` fige ici : la route est ouverte aux porteurs de
    task:update comme a ceux de task:update_own_status, et c'est le service qui
    tranche selon les permissions effectives et l'assignation.
    """
    permissions = set(token_payload.get("perms", []))
    if not permissions & {"*", "task:update", "task:update_own_status"}:
        raise ForbiddenError("Permission insuffisante pour changer le statut d'une tache.")

    task = await task_service.change_status(
        db,
        actor,
        task_id,
        payload.status,
        comment=payload.comment,
        postponed_until=payload.postponed_until,
        actor_permissions=permissions,
        ip_address=ip_address,
    )
    return _to_read(task)


@router.put(
    "/{task_id}/assignees",
    response_model=TaskRead,
    dependencies=[Depends(require_permission("task:assign"))],
)
async def set_assignees(
    task_id: uuid.UUID,
    payload: TaskAssignmentUpdate,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ip_address: str | None = Depends(get_client_ip),
) -> TaskRead:
    task = await task_service.set_assignees(db, actor, task_id, payload.assignee_ids, ip_address)
    return _to_read(task)


@router.delete(
    "/{task_id}", status_code=204, dependencies=[Depends(require_permission("task:delete"))]
)
async def delete_task(
    task_id: uuid.UUID,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ip_address: str | None = Depends(get_client_ip),
) -> None:
    await task_service.delete_task(db, actor, task_id, ip_address)


# ------------------------------------------------------------- commentaires


@router.get(
    "/{task_id}/comments",
    response_model=list[TaskCommentRead],
    dependencies=[Depends(require_permission("task:read"))],
)
async def list_comments(
    task_id: uuid.UUID,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TaskCommentRead]:
    comments = await task_service.list_comments(db, actor, task_id)
    return [TaskCommentRead.model_validate(comment) for comment in comments]


@router.post(
    "/{task_id}/comments",
    response_model=TaskCommentRead,
    status_code=201,
    dependencies=[Depends(require_permission("task:comment"))],
)
async def add_comment(
    task_id: uuid.UUID,
    payload: TaskCommentCreate,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ip_address: str | None = Depends(get_client_ip),
) -> TaskCommentRead:
    comment = await task_service.add_comment(db, actor, task_id, payload.body, ip_address)
    return TaskCommentRead.model_validate(comment)


# ---------------------------------------------------------------- checklist


@router.put(
    "/{task_id}/checklist/{item_id}",
    response_model=TaskRead,
    dependencies=[Depends(require_permission("task:read"))],
)
async def toggle_checklist_item(
    task_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: ChecklistItemToggle,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ip_address: str | None = Depends(get_client_ip),
) -> TaskRead:
    """Cocher un element est un acte d'execution : accessible a tout lecteur de la tache."""
    task = await task_service.toggle_checklist_item(
        db, actor, task_id, item_id, payload.is_done, ip_address
    )
    return _to_read(task)


# -------------------------------------------------------------- dependances


@router.get(
    "/{task_id}/dependencies",
    response_model=list[uuid.UUID],
    dependencies=[Depends(require_permission("task:read"))],
)
async def list_dependencies(
    task_id: uuid.UUID,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[uuid.UUID]:
    return await task_service.list_dependencies(db, actor, task_id)


@router.post(
    "/{task_id}/dependencies",
    status_code=204,
    dependencies=[Depends(require_permission("task:update"))],
)
async def add_dependency(
    task_id: uuid.UUID,
    payload: TaskDependencyCreate,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ip_address: str | None = Depends(get_client_ip),
) -> None:
    await task_service.add_dependency(db, actor, task_id, payload.depends_on_task_id, ip_address)


@router.delete(
    "/{task_id}/dependencies/{depends_on_task_id}",
    status_code=204,
    dependencies=[Depends(require_permission("task:update"))],
)
async def remove_dependency(
    task_id: uuid.UUID,
    depends_on_task_id: uuid.UUID,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ip_address: str | None = Depends(get_client_ip),
) -> None:
    await task_service.remove_dependency(db, actor, task_id, depends_on_task_id, ip_address)


# --------------------------------------------------------------- historique


@router.get(
    "/{task_id}/history",
    response_model=list[TaskStatusHistoryRead],
    dependencies=[Depends(require_permission("task:read"))],
)
async def list_history(
    task_id: uuid.UUID,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TaskStatusHistoryRead]:
    history = await task_service.list_history(db, actor, task_id)
    return [TaskStatusHistoryRead.model_validate(entry) for entry in history]


# ------------------------------------------------------------ pieces jointes


@router.get(
    "/{task_id}/attachments",
    response_model=list[AttachmentRead],
    dependencies=[Depends(require_permission("task:read"))],
)
async def list_attachments(
    task_id: uuid.UUID,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AttachmentRead]:
    await task_service.get_task(db, actor, task_id)
    attachments = await task_repository.list_attachments(db, task_id)
    return [AttachmentRead.model_validate(attachment) for attachment in attachments]


@router.post(
    "/{task_id}/attachments",
    response_model=AttachmentRead,
    status_code=201,
    dependencies=[Depends(require_permission("task:read"))],
)
async def upload_attachment(
    task_id: uuid.UUID,
    file: UploadFile = File(...),
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ip_address: str | None = Depends(get_client_ip),
) -> AttachmentRead:
    attachment = await attachment_service.attach_to_task(db, actor, task_id, file, ip_address)
    return AttachmentRead.model_validate(attachment)


@router.get(
    "/{task_id}/attachments/{attachment_id}/download",
    dependencies=[Depends(require_permission("task:read"))],
)
async def download_attachment(
    task_id: uuid.UUID,
    attachment_id: uuid.UUID,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    await task_service.get_task(db, actor, task_id)
    attachment = await task_repository.get_attachment(db, attachment_id)
    if attachment is None or attachment.task_id != task_id:
        raise NotFoundError("Piece jointe introuvable.")
    return FileResponse(
        attachment_service.file_path(attachment.stored_name),
        media_type=attachment.content_type,
        filename=attachment.filename,
    )


@router.delete(
    "/{task_id}/attachments/{attachment_id}",
    status_code=204,
    dependencies=[Depends(require_permission("task:update"))],
)
async def delete_attachment(
    task_id: uuid.UUID,
    attachment_id: uuid.UUID,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ip_address: str | None = Depends(get_client_ip),
) -> None:
    await attachment_service.delete_task_attachment(db, actor, task_id, attachment_id, ip_address)
