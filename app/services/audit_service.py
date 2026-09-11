"""감사 기록 — 변경 작업만 남긴다.

`detail` 에 넣는 것은 **서비스가 조립한 구조화 값**뿐이다. 요청 본문·헤더·토큰을 통째로
넣지 않는다. instructions 본문도 넣지 않는다(버전 행에 이미 있고, 감사에 중복 보관할
이유가 없다).
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.principal import Principal
from app.db.models.audit import AuditLog
from app.db.models.skill import Skill, SkillVersion
from app.domain.enums import AuditOperation, AuditResult
from app.repositories.audit import AuditRepository

#: detail 에 절대 들어가면 안 되는 키. 조립 실수를 런타임에 잡는다.
_FORBIDDEN_DETAIL_KEYS = frozenset(
    {
        "authorization",
        "access_token",
        "refresh_token",
        "token",
        "password",
        "secret",
        "cookie",
        "api_key",
        "apikey",
        "instructions",
    }
)


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AuditRepository(session)

    async def record(
        self,
        actor: Principal,
        operation: AuditOperation,
        *,
        skill: Skill | None,
        version: SkillVersion | None,
        detail: dict[str, object] | None = None,
        result: AuditResult = AuditResult.SUCCESS,
    ) -> None:
        safe = _sanitize(detail)
        entry = AuditLog(
            actor_user_id=actor.user_id,
            actor_display_name=actor.display_name,
            operation=operation,
            skill_id=skill.id if skill else None,
            skill_key=skill.skill_key if skill else None,
            skill_version_id=version.id if version else None,
            skill_version=version.version if version else None,
            result=result,
            detail=safe,
        )
        self.repo.add(entry)
        await self.session.flush()

    async def list_page(
        self,
        *,
        skill_id: uuid.UUID | None = None,
        operation: AuditOperation | None = None,
        result: AuditResult | None = None,
        page: int,
        page_size: int,
    ) -> tuple[Sequence[AuditLog], int]:
        return await self.repo.list_page(
            skill_id=skill_id,
            operation=operation,
            result=result,
            page=page,
            page_size=page_size,
        )


def _sanitize(detail: dict[str, object] | None) -> dict[str, object] | None:
    """금지 키를 떨어뜨린다. 값이 아니라 **키**로 거른다(값 검사는 오탐이 많다)."""
    if not detail:
        return None
    cleaned = {k: v for k, v in detail.items() if k.lower() not in _FORBIDDEN_DETAIL_KEYS}
    return cleaned or None


__all__ = ["AuditService"]
