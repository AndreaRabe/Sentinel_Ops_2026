"""Import centralise de tous les modeles pour qu'Alembic detecte le schema complet."""

from app.models.audit_log import AuditLog
from app.models.password_history import PasswordHistory
from app.models.permission import Permission
from app.models.refresh_token import RefreshToken
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.site import Site
from app.models.user import User
from app.models.user_site import UserSite

__all__ = [
    "AuditLog",
    "PasswordHistory",
    "Permission",
    "RefreshToken",
    "Role",
    "RolePermission",
    "Site",
    "User",
    "UserSite",
]
