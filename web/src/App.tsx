// 앱 shell — 인증 상태 판정 + 화면 전환.
//
// **frontend 는 authorization boundary 가 아니다.** `is_admin` 은 메뉴와 안내 문구를
// 그릴지만 정한다. 실제 차단은 backend 가 한다 — 여기서 감추는 것으로 끝내지 않는다.

import { ClipboardList, LogOut, Wrench } from "lucide-react";
import { useEffect, useState } from "react";

import { Button, Forbidden, Loading } from "./components/ui";
import { currentCsrfToken, fetchMe } from "./lib/api";
import { useRoute } from "./lib/router";
import AuditLog from "./pages/AuditLog";
import SkillDetailPage from "./pages/SkillDetail";
import SkillList from "./pages/SkillList";
import SkillNew from "./pages/SkillNew";
import type { Me } from "./types/api";

export default function App() {
  const route = useRoute();
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMe()
      .then(setMe)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loading label="확인 중입니다…" />;

  if (!me?.authenticated) return <LoginScreen me={me} />;
  if (!me.is_admin) {
    return (
      <Shell me={me} route={route}>
        <Forbidden />
      </Shell>
    );
  }

  return (
    <Shell me={me} route={route}>
      {route.name === "list" ? <SkillList /> : null}
      {route.name === "new" ? <SkillNew /> : null}
      {route.name === "detail" ? <SkillDetailPage skillId={route.id} /> : null}
      {route.name === "audit" ? <AuditLog /> : null}
    </Shell>
  );
}

function LoginScreen({ me }: { me: Me | null }) {
  // Microsoft 로그인 시작은 **backend 경로**(`/login`)로 넘긴다. 자동 SSO 를 걸지 로그인
  // 화면을 보일지는 HttpOnly 쿠키가 근거라 화면이 판단할 수 없다.
  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-sm rounded-lg border border-slate-300 bg-white p-8 text-center">
        <h1 className="text-lg font-semibold text-slate-900">Didim Skill Registry</h1>
        <p className="mt-2 text-sm text-slate-600">
          회사 Microsoft 계정으로 로그인하세요. 별도 아이디·비밀번호는 없습니다.
        </p>
        {me?.login_url ? (
          <a
            href="/login"
            className="mt-6 inline-flex w-full items-center justify-center rounded-md border border-sky-700 bg-sky-700 px-4 py-2 text-sm font-medium text-white hover:bg-sky-800"
          >
            Microsoft 계정으로 로그인
          </a>
        ) : (
          <p className="mt-6 rounded-md border border-slate-300 bg-slate-50 px-3 py-2 text-xs text-slate-600">
            로그인이 아직 설정되지 않았습니다. 관리자에게 문의하세요.
          </p>
        )}
      </div>
    </main>
  );
}

function Shell({
  me,
  route,
  children,
}: {
  me: Me;
  route: ReturnType<typeof useRoute>;
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-6 py-3">
          <div className="flex items-center gap-6">
            <a href="#/" className="text-sm font-semibold text-slate-900">
              Didim Skill Registry
            </a>
            {me.is_admin ? (
              <nav className="flex gap-1 text-sm">
                <NavLink href="#/" active={route.name !== "audit"}>
                  <Wrench className="h-4 w-4" aria-hidden /> 스킬
                </NavLink>
                <NavLink href="#/audit" active={route.name === "audit"}>
                  <ClipboardList className="h-4 w-4" aria-hidden /> 변경 이력
                </NavLink>
              </nav>
            ) : null}
          </div>
          <div className="flex items-center gap-3 text-sm text-slate-600">
            <span>
              {me.display_name ?? me.email ?? "사용자"}
              {me.role ? <span className="ml-1 text-xs text-slate-400">({me.role})</span> : null}
            </span>
            <LogoutButton />
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-6">{children}</main>
    </div>
  );
}

function NavLink({
  href,
  active,
  children,
}: {
  href: string;
  active: boolean;
  children: React.ReactNode;
}) {
  return (
    <a
      href={href}
      aria-current={active ? "page" : undefined}
      className={
        active
          ? "inline-flex items-center gap-1.5 rounded-md bg-slate-100 px-3 py-1.5 font-medium text-slate-900"
          : "inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-slate-600 hover:bg-slate-50"
      }
    >
      {children}
    </a>
  );
}

/** 로그아웃은 backend 의 `POST /logout` 이다(Refresh 폐기 + 통합 로그아웃 체인). */
function LogoutButton() {
  return (
    <form method="post" action="/logout">
      <input type="hidden" name="csrf_token" value={currentCsrfToken() ?? ""} />
      <Button type="submit" variant="ghost">
        <LogOut className="h-4 w-4" aria-hidden /> 로그아웃
      </Button>
    </form>
  );
}
