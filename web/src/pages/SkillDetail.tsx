// 스킬 상세 — 현재 배포본 / 초안 편집 / 버전 이력 / 배포 · 롤백 · 사용 여부.
//
// **배포본과 초안은 시각적으로 구분된다.** 초안은 Codex 에서 보이지 않는다는 사실을
// 화면에 그대로 적는다 — 운영자가 "고쳤는데 왜 안 바뀌지" 로 헤매는 지점이다.

import { ArrowLeft, Rocket, Save, Trash2, Undo2 } from "lucide-react";
import { useState } from "react";

import { SkillEditor, type EditorValue } from "../components/SkillEditor";
import {
  Badge,
  Button,
  ConfirmDialog,
  ErrorState,
  Forbidden,
  Loading,
} from "../components/ui";
import { ApiError, api } from "../lib/api";
import { enabledLabel, formatDateTime, statusLabel, statusTone, versionLabel } from "../lib/labels";
import { navigate } from "../lib/router";
import { useResource } from "../lib/useResource";
import type { SkillDetail as SkillDetailDto, SkillVersionDetail } from "../types/api";

type Pending =
  | { kind: "publish"; version: number }
  | { kind: "rollback"; version: number }
  | { kind: "delete-draft"; version: number }
  | { kind: "toggle"; enabled: boolean }
  | null;

export default function SkillDetailPage({ skillId }: { skillId: string }) {
  const skill = useResource<SkillDetailDto>(
    () => api.get<SkillDetailDto>(`/api/v1/admin/skills/${skillId}`),
    [skillId],
  );
  const [draft, setDraft] = useState<EditorValue | null>(null);
  const [pending, setPending] = useState<Pending>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  if (skill.loading) return <Loading />;
  if (skill.errorStatus === 403) return <Forbidden />;
  if (skill.error || !skill.data)
    return <ErrorState message={skill.error ?? "스킬을 불러오지 못했습니다."} onRetry={skill.reload} />;

  const data = skill.data;
  const editing = draft ?? (data.draft ? toEditor(data.draft) : null);

  async function run(fn: () => Promise<unknown>, message: string) {
    setBusy(true);
    setActionError(null);
    try {
      await fn();
      setNotice(message);
      setDraft(null);
      skill.reload();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "요청 처리 중 오류가 발생했습니다.");
    } finally {
      setBusy(false);
      setPending(null);
    }
  }

  const startDraft = () =>
    run(
      () => api.post(`/api/v1/admin/skills/${skillId}/versions`, null),
      "현재 배포본을 복사해 새 초안을 만들었습니다.",
    );

  const saveDraft = () => {
    if (!editing || !data.draft) return;
    return run(
      () =>
        api.put(`/api/v1/admin/skills/${skillId}/versions/${data.draft!.version}`, {
          name: editing.name,
          description: editing.description,
          instructions: editing.instructions,
          aliases: editing.aliases,
          tools: editing.tools,
        }),
      "초안을 저장했습니다. 아직 Codex 에는 적용되지 않았습니다.",
    );
  };

  const confirmPending = () => {
    if (!pending) return;
    if (pending.kind === "publish")
      return run(
        () => api.post(`/api/v1/admin/skills/${skillId}/publish`, { version: pending.version }),
        `v${pending.version} 을 배포했습니다.`,
      );
    if (pending.kind === "rollback")
      return run(
        () => api.post(`/api/v1/admin/skills/${skillId}/rollback`, { version: pending.version }),
        `v${pending.version} 내용으로 되돌려 새 버전을 배포했습니다.`,
      );
    if (pending.kind === "delete-draft")
      return run(
        () => api.del(`/api/v1/admin/skills/${skillId}/versions/${pending.version}`),
        "초안을 삭제했습니다.",
      );
    return run(
      () => api.patch(`/api/v1/admin/skills/${skillId}/enabled`, { enabled: pending.enabled }),
      pending.enabled ? "사용으로 변경했습니다." : "사용 안 함으로 변경했습니다.",
    );
  };

  return (
    <div className="space-y-4">
      <Button variant="ghost" onClick={() => navigate("#/")}>
        <ArrowLeft className="h-4 w-4" aria-hidden /> 목록으로
      </Button>

      <header className="rounded-lg border border-slate-200 bg-white p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-slate-900">
              {data.published?.name ?? data.skill_key}
            </h1>
            <p className="mt-1 text-sm text-slate-600">
              <code className="rounded bg-slate-100 px-1.5 py-0.5">{data.skill_key}</code>
              <span className="mx-2 text-slate-300">|</span>
              {data.category ?? "카테고리 없음"}
              <span className="mx-2 text-slate-300">|</span>
              배포 {versionLabel(data.published_version)}
              <span className="mx-2 text-slate-300">|</span>
              최근 수정 {formatDateTime(data.updated_at)}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge
              tone={
                data.enabled
                  ? "border-sky-300 bg-sky-100 text-sky-900"
                  : "border-slate-300 bg-slate-100 text-slate-700"
              }
            >
              {enabledLabel(data.enabled)}
            </Badge>
            <Button onClick={() => setPending({ kind: "toggle", enabled: !data.enabled })}>
              {data.enabled ? "사용 안 함으로" : "사용으로"}
            </Button>
          </div>
        </div>
        {!data.enabled ? (
          <p className="mt-3 rounded-md border border-slate-300 bg-slate-50 px-3 py-2 text-xs text-slate-700">
            사용 안 함 상태입니다. 배포된 버전이 있어도 Codex 에는 노출되지 않습니다.
          </p>
        ) : null}
      </header>

      {notice ? (
        <div
          role="status"
          className="rounded-md border border-emerald-300 bg-emerald-50 px-4 py-2 text-sm text-emerald-900"
        >
          {notice}
        </div>
      ) : null}
      {actionError ? <ErrorState message={actionError} /> : null}

      <section className="rounded-lg border border-emerald-300 bg-white">
        <SectionHeader
          tone="bg-emerald-50 border-emerald-300"
          title="현재 배포본"
          subtitle="Codex 가 지금 읽는 내용입니다."
        />
        {data.published ? (
          <VersionBody version={data.published} />
        ) : (
          <p className="p-5 text-sm text-slate-600">
            아직 배포된 버전이 없습니다. 초안을 배포해야 Codex 가 이 스킬을 사용할 수 있습니다.
          </p>
        )}
      </section>

      <section className="rounded-lg border border-amber-300 bg-white">
        <SectionHeader
          tone="bg-amber-50 border-amber-300"
          title={data.draft ? `초안 v${data.draft.version}` : "초안"}
          subtitle="편집 중인 내용입니다. 배포하기 전에는 Codex 에 보이지 않습니다."
          right={
            data.draft ? (
              <div className="flex gap-2">
                <Button onClick={saveDraft} disabled={busy}>
                  <Save className="h-4 w-4" aria-hidden /> 초안 저장
                </Button>
                <Button
                  variant="primary"
                  onClick={() => setPending({ kind: "publish", version: data.draft!.version })}
                  disabled={busy}
                >
                  <Rocket className="h-4 w-4" aria-hidden /> 배포
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => setPending({ kind: "delete-draft", version: data.draft!.version })}
                  disabled={busy}
                >
                  <Trash2 className="h-4 w-4" aria-hidden /> 삭제
                </Button>
              </div>
            ) : (
              <Button onClick={startDraft} disabled={busy}>
                초안 만들기
              </Button>
            )
          }
        />
        {data.draft && editing ? (
          <div className="p-5">
            <SkillEditor value={editing} onChange={setDraft} showIdentity={false} />
          </div>
        ) : (
          <p className="p-5 text-sm text-slate-600">
            편집 중인 초안이 없습니다. <strong>초안 만들기</strong>를 누르면 현재 배포본을 복사해
            시작합니다.
          </p>
        )}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white">
        <SectionHeader tone="bg-slate-50 border-slate-200" title="버전 이력" />
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs text-slate-600">
              <tr>
                <th className="px-4 py-2 font-medium">버전</th>
                <th className="px-4 py-2 font-medium">이름</th>
                <th className="px-4 py-2 font-medium">상태</th>
                <th className="px-4 py-2 font-medium">작성</th>
                <th className="px-4 py-2 font-medium">배포</th>
                <th className="px-4 py-2 font-medium">관리</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.versions.map((v) => (
                <tr key={v.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-medium text-slate-900">
                    v{v.version}
                    {v.rolled_back_from !== null ? (
                      <span className="ml-1 text-xs font-normal text-slate-500">
                        (v{v.rolled_back_from} 롤백)
                      </span>
                    ) : null}
                  </td>
                  <td className="px-4 py-3 text-slate-700">{v.name}</td>
                  <td className="px-4 py-3">
                    <Badge tone={statusTone(v.status)}>{statusLabel(v.status)}</Badge>
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {v.created_by_name ?? "—"}
                    <div className="text-xs text-slate-500">{formatDateTime(v.created_at)}</div>
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {v.published_by_name ?? "—"}
                    <div className="text-xs text-slate-500">{formatDateTime(v.published_at)}</div>
                  </td>
                  <td className="px-4 py-3">
                    {v.status === "SUPERSEDED" ? (
                      <Button
                        onClick={() => setPending({ kind: "rollback", version: v.version })}
                        disabled={busy}
                      >
                        <Undo2 className="h-4 w-4" aria-hidden /> 이 버전으로 롤백
                      </Button>
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <ConfirmDialog
        open={pending !== null}
        busy={busy}
        title={confirmTitle(pending)}
        body={confirmBody(pending, data)}
        confirmLabel={confirmLabel(pending)}
        variant={pending?.kind === "delete-draft" ? "danger" : "primary"}
        onConfirm={confirmPending}
        onCancel={() => setPending(null)}
      />
    </div>
  );
}

function SectionHeader({
  tone,
  title,
  subtitle,
  right,
}: {
  tone: string;
  title: string;
  subtitle?: string;
  right?: React.ReactNode;
}) {
  return (
    <div className={`flex flex-wrap items-center justify-between gap-3 border-b px-5 py-3 ${tone}`}>
      <div>
        <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
        {subtitle ? <p className="text-xs text-slate-600">{subtitle}</p> : null}
      </div>
      {right}
    </div>
  );
}

function VersionBody({ version }: { version: SkillVersionDetail }) {
  return (
    <dl className="grid gap-3 p-5 text-sm">
      <Row label="버전">v{version.version}</Row>
      <Row label="이름">{version.name}</Row>
      <Row label="설명">{version.description || "—"}</Row>
      <Row label="별칭">{version.aliases.length ? version.aliases.join(", ") : "—"}</Row>
      <Row label="사용할 도구">{version.tools.length ? version.tools.join(", ") : "—"}</Row>
      <Row label="배포">
        {version.published_by_name ?? "—"} · {formatDateTime(version.published_at)}
      </Row>
      <div>
        <dt className="text-xs font-medium text-slate-600">절차 본문</dt>
        <dd className="md-preview mt-1 rounded-md border border-slate-200 bg-slate-50 p-3">
          {version.instructions || "—"}
        </dd>
      </div>
    </dl>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[7rem_1fr] gap-2">
      <dt className="text-xs font-medium text-slate-600">{label}</dt>
      <dd className="text-slate-800">{children}</dd>
    </div>
  );
}

function toEditor(v: SkillVersionDetail): EditorValue {
  return {
    name: v.name,
    description: v.description,
    instructions: v.instructions,
    aliases: [...v.aliases],
    tools: [...v.tools],
  };
}

function confirmTitle(pending: Pending): string {
  switch (pending?.kind) {
    case "publish":
      return "이 초안을 배포할까요?";
    case "rollback":
      return "이 버전으로 되돌릴까요?";
    case "delete-draft":
      return "초안을 삭제할까요?";
    case "toggle":
      return pending.enabled ? "사용으로 바꿀까요?" : "사용 안 함으로 바꿀까요?";
    default:
      return "";
  }
}

function confirmLabel(pending: Pending): string {
  switch (pending?.kind) {
    case "publish":
      return "배포";
    case "rollback":
      return "롤백";
    case "delete-draft":
      return "삭제";
    default:
      return "변경";
  }
}

function confirmBody(pending: Pending, data: SkillDetailDto): React.ReactNode {
  if (!pending) return null;
  if (pending.kind === "publish")
    return (
      <p>
        <strong>v{pending.version}</strong> 이 현재 배포본이 되고, 지금 배포된{" "}
        {versionLabel(data.published_version)} 은 지난 배포로 내려갑니다. 배포 직후부터 Codex 가 이
        내용을 읽습니다.
      </p>
    );
  if (pending.kind === "rollback")
    return (
      <p>
        <strong>v{pending.version}</strong> 의 내용을 복사해 <strong>새 버전</strong>으로 배포합니다.
        기존 이력은 지워지지 않습니다.
      </p>
    );
  if (pending.kind === "delete-draft")
    return (
      <p>
        초안 <strong>v{pending.version}</strong> 을 삭제합니다. 배포 이력은 지워지지 않지만, 저장하지
        않은 편집 내용은 사라집니다.
      </p>
    );
  return pending.enabled ? (
    <p>사용으로 바꾸면 배포된 버전이 다시 Codex 에 노출됩니다.</p>
  ) : (
    <p>사용 안 함으로 바꾸면 배포된 버전이 있어도 Codex 에 노출되지 않습니다.</p>
  );
}
