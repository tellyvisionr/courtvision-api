from logging.config import fileConfig
import os

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.db.models import Base  # noqa: F401 — registers all ORM models

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Build a sync URL from DATABASE_URL (which may use asyncpg).
_raw_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/courtvision")
_sync_url = _raw_url.replace("+asyncpg", "").replace("postgresql+asyncpg", "postgresql")
config.set_main_option("sqlalchemy.url", _sync_url)


def run_migrations_offline() -> None:
    """Emit SQL to stdout without a live DB connection."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
