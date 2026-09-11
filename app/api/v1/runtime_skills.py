"""Runtime Skill API — Codex / MCP gateway 가 읽는 계약.

**PUBLISHED + enabled 만 나간다.** DRAFT 는 여기서 존재하지 않는 것과 같다 — 필터는
`RuntimeSkillRepository` 의 SQL 에 있고 애플리케이션 후처리로 거르지 않는다(요구사항 §34-4).

Admin API 와 **경로가 분리**돼 있다(`/api/v1/runtime/**`). 그래서 인가 가드를 서로 다르게
붙일 수 있고, edge/nginx 나 방화벽에서 경로 단위로 다르게 다룰 수 있다.

이 API 는 **인가 정본이 아니다.** 응답의 `tools` 는 "이 workflow 가 쓰도록 의도된 Tool" 일
뿐이고, 사용자가 그 Tool 을 실제로 부를 수 있는지는 MCP gateway 가 결정한다(요구사항 §11).

장애 시 동작(요구사항 §14): DB 에 닿지 못하면 `get_session` 이 503 을 낸다. 여기서 빈 목록
이나 오래된 캐시로 위장하지 않는다 — fail-closed 다.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query, Request

from app.api.deps import RuntimeCallerDep, SessionDep, SettingsDep
from app.api.dto import Page, PageMeta, RuntimeSkill, RuntimeSkillSummary
from app.api.mappers import runtime_skill, runtime_summary
from app.api.transaction import TransactionalRoute
from app.core.errors import NotFoundError
from app.domain.validators import SKILL_KEY_RE
from app.repositories.skill import RuntimeSkillRepository

router = APIRouter(prefix="/runtime", tags=["runtime"], route_class=TransactionalRoute)

_SKILL_KEY_PATH = Annotated[str, Path(pattern=SKILL_KEY_RE.pattern, max_length=120)]


@router.get(
    "/skills",
    response_model=Page[RuntimeSkillSummary],
    operation_id="list_skills",
    summary="배포된 Skill 목록",
    description=(
        "현재 **배포(PUBLISHED)되고 사용 중(enabled)인** Skill 만 돌려준다. 초안은 포함되지 "
        "않는다. 본문(`instructions`)은 단건 조회에서만 나온다."
    ),
)
async def list_skills(
    session: SessionDep,
    settings: SettingsDep,
    _: RuntimeCallerDep,
    category: Annotated[str | None, Query(max_length=60)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int | None, Query(ge=1, le=100)] = None,
) -> Page[RuntimeSkillSummary]:
    size = settings.clamp_page_size(page_size)
    rows, total = await RuntimeSkillRepository(session).list_published(
        page=page, page_size=size, category=category
    )
    return Page(
        items=[runtime_summary(v, s) for v, s in rows],
        meta=PageMeta(
            page=page, page_size=size, total=total, total_pages=max(1, -(-total // size))
        ),
    )


@router.get(
    "/skills/{skill_key}",
    response_model=RuntimeSkill,
    operation_id="get_skill",
    summary="배포된 Skill 단건(workflow 본문 포함)",
    description=(
        "`skill_key` 의 **현재 배포본**을 돌려준다. 초안·비활성 Skill 은 404 다 — "
        "'존재하지만 아직 배포되지 않았다'는 사실도 알리지 않는다."
    ),
    responses={404: {"description": "배포된 Skill 이 없거나 사용 중이 아님"}},
)
async def get_skill(
    skill_key: _SKILL_KEY_PATH, session: SessionDep, _: RuntimeCallerDep
) -> RuntimeSkill:
    row = await RuntimeSkillRepository(session).get_published(skill_key)
    if row is None:
        # DRAFT 만 있거나 disabled 인 경우와 아예 없는 경우를 구분하지 않는다(정보 노출 최소화).
        raise NotFoundError(f"배포된 스킬이 없습니다: {skill_key}")
    version, skill = row
    return runtime_skill(version, skill)


@router.get(
    "/openapi.json",
    include_in_schema=False,
    summary="runtime 전용 OpenAPI 문서(MCP gateway 등록용)",
)
async def runtime_openapi(request: Request) -> dict[str, object]:
    """`/api/v1/runtime/**` 만 담은 OpenAPI 문서.

    didim-mcp-service-backend 에 이 서비스를 OpenAPI Provider 로 등록할 때 **이 URL** 을
    쓴다. 전체 `/openapi.json` 을 등록하면 Admin mutation(`publish`·`rollback`·초안 삭제)
    까지 MCP Tool 후보로 올라온다 — 운영자가 실수로 하나를 노출하면 Codex 세션에서 스킬을
    배포할 수 있게 된다. 그래서 등록용 문서를 **읽기 전용 경로로 좁혀서** 따로 낸다.

    문서를 새로 쓰지 않는다. 앱이 이미 만든 스키마에서 runtime 경로만 골라낸다 — 두 벌을
    관리하면 곧 갈라진다.
    """
    schema = request.app.openapi()
    prefix = "/api/v1/runtime/"
    paths = {
        path: item
        for path, item in schema.get("paths", {}).items()
        if path.startswith(prefix) and not path.endswith("/openapi.json")
    }
    return {
        "openapi": schema.get("openapi", "3.1.0"),
        "info": {
            "title": f"{schema['info']['title']} — runtime",
            "version": schema["info"]["version"],
            "description": "배포된 Skill 조회 전용(읽기). Admin API 는 이 문서에 포함되지 않는다.",
        },
        "paths": paths,
        "components": schema.get("components", {}),
    }


__all__ = ["router"]
