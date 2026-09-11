"""Skill identity + 버전 + 버전 종속 매핑(alias / tool).

불변식(코드가 아니라 **DB 가** 강제하는 것):

1. ``skills.skill_key`` 는 unique 다. machine identifier 이므로 사실상 immutable 로 다룬다
   (변경 API 를 만들지 않는다 — Codex thin router 와 MCP Tool 인자가 이 값을 문자 그대로 쓴다).
2. 한 Skill 에 ``PUBLISHED`` 버전은 **최대 1개**다 — 부분 unique index
   ``uq_skill_versions_one_published`` 가 강제한다. 애플리케이션 로직만으로 지키지 않는다.
3. ``(skill_id, version)`` 은 unique 하고 version 은 1부터 단조 증가한다.
4. alias / tool 매핑은 **version 종속**이다(skill 종속이 아니다). rollback 하면 그 버전의
   alias·tool 이 함께 돌아가야 하기 때문이다 — skill-level 에 두면 내용만 되돌아가고 라우팅과
   Tool 허용목록은 되돌아가지 않는다.

``skill_version_tools`` 는 **orchestration 정보**다. 사용자의 실제 Tool 권한 정본이 아니다 —
최종 인가는 언제나 Microsoft → DIDIM Auth → MCP gateway policy 가 한다(요구사항 §11).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin
from app.domain.enums import SkillVersionStatus


class Skill(UUIDPKMixin, TimestampMixin, Base):
    """Skill 의 정체성. 내용은 갖지 않는다(내용은 전부 버전에 있다)."""

    __tablename__ = "skills"

    #: Codex thin router 와 MCP Tool 인자가 쓰는 machine identifier. 안정적이어야 한다.
    skill_key: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    #: 화면 분류용 표시값(한글 허용). 인가·라우팅에 쓰지 않는다.
    category: Mapped[str | None] = mapped_column(String(60), nullable=True)
    #: 운영자 on/off. false 면 published 버전이 있어도 runtime 에 노출하지 않는다.
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    #: 현재 배포본 포인터. 편의용 캐시이며 **정본은 status=PUBLISHED 행**이다
    #: (부분 unique index 가 지키는 쪽). 둘은 같은 트랜잭션에서만 갱신한다.
    published_version_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("skill_versions.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
    )

    versions: Mapped[list[SkillVersion]] = relationship(
        back_populates="skill",
        foreign_keys="SkillVersion.skill_id",
        cascade="all, delete-orphan",
        order_by="SkillVersion.version",
    )
    published_version: Mapped[SkillVersion | None] = relationship(
        foreign_keys=[published_version_id], post_update=True, viewonly=True
    )

    __table_args__ = (
        Index("ix_skills_category", "category"),
        Index("ix_skills_enabled", "enabled"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Skill key={self.skill_key} enabled={self.enabled}>"


class SkillVersion(UUIDPKMixin, Base):
    """한 버전의 실제 workflow 내용. **불변에 가깝게 다룬다.**

    publish 이후 내용을 고치지 않는다 — 수정은 새 DRAFT 를 만들고, rollback 도 과거 행을
    되살리는 대신 그 내용을 담은 **새 버전**을 만들어 publish 한다. 그래야 이력이 파괴되지
    않는다(요구사항 §9).
    """

    __tablename__ = "skill_versions"

    skill_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False
    )
    #: 1부터 단조 증가. `(skill_id, version)` unique.
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    #: Codex 가 Skill 선택에 쓰는 문구. thin router 가 Registry 에서 읽어 그대로 전달한다.
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    #: 실제 workflow 본문(Markdown). **runtime source of truth 는 이 컬럼이다.**
    instructions: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[SkillVersionStatus] = mapped_column(
        Enum(
            SkillVersionStatus,
            native_enum=False,
            length=20,
            validate_strings=True,
            name="skill_version_status",
        ),
        nullable=False,
        default=SkillVersionStatus.DRAFT,
    )
    #: 감사용 행위자. Auth 사용자 UUID 문자열 + 그 시점 표시명(개인정보 최소 복제).
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_by_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    published_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    published_by_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: rollback 으로 만들어진 버전이면 원본 버전 번호. 화면과 감사에서 "v2 로 롤백" 을 설명한다.
    rolled_back_from: Mapped[int | None] = mapped_column(Integer, nullable=True)

    skill: Mapped[Skill] = relationship(back_populates="versions", foreign_keys=[skill_id])
    aliases: Mapped[list[SkillVersionAlias]] = relationship(
        back_populates="skill_version",
        cascade="all, delete-orphan",
        order_by="SkillVersionAlias.alias",
    )
    tools: Mapped[list[SkillVersionTool]] = relationship(
        back_populates="skill_version",
        cascade="all, delete-orphan",
        order_by="SkillVersionTool.tool_name",
    )

    __table_args__ = (
        UniqueConstraint("skill_id", "version", name="uq_skill_versions_skill_id_version"),
        # 한 Skill 에 PUBLISHED 는 하나뿐 — 동시 publish 가 들어와도 DB 가 두 번째를 거부한다.
        Index(
            "uq_skill_versions_one_published",
            "skill_id",
            unique=True,
            postgresql_where=text("status = 'PUBLISHED'"),
            sqlite_where=text("status = 'PUBLISHED'"),
        ),
        Index("ix_skill_versions_skill_id_status", "skill_id", "status"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SkillVersion skill={self.skill_id} v={self.version} {self.status}>"


class SkillVersionAlias(UUIDPKMixin, Base):
    """버전 종속 라우팅 alias. rollback 과 함께 돌아가야 하므로 skill-level 이 아니다."""

    __tablename__ = "skill_version_aliases"

    skill_version_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("skill_versions.id", ondelete="CASCADE"), nullable=False
    )
    alias: Mapped[str] = mapped_column(String(120), nullable=False)

    skill_version: Mapped[SkillVersion] = relationship(back_populates="aliases")

    __table_args__ = (
        UniqueConstraint(
            "skill_version_id", "alias", name="uq_skill_version_aliases_skill_version_id_alias"
        ),
        Index("ix_skill_version_aliases_alias", "alias"),
    )


class SkillVersionTool(UUIDPKMixin, Base):
    """이 workflow 가 사용하도록 **의도된** MCP Tool 목록.

    ⚠ 권한이 아니다. 여기 Tool 이름을 추가해도 그 사용자가 그 Tool 을 부를 수 있게 되지
    않는다 — 실제 인가는 MCP gateway 가 강제한다(요구사항 §11 / §34-14,15).
    """

    __tablename__ = "skill_version_tools"

    skill_version_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("skill_versions.id", ondelete="CASCADE"), nullable=False
    )
    tool_name: Mapped[str] = mapped_column(String(200), nullable=False)

    skill_version: Mapped[SkillVersion] = relationship(back_populates="tools")

    __table_args__ = (
        UniqueConstraint(
            "skill_version_id",
            "tool_name",
            name="uq_skill_version_tools_skill_version_id_tool_name",
        ),
    )


__all__ = ["Skill", "SkillVersion", "SkillVersionAlias", "SkillVersionTool"]
