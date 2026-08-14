"""Schemas du dashboard et du planning."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.models.enums import TaskPriority, TaskStatus


class WorkloadEntry(BaseModel):
    user_id: uuid.UUID
    first_name: str
    last_name: str
    open_tasks: int


class DashboardKpis(BaseModel):
    """Chiffres du bandeau haut - affiches en gros caracteres tabulaires animes."""

    tasks_today: int
    tasks_late: int
    tasks_urgent: int
    tasks_open: int
    incidents_open: int


class DashboardRead(BaseModel):
    kpis: DashboardKpis
    tasks_by_status: dict[str, int]
    incidents_by_severity: dict[str, int]
    workload: list[WorkloadEntry]
    generated_at: datetime


class PlanningEntry(BaseModel):
    id: uuid.UUID
    title: str
    status: TaskStatus
    priority: TaskPriority
    site_id: uuid.UUID
    due_at: datetime
    assignee_ids: list[uuid.UUID]


class PlanningDay(BaseModel):
    day: date
    entries: list[PlanningEntry]


class PlanningRead(BaseModel):
    start: date
    end: date
    days: list[PlanningDay]
