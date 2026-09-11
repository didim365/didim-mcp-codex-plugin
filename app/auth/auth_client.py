"""didim-mcp-auth-backend HTTP client — 신원·role 조회와 SSO login_code 교환.

이 서비스는 사용자 계정을 복제하지 않는다. **role 정본은 Auth 의 `GET /api/v1/me` 응답
`role`** 이며(DB `didim_mcp_auth.users.role`), JWT claim 이 아니다. 따라서 토큰이 유효해도
role 은 매 요청 Auth 에서 확인한다 → 계정을 강등/비활성하면 남은 TTL 과 무관하게 즉시 막힌다.

Microsoft/Azure 와 직접 통신하지 않는다. Auth 가 1회용 `login_code` 를 넘기고 이 서비스는
server-to-server 로 교환만 한다(`POST /api/v1/auth/microsoft/exchange`).

토큰 원문·응답 본문은 로그·예외 메시지에 남기지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import SecretStr

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger("auth.client")

ME_PATH = "/api/v1/me"
SSO_EXCHANGE_PATH = "/api/v1/auth/microsoft/exchange"
REFRESH_PATH = "/api/v1/auth/refresh"  # endpoint 경로(토큰 아님)
LOGOUT_PATH = "/api/v1/auth/logout"

#: Auth `UserStatus.ACTIVE`. 이 값일 때만 화면/관리 API 접근을 허용한다.
ACTIVE_STATUS = "ACTIVE"


class AuthUnavailableError(Exception):
    """Auth 에 닿지 못했다(타임아웃/5xx/스키마 오류). fail-closed → 503 또는 401."""


class AuthRejectedError(Exception):
    """Auth 가 이 자격증명을 거부했다(401/403)."""

    def __init__(self, *, inactive: bool = False) -> None:
        super().__init__("auth rejected the credential")
        self.inactive = inactive


@dataclass(frozen=True)
class AuthUser:
    """Auth `/api/v1/me` 의 안전 필드. 토큰·raw claim 을 담지 않는다."""

    id: str
    email: str | None
    display_name: str | None
    role: str
    status: str

    @property
    def is_active(self) -> bool:
        return self.status == ACTIVE_STATUS


@dataclass(frozen=True)
class AuthTokens:
    access_token: SecretStr
    refresh_token: SecretStr


def _opt_str(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _parse_user(data: dict[str, Any]) -> AuthUser:
    uid = data.get("id")
    role = data.get("role")
    status = data.get("status")
    if not isinstance(uid, str) or not isinstance(role, str) or not isinstance(status, str):
        # 응답 본문은 담지 않는다 — 어떤 필드가 빠졌는지도 굳이 밝히지 않는다.
        raise AuthUnavailableError("unexpected /me payload")
    return AuthUser(
        id=uid,
        email=_opt_str(data.get("email")),
        display_name=_opt_str(data.get("display_name")),
        role=role,
        status=status,
    )


class AuthClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    # ── 신원 / role ───────────────────────────────────────

    async def get_me(
        self, access_token: SecretStr, *, correlation: dict[str, str] | None = None
    ) -> AuthUser:
        """호출자 자신의 신원과 **현재 role** 을 Auth 에서 읽는다."""
        headers = {
            "Authorization": f"Bearer {access_token.get_secret_value()}",
            "Accept": "application/json",
        }
        if correlation:
            headers.update(correlation)
        data = await self._request("GET", self._settings.auth_profile_path, headers=headers)
        return _parse_user(data)

    # ── Microsoft SSO ─────────────────────────────────────

    async def exchange_login_code(self, code: str) -> AuthTokens:
        """1회용 login_code → Access/Refresh Token(server-to-server)."""
        data = await self._request(
            "POST", SSO_EXCHANGE_PATH, json={"code": code}, headers={"Accept": "application/json"}
        )
        return _parse_tokens(data)

    async def refresh(self, refresh_token: SecretStr) -> AuthTokens:
        data = await self._request(
            "POST",
            REFRESH_PATH,
            json={"refresh_token": refresh_token.get_secret_value()},
            headers={"Accept": "application/json"},
        )
        return _parse_tokens(data)

    async def logout(self, refresh_token: SecretStr) -> None:
        """Refresh Token 폐기. 실패해도 예외를 올리지 않는다 — 로컬 정리는 계속돼야 한다."""
        try:
            await self._request(
                "POST",
                LOGOUT_PATH,
                json={"refresh_token": refresh_token.get_secret_value()},
                headers={"Accept": "application/json"},
            )
        except (AuthUnavailableError, AuthRejectedError):
            logger.info("auth logout: revoke failed (continuing with local cleanup)")

    # ── 공통 ──────────────────────────────────────────────

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, object] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        base = (self._settings.auth_base_url or "").rstrip("/")
        if not base:
            raise AuthUnavailableError("auth base url is not configured")
        url = f"{base}{path}"
        try:
            async with httpx.AsyncClient(
                timeout=self._settings.auth_http_timeout_seconds
            ) as client:
                resp = await client.request(method, url, json=json, headers=headers)
        except httpx.HTTPError as exc:
            logger.warning("auth call failed: %s %s (%s)", method, path, type(exc).__name__)
            raise AuthUnavailableError("auth service is unreachable") from exc

        if resp.status_code in (401, 403):
            raise AuthRejectedError(inactive=resp.status_code == 403)
        if resp.status_code >= 400:
            logger.warning("auth call error: %s %s status=%s", method, path, resp.status_code)
            raise AuthUnavailableError("auth service returned an error")
        try:
            body: Any = resp.json()
        except ValueError as exc:
            raise AuthUnavailableError("auth response is not json") from exc
        if not isinstance(body, dict):
            raise AuthUnavailableError("auth response is not an object")
        return body


def _parse_tokens(data: dict[str, Any]) -> AuthTokens:
    access = data.get("access_token")
    refresh = data.get("refresh_token")
    if not isinstance(access, str) or not access:
        raise AuthUnavailableError("token response has no access_token")
    if not isinstance(refresh, str) or not refresh:
        raise AuthUnavailableError("token response has no refresh_token")
    return AuthTokens(access_token=SecretStr(access), refresh_token=SecretStr(refresh))


__all__ = [
    "ACTIVE_STATUS",
    "ME_PATH",
    "SSO_EXCHANGE_PATH",
    "AuthClient",
    "AuthRejectedError",
    "AuthTokens",
    "AuthUnavailableError",
    "AuthUser",
]
