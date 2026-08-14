"""Consultation des roles et de la matrice de permissions.

LECTURE SEULE volontairement : la matrice RBAC est versionnee dans
`core/rbac_matrix.py` et appliquee par migration Alembic (voir README -
Securite). Exposer une route d'ecriture ici permettrait de modifier des droits
sans trace versionnee, ce que le projet interdit explicitement.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_permission
from app.db.session import get_db
from app.repositories import role_repository
from app.schemas.admin import RoleRead

router = APIRouter(prefix="/roles", tags=["administration"])


@router.get(
    "", response_model=list[RoleRead], dependencies=[Depends(require_permission("role:read"))]
)
async def list_roles(db: AsyncSession = Depends(get_db)) -> list[RoleRead]:
    roles = await role_repository.list_all(db)
    return [
        RoleRead(
            id=role.id,
            name=role.name,
            description=role.description,
            permissions=sorted(await role_repository.get_permission_codes(db, role.id)),
        )
        for role in roles
    ]


@router.get(
    "/permissions",
    response_model=list[str],
    dependencies=[Depends(require_permission("role:read"))],
)
async def list_permissions(db: AsyncSession = Depends(get_db)) -> list[str]:
    return await role_repository.list_permission_codes(db)
