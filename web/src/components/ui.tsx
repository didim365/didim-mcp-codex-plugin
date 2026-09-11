// 공용 UI 부품. Empty / Loading / Error 는 화면마다 다시 만들지 않고 여기 것을 쓴다.

import clsx from "clsx";
import { AlertTriangle, Inbox, Loader2, ShieldAlert } from "lucide-react";
import type { ReactNode } from "react";

export function Badge({ tone, children }: { tone: string; children: ReactNode }) {
  // 색만으로 구분하지 않는다 — 항상 label 텍스트를 함께 그린다.
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium",
        tone,
      )}
    >
      {children}
    </span>
  );
}

export function Button({
  variant = "default",
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "default" | "primary" | "danger" | "ghost";
}) {
  const tone = {
    default: "border-slate-300 bg-white text-slate-800 hover:bg-slate-50",
    primary: "border-sky-700 bg-sky-700 text-white hover:bg-sky-800",
    danger: "border-rose-700 bg-rose-700 text-white hover:bg-rose-800",
    ghost: "border-transparent bg-transparent text-slate-600 hover:bg-slate-100",
  }[variant];
  return (
    <button
      {...props}
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm font-medium",
        "transition-colors disabled:cursor-not-allowed disabled:opacity-50",
        tone,
        className,
      )}
    />
  );
}

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  // hint 는 `<label>` **밖에** 둔다. 안에 두면 접근성 이름이 "라벨 + 설명문" 이 되어
  // 스크린리더가 입력마다 긴 문장을 읽고, 테스트의 `getByLabelText` 도 맞지 않는다.
  return (
    <div className="space-y-1">
      <label className="block space-y-1">
        <span className="block text-sm font-medium text-slate-700">{label}</span>
        {children}
      </label>
      {hint ? <p className="text-xs text-slate-500">{hint}</p> : null}
    </div>
  );
}

export const inputClass =
  "w-full rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm " +
  "focus:border-sky-600 focus:ring-1 focus:ring-sky-600 focus:outline-none";

export function Loading({ label = "불러오는 중입니다…" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 py-10 text-sm text-slate-500" role="status">
      <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
      {label}
    </div>
  );
}

export function Empty({ label }: { label: string }) {
  return (
    <div className="flex flex-col items-center gap-2 py-14 text-sm text-slate-500">
      <Inbox className="h-6 w-6" aria-hidden />
      {label}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div
      role="alert"
      className="flex items-start gap-3 rounded-md border border-rose-300 bg-rose-50 px-4 py-3 text-sm text-rose-900"
    >
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
      <div className="space-y-2">
        <p>{message}</p>
        {onRetry ? (
          <Button onClick={onRetry} variant="default">
            다시 시도
          </Button>
        ) : null}
      </div>
    </div>
  );
}

/** 권한 부족(403). **화면에 남긴다** — 로그인으로 튕기지 않는다. */
export function Forbidden({ message }: { message?: string }) {
  return (
    <div
      role="alert"
      className="mx-auto mt-16 max-w-lg rounded-lg border border-slate-300 bg-white p-8 text-center"
    >
      <ShieldAlert className="mx-auto h-8 w-8 text-slate-400" aria-hidden />
      <h2 className="mt-3 text-lg font-semibold text-slate-900">접근 권한이 없습니다</h2>
      <p className="mt-2 text-sm text-slate-600">
        {message ?? "스킬 관리 화면은 관리자만 사용할 수 있습니다. 담당자에게 권한을 요청하세요."}
      </p>
    </div>
  );
}

/**
 * 확인 modal. Publish / Rollback / 초안 삭제처럼 되돌리기 어려운 작업 앞에 둔다.
 * 네이티브 `<dialog>` 를 쓴다(포커스 트랩·ESC 가 브라우저 것이다).
 */
export function ConfirmDialog({
  open,
  title,
  body,
  confirmLabel,
  variant = "primary",
  busy,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  body: ReactNode;
  confirmLabel: string;
  variant?: "primary" | "danger";
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="w-full max-w-md rounded-lg border border-slate-300 bg-white p-6 shadow-xl"
      >
        <h3 className="text-base font-semibold text-slate-900">{title}</h3>
        <div className="mt-3 text-sm text-slate-700">{body}</div>
        <div className="mt-6 flex justify-end gap-2">
          <Button onClick={onCancel} disabled={busy}>
            취소
          </Button>
          <Button variant={variant} onClick={onConfirm} disabled={busy}>
            {busy ? "처리 중…" : confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}

export function Pagination({
  page,
  pageSize,
  total,
  totalPages,
  onPage,
  onPageSize,
}: {
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  onPage: (page: number) => void;
  onPageSize: (size: number) => void;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 px-4 py-3 text-sm">
      <span className="text-slate-600">
        전체 {total.toLocaleString()}건 · {page} / {totalPages} 페이지
      </span>
      <div className="flex items-center gap-2">
        <label className="flex items-center gap-1 text-slate-600">
          쪽당
          <select
            className="rounded-md border border-slate-300 bg-white px-2 py-1"
            value={pageSize}
            onChange={(e) => onPageSize(Number(e.target.value))}
            aria-label="쪽당 표시 개수"
          >
            <option value={20}>20</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
        </label>
        <Button onClick={() => onPage(page - 1)} disabled={page <= 1}>
          이전
        </Button>
        <Button onClick={() => onPage(page + 1)} disabled={page >= totalPages}>
          다음
        </Button>
      </div>
    </div>
  );
}
