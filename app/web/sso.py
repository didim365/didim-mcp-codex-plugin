"""Microsoft SSO 진입/복귀 + 통합 로그아웃 — 쿠키와 다음 목적지 계산.

이 서비스는 **Microsoft/Azure 와 직접 통신하지 않는다.** Entra ID Token 검증도 Graph 조회도
`didim-mcp-auth-backend` 만 하고, 여기서 하는 일은 셋뿐이다(didim-mcp-service-backend
`app/web/sso.py` 와 같은 구조).

1. 로그인 흐름을 이 브라우저에 **결박**할 opaque 값(`skill_sso_flow`)을 만들고 대조한다.
2. 자동 SSO 가 무한 왕복이 되지 않게 loop guard(`skill_sso_pause`)를 심는다.
3. 통합 로그아웃 체인의 다음 목적지를 **우리 설정의 Auth 주소로만** 만든다.

두 쿠키에는 **토큰도 신원도 없다.** 로그인 세션은 `app/web/session.py` 의 HttpOnly 토큰
쿠키가 담당한다.
"""

from __future__ import annotations

import re
import secrets
from urllib.parse import urlencode

from fastapi import Request, Response

from app.core.config import Settings

FLOW_COOKIE = "skill_sso_flow"  # 쿠키 이름(비밀 아님)
PAUSE_COOKIE = "skill_sso_pause"  # 쿠키 이름(비밀 아님)

LOGIN_PATH = "/login"
MICROSOFT_LOGIN_PATH = f"{LOGIN_PATH}/microsoft"
MICROSOFT_CALLBACK_PATH = f"{MICROSOFT_LOGIN_PATH}/callback"
FRONTCHANNEL_LOGOUT_PATH = "/logout/frontchannel"

#: Auth 의 로그인 의도 값(`LoginMode`). 자동 진입에는 **아무것도 붙이지 않는다** —
#: `prompt=select_account` 가 번지면 자동 SSO 가 통째로 사라진다.
MODE_USER_INITIATED = "user_initiated"
MODE_ACCOUNT_SELECTION = "account_selection"
USER_INITIATED_MODES = frozenset({MODE_USER_INITIATED, MODE_ACCOUNT_SELECTION})

_FLOW_MAX_AGE = 600
_PAUSE_MAX_AGE = 300

_SLO_SERVICE_PATTERN = re.compile(r"^[a-z0-9_-]{1,64}$")
_SLO_MAX_HOPS = 64


def new_flow_state() -> str:
    """이 브라우저의 로그인 흐름을 가리킬 opaque 값(Auth 의 16~128 urlsafe 제약 충족)."""
    return secrets.token_urlsafe(32)


def set_flow_cookie(response: Response, settings: Settings, flow_state: str) -> None:
    """login CSRF 방지의 한쪽 절반.

    같은 값을 Auth 에 `service_flow_state` 로 보내고, Auth 는 서명된 OAuth state 안에 넣어
    Microsoft 왕복 후 `state=` 로 되돌려준다. callback 은 쿠키와 되돌아온 값을 constant-time
    으로 대조해야만 교환을 진행한다. 값은 브라우저 밖으로 나가지만 **자격증명이 아니다.**
    """
    response.set_cookie(
        FLOW_COOKIE,
        flow_state,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path=LOGIN_PATH,
        max_age=_FLOW_MAX_AGE,
    )


def clear_flow_cookie(response: Response) -> None:
    response.delete_cookie(FLOW_COOKIE, path=LOGIN_PATH)


def flow_state_matches(request: Request, returned: str) -> bool:
    """되돌아온 flow state 가 이 브라우저의 쿠키와 같은가.

    `compare_digest` 는 non-ASCII str 에서 TypeError 를 내므로 비교 전에 ASCII 를 확인한다
    (query 는 신뢰 경계다).
    """
    expected = request.cookies.get(FLOW_COOKIE)
    if not expected or not returned or not returned.isascii():
        return False
    return secrets.compare_digest(expected, returned)


def set_pause_cookie(response: Response, settings: Settings) -> None:
    """자동 진입이 **진행 중**이라는 표식. 로그인 화면을 실제로 그릴 때 내린다."""
    response.set_cookie(
        PAUSE_COOKIE,
        "1",
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
        max_age=_PAUSE_MAX_AGE,
    )


def clear_pause_cookie(response: Response) -> None:
    response.delete_cookie(PAUSE_COOKIE, path="/")


def auto_login_location(request: Request, settings: Settings) -> str:
    """미인증 사용자를 보낼 곳.

    Microsoft SSO 가 설정돼 있고 진행 중인 자동 진입이 없다면 로그인 화면을 건너뛰고 바로
    SSO 를 시작한다 — 같은 Entra tenant 에 이미 로그인한 사용자는 버튼을 누르지 않고 들어온다.
    """
    if settings.microsoft_login_url and not request.cookies.get(PAUSE_COOKIE):
        return MICROSOFT_LOGIN_PATH
    return LOGIN_PATH


def start_url(settings: Settings, flow_state: str, *, mode: str = "") -> str:
    """Auth 의 Microsoft 로그인 시작 URL. 복귀 주소를 query 로 보내지 않는다.

    `mode` 는 사용자가 직접 누른 값일 때만 넘긴다 — 그 외 문자열은 **버린다**(요청 값이
    Microsoft `prompt` 로 흘러가는 것을 막는 두 번째 방어선. 첫 번째는 Auth 의 enum 이다).
    """
    login_url = settings.microsoft_login_url
    params = {"service_flow_state": flow_state}
    if mode in USER_INITIATED_MODES:
        params["mode"] = mode
    separator = "&" if "?" in login_url else "?"
    return f"{login_url}{separator}{urlencode(params)}"


def slo_continue_url(settings: Settings, service: str, index: int) -> str:
    """통합 로그아웃 체인의 다음 hop(Auth) URL. 이어갈 수 없으면 빈 문자열.

    호스트는 **우리 설정**에서만 오고 요청이 준 URL 은 쓰지 않는다. 인덱스 상한이 있어 어떤
    입력으로도 무한 왕복이 되지 않는다.
    """
    base = (settings.auth_public_base_url or "").rstrip("/")
    if not base or not 1 <= index <= _SLO_MAX_HOPS:
        return ""
    if not _SLO_SERVICE_PATTERN.fullmatch(service):
        return ""
    return f"{base}/api/v1/auth/slo?{urlencode({'service': service, 'i': index})}"


__all__ = [
    "FLOW_COOKIE",
    "FRONTCHANNEL_LOGOUT_PATH",
    "LOGIN_PATH",
    "MICROSOFT_CALLBACK_PATH",
    "MICROSOFT_LOGIN_PATH",
    "MODE_ACCOUNT_SELECTION",
    "MODE_USER_INITIATED",
    "PAUSE_COOKIE",
    "USER_INITIATED_MODES",
    "auto_login_location",
    "clear_flow_cookie",
    "clear_pause_cookie",
    "flow_state_matches",
    "new_flow_state",
    "set_flow_cookie",
    "set_pause_cookie",
    "slo_continue_url",
    "start_url",
]
