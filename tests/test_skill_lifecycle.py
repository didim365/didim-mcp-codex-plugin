"""Skill lifecycle — 생성 / 초안 / 버전 증가 / 배포 / 롤백 / 사용 여부.

요구사항 §9 · §34-1,2,3 의 계약을 여기서 고정한다.
"""

from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import new_skill_payload


async def _create(client: AsyncClient, **overrides: object) -> dict:
    resp = await client.post("/api/v1/admin/skills", json=new_skill_payload(**overrides))
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_create_starts_as_draft_not_published(client: AsyncClient) -> None:
    """등록만으로는 배포되지 않는다 — 즉시 노출은 요구사항 §34-2 위반이다."""
    skill = await _create(client, skill_key="lifecycle.create")
    assert skill["published_version"] is None
    assert skill["draft_version"] == 1
    assert skill["draft"]["status"] == "DRAFT"
    assert skill["enabled"] is True


async def test_duplicate_skill_key_conflicts(client: AsyncClient) -> None:
    await _create(client, skill_key="lifecycle.dup")
    resp = await client.post(
        "/api/v1/admin/skills", json=new_skill_payload(skill_key="lifecycle.dup")
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CONFLICT"


async def test_publish_then_edit_creates_v2(client: AsyncClient) -> None:
    skill = await _create(client, skill_key="lifecycle.v2")
    sid = skill["id"]

    published = await client.post(f"/api/v1/admin/skills/{sid}/publish", json={"version": 1})
    assert published.status_code == 200
    assert published.json()["published_version"] == 1
    assert published.json()["draft_version"] is None

    # 내용을 주지 않으면 현재 배포본을 복사해 초안을 시작한다.
    draft = await client.post(f"/api/v1/admin/skills/{sid}/versions")
    assert draft.status_code == 201
    body = draft.json()
    assert body["version"] == 2
    assert body["status"] == "DRAFT"
    assert body["instructions"] == skill["draft"]["instructions"]


async def test_only_one_draft_at_a_time(client: AsyncClient) -> None:
    """두 관리자가 동시에 편집해 서로의 내용을 조용히 덮는 상황을 만들지 않는다."""
    skill = await _create(client, skill_key="lifecycle.onedraft")
    sid = skill["id"]
    resp = await client.post(f"/api/v1/admin/skills/{sid}/versions")
    assert resp.status_code == 409


async def test_published_version_is_immutable(client: AsyncClient) -> None:
    skill = await _create(client, skill_key="lifecycle.immutable")
    sid = skill["id"]
    await client.post(f"/api/v1/admin/skills/{sid}/publish", json={"version": 1})

    resp = await client.put(
        f"/api/v1/admin/skills/{sid}/versions/1",
        json={
            "name": "고쳐보기",
            "description": "",
            "instructions": "바뀐 내용",
            "aliases": [],
            "tools": [],
        },
    )
    assert resp.status_code == 409


async def test_publishing_twice_conflicts(client: AsyncClient) -> None:
    skill = await _create(client, skill_key="lifecycle.twice")
    sid = skill["id"]
    await client.post(f"/api/v1/admin/skills/{sid}/publish", json={"version": 1})
    again = await client.post(f"/api/v1/admin/skills/{sid}/publish", json={"version": 1})
    assert again.status_code == 409


async def test_publish_demotes_previous_to_superseded(client: AsyncClient) -> None:
    skill = await _create(client, skill_key="lifecycle.supersede")
    sid = skill["id"]
    await client.post(f"/api/v1/admin/skills/{sid}/publish", json={"version": 1})
    await client.post(f"/api/v1/admin/skills/{sid}/versions")
    await client.post(f"/api/v1/admin/skills/{sid}/publish", json={"version": 2})

    detail = (await client.get(f"/api/v1/admin/skills/{sid}")).json()
    by_version = {v["version"]: v["status"] for v in detail["versions"]}
    assert by_version == {1: "SUPERSEDED", 2: "PUBLISHED"}
    assert detail["published_version"] == 2
    # PUBLISHED 는 언제나 정확히 하나다.
    assert sum(1 for s in by_version.values() if s == "PUBLISHED") == 1


async def test_rollback_creates_new_version_and_keeps_history(client: AsyncClient) -> None:
    """과거 행을 되살리지 않는다 — 그 내용으로 **새 버전**을 만들어 배포한다(§9)."""
    skill = await _create(client, skill_key="lifecycle.rollback", instructions="원본 v1")
    sid = skill["id"]
    await client.post(f"/api/v1/admin/skills/{sid}/publish", json={"version": 1})

    await client.post(f"/api/v1/admin/skills/{sid}/versions")
    await client.put(
        f"/api/v1/admin/skills/{sid}/versions/2",
        json={
            "name": "두 번째",
            "description": "",
            "instructions": "바뀐 v2",
            "aliases": [],
            "tools": [],
        },
    )
    await client.post(f"/api/v1/admin/skills/{sid}/publish", json={"version": 2})

    rolled = await client.post(f"/api/v1/admin/skills/{sid}/rollback", json={"version": 1})
    assert rolled.status_code == 200
    detail = rolled.json()

    assert detail["published_version"] == 3
    assert detail["published"]["instructions"] == "원본 v1"
    assert detail["published"]["rolled_back_from"] == 1
    # 이력은 하나도 사라지지 않는다.
    assert {v["version"] for v in detail["versions"]} == {1, 2, 3}
    statuses = {v["version"]: v["status"] for v in detail["versions"]}
    assert statuses[1] == "SUPERSEDED"
    assert statuses[2] == "SUPERSEDED"
    assert statuses[3] == "PUBLISHED"


async def test_cannot_rollback_to_current_or_draft(client: AsyncClient) -> None:
    skill = await _create(client, skill_key="lifecycle.badrollback")
    sid = skill["id"]

    to_draft = await client.post(f"/api/v1/admin/skills/{sid}/rollback", json={"version": 1})
    assert to_draft.status_code == 409

    await client.post(f"/api/v1/admin/skills/{sid}/publish", json={"version": 1})
    to_current = await client.post(f"/api/v1/admin/skills/{sid}/rollback", json={"version": 1})
    assert to_current.status_code == 409


async def test_draft_delete_keeps_published_history(client: AsyncClient) -> None:
    skill = await _create(client, skill_key="lifecycle.deldraft")
    sid = skill["id"]
    await client.post(f"/api/v1/admin/skills/{sid}/publish", json={"version": 1})
    await client.post(f"/api/v1/admin/skills/{sid}/versions")

    deleted = await client.delete(f"/api/v1/admin/skills/{sid}/versions/2")
    assert deleted.status_code == 204

    detail = (await client.get(f"/api/v1/admin/skills/{sid}")).json()
    assert detail["draft_version"] is None
    assert detail["published_version"] == 1
    assert {v["version"] for v in detail["versions"]} == {1}


async def test_cannot_delete_published_version(client: AsyncClient) -> None:
    skill = await _create(client, skill_key="lifecycle.delpub")
    sid = skill["id"]
    await client.post(f"/api/v1/admin/skills/{sid}/publish", json={"version": 1})
    resp = await client.delete(f"/api/v1/admin/skills/{sid}/versions/1")
    assert resp.status_code == 409


async def test_enable_disable(client: AsyncClient) -> None:
    skill = await _create(client, skill_key="lifecycle.enable")
    sid = skill["id"]
    off = await client.patch(f"/api/v1/admin/skills/{sid}/enabled", json={"enabled": False})
    assert off.status_code == 200
    assert off.json()["enabled"] is False
    on = await client.patch(f"/api/v1/admin/skills/{sid}/enabled", json={"enabled": True})
    assert on.json()["enabled"] is True


async def test_missing_skill_is_404(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/admin/skills/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
