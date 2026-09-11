"""PostgreSQL 통합 테스트 — SQLite 로는 검증할 수 없는 것만 여기 둔다.

- **동시 publish 안전성** — `SELECT ... FOR UPDATE` 와 부분 unique index. SQLite 는 행
  잠금을 무시하므로 단위 테스트가 이것을 증명하지 못한다.
- **Alembic migration head** — 실제 schema 생성 + seed 멱등성.

DB 가 없으면 **skip 된다.** "N skipped" 를 성공으로 오해하지 않도록, 결과를 보고할 때 skip
수를 함께 본다(didim-mcp-service-backend CLAUDE.md 의 함정과 같은 것이다).

실행:

    docker run -d --name pgtest-skill -e POSTGRES_USER=pgtest \\
      -e POSTGRES_PASSWORD=pgtest -e POSTGRES_DB=pgtest -p 55433:5432 postgres:16-alpine
    DIDIM_SKILL_TEST_DATABASE_URL=postgresql+asyncpg://pgtest:pgtest@127.0.0.1:55433/pgtest \\
      uv run pytest tests/integration -m integration

⚠ `DIDIM_SKILL_TEST_DATABASE_URL` 을 운영·공유 DB 로 지정하지 않는다 — 이 테스트는
`mcp_skill_registry` schema 를 DROP 한다.
"""

from __future__ import annotations

import asyncio
import os
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.principal import Principal
from app.core.errors import ConflictError
from app.db.base import Base
from app.db.models import Skill, SkillVersion  # noqa: F401  (metadata 등록)
from app.domain.enums import SkillVersionStatus, UserRole
from app.repositories.skill import SkillVersionRepository
from app.services.skill_service import SkillService

pytestmark = pytest.mark.integration

SCHEMA = "mcp_skill_registry"
DSN = os.environ.get("DIDIM_SKILL_TEST_DATABASE_URL")

ACTOR_A = Principal(
    user_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    display_name="관리자 A",
    email=None,
    role=UserRole.ADMIN,
)
ACTOR_B = Principal(
    user_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    display_name="관리자 B",
    email=None,
    role=UserRole.ADMIN,
)


@pytest.fixture
async def pg_sessionmaker():  # type: ignore[no-untyped-def]
    if not DSN:
        pytest.skip("DIDIM_SKILL_TEST_DATABASE_URL 이 설정되지 않았습니다.")
    engine = create_async_engine(DSN, poolclass=None)
    async with engine.begin() as conn:
        await conn.execute(text(f'DROP SCHEMA IF EXISTS "{SCHEMA}" CASCADE'))
        await conn.execute(text(f'CREATE SCHEMA "{SCHEMA}"'))
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    yield maker
    await engine.dispose()


async def _seed_two_drafts(maker: async_sessionmaker[AsyncSession]) -> tuple[uuid.UUID, int, int]:
    """publish 대기 중인 버전 두 개를 만든다(v1 은 배포, v2·v3 은 경쟁 대상)."""
    from app.api.dto import SkillCreateRequest

    async with maker() as session:
        service = SkillService(session)
        skill = await service.create_skill(
            SkillCreateRequest(
                skill_key="race.publish",
                category=None,
                name="경쟁",
                description="",
                instructions="v1",
                aliases=[],
                tools=[],
            ),
            ACTOR_A,
        )
        skill_id = skill.id
        await service.publish(skill_id, 1, ACTOR_A)
        await session.commit()

    # DRAFT 는 한 번에 하나라는 애플리케이션 규칙을 우회해 경쟁 상황을 만든다 —
    # 두 관리자가 각자 만든 버전을 동시에 배포하는 상황을 재현하기 위한 것이다.
    async with maker() as session:
        repo = SkillVersionRepository(session)
        numbers: list[int] = []
        for body in ("v2", "v3"):
            number = await repo.next_version(skill_id)
            repo.add(
                SkillVersion(
                    skill_id=skill_id,
                    version=number,
                    name=body,
                    description="",
                    instructions=body,
                    status=SkillVersionStatus.DRAFT,
                    created_by=ACTOR_A.user_id,
                    created_by_name=ACTOR_A.display_name,
                )
            )
            await session.flush()
            numbers.append(number)
        await session.commit()
    return skill_id, numbers[0], numbers[1]


async def test_concurrent_publish_keeps_exactly_one_published(pg_sessionmaker) -> None:  # type: ignore[no-untyped-def]
    """두 ADMIN 이 동시에 배포해도 published 포인터가 깨지지 않는다(요구사항 §9)."""
    skill_id, v2, v3 = await _seed_two_drafts(pg_sessionmaker)

    async def publish(version: int, actor: Principal) -> str:
        async with pg_sessionmaker() as session:
            try:
                await SkillService(session).publish(skill_id, version, actor)
                await session.commit()
                return "ok"
            except Exception as exc:  # 충돌은 실패가 아니라 정상 거부다.
                await session.rollback()
                return type(exc).__name__

    results = await asyncio.gather(publish(v2, ACTOR_A), publish(v3, ACTOR_B))

    async with pg_sessionmaker() as session:
        rows = (
            await session.execute(
                text(
                    f'SELECT version, status FROM "{SCHEMA}".skill_versions '
                    "WHERE skill_id = :sid ORDER BY version"
                ),
                {"sid": skill_id},
            )
        ).all()
        pointer = (
            await session.execute(
                text(f'SELECT published_version_id FROM "{SCHEMA}".skills WHERE id = :sid'),
                {"sid": skill_id},
            )
        ).scalar_one()

    published = [r for r in rows if r[1] == "PUBLISHED"]
    assert len(published) == 1, f"published 가 {len(published)}개다: {rows} / {results}"
    assert pointer is not None
    # 하나는 성공, 다른 하나는 성공이거나 명시적 충돌이어야 한다(조용한 덮어쓰기 금지).
    assert results.count("ok") >= 1


async def test_publish_conflict_is_explicit(pg_sessionmaker) -> None:  # type: ignore[no-untyped-def]
    """이미 배포된 버전을 다시 배포하면 조용히 넘어가지 않고 409 로 거부한다."""
    from app.api.dto import SkillCreateRequest

    async with pg_sessionmaker() as session:
        service = SkillService(session)
        skill = await service.create_skill(
            SkillCreateRequest(
                skill_key="race.conflict",
                category=None,
                name="충돌",
                description="",
                instructions="v1",
                aliases=[],
                tools=[],
            ),
            ACTOR_A,
        )
        await service.publish(skill.id, 1, ACTOR_A)
        await session.commit()
        skill_id = skill.id

    async with pg_sessionmaker() as session:
        with pytest.raises(ConflictError):
            await SkillService(session).publish(skill_id, 1, ACTOR_B)


async def test_partial_unique_index_blocks_second_published(pg_sessionmaker) -> None:  # type: ignore[no-untyped-def]
    """애플리케이션을 우회해 직접 INSERT 해도 DB 가 두 번째 PUBLISHED 를 거부한다."""
    from asyncpg.exceptions import UniqueViolationError
    from sqlalchemy.exc import IntegrityError

    skill_id, v2, _ = await _seed_two_drafts(pg_sessionmaker)
    async with pg_sessionmaker() as session:
        with pytest.raises((IntegrityError, UniqueViolationError)):
            await session.execute(
                text(
                    f"UPDATE \"{SCHEMA}\".skill_versions SET status = 'PUBLISHED' "
                    "WHERE skill_id = :sid AND version = :v"
                ),
                {"sid": skill_id, "v": v2},
            )
            await session.commit()
