"""Moteur et sessions SQLAlchemy.

Le moteur est cree PARESSEUSEMENT, au premier acces, et non a l'import du
module. Deux raisons :

- `create_async_engine` resout et importe le driver (asyncpg) des sa creation.
  A l'import, cela imposerait d'avoir asyncpg installe pour executer le moindre
  test unitaire, alors que ces tests ne touchent jamais la base.
- Cela laisse la possibilite de surcharger `DATABASE_URL` dans un test avant
  la premiere ouverture de session.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(settings.database_url, echo=False)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


class _LazySessionMaker:
    """Conserve l'usage historique `async with SessionLocal() as session:`.

    Sans ce proxy, chaque appelant devrait ecrire `get_session_factory()()`.
    """

    def __call__(self) -> AsyncSession:
        return get_session_factory()()


SessionLocal = _LazySessionMaker()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
