"""Administration des sites."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip, get_current_user
from app.core.permissions import require_permission
from app.db.session import get_db
from app.models.user import User
from app.repositories import site_repository
from app.schemas.admin import SiteCreate, SiteRead, SiteUpdate
from app.services import site_service

router = APIRouter(prefix="/sites", tags=["administration"])


async def _to_read(db: AsyncSession, site) -> SiteRead:
    return SiteRead(
        id=site.id,
        name=site.name,
        is_active=site.is_active,
        created_at=site.created_at,
        user_count=await site_repository.count_active_users(db, site.id),
    )


@router.get(
    "", response_model=list[SiteRead], dependencies=[Depends(require_permission("site:read"))]
)
async def list_sites(
    include_inactive: bool = Query(False),
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SiteRead]:
    sites = await site_service.list_sites(db, actor, include_inactive=include_inactive)
    return [await _to_read(db, site) for site in sites]


@router.post(
    "",
    response_model=SiteRead,
    status_code=201,
    dependencies=[Depends(require_permission("site:create"))],
)
async def create_site(
    payload: SiteCreate,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ip_address: str | None = Depends(get_client_ip),
) -> SiteRead:
    site = await site_service.create_site(db, actor, payload.name, ip_address)
    return await _to_read(db, site)


@router.patch(
    "/{site_id}",
    response_model=SiteRead,
    dependencies=[Depends(require_permission("site:update"))],
)
async def update_site(
    site_id: uuid.UUID,
    payload: SiteUpdate,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ip_address: str | None = Depends(get_client_ip),
) -> SiteRead:
    site = await site_service.update_site(
        db,
        actor,
        site_id,
        name=payload.name,
        is_active=payload.is_active,
        ip_address=ip_address,
    )
    return await _to_read(db, site)


@router.delete(
    "/{site_id}",
    status_code=204,
    dependencies=[Depends(require_permission("site:delete"))],
)
async def delete_site(
    site_id: uuid.UUID,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ip_address: str | None = Depends(get_client_ip),
) -> None:
    await site_service.delete_site(db, actor, site_id, ip_address)
