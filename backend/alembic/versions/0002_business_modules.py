"""modules metier - taches, incidents, notifications, parametres + extension RBAC

Revision ID: 0002_business_modules
Revises: 0001_initial_schema
Create Date: 2026-08-14

La partie RBAC de cette migration est ecrite de maniere IDEMPOTENTE
(ON CONFLICT DO NOTHING). C'est necessaire car 0001 lit la matrice
`app.core.rbac_matrix` a l'execution : une base creee apres l'extension de la
matrice recoit deja les nouvelles permissions des 0001, alors qu'une base
existante ne les recevra qu'ici. Les deux chemins doivent converger vers le
meme etat.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.rbac_matrix import (
    PERMISSION_DESCRIPTIONS,
    ROLE_PERMISSIONS,
    all_permission_codes,
)

revision = "0002_business_modules"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None

TASK_STATUS = ("DRAFT", "ASSIGNED", "IN_PROGRESS", "COMPLETED", "POSTPONED", "CANCELLED", "LATE")
TASK_PRIORITY = ("LOW", "NORMAL", "HIGH", "CRITICAL")
INCIDENT_SEVERITY = ("MINOR", "MODERATE", "MAJOR", "CRITICAL")
INCIDENT_STATUS = ("OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED")
INCIDENT_ACTION_TYPE = ("COMMENT", "STATUS_CHANGE", "ASSIGNMENT", "RESOLUTION")
NOTIFICATION_TYPE = (
    "TASK_ASSIGNED",
    "TASK_DUE_SOON",
    "TASK_LATE",
    "TASK_COMMENTED",
    "INCIDENT_REPORTED",
    "INCIDENT_RESOLVED",
)

_ENUMS = {
    "task_status": TASK_STATUS,
    "task_priority": TASK_PRIORITY,
    "incident_severity": INCIDENT_SEVERITY,
    "incident_status": INCIDENT_STATUS,
    "incident_action_type": INCIDENT_ACTION_TYPE,
    "notification_type": NOTIFICATION_TYPE,
}


def _enum(name: str) -> postgresql.ENUM:
    """Reference un type ENUM deja cree - jamais recree par create_table."""
    return postgresql.ENUM(*_ENUMS[name], name=name, create_type=False)


def _uuid_pk() -> sa.Column:
    return sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True)


def _fk_user(name: str, *, nullable: bool = True, ondelete: str = "SET NULL") -> sa.Column:
    return sa.Column(
        name,
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete=ondelete),
        nullable=nullable,
    )


def _attachment_columns(parent: str) -> list[sa.Column]:
    return [
        _uuid_pk(),
        sa.Column(
            f"{parent}_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{parent}s.id", ondelete="CASCADE"),
            nullable=False,
        ),
        _fk_user("uploaded_by_id"),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("stored_name", sa.String(255), nullable=False, unique=True),
        sa.Column("content_type", sa.String(150), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    ]


def upgrade() -> None:
    for name, values in _ENUMS.items():
        rendered = ", ".join(f"'{value}'" for value in values)
        op.execute(f"CREATE TYPE {name} AS ENUM ({rendered})")

    # ------------------------------------------------------------------ taches
    op.create_table(
        "task_templates",
        _uuid_pk(),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "default_priority", _enum("task_priority"), nullable=False, server_default="NORMAL"
        ),
        sa.Column(
            "site_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sites.id"),
            nullable=False,
        ),
        sa.Column("rrule", sa.String(500), nullable=True),
        sa.Column("estimated_minutes", sa.Integer(), nullable=True),
        sa.Column("checklist_labels", postgresql.JSONB(), nullable=True),
        sa.Column("default_assignee_ids", postgresql.JSONB(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_generated_at", sa.DateTime(timezone=True), nullable=True),
        _fk_user("created_by_id"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_task_templates_site_id", "task_templates", ["site_id"])

    op.create_table(
        "tasks",
        _uuid_pk(),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", _enum("task_status"), nullable=False, server_default="DRAFT"),
        sa.Column("priority", _enum("task_priority"), nullable=False, server_default="NORMAL"),
        sa.Column(
            "site_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sites.id"),
            nullable=False,
        ),
        sa.Column(
            "template_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("task_templates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        _fk_user("created_by_id"),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("postponed_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("estimated_minutes", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_priority", "tasks", ["priority"])
    op.create_index("ix_tasks_site_id", "tasks", ["site_id"])
    op.create_index("ix_tasks_due_at", "tasks", ["due_at"])
    # Index de travail du job de detection des retards et du dashboard :
    # ne porte que sur les taches vivantes et non terminees.
    op.execute(
        """
        CREATE INDEX ix_tasks_open_due_at ON tasks (due_at)
        WHERE deleted_at IS NULL AND status NOT IN ('COMPLETED', 'CANCELLED')
        """
    )

    op.create_table(
        "task_assignments",
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        _fk_user("assigned_by_id"),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_task_assignments_user_id", "task_assignments", ["user_id"])

    op.create_table(
        "task_comments",
        _uuid_pk(),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        _fk_user("author_id"),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_task_comments_task_id", "task_comments", ["task_id"])

    op.create_table("task_attachments", *_attachment_columns("task"))
    op.create_index("ix_task_attachments_task_id", "task_attachments", ["task_id"])

    op.create_table(
        "task_checklist_items",
        _uuid_pk(),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("label", sa.String(300), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_done", sa.Boolean(), nullable=False, server_default=sa.false()),
        _fk_user("done_by_id"),
        sa.Column("done_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_task_checklist_items_task_id", "task_checklist_items", ["task_id"])

    op.create_table(
        "task_dependencies",
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "depends_on_task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("task_id <> depends_on_task_id", name="ck_task_dependency_not_self"),
    )

    op.create_table(
        "task_status_history",
        _uuid_pk(),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_status", _enum("task_status"), nullable=True),
        sa.Column("to_status", _enum("task_status"), nullable=False),
        _fk_user("changed_by_id"),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_task_status_history_task_id", "task_status_history", ["task_id"])

    # --------------------------------------------------------------- incidents
    op.create_table(
        "incidents",
        _uuid_pk(),
        sa.Column("reference", sa.String(20), nullable=False, unique=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", _enum("incident_severity"), nullable=False),
        sa.Column("status", _enum("incident_status"), nullable=False, server_default="OPEN"),
        sa.Column(
            "site_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sites.id"),
            nullable=False,
        ),
        _fk_user("reported_by_id"),
        _fk_user("assigned_to_id"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_incidents_reference", "incidents", ["reference"])
    op.create_index("ix_incidents_severity", "incidents", ["severity"])
    op.create_index("ix_incidents_status", "incidents", ["status"])
    op.create_index("ix_incidents_site_id", "incidents", ["site_id"])

    op.create_table(
        "incident_actions",
        _uuid_pk(),
        sa.Column(
            "incident_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        _fk_user("author_id"),
        sa.Column("action_type", _enum("incident_action_type"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_incident_actions_incident_id", "incident_actions", ["incident_id"])

    op.create_table("incident_attachments", *_attachment_columns("incident"))
    op.create_index("ix_incident_attachments_incident_id", "incident_attachments", ["incident_id"])

    # ----------------------------------------------------- notifications / conf
    op.create_table(
        "notifications",
        _uuid_pk(),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", _enum("notification_type"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.Column("resource_id", sa.String(100), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.execute(
        """
        CREATE INDEX ix_notifications_unread ON notifications (user_id, created_at DESC)
        WHERE read_at IS NULL
        """
    )

    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", postgresql.JSONB(), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        _fk_user("updated_by_id"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    _sync_rbac_matrix()


def _sync_rbac_matrix() -> None:
    """Aligne permissions/role_permissions sur la matrice courante, sans doublon."""
    bind = op.get_bind()

    for code in sorted(all_permission_codes()):
        bind.execute(
            sa.text(
                """
                INSERT INTO permissions (id, code, description)
                VALUES (gen_random_uuid(), :code, :description)
                ON CONFLICT (code) DO UPDATE SET description = EXCLUDED.description
                """
            ),
            {"code": code, "description": PERMISSION_DESCRIPTIONS.get(code)},
        )

    for role_name, codes in ROLE_PERMISSIONS.items():
        for code in sorted(codes):
            bind.execute(
                sa.text(
                    """
                    INSERT INTO role_permissions (role_id, permission_id)
                    SELECT r.id, p.id
                    FROM roles r, permissions p
                    WHERE r.name = :role_name AND p.code = :code
                    ON CONFLICT DO NOTHING
                    """
                ),
                {"role_name": role_name, "code": code},
            )


def downgrade() -> None:
    op.drop_table("system_settings")
    op.execute("DROP INDEX IF EXISTS ix_notifications_unread")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")

    op.drop_index("ix_incident_attachments_incident_id", table_name="incident_attachments")
    op.drop_table("incident_attachments")
    op.drop_index("ix_incident_actions_incident_id", table_name="incident_actions")
    op.drop_table("incident_actions")
    for index in ("site_id", "status", "severity", "reference"):
        op.drop_index(f"ix_incidents_{index}", table_name="incidents")
    op.drop_table("incidents")

    op.drop_index("ix_task_status_history_task_id", table_name="task_status_history")
    op.drop_table("task_status_history")
    op.drop_table("task_dependencies")
    op.drop_index("ix_task_checklist_items_task_id", table_name="task_checklist_items")
    op.drop_table("task_checklist_items")
    op.drop_index("ix_task_attachments_task_id", table_name="task_attachments")
    op.drop_table("task_attachments")
    op.drop_index("ix_task_comments_task_id", table_name="task_comments")
    op.drop_table("task_comments")
    op.drop_index("ix_task_assignments_user_id", table_name="task_assignments")
    op.drop_table("task_assignments")
    op.execute("DROP INDEX IF EXISTS ix_tasks_open_due_at")
    for index in ("due_at", "site_id", "priority", "status"):
        op.drop_index(f"ix_tasks_{index}", table_name="tasks")
    op.drop_table("tasks")
    op.drop_index("ix_task_templates_site_id", table_name="task_templates")
    op.drop_table("task_templates")

    for name in _ENUMS:
        op.execute(f"DROP TYPE IF EXISTS {name}")

    # Les permissions/role_permissions ajoutees ne sont pas retirees : un
    # downgrade ne doit pas silencieusement retirer des droits en base.
