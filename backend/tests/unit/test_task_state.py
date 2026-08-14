"""Machine a etats des taches - piece la plus critique du domaine.

Ces tests couvrent la totalite du graphe de transitions declare dans le cahier
des charges (section 4) : chaque couple (depart, arrivee) est soit explicitement
autorise, soit explicitement refuse.
"""

import pytest

from app.core.exceptions import BusinessRuleError
from app.core.task_state import (
    ALLOWED_TRANSITIONS,
    assert_agent_transition,
    assert_transition,
    can_transition,
    is_terminal,
)
from app.models.enums import TaskStatus


def test_terminal_statuses_have_no_outgoing_transition():
    for status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
        assert is_terminal(status)
        assert ALLOWED_TRANSITIONS[status] == frozenset()


def test_every_status_is_declared_in_the_transition_table():
    # Garde-fou : ajouter une valeur a l'enum sans l'ajouter ici la rendrait
    # silencieusement inatteignable.
    assert set(ALLOWED_TRANSITIONS) == set(TaskStatus)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (TaskStatus.DRAFT, TaskStatus.ASSIGNED),
        (TaskStatus.DRAFT, TaskStatus.CANCELLED),
        (TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS),
        (TaskStatus.ASSIGNED, TaskStatus.POSTPONED),
        (TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED),
        (TaskStatus.POSTPONED, TaskStatus.IN_PROGRESS),
        (TaskStatus.LATE, TaskStatus.COMPLETED),
    ],
)
def test_allowed_transitions(current, target):
    assert can_transition(current, target)
    assert_transition(current, target, assignee_count=1)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        # On ne saute pas l'etape d'assignation.
        (TaskStatus.DRAFT, TaskStatus.IN_PROGRESS),
        (TaskStatus.DRAFT, TaskStatus.COMPLETED),
        # Une tache assignee n'est pas terminee sans etre passee en cours.
        (TaskStatus.ASSIGNED, TaskStatus.COMPLETED),
        # Les etats terminaux sont definitifs.
        (TaskStatus.COMPLETED, TaskStatus.IN_PROGRESS),
        (TaskStatus.COMPLETED, TaskStatus.CANCELLED),
        (TaskStatus.CANCELLED, TaskStatus.ASSIGNED),
    ],
)
def test_forbidden_transitions(current, target):
    assert not can_transition(current, target)
    with pytest.raises(BusinessRuleError):
        assert_transition(current, target, assignee_count=1)


def test_cancellation_is_possible_from_every_non_terminal_status():
    """« CANCELLED a tout moment avant COMPLETED » (cahier des charges section 4)."""
    for status in TaskStatus:
        if is_terminal(status):
            continue
        assert can_transition(status, TaskStatus.CANCELLED)


def test_transition_to_same_status_is_refused():
    with pytest.raises(BusinessRuleError, match="deja au statut"):
        assert_transition(TaskStatus.ASSIGNED, TaskStatus.ASSIGNED, assignee_count=1)


def test_late_cannot_be_set_manually():
    with pytest.raises(BusinessRuleError, match="automatiquement"):
        assert_transition(TaskStatus.ASSIGNED, TaskStatus.LATE, assignee_count=1)


def test_late_can_be_set_by_the_system():
    assert_transition(TaskStatus.ASSIGNED, TaskStatus.LATE, by_system=True, assignee_count=1)


def test_assignment_requires_at_least_one_assignee():
    with pytest.raises(BusinessRuleError, match="au moins un agent"):
        assert_transition(TaskStatus.DRAFT, TaskStatus.ASSIGNED, assignee_count=0)

    assert_transition(TaskStatus.DRAFT, TaskStatus.ASSIGNED, assignee_count=1)


def test_agent_can_close_a_task_without_blocking_validation():
    """Decision explicite : la cloture par l'agent ne demande aucune validation."""
    assert_agent_transition(TaskStatus.COMPLETED)


@pytest.mark.parametrize("target", [TaskStatus.ASSIGNED, TaskStatus.CANCELLED, TaskStatus.LATE])
def test_agent_cannot_use_management_transitions(target):
    with pytest.raises(BusinessRuleError):
        assert_agent_transition(target)
