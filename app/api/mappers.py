"""ORM Entity → API DTO. 한 곳에만 둔다(화면마다 다시 조립하지 않게).

runtime 매퍼는 **instructions 를 내보내는 유일한 경로**다. Admin 매퍼와 분리해 둔 이유는
runtime 응답에 내부 UUID·감사 필드가 섞이는 사고를 구조적으로 막기 위해서다.
"""

from __future__ import annotations

from app.api.dto import (
    AuditLogItem,
    RuntimeSkill,
    RuntimeSkillSummary,
    SkillDetail,
    SkillSummary,
    SkillVersionDetail,
    SkillVersionSummary,
)
from app.db.models.audit import AuditLog
from app.db.models.skill import Skill, SkillVersion
from app.domain.enums import SkillVersionStatus


def _pick(skill: Skill, status: SkillVersionStatus) -> SkillVersion | None:
    """가장 최근의 해당 상태 버전. PUBLISHED 는 정의상 최대 1개다."""
    matches = [v for v in skill.versions if v.status is status]
    return max(matches, key=lambda v: v.version) if matches else None


def version_summary(version: SkillVersion) -> SkillVersionSummary:
    return SkillVersionSummary(
        id=version.id,
        version=version.version,
        name=version.name,
        status=version.status,
        created_by_name=version.created_by_name,
        created_at=version.created_at,
        published_by_name=version.published_by_name,
        published_at=version.published_at,
        rolled_back_from=version.rolled_back_from,
    )


def version_detail(version: SkillVersion) -> SkillVersionDetail:
    return SkillVersionDetail(
        **version_summary(version).model_dump(),
        description=version.description,
        instructions=version.instructions,
        aliases=[a.alias for a in version.aliases],
        tools=[t.tool_name for t in version.tools],
    )


def skill_summary(skill: Skill) -> SkillSummary:
    published = _pick(skill, SkillVersionStatus.PUBLISHED)
    draft = _pick(skill, SkillVersionStatus.DRAFT)
    return SkillSummary(
        id=skill.id,
        skill_key=skill.skill_key,
        category=skill.category,
        enabled=skill.enabled,
        published_version=published.version if published else None,
        published_name=published.name if published else None,
        draft_version=draft.version if draft else None,
        updated_at=skill.updated_at,
    )


def skill_detail(skill: Skill) -> SkillDetail:
    published = _pick(skill, SkillVersionStatus.PUBLISHED)
    draft = _pick(skill, SkillVersionStatus.DRAFT)
    return SkillDetail(
        **skill_summary(skill).model_dump(),
        versions=[version_summary(v) for v in sorted(skill.versions, key=lambda v: -v.version)],
        published=version_detail(published) if published else None,
        draft=version_detail(draft) if draft else None,
    )


def audit_item(entry: AuditLog) -> AuditLogItem:
    return AuditLogItem(
        id=entry.id,
        actor_display_name=entry.actor_display_name,
        operation=entry.operation,
        skill_key=entry.skill_key,
        skill_version=entry.skill_version,
        result=entry.result,
        detail=entry.detail,
        created_at=entry.created_at,
    )


def runtime_summary(version: SkillVersion, skill: Skill) -> RuntimeSkillSummary:
    return RuntimeSkillSummary(
        skill_key=skill.skill_key,
        version=version.version,
        name=version.name,
        description=version.description,
        category=skill.category,
        aliases=[a.alias for a in version.aliases],
        tools=[t.tool_name for t in version.tools],
        published_at=version.published_at,
    )


def runtime_skill(version: SkillVersion, skill: Skill) -> RuntimeSkill:
    return RuntimeSkill(
        **runtime_summary(version, skill).model_dump(),
        instructions=version.instructions,
    )


__all__ = [
    "audit_item",
    "runtime_skill",
    "runtime_summary",
    "skill_detail",
    "skill_summary",
    "version_detail",
    "version_summary",
]
