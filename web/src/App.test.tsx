// 앱 shell — 인증 상태와 ADMIN gate.
//
// `globals: false` 다 — `describe`/`it`/`expect`/`vi` 를 import 하고, 자동 cleanup 이
// 없으므로 `afterEach` 에서 `cleanup()` 을 직접 부른다.
// `src/lib/api.ts` 의 me/CSRF 는 **모듈 스코프 캐시**라 케이스마다 비우지 않으면 앞
// 케이스의 로그인 주체가 다음 케이스로 샌다.

import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { resetAuthCache } from "./lib/api";
import type { Me } from "./types/api";

const ADMIN_ME: Me = {
  authenticated: true,
  user_id: "u-1",
  display_name: "관리자",
  email: "admin@example.com",
  role: "ADMIN",
  is_admin: true,
  csrf_token: "csrf-token",
  login_url: "https://auth.example.com/login",
  logout_url: "/logout",
};

const USER_ME: Me = { ...ADMIN_ME, role: "USER", is_admin: false, display_name: "일반 사용자" };

const ANON_ME: Me = {
  authenticated: false,
  user_id: null,
  display_name: null,
  email: null,
  role: null,
  is_admin: false,
  csrf_token: null,
  login_url: "https://auth.example.com/login",
  logout_url: "/logout",
};

function mockApi(me: Me, overrides: Record<string, unknown> = {}) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.startsWith("/api/v1/me")) return jsonResponse(me);
      for (const [prefix, body] of Object.entries(overrides)) {
        if (url.startsWith(prefix)) return jsonResponse(body);
      }
      return jsonResponse({ items: [], meta: { page: 1, page_size: 20, total: 0, total_pages: 1 } });
    }),
  );
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

beforeEach(() => {
  resetAuthCache();
  window.location.hash = "";
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("인증 상태", () => {
  it("미인증이면 로그인 화면을 보여준다", async () => {
    mockApi(ANON_ME);
    render(<App />);
    expect(await screen.findByText("Microsoft 계정으로 로그인")).toBeInTheDocument();
    // 로그인 시작은 backend 경로다 — 화면이 Auth URL 로 직접 보내지 않는다.
    expect(screen.getByText("Microsoft 계정으로 로그인").closest("a")).toHaveAttribute(
      "href",
      "/login",
    );
  });

  it("SSO 가 설정되지 않으면 깨진 링크 대신 안내를 보여준다", async () => {
    mockApi({ ...ANON_ME, login_url: "" });
    render(<App />);
    expect(await screen.findByText(/로그인이 아직 설정되지 않았습니다/)).toBeInTheDocument();
    expect(screen.queryByText("Microsoft 계정으로 로그인")).not.toBeInTheDocument();
  });
});

describe("ADMIN gate", () => {
  it("일반 USER 에게는 권한 없음 화면을 보여준다", async () => {
    mockApi(USER_ME);
    render(<App />);
    expect(await screen.findByText("접근 권한이 없습니다")).toBeInTheDocument();
    // 메뉴도 그리지 않는다(단, 이것은 표시일 뿐 — 차단은 backend 가 한다).
    expect(screen.queryByRole("link", { name: /변경 이력/ })).not.toBeInTheDocument();
  });

  it("ADMIN 에게는 스킬 목록과 메뉴를 보여준다", async () => {
    mockApi(ADMIN_ME);
    render(<App />);
    expect(await screen.findByRole("heading", { name: "스킬" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /변경 이력/ })).toBeInTheDocument();
    expect(screen.getByText("관리자")).toBeInTheDocument();
  });

  it("해시 라우팅으로 변경 이력 화면을 연다", async () => {
    window.location.hash = "#/audit";
    mockApi(ADMIN_ME);
    render(<App />);
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "변경 이력" })).toBeInTheDocument(),
    );
  });
});
