// API 클라이언트 — CSRF 헤더 · 오류 파싱 · 401/403 분기.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, api, fetchMe, resetAuthCache } from "./api";

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const ME = {
  authenticated: true,
  user_id: "u",
  display_name: "관리자",
  email: null,
  role: "ADMIN",
  is_admin: true,
  csrf_token: "tok-123",
  login_url: "",
  logout_url: "/logout",
};

beforeEach(() => resetAuthCache());
afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("CSRF", () => {
  it("안전 메서드에는 붙이지 않고 변경 메서드에만 붙인다", async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => json(ME));
    vi.stubGlobal("fetch", fetchMock);
    await fetchMe();

    await api.get("/api/v1/admin/skills");
    await api.post("/api/v1/admin/skills", { a: 1 });

    const headersOf = (call: number): Record<string, string> =>
      (fetchMock.mock.calls[call]?.[1]?.headers ?? {}) as Record<string, string>;
    expect(headersOf(1)["X-CSRF-Token"]).toBeUndefined();
    expect(headersOf(2)["X-CSRF-Token"]).toBe("tok-123");
  });

  it("토큰을 localStorage 에 쓰지 않는다", async () => {
    const setItem = vi.spyOn(Storage.prototype, "setItem");
    vi.stubGlobal("fetch", vi.fn(async () => json(ME)));
    await fetchMe();
    expect(setItem).not.toHaveBeenCalled();
  });
});

describe("오류 처리", () => {
  it("도메인 오류 본문을 메시지로 쓴다", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => json({ error: { code: "CONFLICT", message: "이미 배포됨" } }, 409)),
    );
    await expect(api.post("/api/v1/admin/skills/x/publish", {})).rejects.toMatchObject({
      status: 409,
      code: "CONFLICT",
      message: "이미 배포됨",
    });
  });

  it("FastAPI 422 기본 형식도 읽는다", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        json({ detail: [{ loc: ["body", "skill_key"], msg: "형식 오류" }] }, 422),
      ),
    );
    const err = await api.post("/api/v1/admin/skills", {}).catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).message).toContain("skill_key");
  });

  it("403 은 로그인으로 보내지 않는다", async () => {
    const assign = vi.fn();
    vi.stubGlobal("fetch", vi.fn(async () => json({ error: { message: "관리자 전용" } }, 403)));
    Object.defineProperty(window, "location", {
      value: { get href() { return ""; }, set href(v: string) { assign(v); } },
      writable: true,
    });
    await expect(api.get("/api/v1/admin/skills")).rejects.toBeInstanceOf(ApiError);
    expect(assign).not.toHaveBeenCalled();
  });
});

describe("fetchMe", () => {
  it("탭당 한 번만 부르고 캐시한다", async () => {
    const fetchMock = vi.fn(async () => json(ME));
    vi.stubGlobal("fetch", fetchMock);
    await fetchMe();
    await fetchMe();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("실패하면 미인증으로 떨어진다(예외를 던지지 않는다)", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => json({}, 500)));
    const me = await fetchMe();
    expect(me.authenticated).toBe(false);
  });
});
