"""Matrice RBAC role -> permissions - source de verite unique.

Utilisee (1) par la migration Alembic initiale pour peupler
roles/permissions/role_permissions et (2) par le seed pour resoudre le role
du Super Admin. Toute evolution de cette matrice doit passer par une nouvelle
migration versionnee (voir README - Securite).
"""

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "super_admin": {"*"},
    "responsable": {
        "task:create",
        "task:read",
        "task:update",
        "task:delete",
        "incident:read",
        "incident:resolve",
        "user:create",
        "user:update",
        "user:deactivate",
        "site:create",
        "site:update",
        "audit:read",
        "report:read",
        "report:export",
    },
    "chef_equipe": {
        "task:create",
        "task:read",
        "task:update",
        "incident:read",
        "incident:resolve",
        "report:read",
    },
    "agent": {
        "task:read",
        "task:update_own_status",
        "incident:create",
    },
}

ROLE_DESCRIPTIONS: dict[str, str] = {
    "super_admin": "Systeme, roles, utilisateurs, parametres - portee globale.",
    "responsable": "Vue centrale tous sites, gestion agents/chefs d'equipe, rapports et audits.",
    "chef_equipe": "Creation/assignation de taches, planning, incidents de ses sites.",
    "agent": "Execution de ses taches assignees, declaration d'incident.",
}
