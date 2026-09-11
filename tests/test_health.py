"""`/ready` 가 배포 순서를 강제한다 — 요구사항 §19 · §20.

migration Job 이 아직 안 돌아 schema 가 없으면 **Ready 를 내주면 안 된다.** 연결만 됐다고
200 을 주면 kubelet 이 트래픽을 붙이고 모든 API 가 "relation does not exist" 로 죽는다.
"""

from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from tests.conftest import ADMIN


async def _ready(app_factory, connected: bool, schema_exists: bool) -> tuple[int, dict]:  # type: ignore[no-untyped-def]
    app = app_factory(ADMIN)

    async def _check() -> tuple[bool, bool]:
        return connected, schema_exists

    app.state.database.check = _check  # type: ignore[method-assign]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/ready")
    return resp.status_code, resp.json()


async def test_ready_is_503_when_schema_is_missing(app_factory) -> None:  # type: ignore[no-untyped-def]
    status, body = await _ready(app_factory, connected=True, schema_exists=False)
    assert status == 503
    assert body["status"] == "not_ready"
    assert body["checks"]["schema_exists"] is False


async def test_ready_is_503_when_database_is_down(app_factory) -> None:  # type: ignore[no-untyped-def]
    status, body = await _ready(app_factory, connected=False, schema_exists=False)
    assert status == 503
    assert body["status"] == "not_ready"


async def test_ready_is_200_after_migration(app_factory) -> None:  # type: ignore[no-untyped-def]
    status, body = await _ready(app_factory, connected=True, schema_exists=True)
    assert status == 200
    assert body["status"] == "ready"
    assert body["checks"]["schema"] == "mcp_skill_registry"


async def test_health_never_depends_on_the_database(app_factory) -> None:  # type: ignore[no-untyped-def]
    """liveness 는 의존성을 보지 않는다 — DB 가 죽었다고 Pod 을 재시작하면 안 된다."""
    app = app_factory(ADMIN)

    async def _down() -> tuple[bool, bool]:
        return False, False

    app.state.database.check = _down  # type: ignore[method-assign]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
