"""DIDIM Access JWT 검증 — **검증만** 한다. 발급하지 않는다.

서명 정본은 ``didim-mcp-auth-backend`` 의 RS256 이고, 공개키는 JWKS 에서 읽는다. 전환기
HS256 은 ``jwt_legacy_hs256_accepted`` 로만 허용한다(기본 off — 대칭키는 검증키=서명키라
이 서비스가 다른 서비스용 토큰을 만들 수 있게 된다).

audience 규칙(didim-rag-backend 와 같은 판단):

- ``jwt_service_audience`` 가 설정돼 있으면 **그 값 또는 공용 audience** 중 하나면 통과한다.
  MCP gateway 가 위임받아 오는 토큰(`act` 보유)의 `aud` 가 이 서비스 audience 다.
- 미설정이면 공용 audience 만 본다(전환기).

토큰 원문·claim 전체는 로그·예외 메시지에 남기지 않는다. 남기는 것은 오류 코드와 `jti` 뿐이다.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import jwt

from app.auth.jwks import DidimJwksClient, JwksError
from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger("auth.jwt")

AUTH_TYPE_PASSWORD = "password"
AUTH_TYPE_OAUTH = "oauth"


class JwtConfigError(Exception):
    """검증 자체가 불가능한 설정 상태(JWKS 없음, HS256 secret 없음). 503 으로 이어진다."""


class JwtVerificationError(Exception):
    """토큰이 유효하지 않다. ``code`` 만 로그에 남긴다."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class VerifiedJwt:
    """검증된 토큰에서 뽑은 **안전 metadata**. 토큰 원문을 담지 않는다."""

    user_id: uuid.UUID
    auth_type: str
    token_id: str | None
    #: RFC 8693 `act` — 위임 토큰이면 대리인(예: MCP gateway)이 들어 있다.
    actor: str | None

    @property
    def is_oauth(self) -> bool:
        return self.auth_type == AUTH_TYPE_OAUTH

    @property
    def is_delegated(self) -> bool:
        return self.actor is not None


class DidimJwtVerifier:
    def __init__(self, settings: Settings, jwks: DidimJwksClient | None) -> None:
        self._settings = settings
        self._jwks = jwks

    async def verify(self, token: str) -> VerifiedJwt:
        s = self._settings
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            raise JwtVerificationError("MALFORMED_TOKEN") from exc
        alg = header.get("alg")

        if alg == "RS256":
            payload = await self._verify_rs256(token, header.get("kid"))
        elif alg == "HS256":
            payload = self._verify_hs256(token)
        else:
            raise JwtVerificationError("UNSUPPORTED_ALGORITHM")

        if not s.jwt_legacy_hs256_accepted and alg == "HS256":
            raise JwtVerificationError("LEGACY_ALGORITHM_REJECTED")

        raw_sub = payload.get("sub")
        try:
            user_id = uuid.UUID(str(raw_sub))
        except (ValueError, AttributeError, TypeError) as exc:
            raise JwtVerificationError("INVALID_SUBJECT") from exc

        auth_type = payload.get("auth_type")
        if auth_type not in (AUTH_TYPE_PASSWORD, AUTH_TYPE_OAUTH):
            raise JwtVerificationError("INVALID_AUTH_TYPE")

        act = payload.get("act")
        actor = (
            act.get("sub") if isinstance(act, dict) and isinstance(act.get("sub"), str) else None
        )
        jti = payload.get("jti")
        return VerifiedJwt(
            user_id=user_id,
            auth_type=str(auth_type),
            token_id=str(jti) if isinstance(jti, str) else None,
            actor=actor,
        )

    # ── 알고리즘별 서명/claim 검증 ─────────────────────────

    async def _verify_rs256(self, token: str, kid: object) -> dict[str, object]:
        if self._jwks is None:
            raise JwtConfigError("jwks is not configured")
        if not isinstance(kid, str) or not kid:
            raise JwtVerificationError("MISSING_KID")
        try:
            key = await self._jwks.get_key(kid)
        except JwksError as exc:
            # 키를 못 가져오면 "토큰이 나쁘다"가 아니라 "검증할 수 없다"이다(503).
            raise JwtConfigError("jwks unavailable") from exc
        return self._decode(token, key.key, "RS256")

    def _verify_hs256(self, token: str) -> dict[str, object]:
        secret = self._settings.jwt_secret
        if secret is None:
            raise JwtConfigError("hs256 secret is not configured")
        return self._decode(token, secret.get_secret_value(), "HS256")

    def _decode(self, token: str, key: object, algorithm: str) -> dict[str, object]:
        s = self._settings
        audiences = [s.jwt_audience]
        if s.jwt_service_audience:
            audiences.append(s.jwt_service_audience)
        try:
            payload: dict[str, object] = jwt.decode(
                token,
                key,  # type: ignore[arg-type]  # PyJWK.key 는 알고리즘별 key 객체다.
                algorithms=[algorithm],
                issuer=s.jwt_issuer,
                # PyJWT 는 audience 목록 중 **하나라도** 맞으면 통과시킨다.
                audience=audiences,
                options={"require": ["exp", "sub", "iss", "aud"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise JwtVerificationError("TOKEN_EXPIRED") from exc
        except jwt.InvalidAudienceError as exc:
            raise JwtVerificationError("INVALID_AUDIENCE") from exc
        except jwt.InvalidIssuerError as exc:
            raise JwtVerificationError("INVALID_ISSUER") from exc
        except jwt.PyJWTError as exc:
            raise JwtVerificationError("INVALID_TOKEN") from exc
        return payload


__all__ = [
    "AUTH_TYPE_OAUTH",
    "AUTH_TYPE_PASSWORD",
    "DidimJwtVerifier",
    "JwtConfigError",
    "JwtVerificationError",
    "VerifiedJwt",
]
