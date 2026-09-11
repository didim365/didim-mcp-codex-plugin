// 아주 작은 hash 라우터. 라우팅 라이브러리를 새로 들이지 않는다 — 화면이 6개뿐이고
// backend 가 `/login`·`/logout` 같은 자기 경로를 소유하므로, hash 로 두면 SPA fallback 과
// backend 경로가 절대 충돌하지 않는다.

import { useEffect, useState } from "react";

export type Route =
  | { name: "list" }
  | { name: "detail"; id: string }
  | { name: "new" }
  | { name: "audit" };

export function parseHash(hash: string): Route {
  const raw = hash.replace(/^#\/?/, "");
  const [head, tail] = raw.split("/", 2);
  if (head === "skills" && tail) return { name: "detail", id: tail };
  if (head === "new") return { name: "new" };
  if (head === "audit") return { name: "audit" };
  return { name: "list" };
}

export function useRoute(): Route {
  const [route, setRoute] = useState<Route>(() => parseHash(window.location.hash));
  useEffect(() => {
    const onChange = () => setRoute(parseHash(window.location.hash));
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}

export function navigate(to: string): void {
  window.location.hash = to;
}
