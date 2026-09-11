// API 호출의 **유일한 진입점**. 화면이 `fetch` 를 직접 부르지 않는다.
//
// 절대 계약(didim-mcp-service-frontend CLAUDE.md 와 같은 규칙):
// - **토큰을 다루는 코드를 만들지 않는다.** localStorage 저장·Authorization 헤더 조립·
//   refresh 로직 전부 금지다. 인증은 backend 가 심은 HttpOnly 쿠키로 성립한다.
// - **CSRF 헤더를 붙이는 곳은 여기 하나다.** 값은 `GET /api/v1/me` 가 준다.
// - **401 만 로그인으로 보낸다. 403 은 화면에 남긴다.** 403 을 자동 재시도하지 않는다
//   (권한 없는 요청을 두 번 보내게 된다).

import type { Me } from "../types/api";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** 모듈 스코프 캐시 — 탭당 `/api/v1/me` 한 번. 테스트는 `resetAuthCache()` 로 비운다. */
let cachedMe: Me | null = null;
let csrfToken: string | null = null;

export function resetAuthCache(): void {
  cachedMe = null;
  csrfToken = null;
}

const UNSAFE = new Set(["POST", "PUT", "PATCH", "DELETE"]);

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (UNSAFE.has(method) && csrfToken) headers["X-CSRF-Token"] = csrfToken;

  const resp = await fetch(path, {
    method,
    headers,
    credentials: "same-origin",
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (resp.status === 204) return undefined as T;

  let payload: unknown = null;
  try {
    payload = await resp.json();
  } catch {
    payload = null;
  }

  if (!resp.ok) {
    const { code, message } = readError(payload, resp.status);
    if (resp.status === 401) {
      // 세션 만료 — backend 가 다음 목적지를 정한다(자동 SSO 여부는 HttpOnly 쿠키가 근거라
      // 화면이 판단할 수 없다).
      resetAuthCache();
      window.location.href = "/login";
    }
    throw new ApiError(resp.status, code, message);
  }
  return payload as T;
}

function readError(payload: unknown, status: number): { code: string; message: string } {
  if (payload && typeof payload === "object") {
    const err = (payload as { error?: { code?: string; message?: string } }).error;
    if (err?.message) return { code: err.code ?? "ERROR", message: err.message };
    // FastAPI 스키마 검증(422)은 기본 형식이다.
    const detail = (payload as { detail?: unknown }).detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: string; loc?: unknown[] };
      const where = Array.isArray(first.loc) ? first.loc.slice(1).join(".") : "";
      return {
        code: "VALIDATION_FAILED",
        message: where ? `${where}: ${first.msg ?? "입력이 올바르지 않습니다."}` : (first.msg ?? "입력이 올바르지 않습니다."),
      };
    }
    if (typeof detail === "string") return { code: "ERROR", message: detail };
  }
  return { code: "ERROR", message: `요청에 실패했습니다. (HTTP ${status})` };
}

export const api = {
  get: <T,>(path: string) => request<T>("GET", path),
  post: <T,>(path: string, body?: unknown) => request<T>("POST", path, body),
  put: <T,>(path: string, body?: unknown) => request<T>("PUT", path, body),
  patch: <T,>(path: string, body?: unknown) => request<T>("PATCH", path, body),
  del: <T,>(path: string) => request<T>("DELETE", path),
};

/** 현재 로그인 주체. **표시 전용** — 차단은 backend 가 한다. */
export async function fetchMe(force = false): Promise<Me> {
  if (cachedMe && !force) return cachedMe;
  const resp = await fetch("/api/v1/me", {
    headers: { Accept: "application/json" },
    credentials: "same-origin",
  });
  if (!resp.ok) {
    return {
      authenticated: false,
      user_id: null,
      display_name: null,
      email: null,
      role: null,
      is_admin: false,
      csrf_token: null,
      login_url: "",
      logout_url: "/logout",
    };
  }
  const me = (await resp.json()) as Me;
  cachedMe = me;
  csrfToken = me.csrf_token;
  return me;
}

export function currentCsrfToken(): string | null {
  return csrfToken;
}

export function buildQuery(params: Record<string, string | number | boolean | null | undefined>): string {
  const usp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === null || v === undefined || v === "") continue;
    usp.set(k, String(v));
  }
  const q = usp.toString();
  return q ? `?${q}` : "";
}
