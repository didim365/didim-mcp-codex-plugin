// 새 스킬 등록 — identity + v1 초안. **등록만으로는 배포되지 않는다.**

import { ArrowLeft } from "lucide-react";
import { useState } from "react";

import { SkillEditor, type EditorValue } from "../components/SkillEditor";
import { Button, ErrorState } from "../components/ui";
import { ApiError, api } from "../lib/api";
import { navigate } from "../lib/router";
import type { SkillDetail } from "../types/api";

const EMPTY: EditorValue = {
  skill_key: "",
  category: "",
  name: "",
  description: "",
  instructions: "",
  aliases: [],
  tools: [],
};

export default function SkillNew() {
  const [value, setValue] = useState<EditorValue>(EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const created = await api.post<SkillDetail>("/api/v1/admin/skills", {
        skill_key: (value.skill_key ?? "").trim(),
        category: (value.category ?? "").trim() || null,
        name: value.name,
        description: value.description,
        instructions: value.instructions,
        aliases: value.aliases,
        tools: value.tools,
      });
      navigate(`#/skills/${created.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "등록에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <Button variant="ghost" type="button" onClick={() => navigate("#/")}>
        <ArrowLeft className="h-4 w-4" aria-hidden /> 목록으로
      </Button>

      <div className="rounded-lg border border-slate-200 bg-white p-5">
        <h1 className="text-xl font-semibold text-slate-900">새 스킬 등록</h1>
        <p className="mt-1 text-sm text-slate-600">
          등록하면 <strong>초안 v1</strong> 이 만들어집니다. 배포해야 Codex 가 사용합니다.
        </p>
      </div>

      {error ? <ErrorState message={error} /> : null}

      <div className="rounded-lg border border-slate-200 bg-white p-5">
        <SkillEditor value={value} onChange={setValue} showIdentity />
      </div>

      <div className="flex justify-end gap-2">
        <Button type="button" onClick={() => navigate("#/")} disabled={busy}>
          취소
        </Button>
        <Button type="submit" variant="primary" disabled={busy || !value.skill_key || !value.name}>
          {busy ? "등록 중…" : "초안으로 등록"}
        </Button>
      </div>
    </form>
  );
}
