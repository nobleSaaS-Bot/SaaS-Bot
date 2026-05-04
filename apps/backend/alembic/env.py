import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from app.database import Base
import models.business
import models.store
import models.category
import models.product
import models.order
import models.session
import models.flow
import models.payment
import models.subscription
import models.customer
import models.broadcast
import models.bot_config

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override URL from environment so we never hardcode credentials.
# asyncpg does not accept sslmode in the URL — strip it and pass ssl=False via
# connect_args instead (Replit's internal Postgres doesn't require TLS).
_raw_url = os.environ.get("DATABASE_URL", "")
if _raw_url:
    from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
    _parsed = urlparse(_raw_url)
    _qs = {k: v for k, v in parse_qs(_parsed.query).items() if k != "sslmode"}
    _clean = _parsed._replace(
        scheme="postgresql+asyncpg",
        query=urlencode({k: v[0] for k, v in _qs.items()}),
    )
    config.set_main_option("sqlalchemy.url", urlunparse(_clean))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
