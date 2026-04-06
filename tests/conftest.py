import os
from unittest.mock import AsyncMock

# Must be set before app.main is imported so the startup guard doesn't raise.
os.environ.setdefault("BALLDONTLIE_API_KEY", "test-api-key")
os.environ.setdefault("BALLDONTLIE_BASE_URL", "https://api.balldontlie.io/v1")
# Point at a dummy URL so SQLAlchemy doesn't try to reach a real postgres instance.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")

from app.db.database import get_session  # noqa: E402
from app.main import app  # noqa: E402


# ---------------------------------------------------------------------------
# Override get_session for the entire test suite.
# Endpoint tests don't need a real DB — they verify HTTP behaviour only.
# The mock session silently accepts commits and executes without connecting.
# ---------------------------------------------------------------------------
async def _mock_get_session():
    session = AsyncMock()
    yield session


app.dependency_overrides[get_session] = _mock_get_session
