"""SKILL.md 계약 — **Runtime Skill 은 optional recipe 이고 Tool 가용성을 결정하지 않는다.**

이 파일들은 문서가 아니라 런타임 동작이다. Codex 가 읽고 그대로 수행하므로, 문구 하나가
곧 동작이다. 실제로 한 번 깨졌다: Registry 에 `gw.holiday` 가 없다는 이유로
`didim-gw__get_my_holiday_info` 가 노출돼 있는데도 "연차 조회 절차가 Skill Registry 에
등록되어 있지 않아 조회할 수 없습니다" 라고 답했다.

```
Skill = how to use tools   (optional recipe / workflow overlay)
Tool  = what can be executed
```

자동 테스트가 프롬프트의 의미까지 검증할 수는 없다. 그래서 **재발 원인이었던 문구가
남아 있지 않은지**와 **대체 정책이 실제로 적혀 있는지**를 정적으로 고정한다. 요구사항
§20 의 15개 시나리오 중 markdown 계약으로 고정 가능한 것이 여기 있고, runtime API 쪽
계약은 `tests/test_runtime_contract.py` 가 담당한다.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

SKILLS_DIR = Path(__file__).resolve().parents[1] / "plugins/didim-mcp/skills"
ROUTERS = ("didim-mcp-usage", "didim-vault", "molit-apartment-transactions")
DYNAMIC = "didim-dynamic-skill"


def _body(skill: str) -> str:
    """SKILL.md 본문을 공백 정규화해서 돌려준다(줄바꿈 때문에 문장이 끊기지 않게)."""
    return " ".join((SKILLS_DIR / skill / "SKILL.md").read_text(encoding="utf-8").split())


def _all_skills() -> list[str]:
    return sorted(p.parent.name for p in SKILLS_DIR.glob("*/SKILL.md"))


# ── 1. 재발 방지: "Skill 없음 → 중단" 문구가 남아 있으면 안 된다 ──────────

#: 회귀 패턴. Registry 쪽 부재/오류를 **요청 중단**으로 잇는 문장들이다.
_STOP_ON_NO_RECIPE = (
    r"no published procedure for this request, and stop",
    r"this skill stops rather than improvising",
    r"nothing to fall back on",
    r"the Didim procedure list is unavailable right now and stop",
    r"say the workflow is not available right now and stop",
    r"say the workflow is\s+unavailable and stop",
    r"say the Vault workflow\s+is unavailable and stop",
)


@pytest.mark.parametrize("pattern", _STOP_ON_NO_RECIPE)
def test_no_skill_match_never_means_stop(pattern: str) -> None:
    """recipe 부재를 실행 중단으로 잇던 문구가 저장소 어디에도 남아 있지 않다."""
    hits = [s for s in _all_skills() if re.search(pattern, _body(s), re.IGNORECASE)]
    assert hits == [], f"{hits}: 'Skill 없음 → 중단' 문구가 남아 있다 ({pattern})"


def test_dynamic_router_no_match_routes_to_tool_fallback() -> None:
    """§5 — no-match 는 Step 3b(일반 Tool 모드)로 간다. 거기서 멈추지 않는다."""
    body = _body(DYNAMIC)
    assert "**No match** → go to **Step 3b**" in body
    assert "Do not stop, and do not invent a Didim procedure" in body


def test_dynamic_router_defines_skill_versus_tool() -> None:
    """§2 — 개념 계약이 본문에 명시돼 있어야 Codex 가 그렇게 행동한다."""
    body = _body(DYNAMIC)
    assert "Skill = how to use tools. Tool = what can be executed." in body
    assert "A missing runtime skill is **not** an execution failure" in body


def test_dynamic_router_has_tool_fallback_procedure() -> None:
    """§6 — fallback 절차가 실제로 적혀 있다(있다고 말만 하는 것이 아니라)."""
    body = _body(DYNAMIC)
    assert "## Step 3b — no matching runtime skill: use the tools directly" in body
    for phrase in (
        "Do not invent a Didim skill, workflow, or procedure",
        "Look at the Didim MCP tools actually exposed to this session",
        "exact name, description, and input schema",
        "Never add an argument the schema does not define",
        "Only when **no exposed tool fits** do you report that the capability is unavailable",
    ):
        assert phrase in body, phrase


@pytest.mark.parametrize("skill", [DYNAMIC, "didim-mcp-usage"])
def test_tool_absence_is_the_only_stop_condition(skill: str) -> None:
    """§4·§26-5 — capability unavailable 의 유일한 근거는 Tool 부재다."""
    assert "the missing tool is the only reason to stop" in _body(skill), skill


def test_curated_recipe_wins_when_a_skill_matches() -> None:
    """§7 — match 가 있으면 recipe 우선. generic fallback 이 recipe 를 밀어내지 않는다."""
    body = _body(DYNAMIC)
    assert "A curated recipe always beats improvising" in body
    assert "do not skip it in favour of picking tools yourself" in body


def test_registry_failures_do_not_disable_tools() -> None:
    """§11·§12 — 빈 목록 / 5xx / timeout / 401·403 각각의 처리가 적혀 있다."""
    body = _body(DYNAMIC)
    assert "Fail closed **on the procedure, not on the tools.**" in body
    assert "errors (5xx), times out, or the list comes back empty" in body
    assert "An empty catalogue is a normal state" in body
    # Registry 만의 401/403 을 세션 전체 인증 실패로 오해하지 않는다.
    assert "returns 401/403 while other Didim tools work" in body
    assert "If **every** Didim tool returns 401/403" in body


def test_fallback_does_not_relax_safety_rules() -> None:
    """§13 — Skill 부재가 hallucination·정책 우회의 허가증이 되면 안 된다."""
    body = _body(DYNAMIC)
    assert "Everything in Step 4 still applies. A missing recipe relaxes nothing." in body
    assert (
        "Never work around a failing registry by bypassing credentials, guessing at tools "
        "that are not exposed, or relaxing any rule in Step 4." in body
    )
    # Step 4 invariant 자체가 그대로 남아 있어야 한다.
    for phrase in (
        "Use only Didim MCP tools that are exposed to the user in the current session",
        "obtain explicit user approval",
        "Never expose the raw value of a token",
        "Tool authorization is decided by the Didim MCP server",
    ):
        assert phrase in body, phrase


def test_skill_listed_tool_is_not_proof_of_availability() -> None:
    """§14 — Skill catalog ≠ Tool availability catalog. 다른 이름으로 대체하지 않는다."""
    body = _body(DYNAMIC)
    assert "never substitute a differently named tool for the one a recipe asked for" in body
    assert "**A `tools` list in a registry entry is not permission to call those tools.**" in body


@pytest.mark.parametrize("skill", ROUTERS)
def test_thin_routers_fall_back_instead_of_stopping(skill: str) -> None:
    """§15 — 전용 router 도 recipe 를 못 읽었다고 Tool 사용을 막지 않는다."""
    body = _body(skill)
    assert "Fail closed **on the procedure, not on the tools.**" in body
    assert "curated" in body and "could not be loaded" in body
    # 안전 invariant 는 그대로 남아 있어야 한다(회귀 방지).
    assert "exposed" in body


@pytest.mark.parametrize("skill", (*ROUTERS, DYNAMIC))
def test_auth_problems_stay_with_didim_mcp_connect(skill: str) -> None:
    """§16 — fallback 을 넣었다고 인증 처리를 여기로 끌어오지 않는다.

    router 는 인증 문제를 **위임만** 한다. 로그인·재로그인·계정 전환·토큰 갱신 절차를
    직접 적으면 안 된다(그 정본은 `didim-mcp-connect` 하나다).
    """
    body = _body(skill)
    assert "didim-mcp-connect" in body, f"{skill}: 인증 위임 대상이 없다"
    for forbidden in (
        "Microsoft 계정으로 다시 로그인하려면",
        "codex mcp login",
        "codex mcp logout",
        "reinstall the plugin",
    ):
        assert forbidden not in body, (skill, forbidden)


def test_molit_keeps_the_rules_that_must_not_be_guessed() -> None:
    """§20-8 — MOLIT 회귀: fallback 이 법정동코드 기억 생성을 허용하면 안 된다."""
    body = _body("molit-apartment-transactions")
    assert (
        "the legal-dong code comes from `odcloud__get_legal_dong_codes` and never from memory"
        in body
    )
    assert "Never use an abolished (폐지) code" in body
    assert "Do not hardcode a year" in body


def test_vault_keeps_its_approval_and_secret_rules() -> None:
    """§20-9 — Vault 회귀: fallback 에서도 승인 게이트와 secret 규칙이 살아 있다."""
    body = _body("didim-vault")
    assert "**Every invariant above still holds**" in body
    assert (
        "approval before execution or reveal, no credential in the reply, no guessed tool name"
        in body
    )


def test_usage_router_keeps_its_invariants() -> None:
    """§20-10 — mcp.usage 회귀: 7개 invariant 가 그대로 있다."""
    body = _body("didim-mcp-usage")
    assert "These are safety rules, not workflow. The registry cannot relax them." in body
    assert body.count("Didim MCP tools that are exposed") >= 1
    assert "Prefer read-only lookup and inspection operations." in body


def test_fallback_policy_is_generic_not_gw_specific() -> None:
    """§22 — 연차 전용 special case 가 아니라 일반 정책이어야 한다.

    `didim-gw__get_my_holiday_info` 는 **worked example 로만** 등장할 수 있다. 정책
    문장(3b 의 1~7번)에는 특정 Tool 이름이 없어야 다른 새 Tool 에도 그대로 적용된다.
    """
    raw = (SKILLS_DIR / DYNAMIC / "SKILL.md").read_text(encoding="utf-8")
    step3b = raw.split("## Step 3b")[1].split("Worked example")[0]
    assert "didim-gw__" not in step3b, "fallback 정책 본문이 특정 Tool 에 묶여 있다"
    assert "gw.holiday" not in step3b
    # 예시는 예시 문단에만 있다.
    assert "didim-gw__get_my_holiday_info" in raw.split("Worked example")[1]


def test_docs_state_the_skill_versus_tool_contract() -> None:
    """§18 — 사용자·운영자 문서에도 같은 계약이 적혀 있어야 한다."""
    root = Path(__file__).resolve().parents[1]
    plugin_readme = (root / "plugins/didim-mcp/README.md").read_text(encoding="utf-8")
    assert "Skills are optional recipes, not the capability itself" in plugin_readme
    assert "Skill = how to use tools" in plugin_readme

    readme = (root / "README.md").read_text(encoding="utf-8")
    assert "Skill은 선택적 recipe입니다" in readme
    assert "Skill = how to use tools" in readme

    rules = (root / ".claude/rules/skills.md").read_text(encoding="utf-8")
    assert "Skill 은 optional recipe 다" in rules
