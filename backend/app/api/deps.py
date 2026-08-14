"""Dependencies FastAPI partagees entre endpoints."""

import uuid

from fastapi import Depends, Request
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
    if user is None or not user.is_active or user.deleted_at is not None:
        raise InvalidCredentialsError("Session invalide.")
    return user


def get_client_ip(request: Request) -> str | None:
    """IP source journalisee en audit.

    Pas de lecture de X-Forwarded-For : en LAN derriere un unique reverse proxy
    maitrise, l'en-tete serait falsifiable sans apporter d'information fiable.
    """
    return request.client.host if request.client else None
