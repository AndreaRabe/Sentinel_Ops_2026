"""Recurrence RRULE : bornes de generation et validation des regles."""

from datetime import datetime, timedelta, timezone

import pytest

from app.core.exceptions import BusinessRuleError
from app.jobs.recurrence import GENERATION_HORIZON, MAX_OCCURRENCES_PER_RUN, _occurrences
from app.services.task_template_service import validate_rrule

START = datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc)


def test_validate_accepts_a_standard_daily_rule():
    assert validate_rrule("FREQ=DAILY;INTERVAL=1") == "FREQ=DAILY;INTERVAL=1"


def test_validate_accepts_an_absent_rule():
    """Un modele sans RRULE est un simple modele reutilisable, pas une erreur."""
    assert validate_rrule(None) is None
    assert validate_rrule("") is None


def test_validate_rejects_a_malformed_rule():
    with pytest.raises(BusinessRuleError, match="recurrence invalide"):
        validate_rrule("FREQ=NEVER")


def test_daily_rule_generates_one_occurrence_per_day():
    occurrences = _occurrences("FREQ=DAILY", START, after=START, until=START + timedelta(days=5))
    assert len(occurrences) == 4  # bornes exclusives des deux cotes
    assert all(occurrence.hour == 8 for occurrence in occurrences)


def test_weekly_rule_respects_the_requested_weekday():
    occurrences = _occurrences(
        "FREQ=WEEKLY;BYDAY=MO", START, after=START, until=START + timedelta(days=28)
    )
    assert occurrences
    assert all(occurrence.weekday() == 0 for occurrence in occurrences)


def test_generation_is_bounded_by_the_cursor():
    """Le curseur `last_generated_at` evite de regenerer le passe deja traite."""
    cursor = START + timedelta(days=3)
    occurrences = _occurrences("FREQ=DAILY", START, after=cursor, until=START + timedelta(days=6))
    assert all(occurrence > cursor for occurrence in occurrences)


def test_catch_up_is_capped():
    """Une longue interruption ne doit pas creer des centaines de taches d'un coup."""
    occurrences = _occurrences("FREQ=HOURLY", START, after=START, until=START + timedelta(days=365))
    assert len(occurrences) == MAX_OCCURRENCES_PER_RUN


def test_generation_horizon_stays_short():
    """Materialiser trop en avance polluerait le backlog."""
    assert GENERATION_HORIZON <= timedelta(days=31)
