"""Skill Registry 도메인 열거형.

모두 문자열 기반(`StrEnum`, name==value). DB 에는 PostgreSQL native enum 이 아니라
``Enum(..., native_enum=False)`` 로 매핑해 VARCHAR + CHECK 제약으로 저장한다
(didim-mcp-service-backend ADR-0002 와 같은 판단 — 값 추가에 ``ALTER TYPE`` 이 필요 없다).
"""

from __future__ import annotations

from enum import StrEnum


class SkillVersionStatus(StrEnum):
    """Skill 버전의 생애주기.

    - DRAFT: 편집 중. **runtime 에 절대 노출되지 않는다.**
    - PUBLISHED: 현재 배포본. 한 Skill 당 **최대 1개**(부분 unique index 로 DB 가 강제).
    - SUPERSEDED: 과거 배포본. 이력이며 삭제하지 않는다.
    """

    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    SUPERSEDED = "SUPERSEDED"


class AuditOperation(StrEnum):
    """감사 대상 변경 작업. 조회는 감사하지 않는다(runtime 조회가 대부분이라 잡음이 된다)."""

    SKILL_CREATE = "SKILL_CREATE"
    SKILL_ENABLE = "SKILL_ENABLE"
    SKILL_DISABLE = "SKILL_DISABLE"
    DRAFT_CREATE = "DRAFT_CREATE"
    DRAFT_UPDATE = "DRAFT_UPDATE"
    DRAFT_DELETE = "DRAFT_DELETE"
    PUBLISH = "PUBLISH"
    ROLLBACK = "ROLLBACK"


class AuditResult(StrEnum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    DENIED = "DENIED"


class UserRole(StrEnum):
    """중앙 사용자 role — **정본은 didim_mcp_auth.users.role** 이다(Auth ``/api/v1/me``).

    이 서비스는 사용자 계정을 복제하지 않는다. 여기 있는 것은 Auth 응답을 해석하기 위한
    사본일 뿐이며, 새 role 체계를 정의하지 않는다.
    """

    USER = "USER"
    DEVELOPER = "DEVELOPER"
    ADMIN = "ADMIN"


__all__ = ["AuditOperation", "AuditResult", "SkillVersionStatus", "UserRole"]
