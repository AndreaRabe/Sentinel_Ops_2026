"""Verification de la troisieme barriere d'immutabilite : le trigger PostgreSQL.

Les deux premieres barrieres (permissions, absence de code de mutation) sont
couvertes par tests/unit/test_audit_immutability.py. Celle-ci ne peut etre
verifiee que contre une vraie base : ce test est donc ignore tant que
TEST_DATABASE_URL n'est pas defini et que les migrations n'y ont pas ete
appliquees (`make migrate`).
"""

import uuid

import pytest
from sqlalchemy import text

from app.db.session import SessionLocal
from tests.conftest import requires_database

pytestmark = [pytest.mark.integration, requires_database]


async def _insert_entry(session) -> uuid.UUID:
    entry_id = uuid.uuid4()
    await session.execute(
        text(
            """
            INSERT INTO audit_logs (id, action, resource_type, resource_id)
            VALUES (:id, 'test.trigger', 'test', :resource_id)
            """
        ),
        {"id": entry_id, "resource_id": str(entry_id)},
    )
    return entry_id


async def test_update_on_audit_logs_is_rejected():
    async with SessionLocal() as session:
        entry_id = await _insert_entry(session)
        with pytest.raises(Exception, match="append-only"):
            await session.execute(
                text("UPDATE audit_logs SET action = 'falsifie' WHERE id = :id"),
                {"id": entry_id},
            )
        await session.rollback()


async def test_delete_on_audit_logs_is_rejected():
    async with SessionLocal() as session:
        entry_id = await _insert_entry(session)
        with pytest.raises(Exception, match="append-only"):
            await session.execute(text("DELETE FROM audit_logs WHERE id = :id"), {"id": entry_id})
        await session.rollback()
