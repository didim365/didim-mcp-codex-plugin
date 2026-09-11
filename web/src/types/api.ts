// backend DTO(`app/api/dto.py`)의 **사본**이다. 모르는 필드를 추측해서 추가하지 않는다 —
// backend DTO 를 먼저 확인한다.

export type SkillVersionStatus = "DRAFT" | "PUBLISHED" | "SUPERSEDED";

export type AuditOperation =
  | "SKILL_CREATE"
  | "SKILL_ENABLE"
  | "SKILL_DISABLE"
  | "DRAFT_CREATE"
  | "DRAFT_UPDATE"
  | "DRAFT_DELETE"
  | "PUBLISH"
  | "ROLLBACK";

export type AuditResult = "SUCCESS" | "FAILED" | "DENIED";

export interface PageMeta {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface Page<T> {
  items: T[];
  meta: PageMeta;
}

export interface SkillVersionSummary {
  id: string;
  version: number;
  name: string;
  status: SkillVersionStatus;
  created_by_name: string | null;
  created_at: string;
  published_by_name: string | null;
  published_at: string | null;
  rolled_back_from: number | null;
}

export interface SkillVersionDetail extends SkillVersionSummary {
  description: string;
  instructions: string;
  aliases: string[];
  tools: string[];
}

export interface SkillSummary {
  id: string;
  skill_key: string;
  category: string | null;
  enabled: boolean;
  published_version: number | null;
  published_name: string | null;
  draft_version: number | null;
  updated_at: string;
}

export interface SkillDetail extends SkillSummary {
  versions: SkillVersionSummary[];
  published: SkillVersionDetail | null;
  draft: SkillVersionDetail | null;
}

export interface AuditLogItem {
  id: string;
  actor_display_name: string | null;
  operation: AuditOperation;
  skill_key: string | null;
  skill_version: number | null;
  result: AuditResult;
  detail: Record<string, unknown> | null;
  created_at: string;
}

export interface Me {
  authenticated: boolean;
  user_id: string | null;
  display_name: string | null;
  email: string | null;
  role: string | null;
  is_admin: boolean;
  csrf_token: string | null;
  login_url: string;
  logout_url: string;
}

/** 버전 내용 입력 — 생성/수정/롤백이 같은 모양을 쓴다. */
export interface VersionContent {
  name: string;
  description: string;
  instructions: string;
  aliases: string[];
  tools: string[];
}

export interface SkillCreateRequest extends VersionContent {
  skill_key: string;
  category: string | null;
}
