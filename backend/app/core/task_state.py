"""Machine a etats d'une tache (cahier des charges section 4).

```
DRAFT -> ASSIGNED -> IN_PROGRESS -> COMPLETED
                  \\-> POSTPONED
                  \\-> CANCELLED (a tout moment avant COMPLETED)
         -> LATE (automatique si due_at depasse, statut != COMPLETED/CANCELLED)
```

Module pur, sans acces DB ni FastAPI : c'est la piece la plus critique du
domaine et elle doit rester testable isolement (cahier des charges section 12).
"""

from app.core.exceptions import BusinessRuleError
from app.models.enums import TaskStatus

#: Etats terminaux : plus aucune transition n'en sort.
TERMINAL_STATUSES: frozenset[TaskStatus] = frozenset({TaskStatus.COMPLETED, TaskStatus.CANCELLED})

#: Etats consideres comme "en cours de vie", eligibles au passage en retard.
OPEN_STATUSES: frozenset[TaskStatus] = frozenset(
    {TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS, TaskStatus.POSTPONED}
)

ALLOWED_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.DRAFT: frozenset({TaskStatus.ASSIGNED, TaskStatus.CANCELLED}),
    TaskStatus.ASSIGNED: frozenset(
        {TaskStatus.IN_PROGRESS, TaskStatus.POSTPONED, TaskStatus.CANCELLED, TaskStatus.LATE}
    ),
    TaskStatus.IN_PROGRESS: frozenset(
        {TaskStatus.COMPLETED, TaskStatus.POSTPONED, TaskStatus.CANCELLED, TaskStatus.LATE}
    ),
    TaskStatus.POSTPONED: frozenset(
        {TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED, TaskStatus.LATE}
    ),
    TaskStatus.LATE: frozenset(
        {
            TaskStatus.IN_PROGRESS,
            TaskStatus.COMPLETED,
            TaskStatus.POSTPONED,
            TaskStatus.CANCELLED,
        }
    ),
    TaskStatus.COMPLETED: frozenset(),
    TaskStatus.CANCELLED: frozenset(),
}

#: LATE n'est jamais choisi par un humain : seul le job de detection des retards
#: le pose (voir jobs/late_detection.py).
SYSTEM_ONLY_STATUSES: frozenset[TaskStatus] = frozenset({TaskStatus.LATE})

#: Transitions qu'un agent peut declencher sur SES taches via
#: task:update_own_status. La cloture (COMPLETED) en fait partie : elle ne
#: demande aucune validation bloquante d'un superieur (decision explicite du
#: cahier des charges section 4).
AGENT_ALLOWED_TARGETS: frozenset[TaskStatus] = frozenset(
    {TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED, TaskStatus.POSTPONED}
)


def is_terminal(status: TaskStatus) -> bool:
    return status in TERMINAL_STATUSES


def can_transition(current: TaskStatus, target: TaskStatus) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, frozenset())


def assert_transition(
    current: TaskStatus,
    target: TaskStatus,
    *,
    by_system: bool = False,
    assignee_count: int = 0,
) -> None:
    """Leve BusinessRuleError si la transition demandee est interdite."""
    if current == target:
        raise BusinessRuleError(f"La tache est deja au statut {target}.")

    if is_terminal(current):
        raise BusinessRuleError(
            f"Une tache {current} est definitive et ne peut plus changer de statut."
        )

    if not can_transition(current, target):
        raise BusinessRuleError(f"Transition interdite : {current} -> {target}.")

    if target in SYSTEM_ONLY_STATUSES and not by_system:
        raise BusinessRuleError(
            "Le statut LATE est pose automatiquement par le systeme, pas manuellement."
        )

    if target == TaskStatus.ASSIGNED and assignee_count == 0:
        raise BusinessRuleError("Assignez au moins un agent avant de passer la tache en ASSIGNED.")


def assert_agent_transition(target: TaskStatus) -> None:
    """Restriction supplementaire pour un porteur de task:update_own_status."""
    if target not in AGENT_ALLOWED_TARGETS:
        raise BusinessRuleError(
            "Vous ne pouvez faire evoluer vos taches que vers "
            f"{', '.join(sorted(AGENT_ALLOWED_TARGETS))}."
        )
