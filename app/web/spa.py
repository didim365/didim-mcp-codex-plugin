"""React SPA 정적 서빙 + fallback.

단일 container 이므로 FastAPI 가 API 와 화면을 함께 낸다(요구사항 §18). 위험한 지점은
**SPA fallback 이 backend 경로를 먹는 것** 하나다. 그래서:

- fallback 은 `GET`/`HEAD` 로만 동작한다.
- `_RESERVED_PREFIXES` 로 시작하는 경로는 **절대** index.html 로 떨어지지 않는다. API 가
  404 를 내야 할 자리에 HTML 이 돌아가면 화면은 "성공" 으로 보고 파싱에서 죽는다.
- 실제 파일이 있으면 그 파일을, 없으면 index.html 을 돌려준다(client-side routing).

빌드 산출물이 없으면(로컬 API 개발) mount 를 건너뛴다 — API 는 화면 없이도 동작해야 한다.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app.core.errors import error_body
from app.core.logging import get_logger

logger = get_logger("web.spa")

#: 이 접두사로 시작하면 SPA 가 아니라 backend 의 것이다. 먹히면 조용히 깨진다.
_RESERVED_PREFIXES = (
    "/api/",
    "/health",
    "/ready",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/login",
    "/logout",
    "/assets/",
)


def mount_spa(app: FastAPI, spa_dir: str) -> bool:
    """SPA 를 mount 한다. 산출물이 없으면 False 를 돌려주고 아무것도 하지 않는다."""
    root = Path(spa_dir)
    if not root.is_absolute():
        root = Path(__file__).resolve().parents[2] / spa_dir
    index = root / "index.html"
    if not index.is_file():
        logger.warning("spa build not found at %s; serving api only", root)
        return False

    assets = root / "assets"
    if assets.is_dir():
        # 해시가 붙은 불변 파일이라 별도 mount 로 곧바로 낸다.
        app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> Response:
        path = "/" + full_path
        if any(path.startswith(p) or path == p.rstrip("/") for p in _RESERVED_PREFIXES):
            # backend 경로인데 여기까지 왔다 = 그런 endpoint 가 없다. HTML 로 위장하지 않는다.
            return JSONResponse(
                status_code=404, content=error_body("NOT_FOUND", "요청한 경로가 없습니다.")
            )
        candidate = (root / full_path).resolve()
        # path traversal 방어: 산출물 디렉터리 밖은 절대 내보내지 않는다.
        if full_path and candidate.is_file() and candidate.is_relative_to(root.resolve()):
            return FileResponse(candidate)
        return FileResponse(index, headers={"Cache-Control": "no-cache"})

    logger.info("spa mounted from %s", root)
    return True


__all__ = ["mount_spa"]
