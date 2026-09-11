// 변경 이력 — 누가 언제 무엇을 바꿨는지. 조회는 기록하지 않는다(변경만 남는다).

import { useState } from "react";

import { Badge, Empty, ErrorState, Loading, Pagination } from "../components/ui";
import { api, buildQuery } from "../lib/api";
import { formatDateTime, operationLabel, resultLabel } from "../lib/labels";
import { useResource } from "../lib/useResource";
import type { AuditLogItem, Page } from "../types/api";

const OPERATIONS = [
  "",
  "SKILL_CREATE",
  "DRAFT_CREATE",
  "DRAFT_UPDATE",
  "DRAFT_DELETE",
  "PUBLISH",
  "ROLLBACK",
  "SKILL_ENABLE",
  "SKILL_DISABLE",
];

export default function AuditLog() {
  const [operation, setOperation] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const logs = useResource<Page<AuditLogItem>>(
    () =>
      api.get<Page<AuditLogItem>>(
        "/api/v1/admin/audit-logs" + buildQuery({ operation, page, page_size: pageSize }),
      ),
    [operation, page, pageSize],
  );

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">변경 이력</h1>
        <p className="mt-1 text-sm text-slate-600">
          스킬을 만들고 고치고 배포한 기록입니다. 조회는 남지 않습니다.
        </p>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white">
        <div className="border-b border-slate-200 p-4">
          <label className="text-xs font-medium text-slate-600" htmlFor="audit-operation">
            작업
          </label>
          <select
            id="audit-operation"
            className="ml-2 rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm"
            value={operation}
            onChange={(e) => {
              setPage(1);
              setOperation(e.target.value);
            }}
          >
            {OPERATIONS.map((op) => (
              <option key={op} value={op}>
                {op === "" ? "전체" : operationLabel(op)}
              </option>
            ))}
          </select>
        </div>

        {logs.loading ? (
          <Loading />
        ) : logs.error ? (
          <div className="p-4">
            <ErrorState message={logs.error} onRetry={logs.reload} />
          </div>
        ) : !logs.data || logs.data.items.length === 0 ? (
          <Empty label="기록이 없습니다." />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-slate-200 bg-slate-50 text-xs text-slate-600">
                  <tr>
                    <th className="px-4 py-2 font-medium">시각</th>
                    <th className="px-4 py-2 font-medium">작업자</th>
                    <th className="px-4 py-2 font-medium">작업</th>
                    <th className="px-4 py-2 font-medium">대상</th>
                    <th className="px-4 py-2 font-medium">결과</th>
                    <th className="px-4 py-2 font-medium">상세</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {logs.data.items.map((row) => (
                    <tr key={row.id} className="hover:bg-slate-50">
                      <td className="px-4 py-3 text-slate-600">{formatDateTime(row.created_at)}</td>
                      <td className="px-4 py-3 text-slate-800">{row.actor_display_name ?? "—"}</td>
                      <td className="px-4 py-3 text-slate-800">{operationLabel(row.operation)}</td>
                      <td className="px-4 py-3">
                        <code className="text-xs text-slate-700">{row.skill_key ?? "—"}</code>
                        {row.skill_version !== null ? (
                          <span className="ml-1 text-xs text-slate-500">v{row.skill_version}</span>
                        ) : null}
                      </td>
                      <td className="px-4 py-3">
                        <Badge
                          tone={
                            row.result === "SUCCESS"
                              ? "border-emerald-300 bg-emerald-100 text-emerald-900"
                              : "border-rose-300 bg-rose-100 text-rose-900"
                          }
                        >
                          {resultLabel(row.result)}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-600">
                        {row.detail ? JSON.stringify(row.detail) : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination
              page={logs.data.meta.page}
              pageSize={logs.data.meta.page_size}
              total={logs.data.meta.total}
              totalPages={logs.data.meta.total_pages}
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
