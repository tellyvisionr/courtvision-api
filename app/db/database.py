from collections.abc import AsyncGenerator
import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# asyncpg driver is required: pip install asyncpg
# Default points at the local Compose postgres service.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://courtvision:courtvision@localhost:5432/courtvision",
)

engine = create_async_engine(DATABASE_URL, echo=False)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency — yields a transactional async session."""
    async with AsyncSessionLocal() as session:
        yield session
