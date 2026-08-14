"""Rappel des echeances proches.

Notifie les agents assignes des taches qui arrivent a echeance dans les
prochaines 24 heures et qui ne sont ni terminees ni annulees.

Idempotence : il n'existe pas de drapeau "deja notifie" en base. C'est la
cadence du job qui garantit qu'une tache n'est rappelee qu'une fois - une
execution QUOTIDIENNE sur une fenetre de 24 h glissante fait qu'une tache
donnee n'entre dans la fenetre qu'une seule fois. Changer la periodicite sans
changer la fenetre (ou l'inverse) produirait des notifications en double.
"""

import logging
from datetime import datetime, timedelta, timezone

from app.db.session import SessionLocal
from app.models.enums import NotificationType
from app.repositories import task_repository
from app.services import notification_service

logger = logging.getLogger(__name__)

#: Doit rester egal a l'intervalle d'execution du job (voir jobs/scheduler.py).
LOOKAHEAD = timedelta(hours=24)


async def run() -> int:
    """Retourne le nombre de taches ayant declenche un rappel."""
    now = datetime.now(timezone.utc)
    async with SessionLocal() as db:
        tasks = await task_repository.list_due_between_open(db, now, now + LOOKAHEAD)
        for task in tasks:
            assignee_ids = {assignment.user_id for assignment in task.assignments}
            if not assignee_ids:
                continue
            await notification_service.notify(
                db,
                assignee_ids,
                type_=NotificationType.TASK_DUE_SOON,
                title=f"Echeance proche : {task.title}",
                body=f"A rendre le {task.due_at:%d/%m/%Y a %H:%M}.",
                resource_type="task",
                resource_id=str(task.id),
            )
        await db.commit()

    if tasks:
        logger.info("due_soon: %d rappel(s) d'echeance envoye(s)", len(tasks))
    return len(tasks)
