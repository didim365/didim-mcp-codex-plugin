"""테스트 하네스.

DB 는 **in-memory SQLite(aiosqlite)** 를 쓴다. 이유와 한계를 숨기지 않는다:

- 잡히는 것: 인가 경계, publish/rollback 상태 전이, 한 Skill 에 PUBLISHED 하나 제약
  (부분 unique index 는 SQLite 도 지원한다), runtime 이 DRAFT 를 노출하지 않는 것,
  페이징·검색·필터, 감사 기록, 입력 검증.
- **잡히지 않는 것**: `SELECT ... FOR UPDATE` 기반 동시성(SQLite 는 무시한다), JSONB,
  PostgreSQL 전용 타입 동작. 진짜 동시 publish 는 PostgreSQL 통합 테스트
  (`-m integration`, `DIDIM_SKILL_TEST_DATABASE_URL`)에서만 검증된다.

인증은 `auth_enabled=False` 로 두고 **가드를 직접 override** 해서 역할별 경로를 만든다.
Auth 백엔드를 테스트에서 부르지 않는다(respx 로 흉내 내는 것은 계약 테스트의 일이다).
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator, Iterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Settings 는 import 시점에 환경을 읽으므로 app import 전에 세팅한다.
os.environ.setdefault("DIDIM_SKILL_AUTH_ENABLED", "false")
os.environ.setdefault("DIDIM_SKILL_ENV", "local")
os.environ.setdefault("DIDIM_SKILL_SPA_DIR", "does-not-exist")

from app.api.deps import get_session, require_admin, require_runtime_caller
from app.auth.principal import Principal
from app.db.base import Base
from app.db.models import (  # noqa: F401  (metadata 등록용 import)
    AuditLog,
    Skill,
    SkillVersion,
    SkillVersionAlias,
    SkillVersionTool,
)
from app.domain.enums import UserRole
from app.main import create_app

SCHEMA = "mcp_skill_registry"

ADMIN = Principal(
    user_id="11111111-1111-1111-1111-111111111111",
    display_name="관리자",
    email="admin@example.com",
    role=UserRole.ADMIN,
)
USER = Principal(
    user_id="22222222-2222-2222-2222-222222222222",
    display_name="일반 사용자",
    email="user@example.com",
    role=UserRole.USER,
)


@event.listens_for(Engine, "connect")
def _sqlite_pragmas(dbapi_connection: object, _record: object) -> None:
    """SQLite 에서 FK 제약을 켠다(기본이 off 라 ondelete 가 조용히 무시된다).

    **SQLite 커넥션에만** 적용한다 — 전역 리스너라 PostgreSQL 통합 테스트 엔진에도 걸리는데,
    거기서 PRAGMA 를 보내면 문법 오류로 죽는다(실제로 한 번 겪었다).
    """
    if type(dbapi_connection).__module__.split(".")[0] not in ("sqlite3", "aiosqlite"):
        return
    cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


@pytest.fixture
async def sessionmaker_fixture() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """테스트마다 새 in-memory SQLite.

    `StaticPool` 로 커넥션 하나를 공유한다 — in-memory DB 는 커넥션마다 별개라서 풀을
    쓰면 테이블이 사라진다. 모델이 `mcp_skill_registry.<table>` 로 완전 수식돼 있으므로
    같은 이름의 in-memory DB 를 ATTACH 해 schema 를 흉내 낸다.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as conn:
        await conn.execute(text(f"ATTACH DATABASE ':memory:' AS {SCHEMA}"))
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    yield maker
    await engine.dispose()


@pytest.fixture
def app_factory(
    sessionmaker_fixture: async_sessionmaker[AsyncSession],
) -> Iterator[object]:
    """principal 을 골라 앱을 만드는 팩토리. `None` 이면 미인증(401)."""

    created: list[FastAPI] = []

    def make(principal: Principal | None = ADMIN, *, runtime_principal: Principal | None = ADMIN):
        app = create_app()
        created.append(app)

        async def _session() -> AsyncIterator[AsyncSession]:
            async with sessionmaker_fixture() as session:
                try:
                    yield session
                except Exception:
                    await session.rollback()
                    raise
                else:
                    await session.commit()

        async def _admin() -> Principal:
            from app.core.errors import ForbiddenError, UnauthorizedError

            if principal is None:
                raise UnauthorizedError("로그인이 필요합니다.")
            if not principal.is_admin:
                raise ForbiddenError("관리자 권한이 필요합니다.")
            return principal

        async def _runtime() -> Principal | None:
            from app.core.errors import UnauthorizedError

            if runtime_principal is None:
                raise UnauthorizedError("로그인이 필요합니다.")
            return runtime_principal

        app.dependency_overrides[get_session] = _session
        app.dependency_overrides[require_admin] = _admin
        app.dependency_overrides[require_runtime_caller] = _runtime
        # DB 가 설정된 것처럼 보이게 한다(`get_database` 는 override 된 세션이 대신한다).
        app.state.database = _FakeDatabase(sessionmaker_fixture)
        return app

    yield make
    for app in created:
        app.dependency_overrides.clear()


class _FakeDatabase:
    def __init__(self, maker: async_sessionmaker[AsyncSession]) -> None:
        self.sessionmaker = maker

    @property
    def is_configured(self) -> bool:
        return True

    async def check(self) -> tuple[bool, bool]:
        return True, True

    async def dispose(self) -> None:
        return None


@pytest.fixture
async def client(app_factory) -> AsyncIterator[AsyncClient]:  # type: ignore[no-untyped-def]
    """ADMIN 으로 인증된 클라이언트(가장 흔한 경우)."""
    app = app_factory(ADMIN)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


def new_skill_payload(**overrides: object) -> dict[str, object]:
    key = overrides.pop("skill_key", f"test.skill-{uuid.uuid4().hex[:8]}")
    payload: dict[str, object] = {
        "skill_key": key,
        "category": "테스트",
        "name": "테스트 스킬",
        "description": "설명",
        "instructions": "# 절차\n1. 한다\n",
        "aliases": ["test-alias"],
        "tools": ["didim-vault__list_my_resources"],
    }
    payload.update(overrides)
    return payload


#: MCP gateway 가 Auth `/token/delegate` 로 받아 온 위임 토큰의 주체.
#: role 은 실제 사용자의 것(ADMIN 일 수 있다)이지만 `actor` 가 붙어 있다.
DELEGATED_ADMIN = Principal(
    user_id=ADMIN.user_id,
    display_name=ADMIN.display_name,
    email=ADMIN.email,
    role=UserRole.ADMIN,
    actor="mcp",
)
