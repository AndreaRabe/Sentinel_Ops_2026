"""Schemas du module Administration : utilisateurs, sites, roles."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SiteSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    is_active: bool


class SiteCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)


class SiteUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    is_active: bool | None = None


class SiteRead(SiteSummary):
    created_at: datetime
    user_count: int = 0


class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    permissions: list[str] = []


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    first_name: str
    last_name: str
    email: EmailStr
    role: str
    is_active: bool
    must_change_password: bool
    last_login_at: datetime | None
    created_at: datetime
    sites: list[SiteSummary] = []


class UserCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    role: str = Field(description="Nom du role : responsable, chef_equipe, agent...")
    site_ids: list[uuid.UUID] = Field(
        default_factory=list,
        description="Sites couverts. Obligatoire pour les roles a portee limitee.",
    )


class UserUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    role: str | None = None
    site_ids: list[uuid.UUID] | None = None


class UserActivation(BaseModel):
    is_active: bool


class CurrentUserRead(UserRead):
    """`/users/me` : ajoute les permissions effectives pour l'affichage frontend."""

    permissions: list[str] = []
