"""Import centralise de tous les modeles pour qu'Alembic detecte le schema complet."""

from app.models.audit_log import AuditLog
from app.models.incident import Incident, IncidentAction, IncidentAttachment
from app.models.notification import Notification
from app.models.password_history import PasswordHistory
from app.models.permission import Permission
from app.models.refresh_token import RefreshToken
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.site import Site
from app.models.system_setting import SystemSetting
from app.models.task import (
    Task,
    TaskAssignment,
    TaskAttachment,
    TaskChecklistItem,
    TaskComment,
    TaskDependency,
    TaskStatusHistory,
    TaskTemplate,
)
from app.models.user import User
from app.models.user_site import UserSite

__all__ = [
    "AuditLog",
    "Incident",
    "IncidentAction",
    "IncidentAttachment",
    "Notification",
    "PasswordHistory",
    "Permission",
    "RefreshToken",
    "Role",
    "RolePermission",
    "Site",
    "SystemSetting",
    "Task",
    "TaskAssignment",
    "TaskAttachment",
    "TaskChecklistItem",
    "TaskComment",
    "TaskDependency",
    "TaskStatusHistory",
    "TaskTemplate",
    "User",
    "UserSite",
]
