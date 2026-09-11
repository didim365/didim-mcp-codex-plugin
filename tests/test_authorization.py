"""인가 경계 — 요구사항 §6 · §34-5,6.

미인증 401 / 일반 USER 403 / ADMIN 허용. 화면에서 감추는 것이 아니라 **backend 가**
막는다는 사실을 여기서 고정한다.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.principal import Principal
from tests.conftest import ADMIN, DELEGATED_ADMIN, USER, new_skill_payload

ADMIN_PATHS = [
    ("GET", "/api/v1/admin/skills"),
    ("GET", "/api/v1/admin/skills/categories"),
    ("GET", "/api/v1/admin/audit-logs"),
]


async def _client(app_factory, principal, runtime=ADMIN) -> AsyncClient:  # type: ignore[no-untyped-def]
    app = app_factory(principal, runtime_principal=runtime)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.parametrize(("method", "path"), ADMIN_PATHS)
async def test_unauthenticated_admin_is_rejected(app_factory, method, path) -> None:  # type: ignore[no-untyped-def]
    async with await _client(app_factory, None) as ac:
        resp = await ac.request(method, path)
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.parametrize(("method", "path"), ADMIN_PATHS)
async def test_plain_user_gets_403(app_factory, method, path) -> None:  # type: ignore[no-untyped-def]
    async with await _client(app_factory, USER) as ac:
        resp = await ac.request(method, path)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


async def test_admin_is_allowed(app_factory) -> None:  # type: ignore[no-untyped-def]
    async with await _client(app_factory, ADMIN) as ac:
        resp = await ac.get("/api/v1/admin/skills")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


async def test_user_cannot_create_or_publish(app_factory) -> None:  # type: ignore[no-untyped-def]
    """mutation 도 같은 가드다 — 조회만 막고 쓰기를 여는 실수를 잡는다."""
    async with await _client(app_factory, USER) as ac:
        create = await ac.post("/api/v1/admin/skills", json=new_skill_payload())
        publish = await ac.post(
            "/api/v1/admin/skills/00000000-0000-0000-0000-000000000000/publish",
            json={"version": 1},
        )
    assert create.status_code == 403
    assert publish.status_code == 403


async def test_runtime_requires_authentication(app_factory) -> None:  # type: ignore[no-untyped-def]
    """runtime 은 role 을 보지 않지만 **익명 공개도 아니다**(요구사항 §10)."""
    async with await _client(app_factory, ADMIN, runtime=None) as ac:
        resp = await ac.get("/api/v1/runtime/skills")
    assert resp.status_code == 401


async def test_runtime_allows_non_admin(app_factory) -> None:  # type: ignore[no-untyped-def]
    """일반 사용자(또는 MCP 위임 토큰)도 배포본은 읽을 수 있어야 한다."""
    async with await _client(app_factory, USER, runtime=USER) as ac:
        resp = await ac.get("/api/v1/runtime/skills")
    assert resp.status_code == 200


async def test_delegated_token_is_rejected_by_admin_guard() -> None:
    """MCP 위임 토큰으로는 관리 API 를 쓸 수 없다 — role 이 ADMIN 이어도 안 된다.

    이게 없으면 Codex 세션에서 `didim-skill__*` 를 쓸 수 있는 ADMIN 사용자가, MCP gateway
    를 통해 그대로 publish/rollback 까지 부를 수 있게 된다. 관리 작업은 **사람이 브라우저
    에서** 하는 것이고, 대리인은 대리인일 뿐이다.

    `app_factory` 는 `require_admin` 자체를 override 하므로 여기서는 쓰지 않는다 — 진짜
    가드 함수를 부른다. `_authenticate` 만 대체해서 JWT/Auth 왕복을 건너뛴다.
    """
    from starlette.requests import Request

    from app.api import deps
    from app.core.config import Settings
    from app.core.errors import ForbiddenError

    settings = Settings(auth_enabled=True)
    request = Request(
        {"type": "http", "method": "POST", "path": "/api/v1/admin/skills", "headers": []}
    )

    async def _fake(_request: Request, _settings: Settings) -> Principal:
        return DELEGATED_ADMIN

    original = deps._authenticate
    deps._authenticate = _fake  # type: ignore[assignment]
    try:
        with pytest.raises(ForbiddenError) as admin_denied:
            await deps.require_admin(request, settings)
        # 같은 신원이 runtime 에서는 정상 통과한다 — 경계는 경로별로 다르다.
        assert await deps.require_runtime_caller(request, settings) is DELEGATED_ADMIN
    finally:
        deps._authenticate = original  # type: ignore[assignment]

    assert "위임" in str(admin_denied.value.message)
