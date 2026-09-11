"""Runtime 계약 — 요구사항 §10 · §11 · §34-4.

**초안은 Codex 가 볼 수 없다.** 이 파일이 그 invariant 의 정본 테스트다.
"""

from __future__ import annotations

from httpx import AsyncClient, Response

from tests.conftest import new_skill_payload


def _keys(resp: Response) -> set[str]:
    return {i["skill_key"] for i in resp.json()["items"]}


async def _publish(client: AsyncClient, key: str, **overrides: object) -> str:
    created = await client.post(
        "/api/v1/admin/skills", json=new_skill_payload(skill_key=key, **overrides)
    )
    sid = created.json()["id"]
    await client.post(f"/api/v1/admin/skills/{sid}/publish", json={"version": 1})
    return sid


async def test_draft_is_never_visible_in_runtime(client: AsyncClient) -> None:
    created = await client.post(
        "/api/v1/admin/skills", json=new_skill_payload(skill_key="runtime.draft-only")
    )
    assert created.status_code == 201

    listing = await client.get("/api/v1/runtime/skills")
    assert listing.status_code == 200
    assert listing.json()["items"] == []

    single = await client.get("/api/v1/runtime/skills/runtime.draft-only")
    assert single.status_code == 404


async def test_published_skill_is_visible_with_instructions(client: AsyncClient) -> None:
    await _publish(client, "runtime.published", instructions="본문 ABC")

    listing = await client.get("/api/v1/runtime/skills")
    items = listing.json()["items"]
    assert [i["skill_key"] for i in items] == ["runtime.published"]
    # 목록에는 본문을 싣지 않는다.
    assert "instructions" not in items[0]

    single = await client.get("/api/v1/runtime/skills/runtime.published")
    body = single.json()
    assert body["instructions"] == "본문 ABC"
    assert body["version"] == 1
    assert body["aliases"] == ["test-alias"]
    assert body["tools"] == ["didim-vault__list_my_resources"]


async def test_disabled_skill_disappears_from_runtime(client: AsyncClient) -> None:
    sid = await _publish(client, "runtime.disabled")
    await client.patch(f"/api/v1/admin/skills/{sid}/enabled", json={"enabled": False})

    assert (await client.get("/api/v1/runtime/skills")).json()["items"] == []
    assert (await client.get("/api/v1/runtime/skills/runtime.disabled")).status_code == 404

    await client.patch(f"/api/v1/admin/skills/{sid}/enabled", json={"enabled": True})
    assert len((await client.get("/api/v1/runtime/skills")).json()["items"]) == 1


async def test_runtime_never_leaks_internal_fields(client: AsyncClient) -> None:
    """runtime 응답에 내부 UUID·감사 필드가 섞이면 안 된다."""
    await _publish(client, "runtime.fields")
    body = (await client.get("/api/v1/runtime/skills/runtime.fields")).json()
    forbidden = {"id", "created_by", "created_by_name", "published_by", "status", "skill_id"}
    assert forbidden.isdisjoint(body.keys())


async def test_runtime_follows_publish_and_rollback(client: AsyncClient) -> None:
    sid = await _publish(client, "runtime.rollback", instructions="v1 본문")

    await client.post(f"/api/v1/admin/skills/{sid}/versions")
    await client.put(
        f"/api/v1/admin/skills/{sid}/versions/2",
        json={
            "name": "두 번째",
            "description": "",
            "instructions": "v2 본문",
            "aliases": [],
            "tools": [],
        },
    )
    # 배포 전에는 아직 v1 이다.
    assert (await client.get("/api/v1/runtime/skills/runtime.rollback")).json()[
        "instructions"
    ] == "v1 본문"

    await client.post(f"/api/v1/admin/skills/{sid}/publish", json={"version": 2})
    assert (await client.get("/api/v1/runtime/skills/runtime.rollback")).json()[
        "instructions"
    ] == "v2 본문"

    await client.post(f"/api/v1/admin/skills/{sid}/rollback", json={"version": 1})
    after = (await client.get("/api/v1/runtime/skills/runtime.rollback")).json()
    assert after["instructions"] == "v1 본문"
    assert after["version"] == 3  # 새 버전으로 되돌린다(과거 행 미변형).


async def test_invalid_skill_key_is_rejected_by_path_pattern(client: AsyncClient) -> None:
    """`skill_key` 는 machine identifier 다 — 경로 traversal 형태를 라우팅에서 막는다."""
    for bad in ["../etc/passwd", "UPPER", "with space"]:
        resp = await client.get(f"/api/v1/runtime/skills/{bad}")
        assert resp.status_code in (404, 422), bad


async def test_tool_list_is_orchestration_not_permission(client: AsyncClient) -> None:
    """요구사항 §11 — DB 의 tool 목록은 권한이 아니다.

    Registry 는 임의 Tool 이름을 저장할 수 있고 runtime 이 그대로 돌려주지만, 그것으로
    사용자가 그 Tool 을 부를 수 있게 되지 않는다. 인가는 MCP gateway 가 강제한다.
    이 테스트는 **Registry 가 인가 판단을 내리지 않는다**(저장/반환만 한다)는 사실을 고정해
    둔다 — 나중에 여기서 권한 검사를 흉내 내려는 변경을 잡기 위한 것이다.
    """
    await _publish(client, "runtime.tools", tools=["some_admin_delete_tool"])
    body = (await client.get("/api/v1/runtime/skills/runtime.tools")).json()
    assert body["tools"] == ["some_admin_delete_tool"]
    # 응답 어디에도 "허용됨/권한" 같은 판정 필드가 없다 — 판정 주체가 아니기 때문이다.
    assert not any(k in body for k in ("allowed", "permitted", "authorized"))


async def test_runtime_openapi_excludes_admin_paths(client: AsyncClient) -> None:
    """MCP gateway 에 등록할 문서에는 Admin mutation 이 들어가면 안 된다.

    전체 `/openapi.json` 을 등록하면 운영자가 실수로 `publish` 를 Tool 로 노출할 수 있고,
    그 순간 Codex 세션에서 스킬 배포가 가능해진다. 등록용 문서를 좁혀 두는 이유다.
    """
    doc = (await client.get("/api/v1/runtime/openapi.json")).json()
    paths = set(doc["paths"])
    assert paths == {"/api/v1/runtime/skills", "/api/v1/runtime/skills/{skill_key}"}
    assert not any("admin" in p for p in paths)

    ops = {
        method_item["operationId"]
        for item in doc["paths"].values()
        for method_item in item.values()
    }
    # Tool 이름은 `<provider_slug>__<operationId>` 로 조립된다 — thin router SKILL.md 가
    # 참조하는 `didim-skill__get_skill` / `didim-skill__list_skills` 와 맞아야 한다.
    assert ops == {"get_skill", "list_skills"}


async def test_runtime_openapi_is_read_only(client: AsyncClient) -> None:
    """등록용 문서에 **GET 말고 다른 method 가 없다.**

    `operationId` 만 고정해 두면, 같은 경로에 나중에 POST/DELETE 를 붙였을 때 그것이
    조용히 MCP Tool 후보가 된다. method 까지 고정한다.
    """
    doc = (await client.get("/api/v1/runtime/openapi.json")).json()
    methods = {m for item in doc["paths"].values() for m in item}
    assert methods == {"get"}


def test_skill_md_tool_names_match_runtime_operation_ids() -> None:
    """Plugin 의 thin router 가 부르는 Tool 이름과 runtime operationId 를 맞물려 고정한다.

    Tool 이름은 MCP gateway 가 `<provider_slug>__<operationId>` 로 조립한다. FastAPI
    함수 이름을 바꾸거나 파일을 옮겼을 때 `operation_id=` 를 같이 안 고치면 설치된
    플러그인이 존재하지 않는 Tool 을 부르게 된다 — 그 순간 모든 라우터가 죽는다.
    소스 양쪽을 직접 읽어 대조한다(런타임 앱을 띄우지 않는다).
    """
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]

    declared = set(
        re.findall(r'operation_id="([^"]+)"', (root / "app/api/v1/runtime_skills.py").read_text())
    )
    assert declared == {"get_skill", "list_skills"}

    referenced: set[str] = set()
    routers = 0
    for md in sorted((root / "plugins/didim-mcp/skills").glob("*/SKILL.md")):
        found = set(re.findall(r"didim-skill__([a-z_]+)", md.read_text()))
        if found:
            routers += 1
        referenced |= found

    # 라우터가 참조하는 Tool 은 전부 실제 operation 이어야 한다(반대 방향은 강제하지 않는다
    # — 라우터가 list_skills 를 안 쓸 수도 있다).
    assert referenced <= declared, (
        f"SKILL.md references unknown operations: {referenced - declared}"
    )
    # 정적 Skill 은 didim-mcp-connect 하나뿐이다. 나머지는 전부 Registry 를 참조한다.
    assert routers == len(list((root / "plugins/didim-mcp/skills").glob("*/SKILL.md"))) - 1


async def test_new_skill_is_discoverable_without_plugin_release(client: AsyncClient) -> None:
    """요구사항의 핵심: seed 에 없던 **완전히 새로운** Skill 의 전체 수명주기.

    Plugin source 를 건드리지 않고 Admin API 만으로 등록 → 배포 → runtime 노출 →
    비활성 → 재활성 → 롤백까지 간다. generic fallback router(`didim-dynamic-skill`)가
    실제로 기대는 계약이 이것이다 — **목록에 나타나면 발견된다.**
    """
    key = "test.dynamic-skill"

    # 1. 등록 → 초안. runtime 에 없다.
    created = (
        await client.post(
            "/api/v1/admin/skills",
            json=new_skill_payload(
                skill_key=key,
                name="동적 발견 테스트",
                description="플러그인 릴리스 없이 발견되는지 확인하는 스킬",
                category="테스트",
                aliases=["dynamic-test"],
                instructions="# v1\n1. 첫 번째 절차\n",
            ),
        )
    ).json()
    sid = created["id"]
    assert (await client.get(f"/api/v1/runtime/skills/{key}")).status_code == 404
    assert key not in _keys(await client.get("/api/v1/runtime/skills?page_size=100"))

    # 2. 배포 → 목록과 단건 양쪽에 나타난다. 선택에 필요한 필드가 다 있다.
    assert (
        await client.post(f"/api/v1/admin/skills/{sid}/publish", json={"version": 1})
    ).status_code == 200
    listed = (await client.get("/api/v1/runtime/skills?page_size=100")).json()["items"]
    entry = next(i for i in listed if i["skill_key"] == key)
    # generic router 는 이 네 필드만 보고 고른다. 하나라도 비면 고를 수 없다.
    assert entry["name"] and entry["description"] and entry["category"]
    assert entry["aliases"] == ["dynamic-test"]
    assert "instructions" not in entry  # 목록은 가볍게

    body = (await client.get(f"/api/v1/runtime/skills/{key}")).json()
    assert body["instructions"] == "# v1\n1. 첫 번째 절차\n"

    # 3. 비활성 → 사라진다. 재활성 → 돌아온다.
    await client.patch(f"/api/v1/admin/skills/{sid}/enabled", json={"enabled": False})
    assert key not in _keys(await client.get("/api/v1/runtime/skills?page_size=100"))
    assert (await client.get(f"/api/v1/runtime/skills/{key}")).status_code == 404
    await client.patch(f"/api/v1/admin/skills/{sid}/enabled", json={"enabled": True})
    assert key in _keys(await client.get("/api/v1/runtime/skills?page_size=100"))

    # 4. v2 초안은 runtime 을 바꾸지 않는다. 배포해야 바뀐다.
    drafted = await client.post(
        f"/api/v1/admin/skills/{sid}/versions",
        json={"name": "동적 발견 테스트", "instructions": "# v2\n1. 바뀐 절차\n"},
    )
    assert drafted.status_code == 201, drafted.text
    assert (await client.get(f"/api/v1/runtime/skills/{key}")).json()["version"] == 1
    published = await client.post(f"/api/v1/admin/skills/{sid}/publish", json={"version": 2})
    assert published.status_code == 200, published.text
    assert (await client.get(f"/api/v1/runtime/skills/{key}")).json()[
        "instructions"
    ] == "# v2\n1. 바뀐 절차\n"

    # 5. 롤백 → 새 버전으로 과거 내용이 다시 배포된다(과거 행을 되살리지 않는다).
    rolled = await client.post(f"/api/v1/admin/skills/{sid}/rollback", json={"version": 1})
    assert rolled.status_code == 200, rolled.text
    after = (await client.get(f"/api/v1/runtime/skills/{key}")).json()
    assert after["version"] == 3
    assert after["instructions"] == "# v1\n1. 첫 번째 절차\n"


def test_every_api_route_commits_before_responding() -> None:
    """`/api/v1/**` 의 모든 route 가 `TransactionalRoute` 여야 한다.

    FastAPI 의 `yield` 의존성 teardown 은 **응답을 보낸 뒤** 실행된다. 거기서 commit 하면
    클라이언트가 201 을 받은 시점에 아직 커밋 전이라, 화면이 곧바로 다시 읽으면 없다
    (실측: 201 직후 `GET /admin/skills/{id}` → 404, 약 30ms 뒤 200).

    부모 라우터의 `route_class` 는 `include_router` 로 넣은 자식에게 **내려가지 않는다.**
    그래서 endpoint 를 선언하는 라우터 파일마다 직접 지정해야 하고, 새 라우터 파일을
    추가하면서 빠뜨리기 쉽다. 이 테스트가 그걸 잡는다.

    단위 테스트로 경합 자체는 재현할 수 없다 — httpx `ASGITransport` 는 exit stack 까지
    끝난 뒤에 응답을 돌려주기 때문이다. 그래서 **구조**를 고정한다.
    """
    from fastapi.routing import APIRoute

    from app.api.transaction import TransactionalRoute
    from app.api.v1 import admin_audit, admin_skills, me, runtime_skills

    for module in (admin_skills, admin_audit, runtime_skills, me):
        routes = [r for r in module.router.routes if isinstance(r, APIRoute)]
        assert routes, f"{module.__name__} 에 route 가 없다"
        bad = [r.path for r in routes if not isinstance(r, TransactionalRoute)]
        assert not bad, f"{module.__name__}: route_class=TransactionalRoute 누락 {bad}"
