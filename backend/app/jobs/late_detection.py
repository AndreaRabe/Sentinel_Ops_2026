"""Passage automatique des taches echues au statut LATE.

Seule transition du systeme (et non d'un utilisateur) : `changed_by_id` reste
NULL dans l'historique, et l'audit l'attribue a l'acteur NULL. Le job est
idempotent - une tache deja LATE n'est pas retraitee, la requete source
excluant ce statut.
"""

import logging
from datetime import datetime, timezone

from app.models.enums import NotificationType, TaskStatus
from app.db.session import SessionLocal
from app.repositories import task_repository
from app.services import audit_service, notification_service

logger = logging.getLogger(__name__)


async def run() -> int:
    """Retourne le nombre de taches basculees en retard."""
    now = datetime.now(timezone.utc)
    async with SessionLocal() as db:
        overdue = await task_repository.list_overdue_open_tasks(db, now)
        for task in overdue:
            previous_status = task.status
            await task_repository.update_fields(db, task, status=TaskStatus.LATE)
            await task_repository.add_status_history(
                db,
                task.id,
                previous_status,
                TaskStatus.LATE,
                changed_by_id=None,
                comment="Echeance depassee (detection automatique).",
            )
            await audit_service.log_action(
                db,
                actor_user_id=None,
                action="task.marked_late",
                resource_type="task",
                resource_id=str(task.id),
                details={"from": previous_status, "due_at": task.due_at.isoformat()},
            )
            await notification_service.notify(
                db,
                {assignment.user_id for assignment in task.assignments},
                type_=NotificationType.TASK_LATE,
                title=f"Tache en retard : {task.title}",
                resource_type="task",
                resource_id=str(task.id),
            )
        await db.commit()

    if overdue:
        logger.info("late_detection: %d tache(s) passee(s) en retard", len(overdue))
    return len(overdue)
