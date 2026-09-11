// 스킬 목록 — 검색 / 카테고리 / 상태 / 사용 여부 필터 + 20·50·100 페이징 + 정렬.
//
// 열: 스킬 · 카테고리 · 배포 버전 · 상태 · 사용 여부 · 최근 수정 · 관리

import { Plus, Search } from "lucide-react";
import { useState } from "react";

import { Badge, Button, Empty, ErrorState, Loading, Pagination, inputClass } from "../components/ui";
import { api, buildQuery } from "../lib/api";
import { enabledLabel, formatDateTime, statusLabel, statusTone, versionLabel } from "../lib/labels";
import { navigate } from "../lib/router";
import { useResource } from "../lib/useResource";
import type { Page, SkillSummary } from "../types/api";

type StatusFilter = "" | "DRAFT" | "PUBLISHED" | "SUPERSEDED";
type EnabledFilter = "" | "true" | "false";

export default function SkillList() {
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [status, setStatus] = useState<StatusFilter>("");
  const [enabled, setEnabled] = useState<EnabledFilter>("");
  const [sort, setSort] = useState("-updated_at");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const categories = useResource<string[]>(
    () => api.get<string[]>("/api/v1/admin/skills/categories"),
    [],
  );

  const skills = useResource<Page<SkillSummary>>(
    () =>
      api.get<Page<SkillSummary>>(
        "/api/v1/admin/skills" +
          buildQuery({ search: query, category, status, enabled, sort, page, page_size: pageSize }),
      ),
    [query, category, status, enabled, sort, page, pageSize],
  );

  function applySearch(e: React.FormEvent) {
    e.preventDefault();
    setPage(1);
    setQuery(search.trim());
  }

  function reset<T>(setter: (v: T) => void) {
    return (value: T) => {
      setPage(1);
      setter(value);
    };
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">스킬</h1>
          <p className="mt-1 text-sm text-slate-600">
            Codex 가 실행하는 업무 절차입니다. 수정한 내용은 <strong>배포</strong>해야 실제로
            쓰입니다.
          </p>
        </div>
        <Button variant="primary" onClick={() => navigate("#/new")}>
          <Plus className="h-4 w-4" aria-hidden /> 새 스킬 등록
        </Button>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white">
        <form
          onSubmit={applySearch}
          className="flex flex-wrap items-end gap-3 border-b border-slate-200 p-4"
        >
          <div className="min-w-56 flex-1">
            <label className="block text-xs font-medium text-slate-600" htmlFor="skill-search">
              검색
            </label>
            <div className="mt-1 flex gap-2">
              <input
                id="skill-search"
                className={inputClass}
                placeholder="스킬 키 또는 이름"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              <Button type="submit">
                <Search className="h-4 w-4" aria-hidden /> 찾기
              </Button>
            </div>
          </div>

          <FilterSelect
            id="filter-category"
            label="카테고리"
            value={category}
            onChange={reset(setCategory)}
            options={[
              { value: "", label: "전체" },
              ...(categories.data ?? []).map((c) => ({ value: c, label: c })),
            ]}
          />
          <FilterSelect
            id="filter-status"
            label="상태"
            value={status}
            onChange={reset((v: string) => setStatus(v as StatusFilter))}
            options={[
              { value: "", label: "전체" },
              { value: "PUBLISHED", label: "배포됨" },
              { value: "DRAFT", label: "초안 있음" },
              { value: "SUPERSEDED", label: "지난 배포 있음" },
            ]}
          />
          <FilterSelect
            id="filter-enabled"
            label="사용 여부"
            value={enabled}
            onChange={reset((v: string) => setEnabled(v as EnabledFilter))}
            options={[
              { value: "", label: "전체" },
              { value: "true", label: "사용" },
              { value: "false", label: "사용 안 함" },
            ]}
          />
          <FilterSelect
            id="filter-sort"
            label="정렬"
            value={sort}
            onChange={reset(setSort)}
            options={[
              { value: "-updated_at", label: "최근 수정 순" },
              { value: "updated_at", label: "오래된 수정 순" },
              { value: "skill_key", label: "스킬 키 오름차순" },
              { value: "-skill_key", label: "스킬 키 내림차순" },
              { value: "category", label: "카테고리 순" },
            ]}
          />
        </form>

        {skills.loading ? (
          <Loading />
        ) : skills.error ? (
          <div className="p-4">
            <ErrorState message={skills.error} onRetry={skills.reload} />
          </div>
        ) : !skills.data || skills.data.items.length === 0 ? (
          <Empty label="조건에 맞는 스킬이 없습니다." />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-slate-200 bg-slate-50 text-xs text-slate-600">
                  <tr>
                    <Th>스킬</Th>
                    <Th>카테고리</Th>
                    <Th>배포 버전</Th>
                    <Th>상태</Th>
                    <Th>사용 여부</Th>
                    <Th>최근 수정</Th>
                    <Th>관리</Th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {skills.data.items.map((s) => (
                    <tr key={s.id} className="hover:bg-slate-50">
                      <td className="px-4 py-3">
                        <div className="font-medium text-slate-900">
                          {s.published_name ?? s.skill_key}
                        </div>
                        <code className="text-xs text-slate-500">{s.skill_key}</code>
                      </td>
                      <td className="px-4 py-3 text-slate-700">{s.category ?? "—"}</td>
                      <td className="px-4 py-3 text-slate-700">
                        {versionLabel(s.published_version)}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-1">
                          {s.published_version !== null ? (
                            <Badge tone={statusTone("PUBLISHED")}>{statusLabel("PUBLISHED")}</Badge>
                          ) : null}
                          {s.draft_version !== null ? (
                            <Badge tone={statusTone("DRAFT")}>
                              {statusLabel("DRAFT")} v{s.draft_version}
                            </Badge>
                          ) : null}
                          {s.published_version === null && s.draft_version === null ? (
                            <span className="text-slate-500">—</span>
                          ) : null}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <Badge
                          tone={
                            s.enabled
                              ? "border-sky-300 bg-sky-100 text-sky-900"
                              : "border-slate-300 bg-slate-100 text-slate-700"
                          }
                        >
                          {enabledLabel(s.enabled)}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-slate-600">{formatDateTime(s.updated_at)}</td>
                      <td className="px-4 py-3">
                        <Button onClick={() => navigate(`#/skills/${s.id}`)}>열기</Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination
              page={skills.data.meta.page}
              pageSize={skills.data.meta.page_size}
              total={skills.data.meta.total}
              totalPages={skills.data.meta.total_pages}
              onPage={setPage}
              onPageSize={(size) => {
                setPage(1);
                setPageSize(size);
              }}
            />
          </>
        )}
      </div>
    </div>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return <th className="px-4 py-2 font-medium">{children}</th>;
}

function FilterSelect({
  id,
  label,
  value,
  onChange,
  options,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <div>
      <label className="block text-xs font-medium text-slate-600" htmlFor={id}>
        {label}
      </label>
      <select
        id={id}
        className="mt-1 rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}
