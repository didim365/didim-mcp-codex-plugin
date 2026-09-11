// 표시 매핑의 **정본은 여기 하나**다. 화면마다 enum → 한국어를 다시 쓰지 않는다.
// 모르는 값은 감추지 말고 원문을 그대로 보여준다.
// **색만으로 구분하지 않는다** — badge 는 항상 label 을 갖는다.

import type { AuditOperation, AuditResult, SkillVersionStatus } from "../types/api";

const STATUS: Record<SkillVersionStatus, string> = {
  DRAFT: "초안",
  PUBLISHED: "배포됨",
  SUPERSEDED: "지난 배포",
};

const STATUS_TONE: Record<SkillVersionStatus, string> = {
  DRAFT: "bg-amber-100 text-amber-900 border-amber-300",
  PUBLISHED: "bg-emerald-100 text-emerald-900 border-emerald-300",
  SUPERSEDED: "bg-slate-100 text-slate-700 border-slate-300",
};

const OPERATION: Record<AuditOperation, string> = {
  SKILL_CREATE: "스킬 생성",
  SKILL_ENABLE: "사용함으로 변경",
  SKILL_DISABLE: "사용 안 함으로 변경",
  DRAFT_CREATE: "초안 생성",
  DRAFT_UPDATE: "초안 수정",
  DRAFT_DELETE: "초안 삭제",
  PUBLISH: "배포",
  ROLLBACK: "롤백",
};

const RESULT: Record<AuditResult, string> = {
  SUCCESS: "성공",
  FAILED: "실패",
  DENIED: "거부",
};

export function statusLabel(value: string): string {
  return STATUS[value as SkillVersionStatus] ?? value;
}

export function statusTone(value: string): string {
  return STATUS_TONE[value as SkillVersionStatus] ?? "bg-slate-100 text-slate-700 border-slate-300";
}

export function operationLabel(value: string): string {
  return OPERATION[value as AuditOperation] ?? value;
}

export function resultLabel(value: string): string {
  return RESULT[value as AuditResult] ?? value;
}

export function enabledLabel(enabled: boolean): string {
  return enabled ? "사용" : "사용 안 함";
}

/** 날짜는 서버가 준 ISO 를 로컬 시간으로만 바꾼다. 상대시간("3일 전")은 쓰지 않는다. */
export function formatDateTime(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function versionLabel(version: number | null): string {
  return version === null ? "미배포" : `v${version}`;
}
