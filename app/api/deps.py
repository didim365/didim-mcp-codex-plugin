"""FastAPI dependency — 트랜잭션 경계와 **인가 가드**.

인가 규칙(요구사항 §6 · §10 · §11):

- ``/api/v1/admin/**`` → 인증 필요 + **role == ADMIN**. 미인증 401, USER/DEVELOPER 403.
  화면에서 메뉴를 감추는 것은 인가가 아니다 — 차단은 여기서 한다.
- ``/api/v1/runtime/**`` → 인증 필요(기본). role 은 보지 않는다. published skill 조회는
  관리자 권한을 요구하지 않지만, 익명으로 사내 workflow 전문을 공개하지도 않는다.
- role 정본은 **Auth `/api/v1/me`** 다. JWT 에 role claim 이 없다(Auth CLAUDE.md).

트랜잭션 경계는 ``get_session`` 이 소유한다. Service/Repository 는 ``flush`` 만 하고
``commit`` 하지 않는다 — didim-mcp-service-backend 와 같은 규약이다.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.auth_client import AuthClient, AuthRejectedError, AuthUnavailableError
from app.auth.jwt_verifier import (
    DidimJwtVerifier,
    JwtConfigError,
    JwtVerificationError,
)
from app.auth.principal import Principal, parse_role
from app.core.config import Settings, get_settings
from app.core.errors import (
    ForbiddenError,
    ServiceUnavailableError,
    UnauthorizedError,
)
from app.core.logging import get_logger
from app.db.session import Database
from app.domain.enums import UserRole
from app.web import session as web_session

logger = get_logger("api.deps")

#: 인증이 꺼진 로컬/부트스트랩에서 쓰는 가짜 ADMIN. 운영에서는 절대 생기지 않는다
#: (`auth_enabled=true` 면 이 경로를 타지 않는다).
_LOCAL_ADMIN = Principal(
    user_id="00000000-0000-0000-0000-000000000000",
    display_name="로컬 개발자",
    email=None,
    role=UserRole.ADMIN,
)


def get_settings_dep() -> Settings:
    return get_settings()


SettingsDep = Annotated[Settings, Depends(get_settings_dep)]


def get_database(request: Request) -> Database:
    db: Database | None = getattr(request.app.state, "database", None)
    if db is None or not db.is_configured:
        raise ServiceUnavailableError("데이터베이스가 준비되지 않았습니다.")
    return db


async def get_session(
    request: Request,
    database: Annotated[Database, Depends(get_database)],
) -> AsyncIterator[AsyncSession]:
    """요청 하나 = 트랜잭션 하나. 정상 종료에만 commit 한다.

    **commit 은 보통 여기가 아니라 `TransactionalRoute` 에서 일어난다.** 이 teardown 은
    응답을 보낸 뒤에 실행되기 때문이다(`app/api/transaction.py` 의 실측 참고). 여기 남은
    commit 은 route class 를 붙이지 않은 라우터를 위한 안전망이고, 이미 커밋됐으면
    `in_transaction()` 이 False 라 아무 일도 하지 않는다.
    """
    async with database.sessionmaker() as session:
        request.state.session = session
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        else:
            if session.in_transaction():
                await session.commit()


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _correlation(request: Request) -> dict[str, str]:
    """Auth 호출에 전파할 상관관계 헤더. **서버가 생성한 값만** 쓴다(외부 값 미신뢰)."""
    rid = getattr(request.state, "request_id", None)
    if not isinstance(rid, str) or not rid:
        return {}
    return {"X-Request-ID": rid, "X-Correlation-ID": rid}


async def _authenticate(request: Request, settings: Settings) -> Principal:
    """자격증명 → 검증된 Principal. 실패는 fail-closed.

    흐름: 토큰 추출 → 서명/claim 검증 → **같은 토큰으로 Auth `/me`** → sub 일치 확인 →
    현재 role/status 확정. `/me` 를 매번 부르는 이유는 role 정본이 Auth DB 이고, 토큰
    TTL 이 남아 있어도 강등/비활성이 즉시 반영되어야 하기 때문이다.
    """
    credential: SecretStr | None = web_session.access_token(request)
    if credential is None:
        raise UnauthorizedError("로그인이 필요합니다.")

    verifier: DidimJwtVerifier = DidimJwtVerifier(
        settings, getattr(request.app.state, "jwks", None)
    )
    try:
        verified = await verifier.verify(credential.get_secret_value())
    except JwtConfigError:
        logger.error("jwt verification unavailable (config)")
        raise ServiceUnavailableError("인증 검증을 사용할 수 없습니다.") from None
    except JwtVerificationError as exc:
        logger.info("jwt rejected (code=%s)", exc.code)
        raise UnauthorizedError("자격증명이 유효하지 않습니다.") from None

    try:
        me = await AuthClient(settings).get_me(credential, correlation=_correlation(request))
    except AuthRejectedError as exc:
        if exc.inactive:
            raise ForbiddenError("비활성 사용자입니다.") from None
        raise UnauthorizedError("자격증명이 유효하지 않습니다.") from None
    except AuthUnavailableError:
        # 신원을 확인할 수 없으면 통과시키지 않는다(fail-closed).
        raise UnauthorizedError("신원을 확인할 수 없습니다.") from None

    if me.id != str(verified.user_id):
        logger.warning("subject mismatch between token and /me")
        raise UnauthorizedError("자격증명이 유효하지 않습니다.")
    if not me.is_active:
        raise ForbiddenError("비활성 사용자입니다.")

    return Principal(
        user_id=me.id,
        display_name=me.display_name,
        email=me.email,
        role=parse_role(me.role),
        actor=verified.actor,
    )


async def require_admin(request: Request, settings: SettingsDep) -> Principal:
    """Admin API 가드. 미인증 401 / 비관리자 403 / 쿠키 경로는 CSRF 까지.

    Bearer 경로는 CSRF 를 요구하지 않는다(쿠키가 자동 전송되는 요청이 아니다). 세션 쿠키
    경로만 더블 서브밋을 강제한다.
    """
    if not settings.auth_enabled:
        request.state.principal = _LOCAL_ADMIN
        return _LOCAL_ADMIN

    principal = await _authenticate(request, settings)
    if not principal.is_admin:
        logger.info("admin api denied: role=%s user=%s", principal.role, principal.user_id)
        raise ForbiddenError("관리자 권한이 필요합니다.")
    # 위임 토큰(MCP gateway 등 대리인)으로 관리 API 를 쓰지 못하게 한다 — 관리 작업은
    # 사람이 브라우저/Swagger 에서 직접 하는 것이다.
    if principal.is_delegated:
        raise ForbiddenError("위임 토큰으로는 관리 API 를 사용할 수 없습니다.")
    if web_session.bearer_credential(request) is None and not web_session.csrf_ok(request):
        raise ForbiddenError("CSRF 토큰이 없거나 일치하지 않습니다.")
    request.state.principal = principal
    return principal


AdminDep = Annotated[Principal, Depends(require_admin)]


async def require_runtime_caller(request: Request, settings: SettingsDep) -> Principal | None:
    """Runtime API 가드 — 인증만 요구하고 role 은 보지 않는다.

    호출자는 보통 MCP gateway 가 Auth `/token/delegate` 로 받아 온 이 서비스 audience 의
    위임 토큰이다(`act.sub=mcp`). 사람 토큰도 같은 방식으로 통과한다 — 자기 Codex 세션에서
    published workflow 를 읽는 것은 정상이다.

    ``runtime_auth_required=false`` 는 **로컬 개발 전용** 이다. 운영에서 내리면 사내
    workflow 전문이 익명 공개된다.
    """
    if not settings.auth_enabled or not settings.runtime_auth_required:
        return None
    return await _authenticate(request, settings)


RuntimeCallerDep = Annotated[Principal | None, Depends(require_runtime_caller)]


__all__ = [
    "AdminDep",
    "RuntimeCallerDep",
    "SessionDep",
    "SettingsDep",
    "get_database",
    "get_session",
    "require_admin",
    "require_runtime_caller",
]
