"""DB 엔진/세션 관리.

DB 미설정이면 engine 을 만들지 않는다(bootstrap 모드). ``/ready`` 가 상태를 보고한다 —
didim-rag-backend / didim-mcp-service-backend 와 같은 규약이다.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger("db")


class Database:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._engine: AsyncEngine | None = None
        self._sessionmaker: async_sessionmaker[AsyncSession] | None = None
        url = settings.database_url
        if url:
            self._engine = create_async_engine(
                url,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=5,
                # ORM 문장은 MetaData(schema=...) 로 이미 완전 수식된다. search_path 는 raw SQL
                # 이 실수로 public 에 닿는 것을 막는 2차 방어다(다른 DIDIM 서비스와 동일).
                connect_args={"server_settings": {"search_path": settings.effective_schema}},
            )
            self._sessionmaker = async_sessionmaker(
                self._engine, expire_on_commit=False, class_=AsyncSession
            )

    @property
    def is_configured(self) -> bool:
        return self._engine is not None

    @property
    def sessionmaker(self) -> async_sessionmaker[AsyncSession]:
        if self._sessionmaker is None:
            raise RuntimeError("database is not configured")
        return self._sessionmaker

    async def check(self) -> tuple[bool, bool]:
        """(연결 성공, schema 존재). 실패해도 예외를 밖으로 내지 않는다."""
        if self._engine is None:
            return False, False
        try:
            async with self._engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                row = await conn.execute(
                    text("SELECT 1 FROM information_schema.schemata WHERE schema_name = :s"),
                    {"s": self._settings.effective_schema},
                )
                return True, row.first() is not None
        except Exception:
            # 연결 문자열/비밀번호가 예외 문자열에 섞일 수 있어 메시지를 그대로 싣지 않는다.
            logger.warning("database check failed (dsn=%s)", self._settings.database_dsn_safe)
            return False, False

    async def dispose(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()


__all__ = ["Database"]
