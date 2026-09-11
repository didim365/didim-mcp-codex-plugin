# CLAUDE.md

Claude Code 가 이 저장소에서 **항상** 지켜야 하는 운영 계약이다. 프로젝트 소개 문서가
아니다 — 무엇을 만들었고 어떻게 실행하는지는 `README.md` 가 정본이다.

## Project

이 저장소는 **두 가지**를 담는다. 섞지 않는다.

| | 무엇인가 | 배포 경로 |
| --- | --- | --- |
| **Codex Plugin** `plugins/didim-mcp/` · `.agents/` | 매니페스트 2개 + 스크립트 2개 + Skill 5개 | `main` push → 사용자가 Codex 마켓플레이스 갱신 |
| **Skill Registry** `app/` · `web/` · `alembic/` | FastAPI + React Admin + `mcp_skill_registry` schema | Docker image → Harbor → ArgoCD (`didim-mcp-codex-plugin-deploy`) |

**설치본에 들어가는 것은 여전히 `plugins/didim-mcp/` 뿐이다.** Codex 는 설치 시 플러그인
디렉터리만 배포하므로 `app/`·`web/`·`alembic/`·`tests/`·`CLAUDE.md`·`.claude/` 는 사용자
PC 로 가지 않는다. 스크립트가 `plugins/didim-mcp/scripts/` 안에 있어야 하는 이유도 같다.

스택: Python 3.12 · FastAPI · SQLAlchemy 2 async / asyncpg / PostgreSQL · Alembic ·
Pydantic v2 · PyJWT · uv · pytest · ruff · mypy(strict) ·
React 19 + TypeScript 5.9(strict) + Vite + Tailwind v4 + vitest.

Entry point: `app/main.py:create_app()` → `uvicorn app.main:app`.

## Source of Truth

판단 근거의 우선순위. **위가 항상 이긴다.**

```
1. 실제 소스 — app/ · web/src/ · alembic/versions/ · plugins/didim-mcp/**
2. 테스트 — tests/ · web/src/**/*.test.tsx  (정책이 테스트로 고정된 경우가 많다)
3. Dockerfile · Jenkinsfile · pyproject.toml · web/package.json
4. README.md (루트, plugins/didim-mcp/)
```

문서와 코드가 어긋나면 **코드를 따르고, 어긋난 사실을 사용자에게 보고**한다.
문서에 맞추려고 코드를 바꾸지 않는다.

**runtime workflow 의 정본은 소스가 아니라 DB 다.** `app/seed/` 는 초기 이관 스냅샷이며
1회용이다 — 거기를 고쳐도 이미 seed 된 DB 는 바뀌지 않는다.

| 문서 | 독자 | 담는 것 |
| --- | --- | --- |
| `README.md` (루트) | 최종 사용자 + 운영자 + 개발자(한국어) | 설치·연결·문제 해결 / Registry 아키텍처·API·운영 |
| `plugins/didim-mcp/README.md` | 설치본과 함께 배포되는 영문 레퍼런스 | 플러그인 동작·스크립트·Skill·안전 규칙 (자체 완결, 링크는 절대 URL) |
| `CLAUDE.md` | 이 저장소에서 작업하는 에이전트 | 저장소 역할, invariant, 검증 명령 |
| `.claude/rules/*.md` | 에이전트(경로 스코프) | 해당 디렉터리를 건드릴 때만 필요한 상세 규칙 |

`AGENTS.md` 는 두지 않는다.

## Architecture

### Plugin 쪽 (변하지 않은 것)

**연결 시점** — 플러그인 설치 → Codex 가 `plugin.json` 의 `mcpServers` 등록 → 호스트가
OAuth sign-in 수행. 로그인이 **시작되는 경로는 두 가지뿐이다(검증됨)**:
`marketplace.json` 의 `policy.authentication: ON_INSTALL`, 그리고 미인증 상태에서 Tool 을
처음 호출할 때 서버의 `401` + `WWW-Authenticate` 가 띄우는 호스트 인증 흐름. 설치된
플러그인 제공 MCP 항목에는 Connect/Disconnect 버튼이 **없다**(Human UAT 로 반증됨).

**App runtime 과 CLI runtime 은 별개다(검증됨).** Codex App 은 셸 명령을 별도 샌드박스 OS
계정(`CodexSandboxOffline`/`Online`)으로 실행하므로 중첩 `codex` 는 App 과 **다른 Codex
홈**을 읽는다. **중첩 CLI 출력을 App 상태의 근거로 쓰지 않는다.**

Tool 목록은 **동적이다.** 이 저장소는 Tool 을 정의·열거·캐시하지 않는다.

### Skill 선택과 Skill 본문은 다른 축이다 — 가장 중요한 구분

```
Skill 선택   ← SKILL.md frontmatter description   (정적. 플러그인 릴리스 필요)
Skill 본문   ← DB mcp_skill_registry              (동적. Admin Web 배포)
```

Codex 의 Skill selector 는 DB 를 읽지 않는다. 그래서 **트리거 문구는 SKILL.md 에 남고
본문만 DB 로 갔다.**

그 구멍은 `didim-dynamic-skill` 하나로 메운다 — 전용 router 가 없는 Skill 을 위한
generic fallback 이다. `didim-skill__list_skills` 로 배포본 목록을 받아 Codex 가
`skill_key` 를 고른다. **그래서 새 Skill 은 플러그인 릴리스 없이 발견된다.**

정확히 말하면 이렇다.

| 하는 일 | 릴리스 필요? |
| --- | --- |
| 기존 Skill 의 절차 수정 | 아니오 (Admin Web Publish) |
| **새 Skill 등록·배포** | **아니오** (`didim-dynamic-skill` 이 목록에서 찾는다) |
| 전용 router 를 새로 두어 트리거 정확도를 올리는 것 | 예 |
| `didim-dynamic-skill` 의 description 자체를 고치는 것 | 예 |

"전부 DB 에서 바꿀 수 있다" 고도, "새 Skill 은 릴리스가 필요하다" 고도 말하지 않는다.
위 표가 정확한 서술이다.

### Registry 쪽

```
Browser ─ SSO ─┐
MCP gateway ───┼─→ Router ─→ Service ─→ Repository ─→ PostgreSQL(mcp_skill_registry)
Codex ─────────┘                └─→ Auth(/me · JWKS · login_code) 호출
```

항상 참인 것:

- **Router → Service → Repository.** `app/api/**` 는 Repository 를 직접 호출하지 않는다
  (목록 조회처럼 정책이 없는 경로는 예외로 Repository 를 직접 쓴다 — 그때도 DTO 매핑은
  `app/api/mappers.py` 를 거친다).
- **트랜잭션 경계는 `app/api/deps.py:get_session` 이 소유한다.** Service·Repository 는
  `flush` 만 하고 `commit` 하지 않는다.
- **ORM Entity ↔ API DTO 분리.** `app/db/models` 를 응답으로 그대로 내보내지 않는다.
- 모든 DB 객체는 **전용 schema `mcp_skill_registry`** 안에만 있다.
- 설정은 `app/core/config.py:Settings` 하나뿐이다. 환경변수 prefix `DIDIM_SKILL_`.
- **인가 가드는 route decorator 가 아니라 `app/api/v1/router.py` 의
  `include_router(..., dependencies=[Depends(require_admin)])` 에 붙는다.** 개별 endpoint
  만 읽고 "인증이 없다" 고 판단하지 않는다.
- **SPA fallback 은 맨 마지막에 등록한다**(catch-all). `app/web/spa.py` 의
  `_RESERVED_PREFIXES` 에 있는 경로는 절대 index.html 로 떨어지지 않는다.

## Core Development Principles

- **추측하지 말고 먼저 읽는다.** 신규 기능·버그 수정 전에 관련 호출 경로·의존 관계를 실제
  파일에서 확인한다.
- **버그는 증상이 아니라 근본 원인을 고친다.** 공유 함수 한 곳을 고쳐 모든 호출부를
  바로잡는다.
- **요청되지 않은 추상화·설정·스캐폴딩을 만들지 않는다.** 이미 있는 것을 재사용한다.
- **기존 계약을 임의로 바꾸지 않는다** — 인증 정책, runtime API 응답 형태, DB schema,
  `skill_key` 형식, MCP Tool 이름.
- 동작을 바꿨으면 그 동작을 검증하는 테스트를 추가하거나 수정한다.
- 주석·docstring·화면 문구는 한국어로 쓴다(저장소 전체가 한국어).
- mypy strict 를 통과해야 한다. `# type: ignore` 는 사유 주석과 함께만 쓴다.
- **frontend 에 의존성을 새로 추가하지 않는다.** 차트도 server-state 도 라우터도 이미 없이
  돌아간다(`web/src/lib/useResource.ts`, `web/src/lib/router.ts`).

## Invariants (깨면 사고다)

- **`mcp_skill_registry` schema 의 migration owner 는 이 저장소 하나다.** 다른 DIDIM
  저장소가 이 schema 를 소유하지 않고, 이 저장소는 남의 schema 를 건드리지 않는다.
  **DROP SCHEMA 는 어떤 경로로도 실행하지 않는다.**
- **모든 mutation 은 ADMIN 전용이다.** 미인증 401 / USER·DEVELOPER 403 / 위임 토큰 403.
  화면에서 감추는 것은 인가가 아니다.
- **runtime 에는 PUBLISHED + enabled 만 나간다.** DRAFT 가 Codex 에 보이면 안 된다.
  필터는 `RuntimeSkillRepository` 의 SQL 에 있다 — 애플리케이션 후처리로 거르지 않는다.
- **DB 가 workflow 의 runtime source of truth 다.** 같은 본문을 정적 SKILL.md 에 두 번째
  정본으로 복제하지 않는다.
- **정적 SKILL.md 는 bootstrap / router 다.** 업무 절차 본문을 다시 넣지 않는다. 예외는
  `didim-mcp-connect` — 연결이 끊긴 상태를 다루므로 Registry 에 의존할 수 없다.
- **MCP gateway 가 Tool 인가 정본이다.** `skill_version_tools` 는 orchestration 정보다.
  Registry 가 인가를 판단하거나 우회하는 코드를 만들지 않는다.
- **role 정본은 Auth `GET /api/v1/me` 의 `role`** 이다. JWT 에 role claim 이 없다.
  로컬 사용자 테이블을 만들지 않는다.
- **감사에 raw secret 을 넣지 않는다.** `AuditService._sanitize` 의 금지 키 목록을
  약화하지 않는다. `detail` 에 요청 본문·instructions 를 통째로 넣지 않는다.
- **Alembic 은 앱 시작 시 자동 실행되지 않는다**(의도적). 새 컬럼을 기대하는 이미지를
  배포하면 migration Job 이 별도로 필요하다.
- **commit 은 `TransactionalRoute` 가 응답 직전에 한다.** `get_session` 의 teardown 은
  응답을 보낸 뒤 실행되므로 거기에만 맡기면 read-after-write 가 깨진다. 새 라우터 파일에
  `route_class=TransactionalRoute` 를 빠뜨리지 않는다.
- **`/ready` 는 schema 가 없으면 503 이다.** migration 전에 Pod 이 Ready 가 되면 kubelet
  이 트래픽을 붙이고 모든 API 가 "relation does not exist" 로 죽는다. 이 체크가 배포
  순서를 manifest 밖에서 강제하는 장치다 — 완화하지 않는다. `/health` 는 반대로 의존성을
  보지 않는다(DB 가 죽었다고 Pod 을 재시작하면 안 된다).
- **이 저장소는 public 이다.** 사내 Harbor 주소·DB 호스트·TLS 검사 CA 를 소스에 적지
  않는다. Harbor 는 Jenkins 의 `HARBOR_REGISTRY`, CA 는 Jenkins Secret file
  `didim-fortigate-ca` 에서 온다(`certs/*.crt` 는 `.gitignore`). README 에는
  placeholder 만 쓴다.
- **`didim-skill__get_skill` / `didim-skill__list_skills` 이름을 바꾸지 않는다.** router
  SKILL.md 4개가 이 문자열을 참조하고,
  `tests/test_runtime_contract.py::test_skill_md_tool_names_match_runtime_operation_ids`
  가 양쪽을 대조해 고정한다. 이름은 `<provider_slug>__<operationId>` 로
  조립되므로 runtime endpoint 의 `operation_id` 와 gateway 의 provider slug 양쪽에 묶여
  있다.
- **MCP gateway 등록용 문서는 `/api/v1/runtime/openapi.json` 이다.** 전체
  `/openapi.json` 을 등록하면 Admin mutation 이 Tool 후보가 된다.

## Safety / Constraints

- 인증 헤더 값, 토큰, DB 비밀번호, 세션 서명 키, 레거시 `dv_` API Key 의 **원문을
  출력·기록·커밋하지 않는다.** 상세는 `.claude/rules/secrets.md`.
- migrate 스크립트를 이 환경에서 **실행하지 않는다.** 실행하면 사용자 실제
  `~/.codex/config.toml` 이 바뀐다. 분석은 소스 독해로만 한다.
- 이 환경(Linux/WSL2)에 PowerShell 런타임이 없다(`pwsh` 부재). `.ps1` 변경을 "실행
  검증했다" 고 보고하지 않는다.
- **원격 인프라에 임의 명령을 실행하지 않는다** — 원격 PostgreSQL, NCP Kubernetes, Harbor,
  Jenkins, ArgoCD, deploy 저장소.
- **다른 저장소를 수정하지 않는다**(읽기 전용 참조): `didim-mcp-auth-backend`,
  `didim-mcp-service-backend`, `didim-vault-backend`, `didim-rag-backend`,
  각 `-deploy`, 그리고 `didim-mcp-codex-plugin-deploy`(별도 작업 단위).
- **인증이 꺼진 상태를 "운영 완료" 라고 표현하지 않는다.** `auth_enabled` ·
  `runtime_auth_required` · `cookie_secure` 는 운영에서 반드시 켜져 있어야 한다.
- **미결정 값을 추측하지 않는다.** Auth 의 `JWT_SERVICE_AUDIENCES` / SSO service callback
  등록값, DB 계정, Harbor project, DNS 는 사람이 확인한다.
- 사용자가 명시적으로 요청하지 않으면 `git commit` / `git push` 하지 않는다. 상세는
  `.claude/rules/release.md`.
- 플러그인 UAT 중에는 Direct MCP 등록을 **동시에 켜두지 않는다.**

## Verification

```bash
# backend
uv sync --dev
uv run ruff format --check .
uv run ruff check .
uv run mypy app
uv run pytest

# PostgreSQL 통합(동시 publish · 부분 unique index). **skip 수를 반드시 확인한다**
docker run -d --name pgtest-skill -e POSTGRES_USER=pgtest -e POSTGRES_PASSWORD=pgtest \
  -e POSTGRES_DB=pgtest -p 55433:5432 postgres:16-alpine
DIDIM_SKILL_TEST_DATABASE_URL="postgresql+asyncpg://pgtest:pgtest@127.0.0.1:55433/pgtest?ssl=disable" \
  uv run pytest tests/integration -m integration

# frontend
cd web && npm run typecheck && npm run lint && npm run test && npm run build

# 플러그인 매니페스트
python3 -m json.tool .agents/plugins/marketplace.json > /dev/null
python3 -m json.tool plugins/didim-mcp/.codex-plugin/plugin.json > /dev/null

# thin router 가 Registry 참조를 잃지 않았는지
grep -l 'didim-skill__get_skill' plugins/didim-mcp/skills/*/SKILL.md   # 4건이어야 한다

# 레거시 인증 잔재가 런타임 경로에 없어야 한다(기대: 정확히 1건 — migrate 스크립트 주석)
grep -rn "dv_\|X-Didim-Vault-Api-Key\|http://" \
  plugins/didim-mcp/.codex-plugin plugins/didim-mcp/scripts

# .ps1 은 BOM(efbbbf)이 있어야 하고, 그 외 파일에는 없어야 한다
for f in $(git ls-files); do printf '%s: ' "$f"; head -c3 "$f" | od -An -tx1; done

docker build -t didim-mcp-codex-plugin:local .
git diff --check
```

**함정:**

- **PostgreSQL 통합 테스트는 DSN 이 없으면 실패가 아니라 skip 이다** — "N skipped" 가
  성공처럼 보인다. 결과를 보고하기 전에 skip 수를 확인한다. 단위 테스트(SQLite)는
  `SELECT ... FOR UPDATE` 를 검증하지 못한다.
- **`web/` 의 타입 오류는 `npm run build` 에서만 드러난다** — `tests` 도 `tsconfig` 의
  `include` 에 들어 있어 테스트 파일 타입 오류가 Docker 빌드를 멈춘다(실제로 겪었다).
- `codex` CLI 로 매니페스트를 검증할 때는 **반드시 임시 `CODEX_HOME`** 을 쓴다.

**실행하지 못한 검사를 실행한 것처럼 보고하지 않는다.**

## Rules

| 파일 | 적용 대상 | 다루는 것 |
|---|---|---|
| `.claude/rules/skills.md` | `plugins/didim-mcp/skills/**` | SKILL.md 작성 규칙, thin router 계약 |
| `.claude/rules/powershell-scripts.md` | `plugins/didim-mcp/scripts/**` | PS 5.1 호환, 인코딩, config.toml 수정 순서 |
| `.claude/rules/secrets.md` | 전역 | 비밀정보 취급 |
| `.claude/rules/release.md` | 전역 | 배포·버전·Git 규칙 |
| `.claude/rules/registry.md` | `app/**`, `web/**`, `alembic/**` | Registry 계층·인가·DB·화면 규칙 |

전역 도구(ponytail·GSD·gstack 등)는 **작업 방법(how)** 을 제공한다. 이 저장소의
`CLAUDE.md` 와 `.claude/rules/` 는 **지켜야 할 것(what)** 을 정의하며, 충돌 시 이 규칙이
우선한다.
