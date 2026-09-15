"""초기 Skill seed — 정적 SKILL.md 에서 DB 로 옮긴 **스냅샷**.

이것은 runtime source of truth 가 **아니다.** runtime 은 언제나 DB 를 읽는다
(`/api/v1/runtime/**`). 여기 파일은 Alembic data migration 이 Registry 에 built-in Skill 을
처음 넣을 때만 읽히고, 그 뒤로는 아무도 읽지 않는다.

그래서 **운영 중 workflow 수정은 이 파일이 아니라 Admin Web 의 초안 → 배포로 한다.**
여기를 고쳐도 이미 seed 된 DB 는 바뀌지 않는다(멱등 삽입 — 이미 있는 skill_key 는 건너뛴다).

**manifest 에 항목을 추가하는 것만으로는 이미 배포된 DB 에 반영되지 않는다.** 적용된
migration 은 다시 실행되지 않기 때문이다. built-in Skill 을 새로 추가할 때는 항목 추가와
함께 `install_seed_skills(conn, SCHEMA, ("<key>",))` 를 호출하는 **새 migration** 을 둔다
(선례: `0003_add_gw_holiday_skill`). 적용이 끝난 migration 파일(`0002`)은 고치지 않는다 —
그쪽은 지금도 `load_seed_skills()` 를 직접 읽어 자기 방식으로 삽입한다.

파일 구성:
    manifest.json          skill_key / name / description / category / aliases / tools
    skills/<key>.body.md   workflow 본문(= 기존 SKILL.md 본문에서 frontmatter 를 뺀 것)
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.engine import Connection

_ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = _ROOT / "manifest.json"
BODY_DIR = _ROOT / "skills"

#: 행위자가 사람이 아니므로 `created_by` 는 비우고 표시명만 남긴다 — 감사에서
#: "누가 했는지 모른다" 와 "시스템이 했다" 를 구분하기 위해서다.
SEED_ACTOR_NAME = "시스템(초기 이관)"


@dataclass(frozen=True)
class SeedSkill:
    skill_key: str
    name: str
    description: str
    category: str | None
    instructions: str
    aliases: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)


def load_seed_skills(only: Iterable[str] | None = None) -> list[SeedSkill]:
    """manifest + 본문 파일을 읽어 seed 목록을 만든다. 파일이 없으면 빈 목록.

    `only` 를 주면 그 `skill_key` 만 고른다(migration 이 자기 몫만 다루게 하려는 것).
    """
    if not MANIFEST_PATH.is_file():
        return []
    wanted = set(only) if only is not None else None
    raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    skills: list[SeedSkill] = []
    for entry in raw:
        skill_key = str(entry["skill_key"])
        if wanted is not None and skill_key not in wanted:
            continue
        body_path = BODY_DIR / str(entry["body"])
        instructions = body_path.read_text(encoding="utf-8") if body_path.is_file() else ""
        skills.append(
            SeedSkill(
                skill_key=skill_key,
                name=str(entry["name"]),
                description=str(entry["description"]),
                category=entry.get("category") or None,
                instructions=instructions,
                aliases=list(entry.get("aliases") or []),
                tools=list(entry.get("tools") or []),
            )
        )
    return skills


def install_seed_skills(conn: Connection, schema: str, only: Iterable[str] | None = None) -> None:
    """seed 를 v1 PUBLISHED 로 넣는다. **멱등이다.**

    이미 같은 `skill_key` 가 있으면 통째로 건너뛴다 — 운영 중 Admin Web 에서 고친 내용을
    migration 이 되돌리지 않는다. 여러 번 실행해도 결과가 같다.
    """
    for seed in load_seed_skills(only):
        exists = conn.execute(
            sa.text(f'SELECT 1 FROM "{schema}".skills WHERE skill_key = :k'),
            {"k": seed.skill_key},
        ).first()
        if exists:
            continue  # 멱등: 이미 있는 것은 건드리지 않는다.

        skill_id = uuid.uuid4()
        version_id = uuid.uuid4()

        conn.execute(
            sa.text(
                f'INSERT INTO "{schema}".skills '
                "(id, skill_key, category, enabled, published_version_id) "
                "VALUES (:id, :key, :category, true, NULL)"
            ),
            {"id": skill_id, "key": seed.skill_key, "category": seed.category},
        )
        conn.execute(
            sa.text(
                f'INSERT INTO "{schema}".skill_versions '
                "(id, skill_id, version, name, description, instructions, status, "
                " created_by, created_by_name, published_by, published_by_name, published_at) "
                "VALUES (:id, :skill_id, 1, :name, :description, :instructions, 'PUBLISHED', "
                " NULL, :actor, NULL, :actor, now())"
            ),
            {
                "id": version_id,
                "skill_id": skill_id,
                "name": seed.name,
                "description": seed.description,
                "instructions": seed.instructions,
                "actor": SEED_ACTOR_NAME,
            },
        )
        for alias in seed.aliases:
            conn.execute(
                sa.text(
                    f'INSERT INTO "{schema}".skill_version_aliases '
                    "(id, skill_version_id, alias) VALUES (:id, :vid, :alias)"
                ),
                {"id": uuid.uuid4(), "vid": version_id, "alias": alias},
            )
        for tool in seed.tools:
            conn.execute(
                sa.text(
                    f'INSERT INTO "{schema}".skill_version_tools '
                    "(id, skill_version_id, tool_name) VALUES (:id, :vid, :tool)"
                ),
                {"id": uuid.uuid4(), "vid": version_id, "tool": tool},
            )
        conn.execute(
            sa.text(f'UPDATE "{schema}".skills SET published_version_id = :vid WHERE id = :id'),
            {"vid": version_id, "id": skill_id},
        )


def uninstall_seed_skills(conn: Connection, schema: str, only: Iterable[str] | None = None) -> None:
    """seed 로 들어간 Skill 만 지운다(downgrade 용).

    운영 중 만들어진 다른 Skill 은 건드리지 않는다. seed 한 Skill 에 사람이 새 버전을
    올렸을 수 있으므로, **그 경우에는 지우지 않는다**(사람 작업을 downgrade 가 버리지 않게).
    """
    for seed in load_seed_skills(only):
        row = conn.execute(
            sa.text(f'SELECT id FROM "{schema}".skills WHERE skill_key = :k'),
            {"k": seed.skill_key},
        ).first()
        if row is None:
            continue
        skill_id = row[0]
        versions = conn.execute(
            sa.text(f'SELECT count(*) FROM "{schema}".skill_versions WHERE skill_id = :id'),
            {"id": skill_id},
        ).scalar_one()
        if int(versions) != 1:
            continue  # 사람이 손댄 Skill 은 남긴다.
        conn.execute(
            sa.text(f'UPDATE "{schema}".skills SET published_version_id = NULL WHERE id = :id'),
            {"id": skill_id},
        )
        conn.execute(sa.text(f'DELETE FROM "{schema}".skills WHERE id = :id'), {"id": skill_id})


__all__ = [
    "BODY_DIR",
    "MANIFEST_PATH",
    "SEED_ACTOR_NAME",
    "SeedSkill",
    "install_seed_skills",
    "load_seed_skills",
    "uninstall_seed_skills",
]
