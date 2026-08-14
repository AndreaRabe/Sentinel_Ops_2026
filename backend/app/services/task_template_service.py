"""Modeles de taches et recurrence RRULE.

Un template sans `rrule` est un simple modele reutilisable, instancie a la
demande. Un template avec `rrule` est en plus materialise automatiquement par
le job de recurrence (jobs/recurrence.py). La RRULE est validee ici, a
l'ecriture : une regle invalide detectee seulement a l'execution du job
passerait inapercue jusqu'a ce que des taches cessent silencieusement d'etre
generees.
"""

import uuid
from datetime import datetime, timezone

from dateutil.rrule import rrulestr
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models.task import TaskTemplate
from app.models.user import User
from app.repositories import site_repository, task_template_repository
from app.services import audit_service, scope_service, task_service


def validate_rrule(rrule: str | None) -> str | None:
    if not rrule:
        return None
    try:
        rrulestr(rrule, dtstart=datetime.now(timezone.utc))
    except (ValueError, TypeError) as exc:
        raise BusinessRuleError(f"Regle de recurrence invalide : {exc}") from exc
    return rrule


async def list_templates(
    db: AsyncSession, actor: User, *, active_only: bool = True
) -> list[TaskTemplate]:
    site_ids = await scope_service.visible_site_ids(db, actor)
    return await task_template_repository.list_all(db, site_ids=site_ids, active_only=active_only)


async def get_template(db: AsyncSession, actor: User, template_id: uuid.UUID) -> TaskTemplate:
    template = await task_template_repository.get_by_id(db, template_id)
    if template is None:
        raise NotFoundError("Modele de tache introuvable.")
    await scope_service.assert_site_allowed(db, actor, template.site_id)
    return template


async def create_template(
    db: AsyncSession, actor: User, *, payload: dict, ip_address: str | None
) -> TaskTemplate:
    site_id = payload["site_id"]
    if await site_repository.get_by_id(db, site_id) is None:
        raise NotFoundError("Site introuvable.")
    await scope_service.assert_site_allowed(db, actor, site_id)
    validate_rrule(payload.get("rrule"))

    template = await task_template_repository.create(
        db,
        name=payload["name"],
        description=payload.get("description"),
        site_id=site_id,
        default_priority=payload["default_priority"],
        rrule=payload.get("rrule"),
        estimated_minutes=payload.get("estimated_minutes"),
        checklist_labels=payload.get("checklist_labels") or None,
        default_assignee_ids=[str(uid) for uid in payload.get("default_assignee_ids", [])] or None,
        created_by_id=actor.id,
    )
    await audit_service.log_action(
        db,
        actor_user_id=actor.id,
        action="task_template.created",
        resource_type="task_template",
        resource_id=str(template.id),
        details={"name": template.name, "rrule": template.rrule},
        ip_address=ip_address,
    )
    await db.commit()
    return template


async def update_template(
    db: AsyncSession,
    actor: User,
    template_id: uuid.UUID,
    *,
    payload: dict,
    ip_address: str | None,
) -> TaskTemplate:
    template = await get_template(db, actor, template_id)
    if "rrule" in payload:
        validate_rrule(payload["rrule"])

    changes = {key: value for key, value in payload.items() if value is not None}
    if "default_assignee_ids" in changes:
        changes["default_assignee_ids"] = [str(uid) for uid in changes["default_assignee_ids"]]
    if not changes:
        return template

    await task_template_repository.update_fields(db, template, **changes)
    await audit_service.log_action(
        db,
        actor_user_id=actor.id,
        action="task_template.updated",
        resource_type="task_template",
        resource_id=str(template.id),
        details={key: str(value) for key, value in changes.items()},
        ip_address=ip_address,
    )
    await db.commit()
    return template


async def delete_template(
    db: AsyncSession, actor: User, template_id: uuid.UUID, ip_address: str | None
) -> None:
    template = await get_template(db, actor, template_id)
    await task_template_repository.soft_delete(db, template)
    await audit_service.log_action(
        db,
        actor_user_id=actor.id,
        action="task_template.deleted",
        resource_type="task_template",
        resource_id=str(template.id),
        details={"name": template.name},
        ip_address=ip_address,
    )
    await db.commit()


async def instantiate(
    db: AsyncSession,
    actor: User,
    template_id: uuid.UUID,
    *,
    due_at: datetime | None,
    ip_address: str | None,
):
    """Cree une tache a partir d'un modele (usage manuel)."""
    template = await get_template(db, actor, template_id)
    return await task_service.create_task(
        db,
        actor,
        title=template.name,
        description=template.description,
        site_id=template.site_id,
        priority=template.default_priority,
        due_at=due_at,
        estimated_minutes=template.estimated_minutes,
        assignee_ids=[uuid.UUID(uid) for uid in (template.default_assignee_ids or [])],
        checklist_labels=list(template.checklist_labels or []),
        template_id=template.id,
        ip_address=ip_address,
    )
