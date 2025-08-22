from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
from .config import settings
from .models import Base
import aiosqlite

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL.replace('sqlite:///', 'sqlite+aiosqlite:///'),
    echo=False,
    future=True
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    """
    Create all database tables defined on Base.metadata.
    
    This async function opens a transactional engine connection and creates any missing tables
    for the declarative models registered on `Base`. Await this function during application
    startup to ensure the schema exists before handling requests.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@asynccontextmanager
async def get_db_session():
    """
    Asynchronous context manager that yields an AsyncSession for performing database operations.
    
    Yields:
        AsyncSession: an asynchronous SQLAlchemy session from the session factory.
    
    Behavior:
        - Commits the transaction after the caller completes successfully.
        - Rolls back the transaction and re-raises any exception raised by the caller.
        - Ensures the session is closed in all cases.
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