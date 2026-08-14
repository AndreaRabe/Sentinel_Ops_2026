"""Generation des taches recurrentes a partir des modeles portant une RRULE.

Principe : pour chaque template actif avec `rrule`, on calcule les occurrences
comprises entre `last_generated_at` (ou la date de creation du template) et
l'horizon de generation, puis on cree une tache par occurrence.

`last_generated_at` est le curseur qui rend le job idempotent : relancer le job
plusieurs fois dans la meme journee ne duplique rien, et un arret de service de
quelques jours est rattrape a la reprise (les occurrences manquees sont creees).
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from dateutil.rrule import rrulestr

from app.db.session import SessionLocal
from app.models.enums import TaskStatus
from app.repositories import task_repository, task_template_repository
from app.services import audit_service

logger = logging.getLogger(__name__)

#: On ne materialise pas les taches trop en avance : une tache creee des
#: aujourd'hui pour dans 3 mois pollue le backlog sans rien apporter.
GENERATION_HORIZON = timedelta(days=14)

#: Plafond de rattrapage : au-dela, on ne cree pas des centaines de taches
#: retroactives apres une longue interruption.
MAX_OCCURRENCES_PER_RUN = 50


def _occurrences(rrule: str, dtstart: datetime, after: datetime, until: datetime) -> list[datetime]:
    rule = rrulestr(rrule, dtstart=dtstart)
    return list(rule.between(after, until, inc=False))[:MAX_OCCURRENCES_PER_RUN]


async def run() -> int:
    """Retourne le nombre de taches generees."""
    now = datetime.now(timezone.utc)
    horizon = now + GENERATION_HORIZON
    created_count = 0

    async with SessionLocal() as db:
        templates = await task_template_repository.list_all(
            db, recurring_only=True, active_only=True
        )
        for template in templates:
            cursor = template.last_generated_at or template.created_at
            try:
                occurrences = _occurrences(template.rrule, template.created_at, cursor, horizon)
            except (ValueError, TypeError):
                # Une RRULE invalide ne doit pas interrompre la generation des
                # autres modeles : on la signale et on passe au suivant.
                logger.exception(
                    "recurrence: RRULE invalide sur le modele %s (%s)",
                    template.id,
                    template.name,
                )
                continue

            for occurrence in occurrences:
                assignee_ids = {uuid.UUID(value) for value in (template.default_assignee_ids or [])}
                task = await task_repository.create(
                    db,
                    title=template.name,
                    description=template.description,
                    status=TaskStatus.ASSIGNED if assignee_ids else TaskStatus.DRAFT,
                    priority=template.default_priority,
                    site_id=template.site_id,
                    template_id=template.id,
                    created_by_id=None,
                    due_at=occurrence,
                    estimated_minutes=template.estimated_minutes,
                )
                if assignee_ids:
                    await task_repository.set_assignees(db, task.id, assignee_ids, None)
                if template.checklist_labels:
                    await task_repository.replace_checklist(
                        db, task.id, list(template.checklist_labels)
                    )
                await task_repository.add_status_history(
                    db, task.id, None, task.status, changed_by_id=None
                )
                await audit_service.log_action(
                    db,
                    actor_user_id=None,
                    action="task.generated_from_template",
                    resource_type="task",
                    resource_id=str(task.id),
                    details={"template_id": str(template.id), "due_at": occurrence.isoformat()},
                )
                created_count += 1

            if occurrences:
                await task_template_repository.mark_generated(db, template, occurrences[-1])

        await db.commit()

    if created_count:
        logger.info("recurrence: %d tache(s) generee(s)", created_count)
    return created_count
