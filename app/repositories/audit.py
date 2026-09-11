"""감사 로그 데이터 접근."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit import AuditLog
from app.domain.enums import AuditOperation, AuditResult


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def add(self, entry: AuditLog) -> None:
        self.session.add(entry)

    async def list_page(
        self,
        *,
        skill_id: uuid.UUID | None,
        operation: AuditOperation | None,
        result: AuditResult | None,
        page: int,
        page_size: int,
    ) -> tuple[Sequence[AuditLog], int]:
        base = self._filtered(skill_id=skill_id, operation=operation, result=result)
        total = (
            await self.session.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        stmt = (
            base.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        return (await self.session.execute(stmt)).scalars().all(), int(total)

    def _filtered(
        self,
        *,
        skill_id: uuid.UUID | None,
        operation: AuditOperation | None,
        result: AuditResult | None,
    ) -> Select[tuple[AuditLog]]:
        stmt = select(AuditLog)
        if skill_id is not None:
            stmt = stmt.where(AuditLog.skill_id == skill_id)
        if operation is not None:
            stmt = stmt.where(AuditLog.operation == operation)
        if result is not None:
            stmt = stmt.where(AuditLog.result == result)
        return stmt


__all__ = ["AuditRepository"]
