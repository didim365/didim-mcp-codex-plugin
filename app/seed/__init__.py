"""초기 Skill seed — 정적 SKILL.md 에서 DB 로 옮긴 **1회성 스냅샷**.

이것은 runtime source of truth 가 **아니다.** runtime 은 언제나 DB 를 읽는다
(`/api/v1/runtime/**`). 여기 파일은 Alembic data migration(`0002_seed_initial_skills`)이
빈 Registry 를 채울 때 한 번 읽히고, 그 뒤로는 아무도 읽지 않는다.

그래서 **운영 중 workflow 수정은 이 파일이 아니라 Admin Web 의 초안 → 배포로 한다.**
여기를 고쳐도 이미 seed 된 DB 는 바뀌지 않는다(멱등 삽입 — 이미 있는 skill_key 는 건너뛴다).

파일 구성:
    manifest.json          skill_key / name / description / category / aliases / tools
    skills/<key>.body.md   workflow 본문(= 기존 SKILL.md 본문에서 frontmatter 를 뺀 것)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = _ROOT / "manifest.json"
BODY_DIR = _ROOT / "skills"


@dataclass(frozen=True)
class SeedSkill:
    skill_key: str
    name: str
    description: str
    category: str | None
    instructions: str
    aliases: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)


def load_seed_skills() -> list[SeedSkill]:
    """manifest + 본문 파일을 읽어 seed 목록을 만든다. 파일이 없으면 빈 목록."""
    if not MANIFEST_PATH.is_file():
        return []
    raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    skills: list[SeedSkill] = []
    for entry in raw:
        body_path = BODY_DIR / str(entry["body"])
        instructions = body_path.read_text(encoding="utf-8") if body_path.is_file() else ""
        skills.append(
            SeedSkill(
                skill_key=str(entry["skill_key"]),
                name=str(entry["name"]),
                description=str(entry["description"]),
                category=entry.get("category") or None,
                instructions=instructions,
                aliases=list(entry.get("aliases") or []),
                tools=list(entry.get("tools") or []),
            )
        )
    return skills


__all__ = ["BODY_DIR", "MANIFEST_PATH", "SeedSkill", "load_seed_skills"]
