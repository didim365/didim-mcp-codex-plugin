"""Skill lifecycle — Draft / Publish / Rollback / Enable.

여기가 요구사항 §9 의 정본이다.

    Create  → v1 DRAFT               → Publish v1
    Edit    → v2 DRAFT (내용 복사)    → Publish v2  (v1 → SUPERSEDED)
    Rollback(v1) → v3 DRAFT?  아니다  → v1 내용으로 **새 v3 을 만들어 즉시 PUBLISHED**

**과거 행을 변형해 이력을 파괴하지 않는다.** rollback 은 옛 버전을 되살리는 것이 아니라
그 내용을 담은 새 버전을 만든다(`rolled_back_from` 에 원본 번호를 남긴다). 그래서 "언제
무엇으로 되돌렸는가" 가 버전 목록만 봐도 읽힌다.

Publish 원자성
--------------
1. `SELECT ... FOR UPDATE` 로 Skill 행을 잠근다 → 같은 Skill 의 동시 publish 가 줄을 선다.
2. 기존 PUBLISHED 를 SUPERSEDED 로 내리고 대상 버전을 PUBLISHED 로 올린 뒤 `flush` 한다.
3. DB 의 부분 unique index `uq_skill_versions_one_published` 가 최후 방어선이다 —
   잠금을 어떤 이유로 우회해도 두 번째 PUBLISHED 는 DB 가 거부한다.

Draft 는 한 Skill 에 **최대 1개**다. 두 관리자가 동시에 편집해 서로의 내용을 조용히 덮는
상황을 만들지 않기 위해서다(두 번째 요청은 409).
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dto import SkillCreateRequest, SkillVersionContent
from app.auth.principal import Principal
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.db.models.skill import Skill, SkillVersion, SkillVersionAlias, SkillVersionTool
from app.domain.enums import AuditOperation, SkillVersionStatus
from app.repositories.skill import SkillRepository, SkillVersionRepository
from app.services.audit_service import AuditService

logger = get_logger("services.skill")


class SkillService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.skills = SkillRepository(session)
        self.versions = SkillVersionRepository(session)
        self.audit = AuditService(session)

    # ── 조회 ──────────────────────────────────────────────

    async def get_or_404(self, skill_id: uuid.UUID) -> Skill:
        skill = await self.skills.get(skill_id)
        if skill is None:
            raise NotFoundError("해당 스킬을 찾을 수 없습니다.")
        return skill

    async def list_versions(self, skill_id: uuid.UUID) -> Sequence[SkillVersion]:
        await self.get_or_404(skill_id)
        return await self.versions.list_for_skill(skill_id)

    # ── 생성 ──────────────────────────────────────────────

    async def create_skill(self, req: SkillCreateRequest, actor: Principal) -> Skill:
        """Skill identity + v1 DRAFT. publish 는 별도 작업이다(즉시 노출하지 않는다)."""
        if await self.skills.get_by_key(req.skill_key) is not None:
            raise ConflictError(f"이미 존재하는 스킬 키입니다: {req.skill_key}")

        skill = Skill(skill_key=req.skill_key, category=req.category, enabled=True)
        self.skills.add(skill)
        await self.session.flush()  # skill.id 확보

        version = self._new_version(skill.id, 1, req, actor, status=SkillVersionStatus.DRAFT)
        self.versions.add(version)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            # skill_key unique 는 위에서 확인했지만 동시 생성이면 여기서 걸린다.
            raise ConflictError(f"이미 존재하는 스킬 키입니다: {req.skill_key}") from exc

        await self.audit.record(
            actor,
            AuditOperation.SKILL_CREATE,
            skill=skill,
            version=version,
            detail={"version": 1},
        )
        return await self.get_or_404(skill.id)

    async def create_draft(
        self, skill_id: uuid.UUID, req: SkillVersionContent | None, actor: Principal
    ) -> SkillVersion:
        """새 DRAFT. 내용을 주지 않으면 **현재 배포본을 복사**해 시작한다."""
        skill = await self.get_or_404(skill_id)
        existing = await self.versions.get_by_status(skill_id, SkillVersionStatus.DRAFT)
        if existing is not None:
            raise ConflictError(
                f"이미 편집 중인 초안(v{existing.version})이 있습니다. 먼저 배포하거나 삭제하세요."
            )

        if req is None:
            published = await self.versions.get_by_status(skill_id, SkillVersionStatus.PUBLISHED)
            if published is None:
                raise ValidationError("복사할 배포본이 없습니다. 초안 내용을 함께 보내세요.")
            req = _content_of(published)

        number = await self.versions.next_version(skill_id)
        version = self._new_version(skill.id, number, req, actor, status=SkillVersionStatus.DRAFT)
        self.versions.add(version)
        await self.session.flush()
        await self.audit.record(
            actor,
            AuditOperation.DRAFT_CREATE,
            skill=skill,
            version=version,
            detail={"version": number},
        )
        return version

    # ── 수정 ──────────────────────────────────────────────

    async def update_draft(
        self, skill_id: uuid.UUID, version_number: int, req: SkillVersionContent, actor: Principal
    ) -> SkillVersion:
        """DRAFT 만 수정한다. PUBLISHED/SUPERSEDED 는 **불변**이다(이력이므로)."""
        skill = await self.get_or_404(skill_id)
        version = await self.versions.get_by_number(skill_id, version_number)
        if version is None:
            raise NotFoundError(f"버전을 찾을 수 없습니다: v{version_number}")
        if version.status is not SkillVersionStatus.DRAFT:
            raise ConflictError("배포된 버전은 수정할 수 없습니다. 새 초안을 만드세요.")

        version.name = req.name
        version.description = req.description
        version.instructions = req.instructions
        version.updated_at = datetime.now(UTC)
        _replace_children(version, req)
        await self.session.flush()
        await self.audit.record(
            actor,
            AuditOperation.DRAFT_UPDATE,
            skill=skill,
            version=version,
            detail={"version": version_number},
        )
        return version

    async def delete_draft(
        self, skill_id: uuid.UUID, version_number: int, actor: Principal
    ) -> None:
        """DRAFT 폐기. 배포 이력은 어떤 경우에도 지우지 않는다."""
        skill = await self.get_or_404(skill_id)
        version = await self.versions.get_by_number(skill_id, version_number)
        if version is None:
            raise NotFoundError(f"버전을 찾을 수 없습니다: v{version_number}")
        if version.status is not SkillVersionStatus.DRAFT:
            raise ConflictError("배포 이력은 삭제할 수 없습니다.")
        await self.audit.record(
            actor,
            AuditOperation.DRAFT_DELETE,
            skill=skill,
            version=version,
            detail={"version": version_number},
        )
        await self.session.delete(version)
        await self.session.flush()

    # ── 배포 / 롤백 ───────────────────────────────────────

    async def publish(
        self, skill_id: uuid.UUID, version_number: int, actor: Principal
    ) -> SkillVersion:
        """DRAFT → PUBLISHED. 기존 배포본은 SUPERSEDED. 원자적이다."""
        skill = await self._lock_or_404(skill_id)
        target = await self.versions.get_by_number(skill_id, version_number)
        if target is None:
            raise NotFoundError(f"버전을 찾을 수 없습니다: v{version_number}")
        if target.status is SkillVersionStatus.PUBLISHED:
            raise ConflictError(f"v{version_number} 은(는) 이미 배포되어 있습니다.")
        if target.status is SkillVersionStatus.SUPERSEDED:
            raise ConflictError(
                f"v{version_number} 은(는) 지난 배포본입니다. 되돌리려면 롤백을 사용하세요."
            )
        previous = await self._demote_current(skill_id)
        await self._promote(skill, target, actor)
        await self.audit.record(
            actor,
            AuditOperation.PUBLISH,
            skill=skill,
            version=target,
            detail={"from": previous.version if previous else None, "to": target.version},
        )
        return target

    async def rollback(
        self, skill_id: uuid.UUID, source_version: int, actor: Principal
    ) -> SkillVersion:
        """과거 버전의 **내용으로 새 버전을 만들어** 즉시 배포한다.

        과거 행 자체를 되살리지 않는다 — 이력이 파괴되고 "언제 되돌렸는가" 가 사라지기 때문이다.
        """
        skill = await self._lock_or_404(skill_id)
        source = await self.versions.get_by_number(skill_id, source_version)
        if source is None:
            raise NotFoundError(f"버전을 찾을 수 없습니다: v{source_version}")
        if source.status is SkillVersionStatus.DRAFT:
            raise ConflictError("초안으로는 롤백할 수 없습니다. 초안은 배포하세요.")
        if source.status is SkillVersionStatus.PUBLISHED:
            raise ConflictError(f"v{source_version} 은(는) 이미 현재 배포본입니다.")

        # 편집 중인 초안이 있으면 그대로 둔다 — 롤백이 남의 작업을 지우지 않는다.
        number = await self.versions.next_version(skill_id)
        content = _content_of(source)
        new_version = self._new_version(
            skill.id, number, content, actor, status=SkillVersionStatus.DRAFT
        )
        new_version.rolled_back_from = source_version
        self.versions.add(new_version)
        await self.session.flush()

        previous = await self._demote_current(skill_id)
        await self._promote(skill, new_version, actor)
        await self.audit.record(
            actor,
            AuditOperation.ROLLBACK,
            skill=skill,
            version=new_version,
            detail={
                "source_version": source_version,
                "from": previous.version if previous else None,
                "to": number,
            },
        )
        return new_version

    async def set_enabled(self, skill_id: uuid.UUID, enabled: bool, actor: Principal) -> Skill:
        """운영 on/off. 비활성화해도 배포 이력과 published 포인터는 그대로 둔다."""
        skill = await self.get_or_404(skill_id)
        if skill.enabled == enabled:
            return skill
        skill.enabled = enabled
        await self.session.flush()
        await self.audit.record(
            actor,
            AuditOperation.SKILL_ENABLE if enabled else AuditOperation.SKILL_DISABLE,
            skill=skill,
            version=None,
            detail={"enabled": enabled},
        )
        return skill

    async def update_skill(self, skill_id: uuid.UUID, category: str | None) -> Skill:
        """identity 부가정보 수정. `skill_key` 는 바꿀 수 없다(API 에도 없다).

        category 는 화면 필터용 표시값이라 감사 대상이 아니다 — 배포본 내용에 영향이 없다.
        """
        skill = await self.get_or_404(skill_id)
        skill.category = category
        await self.session.flush()
        return skill

    # ── 내부 ──────────────────────────────────────────────

    async def _lock_or_404(self, skill_id: uuid.UUID) -> Skill:
        skill = await self.skills.lock(skill_id)
        if skill is None:
            raise NotFoundError("해당 스킬을 찾을 수 없습니다.")
        return skill

    async def _demote_current(self, skill_id: uuid.UUID) -> SkillVersion | None:
        current = await self.versions.get_by_status(skill_id, SkillVersionStatus.PUBLISHED)
        if current is None:
            return None
        current.status = SkillVersionStatus.SUPERSEDED
        # 부분 unique index 때문에 승격 전에 반드시 내려가 있어야 한다.
        await self.session.flush()
        return current

    async def _promote(self, skill: Skill, target: SkillVersion, actor: Principal) -> None:
        now = datetime.now(UTC)
        target.status = SkillVersionStatus.PUBLISHED
        target.published_by = actor.user_id
        target.published_by_name = actor.display_name
        target.published_at = now
        skill.published_version_id = target.id
        try:
            await self.session.flush()
        except IntegrityError as exc:
            # 동시 publish 가 잠금을 우회한 경우(이론상). 조용히 덮지 않고 충돌로 알린다.
            logger.warning("publish conflict on skill=%s", skill.skill_key)
            raise ConflictError(
                "다른 관리자가 방금 배포했습니다. 새로고침 후 다시 시도하세요."
            ) from exc

    @staticmethod
    def _new_version(
        skill_id: uuid.UUID,
        number: int,
        content: SkillVersionContent,
        actor: Principal,
        *,
        status: SkillVersionStatus,
    ) -> SkillVersion:
        version = SkillVersion(
            skill_id=skill_id,
            version=number,
            name=content.name,
            description=content.description,
            instructions=content.instructions,
            status=status,
            created_by=actor.user_id,
            created_by_name=actor.display_name,
        )
        _replace_children(version, content)
        return version


def _replace_children(version: SkillVersion, content: SkillVersionContent) -> None:
    """alias/tool 을 통째로 교체한다(부분 갱신하지 않는다 — 화면이 전체를 보낸다)."""
    version.aliases = [SkillVersionAlias(alias=a) for a in content.aliases]
    version.tools = [SkillVersionTool(tool_name=t) for t in content.tools]


def _content_of(version: SkillVersion) -> SkillVersionContent:
    return SkillVersionContent(
        name=version.name,
        description=version.description,
        instructions=version.instructions,
        aliases=[a.alias for a in version.aliases],
        tools=[t.tool_name for t in version.tools],
    )


__all__ = ["SkillService"]
