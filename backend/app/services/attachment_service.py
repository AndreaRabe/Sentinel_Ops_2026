"""Pieces jointes des taches et des incidents.

Le fichier n'est ecrit sur disque qu'apres validation du scope : sinon un
utilisateur hors perimetre pourrait deposer des fichiers puis recevoir un 403,
en laissant des orphelins sur le volume.
"""

import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.incident import IncidentAttachment
from app.models.task import TaskAttachment
from app.models.user import User
from app.repositories import incident_repository, task_repository
from app.services import audit_service, incident_service, storage_service, task_service


def file_path(stored_name: str) -> Path:
    return storage_service.resolve_path(stored_name)


async def attach_to_task(
    db: AsyncSession,
    actor: User,
    task_id: uuid.UUID,
    upload: UploadFile,
    ip_address: str | None,
) -> TaskAttachment:
    task = await task_service.get_task(db, actor, task_id)

    filename, stored_name, content_type, size = await storage_service.save_upload(
        upload, subdirectory=f"tasks/{task.id}"
    )
    try:
        attachment = await task_repository.add_attachment(
            db,
            task_id=task.id,
            uploaded_by_id=actor.id,
            filename=filename,
            stored_name=stored_name,
            content_type=content_type,
            size_bytes=size,
        )
        await audit_service.log_action(
            db,
            actor_user_id=actor.id,
            action="task.attachment_added",
            resource_type="task",
            resource_id=str(task.id),
            details={"filename": filename, "size_bytes": size},
            ip_address=ip_address,
        )
        await db.commit()
    except Exception:
        # Le fichier est deja sur disque : sans ce rattrapage il resterait
        # orphelin, sans ligne en base pour le retrouver.
        storage_service.delete_file(stored_name)
        raise
    return attachment


async def delete_task_attachment(
    db: AsyncSession,
    actor: User,
    task_id: uuid.UUID,
    attachment_id: uuid.UUID,
    ip_address: str | None,
) -> None:
    task = await task_service.get_task(db, actor, task_id)
    attachment = await task_repository.get_attachment(db, attachment_id)
    if attachment is None or attachment.task_id != task.id:
        raise NotFoundError("Piece jointe introuvable.")

    stored_name = attachment.stored_name
    filename = attachment.filename
    await task_repository.delete_attachment(db, attachment)
    await audit_service.log_action(
        db,
        actor_user_id=actor.id,
        action="task.attachment_deleted",
        resource_type="task",
        resource_id=str(task.id),
        details={"filename": filename},
        ip_address=ip_address,
    )
    await db.commit()
    storage_service.delete_file(stored_name)


async def attach_to_incident(
    db: AsyncSession,
    actor: User,
    incident_id: uuid.UUID,
    upload: UploadFile,
    ip_address: str | None,
) -> IncidentAttachment:
    incident = await incident_service.get_incident(db, actor, incident_id)

    filename, stored_name, content_type, size = await storage_service.save_upload(
        upload, subdirectory=f"incidents/{incident.id}"
    )
    try:
        attachment = await incident_repository.add_attachment(
            db,
            incident_id=incident.id,
            uploaded_by_id=actor.id,
            filename=filename,
            stored_name=stored_name,
            content_type=content_type,
            size_bytes=size,
        )
        await audit_service.log_action(
            db,
            actor_user_id=actor.id,
            action="incident.attachment_added",
            resource_type="incident",
            resource_id=str(incident.id),
            details={"filename": filename, "size_bytes": size},
            ip_address=ip_address,
        )
        await db.commit()
    except Exception:
        storage_service.delete_file(stored_name)
        raise
    return attachment


async def delete_incident_attachment(
    db: AsyncSession,
    actor: User,
    incident_id: uuid.UUID,
    attachment_id: uuid.UUID,
    ip_address: str | None,
) -> None:
    incident = await incident_service.get_incident(db, actor, incident_id)
    attachment = await incident_repository.get_attachment(db, attachment_id)
    if attachment is None or attachment.incident_id != incident.id:
        raise NotFoundError("Piece jointe introuvable.")

    stored_name = attachment.stored_name
    filename = attachment.filename
    await incident_repository.delete_attachment(db, attachment)
    await audit_service.log_action(
        db,
        actor_user_id=actor.id,
        action="incident.attachment_deleted",
        resource_type="incident",
        resource_id=str(incident.id),
        details={"filename": filename},
        ip_address=ip_address,
    )
    await db.commit()
    storage_service.delete_file(stored_name)
