"""Matrice RBAC role -> permissions - source de verite unique.

Utilisee (1) par les migrations Alembic pour peupler
roles/permissions/role_permissions et (2) par le seed pour resoudre le role
du Super Admin. Toute evolution de cette matrice doit passer par une nouvelle
migration versionnee (voir README - Securite).

Rappel : ce fichier ne repond qu'a "ce role peut-il faire cette action ?".
La question "sur quelle ressource ?" (scope multi-site) est traitee a part
dans core/scope.py et doit etre verifiee explicitement dans les services.
"""

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "super_admin": {"*"},
    "responsable": {
        # Taches
        "task:create",
        "task:read",
        "task:update",
        "task:delete",
        "task:assign",
        "task:comment",
        "task:template_manage",
        # Incidents
        "incident:create",
        "incident:read",
        "incident:update",
        "incident:resolve",
        # Administration (hors roles et parametres systeme : Super Admin only)
        "user:create",
        "user:read",
        "user:update",
        "user:deactivate",
        "user:reset_password",
        "site:create",
        "site:read",
        "site:update",
        # Transverse
        "planning:read",
        "notification:read",
        "audit:read",
        "report:read",
        "report:export",
        "settings:read",
    },
    "chef_equipe": {
        "task:create",
        "task:read",
        "task:update",
        "task:assign",
        "task:comment",
        "task:template_manage",
        "incident:create",
        "incident:read",
        "incident:update",
        "incident:resolve",
        "user:read",
        "site:read",
        "planning:read",
        "notification:read",
        "report:read",
    },
    "agent": {
        "task:read",
        "task:update_own_status",
        "task:comment",
        "incident:create",
        "incident:read",
        "planning:read",
        "notification:read",
    },
}

ROLE_DESCRIPTIONS: dict[str, str] = {
    "super_admin": "Systeme, roles, utilisateurs, parametres - portee globale.",
    "responsable": "Vue centrale tous sites, gestion agents/chefs d'equipe, rapports et audits.",
    "chef_equipe": "Creation/assignation de taches, planning, incidents de ses sites.",
    "agent": "Execution de ses taches assignees, declaration d'incident.",
}

# Permissions reservees au Super Admin : couvertes par le joker "*", elles ne
# sont accordees a aucun autre role. Listees explicitement pour que la migration
# les cree en base (sinon elles n'existeraient nulle part dans `permissions`).
SUPER_ADMIN_ONLY_PERMISSIONS: set[str] = {
    "role:read",
    "role:update",
    "site:delete",
    "task:template_delete",
    "incident:delete",
    "settings:update",
}

PERMISSION_DESCRIPTIONS: dict[str, str] = {
    "task:create": "Creer une tache.",
    "task:read": "Consulter les taches de son perimetre.",
    "task:update": "Modifier une tache (contenu, echeance, statut).",
    "task:delete": "Supprimer (soft delete) une tache.",
    "task:assign": "Assigner ou desassigner des agents sur une tache.",
    "task:update_own_status": "Faire evoluer le statut de ses propres taches assignees.",
    "task:comment": "Commenter une tache.",
    "task:template_manage": "Creer et modifier des modeles de taches recurrentes.",
    "task:template_delete": "Supprimer un modele de tache.",
    "incident:create": "Declarer un incident.",
    "incident:read": "Consulter les incidents de son perimetre.",
    "incident:update": "Modifier un incident et journaliser une action.",
    "incident:resolve": "Cloturer un incident.",
    "incident:delete": "Supprimer (soft delete) un incident.",
    "user:create": "Creer un compte utilisateur.",
    "user:read": "Consulter l'annuaire des utilisateurs.",
    "user:update": "Modifier un compte utilisateur (role, sites, identite).",
    "user:deactivate": "Desactiver ou reactiver un compte utilisateur.",
    "user:reset_password": "Reinitialiser le mot de passe d'un utilisateur.",
    "role:read": "Consulter les roles et leurs permissions.",
    "role:update": "Modifier les permissions d'un role.",
    "site:create": "Creer un site.",
    "site:read": "Consulter les sites.",
    "site:update": "Modifier un site.",
    "site:delete": "Supprimer (soft delete) un site.",
    "planning:read": "Consulter le planning / calendrier.",
    "notification:read": "Consulter ses notifications.",
    "audit:read": "Consulter le journal d'audit (lecture seule).",
    "report:read": "Consulter les rapports.",
    "report:export": "Exporter les rapports en PDF/Excel.",
    "settings:read": "Consulter les parametres systeme.",
    "settings:update": "Modifier les parametres systeme.",
}


def all_permission_codes() -> set[str]:
    """Toutes les permissions devant exister en base, joker "*" exclu."""
    codes = {code for codes in ROLE_PERMISSIONS.values() for code in codes if code != "*"}
    return codes | SUPER_ADMIN_ONLY_PERMISSIONS
