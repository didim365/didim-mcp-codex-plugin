// 스킬 목록 — 표시 · 페이징 · 검색/필터 쿼리 · 오류 상태.

import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { resetAuthCache } from "../lib/api";
import SkillList from "./SkillList";
import type { Page, SkillSummary } from "../types/api";

const ROW: SkillSummary = {
  id: "11111111-1111-1111-1111-111111111111",
  skill_key: "mcp.usage",
  category: "MCP 공통",
  enabled: true,
  published_version: 3,
  published_name: "Didim MCP 도구 사용",
  draft_version: 4,
  updated_at: "2026-09-10T02:30:00Z",
};

function page(items: SkillSummary[], meta: Partial<Page<SkillSummary>["meta"]> = {}) {
  return {
    items,
    meta: { page: 1, page_size: 20, total: items.length, total_pages: 1, ...meta },
  };
}

let calls: string[] = [];

function mockFetch(skills: unknown, status = 200) {
  calls = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      calls.push(url);
      if (url.startsWith("/api/v1/admin/skills/categories"))
        return json(["MCP 공통", "Vault"]);
      return json(skills, status);
    }),
  );
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

beforeEach(() => resetAuthCache());
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("스킬 목록", () => {
  it("배포 버전과 초안을 함께 보여준다", async () => {
    mockFetch(page([ROW]));
    render(<SkillList />);

    expect(await screen.findByText("Didim MCP 도구 사용")).toBeInTheDocument();
    // "배포됨" 은 상태 필터 option 에도 있으므로 표 안으로 범위를 좁힌다.
    const table = within(screen.getByRole("table"));
    expect(table.getByText("mcp.usage")).toBeInTheDocument();
    expect(table.getByText("v3")).toBeInTheDocument();
    // 초안이 있다는 사실이 목록에서 보여야 한다 — 배포와 구분된다.
    expect(table.getByText("초안 v4")).toBeInTheDocument();
    expect(table.getByText("배포됨")).toBeInTheDocument();
    expect(table.getByText("사용")).toBeInTheDocument();
  });

  it("아직 배포 전이면 '미배포' 로 표시한다", async () => {
    mockFetch(page([{ ...ROW, published_version: null, published_name: null }]));
    render(<SkillList />);
    expect(await screen.findByText("미배포")).toBeInTheDocument();
  });

  it("결과가 없으면 빈 상태를 보여준다", async () => {
    mockFetch(page([]));
    render(<SkillList />);
    expect(await screen.findByText("조건에 맞는 스킬이 없습니다.")).toBeInTheDocument();
  });

  it("오류는 화면에 남기고 재시도를 제공한다", async () => {
    mockFetch({ error: { code: "SERVICE_UNAVAILABLE", message: "DB 준비 안 됨" } }, 503);
    render(<SkillList />);
    expect(await screen.findByRole("alert")).toHaveTextContent("DB 준비 안 됨");
    expect(screen.getByRole("button", { name: "다시 시도" })).toBeInTheDocument();
  });

  it("검색어를 쿼리로 넘긴다", async () => {
    mockFetch(page([ROW]));
    render(<SkillList />);
    await screen.findByText("Didim MCP 도구 사용");

    await userEvent.type(screen.getByLabelText("검색"), "vault");
    await userEvent.click(screen.getByRole("button", { name: /찾기/ }));

    await waitFor(() => expect(calls.some((u) => u.includes("search=vault"))).toBe(true));
  });

  it("상태 필터를 쿼리로 넘기고 1페이지로 되돌린다", async () => {
    mockFetch(page([ROW], { total: 40, total_pages: 2 }));
    render(<SkillList />);
    await screen.findByText("Didim MCP 도구 사용");

    await userEvent.selectOptions(screen.getByLabelText("상태"), "DRAFT");
    await waitFor(() =>
      expect(calls.some((u) => u.includes("status=DRAFT") && u.includes("page=1"))).toBe(true),
    );
  });

  it("쪽당 개수를 바꾸면 그 값으로 다시 조회한다", async () => {
    mockFetch(page([ROW], { total: 400, total_pages: 20 }));
    render(<SkillList />);
    await screen.findByText("Didim MCP 도구 사용");

    await userEvent.selectOptions(screen.getByLabelText("쪽당 표시 개수"), "100");
    await waitFor(() => expect(calls.some((u) => u.includes("page_size=100"))).toBe(true));
  });

  it("첫 페이지에서는 '이전' 이 비활성이다", async () => {
    mockFetch(page([ROW], { total: 40, total_pages: 2 }));
    render(<SkillList />);
    await screen.findByText("Didim MCP 도구 사용");
    expect(screen.getByRole("button", { name: "이전" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "다음" })).toBeEnabled();
  });
});
