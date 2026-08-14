"""Verrouillage brute-force du login (cahier des charges section 7).

Le compteur est une fenetre glissante lue dans `audit_logs`. Ces tests
verifient la logique de fenetre et le declenchement du verrou en isolant le
service de la base : seul le comptage est simule.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.core.exceptions import AccountLockedError
from app.services import auth_service


class _FakeSession:
    """Session minimale : le service ne fait qu'un commit sur le chemin verrou."""

    def __init__(self):
        self.committed = False

    async def commit(self):
        self.committed = True


def _user(last_login_at=None):
    return SimpleNamespace(id="00000000-0000-0000-0000-000000000001", last_login_at=last_login_at)


@pytest.fixture
def audit_calls(monkeypatch):
    """Capture les ecritures d'audit et pilote le nombre d'echecs comptes."""
    recorded = {"failures": 0, "logged": []}

    async def fake_count(_db, _email, since):
        recorded["since"] = since
        return recorded["failures"]

    async def fake_log(_db, **kwargs):
        recorded["logged"].append(kwargs)

    monkeypatch.setattr(auth_service.audit_service, "count_failed_logins", fake_count)
    monkeypatch.setattr(auth_service.audit_service, "log_action", fake_log)
    return recorded


async def test_below_threshold_the_login_proceeds(audit_calls):
    audit_calls["failures"] = settings.login_max_attempts - 1
    await auth_service._assert_not_locked(_FakeSession(), "a@b.c", _user(), None)
    assert audit_calls["logged"] == []


async def test_at_threshold_the_account_is_locked(audit_calls):
    audit_calls["failures"] = settings.login_max_attempts
    with pytest.raises(AccountLockedError):
        await auth_service._assert_not_locked(_FakeSession(), "a@b.c", _user(), None)


async def test_locking_is_journalised_as_a_security_event(audit_calls):
    audit_calls["failures"] = settings.login_max_attempts + 3
    with pytest.raises(AccountLockedError):
        await auth_service._assert_not_locked(_FakeSession(), "a@b.c", _user(), None)

    assert len(audit_calls["logged"]) == 1
    entry = audit_calls["logged"][0]
    assert entry["action"] == "auth.login_blocked"
    assert entry["resource_id"] == "a@b.c"


async def test_unknown_email_is_also_rate_limited(audit_calls):
    """Sinon l'enumeration de comptes serait libre de toute limite."""
    audit_calls["failures"] = settings.login_max_attempts
    with pytest.raises(AccountLockedError):
        await auth_service._assert_not_locked(_FakeSession(), "inconnu@b.c", None, None)


async def test_window_is_bounded_by_the_configured_duration(audit_calls):
    audit_calls["failures"] = 0
    before = datetime.now(timezone.utc)
    await auth_service._assert_not_locked(_FakeSession(), "a@b.c", _user(), None)

    expected = before - timedelta(minutes=settings.login_lockout_minutes)
    # Tolerance d'une seconde : le service recalcule "maintenant" de son cote.
    assert abs((audit_calls["since"] - expected).total_seconds()) < 1


async def test_a_successful_login_resets_the_counting_window(audit_calls):
    """Des echecs anterieurs a une connexion reussie ne doivent plus compter."""
    audit_calls["failures"] = 0
    last_login = datetime.now(timezone.utc) - timedelta(minutes=2)
    await auth_service._assert_not_locked(_FakeSession(), "a@b.c", _user(last_login), None)

    assert audit_calls["since"] == last_login


async def test_an_old_successful_login_does_not_widen_the_window(audit_calls):
    """Une connexion reussie hors fenetre ne doit pas rallonger le comptage."""
    audit_calls["failures"] = 0
    old_login = datetime.now(timezone.utc) - timedelta(minutes=settings.login_lockout_minutes + 60)
    await auth_service._assert_not_locked(_FakeSession(), "a@b.c", _user(old_login), None)

    assert audit_calls["since"] > old_login
