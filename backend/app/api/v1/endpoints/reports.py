"""Rapports d'activite et exports."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip, get_current_user
from app.core.exceptions import BusinessRuleError
from app.core.permissions import require_permission
from app.db.session import get_db
from app.models.user import User
from app.services import audit_service, report_service

router = APIRouter(prefix="/reports", tags=["rapports"])

MAX_REPORT_DAYS = 366


async def _resolve_range(
    period: str | None, start: date | None, end: date | None
) -> tuple[date, date]:
    if period:
        if period not in report_service.PERIODS:
            raise BusinessRuleError(
                f"Periode inconnue. Valeurs acceptees : {', '.join(report_service.PERIODS)}."
            )
        return report_service.resolve_period(period, date.today())

    start = start or date.today()
    end = end or start
    if end < start:
        raise BusinessRuleError("La fin de periode precede son debut.")
    if (end - start).days > MAX_REPORT_DAYS:
        raise BusinessRuleError(f"Periode limitee a {MAX_REPORT_DAYS} jours.")
    return start, end


@router.get(
    "/activity",
    dependencies=[Depends(require_permission("report:read"))],
)
async def activity_report(
    period: str | None = Query(None, description="day | week | month (prioritaire sur start/end)."),
    start: date | None = Query(None),
    end: date | None = Query(None),
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    start, end = await _resolve_range(period, start, end)
    return await report_service.build_report(db, actor, start, end)


@router.get(
    "/activity/export",
    dependencies=[Depends(require_permission("report:export"))],
)
async def export_activity_report(
    format: str = Query("xlsx", pattern="^(xlsx|pdf)$"),
    period: str | None = Query(None),
    start: date | None = Query(None),
    end: date | None = Query(None),
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ip_address: str | None = Depends(get_client_ip),
) -> Response:
    start, end = await _resolve_range(period, start, end)
    report = await report_service.build_report(db, actor, start, end)

    # Un export sort des donnees de l'application : c'est une action tracee.
    await audit_service.log_action(
        db,
        actor_user_id=actor.id,
        action="report.exported",
        resource_type="report",
        resource_id=f"{start}_{end}",
        details={"format": format, "scope": report["scope"]},
        ip_address=ip_address,
    )
    await db.commit()

    filename = f"sentinel-ops_{start}_{end}.{format}"
    if format == "pdf":
        return Response(
            content=report_service.to_pdf(report),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    return Response(
        content=report_service.to_excel(report),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
