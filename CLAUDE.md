# CLAUDE.md

## Project

Codex(OpenAI) 플러그인 배포 저장소. 애플리케이션이 아니다. 빌드 산출물, 의존성 매니페스트,
테스트 러너, CI, DB, 서버 코드가 **없다**. 추적 파일은 14개뿐이다.

배포물은 세 가지다.
- 매니페스트 2개 — `.agents/plugins/marketplace.json`(마켓플레이스) → `plugins/didim-mcp/.codex-plugin/plugin.json`(플러그인)
- Windows 스크립트 2개 — `plugins/didim-mcp/scripts/migrate-didim-mcp.{ps1,cmd}`
- Skill 3개 — `plugins/didim-mcp/skills/*/SKILL.md`

플러그인은 **`plugin.json`의 `mcpServers`로 Hosted MCP 서버를 직접 선언한다.** 설치만으로
서버가 등록되고, **로그인은 Codex 내장 MCP OAuth 클라이언트가 수행**한다. 이 저장소는
OAuth를 구현하지 않는다 — client_id·client_secret·redirect URI·토큰을 보유하지 않는다.

`migrate-didim-mcp` 스크립트는 등록 도구가 **아니다.** 0.1.x가 사용자 `config.toml`에 남긴
레거시 `[mcp_servers.didim-mcp]` 블록을 지우는 1회성 정리 도구다. 그 블록이 남아 있으면
플러그인이 제공하는 서버를 **가려서**(shadow) OAuth가 아예 시작되지 않는다.

## Source of Truth

```
plugin.json · marketplace.json · SKILL.md · scripts/*.ps1   ← 실제 동작. 최우선.
        > README.md (루트, plugins/didim-mcp/)              ← 사람 대상 안내
```

README는 근거가 아니다. 충돌 시 소스를 따르고 사용자에게 알린다.

## Architecture

레이어드 아키텍처가 아니다. 두 개의 독립된 흐름만 있다.

**연결 시점** — 플러그인 설치 → Codex가 `plugin.json`의 `mcpServers` 등록 → 사용자가 Connect
→ Codex가 `/.well-known/oauth-protected-resource` 발견 → Didim Auth authorize(PKCE S256,
`resource=https://didimmcp-dev.didimservice.com/mcp`, `scope=read write`) → Microsoft Entra 로그인
→ Didim 동의 → loopback callback → 토큰 저장(Codex)

**런타임** — Codex 기동 → Streamable HTTP로 `https://didimmcp-dev.didimservice.com/mcp` 연결
(`Authorization: Bearer <Codex 관리 토큰>`) → 서버가 OAuth subject 기준으로 사용자별 활성 Tool만
노출 → Skill이 노출된 Tool만 사용

Skill 선택은 코드가 아니라 **SKILL.md frontmatter의 `description`** 이 결정한다. 이 프로젝트에
라우터·디스패처는 없다.

## Core Development Principles

- 이 저장소를 일반 애플리케이션처럼 다루지 않는다. 프레임워크·패키지 매니저·테스트 하네스·
  린터 설정을 새로 도입하지 않는다. 지금 없는 것은 의도된 것이다.
- **인증을 플러그인에서 구현하지 않는다.** OAuth client_id 하드코딩, client_secret 보관,
  redirect/callback 서버, Authorization 헤더 생성, Entra endpoint 직접 호출을 추가하지 않는다.
  그 책임은 Codex MCP OAuth 클라이언트와 didim-mcp-auth-backend에 있다.
- MCP URL은 `plugin.json` 한 곳에만 둔다. 스크립트나 Skill에 두 번째 사본을 만들지 않는다.
- 사용자의 `~/.codex/config.toml`은 남의 파일이다. 이 저장소 작업 중 읽거나 쓰지 않는다.
- 스크립트나 매니페스트 동작을 바꾸면 두 README(루트·플러그인)의 해당 서술을 같이 고친다.

## Safety / Constraints

- 인증 헤더 값, 토큰, 레거시 `dv_` API Key의 **원문을 출력·기록·커밋하지 않는다.** 상세는
  `.claude/rules/secrets.md`.
- migrate 스크립트를 이 환경에서 **실행하지 않는다.** 실행하면 사용자 실제
  `~/.codex/config.toml`이 바뀐다. 분석은 소스 독해로만 한다.
- 이 환경(Linux/WSL2)에 PowerShell 런타임이 없다(`pwsh` 부재). `.ps1` 변경을 "실행 검증했다"고
  보고하지 않는다. 정적 검토임을 명시한다.
- 사용자가 명시적으로 요청하지 않으면 `git commit` / `git push` 하지 않는다. 상세는
  `.claude/rules/release.md`.

## Verification

이 저장소에서 실제로 돌릴 수 있는 검증은 이게 전부다. 없는 테스트를 만들어내지 않는다.

```bash
python3 -m json.tool .agents/plugins/marketplace.json > /dev/null
python3 -m json.tool plugins/didim-mcp/.codex-plugin/plugin.json > /dev/null

# 레거시 인증 잔재가 런타임 경로에 없어야 한다 (README/Skill의 migration 안내는 예외)
grep -rn "dv_\|X-Didim-Vault-Api-Key\|http://" plugins/didim-mcp/.codex-plugin plugins/didim-mcp/scripts

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
