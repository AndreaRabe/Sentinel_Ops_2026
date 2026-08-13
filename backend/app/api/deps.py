"""Dependencies FastAPI partagees entre endpoints."""

import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidCredentialsError
from app.core.permissions import get_current_user_payload
from app.db.session import get_db
from app.models.user import User
from app.repositories import user_repository


async def get_current_user(
    payload: dict = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await user_repository.get_by_id(db, uuid.UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise InvalidCredentialsError("Session invalide.")
    return user
