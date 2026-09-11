"""API v1 라우터 조립 — **인가 가드가 붙는 곳**.

가드는 개별 endpoint decorator 가 아니라 여기 `include_router(..., dependencies=[...])` 에
붙는다. 새 관리 endpoint 를 추가할 때 가드를 빠뜨릴 수 없게 하기 위한 구조다
(didim-mcp-service-backend `app/api/v1/router.py` 와 같은 규약).

    /api/v1/admin/**    → require_admin (ADMIN 만. 미인증 401 / USER 403)
    /api/v1/runtime/**  → require_runtime_caller (인증만. role 무관)
    /api/v1/me          → 가드 없음(미인증도 200 으로 "로그인 안 됨" 을 답한다)

트랜잭션 종료(`TransactionalRoute`)는 **여기에 붙지 않는다.** FastAPI 는 `include_router`
로 넣은 하위 라우터의 route class 를 그대로 유지하므로(부모의 `route_class` 가 자식에게
내려가지 않는다 — 실측), endpoint 를 선언하는 **각 라우터 파일**에서 지정한다.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import require_admin
from app.api.v1 import admin_audit, admin_skills, me, runtime_skills

api_v1_router = APIRouter(prefix="/api/v1")

_admin = APIRouter(prefix="/admin")
_admin.include_router(admin_skills.router)
_admin.include_router(admin_audit.router)

api_v1_router.include_router(_admin, dependencies=[Depends(require_admin)])
api_v1_router.include_router(runtime_skills.router)
api_v1_router.include_router(me.router)

__all__ = ["api_v1_router"]
