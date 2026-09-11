"""감사 로그 — Skill 변경 작업의 기록.

담는 것: 누가(행위자 id + 그 시점 표시명), 무엇을(operation + 대상), 결과, 안전한 상세.

**절대 담지 않는 것**: access/refresh token, Authorization 헤더, 세션 쿠키, DB 비밀번호,
actor secret. `detail` 은 서비스가 조립한 구조화 값만 넣고 요청 본문을 통째로 넣지 않는다
(요구사항 §8 · §34-15).

조회(GET)는 감사하지 않는다 — runtime 조회가 압도적으로 많아 잡음만 된다. 변경만 남긴다.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPKMixin
from app.domain.enums import AuditOperation, AuditResult


class AuditLog(UUIDPKMixin, Base):
    __tablename__ = "audit_logs"

    #: Auth 사용자 UUID(문자열). 이 서비스는 사용자 테이블을 복제하지 않으므로 FK 가 없다.
    actor_user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    #: 그 시점의 표시명. 나중에 Auth 를 조회하지 않아도 이력이 읽히게 하기 위한 최소 사본이다.
    actor_display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    operation: Mapped[AuditOperation] = mapped_column(
        Enum(
            AuditOperation,
            native_enum=False,
            length=32,
            validate_strings=True,
            name="audit_operation",
        ),
        nullable=False,
    )
    #: 대상. Skill 이 삭제돼도 이력은 남아야 하므로 FK 를 걸지 않는다.
    skill_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    skill_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    skill_version_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    skill_version: Mapped[int | None] = mapped_column(nullable=True)
    result: Mapped[AuditResult] = mapped_column(
        Enum(AuditResult, native_enum=False, length=16, validate_strings=True, name="audit_result"),
        nullable=False,
    )
    #: 구조화된 안전 상세(예: {"from": 2, "to": 3}). Secret 을 넣지 않는다.
    #: 운영은 PostgreSQL JSONB 다. SQLite(단위 테스트)에는 JSONB 가 없어 JSON 으로 내려간다
    #: — 저장 형식만 다르고 계약은 같다.
    detail: Mapped[dict[str, object] | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_skill_id", "skill_id"),
        Index("ix_audit_logs_operation", "operation"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AuditLog {self.operation} {self.result} skill={self.skill_key}>"


__all__ = ["AuditLog"]
