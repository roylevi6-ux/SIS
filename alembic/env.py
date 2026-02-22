"""Alembic environment configuration for SIS database migrations.

Reads DATABASE_URL from sis.config (which loads from .env / environment).
Uses Base.metadata from sis.db.models for autogenerate support.
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

from sis.config import DATABASE_URL
from sis.db.models import Base

# This is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Override sqlalchemy.url from sis.config (env var / .env file)
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# MetaData object for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Configures the context with just a URL and not an Engine,
    so a DBAPI is not required. Emits SQL to script output.
    """
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
    """Run migrations in 'online' mode.

    Creates an Engine and associates a connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
