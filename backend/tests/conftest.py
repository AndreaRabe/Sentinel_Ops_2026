"""Configuration commune des tests.

Les variables d'environnement obligatoires sont posees ICI, avant tout import
de `app.*` : `Settings` est instancie au moment de l'import du module de
configuration, et sans ces valeurs la simple collecte des tests echouerait
(y compris en CI, ou aucun `.env` n'existe).

Les valeurs sont volontairement factices : les tests unitaires n'ouvrent
aucune connexion. Les tests qui ont besoin d'une vraie base sont marques
`@pytest.mark.integration` et sautes si TEST_DATABASE_URL n'est pas defini.
"""

import os

os.environ.setdefault(
    "DATABASE_URL",
    os.environ.get(
        "TEST_DATABASE_URL", "postgresql+asyncpg://sentinel:sentinel@localhost:5432/sentinel_test"
    ),
)
os.environ.setdefault("JWT_SECRET_KEY", "0" * 64)
os.environ.setdefault("SCHEDULER_ENABLED", "false")

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.main import app  # noqa: E402

#: Presence d'une base de test reelle - conditionne les tests d'integration.
HAS_TEST_DATABASE = bool(os.environ.get("TEST_DATABASE_URL"))

requires_database = pytest.mark.skipif(
    not HAS_TEST_DATABASE,
    reason="TEST_DATABASE_URL non defini : test d'integration ignore.",
)


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "integration: test necessitant une base PostgreSQL reelle.")


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
