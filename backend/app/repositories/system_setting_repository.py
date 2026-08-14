"""Acces donnees pur sur les parametres systeme."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_setting import SystemSetting


async def get(db: AsyncSession, key: str) -> SystemSetting | None:
    return await db.get(SystemSetting, key)


async def list_all(db: AsyncSession) -> list[SystemSetting]:
    result = await db.execute(select(SystemSetting).order_by(SystemSetting.key))
    return list(result.scalars().all())


async def upsert(
    db: AsyncSession,
    key: str,
    value: dict,
    description: str | None,
    updated_by_id: uuid.UUID | None,
) -> SystemSetting:
    setting = await db.get(SystemSetting, key)
    if setting is None:
        setting = SystemSetting(key=key, value=value, description=description)
        db.add(setting)
    else:
        setting.value = value
        if description is not None:
            setting.description = description
    setting.updated_by_id = updated_by_id
    await db.flush()
    return setting
