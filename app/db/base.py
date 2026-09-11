"""SQLAlchemy Declarative Base + 공통 mixin.

모든 테이블은 ``mcp_skill_registry`` schema 안에만 만든다 — ``MetaData(schema=...)`` 로
고정하므로 모델에 schema 를 따로 쓰지 않는다. 다른 DIDIM schema 는 이 metadata 에 없다.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.db.schema import DATABASE_SCHEMA

#: 제약/인덱스 이름 규칙. Alembic autogenerate 의 이름이 환경마다 갈라지지 않게 고정한다.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(schema=DATABASE_SCHEMA, naming_convention=NAMING_CONVENTION)


class UUIDPKMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


__all__ = ["NAMING_CONVENTION", "Base", "TimestampMixin", "UUIDPKMixin"]
