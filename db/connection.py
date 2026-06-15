from __future__ import annotations

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config.settings import settings
from db.models import Base


def _get_db_path(url: str) -> Path | None:
    if url.startswith("sqlite"):
        path_str = url.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")
        if path_str:
            return Path(path_str)
    return None


db_path = _get_db_path(settings.database_url)
if db_path:
    db_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_async_engine(
    settings.database_url,
    echo=(settings.log_level == "DEBUG"),
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session


async def close_db() -> None:
    await engine.dispose()
