"""Auth RS256 서명 공개키(JWKS) 캐시.

private key 는 이 서비스에 **없다** — 검증 전용이다. 키는 TTL 캐시하고, 모르는 `kid` 를
만나면 한 번만 강제 갱신한다(키 회전 대응). 실패해도 예외 메시지에 응답 본문을 담지 않는다.
"""

from __future__ import annotations

import time
from typing import Any

import httpx
from jwt import PyJWK

from app.core.logging import get_logger

logger = get_logger("auth.jwks")


class JwksError(Exception):
    """JWKS 조회/해석 실패. 검증 불가 = fail-closed."""


class DidimJwksClient:
    def __init__(
        self, url: str, *, timeout_seconds: float = 5.0, cache_ttl_seconds: int = 300
    ) -> None:
        self._url = url
        self._timeout = timeout_seconds
        self._ttl = cache_ttl_seconds
        self._keys: dict[str, PyJWK] = {}
        self._fetched_at = 0.0

    async def get_key(self, kid: str) -> PyJWK:
        """`kid` 에 해당하는 공개키. 캐시 미스면 1회 강제 갱신 후 다시 찾는다."""
        if self._fresh() and kid in self._keys:
            return self._keys[kid]
        await self._refresh()
        key = self._keys.get(kid)
        if key is None:
            raise JwksError("signing key not found")
        return key

    def _fresh(self) -> bool:
        return bool(self._keys) and (time.monotonic() - self._fetched_at) < self._ttl

    async def _refresh(self) -> None:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(self._url, headers={"Accept": "application/json"})
            if resp.status_code != 200:
                raise JwksError(f"jwks fetch failed (status={resp.status_code})")
            payload: Any = resp.json()
        except httpx.HTTPError as exc:
            raise JwksError("jwks fetch failed") from exc
        except ValueError as exc:
            raise JwksError("jwks response is not json") from exc

        keys = payload.get("keys") if isinstance(payload, dict) else None
        if not isinstance(keys, list) or not keys:
            raise JwksError("jwks document has no keys")
        parsed: dict[str, PyJWK] = {}
        for entry in keys:
            if not isinstance(entry, dict):
                continue
            kid = entry.get("kid")
            if not isinstance(kid, str) or not kid:
                continue
            try:
                parsed[kid] = PyJWK.from_dict(entry)
            except Exception:
                logger.warning("jwks: unusable key entry (kid=%s)", kid)
        if not parsed:
            raise JwksError("jwks document has no usable key")
        self._keys = parsed
        self._fetched_at = time.monotonic()
        logger.info("jwks refreshed: %d key(s)", len(parsed))


__all__ = ["DidimJwksClient", "JwksError"]
