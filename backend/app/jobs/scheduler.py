"""Ordonnanceur APScheduler embarque dans le processus FastAPI.

Pas de Celery ni de broker Redis : a l'echelle du projet (5-15 utilisateurs,
LAN, un seul developpeur), un ordonnanceur in-process est exploitable sans
infrastructure supplementaire (cahier des charges section 5).

ATTENTION : ce choix suppose UN SEUL processus backend. Si uvicorn etait un
jour lance avec plusieurs workers, chaque worker executerait les jobs en
parallele et genererait des taches recurrentes en double. Dans ce cas, il
faudrait desactiver le scheduler (SCHEDULER_ENABLED=false) sur tous les
workers sauf un.
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.jobs import due_soon, late_detection, recurrence

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def start() -> AsyncIOScheduler | None:
    global _scheduler
    if not settings.scheduler_enabled:
        logger.info("scheduler: desactive par configuration")
        return None
    if _scheduler is not None:
        return _scheduler

    _scheduler = AsyncIOScheduler(timezone=settings.scheduler_timezone)

    # Detection des retards toutes les 15 minutes : suffisamment reactif pour
    # que le dashboard reste juste, sans marteler la base.
    _scheduler.add_job(
        late_detection.run,
        CronTrigger(minute="*/15"),
        id="late_detection",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # Generation des recurrences une fois par nuit : les taches du jour sont
    # ainsi pretes avant la prise de poste.
    _scheduler.add_job(
        recurrence.run,
        CronTrigger(hour=2, minute=0),
        id="recurrence",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # Rappel des echeances proches, une fois par jour avant la prise de poste.
    # La cadence quotidienne et la fenetre de 24 h de due_soon.LOOKAHEAD vont
    # de pair : les modifier separement produirait des rappels en double.
    _scheduler.add_job(
        due_soon.run,
        CronTrigger(hour=7, minute=0),
        id="due_soon",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    _scheduler.start()
    logger.info("scheduler: demarre (%s)", settings.scheduler_timezone)
    return _scheduler


def shutdown() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("scheduler: arrete")
