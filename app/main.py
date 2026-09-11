"""FastAPI 앱 팩토리 + lifespan.

한 프로세스가 세 표면을 낸다(요구사항 §4 · §18).

    /api/v1/admin/**    ADMIN 전용 관리 REST
    /api/v1/runtime/**  Codex / MCP gateway 가 읽는 배포본 조회
    /login · /logout    Microsoft SSO 진입/종료(backend 소유)
    그 외                React Admin SPA (정적)

계층: Router → Service → Repository. transport 와 도메인 로직을 섞지 않는다.
Alembic migration 은 **앱 기동 시 자동 실행하지 않는다**(의도적 — 별도 Job 이다, §20).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from starlette.middleware.sessions import SessionMiddleware

from app.api.health import router as health_router
from app.api.v1.router import api_v1_router
from app.auth.jwks import DidimJwksClient
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger, set_request_id
from app.db.session import Database
from app.web import session as web_session
from app.web.routes import router as web_router
from app.web.spa import mount_spa

logger = get_logger("main")

DESCRIPTION = """
**Didim MCP Codex Plugin — Dynamic Skill Registry.**

Codex Plugin 의 Skill workflow 를 Git/재배포 없이 Admin Web 에서 관리한다.

| 하고 싶은 것 | endpoint |
|---|---|
| 배포된 Skill 을 읽는다(Codex / MCP gateway) | `GET /api/v1/runtime/skills/{skill_key}` |
| Skill 을 만들고 초안을 편집한다(운영자) | `/api/v1/admin/skills` |
| 배포 / 롤백 | `POST /api/v1/admin/skills/{id}/publish` · `/rollback` |
| 변경 이력을 본다 | `GET /api/v1/admin/audit-logs` |

### 인증

`Authorization: Bearer <Access JWT>` — 토큰은 `didim-mcp-auth-backend` 가 발급하고 이
서비스는 **검증만** 한다. 화면은 backend 가 심은 HttpOnly 쿠키로 성립한다.
**role 정본은 Auth `GET /api/v1/me`** 이며 JWT claim 이 아니다.

### 인가 경계

`skill_version_tools` 는 "이 workflow 가 쓰도록 의도된 Tool" 이라는 **orchestration 정보**다.
사용자의 실제 Tool 권한 정본이 아니다 — 최종 인가는 언제나 Microsoft → DIDIM Auth →
MCP gateway policy 가 강제한다. Skill Registry 는 그 경계를 우회할 수 없다.

### 오류 본문

`{"error": {"code": "...", "message": "..."}}`. 요청 스키마 검증 실패(422)만 FastAPI 기본
형식(`{"detail": [...]}`)을 그대로 쓴다.
"""

TAGS_METADATA = [
    {
        "name": "runtime",
        "description": (
            "**배포된 Skill 조회.** PUBLISHED + enabled 만 나온다 — 초안은 여기 존재하지 "
            "않는다. Codex thin router 와 MCP gateway 가 읽는 계약이다."
        ),
    },
    {"name": "admin-skills", "description": "**ADMIN 전용.** Skill 생성·초안·배포·롤백·사용 여부."},
    {"name": "admin-audit", "description": "**ADMIN 전용.** 변경 이력."},
    {"name": "me", "description": "화면 shell 표시 전용. 인가 판단에 쓰지 않는다."},
    {"name": "health", "description": "liveness / readiness 점검."},
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("starting %s v%s (env=%s)", settings.app_name, settings.version, settings.env)

    database = Database(settings)
    app.state.database = database
    app.state.jwks = (
        DidimJwksClient(
            settings.jwks_url or "",
            timeout_seconds=settings.jwt_jwks_http_timeout_seconds,
            cache_ttl_seconds=settings.jwt_jwks_cache_ttl_seconds,
        )
        if settings.jwt_rs256_ready
        else None
    )
    logger.info(
        "wired: database=%s dsn=%s auth=%s jwks=%s",
        database.is_configured,
        settings.database_dsn_safe,
        settings.auth_enabled,
        settings.jwt_rs256_ready,
    )
    try:
        yield
    finally:
        await database.dispose()


def create_app() -> FastAPI:
    settings = get_settings()

    # 인증을 켰는데 세션 비밀이 없으면 조용히 무인증으로 뜨지 않고 기동에서 막는다.
    if settings.auth_enabled and settings.session_secret is None:
        raise RuntimeError("DIDIM_SKILL_AUTH_ENABLED=true requires DIDIM_SKILL_SESSION_SECRET")
    if settings.auth_enabled and not settings.auth_base_url:
        raise RuntimeError("DIDIM_SKILL_AUTH_ENABLED=true requires DIDIM_SKILL_AUTH_BASE_URL")

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description=DESCRIPTION,
        openapi_tags=TAGS_METADATA,
        lifespan=lifespan,
    )

    if settings.session_secret is not None:
        app.add_middleware(
            SessionMiddleware,
            secret_key=settings.session_secret.get_secret_value(),
            session_cookie="skill_session",
            max_age=settings.session_ttl_seconds,
            https_only=settings.cookie_secure,
            same_site=settings.cookie_samesite,
        )

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex[:16]
        request.state.request_id = request_id
        set_request_id(request_id)
        try:
            response = await call_next(request)
        finally:
            set_request_id(None)
        response.headers["X-Request-Id"] = request_id
        # 요청 처리 중 예약된 인증 쿠키 변경을 여기서 한 번에 굽는다.
        web_session.apply_pending(request, response, settings)
        return response

    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(api_v1_router)
    app.include_router(web_router)
    # SPA fallback 은 **맨 마지막**에 등록한다 — catch-all 이라 먼저 등록하면 위 라우터를 가린다.
    app.state.spa_mounted = mount_spa(app, settings.spa_dir)
    return app


app = create_app()

__all__ = ["app", "create_app"]
