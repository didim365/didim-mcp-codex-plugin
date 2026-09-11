"""입력 검증 · 감사 기록 · 목록 페이징/검색/필터."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import new_skill_payload

# ── 입력 검증 ─────────────────────────────────────────────


@pytest.mark.parametrize(
    "bad_key",
    # 대문자는 거부가 아니라 **소문자 정규화**다(test_skill_key_is_lowercased).
    ["", "with space", "../traversal", "a", "키한글", "x" * 121],
)
async def test_invalid_skill_key_is_rejected(client: AsyncClient, bad_key: str) -> None:
    resp = await client.post("/api/v1/admin/skills", json=new_skill_payload(skill_key=bad_key))
    assert resp.status_code == 422


async def test_skill_key_is_lowercased(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/admin/skills", json=new_skill_payload(skill_key="Mixed.Case-Key")
    )
    assert resp.status_code == 201
    assert resp.json()["skill_key"] == "mixed.case-key"


async def test_invalid_alias_and_tool_are_rejected(client: AsyncClient) -> None:
    bad_alias = await client.post(
        "/api/v1/admin/skills", json=new_skill_payload(aliases=["안 되는 별칭"])
    )
    assert bad_alias.status_code == 422

    bad_tool = await client.post(
        "/api/v1/admin/skills", json=new_skill_payload(tools=["nope$$tool"])
    )
    assert bad_tool.status_code == 422


async def test_duplicates_in_lists_are_collapsed(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/admin/skills",
        json=new_skill_payload(aliases=["aa", "aa", " aa ", "bb"], tools=["tt", "tt"]),
    )
    assert resp.status_code == 201
    draft = resp.json()["draft"]
    assert draft["aliases"] == ["aa", "bb"]
    assert draft["tools"] == ["tt"]


async def test_control_characters_are_rejected(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/admin/skills", json=new_skill_payload(instructions="본문\x00널")
    )
    assert resp.status_code == 422


async def test_unknown_field_is_rejected(client: AsyncClient) -> None:
    """`extra="forbid"` — 오타난 필드를 조용히 무시하지 않는다."""
    payload = new_skill_payload()
    payload["instrcutions"] = "오타"
    resp = await client.post("/api/v1/admin/skills", json=payload)
    assert resp.status_code == 422


async def test_skill_key_cannot_be_changed(client: AsyncClient) -> None:
    created = await client.post("/api/v1/admin/skills", json=new_skill_payload(skill_key="v.fixed"))
    sid = created.json()["id"]
    resp = await client.patch(f"/api/v1/admin/skills/{sid}", json={"skill_key": "v.other"})
    assert resp.status_code == 422  # PATCH 스키마에 그 필드가 없다.
    assert (await client.get(f"/api/v1/admin/skills/{sid}")).json()["skill_key"] == "v.fixed"


# ── 감사 ──────────────────────────────────────────────────


async def test_audit_records_the_lifecycle(client: AsyncClient) -> None:
    created = await client.post("/api/v1/admin/skills", json=new_skill_payload(skill_key="a.audit"))
    sid = created.json()["id"]
    await client.post(f"/api/v1/admin/skills/{sid}/publish", json={"version": 1})
    await client.post(f"/api/v1/admin/skills/{sid}/versions")
    await client.post(f"/api/v1/admin/skills/{sid}/publish", json={"version": 2})
    await client.post(f"/api/v1/admin/skills/{sid}/rollback", json={"version": 1})
    await client.patch(f"/api/v1/admin/skills/{sid}/enabled", json={"enabled": False})

    logs = (await client.get("/api/v1/admin/audit-logs?page_size=100")).json()["items"]
    ops = [row["operation"] for row in logs]
    assert set(ops) == {
        "SKILL_CREATE",
        "PUBLISH",
        "DRAFT_CREATE",
        "ROLLBACK",
        "SKILL_DISABLE",
    }
    assert all(row["result"] == "SUCCESS" for row in logs)
    assert all(row["actor_display_name"] == "관리자" for row in logs)
    assert all(row["skill_key"] == "a.audit" for row in logs)

    rollback = next(r for r in logs if r["operation"] == "ROLLBACK")
    assert rollback["detail"]["source_version"] == 1
    assert rollback["detail"]["to"] == 3


async def test_audit_detail_never_contains_secrets_or_body(client: AsyncClient) -> None:
    """감사에 토큰·본문을 넣지 않는다(요구사항 §8)."""
    created = await client.post(
        "/api/v1/admin/skills",
        json=new_skill_payload(skill_key="a.nosecret", instructions="비밀스러운 본문"),
    )
    sid = created.json()["id"]
    await client.post(f"/api/v1/admin/skills/{sid}/publish", json={"version": 1})

    logs = (await client.get("/api/v1/admin/audit-logs")).json()["items"]
    blob = repr(logs)
    assert "비밀스러운 본문" not in blob
    for row in logs:
        if row["detail"]:
            keys = {k.lower() for k in row["detail"]}
            assert keys.isdisjoint(
                {"authorization", "access_token", "refresh_token", "token", "instructions"}
            )


async def test_audit_filter_by_operation(client: AsyncClient) -> None:
    created = await client.post(
        "/api/v1/admin/skills", json=new_skill_payload(skill_key="a.filter")
    )
    sid = created.json()["id"]
    await client.post(f"/api/v1/admin/skills/{sid}/publish", json={"version": 1})

    only_publish = (await client.get("/api/v1/admin/audit-logs?operation=PUBLISH")).json()
    assert only_publish["meta"]["total"] == 1
    assert only_publish["items"][0]["operation"] == "PUBLISH"


# ── 목록 페이징 / 검색 / 필터 ─────────────────────────────


async def test_pagination_and_filters(client: AsyncClient) -> None:
    for i in range(7):
        payload = new_skill_payload(
            skill_key=f"page.item-{i:02d}",
            category="짝수" if i % 2 == 0 else "홀수",
            name=f"스킬 {i:02d}",
        )
        created = await client.post("/api/v1/admin/skills", json=payload)
        sid = created.json()["id"]
        if i < 4:
            await client.post(f"/api/v1/admin/skills/{sid}/publish", json={"version": 1})
        if i == 6:
            await client.patch(f"/api/v1/admin/skills/{sid}/enabled", json={"enabled": False})

    first = (await client.get("/api/v1/admin/skills?page=1&page_size=3&sort=skill_key")).json()
    assert len(first["items"]) == 3
    assert first["meta"] == {"page": 1, "page_size": 3, "total": 7, "total_pages": 3}
    assert [i["skill_key"] for i in first["items"]] == [
        "page.item-00",
        "page.item-01",
        "page.item-02",
    ]

    last = (await client.get("/api/v1/admin/skills?page=3&page_size=3&sort=skill_key")).json()
    assert [i["skill_key"] for i in last["items"]] == ["page.item-06"]

    by_category = (await client.get("/api/v1/admin/skills?category=홀수")).json()
    assert by_category["meta"]["total"] == 3

    disabled = (await client.get("/api/v1/admin/skills?enabled=false")).json()
    assert [i["skill_key"] for i in disabled["items"]] == ["page.item-06"]

    published_only = (await client.get("/api/v1/admin/skills?status=PUBLISHED")).json()
    assert published_only["meta"]["total"] == 4

    # 검색은 skill_key 와 배포본 이름 둘 다 본다.
    by_key = (await client.get("/api/v1/admin/skills?search=item-03")).json()
    assert [i["skill_key"] for i in by_key["items"]] == ["page.item-03"]
    by_name = (await client.get("/api/v1/admin/skills?search=스킬 02")).json()
    assert [i["skill_key"] for i in by_name["items"]] == ["page.item-02"]


async def test_page_size_is_clamped(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/admin/skills?page_size=5000")
    assert resp.status_code == 422  # Query(le=100) 가 먼저 막는다.


async def test_categories_endpoint(client: AsyncClient) -> None:
    await client.post("/api/v1/admin/skills", json=new_skill_payload(category="가"))
    await client.post("/api/v1/admin/skills", json=new_skill_payload(category="나"))
    await client.post("/api/v1/admin/skills", json=new_skill_payload(category="가"))
    resp = await client.get("/api/v1/admin/skills/categories")
    assert resp.json() == ["가", "나"]
