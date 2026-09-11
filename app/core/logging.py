"""로깅 — request_id 를 contextvar 로 실어 나른다.

자격증명(JWT · 세션 쿠키 · DB 비밀번호 · actor secret)은 **어떤 경로로도** 로그에 남기지
않는다. 실패는 타입명·오류 코드까지만 남긴다.
"""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id.get() or "-"
        return True


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-5s [%(name)s] (%(request_id)s) %(message)s")
    )
    handler.addFilter(_RequestIdFilter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())


def set_request_id(value: str | None) -> None:
    _request_id.set(value)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"didim_skill.{name}")


__all__ = ["configure_logging", "get_logger", "set_request_id"]
