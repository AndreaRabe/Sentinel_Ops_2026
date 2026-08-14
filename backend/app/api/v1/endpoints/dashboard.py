"""Dashboard et planning - lectures agregees."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import BusinessRuleError
from app.core.permissions import require_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardRead, PlanningRead
from app.services import dashboard_service

router = APIRouter(tags=["dashboard"])

#: Garde-fou : une plage trop large ferait exploser la reponse du calendrier.
MAX_PLANNING_DAYS = 62


@router.get(
    "/dashboard",
    response_model=DashboardRead,
    dependencies=[Depends(require_permission("task:read"))],
)
async def get_dashboard(
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardRead:
    return await dashboard_service.get_dashboard(db, actor)


@router.get(
    "/planning",
    response_model=PlanningRead,
    dependencies=[Depends(require_permission("planning:read"))],
)
async def get_planning(
    start: date | None = Query(None, description="Debut de periode (defaut : aujourd'hui)."),
    end: date | None = Query(None, description="Fin de periode incluse (defaut : +7 jours)."),
    mine: bool = Query(False),
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlanningRead:
    start = start or date.today()
    end = end or start + timedelta(days=7)
    if end < start:
        raise BusinessRuleError("La fin de periode precede son debut.")
    if (end - start).days > MAX_PLANNING_DAYS:
        raise BusinessRuleError(f"Periode limitee a {MAX_PLANNING_DAYS} jours.")

    return await dashboard_service.get_planning(db, actor, start, end, mine_only=mine)
