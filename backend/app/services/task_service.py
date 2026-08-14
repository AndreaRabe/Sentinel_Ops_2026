"""Regles metier des taches : machine a etats, scope site, assignations, audit.

Trois verifications se cumulent sur chaque operation et ne doivent jamais etre
confondues :
1. RBAC (fait par l'endpoint via require_permission) : "ce role peut-il ?"
2. Scope site (ici, via scope_service)                : "sur cette ressource ?"
3. Machine a etats (ici, via core.task_state)         : "cette transition est-elle legale ?"
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import task_state
from app.core.exceptions import BusinessRuleError, ForbiddenError, NotFoundError
from app.models.enums import NotificationType, TaskPriority, TaskStatus
from app.models.task import Task, TaskComment, TaskStatusHistory
from app.models.user import User
from app.repositories import site_repository, task_repository, user_repository
from app.schemas.common import Pagination
from app.services import audit_service, notification_service, scope_service


def _now() -> datetime:
    return datetime.now(timezone.utc)


def is_overdue(task: Task) -> bool:
    return (
        task.due_at is not None
        and task.status not in task_state.TERMINAL_STATUSES
        and task.status != TaskStatus.LATE
        and task.due_at < _now()
    )


async def _get_task_in_scope(db: AsyncSession, actor: User, task_id: uuid.UUID) -> Task:
    task = await task_repository.get_by_id(db, task_id)
    if task is None:
        raise NotFoundError("Tache introuvable.")
    await scope_service.assert_site_allowed(db, actor, task.site_id)
    return task


async def _validate_assignees(
    db: AsyncSession, site_id: uuid.UUID, assignee_ids: set[uuid.UUID]
) -> set[uuid.UUID]:
    """Un agent ne peut etre assigne qu'a une tache d'un site qu'il couvre."""
    if not assignee_ids:
        return set()

    users = await user_repository.get_many_by_ids(db, assignee_ids)
    found_ids = {user.id for user in users}
    missing = assignee_ids - found_ids
    if missing:
        raise NotFoundError(
            f"Utilisateur(s) introuvable(s) : {', '.join(str(m) for m in missing)}."
        )

    for user in users:
        if user.role.name in {"super_admin", "responsable"}:
            continue  # portee globale : affectable partout
        user_sites = await site_repository.get_site_ids_for_user(db, user.id)
        if site_id not in user_sites:
            raise BusinessRuleError(
                f"{user.first_name} {user.last_name} n'est pas affecte au site de cette tache."
            )
    return assignee_ids


async def list_tasks(
    db: AsyncSession,
    actor: User,
    pagination: Pagination,
    *,
    statuses: list[TaskStatus] | None = None,
    priorities: list[TaskPriority] | None = None,
    assignee_id: uuid.UUID | None = None,
    mine_only: bool = False,
    site_id: uuid.UUID | None = None,
    due_before: datetime | None = None,
    due_after: datetime | None = None,
    query_text: str | None = None,
) -> tuple[list[Task], int]:
    site_ids = await scope_service.visible_site_ids(db, actor)
    if site_id is not None:
        await scope_service.assert_site_allowed(db, actor, site_id)
        site_ids = {site_id}

    return await task_repository.search(
        db,
        pagination,
        site_ids=site_ids,
        statuses=statuses,
        priorities=[p.value for p in priorities] if priorities else None,
        assignee_id=actor.id if mine_only else assignee_id,
        due_before=due_before,
        due_after=due_after,
        query_text=query_text,
    )


async def get_task(db: AsyncSession, actor: User, task_id: uuid.UUID) -> Task:
    return await _get_task_in_scope(db, actor, task_id)


async def create_task(
    db: AsyncSession,
    actor: User,
    *,
    title: str,
    description: str | None,
    site_id: uuid.UUID,
    priority: TaskPriority,
    due_at: datetime | None,
    estimated_minutes: int | None,
    assignee_ids: list[uuid.UUID],
    checklist_labels: list[str],
    template_id: uuid.UUID | None,
    ip_address: str | None,
) -> Task:
    if await site_repository.get_by_id(db, site_id) is None:
        raise NotFoundError("Site introuvable.")
    await scope_service.assert_site_allowed(db, actor, site_id)

    resolved_assignees = await _validate_assignees(db, site_id, set(assignee_ids))

    # Une tache creee avec au moins un assigne part directement en ASSIGNED :
    # DRAFT ne sert qu'aux taches preparees sans porteur identifie.
    status = TaskStatus.ASSIGNED if resolved_assignees else TaskStatus.DRAFT

    task = await task_repository.create(
        db,
        title=title,
        description=description,
        status=status,
        priority=priority,
        site_id=site_id,
        template_id=template_id,
        created_by_id=actor.id,
        due_at=due_at,
        estimated_minutes=estimated_minutes,
    )
    if resolved_assignees:
        await task_repository.set_assignees(db, task.id, resolved_assignees, actor.id)
    if checklist_labels:
        await task_repository.replace_checklist(db, task.id, checklist_labels)

    await task_repository.add_status_history(db, task.id, None, status, actor.id)
    await audit_service.log_action(
        db,
        actor_user_id=actor.id,
        action="task.created",
        resource_type="task",
        resource_id=str(task.id),
        details={"title": title, "site_id": str(site_id), "status": status},
        ip_address=ip_address,
    )
    await notification_service.notify(
        db,
        resolved_assignees,
        type_=NotificationType.TASK_ASSIGNED,
        title=f"Nouvelle tache : {title}",
        body=description,
        resource_type="task",
        resource_id=str(task.id),
        exclude_user_id=actor.id,
    )
    await db.commit()
    return await task_repository.get_by_id(db, task.id)


async def update_task(
    db: AsyncSession,
    actor: User,
    task_id: uuid.UUID,
    *,
    fields: dict,
    checklist_labels: list[str] | None,
    ip_address: str | None,
) -> Task:
    task = await _get_task_in_scope(db, actor, task_id)
    if task_state.is_terminal(task.status):
        raise BusinessRuleError("Une tache terminee ou annulee n'est plus modifiable.")

    new_site_id = fields.get("site_id")
    if new_site_id and new_site_id != task.site_id:
        if await site_repository.get_by_id(db, new_site_id) is None:
            raise NotFoundError("Site introuvable.")
        # Le demandeur doit couvrir le site de depart ET celui d'arrivee,
        # sinon il pourrait "sortir" une tache de son perimetre de controle.
        await scope_service.assert_site_allowed(db, actor, new_site_id)
        current_assignees = await task_repository.get_assignee_ids(db, task.id)
        if current_assignees:
            raise BusinessRuleError(
                "Retirez les assignations avant de deplacer la tache vers un autre site."
            )

    changes = {key: value for key, value in fields.items() if value is not None}
    if changes:
        await task_repository.update_fields(db, task, **changes)
    if checklist_labels is not None:
        await task_repository.replace_checklist(db, task.id, checklist_labels)

    if not changes and checklist_labels is None:
        return task

    await audit_service.log_action(
        db,
        actor_user_id=actor.id,
        action="task.updated",
        resource_type="task",
        resource_id=str(task.id),
        details={key: str(value) for key, value in changes.items()},
        ip_address=ip_address,
    )
    await db.commit()
    return await task_repository.get_by_id(db, task.id)


async def change_status(
    db: AsyncSession,
    actor: User,
    task_id: uuid.UUID,
    target: TaskStatus,
    *,
    comment: str | None,
    postponed_until: datetime | None,
    actor_permissions: set[str],
    ip_address: str | None,
) -> Task:
    task = await _get_task_in_scope(db, actor, task_id)

    # Un porteur de task:update_own_status (agent) ne pilote que ses propres
    # taches, et seulement vers un sous-ensemble de statuts.
    has_full_update = "*" in actor_permissions or "task:update" in actor_permissions
    if not has_full_update:
        assignees = await task_repository.get_assignee_ids(db, task.id)
        if actor.id not in assignees:
            raise ForbiddenError("Vous n'etes pas assigne a cette tache.")
        task_state.assert_agent_transition(target)

    assignee_count = len(await task_repository.get_assignee_ids(db, task.id))
    task_state.assert_transition(task.status, target, assignee_count=assignee_count)

    if target == TaskStatus.POSTPONED and postponed_until is None:
        raise BusinessRuleError("Indiquez la date de report (postponed_until).")

    if target == TaskStatus.IN_PROGRESS:
        blocking = await task_repository.get_unfinished_dependencies(db, task.id)
        if blocking:
            titles = ", ".join(dependency.title for dependency in blocking)
            raise BusinessRuleError(f"Taches prealables non terminees : {titles}.")

    previous_status = task.status
    updates: dict = {"status": target}
    if target == TaskStatus.IN_PROGRESS and task.started_at is None:
        updates["started_at"] = _now()
    if target == TaskStatus.COMPLETED:
        updates["completed_at"] = _now()
    if target == TaskStatus.POSTPONED:
        updates["postponed_until"] = postponed_until

    await task_repository.update_fields(db, task, **updates)
    await task_repository.add_status_history(
        db, task.id, previous_status, target, actor.id, comment
    )
    await audit_service.log_action(
        db,
        actor_user_id=actor.id,
        action="task.status_changed",
        resource_type="task",
        resource_id=str(task.id),
        details={"from": previous_status, "to": target, "comment": comment},
        ip_address=ip_address,
    )
    await db.commit()
    return await task_repository.get_by_id(db, task.id)


async def set_assignees(
    db: AsyncSession,
    actor: User,
    task_id: uuid.UUID,
    assignee_ids: list[uuid.UUID],
    ip_address: str | None,
) -> Task:
    task = await _get_task_in_scope(db, actor, task_id)
    if task_state.is_terminal(task.status):
        raise BusinessRuleError("Une tache terminee ou annulee ne peut plus etre reassignee.")

    resolved = await _validate_assignees(db, task.site_id, set(assignee_ids))
    previous = await task_repository.get_assignee_ids(db, task.id)
    await task_repository.set_assignees(db, task.id, resolved, actor.id)

    # Une tache DRAFT qui recoit son premier porteur bascule en ASSIGNED, et
    # inversement une tache videe de ses porteurs retourne en DRAFT.
    if resolved and task.status == TaskStatus.DRAFT:
        await task_repository.update_fields(db, task, status=TaskStatus.ASSIGNED)
        await task_repository.add_status_history(
            db, task.id, TaskStatus.DRAFT, TaskStatus.ASSIGNED, actor.id
        )
    elif not resolved and task.status == TaskStatus.ASSIGNED:
        await task_repository.update_fields(db, task, status=TaskStatus.DRAFT)
        await task_repository.add_status_history(
            db, task.id, TaskStatus.ASSIGNED, TaskStatus.DRAFT, actor.id
        )

    await audit_service.log_action(
        db,
        actor_user_id=actor.id,
        action="task.assignees_changed",
        resource_type="task",
        resource_id=str(task.id),
        details={
            "added": [str(uid) for uid in resolved - previous],
            "removed": [str(uid) for uid in previous - resolved],
        },
        ip_address=ip_address,
    )
    await notification_service.notify(
        db,
        resolved - previous,
        type_=NotificationType.TASK_ASSIGNED,
        title=f"Tache assignee : {task.title}",
        resource_type="task",
        resource_id=str(task.id),
        exclude_user_id=actor.id,
    )
    await db.commit()
    return await task_repository.get_by_id(db, task.id)


async def delete_task(
    db: AsyncSession, actor: User, task_id: uuid.UUID, ip_address: str | None
) -> None:
    task = await _get_task_in_scope(db, actor, task_id)
    await task_repository.soft_delete(db, task)
    await audit_service.log_action(
        db,
        actor_user_id=actor.id,
        action="task.deleted",
        resource_type="task",
        resource_id=str(task.id),
        details={"title": task.title},
        ip_address=ip_address,
    )
    await db.commit()


# ------------------------------------------------------------- commentaires


async def list_comments(db: AsyncSession, actor: User, task_id: uuid.UUID) -> list[TaskComment]:
    await _get_task_in_scope(db, actor, task_id)
    return await task_repository.list_comments(db, task_id)


async def add_comment(
    db: AsyncSession, actor: User, task_id: uuid.UUID, body: str, ip_address: str | None
) -> TaskComment:
    task = await _get_task_in_scope(db, actor, task_id)
    comment = await task_repository.add_comment(db, task.id, actor.id, body)

    await audit_service.log_action(
        db,
        actor_user_id=actor.id,
        action="task.commented",
        resource_type="task",
        resource_id=str(task.id),
        ip_address=ip_address,
    )
    assignees = await task_repository.get_assignee_ids(db, task.id)
    await notification_service.notify(
        db,
        assignees,
        type_=NotificationType.TASK_COMMENTED,
        title=f"Nouveau commentaire : {task.title}",
        body=body[:200],
        resource_type="task",
        resource_id=str(task.id),
        exclude_user_id=actor.id,
    )
    await db.commit()
    return comment


# ---------------------------------------------------------------- checklist


async def toggle_checklist_item(
    db: AsyncSession,
    actor: User,
    task_id: uuid.UUID,
    item_id: uuid.UUID,
    is_done: bool,
    ip_address: str | None,
) -> Task:
    task = await _get_task_in_scope(db, actor, task_id)
    item = await task_repository.get_checklist_item(db, item_id)
    if item is None or item.task_id != task.id:
        raise NotFoundError("Element de checklist introuvable.")

    await task_repository.set_checklist_item_done(db, item, is_done, actor.id)
    await audit_service.log_action(
        db,
        actor_user_id=actor.id,
        action="task.checklist_toggled",
        resource_type="task",
        resource_id=str(task.id),
        details={"item_id": str(item.id), "is_done": is_done},
        ip_address=ip_address,
    )
    await db.commit()
    return await task_repository.get_by_id(db, task.id)


# -------------------------------------------------------------- dependances


async def add_dependency(
    db: AsyncSession,
    actor: User,
    task_id: uuid.UUID,
    depends_on_task_id: uuid.UUID,
    ip_address: str | None,
) -> None:
    if task_id == depends_on_task_id:
        raise BusinessRuleError("Une tache ne peut pas dependre d'elle-meme.")

    task = await _get_task_in_scope(db, actor, task_id)
    dependency = await _get_task_in_scope(db, actor, depends_on_task_id)

    # Refus des cycles : si la dependance depend deja (directement ou non) de
    # la tache courante, ajouter ce lien rendrait les deux indemarrables.
    if await task_repository.has_dependency_path(db, dependency.id, task.id):
        raise BusinessRuleError("Cette dependance creerait un cycle entre les taches.")

    if depends_on_task_id in await task_repository.get_dependency_ids(db, task.id):
        return

    await task_repository.add_dependency(db, task.id, dependency.id)
    await audit_service.log_action(
        db,
        actor_user_id=actor.id,
        action="task.dependency_added",
        resource_type="task",
        resource_id=str(task.id),
        details={"depends_on": str(dependency.id)},
        ip_address=ip_address,
    )
    await db.commit()


async def remove_dependency(
    db: AsyncSession,
    actor: User,
    task_id: uuid.UUID,
    depends_on_task_id: uuid.UUID,
    ip_address: str | None,
) -> None:
    task = await _get_task_in_scope(db, actor, task_id)
    await task_repository.remove_dependency(db, task.id, depends_on_task_id)
    await audit_service.log_action(
        db,
        actor_user_id=actor.id,
        action="task.dependency_removed",
        resource_type="task",
        resource_id=str(task.id),
        details={"depends_on": str(depends_on_task_id)},
        ip_address=ip_address,
    )
    await db.commit()


async def list_dependencies(db: AsyncSession, actor: User, task_id: uuid.UUID) -> list[uuid.UUID]:
    await _get_task_in_scope(db, actor, task_id)
    return await task_repository.get_dependency_ids(db, task_id)


async def list_history(
    db: AsyncSession, actor: User, task_id: uuid.UUID
) -> list[TaskStatusHistory]:
    await _get_task_in_scope(db, actor, task_id)
    return await task_repository.list_status_history(db, task_id)
