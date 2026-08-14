"""Agregats du dashboard et du planning.

Service de lecture pure : aucune mutation, donc aucun appel a audit_service
(l'audit trace les actions, pas les consultations d'ecran).

Tous les agregats sont filtres par le scope multi-site de l'appelant : un chef
d'equipe voit les chiffres de ses sites, un responsable ceux de toute
l'organisation (vue centrale, cahier des charges section 3).
"""

from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TaskPriority, TaskStatus
from app.models.user import User
from app.repositories import incident_repository, task_repository, user_repository
from app.schemas.common import Pagination
from app.schemas.dashboard import (
    DashboardKpis,
    DashboardRead,
    PlanningDay,
    PlanningEntry,
    PlanningRead,
    WorkloadEntry,
)
from app.services import scope_service

URGENT_PRIORITIES = (TaskPriority.HIGH, TaskPriority.CRITICAL)

#: Les KPI ne consomment que le total renvoye par une recherche : on demande
#: donc la plus petite page possible plutot que de rapatrier les lignes.
_COUNT_ONLY_PAGE = Pagination(page=1, page_size=1)


def _day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min, tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


async def get_dashboard(db: AsyncSession, actor: User) -> DashboardRead:
    site_ids = await scope_service.visible_site_ids(db, actor)
    now = datetime.now(timezone.utc)
    today_start, today_end = _day_bounds(now.date())

    tasks_by_status = await task_repository.count_by_status(db, site_ids)
    incidents_by_severity = await incident_repository.count_by_severity(db, site_ids)

    open_statuses = {
        TaskStatus.DRAFT,
        TaskStatus.ASSIGNED,
        TaskStatus.IN_PROGRESS,
        TaskStatus.POSTPONED,
        TaskStatus.LATE,
    }
    tasks_open = sum(count for status, count in tasks_by_status.items() if status in open_statuses)

    tasks_today = await task_repository.count_due_between(db, today_start, today_end, site_ids)
    _, urgent_total = await task_repository.search(
        db,
        _COUNT_ONLY_PAGE,
        site_ids=site_ids,
        statuses=[
            TaskStatus.ASSIGNED,
            TaskStatus.IN_PROGRESS,
            TaskStatus.POSTPONED,
            TaskStatus.LATE,
        ],
        priorities=[priority.value for priority in URGENT_PRIORITIES],
    )

    workload_rows = await task_repository.workload_by_user(db, site_ids)
    users = await user_repository.get_many_by_ids(db, {row[0] for row in workload_rows})
    users_by_id = {user.id: user for user in users}
    workload = [
        WorkloadEntry(
            user_id=user_id,
            first_name=users_by_id[user_id].first_name,
            last_name=users_by_id[user_id].last_name,
            open_tasks=count,
        )
        for user_id, count in workload_rows
        if user_id in users_by_id
    ]
    workload.sort(key=lambda entry: entry.open_tasks, reverse=True)

    return DashboardRead(
        kpis=DashboardKpis(
            tasks_today=tasks_today,
            tasks_late=tasks_by_status.get(TaskStatus.LATE, 0),
            tasks_urgent=urgent_total,
            tasks_open=tasks_open,
            incidents_open=sum(incidents_by_severity.values()),
        ),
        tasks_by_status=tasks_by_status,
        incidents_by_severity=incidents_by_severity,
        workload=workload,
        generated_at=now,
    )


async def get_planning(
    db: AsyncSession, actor: User, start: date, end: date, *, mine_only: bool = False
) -> PlanningRead:
    site_ids = await scope_service.visible_site_ids(db, actor)
    start_dt, _ = _day_bounds(start)
    _, end_dt = _day_bounds(end)

    tasks = await task_repository.list_for_period(
        db,
        start_dt,
        end_dt,
        site_ids,
        assignee_id=actor.id if mine_only else None,
    )

    grouped: dict[date, list[PlanningEntry]] = defaultdict(list)
    for task in tasks:
        grouped[task.due_at.date()].append(
            PlanningEntry(
                id=task.id,
                title=task.title,
                status=task.status,
                priority=task.priority,
                site_id=task.site_id,
                due_at=task.due_at,
                assignee_ids=[assignment.user_id for assignment in task.assignments],
            )
        )

    # Les jours vides sont renvoyes explicitement : le calendrier frontend
    # affiche une grille continue et n'a pas a combler les trous lui-meme.
    days: list[PlanningDay] = []
    cursor = start
    while cursor <= end:
        days.append(PlanningDay(day=cursor, entries=grouped.get(cursor, [])))
        cursor += timedelta(days=1)

    return PlanningRead(start=start, end=end, days=days)
