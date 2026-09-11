"""애플리케이션 오류 + FastAPI 예외 핸들러.

오류 본문은 ``{"error": {"code": "...", "message": "..."}}`` 하나로 통일한다
(요청 스키마 검증 실패 422 만 FastAPI 기본 형식). didim-rag-backend 와 같은 계약이다.

**메시지에 자격증명·DSN·스택트레이스를 담지 않는다.**
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger("errors")


class SkillRegistryError(Exception):
    """도메인 오류의 뿌리. ``code`` 는 계약, ``message`` 는 사용자 안내 문구."""

    status_code = 400
    code = "BAD_REQUEST"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code


class NotFoundError(SkillRegistryError):
    status_code = 404
    code = "NOT_FOUND"


class ConflictError(SkillRegistryError):
    """동시 수정·상태 충돌(이미 publish 됨, skill_key 중복 등)."""

    status_code = 409
    code = "CONFLICT"


class ValidationError(SkillRegistryError):
    status_code = 422
    code = "VALIDATION_FAILED"


class ForbiddenError(SkillRegistryError):
    status_code = 403
    code = "FORBIDDEN"


class UnauthorizedError(SkillRegistryError):
    status_code = 401
    code = "UNAUTHORIZED"


class ServiceUnavailableError(SkillRegistryError):
    status_code = 503
    code = "SERVICE_UNAVAILABLE"


def error_body(code: str, message: str) -> dict[str, dict[str, str]]:
    return {"error": {"code": code, "message": message}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(SkillRegistryError)
    async def _domain(_: Request, exc: SkillRegistryError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=error_body(exc.code, exc.message))

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        # 연결 문자열/SQL/스택트레이스를 노출하지 않는다 — 타입명만 로깅한다.
        logger.error("unhandled error: %s", type(exc).__name__)
        return JSONResponse(
            status_code=500,
            content=error_body("INTERNAL_ERROR", "내부 오류가 발생했습니다."),
        )


__all__ = [
    "ConflictError",
    "ForbiddenError",
    "NotFoundError",
    "ServiceUnavailableError",
    "SkillRegistryError",
    "UnauthorizedError",
    "ValidationError",
    "error_body",
    "register_exception_handlers",
]
