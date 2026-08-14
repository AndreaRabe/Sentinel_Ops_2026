"""Parametres systeme (Super Admin).

Aucun secret ne transite par ces routes : cles JWT, mots de passe et URL de
base restent dans `.env` (cahier des charges section 7). On ne stocke ici que
des reglages fonctionnels modifiables a chaud.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip, get_current_user
from app.core.permissions import require_permission
from app.db.session import get_db
from app.models.user import User
from app.repositories import system_setting_repository
from app.services import audit_service

router = APIRouter(prefix="/settings", tags=["administration"])


class SettingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    value: dict
    description: str | None


class SettingUpsert(BaseModel):
    value: dict = Field(description="Valeur JSON du parametre.")
    description: str | None = None


@router.get(
    "",
    response_model=list[SettingRead],
    dependencies=[Depends(require_permission("settings:read"))],
)
async def list_settings(db: AsyncSession = Depends(get_db)) -> list[SettingRead]:
    settings_rows = await system_setting_repository.list_all(db)
    return [SettingRead.model_validate(row) for row in settings_rows]


@router.put(
    "/{key}",
    response_model=SettingRead,
    dependencies=[Depends(require_permission("settings:update"))],
)
async def upsert_setting(
    key: str,
    payload: SettingUpsert,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ip_address: str | None = Depends(get_client_ip),
) -> SettingRead:
    setting = await system_setting_repository.upsert(
        db, key, payload.value, payload.description, actor.id
    )
    await audit_service.log_action(
        db,
        actor_user_id=actor.id,
        action="settings.updated",
        resource_type="system_setting",
        resource_id=key,
        details={"value": payload.value},
        ip_address=ip_address,
    )
    await db.commit()
    return SettingRead.model_validate(setting)
