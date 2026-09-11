"""Admin 화면 세션 — HttpOnly 토큰 쿠키 + 서명 세션 쿠키(CSRF) .

토큰을 어디에 두는가(didim-mcp-service-backend `app/web/auth_session.py` 와 같은 판단):

- **서명 세션 쿠키**(`skill_session`)에는 CSRF 토큰과 사용자 id 만 둔다. 서명은 암호화가
  아니라서 값이 브라우저에서 그대로 읽힌다 — JWT 를 여기 넣지 않는다.
- Access/Refresh Token 은 **각각 별도 HttpOnly 쿠키**에 둔다. JS 가 읽을 수 없고
  localStorage/DB/로그 어디에도 저장하지 않는다.

쿠키 변경은 요청 처리 중간(갱신 시점)에 정해지므로 `request.state` 에 예약하고 미들웨어가
응답에 굽는다 — 라우트마다 쿠키 굽는 코드를 복제하지 않기 위한 최소 장치다.
"""

from __future__ import annotations

import secrets

from fastapi import Request, Response
from pydantic import SecretStr

from app.auth.auth_client import AuthTokens
from app.core.config import Settings

ACCESS_COOKIE = "skill_auth_access"  # 쿠키 이름(토큰 아님)
REFRESH_COOKIE = "skill_auth_refresh"  # 쿠키 이름(토큰 아님)
SESSION_UID = "uid"
SESSION_CSRF = "csrf"
CSRF_HEADER = "X-CSRF-Token"

_PENDING = "pending_auth_cookies"
_UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def _session(request: Request) -> dict[str, object]:
    # SessionMiddleware 미설치(세션 비밀 미설정) 대비 안전 접근.
    return getattr(request, "session", {})


# ── 읽기 ──────────────────────────────────────────────────


def bearer_credential(request: Request) -> SecretStr | None:
    """`Authorization: Bearer <JWT>` 만 본다. 원문은 로그하지 않는다."""
    raw = request.headers.get("authorization")
    if not raw:
        return None
    parts = raw.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return SecretStr(token) if token else None


def access_token(request: Request) -> SecretStr | None:
    """이번 요청에 유효한 Access Token. 우선순위: 이번 요청 갱신분 → Bearer 헤더 → 쿠키."""
    pending = getattr(request.state, _PENDING, "absent")
    if isinstance(pending, AuthTokens):
        return pending.access_token
    if pending is None:  # 이번 요청에서 세션을 종료하기로 했다.
        return None
    presented = bearer_credential(request)
    if presented is not None:
        return presented
    raw = request.cookies.get(ACCESS_COOKIE)
    return SecretStr(raw) if raw else None


def refresh_token(request: Request) -> SecretStr | None:
    pending = getattr(request.state, _PENDING, "absent")
    if isinstance(pending, AuthTokens):
        return pending.refresh_token
    if pending is None:
        return None
    raw = request.cookies.get(REFRESH_COOKIE)
    return SecretStr(raw) if raw else None


# ── 예약 / 적용 ───────────────────────────────────────────


def remember(request: Request, tokens: AuthTokens) -> None:
    setattr(request.state, _PENDING, tokens)


def forget(request: Request) -> None:
    setattr(request.state, _PENDING, None)


def apply_pending(request: Request, response: Response, settings: Settings) -> None:
    """예약된 쿠키 변경을 응답에 적용한다. `app/main.py` 미들웨어가 호출한다."""
    pending = getattr(request.state, _PENDING, "absent")
    if pending == "absent":
        return
    if pending is None:
        response.delete_cookie(ACCESS_COOKIE, path="/")
        response.delete_cookie(REFRESH_COOKIE, path="/")
        return
    assert isinstance(pending, AuthTokens)
    for name, value in (
        (ACCESS_COOKIE, pending.access_token),
        (REFRESH_COOKIE, pending.refresh_token),
    ):
        response.set_cookie(
            name,
            value.get_secret_value(),
            httponly=True,  # 항상 켠다 — JS 가 토큰을 읽을 수 없다.
            secure=settings.cookie_secure,
            samesite=settings.cookie_samesite,
            path="/",
        )
    # 토큰이 실린 응답은 프록시/브라우저 캐시에 남지 않게 한다.
    response.headers["Cache-Control"] = "no-store"


# ── 세션 / CSRF ───────────────────────────────────────────


def login_session(request: Request, user_id: str) -> None:
    """세션 고정 방지: 세션을 비우고 uid + 새 CSRF 토큰을 심는다."""
    sess = _session(request)
    sess.clear()
    sess[SESSION_UID] = user_id
    sess[SESSION_CSRF] = secrets.token_urlsafe(32)


def logout_session(request: Request) -> None:
    _session(request).clear()


def ensure_csrf_token(request: Request) -> str:
    sess = _session(request)
    token = sess.get(SESSION_CSRF)
    if not token:
        token = secrets.token_urlsafe(32)
        sess[SESSION_CSRF] = token
    return str(token)


def csrf_ok(request: Request) -> bool:
    """더블 서브밋 검증. 안전 메서드는 항상 통과."""
    if request.method not in _UNSAFE_METHODS:
        return True
    expected = _session(request).get(SESSION_CSRF)
    provided = request.headers.get(CSRF_HEADER)
    if not expected or not provided:
        return False
    return secrets.compare_digest(str(expected), str(provided))


__all__ = [
    "ACCESS_COOKIE",
    "CSRF_HEADER",
    "REFRESH_COOKIE",
    "SESSION_CSRF",
    "SESSION_UID",
    "access_token",
    "apply_pending",
    "bearer_credential",
    "csrf_ok",
    "ensure_csrf_token",
    "forget",
    "login_session",
    "logout_session",
    "refresh_token",
    "remember",
]
