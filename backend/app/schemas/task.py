"""Schemas du module Taches."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TaskPriority, TaskStatus


class ChecklistItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    label: str
    position: int
    is_done: bool
    done_by_id: uuid.UUID | None
    done_at: datetime | None


class ChecklistItemToggle(BaseModel):
    is_done: bool


class TaskRead(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    site_id: uuid.UUID
    template_id: uuid.UUID | None
    created_by_id: uuid.UUID | None
    due_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    postponed_until: datetime | None
    estimated_minutes: int | None
    created_at: datetime
    assignee_ids: list[uuid.UUID] = []
    checklist: list[ChecklistItemRead] = []
    #: Calcule : la tache est echue mais pas encore marquee LATE par le job.
    is_overdue: bool = False

    @classmethod
    def from_task(cls, task, *, is_overdue: bool = False) -> "TaskRead":
        """Construit la vue d'une tache chargee avec ses assignations et sa checklist."""
        return cls(
            id=task.id,
            title=task.title,
            description=task.description,
            status=task.status,
            priority=task.priority,
            site_id=task.site_id,
            template_id=task.template_id,
            created_by_id=task.created_by_id,
            due_at=task.due_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            postponed_until=task.postponed_until,
            estimated_minutes=task.estimated_minutes,
            created_at=task.created_at,
            assignee_ids=[assignment.user_id for assignment in task.assignments],
            checklist=[
                ChecklistItemRead.model_validate(item)
                for item in sorted(task.checklist_items, key=lambda i: i.position)
            ],
            is_overdue=is_overdue,
        )


class TaskCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str | None = None
    site_id: uuid.UUID
    priority: TaskPriority = TaskPriority.NORMAL
    due_at: datetime | None = None
    estimated_minutes: int | None = Field(default=None, ge=0)
    assignee_ids: list[uuid.UUID] = Field(default_factory=list)
    checklist_labels: list[str] = Field(default_factory=list)
    template_id: uuid.UUID | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = None
    priority: TaskPriority | None = None
    due_at: datetime | None = None
    estimated_minutes: int | None = Field(default=None, ge=0)
    site_id: uuid.UUID | None = None
    checklist_labels: list[str] | None = None


class TaskStatusUpdate(BaseModel):
    status: TaskStatus
    comment: str | None = Field(default=None, max_length=1000)
    postponed_until: datetime | None = Field(
        default=None, description="Obligatoire pour un passage en POSTPONED."
    )


class TaskAssignmentUpdate(BaseModel):
    assignee_ids: list[uuid.UUID]


class TaskCommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    author_id: uuid.UUID | None
    body: str
    created_at: datetime


class TaskCommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class TaskStatusHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    from_status: TaskStatus | None
    to_status: TaskStatus
    changed_by_id: uuid.UUID | None
    comment: str | None
    created_at: datetime


class TaskDependencyCreate(BaseModel):
    depends_on_task_id: uuid.UUID


class AttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    uploaded_by_id: uuid.UUID | None
    created_at: datetime


class TaskTemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    default_priority: TaskPriority
    site_id: uuid.UUID
    rrule: str | None
    estimated_minutes: int | None
    checklist_labels: list[str] | None
    default_assignee_ids: list[uuid.UUID] | None
    is_active: bool
    last_generated_at: datetime | None
    created_at: datetime


class TaskTemplateCreate(BaseModel):
    name: str = Field(min_length=3, max_length=200)
    description: str | None = None
    site_id: uuid.UUID
    default_priority: TaskPriority = TaskPriority.NORMAL
    rrule: str | None = Field(
        default=None,
        description="Regle RRULE (RFC 5545). Vide = modele instancie manuellement.",
        max_length=500,
    )
    estimated_minutes: int | None = Field(default=None, ge=0)
    checklist_labels: list[str] = Field(default_factory=list)
    default_assignee_ids: list[uuid.UUID] = Field(default_factory=list)


class TaskTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = None
    default_priority: TaskPriority | None = None
    rrule: str | None = Field(default=None, max_length=500)
    estimated_minutes: int | None = Field(default=None, ge=0)
    checklist_labels: list[str] | None = None
    default_assignee_ids: list[uuid.UUID] | None = None
    is_active: bool | None = None
