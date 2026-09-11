"""애플리케이션 설정 — pydantic-settings.

- 모든 환경변수는 prefix ``DIDIM_SKILL_``.
- Secret 은 ``SecretStr`` 로만 다룬다. ``repr``/로그/응답에 원문이 나오지 않는다.
- DB 미설정이면 bootstrap 모드(앱은 뜨고 ``/ready`` 가 상태를 알린다) — 기존 DIDIM 규약과 동일.
- 인증 정본은 ``didim-mcp-auth-backend`` 다. 이 서비스는 JWT 를 **검증만** 하고 발급하지 않으며
  사용자 계정을 복제하지 않는다(role 정본은 Auth ``GET /api/v1/me`` 의 ``role``).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.db.schema import DEFAULT_SCHEMA, validate_schema_name

_PLACEHOLDER_TOKENS = ("__db_", "__host__", "__user__", "__password__", "__name__", "replace_me")

#: Auth 의 SSO 복귀 서비스 식별자(`ENTRA_SSO_ALLOWED_SERVICES` / `ENTRA_SSO_SERVICE_CALLBACKS`
#: 에 등록돼 있어야 한다). URL 이 아니라 식별자다 — 요청이 복귀 URL 을 넘기지 않으므로 open
#: redirect 가 구조적으로 불가능하다. 기존 값: `vault` / `mcp` / `rag`.
SSO_SERVICE_NAME = "skill"


def _is_placeholder(value: str | None) -> bool:
    if value is None:
        return True
    v = value.strip().lower()
    if not v:
        return True
    return any(tok in v for tok in _PLACEHOLDER_TOKENS)


class Settings(BaseSettings):
    """환경변수에서 로드되는 런타임 설정."""

    model_config = SettingsConfigDict(
        env_prefix="DIDIM_SKILL_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── 서비스 ──────────────────────────────────────────────
    app_name: str = "didim-mcp-codex-plugin"
    version: str = "0.3.0"
    env: Literal["local", "dev", "prod"] = "local"
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8080

    # ── PostgreSQL (기존 DIDIM 인스턴스 공유, 전용 schema 만 소유) ──
    db_host: str | None = None
    db_port: int = 5432
    db_user: str | None = None
    db_password: SecretStr | None = None
    db_name: str | None = None
    database_schema: str = DEFAULT_SCHEMA

    # ── 인증 (didim-mcp-auth-backend 발급 JWT 검증 전용) ──────
    # false = 무인증 로컬/부트스트랩. 운영은 반드시 true.
    auth_enabled: bool = False
    # 클러스터 내부 service 주소(server-to-server). /me · login_code 교환 · JWKS.
    auth_base_url: str | None = None
    # 브라우저가 직접 여는 Auth 공개 주소. 비어 있으면 Microsoft 버튼을 그리지 않는다.
    auth_public_base_url: str | None = None
    auth_http_timeout_seconds: float = 5.0
    auth_profile_path: str = "/api/v1/me"

    # --- DIDIM Access JWT 비대칭 검증(RS256/JWKS) ---
    # Auth 만 private key 를 갖는다. 이 서비스는 JWKS 공개키로 **검증만** 한다.
    jwt_rs256_enabled: bool = True
    # 비우면 auth_base_url 기준으로 유도(`{auth_base_url}/.well-known/jwks.json`).
    jwt_jwks_url: str | None = None
    jwt_jwks_cache_ttl_seconds: int = 300
    jwt_jwks_http_timeout_seconds: float = 5.0
    jwt_issuer: str = "didim-vault"
    jwt_audience: str = "didim-services"
    # 이 서비스 전용 audience. Auth 의 `JWT_SERVICE_AUDIENCES` 에 등록된 값과 **글자 단위로**
    # 같아야 한다. MCP gateway 가 위임받아 오는 토큰의 `aud` 가 이 값이다. 비우면 service
    # audience 검증을 생략하고 공용 audience 만 본다(전환기).
    jwt_service_audience: str | None = None
    # 전환기: Auth 가 발급하던 HS256 토큰도 받을지. 대칭키는 검증키=서명키라 기본 off 다.
    jwt_legacy_hs256_accepted: bool = False
    jwt_secret: SecretStr | None = None
    jwt_algorithm: str = "HS256"

    # ── Web 세션(Admin 화면) ─────────────────────────────────
    # 브라우저 세션 쿠키 서명 키. 없으면 화면 로그인을 켤 수 없다(fail-closed).
    session_secret: SecretStr | None = None
    session_ttl_seconds: int = 3600
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    # ── Runtime API ─────────────────────────────────────────
    # runtime(`/api/v1/runtime/**`)은 MCP gateway 가 위임 토큰으로 부른다. 익명 공개 금지.
    # false 로 내리는 것은 로컬 개발 전용이다.
    runtime_auth_required: bool = True

    # ── React SPA ───────────────────────────────────────────
    # 빌드 산출물 디렉터리(컨테이너 기준). 없으면 API 만 서비스한다.
    spa_dir: str = "web/dist"

    # ── 페이징 ──────────────────────────────────────────────
    default_page_size: int = 20
    max_page_size: int = 100

    # ── 파생값 ──────────────────────────────────────────────

    @property
    def db_configured(self) -> bool:
        return not any(
            _is_placeholder(v)
            for v in (
                self.db_host,
                self.db_user,
                self.db_password.get_secret_value() if self.db_password else None,
                self.db_name,
            )
        )

    @property
    def database_url(self) -> str | None:
        """asyncpg DSN. 미설정이면 None(bootstrap 모드)."""
        if not self.db_configured:
            return None
        assert self.db_password is not None
        pw = self.db_password.get_secret_value()
        return (
            f"postgresql+asyncpg://{self.db_user}:{pw}@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def database_dsn_safe(self) -> str:
        """로그용 DSN — 비밀번호를 담지 않는다."""
        if not self.db_configured:
            return "not-configured"
        return f"postgresql://{self.db_user}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def effective_schema(self) -> str:
        return validate_schema_name(self.database_schema)

    @property
    def jwks_url(self) -> str | None:
        if self.jwt_jwks_url:
            return self.jwt_jwks_url
        base = (self.auth_base_url or "").rstrip("/")
        return f"{base}/.well-known/jwks.json" if base else None

    @property
    def jwt_rs256_ready(self) -> bool:
        return self.jwt_rs256_enabled and bool(self.jwks_url)

    @property
    def microsoft_login_url(self) -> str:
        """Admin 화면의 "Microsoft 로그인" 시작 URL. 미설정이면 빈 문자열(버튼 미노출).

        복귀 주소를 query 로 보내지 않는다 — `service=skill` **식별자**만 보내고, 실제 복귀
        URL 은 Auth 서버 설정(`ENTRA_SSO_SERVICE_CALLBACKS`)에서만 온다(open redirect 차단).
        """
        base = (self.auth_public_base_url or "").rstrip("/")
        if not base:
            return ""
        return f"{base}/api/v1/auth/microsoft/login?service={SSO_SERVICE_NAME}"

    @property
    def slo_start_url(self) -> str:
        """통합 로그아웃 시작 URL. 미설정이면 빈 문자열(로컬 로그아웃만)."""
        base = (self.auth_public_base_url or "").rstrip("/")
        return f"{base}/api/v1/auth/slo?service={SSO_SERVICE_NAME}&i=1" if base else ""

    def clamp_page_size(self, value: int | None) -> int:
        if value is None:
            return self.default_page_size
        return max(1, min(value, self.max_page_size))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


__all__ = ["SSO_SERVICE_NAME", "Settings", "get_settings"]
