// 스킬 상세 — 편집기 · 배포/롤백 확인 modal · 버전 이력.
//
// 확인 modal 이 **실수 방지 장치**이므로, "누르자마자 배포되지 않는다" 는 것을 고정한다.

import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { resetAuthCache } from "../lib/api";
import SkillDetailPage from "./SkillDetail";
import type { SkillDetail, SkillVersionDetail } from "../types/api";

const SKILL_ID = "11111111-1111-1111-1111-111111111111";

function version(n: number, status: SkillVersionDetail["status"]): SkillVersionDetail {
  return {
    id: `v-${n}`,
    version: n,
    name: `버전 ${n}`,
    status,
    created_by_name: "관리자",
    created_at: "2026-09-01T00:00:00Z",
    published_by_name: status === "DRAFT" ? null : "관리자",
    published_at: status === "DRAFT" ? null : "2026-09-02T00:00:00Z",
    rolled_back_from: null,
    description: `설명 ${n}`,
    instructions: `본문 ${n}`,
    aliases: ["alias-a"],
    tools: ["didim-vault__list_my_resources"],
  };
}

function detail(overrides: Partial<SkillDetail> = {}): SkillDetail {
  const published = version(2, "PUBLISHED");
  const draft = version(3, "DRAFT");
  return {
    id: SKILL_ID,
    skill_key: "mcp.usage",
    category: "MCP 공통",
    enabled: true,
    published_version: 2,
    published_name: published.name,
    draft_version: 3,
    updated_at: "2026-09-03T00:00:00Z",
    versions: [draft, published, version(1, "SUPERSEDED")],
    published,
    draft,
    ...overrides,
  };
}

let posts: { url: string; body: unknown }[] = [];

function mockFetch(body: SkillDetail, status = 200) {
  posts = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (init?.method && init.method !== "GET") {
        posts.push({ url, body: init.body ? JSON.parse(String(init.body)) : null });
      }
      return new Response(JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json" },
      });
    }),
  );
}

beforeEach(() => resetAuthCache());
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("스킬 상세", () => {
  it("배포본과 초안을 구분해 보여준다", async () => {
    mockFetch(detail());
    render(<SkillDetailPage skillId={SKILL_ID} />);

    expect(await screen.findByText("현재 배포본")).toBeInTheDocument();
    expect(screen.getByText("Codex 가 지금 읽는 내용입니다.")).toBeInTheDocument();
    expect(screen.getByText("초안 v3")).toBeInTheDocument();
    expect(
      screen.getByText("편집 중인 내용입니다. 배포하기 전에는 Codex 에 보이지 않습니다."),
    ).toBeInTheDocument();
  });

  it("배포 전에 확인 modal 을 띄운다", async () => {
    mockFetch(detail());
    render(<SkillDetailPage skillId={SKILL_ID} />);
    await screen.findByText("현재 배포본");

    await userEvent.click(screen.getByRole("button", { name: /배포/ }));

    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("이 초안을 배포할까요?")).toBeInTheDocument();
    // 아직 아무것도 보내지 않았다 — 이것이 modal 의 존재 이유다.
    expect(posts).toHaveLength(0);
  });

  it("확인하면 publish 를 호출한다", async () => {
    mockFetch(detail());
    render(<SkillDetailPage skillId={SKILL_ID} />);
    await screen.findByText("현재 배포본");

    await userEvent.click(screen.getByRole("button", { name: /배포/ }));
    const dialog = await screen.findByRole("dialog");
    await userEvent.click(within(dialog).getByRole("button", { name: "배포" }));

    await waitFor(() =>
      expect(posts).toContainEqual({
        url: `/api/v1/admin/skills/${SKILL_ID}/publish`,
        body: { version: 3 },
      }),
    );
  });

  it("취소하면 아무 요청도 보내지 않는다", async () => {
    mockFetch(detail());
    render(<SkillDetailPage skillId={SKILL_ID} />);
    await screen.findByText("현재 배포본");

    await userEvent.click(screen.getByRole("button", { name: /배포/ }));
    const dialog = await screen.findByRole("dialog");
    await userEvent.click(within(dialog).getByRole("button", { name: "취소" }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(posts).toHaveLength(0);
  });

  it("지난 배포에만 롤백 버튼을 준다", async () => {
    mockFetch(detail());
    render(<SkillDetailPage skillId={SKILL_ID} />);
    await screen.findByText("버전 이력");

    const rollbackButtons = screen.getAllByRole("button", { name: /이 버전으로 롤백/ });
    expect(rollbackButtons).toHaveLength(1); // SUPERSEDED 인 v1 하나뿐
  });

  it("롤백 확인 modal 은 이력이 지워지지 않는다고 알린다", async () => {
    mockFetch(detail());
    render(<SkillDetailPage skillId={SKILL_ID} />);
    await screen.findByText("버전 이력");

    await userEvent.click(screen.getByRole("button", { name: /이 버전으로 롤백/ }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText(/기존 이력은 지워지지 않습니다/)).toBeInTheDocument();

    await userEvent.click(within(dialog).getByRole("button", { name: "롤백" }));
    await waitFor(() =>
      expect(posts).toContainEqual({
        url: `/api/v1/admin/skills/${SKILL_ID}/rollback`,
        body: { version: 1 },
      }),
    );
  });

  it("초안이 없으면 초안 만들기를 제공한다", async () => {
    mockFetch(detail({ draft: null, draft_version: null }));
    render(<SkillDetailPage skillId={SKILL_ID} />);
    expect(await screen.findByRole("button", { name: "초안 만들기" })).toBeInTheDocument();
  });

  it("사용 안 함이면 Codex 에 노출되지 않는다고 알린다", async () => {
    mockFetch(detail({ enabled: false }));
    render(<SkillDetailPage skillId={SKILL_ID} />);
    expect(
      await screen.findByText(/배포된 버전이 있어도 Codex 에는 노출되지 않습니다/),
    ).toBeInTheDocument();
  });

  it("403 은 로그인으로 튕기지 않고 화면에 남는다", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(JSON.stringify({ error: { code: "FORBIDDEN", message: "관리자 전용" } }), {
            status: 403,
            headers: { "Content-Type": "application/json" },
          }),
      ),
    );
    render(<SkillDetailPage skillId={SKILL_ID} />);
    expect(await screen.findByText("접근 권한이 없습니다")).toBeInTheDocument();
  });
});
