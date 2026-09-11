"""Alembic 환경.

- DB URL 은 `alembic.ini` 가 아니라 `DIDIM_SKILL_*` 환경변수에서 만든다(자격증명 미커밋).
- `include_schemas`/`version_table_schema` 로 **`mcp_skill_registry` 밖은 건드리지 않는다.**
  다른 DIDIM schema(didim_mcp / didim_vault / didim_mcp_auth / didim_rag / public)를
  autogenerate 가 "삭제 대상" 으로 오인하는 사고를 막는다.
- schema 가 없으면 만든다. **DROP SCHEMA 는 어떤 경로로도 실행하지 않는다.**
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings
from app.db.models import Base
from app.db.schema import DATABASE_SCHEMA

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

_settings = get_settings()
_url = _settings.database_url
if _url is None:
    raise RuntimeError(
        "database is not configured; set DIDIM_SKILL_DB_HOST/PORT/USER/PASSWORD/NAME"
    )
config.set_main_option("sqlalchemy.url", _url)


def _include_object(
    obj: object, name: str | None, type_: str, reflected: bool, compare_to: object
) -> bool:
    schema = getattr(obj, "schema", None)
    return schema in (None, DATABASE_SCHEMA)


def _configure(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        include_object=_include_object,
        version_table="alembic_version",
        version_table_schema=DATABASE_SCHEMA,
        compare_type=True,
    )


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        include_schemas=True,
        include_object=_include_object,
        version_table_schema=DATABASE_SCHEMA,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_migrations(connection: Connection) -> None:
    connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{DATABASE_SCHEMA}"'))
    _configure(connection)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(_do_migrations)
        await connection.commit()
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
