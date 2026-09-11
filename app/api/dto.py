"""API DTO — ORM Entity 를 그대로 내보내지 않는다.

Admin 계약과 runtime 계약을 **분리**한다. runtime 응답에는 DRAFT 가 존재할 수 없고, 내부
식별자(UUID)·감사 필드도 싣지 않는다 — Codex 가 읽는 것은 workflow 그 자체뿐이다.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import AuditOperation, AuditResult, SkillVersionStatus
from app.domain.validators import (
    MAX_ALIASES,
    MAX_CATEGORY_LEN,
    MAX_DESCRIPTION_LEN,
    MAX_INSTRUCTIONS_LEN,
    MAX_NAME_LEN,
    MAX_TOOLS,
    has_control_chars,
    is_valid_alias,
    is_valid_skill_key,
    is_valid_tool_name,
    normalize_list,
)


class PageMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class Page[T](BaseModel):
    items: list[T]
    meta: PageMeta


# ── 공통 입력 검증 ────────────────────────────────────────


def _check_text(value: str, *, field: str, max_len: int) -> str:
    if has_control_chars(value):
        raise ValueError(f"{field}: 제어문자를 포함할 수 없습니다.")
    if len(value) > max_len:
        raise ValueError(f"{field}: 최대 {max_len}자입니다.")
    return value


class SkillVersionContent(BaseModel):
    """버전 내용 입력 — 생성/수정/롤백이 모두 같은 모양을 쓴다."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    description: str = ""
    instructions: str = ""
    aliases: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        return _check_text(v.strip(), field="name", max_len=MAX_NAME_LEN)

    @field_validator("description")
    @classmethod
    def _description(cls, v: str) -> str:
        return _check_text(v, field="description", max_len=MAX_DESCRIPTION_LEN)

    @field_validator("instructions")
    @classmethod
    def _instructions(cls, v: str) -> str:
        # instructions 는 Markdown 본문이라 개행·탭이 정상이다. 제어문자만 막는다.
        return _check_text(v, field="instructions", max_len=MAX_INSTRUCTIONS_LEN)

    @field_validator("aliases")
    @classmethod
    def _aliases(cls, v: list[str]) -> list[str]:
        items = normalize_list(v)
        if len(items) > MAX_ALIASES:
            raise ValueError(f"aliases: 최대 {MAX_ALIASES}개입니다.")
        bad = [a for a in items if not is_valid_alias(a)]
        if bad:
            raise ValueError(f"aliases: 형식이 올바르지 않습니다 ({', '.join(bad[:3])})")
        return items

    @field_validator("tools")
    @classmethod
    def _tools(cls, v: list[str]) -> list[str]:
        items = normalize_list(v)
        if len(items) > MAX_TOOLS:
            raise ValueError(f"tools: 최대 {MAX_TOOLS}개입니다.")
        bad = [t for t in items if not is_valid_tool_name(t)]
        if bad:
            raise ValueError(f"tools: 형식이 올바르지 않습니다 ({', '.join(bad[:3])})")
        return items


class SkillCreateRequest(SkillVersionContent):
    """Skill 생성 = identity + v1 DRAFT 내용."""

    skill_key: str
    category: str | None = None

    @field_validator("skill_key")
    @classmethod
    def _key(cls, v: str) -> str:
        key = v.strip().lower()
        if not is_valid_skill_key(key):
            raise ValueError(
                "skill_key: 소문자/숫자로 시작하고 `. - _` 만 쓰는 2~120자여야 합니다."
            )
        return key

    @field_validator("category")
    @classmethod
    def _category(cls, v: str | None) -> str | None:
        if v is None:
            return None
        value = v.strip()
        if not value:
            return None
        return _check_text(value, field="category", max_len=MAX_CATEGORY_LEN)


class SkillUpdateRequest(BaseModel):
    """Skill identity 수정 — **skill_key 는 바꿀 수 없다**(machine identifier)."""

    model_config = ConfigDict(extra="forbid")

    category: str | None = None

    @field_validator("category")
    @classmethod
    def _category(cls, v: str | None) -> str | None:
        if v is None:
            return None
        value = v.strip()
        return _check_text(value, field="category", max_len=MAX_CATEGORY_LEN) if value else None


class EnabledRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool


class PublishRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(ge=1)


class RollbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    #: 되돌릴 **원본** 버전. 그 내용으로 새 버전을 만들어 publish 한다(과거 행 미변형).
    version: int = Field(ge=1)


# ── Admin 출력 ────────────────────────────────────────────


class SkillVersionSummary(BaseModel):
    id: uuid.UUID
    version: int
    name: str
    status: SkillVersionStatus
    created_by_name: str | None
    created_at: datetime
    published_by_name: str | None
    published_at: datetime | None
    rolled_back_from: int | None


class SkillVersionDetail(SkillVersionSummary):
    description: str
    instructions: str
    aliases: list[str]
    tools: list[str]


class SkillSummary(BaseModel):
    id: uuid.UUID
    skill_key: str
    category: str | None
    enabled: bool
    #: 현재 배포된 버전 번호. 아직 publish 전이면 None.
    published_version: int | None
    published_name: str | None
    #: 편집 중인 DRAFT 버전 번호(있으면).
    draft_version: int | None
    updated_at: datetime


class SkillDetail(SkillSummary):
    versions: list[SkillVersionSummary]
    published: SkillVersionDetail | None
    draft: SkillVersionDetail | None


class AuditLogItem(BaseModel):
    id: uuid.UUID
    actor_display_name: str | None
    operation: AuditOperation
    skill_key: str | None
    skill_version: int | None
    result: AuditResult
    detail: dict[str, object] | None
    created_at: datetime


# ── Runtime 출력 (Codex / MCP gateway 계약) ───────────────


class RuntimeSkillSummary(BaseModel):
    """runtime 목록 항목. **instructions 를 싣지 않는다**(목록은 가벼워야 한다)."""

    skill_key: str
    version: int
    name: str
    description: str
    category: str | None
    aliases: list[str]
    tools: list[str]
    published_at: datetime | None


class RuntimeSkill(RuntimeSkillSummary):
    """runtime 단건. 여기서만 workflow 본문이 나간다."""

    instructions: str


class HealthOut(BaseModel):
    status: str
    service: str
    version: str


class ReadyOut(BaseModel):
    status: str
    mode: str
    checks: dict[str, object]


class MeOut(BaseModel):
    """화면 shell 표시 전용. **인가 판단에 쓰지 않는다** — 차단은 backend 가드가 한다."""

    authenticated: bool
    user_id: str | None = None
    display_name: str | None = None
    email: str | None = None
    role: str | None = None
    is_admin: bool = False
    csrf_token: str | None = None
    #: Microsoft 로그인 시작 URL. 비어 있으면 화면이 버튼을 그리지 않는다.
    login_url: str = ""
    logout_url: str = ""


PageSizeQuery = Annotated[int | None, Field(ge=1, le=100)]

__all__ = [
    "AuditLogItem",
    "EnabledRequest",
    "HealthOut",
    "MeOut",
    "Page",
    "PageMeta",
    "PublishRequest",
    "ReadyOut",
    "RollbackRequest",
    "RuntimeSkill",
    "RuntimeSkillSummary",
    "SkillCreateRequest",
    "SkillDetail",
    "SkillSummary",
    "SkillUpdateRequest",
    "SkillVersionContent",
    "SkillVersionDetail",
    "SkillVersionSummary",
]
