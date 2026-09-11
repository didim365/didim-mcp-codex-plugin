"""입력 검증 — 신뢰 경계에서만 쓰는 순수 함수.

``skill_key`` 와 ``alias`` 는 **machine identifier** 다. Codex thin router SKILL.md 와 MCP
Tool 인자에 문자 그대로 들어가므로, 공백·경로 문자·제어문자가 섞이면 런타임에서 조용히
어긋난다. 그래서 생성 시점에 좁게 검사한다.
"""

from __future__ import annotations

import re

#: `mcp.usage`, `vault.resource-lookup` 같은 dotted machine key.
#: 소문자/숫자로 시작, 구분자는 `.` `-` `_`, 2~120자.
SKILL_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,119}$")
#: alias 는 라우팅 보조 키. 같은 문자 집합을 쓰되 길이만 조금 더 준다.
ALIAS_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,119}$")
#: MCP Tool 노출명 = `<provider_slug>__<operationId>` (didim-mcp-service-backend
#: `app/domain/validators.py:build_exposed_name`, 구분자 `__`). 그 형식을 그대로 받는다.
TOOL_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,190}$")
#: category 는 화면 필터용 표시값. 한글을 허용해야 하므로 길이와 제어문자만 본다.
MAX_CATEGORY_LEN = 60
MAX_NAME_LEN = 200
MAX_DESCRIPTION_LEN = 4000
MAX_INSTRUCTIONS_LEN = 200_000
MAX_ALIASES = 32
MAX_TOOLS = 64

_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def is_valid_skill_key(value: str) -> bool:
    return bool(SKILL_KEY_RE.fullmatch(value))


def is_valid_alias(value: str) -> bool:
    return bool(ALIAS_RE.fullmatch(value))


def is_valid_tool_name(value: str) -> bool:
    return bool(TOOL_NAME_RE.fullmatch(value))


def has_control_chars(value: str) -> bool:
    """탭/개행을 제외한 제어문자 포함 여부. 본문(instructions)에도 적용한다."""
    return bool(_CONTROL_RE.search(value))


def normalize_list(values: list[str] | None) -> list[str]:
    """공백 제거 + 중복 제거(순서 보존). None 은 빈 목록."""
    if not values:
        return []
    seen: dict[str, None] = {}
    for raw in values:
        item = raw.strip()
        if item:
            seen.setdefault(item, None)
    return list(seen)


__all__ = [
    "ALIAS_RE",
    "MAX_ALIASES",
    "MAX_CATEGORY_LEN",
    "MAX_DESCRIPTION_LEN",
    "MAX_INSTRUCTIONS_LEN",
    "MAX_NAME_LEN",
    "MAX_TOOLS",
    "SKILL_KEY_RE",
    "TOOL_NAME_RE",
    "has_control_chars",
    "is_valid_alias",
    "is_valid_skill_key",
    "is_valid_tool_name",
    "normalize_list",
]
