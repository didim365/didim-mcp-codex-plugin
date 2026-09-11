"""liveness / readiness.

- ``/health``: 프로세스 liveness. 의존성 무검사, 항상 200. 인증 불필요.
- ``/ready``: DB 미설정이면 bootstrap 모드로 200, 설정됐는데 연결 실패면 503.

연결 문자열·비밀번호·키는 응답에 넣지 않는다. "설정됨/미설정" 여부만 노출한다.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from app.api.deps import SettingsDep
from app.api.dto import HealthOut, ReadyOut
from app.db.session import Database

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut, summary="Liveness 점검")
async def health(settings: SettingsDep) -> HealthOut:
    return HealthOut(status="ok", service=settings.app_name, version=settings.version)


@router.get(
    "/ready",
    response_model=ReadyOut,
    summary="Readiness 점검 (의존성 확인)",
    responses={503: {"description": "DB 가 설정됐으나 연결할 수 없음"}},
)
async def ready(request: Request, response: Response, settings: SettingsDep) -> ReadyOut:
    database: Database | None = getattr(request.app.state, "database", None)
    checks: dict[str, object] = {
        "auth_enabled": settings.auth_enabled,
        "auth_base_url_configured": bool(settings.auth_base_url),
        "jwks_configured": settings.jwt_rs256_ready,
        "spa": bool(getattr(request.app.state, "spa_mounted", False)),
    }
    if database is None or not database.is_configured:
        checks["database"] = "not_configured"
        return ReadyOut(status="ready", mode="bootstrap", checks=checks)

    connected, schema_exists = await database.check()
    checks["database"] = "ok" if connected else "error"
    checks["schema"] = settings.effective_schema
    checks["schema_exists"] = schema_exists
    # schema 가 없으면 migration Job 이 아직 안 돌았다는 뜻이다. 연결만 됐다고 Ready 를
    # 내주면 kubelet 이 트래픽을 붙이고 모든 API 가 "relation does not exist" 로 500 난다.
    # 여기서 막아야 배포 순서(migration → rollout)가 manifest 밖에서도 강제된다.
    if not connected or not schema_exists:
        response.status_code = 503
        return ReadyOut(status="not_ready", mode="normal", checks=checks)
    return ReadyOut(status="ready", mode="normal", checks=checks)


__all__ = ["router"]
