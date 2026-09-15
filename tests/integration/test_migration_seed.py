"""Alembic migration + seed — 실제 PostgreSQL 에서만 검증되는 것.

SQLite 단위 테스트는 migration 을 돌리지 않는다(`Base.metadata.create_all` 로 스키마만
만든다). 그래서 **"manifest 에 넣은 built-in Skill 이 실제로 배포 환경에 들어가는가"** 는
여기서만 증명된다. 특히 확인하는 것:

- **신규 DB**: `0002` 가 manifest 전체를 넣고 `0003` 이 멱등하게 건너뛴다.
- **기존 운영 DB**(`0002` 적용 완료, `gw.holiday` 없음): `0003` 만 그것을 넣는다.
- 두 경로의 최종 상태가 같다(`0002` 는 원본 그대로 두고 손대지 않는다).
- **이미 있으면 덮어쓰지 않는다** — 운영자가 Admin Web 에서 고친 내용을 보존한다.
- 기존 3건은 `0003` 이 건드리지 않는다.

DSN 이 없으면 **skip** 이다. 결과를 보고할 때 skip 수를 함께 본다.

⚠ 이 테스트는 `mcp_skill_registry` schema 를 DROP 한다. `DIDIM_SKILL_TEST_DATABASE_URL`
을 운영·공유 DB 로 지정하지 않는다.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import make_url, text
from sqlalchemy.ext.asyncio import create_async_engine

pytestmark = pytest.mark.integration

SCHEMA = "mcp_skill_registry"
DSN = os.environ.get("DIDIM_SKILL_TEST_DATABASE_URL")
ROOT = Path(__file__).resolve().parents[2]

SEED_KEYS = {"mcp.usage", "vault.resource", "molit.apartment-transactions"}
ALL_KEYS = SEED_KEYS | {"gw.holiday"}


def _alembic_env() -> dict[str, str]:
    """alembic/env.py 는 URL 을 `DIDIM_SKILL_DB_*` 에서 만든다 — DSN 을 그 형태로 푼다."""
    url = make_url(DSN or "")
    env = dict(os.environ)
    env.update(
        DIDIM_SKILL_DB_HOST=url.host or "127.0.0.1",
        DIDIM_SKILL_DB_PORT=str(url.port or 5432),
        DIDIM_SKILL_DB_USER=url.username or "",
        DIDIM_SKILL_DB_PASSWORD=url.password or "",
        DIDIM_SKILL_DB_NAME=url.database or "",
        DIDIM_SKILL_AUTH_ENABLED="false",
        DIDIM_SKILL_SPA_DIR="does-not-exist",
    )
    return env


def _alembic(*args: str) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=ROOT,
        env=_alembic_env(),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"alembic {' '.join(args)} 실패:\n{result.stdout}{result.stderr}"


async def _sql(statement: str, **params: Any) -> list[tuple[Any, ...]]:
    engine = create_async_engine(DSN or "", poolclass=None)
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text(statement), params)
            if not result.returns_rows:
                return []
            return [tuple(r) for r in result.all()]
    finally:
        await engine.dispose()


def _run(statement: str, **params: Any) -> list[tuple[Any, ...]]:
    return asyncio.run(_sql(statement, **params))


@pytest.fixture
def fresh_schema() -> None:
    if not DSN:
        pytest.skip("DIDIM_SKILL_TEST_DATABASE_URL 미설정 — PostgreSQL 통합 테스트 skip")
    asyncio.run(_sql(f'DROP SCHEMA IF EXISTS "{SCHEMA}" CASCADE'))
    return None


def _gw_holiday_state() -> tuple[Any, ...]:
    rows = _run(
        f"SELECT s.enabled, s.category, s.published_version_id, v.id, v.version, v.status, v.name "
        f'FROM "{SCHEMA}".skills s '
        f'JOIN "{SCHEMA}".skill_versions v ON v.skill_id = s.id '
        "WHERE s.skill_key = :k",
        k="gw.holiday",
    )
    assert len(rows) == 1, "gw.holiday 배포본이 정확히 하나여야 한다"
    return rows[0]


def _assert_gw_holiday_is_seeded_v1() -> Any:
    enabled, category, published_version_id, version_id, version, status, name = _gw_holiday_state()
    assert enabled is True
    assert category == "GW"
    assert version == 1
    assert status == "PUBLISHED"
    assert name == "내 연차 현황 조회"
    assert published_version_id == version_id, "published_version_id 가 v1 을 가리켜야 한다"

    aliases = _run(
        f'SELECT alias FROM "{SCHEMA}".skill_version_aliases '
        "WHERE skill_version_id = :v ORDER BY alias",
        v=version_id,
    )
    assert [a[0] for a in aliases] == ["annual-leave", "gw-holiday", "holiday"]

    tools = _run(
        f'SELECT tool_name FROM "{SCHEMA}".skill_version_tools WHERE skill_version_id = :v',
        v=version_id,
    )
    assert [t[0] for t in tools] == ["didim-gw__get_my_holiday_info"]

    instructions = _run(
        f'SELECT instructions FROM "{SCHEMA}".skill_versions WHERE id = :v', v=version_id
    )[0][0]
    assert "didim-gw__get_my_holiday_info" in instructions
    assert instructions.startswith("# GW Holiday")
    return version_id


def test_fresh_db_upgrade_head_installs_gw_holiday(fresh_schema: None) -> None:
    """신규 DB: `0002` 가 manifest 전체를 넣고 `0003` 은 이미 있는 것을 건너뛴다."""
    _alembic("upgrade", "head")

    _assert_gw_holiday_is_seeded_v1()
    assert {k[0] for k in _run(f'SELECT skill_key FROM "{SCHEMA}".skills')} == ALL_KEYS


def test_existing_db_gets_gw_holiday_from_0003_only(fresh_schema: None) -> None:
    """기존 운영 DB 경로 — `0002` 까지 적용됐고 `gw.holiday` 가 없는 상태를 재현한다.

    실제 운영 DB 는 manifest 에 `gw.holiday` 가 없던 시점에 `0002` 를 적용했다. 그 상태를
    만들려면 `0002` 직후 `gw.holiday` 를 지우면 된다. 그 뒤 `0003` 만으로 들어가야 하고,
    기존 3건은 행 id 까지 그대로여야 한다.
    """
    _alembic("upgrade", "0002_seed_initial_skills")
    _run(f'DELETE FROM "{SCHEMA}".skills WHERE skill_key = :k', k="gw.holiday")
    before = _run(
        f'SELECT skill_key, id, published_version_id FROM "{SCHEMA}".skills ORDER BY skill_key'
    )
    assert {r[0] for r in before} == SEED_KEYS

    _alembic("upgrade", "head")

    _assert_gw_holiday_is_seeded_v1()
    after = _run(
        f'SELECT skill_key, id, published_version_id FROM "{SCHEMA}".skills '
        "WHERE skill_key <> :k ORDER BY skill_key",
        k="gw.holiday",
    )
    assert after == before, "기존 3건은 행 id·배포본까지 그대로여야 한다"
    assert {k[0] for k in _run(f'SELECT skill_key FROM "{SCHEMA}".skills')} == ALL_KEYS


def test_rerunning_0003_preserves_operator_changes(fresh_schema: None) -> None:
    """운영자가 고친 `gw.holiday` 위로 migration 이 다시 돌아도 덮어쓰지 않는다.

    `stamp 0002` 로 버전 테이블만 되돌려 **0003 의 본문을 실제로 재실행**시킨다
    (downgrade 를 쓰면 데이터가 지워져 멱등성을 검증할 수 없다).
    """
    _alembic("upgrade", "head")
    before = _run(
        f'SELECT id, published_version_id FROM "{SCHEMA}".skills WHERE skill_key = :k',
        k="gw.holiday",
    )[0]

    _run(
        f'UPDATE "{SCHEMA}".skill_versions SET instructions = :i, name = :n WHERE id = :v',
        i="# 운영자가 Admin Web 에서 고친 본문",
        n="연차 조회(운영 수정본)",
        v=before[1],
    )

    _alembic("stamp", "0002_seed_initial_skills")
    _alembic("upgrade", "head")

    after = _run(
        f"SELECT s.id, s.published_version_id, v.name, v.instructions, count(*) OVER () "
        f'FROM "{SCHEMA}".skills s '
        f'JOIN "{SCHEMA}".skill_versions v ON v.skill_id = s.id '
        "WHERE s.skill_key = :k",
        k="gw.holiday",
    )
    assert len(after) == 1, "중복 삽입이 일어나면 안 된다"
    assert after[0][0] == before[0]
    assert after[0][1] == before[1]
    assert after[0][2] == "연차 조회(운영 수정본)"
    assert after[0][3] == "# 운영자가 Admin Web 에서 고친 본문"


def test_downgrade_removes_only_untouched_seed(fresh_schema: None) -> None:
    """`0003` downgrade 는 사람이 손대지 않은 seed 만 지운다."""
    _alembic("upgrade", "head")
    _alembic("downgrade", "0002_seed_initial_skills")
    assert not _run(f'SELECT 1 FROM "{SCHEMA}".skills WHERE skill_key = :k', k="gw.holiday")
    # 나머지 3건은 남는다 — `0003` 은 자기가 선언한 key 만 다룬다.
    assert {k[0] for k in _run(f'SELECT skill_key FROM "{SCHEMA}".skills')} == SEED_KEYS

    # 사람이 v2 를 올린 뒤에는 downgrade 가 지우지 않는다.
    _alembic("upgrade", "head")
    skill_id, version_id = _run(
        f'SELECT id, published_version_id FROM "{SCHEMA}".skills WHERE skill_key = :k',
        k="gw.holiday",
    )[0]
    _run(
        f'INSERT INTO "{SCHEMA}".skill_versions (id, skill_id, version, name, description, '
        "instructions, status) VALUES (gen_random_uuid(), :sid, 2, :n, '', :i, 'DRAFT')",
        sid=skill_id,
        n="운영자 초안",
        i="# 초안",
    )
    _alembic("downgrade", "0002_seed_initial_skills")
    still = _run(f'SELECT 1 FROM "{SCHEMA}".skills WHERE skill_key = :k', k="gw.holiday")
    assert still, "사람이 새 버전을 올린 Skill 을 downgrade 가 지우면 안 된다"
    assert version_id  # v1 은 그대로 배포본으로 남아 있다
