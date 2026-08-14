"""Schemas du module Incidents."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import IncidentActionType, IncidentSeverity, IncidentStatus


class IncidentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reference: str
    title: str
    description: str
    severity: IncidentSeverity
    status: IncidentStatus
    site_id: uuid.UUID
    reported_by_id: uuid.UUID | None
    assigned_to_id: uuid.UUID | None
    occurred_at: datetime
    resolved_at: datetime | None
    resolution_summary: str | None
    created_at: datetime


class IncidentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=1)
    severity: IncidentSeverity
    site_id: uuid.UUID
    occurred_at: datetime | None = Field(default=None, description="Par defaut : maintenant.")


class IncidentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = None
    severity: IncidentSeverity | None = None
    status: IncidentStatus | None = None
    assigned_to_id: uuid.UUID | None = None


class IncidentResolve(BaseModel):
    resolution_summary: str = Field(
        min_length=10,
        max_length=5000,
        description="Ce qui a ete fait - conserve pour l'audit et les rapports.",
    )


class IncidentActionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    incident_id: uuid.UUID
    author_id: uuid.UUID | None
    action_type: IncidentActionType
    body: str
    created_at: datetime


class IncidentActionCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)
