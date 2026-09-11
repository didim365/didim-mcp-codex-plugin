"""기존 정적 SKILL.md 내용을 DB 초기 배포본(v1 PUBLISHED)으로 옮긴다.

**멱등이다.** 이미 같은 `skill_key` 가 있으면 건너뛴다 — 운영 중 Admin Web 에서 고친
내용을 이 migration 이 되돌리지 않는다. 여러 번 실행해도 결과가 같다.

seed 이후 runtime 은 DB 만 읽는다. 운영 수정은 소스 수정이 아니라 Admin Web 의
초안 → 배포로 한다(요구사항 §13).

행위자는 사람이 아니므로 `created_by` 는 비우고 표시명만 `시스템(초기 이관)` 으로 둔다 —
감사에서 "누가 했는지 모른다" 와 "시스템이 했다" 를 구분하기 위해서다.

Revision ID: 0002_seed_initial_skills
Revises: 0001_init_skill_registry
Create Date: 2026-09-11
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.seed import load_seed_skills

revision: str = "0002_seed_initial_skills"
down_revision: str | None = "0001_init_skill_registry"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "mcp_skill_registry"
SEED_ACTOR_NAME = "시스템(초기 이관)"


def upgrade() -> None:
    conn = op.get_bind()
    seeds = load_seed_skills()
    if not seeds:
        return

    for seed in seeds:
        exists = conn.execute(
            sa.text(f'SELECT 1 FROM "{SCHEMA}".skills WHERE skill_key = :k'),
            {"k": seed.skill_key},
        ).first()
        if exists:
            continue  # 멱등: 이미 있는 것은 건드리지 않는다.

        skill_id = uuid.uuid4()
        version_id = uuid.uuid4()

        conn.execute(
            sa.text(
                f'INSERT INTO "{SCHEMA}".skills '
                "(id, skill_key, category, enabled, published_version_id) "
                "VALUES (:id, :key, :category, true, NULL)"
            ),
            {"id": skill_id, "key": seed.skill_key, "category": seed.category},
        )
        conn.execute(
            sa.text(
                f'INSERT INTO "{SCHEMA}".skill_versions '
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
                    f'INSERT INTO "{SCHEMA}".skill_version_aliases '
                    "(id, skill_version_id, alias) VALUES (:id, :vid, :alias)"
                ),
                {"id": uuid.uuid4(), "vid": version_id, "alias": alias},
            )
        for tool in seed.tools:
            conn.execute(
                sa.text(
                    f'INSERT INTO "{SCHEMA}".skill_version_tools '
                    "(id, skill_version_id, tool_name) VALUES (:id, :vid, :tool)"
                ),
                {"id": uuid.uuid4(), "vid": version_id, "tool": tool},
            )
        conn.execute(
            sa.text(f'UPDATE "{SCHEMA}".skills SET published_version_id = :vid WHERE id = :id'),
            {"vid": version_id, "id": skill_id},
        )


def downgrade() -> None:
    """seed 로 들어간 Skill 만 지운다.

    운영 중 만들어진 다른 Skill 은 건드리지 않는다. seed 한 Skill 에 사람이 새 버전을
    올렸을 수 있으므로, **그 경우에는 지우지 않는다**(사람 작업을 downgrade 가 버리지 않게).
    """
    conn = op.get_bind()
    for seed in load_seed_skills():
        row = conn.execute(
            sa.text(f'SELECT id FROM "{SCHEMA}".skills WHERE skill_key = :k'),
            {"k": seed.skill_key},
        ).first()
        if row is None:
            continue
        skill_id = row[0]
        versions = conn.execute(
            sa.text(f'SELECT count(*) FROM "{SCHEMA}".skill_versions WHERE skill_id = :id'),
            {"id": skill_id},
        ).scalar_one()
        if int(versions) != 1:
            continue  # 사람이 손댄 Skill 은 남긴다.
        conn.execute(
            sa.text(f'UPDATE "{SCHEMA}".skills SET published_version_id = NULL WHERE id = :id'),
            {"id": skill_id},
        )
        conn.execute(sa.text(f'DELETE FROM "{SCHEMA}".skills WHERE id = :id'), {"id": skill_id})
