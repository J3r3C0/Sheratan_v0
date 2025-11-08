"""Database configuration and connection"""
import os
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator
import logging

logger = logging.getLogger(__name__)

# Database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://sheratan:sheratan@localhost:5432/sheratan"
)

# Convert to async URL if not already
if DATABASE_URL.startswith("postgresql://"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
else:
    ASYNC_DATABASE_URL = DATABASE_URL

# Base class for models
Base = declarative_base()

# Pool configuration
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))

# Echo SQL queries if DEBUG is set
ECHO_SQL = os.getenv("DB_ECHO", "false").lower() == "true"

# Sync engine (for migrations)
sync_engine = create_engine(
    DATABASE_URL,
    echo=ECHO_SQL,
    pool_pre_ping=True,  # Verify connections before using
)

# Async engine (for application)
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=ECHO_SQL,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_recycle=POOL_RECYCLE,
    pool_pre_ping=True,
)

# Async session factory
AsyncSessionLocal = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database session
    
    Usage in FastAPI:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database (create tables)"""
    logger.info("Initializing database...")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized successfully")


async def close_db():
    """Close database connections"""
    logger.info("Closing database connections...")
    await async_engine.dispose()
    logger.info("Database connections closed")


def check_pgvector_extension():
    """Check if pgvector extension is installed"""
    from sqlalchemy import text
    try:
        with sync_engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM pg_extension WHERE extname = 'vector'"))
            if result.rowcount > 0:
                logger.info("pgvector extension is installed")
                return True
            else:
                logger.warning("pgvector extension is NOT installed")
                return False
    except Exception as e:
        logger.error(f"Error checking pgvector extension: {e}")
        return False

