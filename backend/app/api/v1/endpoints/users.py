"""Administration des comptes utilisateurs.

Chaque route : validation Pydantic + garde RBAC (require_permission). Le scope
multi-site et les regles metier sont dans user_service - aucune requete SQL ici.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip, get_current_user
from app.core.permissions import require_permission
from app.db.session import get_db
from app.models.site import Site
from app.models.user import User
from app.repositories import role_repository, site_repository
from app.schemas.admin import (
    CurrentUserRead,
    SiteSummary,
    UserActivation,
    UserCreate,
    UserRead,
    UserUpdate,
)
from app.schemas.common import Page, Pagination, TemporaryPasswordResponse, pagination_params
from app.services import user_service

router = APIRouter(prefix="/users", tags=["administration"])


def _to_read(user: User, sites: list[Site]) -> UserRead:
    return UserRead(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        role=user.role.name,
        is_active=user.is_active,
        must_change_password=user.must_change_password,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        sites=[SiteSummary.model_validate(site) for site in sites],
    )


@router.get("/me", response_model=CurrentUserRead)
async def read_me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CurrentUserRead:
    """Profil de la session courante - aucune permission requise au-dela d'etre authentifie."""
    site_ids = await site_repository.get_site_ids_for_user(db, user.id)
    sites = (
        await site_repository.list_all(db, site_ids=site_ids, include_inactive=True)
        if site_ids
        else []
    )
    permissions = await role_repository.get_permission_codes(db, user.role_id)
    return CurrentUserRead(
        **_to_read(user, sites).model_dump(),
        permissions=sorted(permissions),
    )


@router.get(
    "", response_model=Page[UserRead], dependencies=[Depends(require_permission("user:read"))]
)
async def list_users(
    role: str | None = Query(None, description="Filtrer sur un nom de role."),
    q: str | None = Query(None, description="Recherche sur nom, prenom ou email."),
    include_inactive: bool = Query(True),
    pagination: Pagination = Depends(pagination_params),
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Page[UserRead]:
    rows, total = await user_service.list_users(
        db,
        actor,
        pagination,
        role_name=role,
        query_text=q,
        include_inactive=include_inactive,
    )
    return Page.build([_to_read(user, sites) for user, sites in rows], total, pagination)


@router.get(
    "/{user_id}",
    response_model=UserRead,
    dependencies=[Depends(require_permission("user:read"))],
)
async def get_user(
    user_id: uuid.UUID,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    user, sites = await user_service.get_user(db, actor, user_id)
    return _to_read(user, sites)


@router.post(
    "",
    response_model=TemporaryPasswordResponse,
    status_code=201,
    dependencies=[Depends(require_permission("user:create"))],
)
async def create_user(
    payload: UserCreate,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ip_address: str | None = Depends(get_client_ip),
) -> TemporaryPasswordResponse:
    _, _, temporary_password = await user_service.create_user(
        db,
        actor,
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        role_name=payload.role,
        site_ids=payload.site_ids,
        ip_address=ip_address,
    )
    return TemporaryPasswordResponse(temporary_password=temporary_password)


@router.patch(
    "/{user_id}",
    response_model=UserRead,
    dependencies=[Depends(require_permission("user:update"))],
)
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ip_address: str | None = Depends(get_client_ip),
) -> UserRead:
    user, sites = await user_service.update_user(
        db,
        actor,
        user_id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        role_name=payload.role,
        site_ids=payload.site_ids,
        ip_address=ip_address,
    )
    return _to_read(user, sites)


@router.put(
    "/{user_id}/activation",
    response_model=UserRead,
    dependencies=[Depends(require_permission("user:deactivate"))],
)
async def set_activation(
    user_id: uuid.UUID,
    payload: UserActivation,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ip_address: str | None = Depends(get_client_ip),
) -> UserRead:
    user = await user_service.set_activation(db, actor, user_id, payload.is_active, ip_address)
    _, sites = await user_service.get_user(db, actor, user_id)
    return _to_read(user, sites)


@router.post(
    "/{user_id}/reset-password",
    response_model=TemporaryPasswordResponse,
    dependencies=[Depends(require_permission("user:reset_password"))],
)
async def reset_password(
    user_id: uuid.UUID,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ip_address: str | None = Depends(get_client_ip),
) -> TemporaryPasswordResponse:
    temporary_password = await user_service.reset_password(db, actor, user_id, ip_address)
    return TemporaryPasswordResponse(temporary_password=temporary_password)
