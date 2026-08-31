"""Async SQLAlchemy engine/session setup."""
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.config import settings
from app.database.models import Base


def _normalized_db_url(url: str) -> str:
    """
    Supabase/most providers give you a plain 'postgresql://...' connection
    string. SQLAlchemy's async engine needs the asyncpg driver specified
    explicitly: 'postgresql+asyncpg://...'. This lets you paste either
    format into DATABASE_URL and it just works.
    """
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


engine = create_async_engine(_normalized_db_url(settings.DATABASE_URL), echo=False)
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    """Create tables if they don't exist. Call once on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # create_all() never alters an already-existing table, so a brand
        # new column on an existing model (like is_primary_confirmed) needs
        # its own migration. IF NOT EXISTS makes this safe to run every
        # startup, on a fresh table or an old one.
        try:
            await conn.execute(
                text(
                    "ALTER TABLE threads "
                    "ADD COLUMN IF NOT EXISTS is_primary_confirmed BOOLEAN NOT NULL DEFAULT FALSE"
                )
            )
        except Exception:
            # e.g. running on SQLite locally, which doesn't support this
            # syntax - harmless there since create_all already made the
            # column correctly on a fresh table.
            pass


@asynccontextmanager
async def get_session():
    async with SessionLocal() as session:
        yield session
