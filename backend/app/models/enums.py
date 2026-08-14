"""Enumerations metier - materialisees en types ENUM PostgreSQL natifs.

Choix assume : des types natifs plutot que des colonnes texte libres, pour que
l'integrite soit garantie par la base et pas seulement par l'application
(cahier des charges section 6 - "integrite stricte, contraintes avancees").
Toute valeur ajoutee ici impose donc un ALTER TYPE dans une migration dediee.
"""

from enum import StrEnum


class TaskStatus(StrEnum):
    """Machine a etats d'une tache (cahier des charges section 4)."""

    DRAFT = "DRAFT"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    POSTPONED = "POSTPONED"
    CANCELLED = "CANCELLED"
    LATE = "LATE"


class TaskPriority(StrEnum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IncidentSeverity(StrEnum):
    MINOR = "MINOR"
    MODERATE = "MODERATE"
    MAJOR = "MAJOR"
    CRITICAL = "CRITICAL"


class IncidentStatus(StrEnum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class IncidentActionType(StrEnum):
    COMMENT = "COMMENT"
    STATUS_CHANGE = "STATUS_CHANGE"
    ASSIGNMENT = "ASSIGNMENT"
    RESOLUTION = "RESOLUTION"


class NotificationType(StrEnum):
    TASK_ASSIGNED = "TASK_ASSIGNED"
    TASK_DUE_SOON = "TASK_DUE_SOON"
    TASK_LATE = "TASK_LATE"
    TASK_COMMENTED = "TASK_COMMENTED"
    INCIDENT_REPORTED = "INCIDENT_REPORTED"
    INCIDENT_RESOLVED = "INCIDENT_RESOLVED"


# Types SQLAlchemy partages entre modeles et migrations : nommer les ENUM
# explicitement evite qu'Alembic genere des noms differents d'une migration
# a l'autre.
TASK_STATUS_ENUM = "task_status"
TASK_PRIORITY_ENUM = "task_priority"
INCIDENT_SEVERITY_ENUM = "incident_severity"
INCIDENT_STATUS_ENUM = "incident_status"
INCIDENT_ACTION_TYPE_ENUM = "incident_action_type"
NOTIFICATION_TYPE_ENUM = "notification_type"
