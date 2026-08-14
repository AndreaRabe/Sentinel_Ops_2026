from fastapi import APIRouter

from app.api.v1.endpoints import (
    audit,
    auth,
    dashboard,
    health,
    incidents,
    notifications,
    reports,
    roles,
    settings,
    sites,
    task_templates,
    tasks,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)

# Administration
api_router.include_router(users.router)
api_router.include_router(sites.router)
api_router.include_router(roles.router)
api_router.include_router(settings.router)

# Metier
api_router.include_router(tasks.router)
api_router.include_router(task_templates.router)
api_router.include_router(incidents.router)

# Transverse
api_router.include_router(dashboard.router)
api_router.include_router(notifications.router)
api_router.include_router(reports.router)
api_router.include_router(audit.router)
