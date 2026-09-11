"""Admin 감사 조회 — ADMIN 전용(가드는 router-level)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import AdminDep, SessionDep, SettingsDep
from app.api.dto import AuditLogItem, Page, PageMeta
from app.api.mappers import audit_item
from app.api.transaction import TransactionalRoute
from app.domain.enums import AuditOperation, AuditResult
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit-logs", tags=["admin-audit"], route_class=TransactionalRoute)


@router.get("", response_model=Page[AuditLogItem], summary="감사 로그")
async def list_audit_logs(
    session: SessionDep,
    settings: SettingsDep,
    _: AdminDep,
    skill_id: uuid.UUID | None = None,
    operation: AuditOperation | None = None,
    result: AuditResult | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int | None, Query(ge=1, le=100)] = None,
) -> Page[AuditLogItem]:
    size = settings.clamp_page_size(page_size)
    rows, total = await AuditService(session).list_page(
        skill_id=skill_id, operation=operation, result=result, page=page, page_size=size
    )
    return Page(
        items=[audit_item(r) for r in rows],
        meta=PageMeta(
            page=page, page_size=size, total=total, total_pages=max(1, -(-total // size))
        ),
    )


__all__ = ["router"]
