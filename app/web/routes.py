"""인증 진입/종료 — backend 가 소유하는 경로. React SPA 가 먹으면 안 된다.

    GET  /login                       로그인 화면(SPA 로 넘긴다) 또는 자동 SSO 진입
    GET  /login/microsoft             SSO 시작(flow state 쿠키 + Auth 로 302)
    GET  /login/microsoft/callback    login_code 교환 → 세션 + HttpOnly 토큰 쿠키
    POST /logout                      Refresh 폐기 + 쿠키 정리 + 통합 로그아웃 체인
    GET  /logout/frontchannel         다른 서비스의 로그아웃 체인이 이 서비스를 지나갈 때

흐름(didim-mcp-service-backend 와 동일):

    /login/microsoft → Auth GET /api/v1/auth/microsoft/login?service=skill&service_flow_state=...
      → Microsoft Entra 로그인 → Auth callback(ID Token 검증)
      → 이 서비스 /login/microsoft/callback?code=<1회용>&state=<flow state>
      → 쿠키 flow state 와 constant-time 대조 → 통과해야만 Auth POST /auth/microsoft/exchange
      → Access/Refresh 를 HttpOnly 쿠키로 굽고 세션 생성

토큰은 브라우저 URL·history·HTML 어디에도 실리지 않는다. `code`/`state` 는 이 모듈 밖으로
나가지 않는다(로그·감사 미기록).
"""

from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse, Response

from app.auth.auth_client import AuthClient, AuthRejectedError, AuthUnavailableError
from app.core.config import get_settings
from app.core.logging import get_logger
from app.web import session as web_session
from app.web import sso

logger = get_logger("web.routes")

router = APIRouter(include_in_schema=False)

#: 로그인 후 착지 화면. SPA 의 첫 화면이다.
_HOME = "/admin/skills"


@router.get("/login")
async def login(request: Request) -> Response:
    """미인증 진입점. 자동 SSO 를 걸지, 로그인 화면을 보일지 **서버가** 정한다.

    판정 근거인 loop guard 쿠키가 HttpOnly 라 화면은 이 판정을 할 수 없다.
    """
    settings = get_settings()
    if not settings.auth_enabled:
        return RedirectResponse(url=_HOME, status_code=303)
    target = sso.auto_login_location(request, settings)
    if target == sso.MICROSOFT_LOGIN_PATH:
        return RedirectResponse(url=target, status_code=303)
    # 로그인 화면을 실제로 그린다 = 무인 연쇄가 사람 눈앞에서 끝났다 → loop guard 를 내린다.
    response = RedirectResponse(url="/login/screen", status_code=303)
    sso.clear_pause_cookie(response)
    return response


@router.get("/login/microsoft")
async def microsoft_login_start(mode: str = "") -> Response:
    settings = get_settings()
    if not settings.microsoft_login_url:
        # 설정이 없으면 깨진 링크로 보내지 않는다.
        return RedirectResponse(url="/login/screen?error=sso_not_configured", status_code=303)
    flow_state = sso.new_flow_state()
    response = RedirectResponse(sso.start_url(settings, flow_state, mode=mode), status_code=302)
    sso.set_flow_cookie(response, settings, flow_state)
    sso.set_pause_cookie(response, settings)
    return response


@router.get("/login/microsoft/callback")
async def microsoft_login_callback(
    request: Request, code: str = "", state: str = "", slo_pause: int = 0
) -> Response:
    """1회용 login_code 를 토큰으로 교환하고 세션을 만든다.

    실패 사유를 세분화하지 않는다. 어느 실패 경로에서든 flow 쿠키는 지운다(1회용 흐름).
    """
    settings = get_settings()

    def _fail(reason: str) -> Response:
        resp = RedirectResponse(url=f"/login/screen?error={reason}", status_code=303)
        sso.clear_flow_cookie(resp)
        sso.clear_pause_cookie(resp)
        return resp

    if slo_pause:
        # 통합 로그아웃 직후라 Auth 가 Microsoft 로 보내지 않고 되돌린 것이다. 실패가 아니다.
        resp = RedirectResponse(url="/login/screen", status_code=303)
        sso.clear_flow_cookie(resp)
        sso.clear_pause_cookie(resp)
        return resp

    # 이 브라우저가 시작한 흐름인지 확인한다(login CSRF 차단). 불일치·누락이면 **교환을
    # 호출하지 않는다.**
    if not code or not sso.flow_state_matches(request, state):
        logger.info("microsoft sso: flow state mismatch or missing code")
        return _fail("sso_state")

    try:
        tokens = await AuthClient(settings).exchange_login_code(code)
        me = await AuthClient(settings).get_me(tokens.access_token)
    except AuthRejectedError:
        return _fail("sso_rejected")
    except AuthUnavailableError:
        logger.warning("microsoft sso: auth backend call failed")
        return _fail("auth_unavailable")

    if not me.is_active:
        return _fail("inactive_user")

    response = RedirectResponse(url=_HOME, status_code=303)
    sso.clear_flow_cookie(response)
    sso.clear_pause_cookie(response)
    web_session.remember(request, tokens)
    web_session.login_session(request, me.id)
    logger.info("login ok: user=%s role=%s", me.id, me.role)
    return response


@router.post("/logout")
async def logout(request: Request, csrf_token: str = Form(default="")) -> Response:
    """Refresh 폐기 + 쿠키/세션 정리 + 통합 로그아웃 체인 시작.

    CSRF 불일치여도 **로컬 세션·쿠키는 반드시 지운다**(상태를 더 여는 방향이 아니다).
    """
    settings = get_settings()
    expected = getattr(request, "session", {}).get(web_session.SESSION_CSRF)
    header_token = request.headers.get(web_session.CSRF_HEADER) or csrf_token
    if expected and header_token == expected:
        token = web_session.refresh_token(request)
        if token is not None:
            await AuthClient(settings).logout(token)

    web_session.forget(request)
    web_session.logout_session(request)
    slo_url = settings.slo_start_url
    return RedirectResponse(url=slo_url or "/login/screen", status_code=303)


@router.get("/logout/frontchannel")
async def logout_frontchannel(request: Request, service: str = "", i: int = 0) -> Response:
    """다른 서비스에서 시작한 통합 로그아웃이 이 서비스를 지나갈 때.

    **자기 쿠키만** 지우고 체인의 다음 hop 으로 보낸다. 다음 목적지는 우리 설정의 Auth
    주소로만 만든다(요청이 준 URL 을 쓰지 않는다 — open redirect 차단).
    """
    settings = get_settings()
    web_session.forget(request)
    web_session.logout_session(request)
    nxt = sso.slo_continue_url(settings, service, i) if service else ""
    return RedirectResponse(url=nxt or "/login/screen", status_code=303)


__all__ = ["router"]
