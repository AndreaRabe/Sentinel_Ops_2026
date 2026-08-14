"""Acces donnees pur sur les taches et leurs entites rattachees."""

import uuid
from datetime import datetime

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import TaskStatus
from app.models.task import (
    Task,
    TaskAssignment,
    TaskAttachment,
    TaskChecklistItem,
    TaskComment,
    TaskDependency,
    TaskStatusHistory,
)
from app.schemas.common import Pagination


async def get_by_id(db: AsyncSession, task_id: uuid.UUID) -> Task | None:
    result = await db.execute(
        select(Task)
        .options(selectinload(Task.assignments), selectinload(Task.checklist_items))
        .where(Task.id == task_id, Task.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def search(
    db: AsyncSession,
    pagination: Pagination,
    *,
    site_ids: set[uuid.UUID] | None = None,
    statuses: list[TaskStatus] | None = None,
    priorities: list[str] | None = None,
    assignee_id: uuid.UUID | None = None,
    due_before: datetime | None = None,
    due_after: datetime | None = None,
    query_text: str | None = None,
) -> tuple[list[Task], int]:
    query = (
        select(Task)
        .options(selectinload(Task.assignments), selectinload(Task.checklist_items))
        .where(Task.deleted_at.is_(None))
    )
    if site_ids is not None:
        query = query.where(Task.site_id.in_(site_ids))
    if statuses:
        query = query.where(Task.status.in_(statuses))
    if priorities:
        query = query.where(Task.priority.in_(priorities))
    if assignee_id:
        query = query.where(
            Task.id.in_(select(TaskAssignment.task_id).where(TaskAssignment.user_id == assignee_id))
        )
    if due_before:
        query = query.where(Task.due_at <= due_before)
    if due_after:
        query = query.where(Task.due_at >= due_after)
    if query_text:
        pattern = f"%{query_text.lower()}%"
        query = query.where(
            or_(
                func.lower(Task.title).like(pattern),
                func.lower(func.coalesce(Task.description, "")).like(pattern),
            )
        )

    total = int(
        (
            await db.execute(select(func.count()).select_from(query.order_by(None).subquery()))
        ).scalar_one()
    )
    result = await db.execute(
        query.order_by(Task.due_at.asc().nullslast(), Task.created_at.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    )
    return list(result.scalars().unique().all()), total


async def create(db: AsyncSession, **fields) -> Task:
    task = Task(**fields)
    db.add(task)
    await db.flush()
    return task


async def update_fields(db: AsyncSession, task: Task, **fields) -> Task:
    for key, value in fields.items():
        setattr(task, key, value)
    await db.flush()
    return task


async def soft_delete(db: AsyncSession, task: Task) -> None:
    task.deleted_at = func.now()
    await db.flush()


# ------------------------------------------------------------- assignations


async def get_assignee_ids(db: AsyncSession, task_id: uuid.UUID) -> set[uuid.UUID]:
    result = await db.execute(
        select(TaskAssignment.user_id).where(TaskAssignment.task_id == task_id)
    )
    return set(result.scalars().all())


async def set_assignees(
    db: AsyncSession,
    task_id: uuid.UUID,
    user_ids: set[uuid.UUID],
    assigned_by_id: uuid.UUID | None,
) -> None:
    await db.execute(delete(TaskAssignment).where(TaskAssignment.task_id == task_id))
    for user_id in user_ids:
        db.add(TaskAssignment(task_id=task_id, user_id=user_id, assigned_by_id=assigned_by_id))
    await db.flush()


# ---------------------------------------------------------------- checklist


async def replace_checklist(db: AsyncSession, task_id: uuid.UUID, labels: list[str]) -> None:
    await db.execute(delete(TaskChecklistItem).where(TaskChecklistItem.task_id == task_id))
    for position, label in enumerate(labels):
        db.add(TaskChecklistItem(task_id=task_id, label=label, position=position))
    await db.flush()


async def get_checklist_item(db: AsyncSession, item_id: uuid.UUID) -> TaskChecklistItem | None:
    return await db.get(TaskChecklistItem, item_id)


async def set_checklist_item_done(
    db: AsyncSession, item: TaskChecklistItem, is_done: bool, user_id: uuid.UUID
) -> TaskChecklistItem:
    item.is_done = is_done
    item.done_by_id = user_id if is_done else None
    item.done_at = func.now() if is_done else None
    await db.flush()
    return item


# ------------------------------------------------------------- commentaires


async def add_comment(
    db: AsyncSession, task_id: uuid.UUID, author_id: uuid.UUID, body: str
) -> TaskComment:
    comment = TaskComment(task_id=task_id, author_id=author_id, body=body)
    db.add(comment)
    await db.flush()
    return comment


async def list_comments(db: AsyncSession, task_id: uuid.UUID) -> list[TaskComment]:
    result = await db.execute(
        select(TaskComment)
        .where(TaskComment.task_id == task_id, TaskComment.deleted_at.is_(None))
        .order_by(TaskComment.created_at)
    )
    return list(result.scalars().all())


# -------------------------------------------------------------- dependances


async def add_dependency(
    db: AsyncSession, task_id: uuid.UUID, depends_on_task_id: uuid.UUID
) -> None:
    db.add(TaskDependency(task_id=task_id, depends_on_task_id=depends_on_task_id))
    await db.flush()


async def remove_dependency(
    db: AsyncSession, task_id: uuid.UUID, depends_on_task_id: uuid.UUID
) -> None:
    await db.execute(
        delete(TaskDependency).where(
            TaskDependency.task_id == task_id,
            TaskDependency.depends_on_task_id == depends_on_task_id,
        )
    )
    await db.flush()


async def get_dependency_ids(db: AsyncSession, task_id: uuid.UUID) -> list[uuid.UUID]:
    result = await db.execute(
        select(TaskDependency.depends_on_task_id).where(TaskDependency.task_id == task_id)
    )
    return list(result.scalars().all())


async def get_unfinished_dependencies(db: AsyncSession, task_id: uuid.UUID) -> list[Task]:
    """Dependances qui ne sont ni terminees ni annulees - bloquent le demarrage."""
    result = await db.execute(
        select(Task)
        .join(TaskDependency, TaskDependency.depends_on_task_id == Task.id)
        .where(
            TaskDependency.task_id == task_id,
            Task.deleted_at.is_(None),
            Task.status.notin_([TaskStatus.COMPLETED, TaskStatus.CANCELLED]),
        )
    )
    return list(result.scalars().all())


async def has_dependency_path(
    db: AsyncSession, from_task_id: uuid.UUID, to_task_id: uuid.UUID
) -> bool:
    """Existe-t-il deja un chemin de dependances de `from` vers `to` ?

    Sert a refuser la creation d'un cycle. Parcours en largeur cote Python :
    a l'echelle du projet (quelques centaines de taches), une CTE recursive
    serait plus lourde a maintenir qu'utile.
    """
    seen: set[uuid.UUID] = set()
    frontier = [from_task_id]
    while frontier:
        current = frontier.pop()
        if current == to_task_id:
            return True
        if current in seen:
            continue
        seen.add(current)
        frontier.extend(await get_dependency_ids(db, current))
    return False


# --------------------------------------------------------------- historique


async def add_status_history(
    db: AsyncSession,
    task_id: uuid.UUID,
    from_status: TaskStatus | None,
    to_status: TaskStatus,
    changed_by_id: uuid.UUID | None,
    comment: str | None = None,
) -> None:
    db.add(
        TaskStatusHistory(
            task_id=task_id,
            from_status=from_status,
            to_status=to_status,
            changed_by_id=changed_by_id,
            comment=comment,
        )
    )
    await db.flush()


async def list_status_history(db: AsyncSession, task_id: uuid.UUID) -> list[TaskStatusHistory]:
    result = await db.execute(
        select(TaskStatusHistory)
        .where(TaskStatusHistory.task_id == task_id)
        .order_by(TaskStatusHistory.created_at)
    )
    return list(result.scalars().all())


# ------------------------------------------------------------ pieces jointes


async def add_attachment(db: AsyncSession, **fields) -> TaskAttachment:
    attachment = TaskAttachment(**fields)
    db.add(attachment)
    await db.flush()
    return attachment


async def get_attachment(db: AsyncSession, attachment_id: uuid.UUID) -> TaskAttachment | None:
    return await db.get(TaskAttachment, attachment_id)


async def list_attachments(db: AsyncSession, task_id: uuid.UUID) -> list[TaskAttachment]:
    result = await db.execute(
        select(TaskAttachment)
        .where(TaskAttachment.task_id == task_id)
        .order_by(TaskAttachment.created_at)
    )
    return list(result.scalars().all())


async def delete_attachment(db: AsyncSession, attachment: TaskAttachment) -> None:
    await db.delete(attachment)
    await db.flush()


# ------------------------------------------------ requetes jobs / dashboard


async def list_overdue_open_tasks(db: AsyncSession, now: datetime) -> list[Task]:
    """Taches echues encore ouvertes - entree du job de detection des retards."""
    result = await db.execute(
        select(Task)
        .options(selectinload(Task.assignments))
        .where(
            Task.deleted_at.is_(None),
            Task.due_at.isnot(None),
            Task.due_at < now,
            Task.status.in_([TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS, TaskStatus.POSTPONED]),
        )
    )
    return list(result.scalars().unique().all())


async def list_due_between_open(db: AsyncSession, start: datetime, end: datetime) -> list[Task]:
    """Taches encore ouvertes dont l'echeance tombe dans l'intervalle.

    Entree du job de rappel d'echeance : contrairement a list_for_period, cette
    requete ignore les taches terminees ou annulees et charge les assignations
    (ce sont elles qu'il faut notifier).
    """
    result = await db.execute(
        select(Task)
        .options(selectinload(Task.assignments))
        .where(
            Task.deleted_at.is_(None),
            Task.due_at.isnot(None),
            Task.due_at >= start,
            Task.due_at < end,
            Task.status.in_([TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS, TaskStatus.POSTPONED]),
        )
    )
    return list(result.scalars().unique().all())


async def count_by_status(db: AsyncSession, site_ids: set[uuid.UUID] | None) -> dict[str, int]:
    query = select(Task.status, func.count()).where(Task.deleted_at.is_(None))
    if site_ids is not None:
        query = query.where(Task.site_id.in_(site_ids))
    result = await db.execute(query.group_by(Task.status))
    return {str(status): int(count) for status, count in result.all()}


async def count_due_between(
    db: AsyncSession,
    start: datetime,
    end: datetime,
    site_ids: set[uuid.UUID] | None,
    assignee_id: uuid.UUID | None = None,
) -> int:
    query = (
        select(func.count())
        .select_from(Task)
        .where(
            Task.deleted_at.is_(None),
            Task.due_at >= start,
            Task.due_at < end,
            Task.status.notin_([TaskStatus.COMPLETED, TaskStatus.CANCELLED]),
        )
    )
    if site_ids is not None:
        query = query.where(Task.site_id.in_(site_ids))
    if assignee_id:
        query = query.where(
            Task.id.in_(select(TaskAssignment.task_id).where(TaskAssignment.user_id == assignee_id))
        )
    return int((await db.execute(query)).scalar_one())


async def workload_by_user(
    db: AsyncSession, site_ids: set[uuid.UUID] | None
) -> list[tuple[uuid.UUID, int]]:
    """Nombre de taches ouvertes par agent - bloc "charge de travail" du dashboard."""
    query = (
        select(TaskAssignment.user_id, func.count())
        .join(Task, Task.id == TaskAssignment.task_id)
        .where(
            Task.deleted_at.is_(None),
            Task.status.notin_([TaskStatus.COMPLETED, TaskStatus.CANCELLED]),
        )
    )
    if site_ids is not None:
        query = query.where(Task.site_id.in_(site_ids))
    result = await db.execute(query.group_by(TaskAssignment.user_id))
    return [(user_id, int(count)) for user_id, count in result.all()]


async def list_for_period(
    db: AsyncSession,
    start: datetime,
    end: datetime,
    site_ids: set[uuid.UUID] | None,
    assignee_id: uuid.UUID | None = None,
) -> list[Task]:
    """Taches d'une periode - planning et rapports."""
    query = (
        select(Task)
        .options(selectinload(Task.assignments))
        .where(Task.deleted_at.is_(None), Task.due_at >= start, Task.due_at < end)
    )
    if site_ids is not None:
        query = query.where(Task.site_id.in_(site_ids))
    if assignee_id:
        query = query.where(
            Task.id.in_(select(TaskAssignment.task_id).where(TaskAssignment.user_id == assignee_id))
        )
    result = await db.execute(query.order_by(Task.due_at))
    return list(result.scalars().unique().all())
