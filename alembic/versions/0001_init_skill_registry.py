"""mcp_skill_registry schema 초기 생성.

이 프로젝트가 `mcp_skill_registry` schema 의 **유일한 migration owner** 다. 다른 DIDIM
저장소는 이 schema 를 소유하지 않는다.

생성물:
  skills                  Skill identity
  skill_versions          버전별 실제 workflow
  skill_version_aliases   버전 종속 라우팅 alias
  skill_version_tools     버전 종속 Tool 허용목록(orchestration 정보 — 권한 아님)
  audit_logs              변경 이력

핵심 제약:
  - `skills.skill_key` unique
  - `(skill_id, version)` unique
  - **부분 unique index `uq_skill_versions_one_published`** — 한 Skill 에 PUBLISHED 는 하나뿐.
    애플리케이션 로직이 아니라 DB 가 동시 publish 를 거부한다.

Revision ID: 0001_init_skill_registry
Revises:
Create Date: 2026-09-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_init_skill_registry"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "mcp_skill_registry"

_STATUS = sa.Enum(
    "DRAFT",
    "PUBLISHED",
    "SUPERSEDED",
    name="skill_version_status",
    native_enum=False,
    length=20,
    create_constraint=True,
)
_OPERATION = sa.Enum(
    "SKILL_CREATE",
    "SKILL_ENABLE",
    "SKILL_DISABLE",
    "DRAFT_CREATE",
    "DRAFT_UPDATE",
    "DRAFT_DELETE",
    "PUBLISH",
    "ROLLBACK",
    name="audit_operation",
    native_enum=False,
    length=32,
    create_constraint=True,
)
_RESULT = sa.Enum(
    "SUCCESS",
    "FAILED",
    "DENIED",
    name="audit_result",
    native_enum=False,
    length=16,
    create_constraint=True,
)


def upgrade() -> None:
    op.execute(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"')

    op.create_table(
        "skills",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("skill_key", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=60), nullable=True),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        # published_version_id 의 FK 는 skill_versions 생성 뒤에 건다(순환 참조).
        sa.Column("published_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_skills"),
        sa.UniqueConstraint("skill_key", name="uq_skills_skill_key"),
        schema=SCHEMA,
    )
    op.create_index("ix_skills_category", "skills", ["category"], schema=SCHEMA)
    op.create_index("ix_skills_enabled", "skills", ["enabled"], schema=SCHEMA)

    op.create_table(
        "skill_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("skill_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("instructions", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", _STATUS, nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("created_by_name", sa.String(length=200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("published_by", sa.String(length=64), nullable=True),
        sa.Column("published_by_name", sa.String(length=200), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rolled_back_from", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_skill_versions"),
        sa.ForeignKeyConstraint(
            ["skill_id"],
            [f"{SCHEMA}.skills.id"],
            name="fk_skill_versions_skill_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("skill_id", "version", name="uq_skill_versions_skill_id_version"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_skill_versions_skill_id_status",
        "skill_versions",
        ["skill_id", "status"],
        schema=SCHEMA,
    )
    # 한 Skill 에 PUBLISHED 는 하나뿐 — 동시 publish 의 최후 방어선.
    op.create_index(
        "uq_skill_versions_one_published",
        "skill_versions",
        ["skill_id"],
        unique=True,
        schema=SCHEMA,
        postgresql_where=sa.text("status = 'PUBLISHED'"),
    )
    op.create_foreign_key(
        "fk_skills_published_version_id",
        "skills",
        "skill_versions",
        ["published_version_id"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
        ondelete="SET NULL",
    )

    op.create_table(
        "skill_version_aliases",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("skill_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alias", sa.String(length=120), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_skill_version_aliases"),
        sa.ForeignKeyConstraint(
            ["skill_version_id"],
            [f"{SCHEMA}.skill_versions.id"],
            name="fk_skill_version_aliases_skill_version_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "skill_version_id", "alias", name="uq_skill_version_aliases_skill_version_id_alias"
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_skill_version_aliases_alias", "skill_version_aliases", ["alias"], schema=SCHEMA
    )

    op.create_table(
        "skill_version_tools",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("skill_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tool_name", sa.String(length=200), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_skill_version_tools"),
        sa.ForeignKeyConstraint(
            ["skill_version_id"],
            [f"{SCHEMA}.skill_versions.id"],
            name="fk_skill_version_tools_skill_version_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "skill_version_id",
            "tool_name",
            name="uq_skill_version_tools_skill_version_id_tool_name",
        ),
        schema=SCHEMA,
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_user_id", sa.String(length=64), nullable=True),
        sa.Column("actor_display_name", sa.String(length=200), nullable=True),
        sa.Column("operation", _OPERATION, nullable=False),
        sa.Column("skill_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("skill_key", sa.String(length=120), nullable=True),
        sa.Column("skill_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("skill_version", sa.Integer(), nullable=True),
        sa.Column("result", _RESULT, nullable=False),
        sa.Column("detail", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_audit_logs"),
        schema=SCHEMA,
    )
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"], schema=SCHEMA)
    op.create_index("ix_audit_logs_skill_id", "audit_logs", ["skill_id"], schema=SCHEMA)
    op.create_index("ix_audit_logs_operation", "audit_logs", ["operation"], schema=SCHEMA)


def downgrade() -> None:
    # schema 자체는 지우지 않는다(DROP SCHEMA 금지). 테이블만 되돌린다.
    op.drop_table("audit_logs", schema=SCHEMA)
    op.drop_table("skill_version_tools", schema=SCHEMA)
    op.drop_table("skill_version_aliases", schema=SCHEMA)
    op.drop_constraint(
        "fk_skills_published_version_id", "skills", schema=SCHEMA, type_="foreignkey"
    )
    op.drop_table("skill_versions", schema=SCHEMA)
    op.drop_table("skills", schema=SCHEMA)
