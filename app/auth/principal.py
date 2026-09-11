"""인증된 호출자 — 이 서비스가 인가 판단에 쓰는 유일한 신원 표현.

두 종류가 같은 타입으로 수렴한다.

- **Admin 호출자**: 브라우저 세션(HttpOnly Access 쿠키) 또는 `Authorization: Bearer <JWT>`.
  role 은 Auth `/api/v1/me` 의 현재 값이다(JWT claim 이 아니다).
- **Runtime 호출자**: MCP gateway 가 위임받은 토큰(`act.sub=mcp`). role 을 보지 않는다 —
  published skill 조회에 관리자 권한이 필요하지 않기 때문이다.

토큰 원문은 담지 않는다(요청 범위에서만 `SecretStr` 로 들고 다니고, 그건 `RequestCredential`
쪽의 일이다).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.enums import UserRole


@dataclass(frozen=True)
class Principal:
    user_id: str
    display_name: str | None
    email: str | None
    role: UserRole
    #: 위임 토큰이면 대리인 식별자(예: `mcp`). 사람 로그인이면 None.
    actor: str | None = None

    @property
    def is_admin(self) -> bool:
        return self.role is UserRole.ADMIN

    @property
    def is_delegated(self) -> bool:
        return self.actor is not None


def parse_role(raw: str) -> UserRole:
    """Auth 의 role 문자열 → enum. 모르는 값은 **최소 권한(USER)** 으로 떨어뜨린다.

    Auth 가 새 role 을 추가했을 때 이 서비스가 그것을 ADMIN 으로 오인하지 않게 하는 것이
    목적이다. 확대 해석하지 않는다.
    """
    try:
        return UserRole(raw)
    except ValueError:
        return UserRole.USER


__all__ = ["Principal", "parse_role"]
