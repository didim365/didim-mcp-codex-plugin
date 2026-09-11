"""Admin Skill 관리 API — **ADMIN 전용**.

인가 가드는 개별 endpoint 가 아니라 ``app/api/v1/router.py`` 의
``include_router(..., dependencies=[Depends(require_admin)])`` 에 붙는다. 여기 endpoint 만
읽고 "인증이 없다" 고 판단하지 않는다(didim-mcp-service-backend 와 같은 규약).

각 handler 가 `AdminDep` 를 따로 받는 것은 **행위자(actor)** 가 필요하기 때문이고,
차단 자체는 router-level 가드가 이미 끝냈다.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Response

from app.api.deps import AdminDep, SessionDep, SettingsDep
from app.api.dto import (
    EnabledRequest,
    Page,
    PageMeta,
    PublishRequest,
    RollbackRequest,
    SkillCreateRequest,
    SkillDetail,
    SkillSummary,
    SkillUpdateRequest,
    SkillVersionContent,
    SkillVersionDetail,
    SkillVersionSummary,
)
from app.api.mappers import skill_detail, skill_summary, version_detail, version_summary
from app.api.transaction import TransactionalRoute
from app.domain.enums import SkillVersionStatus
from app.repositories.skill import SkillRepository
from app.services.skill_service import SkillService

router = APIRouter(prefix="/skills", tags=["admin-skills"], route_class=TransactionalRoute)


def _page_meta(page: int, size: int, total: int) -> PageMeta:
    return PageMeta(page=page, page_size=size, total=total, total_pages=max(1, -(-total // size)))


@router.get("", response_model=Page[SkillSummary], summary="Skill 목록")
async def list_skills(
    session: SessionDep,
    settings: SettingsDep,
    _: AdminDep,
    search: Annotated[str | None, Query(max_length=200)] = None,
    category: Annotated[str | None, Query(max_length=60)] = None,
    enabled: bool | None = None,
    status: SkillVersionStatus | None = None,
    sort: Annotated[str, Query(max_length=32)] = "-updated_at",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int | None, Query(ge=1, le=100)] = None,
) -> Page[SkillSummary]:
    size = settings.clamp_page_size(page_size)
    rows, total = await SkillRepository(session).list_page(
        search=search,
        category=category,
        enabled=enabled,
        status=status,
        sort=sort,
        page=page,
        page_size=size,
    )
    return Page(items=[skill_summary(s) for s in rows], meta=_page_meta(page, size, total))


@router.get("/categories", response_model=list[str], summary="카테고리 목록(필터용)")
async def list_categories(session: SessionDep, _: AdminDep) -> list[str]:
    return await SkillRepository(session).categories()


@router.post("", response_model=SkillDetail, status_code=201, summary="Skill 생성(초안 v1)")
async def create_skill(
    body: SkillCreateRequest, session: SessionDep, actor: AdminDep
) -> SkillDetail:
    skill = await SkillService(session).create_skill(body, actor)
    return skill_detail(skill)


@router.get("/{skill_id}", response_model=SkillDetail, summary="Skill 상세")
async def get_skill(skill_id: uuid.UUID, session: SessionDep, _: AdminDep) -> SkillDetail:
    return skill_detail(await SkillService(session).get_or_404(skill_id))


@router.patch("/{skill_id}", response_model=SkillDetail, summary="Skill 정보 수정")
async def update_skill(
    skill_id: uuid.UUID, body: SkillUpdateRequest, session: SessionDep, _: AdminDep
) -> SkillDetail:
    service = SkillService(session)
    await service.update_skill(skill_id, body.category)
    return skill_detail(await service.get_or_404(skill_id))


@router.patch("/{skill_id}/enabled", response_model=SkillDetail, summary="사용 여부 변경")
async def set_enabled(
    skill_id: uuid.UUID, body: EnabledRequest, session: SessionDep, actor: AdminDep
) -> SkillDetail:
    service = SkillService(session)
    await service.set_enabled(skill_id, body.enabled, actor)
    return skill_detail(await service.get_or_404(skill_id))


@router.get("/{skill_id}/versions", response_model=list[SkillVersionSummary], summary="버전 이력")
async def list_versions(
    skill_id: uuid.UUID, session: SessionDep, _: AdminDep
) -> list[SkillVersionSummary]:
    versions = await SkillService(session).list_versions(skill_id)
    return [version_summary(v) for v in versions]


@router.get(
    "/{skill_id}/versions/{version}",
    response_model=SkillVersionDetail,
    summary="버전 상세(본문 포함)",
)
async def get_version(
    skill_id: uuid.UUID, version: int, session: SessionDep, _: AdminDep
) -> SkillVersionDetail:
    from app.core.errors import NotFoundError

    service = SkillService(session)
    await service.get_or_404(skill_id)
    row = await service.versions.get_by_number(skill_id, version)
    if row is None:
        raise NotFoundError(f"버전을 찾을 수 없습니다: v{version}")
    return version_detail(row)


@router.post(
    "/{skill_id}/versions",
    response_model=SkillVersionDetail,
    status_code=201,
    summary="초안 생성(미지정 시 현재 배포본 복사)",
)
async def create_draft(
    skill_id: uuid.UUID,
    session: SessionDep,
    actor: AdminDep,
    body: SkillVersionContent | None = None,
) -> SkillVersionDetail:
    return version_detail(await SkillService(session).create_draft(skill_id, body, actor))


@router.put(
    "/{skill_id}/versions/{version}", response_model=SkillVersionDetail, summary="초안 수정"
)
async def update_draft(
    skill_id: uuid.UUID,
    version: int,
    body: SkillVersionContent,
    session: SessionDep,
    actor: AdminDep,
) -> SkillVersionDetail:
    return version_detail(await SkillService(session).update_draft(skill_id, version, body, actor))


@router.delete("/{skill_id}/versions/{version}", status_code=204, summary="초안 삭제")
async def delete_draft(
    skill_id: uuid.UUID, version: int, session: SessionDep, actor: AdminDep
) -> Response:
    await SkillService(session).delete_draft(skill_id, version, actor)
    return Response(status_code=204)


@router.post("/{skill_id}/publish", response_model=SkillDetail, summary="배포")
async def publish(
    skill_id: uuid.UUID, body: PublishRequest, session: SessionDep, actor: AdminDep
) -> SkillDetail:
    service = SkillService(session)
    await service.publish(skill_id, body.version, actor)
    return skill_detail(await service.get_or_404(skill_id))


@router.post("/{skill_id}/rollback", response_model=SkillDetail, summary="롤백(새 버전으로 재배포)")
async def rollback(
    skill_id: uuid.UUID, body: RollbackRequest, session: SessionDep, actor: AdminDep
) -> SkillDetail:
    service = SkillService(session)
    await service.rollback(skill_id, body.version, actor)
    return skill_detail(await service.get_or_404(skill_id))


__all__ = ["router"]
