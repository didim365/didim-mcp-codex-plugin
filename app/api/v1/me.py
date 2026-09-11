"""`/api/v1/me` — 화면 shell 표시 전용.

여기서 주는 `role` / `is_admin` 은 **메뉴를 그릴지** 만 정한다. 인가 판단에 쓰지 않는다 —
차단은 `/api/v1/admin/**` 의 가드가 한다(요구사항 §6).

미인증도 200 으로 답한다(`authenticated: false`). 화면이 401 을 받고 곧바로 로그인으로
튕기는 대신, 로그인 버튼이 있는 화면을 그릴 수 있어야 하기 때문이다.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.deps import SettingsDep
from app.api.dto import MeOut
from app.api.transaction import TransactionalRoute
from app.auth.auth_client import AuthRejectedError, AuthUnavailableError
from app.core.errors import SkillRegistryError
from app.web import session as web_session

router = APIRouter(tags=["me"], route_class=TransactionalRoute)


@router.get("/me", response_model=MeOut, summary="현재 로그인 주체(화면 표시용)")
async def me(request: Request, settings: SettingsDep) -> MeOut:
    from app.api.deps import _authenticate  # 순환 import 회피(런타임 import).

    login_url = settings.microsoft_login_url
    logout_url = "/logout"
    if not settings.auth_enabled:
        # 로컬/부트스트랩: 로그인 개념이 없다. 화면이 그대로 동작하도록 ADMIN 으로 표시한다.
        return MeOut(
            authenticated=True,
            user_id=None,
            display_name="로컬 개발자",
            role="ADMIN",
            is_admin=True,
            csrf_token=web_session.ensure_csrf_token(request),
            login_url=login_url,
            logout_url=logout_url,
        )
    try:
        principal = await _authenticate(request, settings)
    except (SkillRegistryError, AuthRejectedError, AuthUnavailableError):
        return MeOut(authenticated=False, login_url=login_url, logout_url=logout_url)

    return MeOut(
        authenticated=True,
        user_id=principal.user_id,
        display_name=principal.display_name,
        email=principal.email,
        role=principal.role.value,
        is_admin=principal.is_admin,
        csrf_token=web_session.ensure_csrf_token(request),
        login_url=login_url,
        logout_url=logout_url,
    )


__all__ = ["router"]
