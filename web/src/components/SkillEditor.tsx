// 초안 편집기 — 이름 / 설명 / 별칭 / 사용할 도구 / 절차 본문.
//
// 절차 본문은 Markdown 편집 + 미리보기다. **WYSIWYG 라이브러리를 들이지 않는다** —
// 여기 필요한 것은 원문 그대로의 Markdown 이고, Codex 는 그 원문을 읽는다.

import { useState } from "react";

import { Field, inputClass } from "./ui";
import type { VersionContent } from "../types/api";

export interface EditorValue extends VersionContent {
  skill_key?: string;
  category?: string | null;
}

export function SkillEditor({
  value,
  onChange,
  showIdentity,
}: {
  value: EditorValue;
  onChange: (next: EditorValue) => void;
  /** 새 스킬 등록에서만 true — `skill_key` 는 등록 후 바꿀 수 없다. */
  showIdentity: boolean;
}) {
  const [tab, setTab] = useState<"edit" | "preview">("edit");

  const set = <K extends keyof EditorValue>(key: K, v: EditorValue[K]) =>
    onChange({ ...value, [key]: v });

  return (
    <div className="space-y-4">
      {showIdentity ? (
        <div className="grid gap-4 sm:grid-cols-2">
          <Field
            label="스킬 키"
            hint="Codex 와 MCP 도구가 이 값으로 스킬을 찾습니다. 등록 후에는 바꿀 수 없습니다. 예: mcp.usage"
          >
            <input
              className={inputClass}
              value={value.skill_key ?? ""}
              onChange={(e) => set("skill_key", e.target.value)}
              placeholder="mcp.usage"
              autoComplete="off"
            />
          </Field>
          <Field label="카테고리" hint="목록 화면의 분류·필터에만 쓰입니다.">
            <input
              className={inputClass}
              value={value.category ?? ""}
              onChange={(e) => set("category", e.target.value)}
              placeholder="MCP 공통"
              autoComplete="off"
            />
          </Field>
        </div>
      ) : null}

      <Field label="이름" hint="운영자와 사용자가 보는 이름입니다.">
        <input
          className={inputClass}
          value={value.name}
          onChange={(e) => set("name", e.target.value)}
          autoComplete="off"
        />
      </Field>

      <Field label="설명" hint="이 절차가 무엇을 하는지 한두 문장으로 적습니다.">
        <textarea
          className={`${inputClass} min-h-20`}
          value={value.description}
          onChange={(e) => set("description", e.target.value)}
        />
      </Field>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="별칭" hint="쉼표로 구분합니다. 이 절차를 가리키는 다른 이름입니다.">
          <input
            className={inputClass}
            value={value.aliases.join(", ")}
            onChange={(e) => set("aliases", splitList(e.target.value))}
            placeholder="didim-mcp-usage, mcp-usage"
            autoComplete="off"
          />
        </Field>
        <Field
          label="사용할 도구"
          hint="쉼표로 구분합니다. 이 절차가 쓰도록 의도된 도구 목록일 뿐이며, 권한을 주지 않습니다."
        >
          <input
            className={inputClass}
            value={value.tools.join(", ")}
            onChange={(e) => set("tools", splitList(e.target.value))}
            placeholder="didim-vault__list_my_resources"
            autoComplete="off"
          />
        </Field>
      </div>

      <div className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900">
        여기에 적은 도구 목록은 <strong>권한이 아닙니다.</strong> 사용자가 실제로 그 도구를
        호출할 수 있는지는 Didim MCP 서버가 정합니다.
      </div>

      <div>
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-slate-700">절차 본문 (Markdown)</span>
          <div className="flex gap-1 text-xs" role="tablist" aria-label="본문 보기 방식">
            <TabButton active={tab === "edit"} onClick={() => setTab("edit")}>
              편집
            </TabButton>
            <TabButton active={tab === "preview"} onClick={() => setTab("preview")}>
              미리보기
            </TabButton>
          </div>
        </div>
        {tab === "edit" ? (
          <textarea
            aria-label="절차 본문"
            className={`${inputClass} mt-1 min-h-96 font-mono text-xs`}
            value={value.instructions}
            onChange={(e) => set("instructions", e.target.value)}
          />
        ) : (
          <div
            className="md-preview mt-1 min-h-96 rounded-md border border-slate-300 bg-white p-3"
            aria-label="절차 본문 미리보기"
          >
            {value.instructions || <span className="text-slate-400">내용이 없습니다.</span>}
          </div>
        )}
        <p className="mt-1 text-xs text-slate-500">
          Codex 는 이 본문을 그대로 읽습니다. 계정·토큰·비밀번호 같은 실제 값을 적지 마세요.
        </p>
      </div>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={
        active
          ? "rounded-md border border-slate-300 bg-white px-2 py-1 font-medium text-slate-900"
          : "rounded-md border border-transparent px-2 py-1 text-slate-600 hover:bg-slate-100"
      }
    >
      {children}
    </button>
  );
}

export function splitList(raw: string): string[] {
  return raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}
