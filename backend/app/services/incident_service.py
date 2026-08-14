"""Regles metier des incidents.

Cycle de vie : OPEN -> IN_PROGRESS -> RESOLVED -> CLOSED. Plus simple que celui
des taches (pas de dependances ni de recurrence), il reste garde par des regles
explicites : on ne cloture pas un incident non resolu, et on ne rouvre pas un
incident deja clos - la trace d'origine doit rester intacte pour l'audit.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models.enums import (
    IncidentActionType,
    IncidentSeverity,
    IncidentStatus,
    NotificationType,
)
from app.models.incident import Incident, IncidentAction
from app.models.user import User
from app.repositories import incident_repository, site_repository, user_repository
from app.schemas.common import Pagination
from app.services import audit_service, notification_service, scope_service

ALLOWED_STATUS_TRANSITIONS: dict[IncidentStatus, frozenset[IncidentStatus]] = {
    IncidentStatus.OPEN: frozenset({IncidentStatus.IN_PROGRESS, IncidentStatus.RESOLVED}),
    IncidentStatus.IN_PROGRESS: frozenset({IncidentStatus.RESOLVED}),
    IncidentStatus.RESOLVED: frozenset({IncidentStatus.CLOSED, IncidentStatus.IN_PROGRESS}),
    IncidentStatus.CLOSED: frozenset(),
}

#: Gravites qui declenchent une notification a l'ensemble des utilisateurs du site.
BROADCAST_SEVERITIES: frozenset[IncidentSeverity] = frozenset(
    {IncidentSeverity.MAJOR, IncidentSeverity.CRITICAL}
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def get_incident(db: AsyncSession, actor: User, incident_id: uuid.UUID) -> Incident:
    incident = await incident_repository.get_by_id(db, incident_id)
    if incident is None:
        raise NotFoundError("Incident introuvable.")
    await scope_service.assert_site_allowed(db, actor, incident.site_id)
    return incident


async def list_incidents(
    db: AsyncSession,
    actor: User,
    pagination: Pagination,
    *,
    statuses: list[IncidentStatus] | None = None,
    severities: list[IncidentSeverity] | None = None,
    site_id: uuid.UUID | None = None,
    mine_only: bool = False,
    occurred_after: datetime | None = None,
    occurred_before: datetime | None = None,
    query_text: str | None = None,
) -> tuple[list[Incident], int]:
    site_ids = await scope_service.visible_site_ids(db, actor)
    if site_id is not None:
        await scope_service.assert_site_allowed(db, actor, site_id)
        site_ids = {site_id}

    return await incident_repository.search(
        db,
        pagination,
        site_ids=site_ids,
        statuses=statuses,
        severities=severities,
        reported_by_id=actor.id if mine_only else None,
        occurred_after=occurred_after,
        occurred_before=occurred_before,
        query_text=query_text,
    )


async def create_incident(
    db: AsyncSession,
    actor: User,
    *,
    title: str,
    description: str,
    severity: IncidentSeverity,
    site_id: uuid.UUID,
    occurred_at: datetime | None,
    ip_address: str | None,
) -> Incident:
    if await site_repository.get_by_id(db, site_id) is None:
        raise NotFoundError("Site introuvable.")
    await scope_service.assert_site_allowed(db, actor, site_id)

    occurred = occurred_at or _now()
    if occurred > _now():
        raise BusinessRuleError("La date de survenue ne peut pas etre dans le futur.")

    reference = await incident_repository.next_reference(db, occurred.year)
    incident = await incident_repository.create(
        db,
        reference=reference,
        title=title,
        description=description,
        severity=severity,
        status=IncidentStatus.OPEN,
        site_id=site_id,
        reported_by_id=actor.id,
        occurred_at=occurred,
    )
    await incident_repository.add_action(
        db, incident.id, actor.id, IncidentActionType.STATUS_CHANGE, "Incident declare."
    )
    await audit_service.log_action(
        db,
        actor_user_id=actor.id,
        action="incident.created",
        resource_type="incident",
        resource_id=str(incident.id),
        details={"reference": reference, "severity": severity, "site_id": str(site_id)},
        ip_address=ip_address,
    )

    if severity in BROADCAST_SEVERITIES:
        recipients = await site_repository.get_user_ids_for_sites(db, {site_id})
        await notification_service.notify(
            db,
            recipients,
            type_=NotificationType.INCIDENT_REPORTED,
            title=f"Incident {severity} : {title}",
            body=description[:200],
            resource_type="incident",
            resource_id=str(incident.id),
            exclude_user_id=actor.id,
        )

    await db.commit()
    return incident


async def update_incident(
    db: AsyncSession,
    actor: User,
    incident_id: uuid.UUID,
    *,
    fields: dict,
    ip_address: str | None,
) -> Incident:
    incident = await get_incident(db, actor, incident_id)
    if incident.status == IncidentStatus.CLOSED:
        raise BusinessRuleError("Un incident cloture n'est plus modifiable.")

    new_status = fields.pop("status", None)
    if new_status is not None and new_status != incident.status:
        if new_status not in ALLOWED_STATUS_TRANSITIONS[incident.status]:
            raise BusinessRuleError(f"Transition interdite : {incident.status} -> {new_status}.")
        if new_status == IncidentStatus.RESOLVED and not incident.resolution_summary:
            raise BusinessRuleError(
                "Utilisez la route de resolution : un incident resolu exige un compte rendu."
            )
        fields["status"] = new_status

    assignee_id = fields.get("assigned_to_id")
    if assignee_id:
        assignees = await user_repository.get_many_by_ids(db, {assignee_id})
        if not assignees:
            raise NotFoundError("Utilisateur assigne introuvable.")

    changes = {key: value for key, value in fields.items() if value is not None}
    if not changes:
        return incident

    await incident_repository.update_fields(db, incident, **changes)
    await incident_repository.add_action(
        db,
        incident.id,
        actor.id,
        IncidentActionType.ASSIGNMENT if assignee_id else IncidentActionType.STATUS_CHANGE,
        "Incident mis a jour : " + ", ".join(sorted(changes)),
    )
    await audit_service.log_action(
        db,
        actor_user_id=actor.id,
        action="incident.updated",
        resource_type="incident",
        resource_id=str(incident.id),
        details={key: str(value) for key, value in changes.items()},
        ip_address=ip_address,
    )
    if assignee_id:
        await notification_service.notify(
            db,
            {assignee_id},
            type_=NotificationType.INCIDENT_REPORTED,
            title=f"Incident qui vous est confie : {incident.reference}",
            resource_type="incident",
            resource_id=str(incident.id),
            exclude_user_id=actor.id,
        )
    await db.commit()
    return incident


async def resolve_incident(
    db: AsyncSession,
    actor: User,
    incident_id: uuid.UUID,
    resolution_summary: str,
    ip_address: str | None,
) -> Incident:
    incident = await get_incident(db, actor, incident_id)
    if incident.status in {IncidentStatus.RESOLVED, IncidentStatus.CLOSED}:
        raise BusinessRuleError("Cet incident est deja resolu.")

    await incident_repository.update_fields(
        db,
        incident,
        status=IncidentStatus.RESOLVED,
        resolved_at=_now(),
        resolution_summary=resolution_summary,
    )
    await incident_repository.add_action(
        db, incident.id, actor.id, IncidentActionType.RESOLUTION, resolution_summary
    )
    await audit_service.log_action(
        db,
        actor_user_id=actor.id,
        action="incident.resolved",
        resource_type="incident",
        resource_id=str(incident.id),
        details={"reference": incident.reference},
        ip_address=ip_address,
    )
    recipients = {
        uid for uid in {incident.reported_by_id, incident.assigned_to_id} if uid is not None
    }
    await notification_service.notify(
        db,
        recipients,
        type_=NotificationType.INCIDENT_RESOLVED,
        title=f"Incident resolu : {incident.reference}",
        body=resolution_summary[:200],
        resource_type="incident",
        resource_id=str(incident.id),
        exclude_user_id=actor.id,
    )
    await db.commit()
    return incident


async def close_incident(
    db: AsyncSession, actor: User, incident_id: uuid.UUID, ip_address: str | None
) -> Incident:
    incident = await get_incident(db, actor, incident_id)
    if incident.status != IncidentStatus.RESOLVED:
        raise BusinessRuleError("Seul un incident resolu peut etre cloture.")

    await incident_repository.update_fields(db, incident, status=IncidentStatus.CLOSED)
    await incident_repository.add_action(
        db, incident.id, actor.id, IncidentActionType.STATUS_CHANGE, "Incident cloture."
    )
    await audit_service.log_action(
        db,
        actor_user_id=actor.id,
        action="incident.closed",
        resource_type="incident",
        resource_id=str(incident.id),
        ip_address=ip_address,
    )
    await db.commit()
    return incident


async def add_action(
    db: AsyncSession,
    actor: User,
    incident_id: uuid.UUID,
    body: str,
    ip_address: str | None,
) -> IncidentAction:
    incident = await get_incident(db, actor, incident_id)
    action = await incident_repository.add_action(
        db, incident.id, actor.id, IncidentActionType.COMMENT, body
    )
    await audit_service.log_action(
        db,
        actor_user_id=actor.id,
        action="incident.action_added",
        resource_type="incident",
        resource_id=str(incident.id),
        ip_address=ip_address,
    )
    await db.commit()
    return action


async def list_actions(
    db: AsyncSession, actor: User, incident_id: uuid.UUID
) -> list[IncidentAction]:
    await get_incident(db, actor, incident_id)
    return await incident_repository.list_actions(db, incident_id)


async def delete_incident(
    db: AsyncSession, actor: User, incident_id: uuid.UUID, ip_address: str | None
) -> None:
    incident = await get_incident(db, actor, incident_id)
    await incident_repository.soft_delete(db, incident)
    await audit_service.log_action(
        db,
        actor_user_id=actor.id,
        action="incident.deleted",
        resource_type="incident",
        resource_id=str(incident.id),
        details={"reference": incident.reference},
        ip_address=ip_address,
    )
    await db.commit()
