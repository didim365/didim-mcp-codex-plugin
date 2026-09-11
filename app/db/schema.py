"""DB schema 이름 — 이 프로젝트가 migration owner 인 단 하나의 schema.

``mcp_skill_registry`` 는 **고정값**이다. 다른 DIDIM 서비스(didim_mcp / didim_vault /
didim_mcp_auth / didim_rag)의 schema 를 이 저장소의 Alembic 이 건드리지 않는다.
DROP SCHEMA 는 어떤 경로로도 실행하지 않는다.
"""

from __future__ import annotations

import re

#: 이 서비스가 소유하는 schema. 변경 금지(요구사항 §34-10).
DATABASE_SCHEMA = "mcp_skill_registry"
DEFAULT_SCHEMA = DATABASE_SCHEMA

_SCHEMA_RE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


def validate_schema_name(value: str) -> str:
    """schema 이름 형식 검증. SQL 문자열에 끼워 넣기 전에 반드시 통과시킨다."""
    if not _SCHEMA_RE.fullmatch(value):
        raise ValueError(f"invalid schema name: {value!r}")
    return value


__all__ = ["DATABASE_SCHEMA", "DEFAULT_SCHEMA", "validate_schema_name"]
