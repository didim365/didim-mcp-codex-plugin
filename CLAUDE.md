# CLAUDE.md

## Project

Codex(OpenAI) 플러그인 배포 저장소. 애플리케이션이 아니다. 빌드 산출물, 의존성 매니페스트,
테스트 러너, CI, DB, 서버 코드가 **없다**. 파일 수는 20개 미만이고, 그 중 사용자에게
배포되는 것은 `plugins/didim-mcp/` 아래뿐이다.

배포물은 세 가지다.
- 매니페스트 2개 — `.agents/plugins/marketplace.json`(마켓플레이스) → `plugins/didim-mcp/.codex-plugin/plugin.json`(플러그인)
- Windows 스크립트 2개 — `plugins/didim-mcp/scripts/migrate-didim-mcp.{ps1,cmd}`
- Skill 3개 — `plugins/didim-mcp/skills/*/SKILL.md`

플러그인은 **`plugin.json`의 `mcpServers`로 Hosted MCP 서버를 직접 선언한다.** 설치만으로
서버가 등록되고, **로그인은 Codex 내장 MCP OAuth 클라이언트가 수행**한다. 이 저장소는
OAuth를 구현하지 않는다 — client_id·client_secret·redirect URI·토큰을 보유하지 않는다.

`plugin.json`의 `interface` 블록(`displayName`, `shortDescription`, `longDescription`,
`capabilities`, `websiteURL`, `defaultPrompt`)은 Codex App의 플러그인 화면 표시만 결정한다.
동작에는 영향이 없다. `websiteURL`은 Didim MCP 포털
(`https://didimmcp-dev.didimservice.com/`)을 가리킨다 — MCP 엔드포인트와 같은 호스트이므로
도메인을 옮길 때 `mcpServers.didim-mcp.url`과 함께 고친다.

`migrate-didim-mcp` 스크립트는 등록 도구가 **아니다.** 0.1.x가 사용자 `config.toml`에 남긴
레거시 `[mcp_servers.didim-mcp]` 블록을 지우는 1회성 정리 도구다. 그 블록이 남아 있으면
플러그인이 제공하는 서버를 **가려서**(shadow) OAuth가 아예 시작되지 않는다.

## Source of Truth

```
plugin.json · marketplace.json · SKILL.md · scripts/*.ps1   ← 실제 동작. 최우선.
        > README.md (루트, plugins/didim-mcp/)              ← 사람 대상 안내
```

README는 근거가 아니다. 충돌 시 소스를 따르고 사용자에게 알린다.

문서의 역할은 겹치지 않게 나눠져 있다. 같은 내용을 두 곳에 길게 복제하지 않는다.

| 문서 | 독자 | 담는 것 |
| --- | --- | --- |
| `README.md` (루트) | 최종 사용자(한국어) | 설치·연결·업그레이드·제거·문제 해결 절차 |
| `plugins/didim-mcp/README.md` | 설치본과 함께 배포되는 영문 레퍼런스 | 플러그인 자체의 동작·스크립트·Skill·안전 규칙 (설치본에는 루트 README가 없으므로 자체 완결적으로 유지하고, 링크는 절대 URL로 쓴다) |
| `CLAUDE.md` | 이 저장소에서 작업하는 에이전트 | 저장소 역할, 아키텍처, invariant, 검증 명령 |
| `.claude/rules/*.md` | 에이전트(경로 스코프) | 해당 디렉터리를 건드릴 때만 필요한 상세 규칙 |

`AGENTS.md`는 두지 않는다. 이 규모에서는 `CLAUDE.md`와 내용이 즉시 갈라지기 때문이다.
Codex 쪽 지침이 필요해지면 `CLAUDE.md`를 옮기고 한쪽만 남긴다 — 양쪽에 복제하지 않는다.

## Architecture

레이어드 아키텍처가 아니다. 두 개의 독립된 흐름만 있다.

**연결 시점** — 플러그인 설치 → Codex가 `plugin.json`의 `mcpServers` 등록 → 호스트가 OAuth
sign-in 수행. 로그인이 **시작되는 경로는 두 가지뿐이다(검증됨)**: `marketplace.json`의
`policy.authentication: ON_INSTALL`에 의한 설치 시점 로그인, 그리고 미인증 상태에서 Tool을
처음 호출할 때 서버의 `401` + `WWW-Authenticate`가 띄우는 호스트 인증 흐름. 설치된
플러그인 제공 MCP 항목에는 Connect/Disconnect 버튼이 **없다**(Human UAT로 반증됨).

그 뒤의 세부 흐름은 Codex 호스트와 Didim Auth 사이의 계약이며 **이 저장소 소스로는 검증할 수
없다** — `/.well-known/oauth-protected-resource` 발견 → authorize(PKCE S256,
`resource=https://didimmcp-dev.didimservice.com/mcp`, `scope=read write`) → Microsoft Entra 로그인
→ Didim 동의 → loopback callback → 토큰 저장(Codex). 이 저장소를 고쳐서 바꿀 수 있는 부분이
아니므로, 문서에서 단정할 때는 출처가 서버 계약임을 함께 적는다.

**런타임** — Codex 기동 → Streamable HTTP로 `https://didimmcp-dev.didimservice.com/mcp` 연결
(`Authorization: Bearer <Codex 관리 토큰>`) → 서버가 OAuth subject 기준으로 사용자별 활성 Tool만
노출 → Skill이 노출된 Tool만 사용

Skill 선택은 코드가 아니라 **SKILL.md frontmatter의 `description`** 이 결정한다. 이 프로젝트에
라우터·디스패처는 없다.

**App runtime과 CLI runtime은 별개다(검증됨).** Codex App은 셸 명령을 별도 샌드박스 OS 계정
(`CodexSandboxOffline`/`CodexSandboxOnline`)으로 실행하므로, Skill이 실행한 중첩 `codex`는
App과 **다른 Codex 홈**을 읽는다. 실제로 플러그인이 동작 중인 채팅에서 `codex mcp list`와
`codex plugin list`가 0개로 나온다. App의 플러그인과 MCP OAuth 자격증명은 App 사용자
Codex 홈(`plugins/didim-mcp`, `secrets/mcp_oauth.age`)에 있다. **중첩 CLI 출력을 App 상태의
근거로 쓰지 않는다.** 재인증은 Tool 호출이 호스트 인증 흐름을 띄우는 경로를 정본으로 한다.

Tool 목록은 **동적이다.** 이 저장소는 Tool을 정의·열거·캐시하지 않는다. 서버가 `tools/list`로
로그인 사용자에게 허용된 것만 내려준다. 매니페스트·Skill·README에 Tool 카탈로그나 고정 개수를
박지 않는다(특정 Tool 이름을 Skill이 참조하는 것은 예외 — `.claude/rules/skills.md` 참조).

## Core Development Principles

- 이 저장소를 일반 애플리케이션처럼 다루지 않는다. 프레임워크·패키지 매니저·테스트 하네스·
  린터 설정을 새로 도입하지 않는다. 지금 없는 것은 의도된 것이다.
- **인증을 플러그인에서 구현하지 않는다.** OAuth client_id 하드코딩, client_secret 보관,
  redirect/callback 서버, Authorization 헤더 생성, Entra endpoint 직접 호출을 추가하지 않는다.
  그 책임은 Codex MCP OAuth 클라이언트와 didim-mcp-auth-backend에 있다.
- MCP URL은 `plugin.json` 한 곳에만 둔다. 스크립트나 Skill에 두 번째 사본을 만들지 않는다.
- 사용자의 `~/.codex/config.toml`은 남의 파일이다. 이 저장소 작업 중 읽거나 쓰지 않는다.
- 스크립트나 매니페스트 동작을 바꾸면 두 README(루트·플러그인)의 해당 서술을 같이 고친다.
- **외부 Provider resource credential을 레거시 API Key로 오인해 지우지 않는다.** 폐지된 것은
  사용자 로그인용 `dv_` 개인 키뿐이다. Vault에 저장된 공공데이터 `serviceKey`·SSH·외부 API
  자격증명은 현재도 정상 기능이며, 서버가 OAuth 신원을 확인한 뒤 주입한다.

## Safety / Constraints

- 인증 헤더 값, 토큰, 레거시 `dv_` API Key의 **원문을 출력·기록·커밋하지 않는다.** 상세는
  `.claude/rules/secrets.md`.
- migrate 스크립트를 이 환경에서 **실행하지 않는다.** 실행하면 사용자 실제
  `~/.codex/config.toml`이 바뀐다. 분석은 소스 독해로만 한다.
- 이 환경(Linux/WSL2)에 PowerShell 런타임이 없다(`pwsh` 부재). `.ps1` 변경을 "실행 검증했다"고
  보고하지 않는다. 정적 검토임을 명시한다.
- 사용자가 명시적으로 요청하지 않으면 `git commit` / `git push` 하지 않는다. 에이전트는
  파일 수정·검증까지만 하고, commit/push/브랜치 생성은 사용자가 직접 한다. 상세는
  `.claude/rules/release.md`.
- 플러그인 UAT 중에는 Direct MCP 등록(`didim-mcp-oauth-uat` 등)을 **동시에 켜두지 않는다.**
  둘 다 켜진 상태의 성공은 플러그인 경로의 PASS 근거가 되지 않는다.

## Verification

이 저장소에서 실제로 돌릴 수 있는 검증은 이게 전부다. 없는 테스트를 만들어내지 않는다.

```bash
python3 -m json.tool .agents/plugins/marketplace.json > /dev/null
python3 -m json.tool plugins/didim-mcp/.codex-plugin/plugin.json > /dev/null

# 레거시 인증 잔재가 런타임 경로에 없어야 한다.
# 기대 결과는 "정확히 1건" — migrate 스크립트의 .DESCRIPTION 주석이 지우려는 헤더 이름을
# 설명하는 줄이다. 그 밖의 hit(특히 dv_ 로 시작하는 실제 값, http:// URL)는 회귀다.
grep -rn "dv_\|X-Didim-Vault-Api-Key\|http://" plugins/didim-mcp/.codex-plugin plugins/didim-mcp/scripts

# 문서의 저장소 내부 상대 링크가 실제로 존재하는지
grep -rnoE '\]\([^)#h][^)]*\)' --include='*.md' . | sed -E 's/\]\(/\t/;s/\)$//'

# .ps1 은 BOM(efbbbf)이 있어야 하고, 그 외 파일에는 없어야 한다
for f in $(git ls-files); do printf '%s: ' "$f"; head -c3 "$f" | od -An -tx1; done

git diff --stat
```

`codex` CLI가 있으면, **사용자 CODEX_HOME을 건드리지 않도록 임시 `CODEX_HOME`을 지정해서만**
매니페스트를 실제로 검증한다.

```bash
export CODEX_HOME=$(mktemp -d)
codex plugin marketplace add "$PWD" && codex plugin add didim-mcp@didim
codex mcp list      # didim-mcp / HTTPS URL / Auth "Not logged in" 이면 정상
```

`.ps1` 변경 시에는 위에 더해 `.claude/rules/powershell-scripts.md`의 체크 항목을 눈으로 확인한다.
