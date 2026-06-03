from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from src.config import get_settings


_engine = None
_session_factory = None


def init_db() -> None:
    global _engine, _session_factory
    settings = get_settings()

    _engine = create_async_engine(
        settings.database_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False,
    )
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def get_session() -> AsyncSession:
    if _session_factory is None:
        init_db()
    async with _session_factory() as session:
        yield session


async def close_db() -> None:
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None
