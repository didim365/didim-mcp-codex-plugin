"""built-in Skill `gw.holiday`(내 연차 현황 조회)를 Registry 에 추가한다.

`app/seed/manifest.json` 에 항목을 넣는 것만으로는 **이미 배포된 DB 에 반영되지 않는다** —
`0002` 는 이미 적용됐고 다시 실행되지 않기 때문이다. 그래서 새 built-in Skill 은 매번
이런 migration 한 건으로 배포한다.

**멱등이다.** `gw.holiday` 가 이미 있으면(운영자가 Admin Web 에서 먼저 만들었거나 이
migration 이 다시 돌아도) 통째로 건너뛴다. 다른 Skill 은 조회조차 하지 않는다.

본문·alias·tool 의 정본은 `app/seed` 다. 여기에 문자열을 다시 적지 않는다.

Revision ID: 0003_add_gw_holiday_skill
Revises: 0002_seed_initial_skills
Create Date: 2026-09-15
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from app.seed import install_seed_skills, uninstall_seed_skills

revision: str = "0003_add_gw_holiday_skill"
down_revision: str | None = "0002_seed_initial_skills"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "mcp_skill_registry"
SEEDED_KEYS = ("gw.holiday",)


def upgrade() -> None:
    install_seed_skills(op.get_bind(), SCHEMA, SEEDED_KEYS)


def downgrade() -> None:
    """`gw.holiday` 가 **seed 상태 그대로(v1 하나)** 일 때만 지운다.

    운영자가 v2 를 만들었거나 배포했다면 사람 작업이 얹힌 것이므로 남긴다.
    """
    uninstall_seed_skills(op.get_bind(), SCHEMA, SEEDED_KEYS)
