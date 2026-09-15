"""seed manifest 계약 — built-in Skill 이 **Admin API 와 같은 규칙**을 통과하는지 고정한다.

seed 는 raw SQL 로 들어가므로 Pydantic·validator 를 거치지 않는다. 그래서 manifest 에
운영자가 화면에서는 저장할 수 없는 값(대문자 alias, 한글 alias, 규격 밖 Tool 이름)을
넣어도 migration 은 조용히 통과하고, 나중에 Admin Web 에서 그 Skill 을 편집하려는 순간
422 로 막힌다. 그 어긋남을 여기서 잡는다.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.domain import validators as v
from app.seed import SeedSkill, load_seed_skills

SEEDS = load_seed_skills()
GW_HOLIDAY_TOOL = "didim-gw__get_my_holiday_info"


def _by_key(key: str) -> SeedSkill:
    return next(s for s in SEEDS if s.skill_key == key)


def test_manifest_contains_every_builtin_skill() -> None:
    assert {s.skill_key for s in SEEDS} == {
        "mcp.usage",
        "vault.resource",
        "molit.apartment-transactions",
        "gw.holiday",
    }


@pytest.mark.parametrize("seed", SEEDS, ids=[s.skill_key for s in SEEDS])
def test_seed_entry_passes_admin_validation_rules(seed: SeedSkill) -> None:
    """화면에서 저장 가능한 값만 seed 에 넣는다(alias 는 소문자 ASCII machine key 다)."""
    assert v.is_valid_skill_key(seed.skill_key), seed.skill_key
    assert seed.name and len(seed.name) <= v.MAX_NAME_LEN
    assert seed.description and len(seed.description) <= v.MAX_DESCRIPTION_LEN
    assert seed.category is None or len(seed.category) <= v.MAX_CATEGORY_LEN
    assert seed.instructions.strip(), f"{seed.skill_key}: 본문 파일이 비어 있다"
    assert len(seed.instructions) <= v.MAX_INSTRUCTIONS_LEN
    assert not v.has_control_chars(seed.instructions)
    assert len(seed.aliases) <= v.MAX_ALIASES
    for alias in seed.aliases:
        assert v.is_valid_alias(alias), f"{seed.skill_key}: 허용되지 않는 alias {alias!r}"
    assert len(seed.tools) <= v.MAX_TOOLS
    for tool in seed.tools:
        assert v.is_valid_tool_name(tool), f"{seed.skill_key}: 허용되지 않는 tool {tool!r}"
    # normalize 를 거쳐도 그대로여야 한다(공백·중복이 manifest 에 남아 있지 않다).
    assert v.normalize_list(seed.aliases) == seed.aliases
    assert v.normalize_list(seed.tools) == seed.tools


def test_gw_holiday_metadata() -> None:
    seed = _by_key("gw.holiday")
    assert seed.category == "GW"
    assert seed.name == "내 연차 현황 조회"
    # Tool 이름은 MCP gateway 계약이다 — 오타 하나로 라우팅이 죽는다.
    assert seed.tools == [GW_HOLIDAY_TOOL]
    assert seed.aliases == ["gw-holiday", "holiday", "annual-leave"]
    # generic router 가 고를 때 보는 것은 name/description/aliases/category 뿐이다.
    for word in ("연차", "휴가", "작년", "올해"):
        assert word in seed.description, word


def test_gw_holiday_body_rules() -> None:
    body = _by_key("gw.holiday").instructions
    flat = " ".join(body.split())  # 본문이 줄바꿈돼 있어도 문장으로 본다
    assert body.count(GW_HOLIDAY_TOOL) >= 2  # 도구 선언 + 흐름에서 최소 한 번씩
    # 다른 Didim Tool 로 우회하지 않는다 — 본문이 부르는 Tool 은 이것 하나뿐이다.
    other_tools = _tool_like_tokens(body) - {GW_HOLIDAY_TOOL}
    assert other_tools == set(), other_tools
    # 연도는 **실제 현재 날짜**로 계산한다 — 절차에 올해를 못 박으면 내년에 조용히 틀린다.
    assert "do not hardcode a current year in this procedure" in flat.lower()
    for phrase in ("현재 연도 - 1", "현재 연도 - 2"):
        assert phrase in flat, phrase
    # 본인만 조회한다는 제약과 인증 오류/데이터 없음 구분이 본문에 있어야 한다.
    assert "다른 사람의 연차는 조회할 수 없습니다" in flat
    assert "never conflate" in flat.lower()


def _tool_like_tokens(body: str) -> set[str]:
    import re

    return set(re.findall(r"`([a-z0-9-]+__[a-z0-9_]+)`", body))


async def test_gw_holiday_seed_survives_admin_api_and_reaches_runtime(client: AsyncClient) -> None:
    """seed 내용 그대로 등록·배포하면 runtime 계약을 만족하는가.

    migration 은 raw SQL 이라 이 경로를 타지 않는다. 하지만 **같은 데이터**가 화면에서도
    통해야 하고, 배포되면 `didim-dynamic-skill` 이 목록에서 고를 수 있어야 한다.
    """
    seed = _by_key("gw.holiday")
    created = await client.post(
        "/api/v1/admin/skills",
        json={
            "skill_key": seed.skill_key,
            "category": seed.category,
            "name": seed.name,
            "description": seed.description,
            "instructions": seed.instructions,
            "aliases": seed.aliases,
            "tools": seed.tools,
        },
    )
    assert created.status_code == 201, created.text
    sid = created.json()["id"]

    # 배포 전에는 runtime 에 없다(DRAFT 는 존재하지 않는 것과 같다).
    assert (await client.get("/api/v1/runtime/skills/gw.holiday")).status_code == 404

    published = await client.post(f"/api/v1/admin/skills/{sid}/publish", json={"version": 1})
    assert published.status_code == 200, published.text

    listed = (await client.get("/api/v1/runtime/skills?page_size=100")).json()["items"]
    entry = next(i for i in listed if i["skill_key"] == "gw.holiday")
    assert entry["name"] == seed.name
    assert entry["category"] == "GW"
    assert entry["aliases"] == sorted(seed.aliases)
    assert "instructions" not in entry  # 목록은 가볍게

    body = (await client.get("/api/v1/runtime/skills/gw.holiday")).json()
    assert body["instructions"] == seed.instructions
    assert body["tools"] == [GW_HOLIDAY_TOOL]
    assert body["version"] == 1
